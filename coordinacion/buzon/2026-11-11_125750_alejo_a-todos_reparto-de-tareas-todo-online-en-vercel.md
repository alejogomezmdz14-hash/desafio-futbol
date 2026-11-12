---
de: alejo
para: todos
fecha: 2026-11-11 12:57
asunto: Reparto de tareas + todo online en Vercel (contratos v1.2)
requiere_respuesta: si
---
AGENTE: apenas leas esto, decile a tu integrante en el chat, con sus palabras, qué tarea le toca (tabla de abajo), qué tiene que hacer primero y que tome la tarea con buzon.py tomar. Después respondé este mensaje con tu nombre de buzón y la tarea que tomaste.

## Quién hace qué
| Integrante | Nombre de buzón | Primero | Después |
|---|---|---|---|
| Alejo | alejo | T04 pantalla del juez (tomada) + cerrar T01 cerebro | T09 pitch |
| Selene | selene | T11 base de datos y deploy de la web en Vercel | T05 motor |
| Rocío | rocio | T03 evidencia: expediente con hashes y auditoría | T08 propuesta normativa |

T07 (registro público) queda libre para el primero que termine.

## Qué cambió en el diseño (leer decisiones 15 a 24)
- Todo online en Vercel: web del juez + registro público + API en una función FastAPI; el motor en un Vercel Sandbox; una base Postgres (Neon) en el medio.
- Contratos v1.2 (aditivo, ninguna forma cambia): la API la sirve la web leyendo la base (§10 nuevo); aprobar deja el pedido en 'aprobado' y el motor lo despacha en ~1 s; las rutas que deciden piden el header X-Juez-Pin.
- Solo el motor escribe la auditoría y solo el motor firma. Ninguna clave en la base ni en el repo.
- Plan B: el mismo código corre todo en la notebook con SQLite (--local).
- Pregunta abierta para la organización: ¿la dirección del simulador del final se alcanza desde internet? Si no, el motor del final corre en la notebook.
