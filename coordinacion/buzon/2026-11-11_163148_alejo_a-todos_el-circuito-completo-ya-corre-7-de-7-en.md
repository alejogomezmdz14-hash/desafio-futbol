---
de: alejo
para: todos
fecha: 2026-11-11 16:31
asunto: El circuito completo ya corre: 7 de 7 en el verificador
requiere_respuesta: no
---
Equipo: la plataforma ya hace el circuito completo contra el simulador.

NÚMEROS (verificador oficial, práctica a x30, juez automático):
- 7 de 7 fases piratas bloqueadas, con 100 % de clientes cubiertos en cada una
- visibilidad residual promedio: 3,1 % (el cliente de ejemplo daba 92,4 %)
- primer bloqueo entre 0,4 y 0,9 min después de cada detección
- 0 colateral, 0 falsos positivos, 0 rechazos, 0 firmas fuera de turno, 0 IP después del partido
- las 7 fallas de Cumbre se reintentaron solas
Evidencia en entrega/practica/ (expediente con hash ok, auditoría íntegra, salida del verificador).

CÓMO CORRERLO (dos terminales):
  PYTHONUTF8=1 python simulador/servidor.py --acelerar 30
  PYTHONUTF8=1 python -m plataforma.main --sim http://localhost:8080 --juez-automatico
Sin --juez-automatico se aprueba desde http://localhost:8000/juez/ con el PIN que imprime el motor. Para entrar desde el celular: --red y JUEZ_PIN de 8 caracteres o más. Después: python evaluacion/verificar.py --log salida/registro.jsonl

POR PERSONA:
- Selene (T11): el motor (plataforma/motor/) tiene en memoria lo que tu base tiene que guardar; las rutas de la API son las mismas. Cuando plataforma/db esté lista lo conectamos. Revisá mi mensaje sobre los dos ajustes de seguridad de app.py.
- Rocío (T07): Motor.publico_api() y GET /api/publico ya devuelven el registro público.
- TODOS, para el viernes: la notebook del final NO se puede suspender (decisión 31). Hoy una corrida se congeló una hora porque se cerró la tapa.
