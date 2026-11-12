"""API pública de la plataforma (T11, contratos v1.5 §5).

Se despliega en Vercel (entrypoint: plataforma.api.app:app) y también se usa en modo local.
No guarda estado en memoria ni lee claves de firma: todo sale de `plataforma.db`.
"""
import hmac
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from plataforma import db
from plataforma.contratos import (
    EJEMPLO_SIM_JUZGADOS,
    ESTADOS_ORDEN_ACTIVA,
)

RAIZ = Path(__file__).resolve().parents[2]
WEB_DIR = RAIZ / "plataforma" / "web"

# Mapa público juez_id -> juzgado_id (de EJEMPLO_SIM_JUZGADOS; nunca lee datos/juzgados.json).
_JUZGADO_DE_JUEZ: Dict[str, str] = {
    juez["id"]: juzgado["id"]
    for juzgado in EJEMPLO_SIM_JUZGADOS["juzgados"]
    for juez in juzgado["jueces"]
}

# Nombres públicos (ficticios) para el registro de transparencia.
_NOMBRE_JUZGADO: Dict[str, str] = {j["id"]: j["nombre"] for j in EJEMPLO_SIM_JUZGADOS["juzgados"]}
_NOMBRE_JUEZ: Dict[str, str] = {
    juez["id"]: juez["nombre"] for j in EJEMPLO_SIM_JUZGADOS["juzgados"] for juez in j["jueces"]
}

app = FastAPI(title="Plataforma Federal de Órdenes de Bloqueo en Vivo")

# T12: partido de demo online (Vercel Sandbox). Las rutas viven en plataforma/nube/.
from plataforma.nube.rutas import router as _router_demo  # noqa: E402
app.include_router(_router_demo)


@app.on_event("startup")
def _startup() -> None:
    try:
        db.crear_esquema()
    except Exception:
        pass


@app.exception_handler(HTTPException)
async def _http_error(_, exc: HTTPException):
    detalle = exc.detail
    if isinstance(detalle, dict) and "error" in detalle:
        return JSONResponse(status_code=exc.status_code, content=detalle)
    return JSONResponse(status_code=exc.status_code, content={"error": str(detalle)})


def pin_juez(x_juez_pin: Optional[str] = Header(default=None)) -> None:
    esperado = os.environ.get("JUEZ_PIN", "")
    if not esperado or not x_juez_pin or not hmac.compare_digest(x_juez_pin.encode(), esperado.encode()):
        raise HTTPException(status_code=401, detail={"error": "PIN de juez inválido"})


def _partido_o_defecto(partido_id: Optional[str] = None) -> str:
    pid = partido_id or db.partido_actual()
    return pid or "demo"


def _resumen_de_caso(caso: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "caso_id": caso["caso_id"],
        "host": caso["host"],
        "ip": caso["ip"],
        "organizacion": caso.get("organizacion"),
        "marca": caso.get("marca"),
        "motivo_clasificacion": caso["motivo_clasificacion"],
        "ip_compartida": caso["ip_compartida"],
        "dominios_en_ip": caso.get("dominios_en_ip", []),
        "tipo_recomendado": caso["tipo_recomendado"],
        "motivo_tipo": caso["motivo_tipo"],
        "primer_minuto": caso["primer_minuto"],
    }


def _recalcular_contadores(pid: str, estado_base: Dict[str, Any]) -> Dict[str, Any]:
    """Actualiza los contadores de pedidos con el estado vivo de la tabla pedidos."""
    pedidos = db.listar("pedidos", pid)
    ordenes = db.listar("ordenes", pid)
    reclamos = db.listar("reclamos", pid)
    casos = db.listar("casos", pid)
    contadores = dict(estado_base.get("contadores") or {})
    if casos:
        contadores["casos_piratas"] = sum(1 for c in casos if c.get("clasificacion") == "pirata")
        contadores["casos_descartados"] = sum(1 for c in casos if c.get("clasificacion") != "pirata")
    contadores["pedidos_pendientes"] = sum(1 for p in pedidos if p.get("estado") == "pendiente")
    contadores["pedidos_aprobados"] = sum(1 for p in pedidos if p.get("estado") == "aprobado")
    contadores["pedidos_rechazados"] = sum(1 for p in pedidos if p.get("estado") == "rechazado")
    if ordenes:
        contadores["ordenes_activas"] = sum(1 for o in ordenes if o.get("estado") in ESTADOS_ORDEN_ACTIVA)
        contadores["ordenes_fallidas"] = sum(1 for o in ordenes if o.get("estado") == "fallida")
    if reclamos:
        contadores["reclamos_pendientes"] = sum(1 for r in reclamos if r.get("estado") == "pendiente")
    res = dict(estado_base)
    res["contadores"] = contadores
    return res


@app.get("/api/estado")
def api_estado(partido_id: Optional[str] = None):
    pid = _partido_o_defecto(partido_id)
    est = db.estado_partido(pid)
    if est is None:
        return {
            "partido_id": pid,
            "minuto_actual": 0.0,
            "fin_min": 105.0,
            "finalizado": False,
            "jueces_de_turno": ["jueza-laura-ficticia"],
            "proximo_cambio_turno_min": 50.0,
            "simulador_ok": False,
            "turno_ratificado": True,
            "contadores": {
                "casos_piratas": 0,
                "casos_descartados": 0,
                "pedidos_pendientes": 0,
                "pedidos_aprobados": 0,
                "pedidos_rechazados": 0,
                "ordenes_activas": 0,
                "ordenes_fallidas": 0,
                "reclamos_pendientes": 0,
            },
        }
    return _recalcular_contadores(pid, est)


@app.get("/api/pedidos")
def api_pedidos(estado: Optional[str] = None, partido_id: Optional[str] = None):
    pid = _partido_o_defecto(partido_id)
    pedidos = db.listar("pedidos", pid, estado=estado) if estado else db.listar("pedidos", pid)
    expedientes_cache: Dict[str, Optional[Dict[str, Any]]] = {}
    resultado: List[Dict[str, Any]] = []
    for p in pedidos:
        item = dict(p)
        if "resumen" not in item or not item["resumen"]:
            eid = item.get("expediente_id", "")
            if eid not in expedientes_cache:
                expedientes_cache[eid] = db.obtener("expedientes", pid, eid)
            exp = expedientes_cache[eid]
            if exp and "caso" in exp:
                item["resumen"] = _resumen_de_caso(exp["caso"])
        resultado.append(item)
    return {"pedidos": resultado}


@app.get("/api/expedientes/{expediente_id}")
def api_expediente(expediente_id: str, partido_id: Optional[str] = None):
    pid = _partido_o_defecto(partido_id)
    exp = db.obtener("expedientes", pid, expediente_id)
    if exp is None:
        raise HTTPException(status_code=404, detail=f"No existe el expediente {expediente_id}")
    return exp


def _procesar_decision_pedidos(cuerpo: Dict[str, Any], nuevo_estado: str, partido_id: Optional[str] = None) -> Dict[str, Any]:
    pid = _partido_o_defecto(partido_id)
    pedido_ids = cuerpo.get("pedido_ids")
    juez_id = cuerpo.get("juez_id")
    if not isinstance(pedido_ids, list) or not juez_id:
        raise HTTPException(status_code=400, detail="Faltan pedido_ids o juez_id")

    juzgado_id = _JUZGADO_DE_JUEZ.get(juez_id)
    if juzgado_id is None:
        raise HTTPException(status_code=400, detail="Juez desconocido")

    motivo: Optional[str] = None
    if nuevo_estado == "rechazado":
        motivo = (cuerpo.get("motivo") or "").strip()
        if not motivo:
            raise HTTPException(status_code=400, detail="Rechazar requiere un motivo")

    est_partido = db.estado_partido(pid)
    if not est_partido or juez_id not in est_partido.get("jueces_de_turno", []):
        minuto_err = round(float(est_partido["minuto_actual"]), 2) if est_partido else 0.0
        raise HTTPException(status_code=409, detail=f"{juez_id} no está de turno en el minuto {minuto_err}")

    minuto_actual = round(float(est_partido["minuto_actual"]), 2)

    decididos: List[str] = []
    errores: List[Dict[str, str]] = []

    for req_pid in pedido_ids:
        actual = db.obtener("pedidos", pid, req_pid)
        if actual is None:
            errores.append({"pedido_id": req_pid, "error": "No existe el pedido"})
            continue
        if actual.get("estado") != "pendiente":
            errores.append({"pedido_id": req_pid, "error": f"El pedido ya está {actual.get('estado')}"})
            continue
        ok = db.decidir_pedido(
            partido_id=pid,
            pedido_id=req_pid,
            estado=nuevo_estado,
            juez_id=juez_id,
            juzgado_id=juzgado_id,
            decidido_min=minuto_actual,
            motivo=motivo,
        )
        if ok:
            decididos.append(req_pid)
        else:
            errores.append({"pedido_id": req_pid, "error": "El pedido ya fue decidido"})

    clave_lista = "aprobados" if nuevo_estado == "aprobado" else "rechazados"
    return {clave_lista: decididos, "errores": errores, "decidido_min": minuto_actual}


@app.post("/api/pin/verificar", dependencies=[Depends(pin_juez)])
def verificar_pin():
    """La pantalla del juez valida el PIN al entrar, no recién al firmar."""
    return {"ok": True}


@app.post("/api/pedidos/aprobar", dependencies=[Depends(pin_juez)])
def api_aprobar(cuerpo: Dict[str, Any], partido_id: Optional[str] = None):
    return _procesar_decision_pedidos(cuerpo, "aprobado", partido_id)


@app.post("/api/pedidos/rechazar", dependencies=[Depends(pin_juez)])
def api_rechazar(cuerpo: Dict[str, Any], partido_id: Optional[str] = None):
    return _procesar_decision_pedidos(cuerpo, "rechazado", partido_id)


@app.get("/api/ordenes")
def api_ordenes(partido_id: Optional[str] = None):
    pid = _partido_o_defecto(partido_id)
    return {"ordenes": db.listar("ordenes", pid)}


@app.get("/api/auditoria")
def api_auditoria(partido_id: Optional[str] = None):
    pid = _partido_o_defecto(partido_id)
    return {"eventos": db.auditoria(pid)}


@app.get("/api/reclamos")
def api_reclamos(partido_id: Optional[str] = None):
    pid = _partido_o_defecto(partido_id)
    return {"reclamos": db.listar("reclamos", pid)}


@app.post("/api/turno/asumir", dependencies=[Depends(pin_juez)])
def api_asumir_turno(cuerpo: Dict[str, Any], partido_id: Optional[str] = None):
    pid = _partido_o_defecto(partido_id)
    juez_id = cuerpo.get("juez_id")
    if not juez_id:
        raise HTTPException(status_code=400, detail="Falta juez_id")
    if _JUZGADO_DE_JUEZ.get(juez_id) is None:
        raise HTTPException(status_code=400, detail="Juez desconocido")

    est = db.estado_partido(pid)
    minuto_actual = round(float(est["minuto_actual"]), 2) if est else 0.0
    if not est or juez_id not in est.get("jueces_de_turno", []):
        raise HTTPException(status_code=409, detail=f"{juez_id} no está de turno en el minuto {minuto_actual}")

    db.crear_solicitud(pid, "asumir_turno", {"juez_id": juez_id, "decidido_min": minuto_actual})

    ordenes = db.listar("ordenes", pid)
    vigentes = [o["orden_id"] for o in ordenes if o.get("estado") in ESTADOS_ORDEN_ACTIVA]
    return {"juez_id": juez_id, "ratificadas": vigentes, "decidido_min": minuto_actual}


@app.post("/api/reclamos/levantar", dependencies=[Depends(pin_juez)])
def api_levantar_reclamo(cuerpo: Dict[str, Any], partido_id: Optional[str] = None):
    pid = _partido_o_defecto(partido_id)
    reclamo_id = cuerpo.get("reclamo_id")
    juez_id = cuerpo.get("juez_id")
    motivo = (cuerpo.get("motivo") or "").strip()
    reemplazar = bool(cuerpo.get("reemplazar", True))

    if not reclamo_id or not juez_id or not motivo:
        raise HTTPException(status_code=400, detail="Faltan reclamo_id, juez_id o motivo")
    if _JUZGADO_DE_JUEZ.get(juez_id) is None:
        raise HTTPException(status_code=400, detail="Juez desconocido")

    reclamo = db.obtener("reclamos", pid, reclamo_id)
    if reclamo is None:
        raise HTTPException(status_code=404, detail=f"No existe el reclamo {reclamo_id}")

    est = db.estado_partido(pid)
    minuto_actual = round(float(est["minuto_actual"]), 2) if est else 0.0
    if not est or juez_id not in est.get("jueces_de_turno", []):
        raise HTTPException(status_code=409, detail=f"{juez_id} no está de turno en el minuto {minuto_actual}")

    db.crear_solicitud(pid, "levantar", {
        "reclamo_id": reclamo_id,
        "juez_id": juez_id,
        "motivo": motivo,
        "reemplazar": reemplazar,
        "decidido_min": minuto_actual,
    })

    return {
        "reclamo_id": reclamo_id,
        "estado": "levantado",
        "ordenes_levantadas": reclamo.get("ordenes_levantadas", []),
        "errores": [],
        "pedido_reemplazo_id": reclamo.get("pedido_reemplazo_id"),
    }


@app.get("/api/publico")
def api_publico(partido_id: Optional[str] = None):
    pid = _partido_o_defecto(partido_id)
    ordenes = db.listar("ordenes", pid)
    entradas = [
        {
            "objetivo": o["objetivo"],
            "tipo": o["tipo"],
            "proveedor_id": o["proveedor_id"],
            "desde_min": o.get("aplicada_min"),
            "hasta_min": o.get("finalizada_min") or o["vence_min"],
            "juzgado_id": o["juzgado_id"],
            "juez_id": o["juez_id"],
            "juzgado_nombre": _NOMBRE_JUZGADO.get(o["juzgado_id"], o["juzgado_id"]),
            "juez_nombre": _NOMBRE_JUEZ.get(o["juez_id"], o["juez_id"]),
            "estado": o["estado"],
            "expediente_id": o["expediente_id"],
        }
        for o in ordenes
        if o.get("aplicada_min") is not None
    ]
    return {"entradas": entradas}


@app.get("/")
def raiz():
    return RedirectResponse("/juez/")


if WEB_DIR.exists():
    app.mount("/juez", StaticFiles(directory=str(WEB_DIR), html=True), name="juez")
