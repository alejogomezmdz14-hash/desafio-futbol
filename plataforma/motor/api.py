"""API del motor (contratos.md §5) + pantalla del juez en /juez y registro público en /api/publico.

Mismas rutas y formas que la app de T11 en Vercel: la web del juez (plataforma/web) funciona igual contra las dos.
"""
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

from plataforma.api.sesion import router as router_sesion, sesion
from plataforma.motor.motor import Motor

WEB = Path(__file__).resolve().parents[1] / "web"


def crear_app(motor: Motor) -> FastAPI:
    """Mismo login simple que en Vercel (plataforma/api/sesion.py): COORD_USUARIO, COORD_PASSWORD y SESION_SECRET."""
    app = FastAPI(title="Plataforma federal de órdenes de bloqueo en vivo")
    app.include_router(router_sesion)

    @app.exception_handler(HTTPException)
    async def _error(_, exc: HTTPException):
        detalle = exc.detail
        return JSONResponse(status_code=exc.status_code,
                            content=detalle if isinstance(detalle, dict) and "error" in detalle else {"error": detalle})

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

    @app.post("/api/pedidos/aprobar", dependencies=[Depends(sesion)])
    def aprobar(cuerpo: dict):
        r = motor.decidir(cuerpo.get("pedido_ids", []), cuerpo.get("juez_id"), "aprobado")
        return {"aprobados": r["hechos"], "errores": r["errores"], "decidido_min": r["decidido_min"]}

    @app.post("/api/pedidos/rechazar", dependencies=[Depends(sesion)])
    def rechazar(cuerpo: dict):
        motivo = (cuerpo.get("motivo") or "").strip()
        if not motivo:
            raise HTTPException(422, "Rechazar requiere un motivo")
        r = motor.decidir(cuerpo.get("pedido_ids", []), cuerpo.get("juez_id"), "rechazado", motivo)
        return {"rechazados": r["hechos"], "errores": r["errores"], "decidido_min": r["decidido_min"]}

    @app.post("/api/turno/asumir", dependencies=[Depends(sesion)])
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
