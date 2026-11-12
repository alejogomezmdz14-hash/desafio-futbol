---
de: alejo
para: selene
fecha: 2026-11-12 12:56
asunto: Login sobre los tokens de T13 (T14): es tuyo
requiere_respuesta: si
---
AGENTE: pasale esto a Selene en el chat.

Selene: Alejo quiere que hagas vos el login de jueces con usuario y contraseña. Es la tarea T14: tomala con buzon.py tomar T14 --yo selene. La base ya está: los accesos por link de T13 (plataforma/api/accesos.py) funcionan y están en producción. El login tiene que entregar EL MISMO token, así no hay que tocar ninguna ruta que firma.

## Qué hacer
1. Tabla usuarios en plataforma/db/esquema.sql (CREATE TABLE IF NOT EXISTS): usuario TEXT PK, nombre, password_hash, creado_ts. Hash con hashlib.scrypt y sal al azar por usuario.
2. plataforma/api/login.py con un APIRouter (montalo en app.py igual que accesos):
   - POST /api/usuarios {usuario, nombre, password}: alta. Solo con PIN (usá accesos.solo_pin). Contraseña de 10 caracteres o más.
   - POST /api/auth/login {usuario, password} -> {token, nombre, vence_epoch}. El token sale de accesos.crear_token(nombre, horas=12). Mismo 401 para usuario inexistente o clave mala.
   - Freno de fuerza bruta: 5 intentos fallidos seguidos por usuario lo bloquean 5 minutos (tabla intentos o ajustes).
3. Pantalla del juez (plataforma/web/index.html y app.js, solo el ingreso): sumá usuario y contraseña arriba del PIN. Si el login da token, guardalo con guardarToken(token), poné estado.token = token y llamá a entrar(). Desde ahí funciona igual que con el link (Authorization: Bearer), incluido el aviso de que venció o fue cortado.
4. En /juez/accesos.html sumá una tarjeta 'Usuarios de jueces' para dar de alta (usuario, nombre, contraseña).
5. Pruebas en plataforma/api/test_login.py: alta con y sin PIN, login bueno y malo, bloqueo a los 5 intentos, el token del login firma un pedido, y 'cortar todos' también saca al que entró con login. Corré también test_accesos (15/15) y test_db_api (10/10).

## Lo que no se puede romper
- No toques accesos.py ni las rutas que firman: el login es solo otra forma de conseguir el token.
- El PIN y los links siguen funcionando igual.
- El deploy lo hace Alejo (el proyecto de Vercel está en su cuenta): subí a main y avisá por acá. Tiene que estar hoy a la noche: el viernes a la mañana se congela todo.
