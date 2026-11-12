# Escenarios y modelo de negocio

Qué pasa en cada situación que puede aparecer, qué hace la plataforma, dónde está probado y por qué alguien pagaría por esto.

> **Cómo leer los números:** las cifras de mercado vienen de la industria (ALIANZA, LaLiga, operadoras), que es parte interesada. Las usamos como orden de magnitud, no como verdad. Los precios son **hipótesis a validar**, no cotizaciones.

---

## 1. Lo que vendemos, en una línea
**Infraestructura para que un juez de turno ordene bloqueos en vivo, con evidencia válida, y que la orden llegue a todos los proveedores de internet en minutos, sin tirar abajo sitios legítimos.**

- **Usuarios:** jueces y fiscalías, que deciden; proveedores de internet, que ejecutan; titulares de derechos, que denuncian; el público, que controla.
- **Quién paga:** el titular de derechos, que es quien pierde plata (ver §5).

---

## 2. Escenarios del partido (lo que mide el jurado)
| Escenario | Qué hace la plataforma | Dónde está probado |
|---|---|---|
| El radar avisa varias veces del mismo stream | Un solo caso, un solo pedido al juez | `test_cerebro`: partido de práctica, 43 avisos → 9 casos |
| El pirata se muda de servidor o de IP | Caso nuevo y pedido nuevo en el acto; el bloqueo anterior sigue hasta que vence | Práctica: pelotaya ×3 y tribuna ×2. Escenario final simulado |
| El stream sale de una CDN o de un hosting compartido | **Nunca bloquea la IP**: bloquea el nombre del servidor del video | golazo (11 sitios legítimos en la IP) y verpartido |
| Hosting real: `.com.ar`, `vercel.app` | Distingue `pirata.com.ar` de `panaderia.com.ar` con una lista de sufijos públicos | `prueba_hosting_compartido_real_va_por_dominio` |
| El DNS pasivo no tiene datos o está caído | Va a lo seguro: bloquea el nombre, sin cortar el circuito | `prueba_dns_caido_no_frena_el_circuito` |
| Un licenciatario transmite en su dominio | No se toca | Canal Norte |
| La señal de un licenciatario aparece en otro dominio | Es piratería (le robaron la señal): se bloquea | `prueba_licenciatario_fuera_de_su_dominio_es_pirata` |
| Un dominio del licenciatario aparece con otra marca | No se bloquea nunca: se informa al titular, porque es un tema de contrato | `prueba_marca_oficial_en_dominio_del_licenciatario_no_se_bloquea` |
| El video es de otro partido o no tiene marca | Se descarta y queda registrado | resúmenes (LP25) y `sin_marca` |
| Un proveedor solo bloquea por nombre | Recibe el nombre; los demás, la IP | FibraValle en todos los pedidos |
| Un proveedor falla a veces | Reintento inmediato con una orden nueva | Cumbre en el mock (intento 2) |
| Cambia el turno judicial a mitad del partido | El juez entrante ratifica con un toque y desde ahí todo sale con su firma | Mock, minuto 50 |
| Llegan muchos pedidos juntos | Firma en lote: varias firmas en un toque, una por orden | Mock: 3 pedidos de un toque |
| Termina el partido | Las órdenes vencen solas en el fin del partido | `vence_min` = fin del partido |
| Un sitio legítimo reclama | Se verifica, se levanta con firma y se reemplaza por un bloqueo más preciso | T06, extra |
| Alguien adultera la evidencia | La cadena de hashes lo detecta en la línea exacta | `test_evidencia` (T03) |

**Ensayo en vivo contra el simulador real**, por HTTP (`python -m plataforma.analisis.ensayo_en_vivo`): 9 de 9 casos bien, y cada decisión sale apenas llega el aviso.

---

## 3. Escenarios del mundo real

### Técnicos
- **Usuarios que usan VPN o cambian de DNS.** Esto no lo frena ningún bloqueo, y lo decimos de frente. Un bloqueo en vivo no apunta al usuario experto: apunta a **cortar el acceso masivo durante los 90 minutos**, que es donde se pierde la plata. La métrica honesta es la **visibilidad residual** (qué porcentaje de clientes pudo ver el stream), y la reportamos así.
- **CDN grandes (Cloudflare y similares).** Bloquear su IP es tirar miles de sitios: le pasó a Italia con Cloudflare y con Google Drive ([Techdirt](https://www.techdirt.com/2024/10/21/italys-piracy-shield-misfires-blocks-google-drive-in-anti-piracy-blunder), [Cloudflare](https://blog.cloudflare.com/standing-up-for-the-open-internet/)). Nuestra regla lo impide por diseño: IP compartida → solo el nombre. **Siguiente paso:** notificar a la CDN con la misma orden firmada para que corte el origen.
- **Dominios que cambian cada minuto.** Cada dominio nuevo pasa por el juez en segundos. Es lo que exige la Corte, y lo que el modelo de San Isidro (la fiscalía elige los dominios) no garantiza.
- **Proveedores chicos sin DNS propio ni técnico de guardia**, que es la objeción de CABASE. Hoy les mandamos la orden por API. Para un producto real proponemos un **canal estándar RPZ** (Response Policy Zones), el formato que ya entienden los servidores DNS más comunes (BIND, Unbound, PowerDNS). El proveedor chico se suscribe una vez y aplica solo, sin intervención humana.
- **Apps de IPTV y Telegram.** El bloqueo de dominio o IP alcanza al servidor que entrega el video. El expediente ya guarda dónde se promocionó el enlace (X, Discord, Telegram), para pedir la baja en la plataforma.
- **Escala.** Para el Superclásico se pidieron 182 dominios, y en el país hay del orden de mil proveedores. Son unos 182.000 envíos por partido, más confirmaciones y reintentos. Es carga chica para una API, pero exige colas y reintentos, que ya están en el diseño (T02).

### Legales (Argentina)
| Requisito | Cómo lo resuelve el diseño |
|---|---|
| Sin orden judicial no hay bloqueo (art. 57, Ley 27.078) | Ningún bloqueo sale sin la firma del juez de turno |
| Examen previo de cada contenido ("Rodríguez c/ Google") | Un pedido por objetivo, con la evidencia a la vista; nada de listas genéricas |
| Firma válida (Ley 25.506, art. 288 del Código Civil y Comercial) | En producción, firma digital del juez desde el celular (firma remota del Estado). La demo usa HMAC porque lo pide el simulador |
| Proporcionalidad | Vencimiento automático; nunca IP compartida; extender un bloqueo requiere otra orden |
| Defensa del afectado | Reclamos con levantamiento firmado y reemplazo por algo más preciso (T06) |
| Transparencia | Registro público: qué se bloqueó, cuándo, por orden de quién y hasta cuándo (T07) |
| Datos personales (Ley 25.326) | Los expedientes no tienen datos de usuarios finales: solo servidores, dominios y capturas del stream |
| Competencia territorial | Un pedido va al juzgado de la causa y a sus turnos; la competencia federal explícita va en la propuesta normativa |

### Operativos
- **El juez no responde:** la pantalla avisa con vibración, sonido y notificación. **Siguiente paso:** escalar al juez suplente pasados N minutos.
- **El proveedor no confirma:** el estado queda visible por proveedor; el incumplimiento queda auditado y se puede informar a ENACOM.
- **La máquina del motor se suspende** (nos pasó en una prueba: se cerró la tapa y el motor se congeló una hora). En producción, el motor corre en un servidor siempre prendido (Vercel Sandbox o similar), no en una notebook. El viernes, si corre en la notebook: enchufada, tapa abierta y suspensión desactivada.
- **Se cae la plataforma:** el estado vive en la base, así que el motor retoma. Plan B: todo corre en una notebook con SQLite (decisión 20).
- **Confianza en la auditoría:** la cadena de hashes ya detecta alteraciones. **Siguiente paso:** publicar el hash del día en el registro público, para que nadie pueda reescribir la historia completa sin que se note.

---

## 4. Por qué esto y no lo que ya existe
| | Italia (Piracy Shield) | Francia (ARCOM) | España (LaLiga) | Brasil (ANCINE + Anatel) | Argentina hoy (San Isidro) | **Nuestra plataforma** |
|---|---|---|---|---|---|---|
| ¿Decide un juez? | No (regulador) | Orden inicial; desde jul-2026 bloqueo automático sin revisión humana previa | Una sentencia; después LaLiga actualiza la lista sola | No (administrativo) | Una orden inicial; la fiscalía suma dominios | **Sí, cada objetivo, de turno** |
| Velocidad | 30 min por norma | ~45 min (ARCOM dice que no alcanza) | Tiempo real | Órdenes nuevas cada 30 min | No medida; en ago-2026 arrancó 10 min después del inicio | **Minutos (se mide en la demo)** |
| ¿Llega a todos los proveedores? | Sí, por plataforma | Grandes ISP | 4 operadores | Más de 21.000 prestadoras | Por ENACOM o las cámaras, por oficio, sin acuse | **Sí, por API, con confirmación** |
| Daño colateral | Bloqueó Cloudflare y Google Drive | Advertido por la propia ARCOM | ~3.000 IP por finde contra ~120 en la sentencia; cae Cloudflare | Autodeclarado bajo | IP compartidas, denunciado por CABASE | **Regla: nunca IP compartida** |
| ¿Legal en Argentina? | No sin cambiar la ley | No sin cambiar la ley | El modelo ya se autorizó acá en sep-2026 | No (art. 57) | Discutible (delegación en la fiscalía) | **Encaja en la ley actual** |
| Transparencia y reclamos | Sin lista pública completa | Apelación durante el partido (ley nueva) | Sin registro ni apelación | 2 reclamos informados | No hay | **Registro público + reclamos** |

**Vendors comerciales** (Friend MTS, NAGRA, Irdeto, Viaccess-Orca, Sportian): venden detección y marca de agua por contrato privado, sin precios públicos. Ninguno firma con un juez ni tiene un canal hacia todos los proveedores. No compiten con nosotros: pueden ser la fuente de detecciones de la plataforma.

Detalle, fuentes y cifras dudosas: `coordinacion/investigacion/soluciones-parecidas.md`.

---

## 5. Modelo de negocio

**El problema también cuesta datos de la gente.** Los sitios de fútbol gratis se usan para robar datos bancarios e instalar software malicioso: en septiembre de 2026 la Justicia bloqueó unos 300 por eso, tras una denuncia de ALIANZA ([DPL News](https://dplnews.com/?p=329227)), y un análisis de OpenText encontró contenido malicioso en los 50 sitios de streaming deportivo que revisó ([Piracy Monitor](https://piracymonitor.org/webroot-illegal-streaming-sites-expose-fans-to-fraud-scams-and-explicit-content/)). Esto suma un interesado más, además del titular de derechos: quien protege a los usuarios (defensa del consumidor, bancos, el propio Estado). No hay datos serios de qué porcentaje de usuarios sufre el robo, así que no damos esa cifra.

**El problema vale plata.** La industria estima pérdidas por piratería audiovisual en Argentina de entre **US$ 258 millones y US$ 590 millones por año**, según la fuente ([La Nación](https://www.lanacion.com.ar/seguridad/bloquearon-en-vivo-sitios-y-apps-que-transmitian-partidos-de-futbol-de-manera-ilegal-nid02062025/), [Ámbito](https://www.ambito.com/negocios/futbol-y-pirateria-crecen-usuarios-transmisiones-ilegales-y-los-sitios-facturan-mas-us100-millones-n6068848)). Según ALIANZA, los 30 sitios piratas más visitados desde Argentina sumaron **97 millones de visitas en un mes** (junio de 2026) ([DPL News](https://dplnews.com/?p=329227)). Son cifras de parte interesada, pero aunque fueran la mitad, el problema sigue siendo enorme.

**Cuánto cuesta operarlo.** En Italia lo caro no es el software: los proveedores reclaman unos **10 millones de euros por año** de trabajo manual sin compensación ([ZeusNews](https://www.zeusnews.it/n.php?c=31580)). Nuestra nube, para 30 partidos por mes con un motor por partido, sale entre **US$ 20 y 60 por mes**, o sea entre 35 y 90 centavos por partido. Es una **estimación nuestra** con los precios publicados de Vercel Sandbox y Neon, sin contar personal.

**Quién usa y quién paga** (hipótesis a validar):
| Actor | Qué obtiene | Qué paga |
|---|---|---|
| **Titulares de derechos** (liga, señales deportivas y cableras agrupadas en ALIANZA) | Bloqueos en minutos, legales y documentados | **Suscripción por temporada** según la cantidad de eventos protegidos. Es el cliente que paga |
| **Poder Judicial / ENACOM** | Una herramienta federal sin costo de desarrollo, con auditoría y transparencia | Nada, o un convenio de implementación: es el operador institucional |
| **Proveedores de internet** | Un canal estándar (API o RPZ) en lugar de órdenes por mail y llamados; los chicos cumplen sin personal de guardia | Nada: bajarles el costo es lo que destraba la adopción |
| **Público** | Transparencia y vía de reclamo | — |

**Por qué paga el titular:** hoy paga abogados, monitoreo y coordinación manual con cada fiscalía para cada partido. La plataforma le vende **minutos de visibilidad pirata evitados** con evidencia que aguanta un juicio. La métrica de venta es la que ya mide el verificador: visibilidad residual y minutos hasta el bloqueo.

**Mercado:** el mismo problema, con marcos legales que exigen intervención judicial o administrativa, existe en toda la región:
- **Perú:** Indecopi bloqueó 238 webs en el Mundial 2026 ([El Peruano](https://www.elperuano.pe/noticia/300328-pirateria-en-el-mundial-2026-que-falta-tras-el-bloqueo-de-238-webs-ordenado-por-indecopi)).
- **México:** el IMPI hizo bloqueos masivos ([Almomento](https://almomento.mx/el-impi-ejecuta-un-bloqueo-masivo-contra-la-pirateria-digital-que-transmitian-partidos-del-mundial-2026/)).
- **Colombia:** discute un proyecto de bloqueo exprés para transmisiones en vivo ([PL 448/2025](https://www.camara.gov.co/wp-content/uploads/2026/06/proyectos-ley/publicaciones/proyecto-35934/PONENCIA-1-PL-448-2025-C-PIRATERIA-DIGITAL.docx.pdf)).
- **Canal de venta:** ALIANZA y LaLiga ya coordinan acciones regionales ([La Nación](https://www.lanacion.com.ar/agencias/futbol-laliga-y-alianza-refuerzan-la-ofensiva-regional-contra-la-pirateria-audiovisual-en-america-nid01122025/)). El producto se configura por país: cambian la ley citada, el juzgado y el registro de proveedores, no el circuito.

**Camino a producción:**
1. **Piloto (30 días):** un partido de la liga con la fiscalía de San Isidro y ALIANZA, en paralelo al proceso actual. Se miden minutos hasta el bloqueo y colateral contra el método de hoy.
2. **Institucional (90 días):** resolución de ENACOM que obligue a cada proveedor a declarar un canal electrónico de órdenes (API o RPZ). Firma digital remota para los jueces del piloto.
3. **Federal (180 días):** adhesión de las jurisdicciones; reclamos y registro público en producción; primer país de la región.

**Riesgos y cómo se mitigan:**
| Riesgo | Mitigación |
|---|---|
| Impugnación por censura previa | Juez en cada objetivo, vencimiento, reclamos y transparencia: es el diseño más defendible que conocemos |
| Resistencia de los proveedores | Costo cero para ellos, canal estándar automático, compensación definida en la norma |
| Falsos positivos | Regla de IP compartida, licenciatarios protegidos, caución del art. 79 de la Ley 11.723 para cubrir daños |
| Evasión por VPN y DNS alternativos | Se mide y se reporta (visibilidad residual); el objetivo es el acceso masivo, no el usuario experto |

---

## 6. Qué medimos para venderlo
- Minutos desde la detección hasta el bloqueo confirmado en todos los proveedores.
- Porcentaje de clientes cubiertos y visibilidad residual del stream.
- Sitios legítimos afectados: objetivo **cero**.
- Minutos hasta resolver un reclamo.
- Porcentaje de proveedores conectados al canal estándar.

*Este documento no es asesoramiento legal ni una cotización. Las cifras de mercado son estimaciones de la industria.*
