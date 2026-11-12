"""Accesos de jueces por link que vence (T13, decisiones 38 a 40).

Quien coordina (con el PIN) crea un link por juez y por N horas. El juez lo abre y firma; cada firma queda con su
nombre. "Cortar todos los accesos" invalida de golpe todos los links emitidos. Sin usuarios ni contraseñas.

El link lleva un token: base64url(datos) + "." + HMAC-SHA256(clave, base64url(datos)). Los datos son el nombre, el
vencimiento y la "generación" de accesos; si alguien los toca, la firma no coincide. La clave sale de un secreto largo
que solo tiene el servidor (ver _clave): nunca solo del PIN.
"""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from plataforma import db

URL_WEB = "https://desafio-futbol-iota.vercel.app"
HORAS_MAX = 24
AJUSTE_GENERACION = "generacion_accesos"

router = APIRouter()


def _clave() -> bytes:
    """Clave de firma de los links. Nunca sale solo del PIN: quien tiene un link podría probar PINs offline.

    1. SESION_SECRET (al menos 32 caracteres al azar), cargada en Vercel: la opción preferida.
    2. Si no está: se deriva de DATABASE_URL (lleva la contraseña larga y aleatoria de Neon, que solo tiene el
       servidor) junto con el PIN, así cambiar el PIN sigue cortando todos los links.
    3. Sin ninguna de las dos: falla cerrado.
    """
    secreto = os.environ.get("SESION_SECRET", "")
    if len(secreto) >= 32:
        return secreto.encode()
    base, pin = os.environ.get("DATABASE_URL", ""), os.environ.get("JUEZ_PIN", "")
    if base.startswith(("postgres://", "postgresql://")) and pin:
        return hmac.new(hashlib.sha256(base.encode()).digest(), b"accesos-jueces-v2|" + pin.encode(),
                        hashlib.sha256).digest()
    raise HTTPException(status_code=503, detail={"error": "La plataforma no tiene clave para firmar accesos"})


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).decode().rstrip("=")


def _de_b64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _firma(cuerpo: str) -> str:
    return hmac.new(_clave(), cuerpo.encode(), hashlib.sha256).hexdigest()


def generacion() -> int:
    return int(db.leer_ajuste(AJUSTE_GENERACION, "1"))


def crear_token(nombre: str, horas: float) -> Dict[str, Any]:
    vence = int(time.time() + horas * 3600)
    datos = {"n": nombre, "exp": vence, "g": generacion(), "id": secrets.token_hex(4)}
    cuerpo = _b64(json.dumps(datos, ensure_ascii=False, separators=(",", ":")).encode("utf-8"))
    return {"token": f"{cuerpo}.{_firma(cuerpo)}", "nombre": nombre, "vence_epoch": vence}


def validar_token(token: str) -> Dict[str, Any]:
    """Devuelve los datos del acceso o levanta 401 con el motivo, en palabras que entiende un juez."""
    try:
        cuerpo, firma = token.split(".", 1)
    except ValueError:
        raise HTTPException(status_code=401, detail={"error": "El link de acceso no es válido"})
    if not hmac.compare_digest(firma, _firma(cuerpo)):
        raise HTTPException(status_code=401, detail={"error": "El link de acceso no es válido"})
    datos = json.loads(_de_b64(cuerpo))
    if time.time() >= datos["exp"]:
        raise HTTPException(status_code=401, detail={"error": "Tu acceso venció. Pedile un link nuevo a la coordinación."})
    if datos.get("g") != generacion():
        raise HTTPException(status_code=401, detail={"error": "Tu acceso fue cortado. Pedile un link nuevo a la coordinación."})
    return datos


def _pin_ok(x_juez_pin: Optional[str]) -> bool:
    esperado = os.environ.get("JUEZ_PIN", "")
    return bool(esperado and x_juez_pin and hmac.compare_digest(x_juez_pin.encode(), esperado.encode()))


def firmante(x_juez_pin: Optional[str] = Header(default=None),
             authorization: Optional[str] = Header(default=None)) -> Dict[str, str]:
    """Dependencia de las rutas que firman: acepta el link del juez o el PIN de la coordinación."""
    if authorization and authorization.lower().startswith("bearer "):
        datos = validar_token(authorization[7:].strip())
        return {"nombre": datos["n"], "via": "link"}
    if _pin_ok(x_juez_pin):
        return {"nombre": "Coordinación (PIN)", "via": "pin"}
    raise HTTPException(status_code=401, detail={"error": "PIN de juez inválido"})


def solo_pin(x_juez_pin: Optional[str] = Header(default=None)) -> None:
    """Crear y cortar accesos es solo para quien tiene el PIN: un link de juez no alcanza."""
    if not _pin_ok(x_juez_pin):
        raise HTTPException(status_code=401, detail={"error": "Esto requiere el PIN de la coordinación"})


class NuevoAcceso(BaseModel):
    nombre: str
    horas: float = 4


@router.post("/api/accesos", dependencies=[Depends(solo_pin)])
def crear_acceso(pedido: NuevoAcceso):
    nombre = " ".join(pedido.nombre.split())[:60]
    if len(nombre) < 2:
        raise HTTPException(status_code=400, detail={"error": "Poné el nombre del juez"})
    if not 0 < pedido.horas <= HORAS_MAX:
        raise HTTPException(status_code=400, detail={"error": f"La duración tiene que ser de hasta {HORAS_MAX} horas"})
    t = crear_token(nombre, pedido.horas)
    return {"nombre": nombre, "vence_epoch": t["vence_epoch"], "link": f"{URL_WEB}/juez/?t={t['token']}"}


@router.post("/api/accesos/cortar", dependencies=[Depends(solo_pin)])
def cortar_accesos():
    nueva = generacion() + 1
    db.escribir_ajuste(AJUSTE_GENERACION, str(nueva))
    return {"cortados": True, "mensaje": "Todos los links emitidos hasta ahora dejaron de funcionar."}


@router.get("/api/accesos/yo")
def quien_soy(quien: Dict[str, str] = Depends(firmante), authorization: Optional[str] = Header(default=None)):
    vence = None
    if quien["via"] == "link":
        vence = validar_token(authorization[7:].strip())["exp"]
    return {"nombre": quien["nombre"], "via": quien["via"], "vence_epoch": vence}
