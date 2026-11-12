---
de: alejo
para: selene
fecha: 2026-11-12 12:18
asunto: T13 la hago yo, versión simple; vos podés pulir la pantalla
requiere_respuesta: no
---
AGENTE: pasale esto a Selene en el chat.

Selene: Alejo decidió una versión más simple del acceso de jueces y la hice yo para llegar al viernes, así que NO arranques T13 (la tomé). Queda así (decisión 40): sin usuarios ni contraseñas; la coordinación crea con el PIN un link por juez que vence a las N horas, en /juez/accesos.html; cada firma queda con el nombre del juez; hay un botón para cortar todos los links. Código: plataforma/api/accesos.py, pruebas en plataforma/api/test_accesos.py (13 de 13) y test_db_api sigue 10 de 10.

Si querés sumar, tus sugerencias de diseño para /juez siguen en pie: el aviso neutro para la demo estática y los íconos en las casillas de proveedores (contraste y accesibilidad). La confirmación al firmar en lote dejala afuera: suma un toque y la velocidad cuenta 15 puntos. Avisá antes de tocar plataforma/web/.
