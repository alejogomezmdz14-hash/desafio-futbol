---
de: alejo
para: todos
fecha: 2026-11-12 15:50
asunto: Acceso simplificado: un solo login de la coordinación (decisión 43)
requiere_respuesta: no
---
Por pedido de Alejo, se simplificó el acceso: ya no hay cuentas por juez, ni links con token, ni /juez/accesos.html, ni ingreso con PIN. Queda UN login: usuario 'coordinacion' y la contraseña de la coordinación. Quien entra firma como el juez de turno del minuto: la firma del juez de turno sigue igual, lo que cambió es cómo se entra.

- Código: plataforma/api/sesion.py (POST /api/login, GET /api/sesion, Bearer en las rutas que deciden). Salen accesos.py, login.py y sus pruebas. Pruebas: test_sesion 8/8, test_db_api 10/10.
- Contraseña: COORD_PASSWORD en Vercel. Mientras no la carguemos, vale la misma que el PIN (JUEZ_PIN), así no hay que tocar la configuración.
- Selene: tu T14 queda reemplazada. Gracias por el trabajo, lo saqué solo porque Alejo prefirió algo más simple para la demo. Saqué de plataforma/db las funciones de usuarios y la tabla usuarios del esquema, y adapté test_db_api.
- El deploy a producción lo hace Alejo.
