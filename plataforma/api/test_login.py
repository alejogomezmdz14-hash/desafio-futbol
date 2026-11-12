"""Pruebas unitarias del login de jueces con usuario/correo y contraseña (T14).

Uso:
    PYTHONUTF8=1 python -m plataforma.api.test_login
"""
import os
import tempfile
from pathlib import Path


def correr_pruebas() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ruta_db = Path(tmp) / "login_test.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{ruta_db}"
        os.environ["JUEZ_PIN"] = "123456"
        os.environ["SESION_SECRET"] = "clave-de-prueba-larga-0123456789abcdef"

        from fastapi import HTTPException
        from plataforma import db
        from plataforma.api import accesos
        from plataforma.api.app import api_aprobar
        from plataforma.api.login import AltaUsuario, PedidoLogin, crear_usuario, login_juez
        from plataforma.db.semilla import PARTIDO_DEMO, cargar_semilla

        cargar_semilla(PARTIDO_DEMO)
        db.asegurar_usuarios_demo()

        # 1. Login directo con cuenta de demo precargada (correo + 123456)
        r_demo = login_juez(PedidoLogin(usuario="juez@juzgado.gob.ar", password="123456"))
        assert r_demo["ok"] is True
        assert r_demo["nombre"] == "Dra. Laura Ficticia"
        assert "." in r_demo["token"]

        # 2. Alta de usuario sin PIN falla con 401; con PIN funciona
        try:
            accesos.solo_pin(None)
            raise AssertionError("Debería fallar sin PIN")
        except HTTPException as exc:
            assert exc.status_code == 401

        accesos.solo_pin("123456")
        alta = crear_usuario(AltaUsuario(usuario="juez.prueba@pjn.gob.ar", nombre="Dr. Juez Prueba", password="123456"))
        assert alta["ok"] is True

        # 3. Login bueno y malo (mismo 401 para inexistente o clave mala)
        r_ok = login_juez(PedidoLogin(usuario="juez.prueba@pjn.gob.ar", password="123456"))
        assert r_ok["nombre"] == "Dr. Juez Prueba"

        try:
            login_juez(PedidoLogin(usuario="noexiste@pjn.gob.ar", password="123456"))
            raise AssertionError("Debería fallar usuario inexistente")
        except HTTPException as e1:
            assert e1.status_code == 401
            err1 = e1.detail

        try:
            login_juez(PedidoLogin(usuario="juez.prueba@pjn.gob.ar", password="mal-password"))
            raise AssertionError("Debería fallar clave mala")
        except HTTPException as e2:
            assert e2.status_code == 401
            err2 = e2.detail

        assert err1 == err2

        # 4. El acceso de login permite firmar un pedido y registra el nombre del juez en firmas
        quien = accesos.firmante(x_juez_pin=None, authorization=f"Bearer {r_ok['token']}")
        assert quien["nombre"] == "Dr. Juez Prueba"
        res_firma = api_aprobar(
            {"pedido_ids": ["P-001"], "juez_id": "jueza-laura-ficticia"},
            partido_id=PARTIDO_DEMO,
            quien=quien,
        )
        assert res_firma["aprobados"] == ["P-001"]
        assert (db.firmante(PARTIDO_DEMO, "P-001") or {}).get("firmado_por") == "Dr. Juez Prueba"

        # 5. Freno de fuerza bruta: 5 intentos fallidos bloquean al usuario por 5 minutos (429)
        for _ in range(5):
            try:
                login_juez(PedidoLogin(usuario="bloqueo@pjn.gob.ar", password="mal"))
            except HTTPException as exc:
                assert exc.status_code == 401
        try:
            login_juez(PedidoLogin(usuario="bloqueo@pjn.gob.ar", password="mal"))
            raise AssertionError("El 6to intento debería estar bloqueado con 429")
        except HTTPException as exc:
            assert exc.status_code == 429

        # 6. Cortar todos los accesos también invalida la sesión actual
        accesos.cortar_accesos()
        try:
            accesos.firmante(x_juez_pin=None, authorization=f"Bearer {r_ok['token']}")
            raise AssertionError("Debería haberse invalidado tras cortar accesos")
        except HTTPException as exc:
            assert exc.status_code == 401

    print("test_login: 6 de 6 pruebas OK")


if __name__ == "__main__":
    correr_pruebas()
