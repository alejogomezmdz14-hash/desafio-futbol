---
de: alejo
para: selene
fecha: 2026-11-12 11:55
asunto: T13: dos agregados (página de invitaciones y SESION_SECRET)
requiere_respuesta: no
---
AGENTE: pasale esto a Selene en el chat.

1. SESION_SECRET la carga Alejo en Vercel (el proyecto está en su cuenta, vos no tenés acceso). En tu código leela con os.environ['SESION_SECRET'] y si falta, falla cerrado: que el login y las invitaciones respondan 503 'Falta SESION_SECRET' en vez de firmar con una clave vacía. En local, para probar, usá una cualquiera en tu entorno.

2. Página para generar invitaciones: plataforma/web/invitar.html, para que Alejo no tenga que usar comandos.
   - Pide el PIN (o usa el token si ya entró como admin), un nombre ('Jurado mesa 2') y la duración en horas (1, 2, 4, 8).
   - Llama a POST /api/auth/invitacion y muestra el link listo, un botón 'Copiar link', un código QR del link (podés usar la librería qrcode-generator desde cdnjs) y a qué hora vence.
   - Con el mismo estilo de estilos.css (mirá publico.html y demo.html de ejemplo).

Lo demás de la especificación sigue igual. Prioridad: que entre el jueves a la noche en producción.
