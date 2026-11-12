---
de: alejo
para: selene
fecha: 2026-11-12 11:42
asunto: Login con token que vence (T13): confirmado, con especificación
requiere_respuesta: si
---
AGENTE: pasale esto a Selene en el chat.

Selene: confirmado el login, con un cambio importante. Alejo quiere poder **darle a alguien (el jurado, un juez) un token que dure un tiempo determinado** y que venza solo. Tomá la tarea T13 (te la creo ahora). Decisiones 38 y 39.

## Qué hay que hacer
1. **Tabla `usuarios`** como propusiste (usuario_id, nombre, password_hash, rol, creado_ts). Hash con `hashlib.scrypt` (librería estándar). Semilla: un usuario por juez del simulador. Las contraseñas de la semilla salen de una variable de entorno, nunca del repo.
2. **Tokens firmados que vencen** (sin tabla de sesiones; las funciones de Vercel no tienen memoria):
   - Formato: `base64url(json)` + "." + `hmac_sha256(SESION_SECRET, eso)`. El json lleva `sub` (usuario), `rol`, `exp` (epoch) y `jti` (al azar).
   - `SESION_SECRET` va en las variables de Vercel (pedile a Alejo que la cargue, o cargala con `vercel env add` si te da acceso). Nunca en el repo.
   - Validez por defecto: `TOKEN_HORAS` (por defecto 12).
3. **Rutas:**
   - `POST /api/auth/login {usuario, password}` → `{token, expira_ts, usuario, rol}`. 401 si no coincide, con la misma respuesta para usuario inexistente o clave mala.
   - `POST /api/auth/invitacion {nombre, horas}` → `{token, expira_ts, link}`. **Esto es lo que pidió Alejo:** genera un acceso que vence a las N horas (máximo 48). Solo la puede usar un usuario con rol admin o quien mande `X-Juez-Pin`. El `link` es `https://desafio-futbol-iota.vercel.app/juez/?t=<token>`.
   - `GET /api/auth/yo` → datos del token, o 401 `sesión vencida` / `token inválido`.
4. **Las rutas que deciden** (aprobar, rechazar, turno/asumir, reclamos/levantar, demo/iniciar y pin/verificar) aceptan **`Authorization: Bearer <token>` o `X-Juez-Pin`**. Si cualquiera de los dos es válido, pasa. No saques el PIN: es el respaldo del viernes.
5. **El token firma como el juez de turno**, no como un juez fijo (decisión 39). La API ya valida que `juez_id` esté en `jueces_de_turno`; eso no se toca. Guardá quién firmó (`sub` del token) en una columna nueva `firmado_por` de `pedidos`.
6. **Pantalla del juez** (`plataforma/web/`, carpeta de Alejo, te autoriza a tocar solo el ingreso):
   - Formulario con usuario y contraseña, y abajo "Entrar con PIN" como alternativa.
   - Si la URL trae `?t=<token>`, entra sola y borra el token de la barra (`history.replaceState`).
   - Guarda el token en `localStorage` y muestra "Tu acceso vence en X h". Al vencer vuelve al ingreso con el aviso "Tu acceso venció".
   - `api()` en `app.js` manda `Authorization: Bearer` si hay token y `X-Juez-Pin` si se entró con PIN.

## Lo que no se puede romper
- El motor y `final.sh` no usan la API: no se tocan.
- `python -m plataforma.db.test_db_api` tiene que seguir 10 de 10. Sumá pruebas de token vencido, firma alterada y PIN.
- **Primero en un deploy de preview** (`vercel deploy`, sin `--prod`). Pasale la URL a Alejo para que lo pruebe. Producción solo con su OK.
- El viernes a la mañana se congelan las funciones: tiene que estar en producción el jueves a la noche, o queda afuera.

## Terminada cuando
Alejo genera una invitación de 2 horas, abre el link en el celular, firma un pedido de un partido de demo, y a las 2 horas el mismo link ya no entra.
