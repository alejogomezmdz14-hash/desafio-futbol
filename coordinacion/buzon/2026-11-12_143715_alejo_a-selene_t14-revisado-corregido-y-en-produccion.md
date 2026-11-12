---
de: alejo
para: selene
fecha: 2026-11-12 14:37
asunto: T14: revisado, corregido y en producción
requiere_respuesta: no
---
AGENTE: pasale esto a Selene en el chat.

Selene, gracias: el login anda bien y a Alejo le encantó. Antes de publicarlo corregí cuatro cosas de seguridad (decisión 42), para que lo tengas en cuenta:
1. La cuenta de demo con clave 123456 estaba precargada y escrita en la pantalla pública: cualquiera podía firmar órdenes. Ahora el formulario aparece vacío y la cuenta de demo solo existe si se carga DEMO_PASSWORD en Vercel (sin valor por defecto).
2. login.py ponía una SESION_SECRET fija escrita en el código si faltaba la clave: con eso cualquiera podía fabricarse un acceso. Lo saqué: falla cerrado.
3. El PIN servía como contraseña de cualquier juez, y la firma quedaba a nombre de ese juez sin que la hiciera él. Lo saqué.
4. Dominios gob.ar reales -> juzgado.test. Contraseñas de 8 o más.
Además, por pedido de Alejo, saqué de accesos.html la parte de links: queda alta de jueces y 'Cerrar la sesión de todos'. Pruebas: test_login 9/9 (sumé 3), test_accesos 15/15, test_db_api 10/10. T14 queda hecha.
