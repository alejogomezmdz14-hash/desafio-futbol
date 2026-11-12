"""Puente entre el motor (en memoria) y la base de T11 (plataforma/db), para que la web en Vercel vea y decida.

Reglas (contratos §10, decisiones 15 a 19):
- El motor ESCRIBE: estado del partido, casos, expedientes, pedidos (solo al crearlos), órdenes, reclamos y auditoría.
- La web solo cambia la decisión de los pedidos (aprobado o rechazado) e inserta solicitudes (asumir_turno, levantar).
- El motor LEE esas decisiones y solicitudes, y las ejecuta. Un pedido nunca se reescribe desde acá: pisaría la
  decisión del juez.
- Solo se escribe lo que cambió (huella por fila), para no saturar una base remota en cada vuelta.
"""
import json
import os
import threading
import time
import traceback
from typing import Dict, Optional

from plataforma import db
from plataforma.contratos import json_canonico

ESPERA_SINCRO_S = 0.3


class SincroDB:
    def __init__(self, motor, partido_db_id: str):
        self.motor = motor
        self.pid = partido_db_id
        self._huellas: Dict[str, bytes] = {}
        self._pedidos_subidos: set = set()
        self._rechazos_vistos: set = set()
        self._aud_offset = 0
        db.usar_conexion_persistente()
        db.crear_esquema()

    def _cambio(self, clave: str, obj) -> bool:
        h = json_canonico(obj)
        if self._huellas.get(clave) == h:
            return False
        self._huellas[clave] = h
        return True

    # --- motor -> base ----------------------------------------------------------------------

    # --- hilo propio: la base nunca frena la vuelta del motor ----------------------------------
    # Contra Neon cada consulta tarda 50-200 ms; hecha dentro de la vuelta, a x30 eran minutos de partido
    # de demora por bloqueo. Ahora el motor detecta y despacha solo, y este hilo sube y baja cambios en paralelo.

    def arrancar(self) -> None:
        self._hilo = threading.Thread(target=self._bucle, name="sincro-db", daemon=True)
        self._hilo.start()

    def _una_vuelta(self) -> None:
        try:
            self.traer()
            self.empujar()
        except Exception:   # un corte de la base no puede frenar el partido: se reintenta en la próxima
            traceback.print_exc()

    def _bucle(self) -> None:
        while not self.motor.terminado:
            self._una_vuelta()
            time.sleep(ESPERA_SINCRO_S)
        self._una_vuelta()   # última subida: estado final, órdenes vencidas y cierre de la auditoría

    def esperar(self, timeout: float = 120) -> None:
        if getattr(self, "_hilo", None):
            self._hilo.join(timeout)

    def empujar(self) -> None:
        m = self.motor
        estado = m.estado_api()
        with m.lock:   # foto del estado bajo el candado; las escrituras van afuera para no frenar al motor
            casos = [dict(c) for c in m.cerebro.casos()]
            expedientes = list(m.expedientes.items())
            pedidos = [(k, dict(p), m.resumenes.get(k), k in m.despachados) for k, p in m.pedidos.items()
                       if k not in self._pedidos_subidos]
            reclamos = [dict(r) for r in m.reclamos.values()]
        db.guardar_estado_partido(self.pid, estado)
        for caso in casos:
            if self._cambio(f"caso:{caso['caso_id']}", caso):
                db.guardar("casos", self.pid, caso["caso_id"], caso)
        for eid, exp in expedientes:
            if self._cambio(f"exp:{eid}", {"h": exp["hash"]}):
                db.guardar("expedientes", self.pid, eid, exp)
        for pid_, p, resumen, despachado in pedidos:
            db.guardar("pedidos", self.pid, pid_, dict(p, resumen=resumen), estado=p["estado"],
                       juez_id=p["juez_id"], juzgado_id=p["juzgado_id"], decidido_min=p["decidido_min"],
                       motivo_rechazo=p["motivo_rechazo"], despachado=despachado)
            self._pedidos_subidos.add(pid_)
        for o in m.despacho.vista():
            if self._cambio(f"ord:{o['orden_id']}", o):
                db.guardar("ordenes", self.pid, o["orden_id"], o)
        for r in reclamos:
            if self._cambio(f"rec:{r['reclamo_id']}", r):
                db.guardar("reclamos", self.pid, r["reclamo_id"], r)
        self._subir_auditoria()

    def _subir_auditoria(self) -> None:
        ruta = self.motor.ruta_auditoria
        if not os.path.exists(ruta):
            return
        with open(ruta, encoding="utf-8") as f:
            f.seek(self._aud_offset)
            for linea in f:
                if linea.strip():
                    db.agregar_auditoria(self.pid, json.loads(linea))
            self._aud_offset = f.tell()

    # --- base -> motor ------------------------------------------------------------------------

    def traer(self) -> None:
        m = self.motor
        for p in db.pedidos_para_despachar(self.pid):
            local = m.pedidos.get(p["pedido_id"])
            if local is None:
                continue
            m.aplicar_decision(p["pedido_id"], "aprobado", p["juez_id"], p.get("decidido_min"))
            db.marcar_despachado(self.pid, p["pedido_id"])
        for p in db.listar("pedidos", self.pid, estado="rechazado"):
            if p["pedido_id"] not in self._rechazos_vistos:
                self._rechazos_vistos.add(p["pedido_id"])
                m.aplicar_decision(p["pedido_id"], "rechazado", p["juez_id"], p.get("decidido_min"),
                                   p.get("motivo_rechazo"))
        for s in db.solicitudes_pendientes(self.pid):
            datos = s["datos"] or {}
            try:
                if s["tipo"] == "asumir_turno":
                    resultado = {"ratificadas": m.despacho.ratificar(datos.get("juez_id"))}
                elif s["tipo"] == "levantar":
                    resultado = m.levantar_por_reclamo(datos.get("reclamo_id"), datos.get("juez_id"),
                                                       datos.get("motivo", ""), bool(datos.get("reemplazar", True)))
                else:
                    resultado = {"error": f"Solicitud desconocida: {s['tipo']}"}
            except Exception as e:  # una solicitud mala no frena el partido; queda resuelta con el error
                resultado = {"error": str(e)}
            db.resolver_solicitud(self.pid, s["solicitud_id"], resultado)

    def decidir_en_base(self, pedido_id: str, estado: str, juez_id: str, juzgado_id: str, minuto: float,
                        motivo: Optional[str] = None) -> bool:
        """Para el juez automático o la API local: decide en la base como lo haría la web."""
        return db.decidir_pedido(self.pid, pedido_id, estado, juez_id, juzgado_id, minuto, motivo)
