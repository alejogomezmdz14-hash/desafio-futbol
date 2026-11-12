"""SOLO DESARROLLO de T04: imita la API de T11 (contratos.md §5) para probar la pantalla del juez sin base ni motor.

    uvicorn plataforma.web.mock_api:app --port 8000      ->  http://localhost:8000/juez/   (usuario coordinacion; la contraseña se imprime al arrancar)

Corre el partido de práctica (datos/escenario_practica.json) con el reloj acelerado (MOCK_ACELERAR, por defecto x10),
usa el Cerebro real (T01) para armar casos y pedidos, y simula el avance de las órdenes, los reintentos de Cumbre y
el cambio de turno del minuto 50. No firma nada ni habla con el simulador.
"""
import json
import os
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from plataforma.analisis import Cerebro
from plataforma.contratos import hash_expediente, sha256_captura, vence_min_para

RAIZ = Path(__file__).resolve().parents[2]
WEB = Path(__file__).resolve().parent
ACELERAR = float(os.environ.get("MOCK_ACELERAR", "10"))
INICIO_MIN = float(os.environ.get("MOCK_INICIO_MIN", "0"))
# Login simple (decisión 43): sin contraseña fija, se genera por corrida si no se define COORD_PASSWORD.
if not os.environ.get("COORD_PASSWORD"):
    import secrets as _secrets
    os.environ["COORD_PASSWORD"] = _secrets.token_urlsafe(9)
    print(f"Mock: usuario coordinacion, contraseña {os.environ['COORD_PASSWORD']}", flush=True)
os.environ.setdefault("SESION_SECRET", __import__("secrets").token_urlsafe(32))
ARG = timezone(timedelta(hours=-3))

escenario = json.loads((RAIZ / "datos/escenario_practica.json").read_text(encoding="utf-8"))
proveedores = json.loads((RAIZ / "datos/proveedores.json").read_text(encoding="utf-8"))["proveedores"]
juzgados = json.loads((RAIZ / "datos/juzgados.json").read_text(encoding="utf-8"))
JUZGADO_DE = {j["id"]: z["id"] for z in juzgados["juzgados"] for j in z["jueces"]}
partido = escenario["partido"]
FIN = float(partido["fin_min"])
DEMORA = {p["id"]: p["comportamiento"]["demora_min"] for p in proveedores}


def dns(ip: str):
    if ip not in escenario["dns_pasivo"]:
        return None
    asn = escenario["ip_asn"].get(ip)
    return {"ip": ip, "asn": asn, "organizacion": escenario["asn"].get(str(asn)), "dominios": escenario["dns_pasivo"][ip]}


class Estado:
    def __init__(self):
        self.lock = threading.RLock()
        self.t0 = time.monotonic()
        self.cerebro = Cerebro(partido, dns)
        self.pendientes = sorted(escenario["detecciones"], key=lambda d: d["minuto"])
        self.pedidos: Dict[str, dict] = {}
        self.resumenes: Dict[str, dict] = {}
        self.expedientes: Dict[str, dict] = {}
        self.ordenes: List[dict] = []
        self.descartados = 0
        self.juez_ratificado: Optional[str] = None
        self.turno_anterior: Optional[str] = None

    def minuto(self) -> float:
        return INICIO_MIN + (time.monotonic() - self.t0) * ACELERAR / 60

    def de_turno(self, m: float) -> List[str]:
        return [t["juez_id"] for t in juzgados["turnos"] if t["desde_min"] <= m < t["hasta_min"]]

    def avanzar(self) -> None:
        with self.lock:
            m = self.minuto()
            turno = self.de_turno(m)
            if self.turno_anterior is None:
                self.juez_ratificado = turno[0] if turno else None
            self.turno_anterior = turno[0] if turno else None
            while self.pendientes and self.pendientes[0]["minuto"] <= m:
                d = self.pendientes.pop(0)
                caso, nuevo = self.cerebro.procesar(d)
                if not nuevo:
                    continue
                if caso["clasificacion"] != "pirata":
                    self.descartados += 1
                    continue
                self._crear_pedido(caso, d, m)
            for o in self.ordenes:
                self._avanzar_orden(o, m)

    def _crear_pedido(self, caso: dict, d: dict, m: float) -> None:
        n = len(self.pedidos) + 1
        pid, eid = f"P-{n:03d}", f"EXP-2026-{n:06d}"
        cap = d["captura"]
        exp = {"expediente_id": eid, "partido_id": partido["id"], "caso": caso,
               "capturas": [{"deteccion_id": d["id"], "capturada_min": cap["capturada_min"], "formato": cap["formato"],
                             "duracion_seg": cap["duracion_seg"], "bytes": len(cap["contenido_b64"]) * 3 // 4,
                             "sha256": sha256_captura(cap["contenido_b64"])}],
               "promocion": d.get("promocion", []), "vence_propuesto_min": vence_min_para(FIN),
               "creado_min": round(m, 2), "creado_ts": datetime.now(ARG).isoformat(timespec="seconds"), "hash": ""}
        exp["hash"] = hash_expediente(exp)
        objetivos = []
        for p in proveedores:
            usa_ip = caso["tipo_recomendado"] == "ip" and "ip" in p["capacidades"]
            objetivos.append({"proveedor_id": p["id"], "tipo": "ip" if usa_ip else "dominio",
                              "objetivo": caso["ip"] if usa_ip else caso["host"]})
        self.expedientes[eid] = exp
        self.pedidos[pid] = {"pedido_id": pid, "expediente_id": eid, "origen": "deteccion", "objetivos": objetivos,
                             "vence_min": vence_min_para(FIN), "creado_min": round(m, 2), "estado": "pendiente",
                             "juez_id": None, "juzgado_id": None, "decidido_min": None, "motivo_rechazo": None}
        self.resumenes[pid] = {k: caso[k] for k in ("caso_id", "host", "ip", "organizacion", "marca",
                                                    "motivo_clasificacion", "ip_compartida", "dominios_en_ip",
                                                    "tipo_recomendado", "motivo_tipo", "primer_minuto")}

    def despachar(self, pedido: dict, juez: str, m: float, intento: int = 1, solo: Optional[str] = None,
                  reemplaza: Optional[str] = None) -> None:
        for ob in pedido["objetivos"]:
            if solo and ob["proveedor_id"] != solo:
                continue
            oid = f"ord-mock-{pedido['pedido_id']}-{ob['proveedor_id']}-{intento}"
            falla = ob["proveedor_id"] == "cumbre" and intento == 1 and int(pedido["pedido_id"][2:]) % 2 == 1
            self.ordenes.append({
                "orden_id": oid, "pedido_id": pedido["pedido_id"], "expediente_id": pedido["expediente_id"],
                "proveedor_id": ob["proveedor_id"], "tipo": ob["tipo"], "objetivo": ob["objetivo"],
                "vence_min": pedido["vence_min"], "juzgado_id": JUZGADO_DE[juez], "juez_id": juez,
                "estado": "recibida", "intentos": intento, "reemplaza_a": reemplaza, "enviada_min": round(m, 2),
                "recibida_min": round(m, 2), "aplicada_min": None, "finalizada_min": None, "motivo": None,
                "consultar": f"/proveedores/{ob['proveedor_id']}/ordenes/{oid}",
                "_aplica": m + DEMORA[ob["proveedor_id"]], "_falla": falla})

    def _avanzar_orden(self, o: dict, m: float) -> None:
        if o["estado"] == "recibida" and m >= o["_aplica"]:
            if o["_falla"]:
                o["estado"], o["motivo"] = "fallida", "Error interno del proveedor. Reenviar la orden con un nuevo orden_id."
                juez = self.de_turno(m)[0]
                if self.juez_ratificado == juez:  # sin ratificar el turno, el reintento queda en espera
                    self.despachar(self.pedidos[o["pedido_id"]], juez, m, o["intentos"] + 1, o["proveedor_id"], o["orden_id"])
                else:
                    o["_espera"] = True
                return
            o["estado"], o["aplicada_min"] = "aplicada", round(o["_aplica"], 2)
        if o["estado"] == "aplicada" and m >= o["vence_min"]:
            o["estado"], o["finalizada_min"] = "vencida", float(o["vence_min"])

    def estado_api(self) -> dict:
        m = self.minuto()
        turno = self.de_turno(m)
        prox = min((t["hasta_min"] for t in juzgados["turnos"] if t["hasta_min"] > m), default=None)
        ps = list(self.pedidos.values())
        return {
            "partido_id": partido["id"], "minuto_actual": round(m, 2), "fin_min": FIN, "finalizado": m >= FIN,
            "jueces_de_turno": turno, "proximo_cambio_turno_min": prox, "simulador_ok": True,
            "turno_ratificado": bool(turno) and self.juez_ratificado == turno[0],
            "contadores": {
                "casos_piratas": len(ps), "casos_descartados": self.descartados,
                "pedidos_pendientes": sum(p["estado"] == "pendiente" for p in ps),
                "pedidos_aprobados": sum(p["estado"] == "aprobado" for p in ps),
                "pedidos_rechazados": sum(p["estado"] == "rechazado" for p in ps),
                "ordenes_activas": sum(o["estado"] in ("recibida", "aplicada") for o in self.ordenes),
                "ordenes_fallidas": sum(o["estado"] == "fallida" for o in self.ordenes),
                "reclamos_pendientes": 0,
            },
        }


estado = Estado()


def _ciclo() -> None:
    while True:
        estado.avanzar()
        time.sleep(0.2)


threading.Thread(target=_ciclo, daemon=True).start()

app = FastAPI(title="Mock API del juez (solo desarrollo)")


from plataforma.api.sesion import router as router_sesion, sesion  # noqa: E402

app.include_router(router_sesion)


@app.exception_handler(HTTPException)
async def _error(_, exc: HTTPException):
    d = exc.detail
    return JSONResponse(status_code=exc.status_code, content=d if isinstance(d, dict) and "error" in d else {"error": d})


@app.get("/api/estado")
def api_estado():
    with estado.lock:
        return estado.estado_api()


def _pedidos(filtro: Optional[str]):
    with estado.lock:
        ps = [dict(p, resumen=estado.resumenes[p["pedido_id"]]) for p in estado.pedidos.values()
              if filtro is None or p["estado"] == filtro]
        return {"pedidos": ps}


@app.get("/api/pedidos")
def api_pedidos(estado: Optional[str] = None):  # ?estado=pendiente (tapa a la global solo acá adentro)
    return _pedidos(estado)


@app.get("/api/expedientes/{expediente_id}")
def api_expediente(expediente_id: str):
    exp = estado.expedientes.get(expediente_id)
    if exp is None:
        raise HTTPException(404, f"No existe el expediente {expediente_id}")
    return exp


def _decidir(cuerpo: dict, nuevo: str) -> dict:
    juez = cuerpo.get("juez_id")
    with estado.lock:
        m = estado.minuto()
        hechos, errores = [], []
        for pid in cuerpo.get("pedido_ids", []):
            p = estado.pedidos.get(pid)
            if p is None:
                errores.append({"pedido_id": pid, "error": "No existe el pedido"})
            elif juez not in estado.de_turno(m):
                errores.append({"pedido_id": pid, "error": f"{juez} no está de turno en el minuto {m:.1f}"})
            elif p["estado"] != "pendiente":
                errores.append({"pedido_id": pid, "error": f"El pedido ya está {p['estado']}"})
            else:
                p.update(estado=nuevo, juez_id=juez, juzgado_id=JUZGADO_DE[juez], decidido_min=round(m, 2),
                         motivo_rechazo=cuerpo.get("motivo") if nuevo == "rechazado" else None)
                if nuevo == "aprobado":
                    estado.despachar(p, juez, m)
                hechos.append(pid)
        return {"hechos": hechos, "errores": errores, "decidido_min": round(m, 2)}


@app.post("/api/pedidos/aprobar", dependencies=[Depends(sesion)])
def api_aprobar(cuerpo: dict):
    r = _decidir(cuerpo, "aprobado")
    return {"aprobados": r["hechos"], "errores": r["errores"], "decidido_min": r["decidido_min"]}


@app.post("/api/pedidos/rechazar", dependencies=[Depends(sesion)])
def api_rechazar(cuerpo: dict):
    if not (cuerpo.get("motivo") or "").strip():
        raise HTTPException(422, "Rechazar requiere un motivo")
    r = _decidir(cuerpo, "rechazado")
    return {"rechazados": r["hechos"], "errores": r["errores"], "decidido_min": r["decidido_min"]}


@app.post("/api/turno/asumir", dependencies=[Depends(sesion)])
def api_asumir(cuerpo: dict):
    juez = cuerpo.get("juez_id")
    with estado.lock:
        m = estado.minuto()
        if juez not in estado.de_turno(m):
            raise HTTPException(409, f"{juez} no está de turno en el minuto {m:.1f}")
        estado.juez_ratificado = juez
        vigentes = [o["orden_id"] for o in estado.ordenes if o["estado"] in ("recibida", "aplicada")]
        for o in list(estado.ordenes):
            if o.pop("_espera", False):
                estado.despachar(estado.pedidos[o["pedido_id"]], juez, m, o["intentos"] + 1, o["proveedor_id"], o["orden_id"])
        return {"juez_id": juez, "ratificadas": vigentes, "decidido_min": round(m, 2)}


@app.get("/api/ordenes")
def api_ordenes():
    with estado.lock:
        return {"ordenes": [{k: v for k, v in o.items() if not k.startswith("_")} for o in estado.ordenes]}


@app.get("/")
def raiz():
    return RedirectResponse("/juez/")


app.mount("/juez", StaticFiles(directory=WEB, html=True), name="juez")
