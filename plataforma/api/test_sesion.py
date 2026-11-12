"""Pruebas del login simple de la coordinación (decisión 43). Correr desde la raíz del repo:

    python -m plataforma.api.test_sesion
"""
import os
import sys
import tempfile
from pathlib import Path

_tmp = Path(tempfile.mkdtemp())
os.environ["DATABASE_URL"] = f"sqlite:///{(_tmp / 'sesion.db').as_posix()}"
os.environ["SESION_SECRET"] = "x" * 40
os.environ["COORD_USUARIO"] = "coordinacion"
os.environ["COORD_PASSWORD"] = "clave-de-prueba-123"
os.environ.pop("JUEZ_PIN", None)

from fastapi.testclient import TestClient  # noqa: E402

from plataforma import db  # noqa: E402
from plataforma.api import sesion  # noqa: E402
from plataforma.api.app import app  # noqa: E402

db.crear_esquema()
c = TestClient(app)


def login(usuario="coordinacion", password="clave-de-prueba-123"):
    return c.post("/api/login", json={"usuario": usuario, "password": password})


def prueba_login_correcto_da_sesion():
    r = login()
    assert r.status_code == 200, r.text
    tok = r.json()["token"]
    q = c.get("/api/sesion", headers={"Authorization": f"Bearer {tok}"})
    assert q.status_code == 200 and q.json()["nombre"] == "Coordinación", q.text


def prueba_usuario_sin_importar_mayusculas():
    assert login(usuario="  Coordinacion ").status_code == 200


def prueba_contrasena_o_usuario_malos():
    assert login(password="mala").status_code == 401
    assert login(usuario="otro").status_code == 401


def prueba_bloqueo_tras_5_intentos():
    for _ in range(5):
        login(usuario="bloqueado", password="mala")
    r = login(usuario="bloqueado", password="mala")
    assert r.status_code == 429, r.status_code


def prueba_rutas_que_deciden_exigen_sesion():
    cuerpo = {"pedido_ids": ["P-001"], "juez_id": "jueza-laura-ficticia"}
    assert c.post("/api/pedidos/aprobar", json=cuerpo).status_code == 401
    assert c.post("/api/pedidos/aprobar", json=cuerpo, headers={"X-Juez-Pin": "clave-de-prueba-123"}).status_code == 401
    assert c.post("/api/turno/asumir", json={"juez_id": "x"}).status_code == 401
    assert c.post("/api/demo/iniciar", json={}).status_code == 401


def prueba_token_alterado_o_vencido():
    tok = login().json()["token"]
    cuerpo, firma = tok.split(".")
    malo = cuerpo + "." + ("0" if firma[0] != "0" else "1") + firma[1:]
    assert c.get("/api/sesion", headers={"Authorization": f"Bearer {malo}"}).status_code == 401
    vencido = sesion.crear_token("coordinacion", horas=-1)["token"]
    assert c.get("/api/sesion", headers={"Authorization": f"Bearer {vencido}"}).status_code == 401
    assert c.get("/api/sesion", headers={"Authorization": "Bearer basura"}).status_code == 401


def prueba_sin_contrasena_configurada_falla_cerrado():
    guardada = os.environ.pop("COORD_PASSWORD")
    try:
        assert login().status_code == 503
        os.environ["JUEZ_PIN"] = "pin-que-ya-estaba"
        assert login(password="pin-que-ya-estaba").status_code == 200, "sin COORD_PASSWORD se usa JUEZ_PIN"
    finally:
        os.environ["COORD_PASSWORD"] = guardada
        os.environ.pop("JUEZ_PIN", None)


def prueba_rutas_viejas_no_existen():
    for ruta in ("/api/accesos", "/api/auth/login", "/api/usuarios", "/api/pin/verificar"):
        assert c.post(ruta, json={}).status_code in (404, 405), ruta


def main() -> int:
    pruebas = [v for k, v in globals().items() if k.startswith("prueba_")]
    fallas = 0
    for prueba in pruebas:
        try:
            prueba()
            print(f"OK    {prueba.__name__}")
        except AssertionError as e:
            fallas += 1
            print(f"FALLA {prueba.__name__}: {e}")
    print(f"\ntest_sesion: {len(pruebas) - fallas} de {len(pruebas)} pruebas OK")
    return 1 if fallas else 0


if __name__ == "__main__":
    sys.exit(main())
