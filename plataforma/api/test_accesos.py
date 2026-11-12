"""Pruebas de los accesos por link que vence (T13). Uso: python -m plataforma.api.test_accesos"""
import os
import sys
import tempfile
import time
from pathlib import Path

_tmp = Path(tempfile.mkdtemp()) / "accesos.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.as_posix()}"
os.environ["JUEZ_PIN"] = "pin-de-prueba-123"
os.environ["SESION_SECRET"] = "clave-de-prueba-larga-0123456789abcdef"

from fastapi.testclient import TestClient  # noqa: E402

from plataforma import db  # noqa: E402
from plataforma.api import accesos  # noqa: E402
from plataforma.api.app import app  # noqa: E402
from plataforma.contratos import EJEMPLO_API_ESTADO, EJEMPLO_PEDIDO_PENDIENTE  # noqa: E402

PIN = {"X-Juez-Pin": "pin-de-prueba-123"}
resultados = []


def prueba(nombre, condicion):
    resultados.append(bool(condicion))
    print(("OK   " if condicion else "FALLA") + " " + nombre)


def con_link(link):
    return {"Authorization": "Bearer " + link.split("?t=", 1)[1]}


with TestClient(app) as c:
    pid = "prueba-accesos"
    db.guardar_estado_partido(pid, dict(EJEMPLO_API_ESTADO, partido_id=pid))
    for n in ("P-901", "P-902", "P-903"):
        db.guardar("pedidos", pid, n, dict(EJEMPLO_PEDIDO_PENDIENTE, pedido_id=n), estado="pendiente")
    juez = EJEMPLO_API_ESTADO["jueces_de_turno"][0]

    r = c.post("/api/accesos", json={"nombre": "Dra. Prueba", "horas": 2})
    prueba("crear un acceso sin PIN da 401", r.status_code == 401)
    r = c.post("/api/accesos", json={"nombre": "Dra. Prueba", "horas": 2}, headers=PIN)
    prueba("crear un acceso con PIN da 200 y un link", r.status_code == 200 and "?t=" in r.json()["link"])
    link = r.json()["link"]

    r = c.post("/api/accesos", json={"nombre": "Otro", "horas": 2}, headers=con_link(link))
    prueba("con un link no se pueden crear otros accesos", r.status_code == 401)
    r = c.post("/api/accesos", json={"nombre": "X", "horas": 100}, headers=PIN)
    prueba("no se puede crear un acceso de más de 24 horas", r.status_code == 400)

    r = c.get("/api/accesos/yo", headers=con_link(link))
    prueba("el link dice de quién es y cuándo vence", r.json().get("nombre") == "Dra. Prueba" and r.json().get("vence_epoch"))

    r = c.post(f"/api/pedidos/aprobar?partido_id={pid}", json={"pedido_ids": ["P-901"], "juez_id": juez}, headers=con_link(link))
    prueba("con el link se firma un pedido", r.status_code == 200 and r.json()["aprobados"] == ["P-901"])
    prueba("la firma queda con el nombre del juez", (db.firmante(pid, "P-901") or {}).get("firmado_por") == "Dra. Prueba")

    token = link.split("?t=", 1)[1]
    cuerpo, firma = token.split(".")
    alterado = cuerpo[:-2] + ("AA" if cuerpo[-2:] != "AA" else "BB") + "." + firma
    r = c.post(f"/api/pedidos/aprobar?partido_id={pid}", json={"pedido_ids": ["P-902"], "juez_id": juez},
               headers={"Authorization": "Bearer " + alterado})
    prueba("un link alterado no firma", r.status_code == 401)

    vencido = accesos.crear_token("Dr. Vencido", horas=1 / 3600)["token"]
    time.sleep(1.5)
    r = c.post(f"/api/pedidos/aprobar?partido_id={pid}", json={"pedido_ids": ["P-902"], "juez_id": juez},
               headers={"Authorization": "Bearer " + vencido})
    prueba("un link vencido no firma y explica que venció", r.status_code == 401 and "venció" in r.json()["error"])

    r = c.post("/api/accesos/cortar", headers=PIN)
    prueba("cortar todos los accesos con PIN da 200", r.status_code == 200)
    r = c.post(f"/api/pedidos/aprobar?partido_id={pid}", json={"pedido_ids": ["P-902"], "juez_id": juez}, headers=con_link(link))
    prueba("después de cortar, el link viejo no firma y explica que fue cortado",
           r.status_code == 401 and "cortado" in r.json()["error"])
    nuevo = c.post("/api/accesos", json={"nombre": "Dra. Nueva", "horas": 1}, headers=PIN).json()["link"]
    r = c.post(f"/api/pedidos/aprobar?partido_id={pid}", json={"pedido_ids": ["P-902"], "juez_id": juez}, headers=con_link(nuevo))
    prueba("un link creado después de cortar funciona", r.status_code == 200 and r.json()["aprobados"] == ["P-902"])

    r = c.post(f"/api/pedidos/aprobar?partido_id={pid}", json={"pedido_ids": ["P-903"], "juez_id": juez}, headers=PIN)
    prueba("el PIN sigue firmando como respaldo", r.status_code == 200 and
           (db.firmante(pid, "P-903") or {}).get("firmado_por") == "Coordinación (PIN)")

    secreto = os.environ.pop("SESION_SECRET")
    r = c.post("/api/accesos", json={"nombre": "Sin clave", "horas": 1}, headers=PIN)
    prueba("sin un secreto largo (solo PIN y SQLite) no se crean links: falla cerrado", r.status_code == 503)
    os.environ["SESION_SECRET"] = "corta"
    r = c.post("/api/accesos", json={"nombre": "Clave corta", "horas": 1}, headers=PIN)
    prueba("una SESION_SECRET corta no se acepta", r.status_code == 503)
    os.environ["SESION_SECRET"] = secreto

ok = sum(resultados)
print(f"\ntest_accesos: {ok} de {len(resultados)} pruebas OK")
sys.exit(0 if ok == len(resultados) else 1)
