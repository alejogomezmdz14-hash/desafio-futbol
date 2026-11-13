---
id: T04
titulo: Pantalla del juez (web para celular)
carpeta: plataforma/web/
estado: hecha
dueno: alejo
desde: 2026-11-13 11:50
creada_por: alejo
depende_de: T00
---
## Qué hay que hacer
- Página mobile-first servida por la app FastAPI de Vercel (T11). Pide el PIN de juez una vez y lo manda en X-Juez-Pin.
- Lista de pedidos pendientes, cada uno con el resumen del expediente en lenguaje claro: por qué es el partido, qué servidor, si la IP es compartida, qué se bloquea y hasta cuándo.
- Botón Aprobar todos y aprobar o rechazar de a uno. Muestra quién está de turno.
- Se actualiza sola (polling o SSE) y avisa cuando entra un pedido nuevo.

## Terminada cuando
Desde un celular, con la URL pública de Vercel, se aprueba un lote en un toque y se ve el estado de las órdenes.
