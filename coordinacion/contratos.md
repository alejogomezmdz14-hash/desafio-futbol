# Contratos entre piezas — v1.5

> **Versión v1 (cerrada por T00, 2026-11-11).** Reemplaza al borrador v0.
> La versión en código, con TypedDict, constantes y ejemplos coherentes, está en `plataforma/contratos.py`.
> Cualquier cambio se avisa con un mensaje a `todos` y sube la versión (v1 → v2).
> Fuente de verdad del lado del simulador: `README.md`, `simulador/servidor.py` y `evaluacion/verificar.py`. Si este documento y el simulador no coinciden, manda el simulador: avisen en el buzón.

## Cambios v1.4 → v1.5
- **`sitio_de(host)` usa una lista de sufijos públicos** (`SUFIJOS_PUBLICOS` en `contratos.py`, un subconjunto de la Public Suffix List). Ejemplos: `www.diario.com.ar` → `diario.com.ar` (antes `com.ar`) y `tienda.vercel.app` → `tienda.vercel.app`. Para los `.test` y `.example` del simulador no cambia nada.
- **Cerebro:** un dominio autorizado de un licenciatario nunca se clasifica `pirata`, venga con la marca que venga. Marcas y hosts se comparan sin importar mayúsculas ni espacios. Si el DNS pasivo falla o no trae dominios, se va a `dominio`.

## Cambios v1.3 → v1.4 (aditivo)
- **API de T01 definida** (§2, al final): `Cerebro(partido, consultar_dns).procesar(deteccion) -> (caso, es_nuevo)`. Implementada en `plataforma/analisis/`.
- `plataforma/contratos.py` se pone al día con v1.1: `EstadoMotor.turno_ratificado`, `AsumirTurnoReq` y `AsumirTurnoResp`, y `EJEMPLO_API_ASUMIR_TURNO_REQ` y `_RESP`. `VERSION_CONTRATOS = "v1.4"`.

## Cambios v1.2 → v1.3 (aditivo)

- **§10 suma tres tablas:** `partidos` (el motor escribe ahí el estado vivo en cada ciclo y la web lo lee para `/api/estado` y para validar el turno), `solicitudes` (la web deja ahí "asumir turno" y "levantar"; el motor las resuelve) y `verificaciones` (salida de `verificar.py` en los partidos de demo).
- `pedidos` suma la columna `despachado` (la pone el motor al tomar un aprobado).
- Esquema SQL completo y funciones de `plataforma/db/`: `coordinacion/guias/T11-base-y-vercel.md`.

## Cambios v1.1 → v1.2 (aditivo: no cambia ninguna forma)

- **Dónde vive el estado.** La API de §5 ya no la sirve el proceso del motor: la sirve la web en Vercel, que lee y escribe la base Postgres (decisiones 15 a 21). Las rutas, los requests y los responses son los mismos.
- **Base de datos (§10, nuevo).** Una tabla por contrato, con el dict completo en JSONB. Todas las filas llevan `partido_id`.
- **`POST /api/pedidos/aprobar`, `/api/pedidos/rechazar`, `/api/turno/asumir`, `/api/reclamos/levantar` y `/api/demo/iniciar`** piden `Authorization: Bearer <token>`. El token sale de `POST /api/login` `{"usuario", "password"}` (login simple de la coordinación, decisión 43; `GET /api/sesion` dice si sigue vigente). Sin sesión o con una vencida: 401 `{"error"}`. Esto reemplaza al header `X-Juez-Pin`.
- **Aprobar ya no despacha en el acto.** Deja el pedido en `aprobado` y el motor lo despacha en su próximo ciclo (~1 s). La auditoría de la aprobación la escribe el motor.

## Cambios v0 → v1

- **Orden al simulador corregida.** El payload del `POST /proveedores/<id>/ordenes` lleva exactamente `orden_id, expediente_id, tipo, objetivo, vence_min, juzgado_id, juez_id, firma`. Se agregaron `expediente_id`, `juzgado_id`, `juez_id` y `firma`; **`pedido_id` sale del payload** (queda solo en el seguimiento interno, §6).
- **Firmas documentadas.** Orden: HMAC-SHA256 hex sobre `orden_id|tipo|objetivo|vence_min|juez_id`. Levantamiento: sobre `LEVANTAR|orden_id|juez_id`. Cada envío, **incluido cada reintento**, se firma con el juez de turno en el minuto del envío.
- **`vence_min` es `int`** (no float, no bool) y tiene que ser mayor al minuto actual. En el MVP vale `int(fin_min)` para IP y para dominio.
- **Estados reales de la orden:** `recibida → aplicada → vencida | levantada`, más `fallida` (se reenvía con `orden_id` nuevo). Internamente sumamos `rechazada` (el POST volvió 4xx). El seguimiento interno suma `recibida_min`, `finalizada_min`, `motivo`, `consultar` y `reemplaza_a` (§6).
- **Formas del simulador documentadas** con sus nombres reales (detección, estado, partido, DNS pasivo, juzgados, proveedores, reclamos, respuestas y errores) y el **registro `salida/registro.jsonl` que lee el verificador**, separado de nuestra **auditoría interna** (son dos cosas distintas).
- **Hashes precisos:** capturas = SHA-256 del **binario decodificado** de `contenido_b64` (no del texto base64); expediente y auditoría con JSON canónico definido.
- **Nuevas interfaces:** reclamos (T06: verificación, correlación sin `orden_id`, levantamiento firmado y reemplazo) y registro público (T07). La API del motor suma `GET /api/reclamos`, `POST /api/reclamos/levantar` y `GET /api/publico`.
- **Agregados chicos:** `Caso` suma `sitio` y `marca_origen`; `Expediente` suma `partido_id`, `promocion`, `vence_propuesto_min`, `creado_ts` y detalle de capturas; `Pedido` suma `origen`, `creado_min` y `juzgado_id`.

---

## 0. Convención general

- Todo el código nuestro va en el paquete `plataforma/`. Los datos viajan como `dict` (JSON) con las claves de este documento.
- **Minutos de partido** desde el minuto 0, como en el simulador. Son `float`, **salvo `vence_min`, que es `int`**.
- En los contratos internos **todas las claves están siempre**; si no aplica, valen `None`/`null`. (En las formas del simulador, algunas claves aparecen recién cuando corresponde: lo marcamos.)
- `ts` = reloj real de la máquina, ISO 8601 con zona (`2026-11-11T18:02:36-03:00`). Con el simulador acelerado no coincide con `inicio_iso + min`, y está bien.
- **Cuatro mundos que no hay que mezclar:**

| Mundo | Quién lo define | Dónde está | Sección |
|---|---|---|---|
| API del simulador (entrada/salida hacia afuera) | La organización | `http://<sim>/...` | §1 |
| Registro del simulador | El simulador lo escribe | `salida/registro.jsonl` (lo lee `evaluacion/verificar.py`) | §1.11 |
| Contratos internos (Caso, Expediente, Pedido, Orden, Reclamo, Entrada pública) y API del motor | Nosotros | `plataforma/` | §2–§9 |
| Auditoría interna con cadena de hashes | Nosotros (T03) | archivo propio de `plataforma/` | §7 |

- Ejemplos: solo dominios `.test`/`.example`, IPs de documentación (`203.0.113.x`, `198.51.100.x`, `192.0.2.x`), jueces ficticios. Las claves de demo existen en `datos/juzgados.json`; **no se copian** a ningún otro archivo.

---

## 1. Formas del simulador

Ejemplos completos en `plataforma/contratos.py` (`EJEMPLO_SIM_*`, `EJEMPLO_DETECCION`, `EJEMPLO_ORDEN_PAYLOAD`, `EJEMPLO_LEVANTAR_REQ`, `EJEMPLO_REGISTRO`).

### 1.1 Detección — `GET /detecciones?desde=<min>`
```json
{"minuto_actual": 2.013, "detecciones": [{
  "id": "D-0001", "minuto": 2.0,
  "pagina": "https://pelotaya.test/en-vivo",
  "stream_url": "https://s1.pelotaya.test/hls/en-vivo/index.m3u8",
  "host_stream": "s1.pelotaya.test", "ip_servidor": "203.0.113.10", "asn": 64600,
  "marca_de_agua_extraida": "LP26-PRA-OFI-S048211",
  "captura": {"capturada_min": 2.0, "formato": "mpegts", "duracion_seg": 6, "contenido_b64": "R78w..."},
  "promocion": [{"red": "x", "url": "https://x.example/futbolya_ok/status/1001", "minuto": 1.0}]
}]}
```
- Devuelve las detecciones con `desde < minuto <= minuto_actual`. **Usar `minuto_actual` (redondeado a 3) como próximo `desde`**; la primera vez, `desde=-1`.
- Las detecciones se repiten (varias por stream). `marca_de_agua_extraida` puede no venir o venir vacía en el escenario final → `sin_marca`.

### 1.2 Estado — `GET /estado`
```json
{"partido": "practica-01", "minuto_actual": 2.6, "fin_min": 105.0, "finalizado": false,
 "acelerar": 6.0, "jueces_de_turno": ["jueza-laura-ficticia"]}
```
`minuto_actual` redondeado a 2. `fin_min` acá es float; en `/partido` es int.

### 1.3 Partido — `GET /partido`
```json
{"id": "practica-01", "nombre": "...", "titular_derechos": "Liga Profesional Ficticia",
 "inicio_iso": "2026-11-11T18:00:00-03:00", "fin_min": 105,
 "marcas_de_agua_validas": [{"prefijo": "LP26-PRA-OFI", "origen": "Señal oficial del titular (plataforma propia)"},
                            {"prefijo": "LP26-PRA-LIC-NORTE", "origen": "Licenciatario autorizado: Canal Norte TV (ficticio)"}],
 "licenciatarios": [{"nombre": "Canal Norte TV (ficticio)", "prefijo_marca": "LP26-PRA-LIC-NORTE",
                     "dominios_autorizados": ["canalnorte.test", "envivo.canalnorte.test"]}]}
```

### 1.4 DNS pasivo
- `GET /dns-pasivo?ip=203.0.113.10` → `{"ip", "asn", "organizacion", "dominios": [...]}`
- `GET /dns-pasivo?dominio=s1.pelotaya.test` → `{"dominio", "ips": [{"ip", "asn", "organizacion"}]}`
- **404** `{"error": ...}` si no hay registros; 400 si no se pasa ninguno.

### 1.5 Juzgados — `GET /juzgados` (sin claves)
```json
{"juzgados": [{"id": "jg-centro-3", "nombre": "...", "jurisdiccion": "...",
               "jueces": [{"id": "jueza-laura-ficticia", "nombre": "Dra. Laura Ficticia"}]}, ...],
 "turnos": [{"juez_id": "jueza-laura-ficticia", "desde_min": -60, "hasta_min": 50},
            {"juez_id": "juez-martin-ejemplo", "desde_min": 50, "hasta_min": 240}],
 "de_turno_ahora": ["jueza-laura-ficticia"]}
```
De turno ⇔ `desde_min <= minuto < hasta_min` (hasta **exclusive**). Las claves (`clave_firma_demo`) están solo en `datos/juzgados.json`; las lee únicamente despacho (T02) y reclamos (T06) para firmar.

### 1.6 Proveedores — `GET /proveedores` (lista; sin `comportamiento`)
```json
[{"id": "aurora", "nombre": "Conectividad Aurora (ficticio)", "tamano": "grande", "clientes": 3800000,
  "capacidades": ["ip", "dominio"], "ordenes": "/proveedores/aurora/ordenes"}, ...]
```
En práctica: `aurora`, `andina`, `cumbre` (ip + dominio; cumbre a veces falla) y `valle` (**solo dominio**). Las demoras y fallas no se publican; se descubren usando la API.

### 1.7 Orden hacia el simulador — `POST /proveedores/<id>/ordenes`
```json
{"orden_id": "ord-c0a1-P-001-aurora-1", "expediente_id": "EXP-2026-000001", "tipo": "ip",
 "objetivo": "203.0.113.10", "vence_min": 105, "juzgado_id": "jg-centro-3",
 "juez_id": "jueza-laura-ficticia", "firma": "<64 hex>"}
```
- Campos **obligatorios y exactos** (`CAMPOS_ORDEN`). No lleva `pedido_id`.
- `tipo`: `ip` | `dominio`, y tiene que estar en `capacidades` del proveedor.
- `objetivo`: la IP (`ip_servidor`) o el `host_stream` si es `dominio`.
- `vence_min`: `int` (no float, no bool), **estrictamente mayor** al minuto actual.
- `orden_id`: único **por proveedor**. Formato nuestro: `ord-{corrida}-{pedido_id}-{proveedor_id}-{intento}`, con `corrida` = 4 hex al azar al arrancar el motor (evita 409 si se reinicia la plataforma con el simulador andando).
- **Firma:** `HMAC-SHA256(clave_firma_demo del juez, "orden_id|tipo|objetivo|vence_min|juez_id")` en hex.
  Ejemplo de texto firmado: `ord-c0a1-P-001-aurora-1|ip|203.0.113.10|105|jueza-laura-ficticia`.
- **Turno:** el simulador **no rechaza** por turno; registra `juez_de_turno` al recibir y el verificador penaliza las firmadas fuera de turno. Como la orden se evalúa al llegar (en el POST), **cada envío y cada reintento se firma con el juez de turno en ese minuto** (`GET /estado` → `jueces_de_turno`). Cambio de turno en práctica: minuto 50 (laura hasta 50 exclusive, martín desde 50). Ver decisión 6.

### 1.8 Respuestas y errores
| Código | Cuándo | Cuerpo |
|---|---|---|
| 202 | Orden aceptada | `{"orden_id", "estado": "recibida", "consultar": "/proveedores/<id>/ordenes/<orden_id>"}` |
| 400 | Faltan campos / cuerpo no es objeto JSON | `{"error": "Faltan campos: ..."}` |
| 403 | Juez inexistente, juez no pertenece al juzgado, firma inválida | `{"error": ...}` |
| 404 | Proveedor u orden inexistente | `{"error": ...}` |
| 409 | `orden_id` repetido en ese proveedor / levantar una orden no activa | `{"error": ...}` |
| 422 | `tipo` inválido o no soportado, `vence_min` no entero o no futuro | `{"error": ...}` |

Una orden rechazada (4xx) **no queda guardada** y el simulador loguea `orden_rechazada`. Cada rechazo suma en contra en el verificador: validar antes de enviar.

**Vista de una orden** — `GET /proveedores/<id>/ordenes/<orden_id>` (o la lista sin `<orden_id>`): los campos del payload **sin `firma`**, más `estado` y `recibida_min`; aparecen `aplicada_min` (si se aplicó), `motivo` (si quedó `fallida`) y `finalizada_min` (si venció o se levantó).

Estados: `recibida` → `aplicada` → `vencida` | `levantada`; o `recibida` → `fallida` (no se reintenta sola: reenviar con `orden_id` nuevo).

### 1.9 Levantar — `POST /proveedores/<id>/ordenes/<orden_id>/levantar`
```json
{"juez_id": "jueza-laura-ficticia", "firma": "<64 hex>", "motivo": "Reclamo R-001 verificado: ..."}
```
- Firma: `HMAC-SHA256(clave del juez, "LEVANTAR|{orden_id}|{juez_id}")`.
- Solo si la orden está `recibida` o `aplicada`; si no, **409**. Responde **200** con la vista de la orden (`estado: "levantada"`, `finalizada_min`).

### 1.10 Reclamos — `GET /reclamos?desde=<min>`
```json
{"minuto_actual": 16.02, "reclamos": [{"id": "R-001", "minuto": 16.0, "dominio": "panaderia-la-espiga.test",
  "proveedor": "andina", "mensaje": "Panadería La Espiga: ..."}]}
```
**No trae `orden_id`** (sí aparece en el log del simulador). Cada proveedor que aplicó la orden problemática genera su propio reclamo. Correlación en §8.

### 1.11 Registro del simulador — `salida/registro.jsonl`
Lo escribe **el simulador**, no nosotros. Una línea JSON por evento: `{"min": <float, 3 decimales>, "evento": "<nombre>", ...}`. Es lo que lee `evaluacion/verificar.py`.

| `evento` | Campos además de `min` y `evento` |
|---|---|
| `simulacion_iniciada` | `escenario`, `acelerar`, `fin_min` |
| `orden_recibida` | `proveedor`, `juez_de_turno`, `orden_id`, `expediente_id`, `tipo`, `objetivo`, `vence_min`, `juzgado_id`, `juez_id` |
| `orden_aplicada` | `proveedor`, `orden_id`, `tipo`, `objetivo` |
| `orden_fallida` | `proveedor`, `orden_id`, `motivo` |
| `orden_vencida` | `proveedor`, `orden_id` |
| `orden_levantada` | `proveedor`, `orden_id`, `juez_id`, `motivo` |
| `orden_rechazada` | `proveedor`, `orden_id` (puede ser `null`), `motivo` |
| `reclamo_emitido` | `orden_id`, `id`, `dominio`, `proveedor`, `mensaje` (el minuto va en `min`) |
| `partido_finalizado` | — |
| `ventana_cerrada` | `ordenes_activas: [{proveedor, orden_id, tipo, objetivo}]` (en `fin_min + 5`) |

Qué mira el verificador: reconstruye cada orden por `(proveedor, orden_id)`; por fase pirata, minutos hasta el primer bloqueo aplicado que afecta (`ip == objetivo` o `host == objetivo`), clientes cubiertos y visibilidad residual; daño colateral (dominios legítimos detrás de un bloqueo aplicado); falsos positivos; **bloqueos por IP activos en `fin_min + GRACIA_MIN` (5)**; reclamos levantados vs. vencidos solos; rechazos por motivo; firmas fuera de turno. Los bloqueos por dominio activos después del partido son **solo informativos**.

---

## 2. Caso — lo produce `plataforma/analisis/` (T01)

Un caso = un stream en un servidor: clave **`(host_stream, ip_servidor)`**. Varias detecciones con el mismo host e IP son el mismo caso. **Mudanza** (mismo sitio, otro host o IP) = **caso nuevo**.

```python
{
  "caso_id": "C-001",
  "host": "s1.pelotaya.test",          # <- host_stream (lo que se bloquea por dominio)
  "ip": "203.0.113.10",                # <- ip_servidor
  "asn": 64600,                        # <- asn
  "organizacion": "Bruma Hosting Dedicado (ficticio)",   # <- dns-pasivo?ip= (None si 404)
  "sitio": "pelotaya.test",            # NUEVO: últimas dos etiquetas del host (sitio_de)
  "pagina": "https://pelotaya.test/en-vivo",
  "deteccion_ids": ["D-0001"],         # <- id de cada detección agrupada
  "primer_minuto": 2.0,
  "marca": "LP26-PRA-OFI-S048211",     # <- marca_de_agua_extraida
  "marca_origen": "Señal oficial del titular (plataforma propia)",   # NUEVO: origen del prefijo que coincidió, o None
  "clasificacion": "pirata",           # pirata | licenciatario_legal | otra_senal | sin_marca
  "motivo_clasificacion": "Marca de agua de la señal oficial del partido (LP26-PRA-OFI) en un dominio no autorizado",
  "dominios_en_ip": ["s1.pelotaya.test", "s1-respaldo.pelotaya.test"],   # <- dns-pasivo?ip= ([] si 404)
  "ip_compartida": False,
  "tipo_recomendado": "ip",            # ip | dominio
  "motivo_tipo": "La IP solo aloja dominios del mismo sitio pirata (pelotaya.test)",
}
```

**Clasificación** (contra `GET /partido`). Una marca coincide con un prefijo si `marca == prefijo` o `marca.startswith(prefijo + "-")`; probar primero el prefijo más largo.
1. Sin marca (`None` o vacía) → `sin_marca`.
2. Coincide con el `prefijo_marca` de un licenciatario: si el host está en sus `dominios_autorizados` (igual, o subdominio de uno) → `licenciatario_legal`; **si no → `pirata`** (retransmite su señal fuera de sus dominios).
3. Coincide con otro prefijo válido (señal oficial) → `pirata`.
4. Cualquier otra marca → `otra_senal`.

Solo los `pirata` van al juez. Los demás se auditan como `caso_descartado`. En práctica son **7 casos piratas**: pelotaya ×3, golazo-cdn ×1, verpartido ×1, tribuna ×2 (ninguno del licenciatario ni de `resumenes-deportivos`).

**Tipo recomendado.** `ip_compartida = True` si algún dominio de `dominios_en_ip` no pertenece al mismo `sitio` que el host (hay sitios legítimos u otros). Si es compartida → `tipo_recomendado = "dominio"`; si no → `"ip"`. Si el DNS pasivo da 404, por precaución `ip_compartida = True` y `"dominio"`.

**API de T01 (v1.4)**, la que llama el motor (T05):
```python
from plataforma.analisis import Cerebro

cerebro = Cerebro(partido, consultar_dns)   # partido = GET /partido
                                            # consultar_dns(ip) -> DnsPorIp | None  (GET /dns-pasivo?ip=, None si 404)
for deteccion in nuevas:                    # GET /detecciones?desde=
    caso, es_nuevo = cerebro.procesar(deteccion)
    if not es_nuevo:
        continue                            # repetición: el caso ya sumó la detección a deteccion_ids
    if caso["clasificacion"] == "pirata":
        ...                                 # expediente (T03) + pedido al juez
    else:
        ...                                 # auditar caso_descartado
cerebro.casos()                             # todos los casos, para guardar o mostrar
```
- El cerebro no hace red. Cachea el DNS por IP: una consulta por IP en todo el partido.
- Los `caso_id` son `C-001`, `C-002`, … en orden de aparición, únicos por instancia de `Cerebro` (una por partido).
- Pruebas: `python -m plataforma.analisis.test_cerebro`. Contra la verdad de práctica da 9 de 9 casos y 7 piratas con el tipo correcto.

---

## 3. Expediente — lo produce `plataforma/evidencia/` (T03)

```python
{
  "expediente_id": "EXP-2026-000001",
  "partido_id": "practica-01",
  "caso": {...},                          # el Caso completo
  "capturas": [{"deteccion_id": "D-0001", "capturada_min": 2.0, "formato": "mpegts",
                "duracion_seg": 6, "bytes": 64,
                "sha256": "77b14ea8874ef8bbbf99cc292fd820a9e8df09fa4d4c00ebaeb9003e6b9bfbe1"}],
  "promocion": [{"red": "x", "url": "https://x.example/futbolya_ok/status/1001", "minuto": 1.0}],  # extra
  "vence_propuesto_min": 105,
  "creado_min": 2.1,
  "creado_ts": "2026-11-11T18:02:06-03:00",
  "hash": "5332df39e30d98c8cb4a6403e382dee9eced62ec89d50e58639eedf49f63cb31",
}
```
- **`capturas[].sha256` = SHA-256 del binario decodificado** de `captura.contenido_b64` (`base64.b64decode(...)`), en hex. **No** se hashea el texto base64. `bytes` = largo de ese binario.
- **JSON canónico:** `json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")`.
- **`hash` = sha256 del JSON canónico del expediente sin el campo `"hash"`**, en hex.
- No se guarda el `contenido_b64` en el expediente (pesa y no aporta: alcanza el hash). Si se quiere exportar la captura, va aparte.
- Funciones de referencia: `sha256_captura`, `hash_expediente`, `json_canonico` en `plataforma/contratos.py`.

---

## 4. Pedido — lo crea el motor (T05) y lo aprueba el juez desde la web (T04)

```python
{
  "pedido_id": "P-001",
  "expediente_id": "EXP-2026-000001",
  "origen": "deteccion",                  # deteccion | reclamo:<reclamo_id> (reemplazo, §8)
  "objetivos": [{"proveedor_id": "aurora", "tipo": "ip",      "objetivo": "203.0.113.10"},
                {"proveedor_id": "andina", "tipo": "ip",      "objetivo": "203.0.113.10"},
                {"proveedor_id": "valle",  "tipo": "dominio", "objetivo": "s1.pelotaya.test"},
                {"proveedor_id": "cumbre", "tipo": "ip",      "objetivo": "203.0.113.10"}],
  "vence_min": 105,
  "creado_min": 2.1,
  "estado": "pendiente",                  # pendiente | aprobado | rechazado
  "juez_id": None, "juzgado_id": None, "decidido_min": None, "motivo_rechazo": None,
}
```
- **`objetivos`: una entrada por proveedor** de `GET /proveedores`, con el tipo que **ese** proveedor acepta: si el recomendado es `ip` y el proveedor no tiene `ip` en `capacidades` (valle), va `dominio` con el `host`. Si el recomendado es `dominio`, va `dominio` para todos.
- **Vencimiento (MVP):** `vence_min = int(fin_min)` (105 en práctica) **para IP y para dominio**. El verificador solo penaliza IP activas después del partido; no hace falta bloqueo DNS permanente para el MVP.
- Al aprobar se llenan `juez_id`, `juzgado_id` (el del juez, según `/juzgados`) y `decidido_min`. Al rechazar, además `motivo_rechazo`.
- Si un objetivo ya tiene una orden activa nuestra en ese proveedor (mismo tipo y objetivo), el motor no la duplica.
- Ejemplos: `EJEMPLO_PEDIDO_PENDIENTE`, `EJEMPLO_PEDIDO` (aprobado).

---

## 5. API del motor (T05 la sirve; T04, T06 y T07 la consumen)

La sirve la web en Vercel (FastAPI), que lee la base (§10); en modo local la sirve el mismo proceso que el motor. JSON en request y response. Errores: `{"error": "..."}` con 400/404/409.

| Método y ruta | Request | Response (ejemplo en `contratos.py`) |
|---|---|---|
| `GET /api/estado` | — | `EJEMPLO_API_ESTADO` |
| `GET /api/pedidos?estado=pendiente` | — | `{"pedidos": [Pedido + "resumen"]}` → `EJEMPLO_API_PEDIDOS` |
| `GET /api/expedientes/{expediente_id}` | — | `Expediente` → `EJEMPLO_EXPEDIENTE` |
| `POST /api/pedidos/aprobar` | `{"pedido_ids": [...], "juez_id": "..."}` | `{"aprobados": [...], "errores": [{"pedido_id", "error"}], "decidido_min"}` |
| `POST /api/pedidos/rechazar` | `{"pedido_ids": [...], "juez_id": "...", "motivo": "..."}` | `{"rechazados": [...], "errores": [...], "decidido_min"}` |
| `GET /api/ordenes` | — | `{"ordenes": [Orden]}` → `EJEMPLO_API_ORDENES` |
| `GET /api/auditoria` | — | `{"eventos": [EventoAuditoria]}` → `EJEMPLO_API_AUDITORIA` |
| `GET /api/reclamos` | — | `{"reclamos": [Reclamo]}` → `EJEMPLO_API_RECLAMOS` |
| `POST /api/reclamos/levantar` | `{"reclamo_id", "juez_id", "motivo", "reemplazar": true}` | `{"reclamo_id", "estado", "ordenes_levantadas", "errores", "pedido_reemplazo_id"}` |
| `GET /api/publico` | — | `{"entradas": [EntradaPublica]}` → `EJEMPLO_API_PUBLICO` |
| `POST /api/turno/asumir` *(v1.1)* | `{"juez_id": "..."}` | `{"juez_id", "ratificadas": [orden_id...], "decidido_min"}`. 409 si `juez_id` no está de turno |

**v1.1 (aditivo, no rompe nada):** `GET /api/estado` suma `"turno_ratificado": true|false`. Cuando cambia el juez de turno queda en `false` hasta que el entrante llama a `POST /api/turno/asumir`. Mientras está en `false`, despacho **no reenvía** órdenes aprobadas por el juez saliente; las deja en espera y las firma el entrante después de ratificar. Ver `diseno.md` §3 y la decisión 12.

`GET /api/estado`:
```json
{"partido_id": "practica-01", "minuto_actual": 3.3, "fin_min": 105.0, "finalizado": false,
 "jueces_de_turno": ["jueza-laura-ficticia"], "proximo_cambio_turno_min": 50.0, "simulador_ok": true,
 "contadores": {"casos_piratas": 1, "casos_descartados": 0, "pedidos_pendientes": 0, "pedidos_aprobados": 1,
                "pedidos_rechazados": 0, "ordenes_activas": 4, "ordenes_fallidas": 0, "reclamos_pendientes": 0}}
```
`GET /api/pedidos` agrega a cada pedido un `"resumen"` para la pantalla del juez: `caso_id, host, ip, organizacion, marca, motivo_clasificacion, ip_compartida, dominios_en_ip, tipo_recomendado, motivo_tipo, primer_minuto`.

Aprobar: `{"pedido_ids": ["P-001"], "juez_id": "jueza-laura-ficticia"}` → `{"aprobados": ["P-001"], "errores": [], "decidido_min": 2.6}`.
- El `juez_id` tiene que estar de turno en ese minuto; si no, el pedido va a `errores` y sigue pendiente.
- Un pedido que no está `pendiente` va a `errores` (aprobar es idempotente por pedido).
- Al aprobar, el motor pasa el pedido a despacho (§6).

---

## 6. Orden — la maneja `plataforma/despacho/` (T02)

Una orden por proveedor y objetivo. Hay **dos formas**:

**a) Payload al simulador** (§1.7, `OrdenPayload`): exactamente los 8 campos de `CAMPOS_ORDEN`. Ejemplo: `EJEMPLO_ORDEN_PAYLOAD`.

**b) Seguimiento interno** (`Orden`), lo que exponemos en `/api/ordenes` y usamos para reintentos, reclamos y registro público:
```python
{"orden_id": "ord-c0a1-P-001-aurora-1", "pedido_id": "P-001", "expediente_id": "EXP-2026-000001",
 "proveedor_id": "aurora", "tipo": "ip", "objetivo": "203.0.113.10", "vence_min": 105,
 "juzgado_id": "jg-centro-3", "juez_id": "jueza-laura-ficticia",   # quien firmó ESTE envío
 "estado": "aplicada",            # recibida | aplicada | vencida | levantada | fallida | rechazada
 "intentos": 1, "reemplaza_a": None,
 "enviada_min": 2.7, "recibida_min": 2.7, "aplicada_min": 3.2, "finalizada_min": None,
 "motivo": None, "consultar": "/proveedores/aurora/ordenes/ord-c0a1-P-001-aurora-1"}
```
- `estado` copia el del simulador (se sigue con `GET` a `consultar`). `rechazada` es nuestro: el POST volvió 4xx; `motivo` = el `error` del simulador.
- **Reintento = orden nueva** con `orden_id` nuevo (`intento` + 1), `intentos` = nº de intento y `reemplaza_a` = `orden_id` anterior. La anterior queda en el historial, no se pisa. Se reintenta ante `fallida` (cumbre) y ante errores de red. Ante `rechazada`, solo si el motivo se corrige (no reenviar a ciegas: cada rechazo cuenta).
- Cada envío se firma con el **juez de turno en el minuto del envío**; por eso `Orden.juez_id` puede diferir de `Pedido.juez_id` en un reintento después del cambio de turno (queda en auditoría).
- No enviar si `vence_min <= minuto actual` (el partido ya terminó).
- Ejemplos: `EJEMPLO_ORDEN` (aplicada), `EJEMPLO_ORDEN_FALLIDA`, `EJEMPLO_ORDEN_REINTENTO`.

---

## 7. Evento de auditoría INTERNA — lo escribe `plataforma/evidencia/` (T03); todos lo llaman

> **No es `salida/registro.jsonl`.** Ese lo escribe el simulador (§1.11). Esto es nuestro registro inalterable, en un archivo propio.

```python
auditar(actor="motor", accion="caso_descartado", datos={...})
# se guarda como una línea JSONL:
{"seq": 3, "min": 2.6, "ts": "2026-11-11T18:02:36-03:00", "actor": "juez:jueza-laura-ficticia",
 "accion": "pedido_aprobado",
 "datos": {"pedido_id": "P-001", "expediente_id": "EXP-2026-000001", "juzgado_id": "jg-centro-3"},
 "hash_prev": "f16dd4b5c1dc188c62bdffa7f0a999b6c358f1aaa521f7fbe484bb55b24ed281",
 "hash": "e9810d6649f17471c2f004708d82e43cebc2ec5a19b4ffa4bbefa354e109618c"}
```
- **`hash = sha256(hash_prev.encode("utf-8") + json_canonico(evento sin "hash"))`** en hex. El evento sin `hash` **incluye** `hash_prev`. Primer evento: `hash_prev = "0" * 64`.
- `seq` empieza en 1 y no tiene huecos. Si se toca un byte de una línea, se rompe la cadena desde ahí.
- `actor`: `motor`, `analisis`, `evidencia`, `despacho`, `reclamos`, `juez:<juez_id>`, `proveedor:<id>`.
- `accion` (lista en `ACCIONES_AUDITORIA`): `caso_creado`, `caso_descartado`, `expediente_creado`, `pedido_creado`, `pedido_aprobado`, `pedido_rechazado`, `orden_enviada`, `orden_rechazada`, `orden_aplicada`, `orden_fallida`, `orden_reenviada`, `orden_vencida`, `orden_levantada`, `reclamo_recibido`, `reclamo_descartado`, `reclamo_levantado`, `motor_iniciado`, `partido_finalizado`. Se pueden sumar; avisar en el buzón.
- En `datos` no van claves ni firmas completas ni `contenido_b64`. Para expedientes va `expediente_hash`.
- Cadena de ejemplo de 4 eventos con hashes reales: `EJEMPLO_AUDITORIA` (verificable con `python -m plataforma.contratos`).

---

## 8. Reclamos — `plataforma/reclamos/` (T06, extra)

**Entrada:** el feed `GET /reclamos?desde=` (§1.10). Se guarda como `Reclamo`:
```python
{"reclamo_id": "R-001", "minuto": 16.0, "dominio": "panaderia-la-espiga.test", "proveedor_id": "andina",
 "mensaje": "...", "estado": "pendiente",          # pendiente | descartado | levantado
 "verificacion": "panaderia-la-espiga.test no es un sitio pirata y comparte la IP 192.0.2.50 con ...",
 "orden_ids": ["ord-c0a1-P-003-andina-1"], "caso_id": "C-003",
 "juez_id": None, "decidido_min": None, "ordenes_levantadas": [], "pedido_reemplazo_id": None}
```
(Escenario hipotético de ejemplo: se bloqueó por IP la IP compartida de `tv.verpartido-hd.test`.)

**Correlación** (el feed no trae `orden_id`): órdenes nuestras con
1. `proveedor_id == reclamo.proveedor`;
2. aplicadas en el minuto del reclamo: `aplicada_min <= minuto` y (`finalizada_min` es `None` o `> minuto`);
3. que afectan al dominio: `tipo == "dominio"` y `objetivo == dominio`, o `tipo == "ip"` y `dominio` está en los `dominios_en_ip` del caso (o en `dns-pasivo?ip=objetivo`).

**Verificación** → `pendiente` si se cumplen las dos; si no, `descartado` (con `verificacion` explicando por qué):
- el dominio reclamante **no es pirata**: no es `host` de un caso `pirata` ni tiene el mismo `sitio` que uno;
- hay al menos una orden nuestra correlacionada (punto anterior).

**Levantamiento** (lo decide el juez desde la web): `POST /api/reclamos/levantar {"reclamo_id", "juez_id", "motivo", "reemplazar"}`.
- Se levantan **todas** nuestras órdenes activas (`recibida`/`aplicada`) con el mismo `tipo` y `objetivo` que la correlacionada, **en todos los proveedores** (los otros proveedores van a reclamar lo mismo). Cada una con `POST .../levantar` firmado `LEVANTAR|orden_id|juez_id` por el juez de turno.
- Si `reemplazar` es `true` y la orden levantada era por IP: se crea un **Pedido nuevo** con `origen: "reclamo:R-001"`, tipo `dominio` y objetivo = `host` del caso pirata para todos los proveedores, ya `aprobado` por ese mismo juez en el mismo acto, y pasa a despacho.
- Si la orden levantada ya era por dominio (bloqueamos un sitio legítimo, p. ej. el licenciatario), no hay reemplazo: `reemplazar: false` y se revisa la clasificación del caso.
- Respuesta: `EJEMPLO_API_LEVANTAR_RESP`. Auditoría: `reclamo_recibido`, `reclamo_descartado` / `reclamo_levantado`, `orden_levantada`, `pedido_creado`.

---

## 9. Registro público de transparencia — `plataforma/transparencia/` (T07, extra)

Una entrada por **(pedido, tipo, objetivo)**, servida por `GET /api/publico`:
```python
{"entrada_id": "P-001/ip/203.0.113.10", "pedido_id": "P-001", "expediente_id": "EXP-2026-000001",
 "partido_id": "practica-01", "tipo": "ip", "objetivo": "203.0.113.10",
 "motivo": "Retransmisión no autorizada del partido (marca de agua oficial en un sitio no autorizado)",
 "juez_id": "jueza-laura-ficticia", "juez_nombre": "Dra. Laura Ficticia",
 "juzgado_id": "jg-centro-3", "juzgado_nombre": "Juzgado de Garantías N.º 3 (ficticio) — Distrito Judicial Centro",
 "ordenado_min": 2.6, "vence_min": 105,
 "estado": "vigente",             # en_curso | vigente | vencido | levantado
 "finalizado_min": None, "motivo_fin": None,
 "proveedores": [{"proveedor_id": "aurora", "estado": "aplicada", "aplicada_min": 3.2, "finalizada_min": None},
                 {"proveedor_id": "andina", "estado": "recibida", "aplicada_min": None, "finalizada_min": None},
                 {"proveedor_id": "cumbre", "estado": "recibida", "aplicada_min": None, "finalizada_min": None}]}
```
- Qué se bloqueó (`tipo`, `objetivo`), cuándo (`ordenado_min`), por orden de qué juez y juzgado, hasta cuándo (`vence_min`) y en qué estado está.
- `proveedores`: la **última** orden de cada proveedor para ese objetivo (los reintentos no se muestran).
- `estado`: `levantado` si se levantó; `vencido` si todas terminaron por vencimiento; `vigente` si al menos un proveedor la tiene aplicada; si no, `en_curso`.
- **No va:** capturas, firmas, claves, mensajes de reclamos ni datos personales reales. Nombres de jueces y juzgados son los ficticios públicos de `/juzgados`.
- Tiene que coincidir con la auditoría interna.

---

## 10. Base de datos (v1.2) — `plataforma/db/` (T11)

- `DATABASE_URL`: `postgres://...` en Vercel y en el motor, o `sqlite:///salida/plataforma.db` en modo local. El mismo código funciona con las dos.
- Tablas: `partidos`, `casos`, `expedientes`, `pedidos`, `ordenes`, `reclamos`, `solicitudes`, `auditoria` y `verificaciones` (SQL completo en `coordinacion/guias/T11-base-y-vercel.md`, paso 5). Columnas: `partido_id`, el id del contrato (`caso_id`, `pedido_id`, …), `estado` cuando corresponda y `datos` (el dict del contrato, JSONB en Postgres y TEXT en SQLite). `auditoria` suma `seq` y `hash`, con `UNIQUE (partido_id, seq)`.
- Quién escribe qué: el **motor** escribe todo, menos la decisión del juez. La **web** solo cambia la decisión en `pedidos` (`estado`, `juez_id`, `juzgado_id`, `decidido_min`, `motivo_rechazo`) y crea filas en `solicitudes` (asumir turno, levantar). El motor escribe `partidos` en cada ciclo y resuelve las `solicitudes`. **Solo el motor escribe en `auditoria`.**
- Nadie guarda en la base claves de firma, firmas completas ni `contenido_b64`.

## Ejemplos

```python
from plataforma.contratos import (
    EJEMPLO_DETECCION, EJEMPLO_CASO, EJEMPLO_EXPEDIENTE, EJEMPLO_PEDIDO, EJEMPLO_PEDIDO_PENDIENTE,
    EJEMPLO_ORDEN, EJEMPLO_ORDEN_PAYLOAD, EJEMPLO_ORDEN_FALLIDA, EJEMPLO_ORDEN_REINTENTO,
    EJEMPLO_EVENTO_AUDITORIA, EJEMPLO_AUDITORIA, EJEMPLO_RECLAMO, EJEMPLO_RECLAMO_GESTION,
    EJEMPLO_EVENTO_REGISTRO, EJEMPLO_REGISTRO, EJEMPLO_ENTRADA_PUBLICA, EJEMPLO_LEVANTAR_REQ,
    EJEMPLO_API_ESTADO, EJEMPLO_API_PEDIDOS, EJEMPLO_API_APROBAR_REQ, EJEMPLO_API_APROBAR_RESP,
    EJEMPLO_API_RECHAZAR_REQ, EJEMPLO_API_RECHAZAR_RESP, EJEMPLO_API_ORDENES, EJEMPLO_API_AUDITORIA,
    EJEMPLO_API_RECLAMOS, EJEMPLO_API_LEVANTAR_REQ, EJEMPLO_API_LEVANTAR_RESP, EJEMPLO_API_PUBLICO,
)
# Formas del simulador: EJEMPLO_SIM_ESTADO, EJEMPLO_SIM_PARTIDO, EJEMPLO_SIM_DETECCIONES, EJEMPLO_SIM_DNS_IP,
# EJEMPLO_SIM_DNS_DOMINIO, EJEMPLO_SIM_JUZGADOS, EJEMPLO_SIM_PROVEEDORES, EJEMPLO_SIM_RECLAMOS,
# EJEMPLO_SIM_RESPUESTA_ORDEN, EJEMPLO_SIM_VISTA_ORDEN.
```
`python -m plataforma.contratos` verifica que los hashes y los ids de los ejemplos cierren.
