"""API del motor (contratos.md §5) + pantalla del juez en /juez y registro público en /api/publico.

Mismas rutas y formas que la app de T11 en Vercel: la web del juez (plataforma/web) funciona igual contra las dos.
"""
import hmac
import time
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from plataforma.motor.motor import Motor

WEB = Path(__file__).resolve().parents[1] / "web"


def crear_app(motor: Motor, pin: str) -> FastAPI:
    """`pin` es obligatorio: sin PIN no se puede decidir nada (falla cerrado)."""
    if not pin:
        raise RuntimeError("Falta el PIN del juez (JUEZ_PIN)")
    app = FastAPI(title="Plataforma federal de órdenes de bloqueo en vivo")
    fallos: dict = {}            # ip -> (intentos fallidos, bloqueado_hasta)
    MAX_FALLOS, BLOQUEO_S = 5, 300

    def exigir_pin(request: Request, x_juez_pin: Optional[str] = Header(default=None)) -> None:
        ip = request.client.host if request.client else "?"
        n, hasta = fallos.get(ip, (0, 0.0))
        if time.monotonic() < hasta:
            raise HTTPException(429, "Demasiados intentos con PIN incorrecto. Esperá 5 minutos.")
        if not x_juez_pin or not hmac.compare_digest(x_juez_pin.encode(), pin.encode()):
            n += 1
            fallos[ip] = (0, time.monotonic() + BLOQUEO_S) if n >= MAX_FALLOS else (n, 0.0)
            raise HTTPException(status_code=401, detail="PIN inválido o ausente")
        fallos.pop(ip, None)

    @app.exception_handler(HTTPException)
    async def _error(_, exc: HTTPException):
        return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})

    @app.get("/api/estado")
    def estado():
        return motor.estado_api()

    @app.get("/api/pedidos")
    def pedidos(estado: Optional[str] = None):
        return {"pedidos": motor.pedidos_api(estado)}

    @app.get("/api/expedientes/{expediente_id}")
    def expediente(expediente_id: str):
        exp = motor.expedientes.get(expediente_id)
        if exp is None:
            raise HTTPException(404, f"No existe el expediente {expediente_id}")
        return exp

    @app.post("/api/pin/verificar", dependencies=[Depends(exigir_pin)])
    def verificar_pin():
        return {"ok": True}

    @app.post("/api/pedidos/aprobar", dependencies=[Depends(exigir_pin)])
    def aprobar(cuerpo: dict):
        r = motor.decidir(cuerpo.get("pedido_ids", []), cuerpo.get("juez_id"), "aprobado")
        return {"aprobados": r["hechos"], "errores": r["errores"], "decidido_min": r["decidido_min"]}

    @app.post("/api/pedidos/rechazar", dependencies=[Depends(exigir_pin)])
    def rechazar(cuerpo: dict):
        motivo = (cuerpo.get("motivo") or "").strip()
        if not motivo:
            raise HTTPException(422, "Rechazar requiere un motivo")
        r = motor.decidir(cuerpo.get("pedido_ids", []), cuerpo.get("juez_id"), "rechazado", motivo)
        return {"rechazados": r["hechos"], "errores": r["errores"], "decidido_min": r["decidido_min"]}

    @app.post("/api/turno/asumir", dependencies=[Depends(exigir_pin)])
    def asumir(cuerpo: dict):
        try:
            ratificadas = motor.despacho.ratificar(cuerpo.get("juez_id"))
        except PermissionError as e:
            raise HTTPException(409, str(e))
        return {"juez_id": cuerpo.get("juez_id"), "ratificadas": ratificadas, "decidido_min": motor.minuto}

    @app.get("/api/ordenes")
    def ordenes():
        return {"ordenes": motor.despacho.vista()}

    @app.get("/api/auditoria")
    def auditoria():
        import json
        with open(motor.ruta_auditoria, encoding="utf-8") as f:
            return {"eventos": [json.loads(l) for l in f if l.strip()]}

    @app.get("/api/publico")
    def publico():
        return {"entradas": motor.publico_api()}

    @app.get("/")
    def raiz():
        return RedirectResponse("/juez/")

    app.mount("/juez", StaticFiles(directory=WEB, html=True), name="juez")
    return app
