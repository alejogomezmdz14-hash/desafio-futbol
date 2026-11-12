---
de: selene
para: alejo,todos
fecha: 2026-11-12 00:40
asunto: Login y registro de usuarios en DB/API — esperando confirmación
requiere_respuesta: si
---
**Archivos a modificar (plataforma/db/ y plataforma/api/):**
- plataforma/db/esquema.sql y plataforma/db/__init__.py: agregar tabla usuarios (usuario_id, nombre, password_hash, rol, juez_id, juzgado_id, creado_ts), compatible con Postgres y SQLite.
- plataforma/db/semilla.py: pre-cargar las cuentas de los jueces del simulador (jueza-laura-ficticia y juez-martin-ejemplo).
- plataforma/api/app.py: sumar los endpoints POST /api/auth/login y POST /api/auth/registro.

**Integración con la arquitectura actual:**
- Cada cuenta de juez queda vinculada a su juez_id y juzgado_id oficiales del simulador, manteniendo intacto el flujo de firmas y la validación de turnos.
- El alta en /api/auth/registro solicita JUEZ_PIN como código de habilitación judicial y almacena la contraseña hasheada (scrypt/pbkdf2).
- Compatibilidad total: los endpoints de decisión (/api/pedidos/aprobar, rechazar, turno/asumir, reclamos/levantar) aceptan tanto el token de sesión del login como X-Juez-Pin, sin afectar al motor ni a las pruebas actuales.
- En el frontend (plataforma/web/), solo requeriría conectar el formulario de ingreso a /api/auth/login y /api/auth/registro.
