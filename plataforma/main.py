"""Plataforma completa en una notebook: motor + API + pantalla del juez.

    python -m plataforma.main --sim http://localhost:8080                      # aprueba un juez desde /juez
    python -m plataforma.main --sim http://localhost:8080 --juez-automatico    # solo para pruebas aceleradas
    python -m plataforma.main --sim URL --exportar-entrega                     # al cerrar, copia a entrega/

La pantalla del juez queda en http://localhost:8000/juez/. Se entra con el usuario (COORD_USUARIO, por defecto
"coordinacion") y la contraseña (COORD_PASSWORD; si no está, se genera al azar y se imprime al arrancar). Con --red escucha en toda la red local (para entrar desde el celular por wifi).
"""
import argparse
import os
import secrets
import sys
import threading
from pathlib import Path

import uvicorn

from plataforma.motor.api import crear_app
from plataforma.motor.motor import RAIZ, Motor


def main() -> int:
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Plataforma federal de órdenes de bloqueo en vivo")
    p.add_argument("--sim", default="http://localhost:8080", help="dirección del simulador")
    p.add_argument("--juez-automatico", action="store_true", help="aprueba solo (SOLO para pruebas)")
    p.add_argument("--puerto", type=int, default=8000)
    p.add_argument("--sin-web", action="store_true", help="solo el motor, sin API ni pantalla")
    p.add_argument("--base", action="store_true",
                   help="sincronizar con la base de T11 (DATABASE_URL) para que decida la web de Vercel")
    p.add_argument("--red", action="store_true",
                   help="escuchar en toda la red local (para el celular del juez); por defecto solo esta máquina")
    p.add_argument("--exportar-entrega", action="store_true", help="al cerrar, copia expediente y auditoría a entrega/")
    args = p.parse_args()

    if args.base and not os.environ.get("DATABASE_URL"):
        print("--base necesita DATABASE_URL (postgres://... de Neon, o sqlite:///salida/plataforma.db).", file=sys.stderr)
        return 2
    motor = Motor(args.sim, juez_automatico=args.juez_automatico, con_base=args.base)
    if args.base:
        print(f"Escribiendo en la base como partido {motor.partido_db_id}: la web de Vercel lo muestra y decide ahí.",
              flush=True)
    print(f"Motor conectado a {args.sim}: {motor.partido['nombre']} (corrida {motor.corrida})", flush=True)
    if args.juez_automatico:
        print("ATENCIÓN: juez automático encendido. Solo para pruebas; en el partido final va apagado.", flush=True)

    hilo = threading.Thread(target=motor.correr, daemon=True)
    hilo.start()
    if args.sin_web:
        hilo.join()
    else:
        # Login simple (decisión 43). Sin contraseña fija: o la define la coordinación en COORD_PASSWORD, o se genera.
        pwd = os.environ.get("COORD_PASSWORD") or os.environ.get("JUEZ_PIN") or secrets.token_urlsafe(9)
        os.environ["COORD_PASSWORD"] = pwd
        os.environ.setdefault("SESION_SECRET", secrets.token_urlsafe(32))   # sesiones válidas solo en esta corrida
        usuario = (os.environ.get("COORD_USUARIO") or "coordinacion").strip().lower()
        if args.red and len(pwd) < 8:
            print("Con --red la contraseña tiene que tener al menos 8 caracteres (COORD_PASSWORD).", file=sys.stderr)
            return 2
        host = "0.0.0.0" if args.red else "127.0.0.1"
        print(f"Pantalla del juez: http://localhost:{args.puerto}/juez/  (usuario: {usuario}, contraseña: {pwd})", flush=True)
        if args.red:
            print("Escuchando en toda la red local para que el juez entre desde el celular por wifi.", flush=True)
        servidor = uvicorn.Server(uvicorn.Config(crear_app(motor), host=host, port=args.puerto, log_level="warning"))
        threading.Thread(target=servidor.run, daemon=True).start()
        hilo.join()
        servidor.should_exit = True
    if args.exportar_entrega:
        carpeta = motor.exportar_entrega(RAIZ / "entrega")
        print(f"Expediente y auditoría copiados a {carpeta}. Sumá ahí la salida de evaluacion/verificar.py.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
