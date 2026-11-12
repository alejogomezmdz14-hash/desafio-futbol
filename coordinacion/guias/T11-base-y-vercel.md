# Guía T11 — Base de datos y deploy en Vercel

Para: **Selene** (y su agente). Escrita por Alejo el 2026-11-11.
Leé antes las decisiones 15 a 24 (`coordinacion/decisiones.md`) y `coordinacion/contratos.md` §5 y §10. Si esta guía y los contratos difieren, mandan los contratos.

## Qué entregás

1. Una **base Postgres (Neon)** conectada al proyecto de Vercel.
2. **`plataforma/db/`**: la capa de datos que usa todo el equipo. Funciona con Postgres o con SQLite según `DATABASE_URL`.
3. **`plataforma/api/app.py`**: la app FastAPI con la API de contratos §5, desplegada en Vercel.
4. Una **semilla** con datos de ejemplo, para que la URL pública muestre algo desde hoy.

Orden recomendado: pasos 1 a 4 de abajo hoy a la tarde (deploy vacío con la semilla), y después la API completa.

---

## Paso 1 — Proyecto en Vercel

Requisito: Vercel CLI 48.1.8 o más nueva (`vercel --version`; si no, `npm i -g vercel`).

```bash
cd desafio-futbol
vercel login
vercel link          # crear proyecto nuevo: desafio-futbol
```

- **Cuenta:** el proyecto vive en **tu** cuenta de Vercel. El plan Hobby no admite miembros de equipo, así que vos sos la dueña del deploy. Conectá el repo de GitHub (Settings → Git) para que cada push a `main` redespliegue solo.
- `vercel link` crea la carpeta `.vercel/`. Ya está en el `.gitignore`: no la subas.

## Paso 2 — La base

```bash
vercel integration add neon
```

(O desde el dashboard: Storage → Create Database → Neon, plan gratis, y conectala al proyecto.)

- **Región:** si Neon ofrece São Paulo (`aws-sa-east-1`), elegila y fijá la función en `gru1` (paso 5). Si no, `aws-us-east-1` con `iad1`. **La base y la función van en la misma región.**
- Vercel carga solo `DATABASE_URL` y otras `POSTGRES_*` en producción, preview y desarrollo.
- Usá la URL **pooled** (el host tiene `-pooler`). Las funciones abren muchas conexiones cortas, y sin pooler Neon se queda sin conexiones.

## Paso 3 — Variables

```bash
vercel env add JUEZ_PIN            # un número de 4 a 6 dígitos; elegilo vos
vercel env pull .env.local         # trae DATABASE_URL y JUEZ_PIN a tu máquina
```

- `.env` y `.env.*` están en el `.gitignore`. **Nunca** pegues la `DATABASE_URL` en el repo, en el buzón ni en un mensaje del grupo.
- Para pasársela a otro integrante (quien maneje el Sandbox o corra el motor en la notebook): por privado, o mejor, que cada uno haga `vercel env pull` si le das acceso.

## Paso 4 — Archivos de configuración (en la raíz del repo)

`pyproject.toml`:
```toml
[project]
name = "desafio-futbol-plataforma"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.117",
    "psycopg[binary]>=3.2",
    "httpx>=0.27",
]

[tool.vercel]
entrypoint = "plataforma.api.app:app"
```

`vercel.json`:
```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "regions": ["gru1"]
}
```
(Usá `iad1` si la base quedó en us-east-1.)

- El simulador, el verificador y `datos/` de la organización quedan en el repo, pero la web no los usa. **La web nunca lee `datos/juzgados.json`** (ahí están las claves de firma).

## Paso 5 — Esquema (`plataforma/db/esquema.sql`)

Tiene que andar igual en Postgres y en SQLite. En SQLite, `JSONB` se guarda como texto, y el código convierte con `json.dumps` y `json.loads`.

```sql
-- Estado vivo del partido: lo escribe el motor en cada ciclo (~1 s), lo lee la web.
CREATE TABLE IF NOT EXISTS partidos (
  partido_id     TEXT PRIMARY KEY,
  datos          JSONB NOT NULL,        -- la forma de GET /api/estado (contratos §5)
  actualizado_ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS casos (
  partido_id TEXT NOT NULL, caso_id TEXT NOT NULL,
  clasificacion TEXT, datos JSONB NOT NULL,
  PRIMARY KEY (partido_id, caso_id)
);

CREATE TABLE IF NOT EXISTS expedientes (
  partido_id TEXT NOT NULL, expediente_id TEXT NOT NULL,
  hash TEXT NOT NULL, datos JSONB NOT NULL,
  PRIMARY KEY (partido_id, expediente_id)
);

-- La decisión del juez va en columnas propias: la web solo toca esas.
CREATE TABLE IF NOT EXISTS pedidos (
  partido_id TEXT NOT NULL, pedido_id TEXT NOT NULL,
  estado TEXT NOT NULL DEFAULT 'pendiente',   -- pendiente | aprobado | rechazado
  juez_id TEXT, juzgado_id TEXT, decidido_min REAL, motivo_rechazo TEXT,
  despachado BOOLEAN NOT NULL DEFAULT FALSE,  -- lo pone el motor al tomarlo
  datos JSONB NOT NULL,                       -- el resto del Pedido (contratos §4)
  PRIMARY KEY (partido_id, pedido_id)
);

CREATE TABLE IF NOT EXISTS ordenes (
  partido_id TEXT NOT NULL, orden_id TEXT NOT NULL,
  pedido_id TEXT, proveedor_id TEXT, estado TEXT,
  datos JSONB NOT NULL,
  PRIMARY KEY (partido_id, orden_id)
);

CREATE TABLE IF NOT EXISTS reclamos (
  partido_id TEXT NOT NULL, reclamo_id TEXT NOT NULL,
  estado TEXT, datos JSONB NOT NULL,
  PRIMARY KEY (partido_id, reclamo_id)
);

-- Pedidos de la web al motor que no son aprobar o rechazar: asumir turno y levantar por reclamo.
CREATE TABLE IF NOT EXISTS solicitudes (
  partido_id TEXT NOT NULL, solicitud_id TEXT NOT NULL,
  tipo TEXT NOT NULL,                  -- asumir_turno | levantar
  datos JSONB NOT NULL,                -- el body del POST
  creada_ts TEXT NOT NULL,
  resultado JSONB,                     -- lo completa el motor; NULL = pendiente
  PRIMARY KEY (partido_id, solicitud_id)
);

-- Solo el motor escribe acá. La cadena de hashes la calcula evidencia (T03).
CREATE TABLE IF NOT EXISTS auditoria (
  partido_id TEXT NOT NULL, seq INTEGER NOT NULL,
  hash TEXT NOT NULL, hash_prev TEXT NOT NULL,
  datos JSONB NOT NULL,                -- el EventoAuditoria completo (contratos §7)
  PRIMARY KEY (partido_id, seq)
);

-- Salida de evaluacion/verificar.py de los partidos de demo (T12).
CREATE TABLE IF NOT EXISTS verificaciones (
  partido_id TEXT PRIMARY KEY, salida TEXT NOT NULL, creada_ts TEXT NOT NULL
);
```

## Paso 6 — La capa de datos (`plataforma/db/__init__.py`)

Es una sola puerta para todo el equipo. **Estas son las funciones que los demás van a llamar**: mantené los nombres, y si cambiás alguno, avisá en el buzón.

```python
def conectar():                     # lee DATABASE_URL; postgres:// → psycopg, sqlite:/// → sqlite3
def crear_esquema():                # corre esquema.sql (idempotente)

# Motor (T05) y piezas que escriben
def guardar(tabla, partido_id, id_, datos, **columnas):   # upsert por (partido_id, id)
def guardar_estado_partido(partido_id, estado_api):       # upsert en partidos
def agregar_auditoria(partido_id, evento):                # INSERT; falla si el seq ya existe
def ultimo_evento_auditoria(partido_id):                  # para encadenar el próximo hash
def pedidos_para_despachar(partido_id):                   # aprobados y despachado = FALSE
def marcar_despachado(partido_id, pedido_id):
def solicitudes_pendientes(partido_id):                   # resultado IS NULL
def resolver_solicitud(partido_id, solicitud_id, resultado)

# Web (T11, T04, T07) que lee
def obtener(tabla, partido_id, id_)                       # dict o None
def listar(tabla, partido_id, **filtros)                  # lista de dicts
def estado_partido(partido_id)
def auditoria(partido_id)                                 # en orden de seq
def partido_actual()                                      # el de actualizado_ts más reciente

# Web que decide (solo estas escriben desde Vercel)
def decidir_pedido(partido_id, pedido_id, estado, juez_id, juzgado_id, decidido_min, motivo=None) -> bool
def crear_solicitud(partido_id, tipo, datos) -> str
```

Reglas:
- **Placeholders:** psycopg usa `%s` y sqlite3 usa `?`. Resolvelo en una función interna (`_q(sql)`), no en cada consulta.
- **Una conexión por request** en la web: abrir, usar y cerrar. No guardes la conexión en una variable global. En Vercel las instancias se reciclan.
- **Aprobar es atómico:** en `decidir_pedido`, primero `UPDATE pedidos SET estado=..., juez_id=..., ... WHERE partido_id=... AND pedido_id=... AND estado='pendiente'`, y después mirás `rowcount`. Si da 0, ya estaba decidido: va a `errores`. Así, dos toques del juez no aprueban dos veces.
- **Al devolver un pedido**, combiná `datos` con las columnas de la decisión: `{**datos, "estado": ..., "juez_id": ..., ...}`. La forma sale igual que en contratos §4.
- **Nada de claves, firmas completas ni `contenido_b64`** en ninguna tabla.

## Paso 7 — La API (`plataforma/api/app.py`)

Las rutas son las de contratos §5. Cómo resolver cada una con la base:

| Ruta | Cómo |
|---|---|
| `GET /api/estado` | `estado_partido(partido_actual())`. Si el motor no escribió hace más de 5 s, `simulador_ok: false`. |
| `GET /api/pedidos?estado=` | `listar("pedidos", ...)` + `resumen` armado desde el caso del expediente |
| `GET /api/expedientes/{id}` | `obtener("expedientes", ...)` |
| `POST /api/pedidos/aprobar` / `rechazar` | PIN → validar que `juez_id` está en `jueces_de_turno` de `partidos` → `decidir_pedido` por cada id → `decidido_min` = `minuto_actual` de `partidos` |
| `GET /api/ordenes`, `/api/reclamos`, `/api/auditoria` | `listar(...)` / `auditoria(...)` |
| `POST /api/turno/asumir` | PIN → `crear_solicitud("asumir_turno", body)`. Responde con lo que haya; el motor la resuelve en ~1 s. |
| `POST /api/reclamos/levantar` | PIN → `crear_solicitud("levantar", body)` |
| `GET /api/publico` | lo arma T07 leyendo `pedidos` y `ordenes`. Mientras tanto, devolvé `{"entradas": []}`. |

**El PIN** va como dependencia de FastAPI en las rutas que deciden:
```python
import hmac, os
from fastapi import Header, HTTPException

def pin_juez(x_juez_pin: str | None = Header(default=None)):
    esperado = os.environ.get("JUEZ_PIN", "")
    if not esperado or not x_juez_pin or not hmac.compare_digest(x_juez_pin, esperado):
        raise HTTPException(status_code=401, detail={"error": "PIN de juez inválido"})
```

**La web del juez (T04, de Alejo)** vive en `plataforma/web/`. Montala así:
```python
from fastapi.staticfiles import StaticFiles
app.mount("/juez", StaticFiles(directory="plataforma/web", html=True), name="juez")
```
Y `GET /` redirige a `/juez/`. Vercel sirve los archivos montados así desde su CDN.

## Paso 8 — Semilla (`python -m plataforma.db.semilla`)

Carga los `EJEMPLO_*` de `plataforma/contratos.py` con `partido_id = "demo"`: un estado de partido, un caso, un expediente, dos pedidos pendientes, órdenes y una auditoría corta. Sirve para que hoy mismo la URL pública muestre algo y Alejo pruebe la pantalla del juez sin el motor.

## Paso 9 — Probar

```bash
# Local con SQLite, sin internet
DATABASE_URL=sqlite:///salida/plataforma.db JUEZ_PIN=1234 PYTHONUTF8=1 python -m plataforma.db.semilla
DATABASE_URL=sqlite:///salida/plataforma.db JUEZ_PIN=1234 uvicorn plataforma.api.app:app --reload

# Local contra Neon (lee .env.local)
vercel dev

# Chequeos rápidos
curl http://localhost:8000/api/estado
curl -X POST http://localhost:8000/api/pedidos/aprobar -H "Content-Type: application/json" \
     -H "X-Juez-Pin: 1234" -d '{"pedido_ids":["P-001"],"juez_id":"jueza-laura-ficticia"}'
```

En Windows, `PYTHONUTF8=1` siempre: si no, falla cualquier cosa que imprima acentos o `≈`.

## Paso 10 — Deploy

```bash
vercel             # preview: una URL para probar
vercel --prod      # producción: la URL que va al pitch y al README
```
Con el repo conectado, cada push a `main` despliega solo. **Redeploys chicos y seguidos.** Si un push rompe producción: `vercel rollback`.

## Paso 11 — Avisos al terminar cada parte

- **A `todos`:** la URL pública y cómo apuntar el motor a la base (`DATABASE_URL` + `python -m plataforma.motor`).
- **A `alejo` (T04):** que la semilla está cargada, la URL de `/juez/` y el PIN de demo (por privado, no por el buzón).
- **A `rocio` (T03):** que la auditoría se guarda con `agregar_auditoria` / `ultimo_evento_auditoria`. Ella calcula el hash y vos lo guardás.
- **Para T12 (Sandbox):** cómo le llega `DATABASE_URL` al Sandbox (por `env` al crearlo, desde la propia app de Vercel) y dónde guardar la salida del verificador (`verificaciones`).

## Errores típicos

- **Estado en memoria en la web:** en Vercel cada request puede caer en otra instancia. Todo sale de la base.
- **URL sin pooler:** errores de "too many connections" en el medio de la demo.
- **Base y función en regiones distintas:** cada consulta tarda 150 ms más y el celular del juez se siente lento.
- **Commitear `.env.local` o `.vercel/`:** ya están en el `.gitignore`. Si aparecen en `git status`, algo anda mal.
- **Cambiar un nombre de columna o de función sin avisar:** rompe el motor de otro. Avisá en el buzón siempre.

## Terminada cuando

La URL pública de Vercel muestra los pedidos de la semilla, aprobar uno con el PIN cambia su estado en Neon, y lo mismo funciona en local con SQLite.
