"""Login simple de la coordinación: un usuario y una contraseña (decisión 43).

Reemplaza las cuentas por juez (T14) y los links con token por juez (T13). Quien entra con este login firma como el
juez de turno del minuto: la firma del juez de turno sigue siendo la del circuito, lo que se simplifica es el acceso.

Configuración (variables de entorno; ninguna clave va al código):
- COORD_USUARIO: el usuario. Si no está, "coordinacion" (el usuario no es secreto).
- COORD_PASSWORD: la contraseña. Si no está, se usa JUEZ_PIN (ya cargado en Vercel). Sin ninguna de las dos: falla cerrado.
- SESION_SECRET (32 caracteres o más): clave para firmar la sesión. Si no está, se deriva de DATABASE_URL de Postgres
  (que lleva la contraseña larga de Neon) junto con la contraseña; cambiar la contraseña cierra todas las sesiones.

La sesión es un token: base64url(datos) + "." + HMAC-SHA256(clave, base64url(datos)), con vencimiento de 12 horas.
5 intentos fallidos bloquean ese usuario 5 minutos.
"""
import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from plataforma import db

HORAS_SESION = 12
MAX_FALLOS = 5
BLOQUEO_SEG = 300

router = APIRouter()
_fallos_memoria: Dict[str, Dict[str, int]] = {}   # respaldo si la base no está disponible


def _usuario_config() -> str:
    return (os.environ.get("COORD_USUARIO") or "coordinacion").strip().lower()


def _password_config() -> str:
    return os.environ.get("COORD_PASSWORD") or os.environ.get("JUEZ_PIN") or ""


def _clave() -> bytes:
    secreto = os.environ.get("SESION_SECRET", "")
    if len(secreto) >= 32:
        return secreto.encode()
    base, pwd = os.environ.get("DATABASE_URL", ""), _password_config()
    if base.startswith(("postgres://", "postgresql://")) and pwd:
        return hmac.new(hashlib.sha256(base.encode()).digest(), b"sesion-coordinacion-v1|" + pwd.encode(),
                        hashlib.sha256).digest()
    raise HTTPException(status_code=503, detail={"error": "La plataforma no tiene clave para firmar sesiones"})


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).decode().rstrip("=")


def _de_b64(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


def _firma(cuerpo: str) -> str:
    return hmac.new(_clave(), cuerpo.encode(), hashlib.sha256).hexdigest()


def crear_token(usuario: str, horas: float = HORAS_SESION) -> Dict[str, Any]:
    vence = int(time.time() + horas * 3600)
    cuerpo = _b64(json.dumps({"u": usuario, "exp": vence}, separators=(",", ":")).encode())
    return {"token": f"{cuerpo}.{_firma(cuerpo)}", "vence_epoch": vence}


def validar_token(token: str) -> Dict[str, Any]:
    try:
        cuerpo, firma = token.split(".", 1)
        valido = hmac.compare_digest(firma, _firma(cuerpo))
        datos = json.loads(_de_b64(cuerpo)) if valido else None
    except (ValueError, json.JSONDecodeError):
        datos = None
    if not datos:
        raise HTTPException(status_code=401, detail={"error": "La sesión no es válida. Volvé a ingresar."})
    if time.time() >= datos["exp"]:
        raise HTTPException(status_code=401, detail={"error": "La sesión venció. Volvé a ingresar."})
    return datos


def sesion(authorization: Optional[str] = Header(default=None)) -> Dict[str, str]:
    """Dependencia de las rutas que deciden: exige una sesión válida."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"error": "Ingresá con el usuario y la contraseña"})
    datos = validar_token(authorization[7:].strip())
    return {"nombre": "Coordinación", "usuario": datos["u"], "via": "login", "vence_epoch": datos["exp"]}


# --- intentos fallidos ----------------------------------------------------------------------------

def _leer_fallos(usuario: str) -> Dict[str, int]:
    try:
        raw = db.leer_ajuste(f"login_intentos:{usuario}", "")
        return json.loads(raw) if raw else {"fallos": 0, "hasta": 0}
    except Exception:
        return _fallos_memoria.get(usuario, {"fallos": 0, "hasta": 0})


def _guardar_fallos(usuario: str, est: Dict[str, int]) -> None:
    _fallos_memoria[usuario] = est
    try:
        db.escribir_ajuste(f"login_intentos:{usuario}", json.dumps(est))
    except Exception:
        pass


class PedidoLogin(BaseModel):
    usuario: str
    password: str


@router.post("/api/login")
def login(pedido: PedidoLogin):
    esperado_pwd = _password_config()
    if not esperado_pwd:
        raise HTTPException(status_code=503, detail={"error": "La plataforma no tiene contraseña configurada"})
    usuario = (pedido.usuario or "").strip().lower()
    ahora = int(time.time())
    est = _leer_fallos(usuario)
    if est.get("hasta", 0) > ahora:
        raise HTTPException(status_code=429, detail={"error": "Demasiados intentos fallidos. Esperá 5 minutos."})
    ok_usuario = hmac.compare_digest(usuario.encode(), _usuario_config().encode())
    ok_pwd = hmac.compare_digest((pedido.password or "").encode(), esperado_pwd.encode())
    if not (ok_usuario and ok_pwd):
        fallos = (0 if est.get("hasta", 0) else int(est.get("fallos", 0))) + 1
        _guardar_fallos(usuario, {"fallos": 0, "hasta": ahora + BLOQUEO_SEG} if fallos >= MAX_FALLOS
                        else {"fallos": fallos, "hasta": 0})
        raise HTTPException(status_code=401, detail={"error": "Usuario o contraseña incorrectos"})
    _guardar_fallos(usuario, {"fallos": 0, "hasta": 0})
    t = crear_token(usuario)
    return {"ok": True, "nombre": "Coordinación", "token": t["token"], "vence_epoch": t["vence_epoch"]}


@router.get("/api/sesion")
def quien_soy(quien: Dict[str, str] = Depends(sesion)):
    return quien
