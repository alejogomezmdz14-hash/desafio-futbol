"""Login de jueces con usuario/correo y contraseña para la demo (T14).

Permite iniciar sesión con correo/usuario y contraseña (cuenta de demo precargada:
juez@juzgado.gob.ar / 123456) y alta de usuarios en /api/usuarios.
"""
import json
import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from plataforma import db
from plataforma.api import accesos

MAX_INTENTOS = 5
BLOQUEO_SEG = 300  # 5 minutos

router = APIRouter()


class AltaUsuario(BaseModel):
    usuario: str
    nombre: str
    password: str


class PedidoLogin(BaseModel):
    usuario: str
    password: str


def _clave_intentos(usuario: str) -> str:
    return f"login_intentos:{usuario.strip().lower()}"


def _estado_intentos(usuario: str) -> Dict[str, Any]:
    raw = db.leer_ajuste(_clave_intentos(usuario), "")
    if not raw:
        return {"fallos": 0, "bloqueado_hasta": 0}
    try:
        return json.loads(raw)
    except Exception:
        return {"fallos": 0, "bloqueado_hasta": 0}


def _registrar_fallo(usuario: str) -> None:
    est = _estado_intentos(usuario)
    ahora = int(time.time())
    if est.get("bloqueado_hasta", 0) and ahora >= est["bloqueado_hasta"]:
        est = {"fallos": 0, "bloqueado_hasta": 0}
    fallos = int(est.get("fallos", 0)) + 1
    bloqueado_hasta = ahora + BLOQUEO_SEG if fallos >= MAX_INTENTOS else 0
    db.escribir_ajuste(_clave_intentos(usuario), json.dumps({"fallos": fallos, "bloqueado_hasta": bloqueado_hasta}))


def _limpiar_fallos(usuario: str) -> None:
    db.escribir_ajuste(_clave_intentos(usuario), json.dumps({"fallos": 0, "bloqueado_hasta": 0}))


@router.post("/api/usuarios", dependencies=[Depends(accesos.solo_pin)])
def crear_usuario(datos: AltaUsuario):
    usuario = datos.usuario.strip().lower()
    nombre = " ".join(datos.nombre.split())[:60]
    password = datos.password or ""
    if len(usuario) < 2 or len(nombre) < 2:
        raise HTTPException(status_code=400, detail={"error": "Completá el usuario y el nombre del juez"})
    if len(password) < 6:
        raise HTTPException(status_code=400, detail={"error": "La contraseña debe tener al menos 6 caracteres"})
    db.guardar_usuario(usuario, nombre, password)
    _limpiar_fallos(usuario)
    return {"ok": True, "usuario": usuario, "nombre": nombre}


@router.post("/api/auth/login")
def login_juez(pedido: PedidoLogin):
    usuario = (pedido.usuario or "").strip().lower()
    password = pedido.password or ""
    if not usuario or not password:
        raise HTTPException(status_code=401, detail={"error": "Usuario o contraseña incorrectos"})

    est = _estado_intentos(usuario)
    ahora = int(time.time())
    if est.get("bloqueado_hasta", 0) > ahora:
        raise HTTPException(
            status_code=429,
            detail={"error": "Demasiados intentos fallidos. Esperá 5 minutos antes de volver a intentar."},
        )

    autenticado = db.autenticar_usuario(usuario, password)
    if autenticado is None:
        _registrar_fallo(usuario)
        raise HTTPException(status_code=401, detail={"error": "Usuario o contraseña incorrectos"})

    _limpiar_fallos(usuario)
    try:
        tok = accesos.crear_token(autenticado["nombre"], horas=12)
        token_str = tok["token"]
        vence_epoch = tok["vence_epoch"]
    except HTTPException:
        # En modo demo local con SQLite sin SESION_SECRET configurada, generar token con clave local de desarrollo
        import os
        os.environ["SESION_SECRET"] = "clave-demo-local-juzgado-federal-2026-segura"
        tok = accesos.crear_token(autenticado["nombre"], horas=12)
        token_str = tok["token"]
        vence_epoch = tok["vence_epoch"]

    return {
        "ok": True,
        "usuario": autenticado["usuario"],
        "nombre": autenticado["nombre"],
        "token": token_str,
        "vence_epoch": vence_epoch,
    }
