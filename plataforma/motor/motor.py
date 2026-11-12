"""T05 — Motor: el loop que une simulador, cerebro (T01), evidencia (T03), juez (T04) y despacho (T02).

Estado en memoria (plan B de la decisión 20: todo corre en la notebook). Cuando T11 tenga plataforma/db,
se persiste ahí sin cambiar las formas: la API (api.py) devuelve exactamente lo de contratos.md §5.
"""
import copy
import json
import secrets
import shutil
import threading
import time
import traceback
from pathlib import Path
from typing import Dict, List, Optional

from plataforma.analisis import Cerebro
from plataforma.contratos import GRACIA_MIN, vence_min_para
from plataforma.despacho.despacho import Despacho, _http, normalizar_sim
from plataforma.evidencia.gestor import GestorEvidencia

RAIZ = Path(__file__).resolve().parents[2]
ESPERA_S = 0.25        # a x30, un cuarto de segundo real son ~0,12 minutos de partido


class Motor:
    def __init__(self, sim: str, juez_automatico: bool = False, salida: Path = RAIZ / "salida",
                 con_base: bool = False):
        self.sim = normalizar_sim(sim)
        self.juez_automatico = juez_automatico
        self.corrida = secrets.token_hex(2)
        self.lock = threading.RLock()          # estado del motor (pedidos, expedientes)
        self._lock_aud = threading.Lock()      # SOLO la auditoría: nunca toma otro lock adentro (evita deadlocks)
        self.partido = self._pedir("/partido")
        self.proveedores = self._pedir("/proveedores")
        self.turnos = self._pedir("/juzgados").get("turnos", [])
        self.fin = float(self.partido["fin_min"])
        self.salida = Path(salida)
        self.ruta_auditoria = self.salida / f"auditoria_{self.partido['id']}_{self.corrida}.jsonl"
        self.evidencia = GestorEvidencia(str(self.ruta_auditoria))
        self.cerebro = Cerebro(self.partido, self._dns)
        self.despacho = Despacho(self.sim, self.corrida, self.auditar)
        self.pedidos: Dict[str, dict] = {}
        self.resumenes: Dict[str, dict] = {}
        self.expedientes: Dict[str, dict] = {}
        self.despachados: set = set()
        self.minuto = 0.0
        self.de_turno: List[str] = []
        self.ultimo_ok = 0.0
        self.desde = -1.0
        self.terminado = False
        self.descartados = 0
        self.reclamos: Dict[str, dict] = {}
        self.desde_reclamos = -1.0
        # Con base (T11): la web en Vercel lee y decide ahí. Un partido_id por corrida para no mezclar corridas.
        self.partido_db_id = f"{self.partido['id']}-{self.corrida}"
        self.sincro = None
        if con_base:
            from plataforma.motor.sincro_db import SincroDB
            self.sincro = SincroDB(self, self.partido_db_id)

    # --- utilidades -------------------------------------------------------------------------

    def _pedir(self, ruta: str):
        estado, datos = _http(self.sim, ruta)
        if estado != 200:
            raise RuntimeError(f"El simulador respondió {estado} en {ruta}: {datos}")
        return datos

    def _dns(self, ip: str):
        estado, datos = _http(self.sim, f"/dns-pasivo?ip={ip}")
        return datos if estado == 200 else None

    def auditar(self, actor: str, accion: str, datos: dict, minuto: Optional[float] = None) -> None:
        with self._lock_aud:
            self.evidencia.registrar_evento(actor, accion, datos, round(minuto if minuto is not None else self.minuto, 3))

    # --- loop ---------------------------------------------------------------------------------

    def correr(self) -> None:
        self.auditar("motor", "partido_iniciado", {"partido_id": self.partido["id"], "corrida": self.corrida,
                                                   "juez_automatico": self.juez_automatico})
        if self.sincro:
            self.sincro.arrancar()          # la base se sincroniza en su propio hilo (sincro_db.py)
        while not self.terminado:
            try:
                self.vuelta()
            except Exception:  # un error en una vuelta no puede frenar el partido
                traceback.print_exc()
            time.sleep(ESPERA_S)
        if self.sincro:
            self.sincro.esperar()           # última subida a la base antes de salir

    def vuelta(self) -> None:
        estado = self._pedir("/estado")
        with self.lock:
            self.minuto = estado["minuto_actual"]
            self.de_turno = estado["jueces_de_turno"]
            self.ultimo_ok = time.monotonic()
        self.despacho.actualizar_turno(self.minuto, self.de_turno)

        lote = self._pedir(f"/detecciones?desde={self.desde}")
        for d in lote["detecciones"]:
            self._procesar(d)
        self.desde = lote["minuto_actual"]
        self._leer_reclamos()

        if self.juez_automatico:
            if self.de_turno and not self.despacho.turno_ratificado():
                self.despacho.ratificar(self.de_turno[0])
            pendientes = [p for p, x in self.pedidos.items() if x["estado"] == "pendiente"]
            if pendientes and self.de_turno:
                self.decidir(pendientes, self.de_turno[0], "aprobado")
            for r in list(self.reclamos.values()):
                if r["estado"] == "pendiente" and r["verificado"] and self.de_turno:
                    self.levantar_por_reclamo(r["reclamo_id"], self.de_turno[0],
                                              "Sitio legítimo afectado: se reemplaza por bloqueo de dominio", True)

        for pid, p in list(self.pedidos.items()):
            if p["estado"] == "aprobado" and pid not in self.despachados:
                self.despachados.add(pid)
                self.despacho.despachar(p)
        self.despacho.seguir(self.pedidos)

        if self.minuto >= self.fin + GRACIA_MIN + 0.5:
            self._cerrar()

    def _procesar(self, d: dict) -> None:
        caso, nuevo = self.cerebro.procesar(d)
        if not nuevo:
            return
        if caso["clasificacion"] != "pirata":
            with self.lock:
                self.descartados += 1
            self.auditar("analisis", "caso_descartado",
                         {"caso_id": caso["caso_id"], "host": caso["host"], "clasificacion": caso["clasificacion"],
                          "motivo": caso["motivo_clasificacion"]}, d["minuto"])
            return
        self.auditar("analisis", "caso_creado", {"caso_id": caso["caso_id"], "host": caso["host"], "ip": caso["ip"],
                                                "tipo_recomendado": caso["tipo_recomendado"]}, self.minuto)
        with self.lock:
            # Copia congelada: el cerebro sigue sumando detecciones al caso vivo, y el expediente ya está hasheado.
            with self._lock_aud:
                exp = self.evidencia.crear_expediente(copy.deepcopy(caso), d, self.partido["id"], round(self.minuto, 3))
            self.expedientes[exp["expediente_id"]] = exp
            pid = f"P-{len(self.pedidos) + 1:03d}"
            objetivos = []
            for pv in self.proveedores:
                if caso["tipo_recomendado"] == "ip" and "ip" in pv["capacidades"]:
                    objetivos.append({"proveedor_id": pv["id"], "tipo": "ip", "objetivo": caso["ip"]})
                elif "dominio" in pv["capacidades"]:
                    objetivos.append({"proveedor_id": pv["id"], "tipo": "dominio", "objetivo": caso["host"]})
            self.pedidos[pid] = {"pedido_id": pid, "expediente_id": exp["expediente_id"], "origen": "deteccion",
                                 "objetivos": objetivos, "vence_min": vence_min_para(self.fin),
                                 "creado_min": round(self.minuto, 3), "estado": "pendiente", "juez_id": None,
                                 "juzgado_id": None, "decidido_min": None, "motivo_rechazo": None}
            self.resumenes[pid] = {k: caso[k] for k in ("caso_id", "host", "ip", "organizacion", "marca",
                                                        "motivo_clasificacion", "ip_compartida", "dominios_en_ip",
                                                        "tipo_recomendado", "motivo_tipo", "primer_minuto")}
        self.auditar("motor", "pedido_creado", {"pedido_id": pid, "expediente_id": exp["expediente_id"],
                                               "objetivos": objetivos}, self.minuto)

    # --- decisiones del juez (las llama la API o el juez automático) -------------------------

    def decidir(self, pedido_ids: List[str], juez_id: str, nuevo: str, motivo: Optional[str] = None) -> dict:
        hechos, errores = [], []
        with self.lock:
            for pid in pedido_ids:
                p = self.pedidos.get(pid)
                if p is None:
                    errores.append({"pedido_id": pid, "error": "No existe el pedido"})
                elif juez_id not in self.de_turno:
                    errores.append({"pedido_id": pid, "error": f"{juez_id} no está de turno en el minuto {self.minuto:.1f}"})
                elif p["estado"] != "pendiente":
                    errores.append({"pedido_id": pid, "error": f"El pedido ya está {p['estado']}"})
                else:
                    hechos.append(pid)
        for pid in hechos:
            if self.sincro:   # con base, se decide en la base (como la web) y vuelve por sincro.traer()
                self.sincro.decidir_en_base(pid, nuevo, juez_id, self.despacho.juzgado_de(juez_id),
                                            round(self.minuto, 3), motivo)
            else:
                self.aplicar_decision(pid, nuevo, juez_id, round(self.minuto, 3), motivo)
        return {"hechos": hechos, "errores": errores, "decidido_min": round(self.minuto, 3)}

    def aplicar_decision(self, pid: str, nuevo: str, juez_id: str, decidido_min: Optional[float],
                         motivo: Optional[str] = None) -> None:
        """Registra la decisión del juez en el pedido local. El despacho la toma en la próxima vuelta."""
        with self.lock:
            p = self.pedidos.get(pid)
            if p is None or p["estado"] != "pendiente":
                return
            p.update(estado=nuevo, juez_id=juez_id, juzgado_id=self.despacho.juzgado_de(juez_id),
                     decidido_min=decidido_min if decidido_min is not None else round(self.minuto, 3),
                     motivo_rechazo=motivo if nuevo == "rechazado" else None)
        self.auditar(f"juez:{juez_id}", "pedido_aprobado" if nuevo == "aprobado" else "pedido_rechazado",
                     {"pedido_id": pid, **({"motivo": motivo} if motivo else {})})

    # --- reclamos (T06): verificar, levantar con firma y reemplazar por algo más preciso ----------

    def _leer_reclamos(self) -> None:
        estado, lote = _http(self.sim, f"/reclamos?desde={self.desde_reclamos}")
        if estado != 200:
            return
        piratas = {c["host"] for c in self.cerebro.casos() if c["clasificacion"] == "pirata"}
        for r in lote.get("reclamos", []):
            if r["id"] in self.reclamos:
                continue
            afectadas = []
            for o in self.despacho.vista():
                if o["proveedor_id"] != r["proveedor"] or o["estado"] not in ("recibida", "aplicada"):
                    continue
                if o["tipo"] == "dominio":
                    cubre = o["objetivo"] == r["dominio"]
                else:
                    cubre = r["dominio"] in (self._dns(o["objetivo"]) or {}).get("dominios", [])
                if cubre:
                    afectadas.append(o["orden_id"])
            verificado = r["dominio"] not in piratas and bool(afectadas)
            rec = {"reclamo_id": r["id"], "minuto": r["minuto"], "dominio": r["dominio"],
                   "proveedor_id": r["proveedor"], "mensaje": r.get("mensaje"),
                   "estado": "pendiente" if verificado else "descartado", "verificado": verificado,
                   "ordenes_afectadas": afectadas, "ordenes_levantadas": [], "pedido_reemplazo_id": None}
            with self.lock:
                self.reclamos[r["id"]] = rec
            self.auditar("motor", "reclamo_recibido", {k: rec[k] for k in (
                "reclamo_id", "dominio", "proveedor_id", "verificado", "ordenes_afectadas")})
        self.desde_reclamos = lote.get("minuto_actual", self.desde_reclamos)

    def levantar_por_reclamo(self, reclamo_id: str, juez_id: str, motivo: str, reemplazar: bool) -> dict:
        """El juez levanta las órdenes que tocaban al sitio legítimo y, si eran por IP, las reemplaza por el dominio."""
        rec = self.reclamos.get(reclamo_id)
        if rec is None or rec["estado"] != "pendiente":
            return {"error": f"El reclamo {reclamo_id} no está pendiente"}
        levantadas, reemplazos = [], []
        for oid in rec["ordenes_afectadas"]:
            if self.despacho.levantar(oid, juez_id, motivo)["ok"]:
                levantadas.append(oid)
                o = next(x for x in self.despacho.vista() if x["orden_id"] == oid)
                if reemplazar and o["tipo"] == "ip":
                    reemplazos.append((o, self.expedientes[o["expediente_id"]]["caso"]["host"]))
        pedido_reemplazo = None
        if reemplazos:
            with self.lock:
                pedido_reemplazo = f"P-{len(self.pedidos) + 1:03d}"
                o0, host = reemplazos[0]
                self.pedidos[pedido_reemplazo] = {
                    "pedido_id": pedido_reemplazo, "expediente_id": o0["expediente_id"],
                    "origen": f"reclamo:{reclamo_id}",
                    "objetivos": [{"proveedor_id": o["proveedor_id"], "tipo": "dominio", "objetivo": h}
                                  for o, h in reemplazos],
                    "vence_min": vence_min_para(self.fin), "creado_min": round(self.minuto, 3), "estado": "aprobado",
                    "juez_id": juez_id, "juzgado_id": self.despacho.juzgado_de(juez_id),
                    "decidido_min": round(self.minuto, 3), "motivo_rechazo": None}
                base = self.resumenes[next(iter(self.resumenes))] if self.resumenes else {}
                self.resumenes[pedido_reemplazo] = dict(base, host=host, tipo_recomendado="dominio",
                                                        motivo_tipo=f"Reemplazo por el reclamo {reclamo_id}")
        with self.lock:
            rec.update(estado="levantado", ordenes_levantadas=levantadas, pedido_reemplazo_id=pedido_reemplazo)
        self.auditar(f"juez:{juez_id}", "reclamo_resuelto", {
            "reclamo_id": reclamo_id, "ordenes_levantadas": levantadas,
            "pedido_reemplazo_id": pedido_reemplazo, "motivo": motivo})
        return {"reclamo_id": reclamo_id, "estado": "levantado", "ordenes_levantadas": levantadas,
                "pedido_reemplazo_id": pedido_reemplazo}

    # --- vistas para la API ---------------------------------------------------------------

    def estado_api(self) -> dict:
        ordenes = self.despacho.vista()           # fuera del lock del motor: nunca anidar motor -> despacho
        ratificado = self.despacho.turno_ratificado()
        with self.lock:
            ps = list(self.pedidos.values())
            prox = min((t["hasta_min"] for t in self.turnos if t["hasta_min"] > self.minuto), default=None)
            return {
                "partido_id": self.partido["id"], "minuto_actual": self.minuto, "fin_min": self.fin,
                "finalizado": self.minuto >= self.fin, "jueces_de_turno": self.de_turno,
                "proximo_cambio_turno_min": prox if prox is not None and prox < self.fin else None,
                "simulador_ok": time.monotonic() - self.ultimo_ok < 5,
                "turno_ratificado": ratificado,
                "contadores": {
                    "casos_piratas": len(ps), "casos_descartados": self.descartados,
                    "pedidos_pendientes": sum(p["estado"] == "pendiente" for p in ps),
                    "pedidos_aprobados": sum(p["estado"] == "aprobado" for p in ps),
                    "pedidos_rechazados": sum(p["estado"] == "rechazado" for p in ps),
                    "ordenes_activas": sum(o["estado"] in ("recibida", "aplicada") for o in ordenes),
                    "ordenes_fallidas": sum(o["estado"] == "fallida" for o in ordenes),
                    "reclamos_pendientes": sum(r["estado"] == "pendiente" for r in self.reclamos.values()),
                },
            }

    def pedidos_api(self, filtro: Optional[str]) -> List[dict]:
        with self.lock:
            return [dict(p, resumen=self.resumenes[p["pedido_id"]]) for p in self.pedidos.values()
                    if filtro is None or p["estado"] == filtro]

    def publico_api(self) -> List[dict]:
        """Registro público: qué se bloqueó, cuándo, por orden de quién y hasta cuándo. Sin capturas ni claves."""
        return [{"objetivo": o["objetivo"], "tipo": o["tipo"], "proveedor_id": o["proveedor_id"],
                 "desde_min": o["aplicada_min"], "hasta_min": o["finalizada_min"] or o["vence_min"],
                 "juzgado_id": o["juzgado_id"], "juez_id": o["juez_id"], "estado": o["estado"],
                 "expediente_id": o["expediente_id"]}
                for o in self.despacho.vista() if o["aplicada_min"] is not None]

    # --- cierre ---------------------------------------------------------------------------

    def _cerrar(self) -> None:
        self.auditar("motor", "partido_cerrado", {"pedidos": len(self.pedidos),
                                                  "ordenes": len(self.despacho.ordenes)})
        with self.lock:
            self.terminado = True
            primero = next(iter(self.expedientes.values()), None)
            if primero:
                (self.salida / f"expediente_{self.partido['id']}_{self.corrida}.json").write_text(
                    json.dumps(primero, ensure_ascii=False, indent=2), encoding="utf-8")
        with self._lock_aud:
            integra = self.evidencia.verificar_integridad()
        print(f"\nPartido cerrado. Auditoría: {self.ruta_auditoria} (íntegra: {integra}).")

    def exportar_entrega(self, destino: Path) -> Path:
        """Copia la auditoría y el primer expediente a entrega/<partido_id>/ (el viernes: el del partido final)."""
        carpeta = destino / self.partido["id"]
        carpeta.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.ruta_auditoria, carpeta / "auditoria.jsonl")
        with self.lock:
            primero = next(iter(self.expedientes.values()), None)
        if primero:
            (carpeta / "expediente.json").write_text(json.dumps(primero, ensure_ascii=False, indent=2), encoding="utf-8")
        return carpeta
