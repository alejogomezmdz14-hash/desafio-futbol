# Plataforma federal de órdenes de bloqueo en vivo

**Equipo Desafío Fútbol, Hackatón Argentina Space 2026 (track Datos y Streaming, QualyData).**

Mientras se juega el partido, la plataforma detecta un stream pirata y arma el expediente con evidencia verificable. Después se lo muestra al **juez de turno en el celular**, que firma con un toque, y manda la orden a **todos los proveedores de internet**, cada uno en el tipo de bloqueo que acepta. Sigue cada orden hasta que confirma, reintenta las que fallan, levanta sola los bloqueos por IP al terminar el partido y deja todo en una auditoría que no se puede alterar sin que se note.

**En línea:** https://desafio-futbol-iota.vercel.app (pantalla del juez en `/juez/`, partido de práctica en vivo en `/juez/demo.html`, registro público en `/api/publico`).

> Todo es ficticio: proveedores, juzgados, dominios `.test` e IPs de documentación. Solo trabajamos contra el simulador de la organización. No se bloquea nada real.

## No es solo un problema de derechos de televisión
Las páginas de fútbol gratis también se usan para **robar los datos de quienes las miran**. En septiembre de 2026, tras una denuncia de ALIANZA, la Justicia bloqueó unos 300 sitios que robaban datos bancarios e instalaban software malicioso ([DPL News](https://dplnews.com/?p=329227), [Señal News](https://senalnews.com/es/data/tras-denuncia-de-alianza-la-justicia-argentina-bloquea-300-dominios-clandestinos)). Un análisis de OpenText sobre 50 sitios ilegales de streaming deportivo encontró contenido malicioso en todos ([Piracy Monitor](https://piracymonitor.org/webroot-illegal-streaming-sites-expose-fans-to-fraud-scams-and-explicit-content/)). Cortar un stream pirata a tiempo también protege a la gente que entra a verlo.

## Por qué un juez, y por qué en Argentina
El art. 57 inc. a) de la **Ley 27.078 (Argentina Digital)** prohíbe a los proveedores bloquear contenidos "salvo orden judicial". Por eso el modelo italiano, donde el regulador bloquea sin juez, acá no tiene base legal. Además, la Corte Suprema ("Rodríguez c/ Google") exige examinar cada contenido concreto antes de bloquearlo. La plataforma resuelve eso: **cada objetivo nuevo pasa por el juez de turno**, en segundos, con la evidencia a la vista. La propuesta normativa está en [`propuesta-normativa.md`](propuesta-normativa.md). Los escenarios, la comparación con Italia y el modelo de negocio están en [`escenarios-y-modelo.md`](escenarios-y-modelo.md).

## Cómo funciona
```
simulador ──detecciones──► CEREBRO ──caso pirata──► EVIDENCIA ──expediente──► PEDIDO
                           (analisis/)               (evidencia/)                 │
                                                                                  ▼
proveedores ◄──órdenes firmadas── DESPACHO ◄──aprobado── JUEZ EN EL CELULAR (web/)
   │                              (despacho/)
   └──confirmación, reintentos, vencimiento──► AUDITORÍA encadenada + REGISTRO PÚBLICO
```
| Pieza | Qué decide | Dónde |
|---|---|---|
| Cerebro | Agrupa avisos repetidos. Verifica la marca de agua contra el partido (oficial, licenciatario en su dominio, otra señal o sin marca). Si la IP es compartida con sitios legítimos, recomienda bloquear el **nombre** y no la IP. | `plataforma/analisis/` |
| Evidencia | Expediente con SHA-256 de cada captura (sobre el binario), servidor, ASN, sitios en la misma IP, promoción del enlace y hash del expediente. La auditoría está encadenada con hashes. | `plataforma/evidencia/` |
| Juez | Pantalla para celular: lee el pedido en lenguaje claro y firma en lote. Rechazar exige un motivo. En el cambio de turno, el juez entrante ratifica las órdenes vigentes. | `plataforma/web/` |
| Despacho | Firma con el juez de turno en el minuto del envío. Manda IP o nombre según lo que acepta cada proveedor, reintenta las fallidas y vence en el fin del partido. | `plataforma/despacho/` |
| Motor y API | El loop que une todo, y la API que usa la web. | `plataforma/motor/`, `plataforma/api/` |

Las reglas y el porqué de cada decisión están en [`coordinacion/diseno.md`](../coordinacion/diseno.md). Las formas de datos entre piezas están en [`coordinacion/contratos.md`](../coordinacion/contratos.md).

## Cómo correrlo
Requisitos: Python 3.10 o superior.
```bash
pip install fastapi uvicorn
```
En Windows, anteponé `PYTHONUTF8=1` a cada comando, porque el simulador imprime caracteres que la consola no muestra.

**1. El cerebro contra el partido de práctica** (no necesita red):
```bash
python -m plataforma.analisis.test_cerebro
```
Resultado esperado: `13 de 13 pruebas OK`. Incluye:
- el partido de práctica completo (9 casos, igual que `evaluacion/verdad_practica.json`);
- un "partido final" simulado con otros nombres y varios licenciatarios;
- hosting real (`.com.ar`, `vercel.app`);
- DNS caído;
- mayúsculas y espacios.

Para ensayarlo **en vivo contra el simulador**, solo leyendo, sin mandar órdenes:
```bash
python simulador/servidor.py --acelerar 30
python -m plataforma.analisis.ensayo_en_vivo --sim http://localhost:8080 --verdad evaluacion/verdad_practica.json
```
El segundo comando va en otra terminal. Resultado: 9 de 9.

**2. La evidencia y la auditoría** (detecta alteraciones):
```bash
python -m plataforma.evidencia.test_evidencia
```

**3. La pantalla del juez con datos simulados** (sin base ni motor):
```bash
uvicorn plataforma.web.mock_api:app --port 8000
```
Abrir http://localhost:8000/juez/ con el usuario `coordinacion` y la contraseña que imprime el mock al arrancar, idealmente en tamaño celular. El mock corre el partido de práctica a x10 con el cerebro real. Para ver el cambio de turno del minuto 50, arrancalo con `MOCK_INICIO_MIN=46`.

**4. El circuito completo contra el simulador** (motor, despacho, API y pantalla del juez en un solo comando):
```bash
python simulador/servidor.py --acelerar 6
python -m plataforma.main --sim http://localhost:8080 --local
python evaluacion/verificar.py --log salida/registro.jsonl
```
El segundo comando va en otra terminal. Sin `--juez-automatico`, aprobás desde http://localhost:8000/juez/ con el usuario y la contraseña que imprime el motor al arrancar (o los de las variables `COORD_USUARIO` y `COORD_PASSWORD`). Esto reemplaza al PIN (`JUEZ_PIN`). Para entrar desde el celular por wifi agregá `--red`. Por defecto el motor solo escucha en la propia máquina. El tercero se corre cuando termina el partido.

**5. Con la base y la web de Vercel** (modo del partido final). La web de T11 corre en Vercel y lee y decide sobre la base. El motor corre donde llegue al simulador y sincroniza con esa misma base:
```bash
DATABASE_URL=postgres://...  python -m plataforma.main --sim URL_DEL_SIMULADOR --base --sin-web --exportar-entrega
```
Para probarlo todo en local, con SQLite: `DATABASE_URL=sqlite:///salida/plataforma.db COORD_PASSWORD=<contraseña> SESION_SECRET=<32+ caracteres> uvicorn plataforma.api.app:app --port 8020` en una terminal, el motor con `--base --sin-web` en otra, y la pantalla del juez en http://localhost:8020/juez/. Así se hizo la corrida `practica-juez-humano/`.

**En línea:** https://desafio-futbol-iota.vercel.app. La web y la API corren en Vercel sobre una base Postgres en Neon (São Paulo).

**6. Partido de práctica online (T12), sin ninguna notebook.** En https://desafio-futbol-iota.vercel.app/juez/demo.html se entra con el usuario y la contraseña de la coordinación y se aprieta "Correr partido de práctica". La web prende un Vercel Sandbox que clona este repo y levanta el simulador de la organización y nuestro motor apuntando a la base. El juez firma desde `/juez/` en el celular y, al terminar, la página muestra la salida de `evaluacion/verificar.py`. Hay un solo partido a la vez, con velocidad de x6 a x30.

## Estado (se actualiza durante el evento)
| Tarea | Estado |
|---|---|
| T01 Cerebro | ✅ Hecho y probado (13 de 13, más 9 de 9 en vivo contra el simulador) |
| T03 Evidencia y auditoría | ✅ Hecho y probado |
| T04 Pantalla del juez | ✅ En línea en Vercel, leyendo la base real |
| T08 Propuesta normativa | ✅ Hecho (Rocío) |
| T02 Despacho + T05 Motor | ✅ Circuito completo, conectado a la base de T11: **7 de 7, 0 colateral** (ver abajo) |
| T11 Base y API | ✅ En línea: Vercel + Neon (Selene escribió la base y la API; Alejo publicó el deploy) |
| T06 Reclamos | ✅ El motor lee `/reclamos`, verifica, levanta con firma y reemplaza por dominio; la web los pide por solicitud |
| T07 Registro público | ✅ Hecho (Rocío) |
| T10 Validación | ✅ Partido completo y cambio de turno, en `entrega/validacion/` |
| T12 Partido de demo online | ✅ Vercel Sandbox con simulador + motor, lanzado desde la web |

## Resultado del verificador oficial
Dos corridas del partido de práctica. Cada una tiene su evidencia (expediente con hash verificado, auditoría íntegra y salida del verificador):

- [`practica-juez-automatico/`](practica-juez-automatico/): a x30, el juez aprueba al instante. Es el techo técnico.
- [`practica-juez-humano/`](practica-juez-humano/): a x10, **con la web de T11 y la base**, y un juez que firma desde la pantalla revisándola cada ~10 segundos. Es la prueba de integración completa: el motor escribe en la base, la web la lee, el juez decide ahí, el cambio de turno va por solicitud y el motor despacha.

| Métrica | Cliente de ejemplo | Juez automático (x30) | **Juez desde la web (x10)** |
|---|---|---|---|
| Fases piratas bloqueadas | 1 de 7 | 7 de 7 | **7 de 7** |
| Visibilidad residual promedio | 92,4 % | 3,1 % | **6,3 %** |
| Primer bloqueo después de la detección | 14,7 min | 0,4–0,9 min | **0,9–1,8 min** (5,3 en el primero, que esperó el ingreso) |
| Clientes cubiertos por fase | — | 100 % | **100 %** |
| Sitios legítimos afectados / falsos positivos | 0 / 0 | 0 / 0 | **0 / 0** |
| Órdenes rechazadas / firmadas fuera de turno | 1 / 0 | 0 / 0 | **0 / 0** |
| IP bloqueadas después del partido | 0 | 0 | **0** |

**Cómo leer la diferencia:** a x10, los 10 segundos que tarda el juez son 1,7 minutos de partido. En un partido real (x1), esos mismos 10 segundos son 0,17 minutos, así que el resultado real se acerca al del juez automático. Las órdenes que Cumbre hace fallar se reintentan solas.

## Supuestos
- **La firma del juez es un HMAC** con la clave de demostración del simulador, porque es lo que acepta. **Legalmente no alcanza:**
  - la clave es compartida, así que cualquiera que la tenga puede firmar;
  - no se puede verificar sin tenerla;
  - el art. 288 del Código Civil y Comercial exige **firma digital** en documentos electrónicos.

  En producción, la plataforma arma cada orden como documento PDF con su expediente y sus hashes. **El juez la firma con su propio certificado** de firma digital (Ley 25.506), desde el celular, con la [Plataforma de Firma Digital Remota](https://www.argentina.gob.ar/jefatura/innovacion-ciencia-y-tecnologia/innovacion/firma-digital/pfdr), que funciona sin token y con un código de un solo uso. **La plataforma nunca tiene la clave del juez.** Cada proveedor verifica la firma con el certificado público antes de bloquear. "Firmar en lote" son varias firmas, una por orden y cada una con su fundamento; no una sola firma que cubra todo.
- **Acceso: un solo login de la coordinación** (usuario y contraseña, decisión 43). Quien entra firma como el juez de turno del minuto. Las sesiones vencen a las 12 horas y 5 intentos fallidos bloquean 5 minutos. En producción, la identidad de cada juez la da su propia firma digital.
- **"Sitio" son las dos últimas etiquetas del dominio** (`s1.pelotaya.test` → `pelotaya.test`). Alcanza para los dominios `.test` del simulador; en producción haría falta la Public Suffix List.
- **Si el DNS pasivo no tiene datos de una IP, la tratamos como compartida** y bloqueamos solo el nombre: preferimos no bloquear de más.
- **Todas las órdenes vencen en el minuto en que termina el partido**, también las de nombre. Extenderlas requiere una orden nueva, por proporcionalidad.
- **Un único juzgado de turno por momento**, como en el simulador. La competencia territorial real es parte de la propuesta normativa.

## Qué existía antes del evento y qué es nuestro
- **De la organización (QualyData), sin cambios:** `simulador/`, `evaluacion/`, `ejemplos/` y `datos/`. Repo original: [qualydata-org/desafio-futbol](https://github.com/qualydata-org/desafio-futbol).
- **Hecho por el equipo durante la hackatón (11 al 13 de noviembre de 2026):** `plataforma/`, `entrega/` y `coordinacion/`. `coordinacion/` es el tablero, el buzón y los contratos con los que se coordinaron los agentes de los 5 integrantes.
- **Librerías públicas:**
  - FastAPI y Uvicorn, para la API y para servir la web;
  - psycopg, para Postgres en el deploy;
  - del navegador, solo las fuentes Public Sans y Barlow Condensed de Google Fonts.

  El resto es la biblioteca estándar de Python y JavaScript sin dependencias.

## Entregables (`entrega/`)
- `README.md`: este archivo.
- [`escenarios-y-modelo.md`](escenarios-y-modelo.md): cada escenario (del partido y del mundo real), cómo lo resuelve la plataforma, quién paga y el camino a producción.
- **Video del pitch** (2:58, con subtítulos): [en Google Drive](https://drive.google.com/file/d/13LJJsUij3JoVxd3yyLj61Qy19zkRFPBb/view?usp=sharing), que es el link cargado en Hacki, y el mismo archivo en el repo: [`video-pitch.mp4`](video-pitch.mp4). Los subtítulos sueltos están en [`video-pitch.srt`](video-pitch.srt).
- [`pitch.md`](pitch.md): guion del pitch y del video de 3 minutos.
- `propuesta-normativa.md`: 1 página (T08).
- `expediente-final.json` y `auditoria-final.jsonl`: exportados del partido final (T03).

## Equipo
Alejo, Selene y Rocío. Quién hizo qué está en [`coordinacion/equipo.md`](../coordinacion/equipo.md) y en el historial de `coordinacion/tareas/`.
