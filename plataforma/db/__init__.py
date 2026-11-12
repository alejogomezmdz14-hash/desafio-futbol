"""Capa de datos única del equipo (T11, contratos v1.4 §10).

Funciona igual con Postgres (DATABASE_URL=postgres://... o postgresql://...) y con
SQLite en modo local (DATABASE_URL=sqlite:///salida/plataforma.db).
"""
import hmac
import json
import os
import secrets
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Tuple

RAIZ = Path(__file__).resolve().parents[2]
ESQUEMA_SQL = (Path(__file__).resolve().parent / "esquema.sql").read_text(encoding="utf-8")
ARG = timezone(timedelta(hours=-3))

# Mapeo de cada tabla a su columna de clave primaria (además de partido_id) y columnas extra.
_TABLAS: Dict[str, Tuple[str, Tuple[str, ...]]] = {
    "casos": ("caso_id", ("clasificacion",)),
    "expedientes": ("expediente_id", ("hash",)),
    "pedidos": ("pedido_id", ("estado", "juez_id", "juzgado_id", "decidido_min", "motivo_rechazo", "despachado")),
    "ordenes": ("orden_id", ("pedido_id", "proveedor_id", "estado")),
    "reclamos": ("reclamo_id", ("estado",)),
}


def ahora_ts() -> str:
    return datetime.now(ARG).isoformat(timespec="seconds")


def _url_db() -> str:
    return os.environ.get("DATABASE_URL") or os.environ.get("POSTGRES_URL") or "sqlite:///salida/plataforma.db"


def _es_postgres(url: Optional[str] = None) -> bool:
    u = (url or _url_db()).lower()
    return u.startswith("postgres://") or u.startswith("postgresql://")


def _q(sql: str, pg: Optional[bool] = None) -> str:
    """Convierte placeholders '?' a '%s' cuando el driver es psycopg (Postgres)."""
    es_pg = _es_postgres() if pg is None else pg
    if es_pg:
        return sql.replace("?", "%s")
    return sql


def _json_param(obj: Any, pg: bool) -> Any:
    texto = json.dumps(obj, ensure_ascii=False)
    if pg:
        from psycopg.types.json import Jsonb  # type: ignore
        return Jsonb(obj)
    return texto


def _json_load(val: Any) -> Any:
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, (bytes, bytearray)):
        val = val.decode("utf-8")
    if isinstance(val, str):
        return json.loads(val)
    return val


def conectar():
    """Abre y devuelve una conexión nueva según DATABASE_URL (postgres:// -> psycopg, sqlite:/// -> sqlite3)."""
    url = _url_db()
    if _es_postgres(url):
        import psycopg  # type: ignore
        return psycopg.connect(url, autocommit=False)
    ruta_str = url[len("sqlite:///"):] if url.startswith("sqlite:///") else url
    if ruta_str != ":memory:":
        ruta = Path(ruta_str)
        if not ruta.is_absolute():
            ruta = RAIZ / ruta
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta_str = str(ruta)
    conn = sqlite3.connect(ruta_str, timeout=15.0)
    conn.row_factory = sqlite3.Row
    return conn


# Procesos largos (el motor) reusan una conexión por hilo: abrir una contra Neon cuesta ~0,8 s y, a x30,
# eso son minutos de partido por vuelta. La web de Vercel sigue con una conexión por request.
_persistente = False
_local = threading.local()


def usar_conexion_persistente(si: bool = True) -> None:
    global _persistente
    _persistente = si


@contextmanager
def _sesion() -> Iterator[Tuple[Any, Any, bool]]:
    pg = _es_postgres()
    if _persistente:
        conn = getattr(_local, "conn", None)
        if conn is None or getattr(conn, "closed", False):
            conn = conectar()
            _local.conn = conn
        try:
            cur = conn.cursor()
            yield conn, cur, pg
            conn.commit()
        except Exception:
            # Ante cualquier error se descarta la conexión: la próxima sesión abre una sana.
            for cerrar in (conn.rollback, conn.close):
                try:
                    cerrar()
                except Exception:
                    pass
            _local.conn = None
            raise
        return
    conn = conectar()
    try:
        cur = conn.cursor()
        yield conn, cur, pg
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def crear_esquema() -> None:
    """Corre esquema.sql de forma idempotente en Postgres o SQLite."""
    sin_comentarios = "\n".join(
        linea.split("--", 1)[0] for linea in ESQUEMA_SQL.splitlines()
    )
    with _sesion() as (_, cur, _):
        for sentencia in sin_comentarios.split(";"):
            s = sentencia.strip()
            if s:
                cur.execute(s)


def _combinar_pedido(datos: Dict[str, Any], estado: str, juez_id: Optional[str],
                     juzgado_id: Optional[str], decidido_min: Optional[float],
                     motivo_rechazo: Optional[str]) -> Dict[str, Any]:
    d = dict(datos)
    d["estado"] = estado
    d["juez_id"] = juez_id
    d["juzgado_id"] = juzgado_id
    d["decidido_min"] = decidido_min
    d["motivo_rechazo"] = motivo_rechazo
    return d


# =====================================================================================
# Funciones del Motor (T05) y piezas que escriben
# =====================================================================================

def guardar(tabla: str, partido_id: str, id_: str, datos: Dict[str, Any], **columnas: Any) -> None:
    """Upsert por (partido_id, id_) en casos, expedientes, pedidos, ordenes o reclamos."""
    if tabla not in _TABLAS:
        raise ValueError(f"Tabla no soportada en guardar(): {tabla}")
    pk_col, cols_extra = _TABLAS[tabla]

    # Extraer valores de columnas extra desde kwargs o desde el propio dict datos.
    valores_extra: Dict[str, Any] = {}
    for c in cols_extra:
        if c in columnas:
            valores_extra[c] = columnas[c]
        elif c in datos:
            valores_extra[c] = datos[c]
        elif c == "estado" and tabla == "pedidos":
            valores_extra[c] = "pendiente"
        elif c == "despachado" and tabla == "pedidos":
            valores_extra[c] = False
        else:
            valores_extra[c] = None

    with _sesion() as (_, cur, pg):
        nombres_cols = ["partido_id", pk_col] + list(cols_extra) + ["datos"]
        placeholders = ", ".join(["?"] * len(nombres_cols))
        updates = ", ".join([f"{c} = EXCLUDED.{c}" for c in list(cols_extra) + ["datos"]])
        sql = (
            f"INSERT INTO {tabla} ({', '.join(nombres_cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT (partido_id, {pk_col}) DO UPDATE SET {updates}"
        )
        params = [partido_id, id_] + [valores_extra[c] for c in cols_extra] + [_json_param(datos, pg)]
        cur.execute(_q(sql, pg), params)


def guardar_estado_partido(partido_id: str, estado_api: Dict[str, Any]) -> None:
    """Upsert del estado vivo del partido en la tabla partidos."""
    ts = ahora_ts()
    with _sesion() as (_, cur, pg):
        sql = (
            "INSERT INTO partidos (partido_id, datos, actualizado_ts) VALUES (?, ?, ?) "
            "ON CONFLICT (partido_id) DO UPDATE SET datos = EXCLUDED.datos, actualizado_ts = EXCLUDED.actualizado_ts"
        )
        cur.execute(_q(sql, pg), [partido_id, _json_param(estado_api, pg), ts])


def agregar_auditoria(partido_id: str, evento: Dict[str, Any]) -> None:
    """INSERT en auditoria; falla si (partido_id, seq) ya existe."""
    with _sesion() as (_, cur, pg):
        sql = "INSERT INTO auditoria (partido_id, seq, hash, hash_prev, datos) VALUES (?, ?, ?, ?, ?)"
        cur.execute(_q(sql, pg), [
            partido_id,
            int(evento["seq"]),
            str(evento["hash"]),
            str(evento["hash_prev"]),
            _json_param(evento, pg),
        ])


def ultimo_evento_auditoria(partido_id: str) -> Optional[Dict[str, Any]]:
    """Devuelve el último EventoAuditoria de ese partido (para encadenar el próximo hash) o None."""
    with _sesion() as (_, cur, pg):
        sql = "SELECT datos FROM auditoria WHERE partido_id = ? ORDER BY seq DESC LIMIT 1"
        cur.execute(_q(sql, pg), [partido_id])
        row = cur.fetchone()
        return _json_load(row[0]) if row else None


def pedidos_para_despachar(partido_id: str) -> List[Dict[str, Any]]:
    """Devuelve los pedidos con estado = 'aprobado' y despachado = FALSE."""
    with _sesion() as (_, cur, pg):
        sql = (
            "SELECT datos, estado, juez_id, juzgado_id, decidido_min, motivo_rechazo "
            "FROM pedidos WHERE partido_id = ? AND estado = 'aprobado' AND despachado = ?"
        )
        cur.execute(_q(sql, pg), [partido_id, False])
        filas = cur.fetchall()
        return [
            _combinar_pedido(_json_load(r[0]), r[1], r[2], r[3], r[4], r[5])
            for r in filas
        ]


def marcar_despachado(partido_id: str, pedido_id: str) -> None:
    """Marca un pedido como despachado = TRUE."""
    with _sesion() as (_, cur, pg):
        sql = "UPDATE pedidos SET despachado = ? WHERE partido_id = ? AND pedido_id = ?"
        cur.execute(_q(sql, pg), [True, partido_id, pedido_id])


def solicitudes_pendientes(partido_id: str) -> List[Dict[str, Any]]:
    """Devuelve las solicitudes de la web aún no resueltas por el motor (resultado IS NULL)."""
    with _sesion() as (_, cur, pg):
        sql = (
            "SELECT solicitud_id, tipo, datos, creada_ts "
            "FROM solicitudes WHERE partido_id = ? AND resultado IS NULL ORDER BY creada_ts ASC"
        )
        cur.execute(_q(sql, pg), [partido_id])
        return [
            {
                "solicitud_id": r[0],
                "partido_id": partido_id,
                "tipo": r[1],
                "datos": _json_load(r[2]),
                "creada_ts": r[3],
                "resultado": None,
            }
            for r in cur.fetchall()
        ]


def resolver_solicitud(partido_id: str, solicitud_id: str, resultado: Dict[str, Any]) -> None:
    """Completa el resultado de una solicitud procesada por el motor."""
    with _sesion() as (_, cur, pg):
        sql = "UPDATE solicitudes SET resultado = ? WHERE partido_id = ? AND solicitud_id = ?"
        cur.execute(_q(sql, pg), [_json_param(resultado, pg), partido_id, solicitud_id])


def guardar_verificacion(partido_id: str, salida: str) -> None:
    """Guarda la salida de evaluacion/verificar.py en verificaciones (T12)."""
    ts = ahora_ts()
    with _sesion() as (_, cur, pg):
        sql = (
            "INSERT INTO verificaciones (partido_id, salida, creada_ts) VALUES (?, ?, ?) "
            "ON CONFLICT (partido_id) DO UPDATE SET salida = EXCLUDED.salida, creada_ts = EXCLUDED.creada_ts"
        )
        cur.execute(_q(sql, pg), [partido_id, salida, ts])


def obtener_verificacion(partido_id: str) -> Optional[Dict[str, Any]]:
    """Devuelve la verificación guardada para partido_id o None."""
    with _sesion() as (_, cur, pg):
        sql = "SELECT partido_id, salida, creada_ts FROM verificaciones WHERE partido_id = ?"
        cur.execute(_q(sql, pg), [partido_id])
        r = cur.fetchone()
        if not r:
            return None
        return {"partido_id": r[0], "salida": r[1], "creada_ts": r[2]}


# =====================================================================================
# Funciones de la Web (T11, T04, T07) que leen
# =====================================================================================

def obtener(tabla: str, partido_id: str, id_: str) -> Optional[Dict[str, Any]]:
    """Devuelve el dict del contrato por (partido_id, id_) o None."""
    if tabla not in _TABLAS:
        raise ValueError(f"Tabla no soportada en obtener(): {tabla}")
    pk_col, _ = _TABLAS[tabla]
    with _sesion() as (_, cur, pg):
        if tabla == "pedidos":
            sql = (
                "SELECT datos, estado, juez_id, juzgado_id, decidido_min, motivo_rechazo "
                f"FROM pedidos WHERE partido_id = ? AND {pk_col} = ?"
            )
            cur.execute(_q(sql, pg), [partido_id, id_])
            r = cur.fetchone()
            if not r:
                return None
            return _combinar_pedido(_json_load(r[0]), r[1], r[2], r[3], r[4], r[5])
        else:
            sql = f"SELECT datos FROM {tabla} WHERE partido_id = ? AND {pk_col} = ?"
            cur.execute(_q(sql, pg), [partido_id, id_])
            r = cur.fetchone()
            if not r:
                return None
            datos = _json_load(r[0])
            return datos


def listar(tabla: str, partido_id: str, **filtros: Any) -> List[Dict[str, Any]]:
    """Devuelve la lista de dicts de la tabla para partido_id, aplicando filtros opcionales por columna."""
    if tabla not in _TABLAS:
        raise ValueError(f"Tabla no soportada en listar(): {tabla}")
    pk_col, cols_extra = _TABLAS[tabla]
    conds = ["partido_id = ?"]
    params: List[Any] = [partido_id]
    for k, v in filtros.items():
        if v is None:
            continue
        if k not in cols_extra and k != pk_col:
            raise ValueError(f"Filtro inválido {k} para tabla {tabla}")
        conds.append(f"{k} = ?")
        params.append(v)
    where = " AND ".join(conds)

    with _sesion() as (_, cur, pg):
        if tabla == "pedidos":
            sql = (
                "SELECT datos, estado, juez_id, juzgado_id, decidido_min, motivo_rechazo "
                f"FROM pedidos WHERE {where} ORDER BY {pk_col} ASC"
            )
            cur.execute(_q(sql, pg), params)
            return [
                _combinar_pedido(_json_load(r[0]), r[1], r[2], r[3], r[4], r[5])
                for r in cur.fetchall()
            ]
        else:
            sql = f"SELECT datos FROM {tabla} WHERE {where} ORDER BY {pk_col} ASC"
            cur.execute(_q(sql, pg), params)
            return [_json_load(r[0]) for r in cur.fetchall()]


def estado_partido(partido_id: Optional[str]) -> Optional[Dict[str, Any]]:
    """Devuelve el dict de GET /api/estado para partido_id. Si el motor no actualizó hace > 5 s, simulador_ok=False."""
    if not partido_id:
        return None
    with _sesion() as (_, cur, pg):
        sql = "SELECT datos, actualizado_ts FROM partidos WHERE partido_id = ?"
        cur.execute(_q(sql, pg), [partido_id])
        r = cur.fetchone()
        if not r:
            return None
        datos = dict(_json_load(r[0]))
        ts_str = r[1]
        try:
            dt = datetime.fromisoformat(ts_str)
            if (datetime.now(ARG) - dt).total_seconds() > 5.0:
                datos["simulador_ok"] = False
        except Exception:
            pass
        return datos


def auditoria(partido_id: str) -> List[Dict[str, Any]]:
    """Devuelve los eventos de auditoría en orden de seq."""
    with _sesion() as (_, cur, pg):
        sql = "SELECT datos FROM auditoria WHERE partido_id = ? ORDER BY seq ASC"
        cur.execute(_q(sql, pg), [partido_id])
        return [_json_load(r[0]) for r in cur.fetchall()]


def partido_actual() -> Optional[str]:
    """Devuelve el partido_id con actualizado_ts más reciente en partidos, o None."""
    with _sesion() as (_, cur, pg):
        sql = "SELECT partido_id FROM partidos ORDER BY actualizado_ts DESC LIMIT 1"
        cur.execute(_q(sql, pg))
        r = cur.fetchone()
        return r[0] if r else None


# =====================================================================================
# Funciones de la Web que deciden (las únicas que escriben desde Vercel)
# =====================================================================================

def decidir_pedido(
    partido_id: str,
    pedido_id: str,
    estado: str,
    juez_id: str,
    juzgado_id: Optional[str],
    decidido_min: float,
    motivo: Optional[str] = None,
) -> bool:
    """Cambia atómicamente un pedido de 'pendiente' a 'aprobado' o 'rechazado'. Devuelve True si se actualizó."""
    with _sesion() as (_, cur, pg):
        sql = (
            "UPDATE pedidos SET estado = ?, juez_id = ?, juzgado_id = ?, decidido_min = ?, motivo_rechazo = ? "
            "WHERE partido_id = ? AND pedido_id = ? AND estado = 'pendiente'"
        )
        cur.execute(_q(sql, pg), [estado, juez_id, juzgado_id, decidido_min, motivo, partido_id, pedido_id])
        return cur.rowcount == 1


def crear_solicitud(partido_id: str, tipo: str, datos: Dict[str, Any]) -> str:
    """Crea una fila en solicitudes (asumir_turno | levantar) para que el motor la resuelva y devuelve solicitud_id."""
    solicitud_id = f"sol-{uuid.uuid4().hex[:8]}"
    ts = ahora_ts()
    with _sesion() as (_, cur, pg):
        sql = "INSERT INTO solicitudes (partido_id, solicitud_id, tipo, datos, creada_ts, resultado) VALUES (?, ?, ?, ?, ?, NULL)"
        cur.execute(_q(sql, pg), [partido_id, solicitud_id, tipo, _json_param(datos, pg), ts])
    return solicitud_id


# =====================================================================================
# Firmas y ajustes (T13: accesos de jueces por link que vence)
# =====================================================================================


def registrar_firma(partido_id: str, pedido_id: str, firmado_por: str, via: str) -> None:
    """Guarda quién firmó la decisión de un pedido. La primera firma es la que vale."""
    with _sesion() as (_, cur, pg):
        cur.execute(_q("INSERT INTO firmas (partido_id, pedido_id, firmado_por, via, creada_ts) VALUES (?, ?, ?, ?, ?) "
                       "ON CONFLICT (partido_id, pedido_id) DO NOTHING", pg),
                    (partido_id, pedido_id, firmado_por, via, ahora_ts()))


def firmante(partido_id: str, pedido_id: str) -> Optional[Dict[str, str]]:
    with _sesion() as (_, cur, pg):
        cur.execute(_q("SELECT firmado_por, via FROM firmas WHERE partido_id = ? AND pedido_id = ?", pg),
                    (partido_id, pedido_id))
        fila = cur.fetchone()
    return {"firmado_por": fila[0], "via": fila[1]} if fila else None


def leer_ajuste(clave: str, defecto: str) -> str:
    with _sesion() as (_, cur, pg):
        cur.execute(_q("SELECT valor FROM ajustes WHERE clave = ?", pg), (clave,))
        fila = cur.fetchone()
    return fila[0] if fila else defecto


def escribir_ajuste(clave: str, valor: str) -> None:
    with _sesion() as (_, cur, pg):
        cur.execute(_q("INSERT INTO ajustes (clave, valor) VALUES (?, ?) "
                       "ON CONFLICT (clave) DO UPDATE SET valor = EXCLUDED.valor", pg), (clave, valor))
