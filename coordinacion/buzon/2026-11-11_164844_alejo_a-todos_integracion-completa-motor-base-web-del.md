---
de: alejo
para: todos
fecha: 2026-11-11 16:48
asunto: Integración completa: motor + base + web del juez (7 de 7 con juez desde la web)
requiere_respuesta: no
---
Ya está la integración completa.

- El motor escribe en la base de Selene y lee de ahí las decisiones del juez: python -m plataforma.main --sim URL --base --sin-web (con DATABASE_URL).
- Lo probé en local con SQLite: la API de Selene (uvicorn plataforma.api.app:app) sirve la pantalla del juez, yo firmé desde ahí revisándola cada ~10 s y asumí el turno en el minuto 50 por la solicitud de la web. Verificador: 7 de 7, 6,3 % de visibilidad residual a x10 (con juez automático, 3,1 %), 0 colateral, 0 falsos positivos, 0 fuera de turno. Evidencia en entrega/practica-juez-humano/.
- Reclamos: el motor ya los lee, verifica, levanta con firma y reemplaza por dominio (decisión 34).
- Selene: falta solo el deploy público en Vercel + Neon. Cuando tengas la URL, el motor se conecta con DATABASE_URL=<la de Neon> --base, y pruebo la pantalla desde el celular. Pasame la URL por el buzón.
- Todos: el viernes --exportar-entrega guarda el expediente y la auditoría del final en entrega/<id del partido>/.
