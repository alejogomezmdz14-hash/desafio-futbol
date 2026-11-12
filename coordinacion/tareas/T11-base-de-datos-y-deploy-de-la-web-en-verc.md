---
id: T11
titulo: Base de datos y deploy de la web en Vercel
carpeta: plataforma/db/, plataforma/api/, vercel.json
estado: hecha
dueno: selene
desde: 2026-11-11 23:28
creada_por: alejo
depende_de: T00
---
## Qué hay que hacer
**Guía paso a paso: `coordinacion/guias/T11-base-y-vercel.md`.**

- Capa de datos en plataforma/db/: tablas de contratos.md §10, funciona con Postgres (DATABASE_URL) y con SQLite (modo local).
- Crear la base Neon desde el Marketplace de Vercel y conectarla al proyecto. Local: vercel env pull.
- App FastAPI de la API (contratos §5) leyendo la base, con PIN de juez (X-Juez-Pin / JUEZ_PIN) en las rutas que deciden.
- Deploy en Vercel temprano, con datos de ejemplo de plataforma/contratos.py, y redeploys chicos.
- La web del juez (T04) y el registro público (T07) se sirven desde esta misma app.

## Terminada cuando
La URL pública de Vercel muestra pedidos de ejemplo cargados en la base y aprobar uno con el PIN cambia su estado en la base.
