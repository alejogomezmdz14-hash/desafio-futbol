"""Pruebas unitarias de la capa de datos plataforma/db/ y la API plataforma/api/app.py (T11).

Uso:
    PYTHONUTF8=1 python -m plataforma.db.test_db_api
"""
import os
import tempfile
from pathlib import Path


def correr_pruebas() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        ruta_db = Path(tmp) / "test.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{ruta_db}"
        os.environ["COORD_PASSWORD"] = "clave-de-prueba-4321"
        os.environ["SESION_SECRET"] = "s" * 40

        from fastapi import HTTPException
        from plataforma import db
        from plataforma.api.app import (
            api_aprobar,
            api_asumir_turno,
            api_auditoria,
            api_estado,
            api_expediente,
            api_levantar_reclamo,
            api_ordenes,
            api_pedidos,
            api_publico,
            api_reclamos,
            api_rechazar,
        )
        from plataforma.api.sesion import PedidoLogin, login, sesion
        from plataforma.db.semilla import PARTIDO_DEMO, cargar_semilla

        # 1. Semilla y esquema
        cargar_semilla(PARTIDO_DEMO)
        assert db.partido_actual() == PARTIDO_DEMO
        est = db.estado_partido(PARTIDO_DEMO)
        assert est is not None and est["partido_id"] == PARTIDO_DEMO

        # 2. Endpoints de la API
        datos_est = api_estado()
        assert datos_est["partido_id"] == PARTIDO_DEMO
        assert datos_est["contadores"]["pedidos_pendientes"] == 2

        pedidos = api_pedidos(estado="pendiente")["pedidos"]
        assert len(pedidos) == 2
        assert "resumen" in pedidos[0]
        assert pedidos[0]["resumen"]["host"] == "s1.pelotaya.test"

        exp = api_expediente("EXP-2026-000001")
        assert exp["expediente_id"] == "EXP-2026-000001"

        # Login simple de la coordinación (decisión 43)
        try:
            sesion(None)
            raise AssertionError("Debería fallar sin sesión")
        except HTTPException as exc:
            assert exc.status_code == 401
        tok = login(PedidoLogin(usuario="coordinacion", password="clave-de-prueba-4321"))["token"]
        assert sesion(f"Bearer {tok}")["nombre"] == "Coordinación"

        # Aprobar P-001
        resp_ap = api_aprobar({"pedido_ids": ["P-001"], "juez_id": "jueza-laura-ficticia"})
        assert resp_ap["aprobados"] == ["P-001"]
        assert resp_ap["errores"] == []

        # Verificar atomicidad: volver a aprobar P-001 -> va a errores
        r2 = api_aprobar({"pedido_ids": ["P-001"], "juez_id": "jueza-laura-ficticia"})
        assert r2["aprobados"] == []
        assert len(r2["errores"]) == 1

        # Verificar que el motor lo ve en pedidos_para_despachar y lo marca despachado
        para_desp = db.pedidos_para_despachar(PARTIDO_DEMO)
        assert len(para_desp) == 1 and para_desp[0]["pedido_id"] == "P-001"
        db.marcar_despachado(PARTIDO_DEMO, "P-001")
        assert db.pedidos_para_despachar(PARTIDO_DEMO) == []

        # Rechazar P-002
        r_rec = api_rechazar({"pedido_ids": ["P-002"], "juez_id": "jueza-laura-ficticia", "motivo": "Evidencia insuficiente"})
        assert r_rec["rechazados"] == ["P-002"]

        # Asumir turno y levantar reclamo -> crean solicitudes pendientes
        r_turno = api_asumir_turno({"juez_id": "jueza-laura-ficticia"})
        assert len(r_turno["ratificadas"]) >= 1

        r_lev = api_levantar_reclamo({"reclamo_id": "R-001", "juez_id": "jueza-laura-ficticia", "motivo": "IP compartida", "reemplazar": True})
        assert r_lev["estado"] == "levantado"

        sols = db.solicitudes_pendientes(PARTIDO_DEMO)
        assert len(sols) == 2
        for s in sols:
            db.resolver_solicitud(PARTIDO_DEMO, s["solicitud_id"], {"ok": True})
        assert db.solicitudes_pendientes(PARTIDO_DEMO) == []

        # Ordenes, auditoria, reclamos, publico
        assert len(api_ordenes()["ordenes"]) == 3
        assert len(api_auditoria()["eventos"]) == 4
        assert len(api_reclamos()["reclamos"]) == 1
        assert "entradas" in api_publico()

    print("test_db_api: 10 de 10 pruebas OK")


if __name__ == "__main__":
    correr_pruebas()
