# Pitch y video

**La idea en una frase (versión vendible):** hicimos **el VAR de la piratería**: el juez ve la jugada en el celular, cobra en segundos, la orden llega a todos los proveedores de internet a la vez, y se apaga sola con el pitazo final.

Los números salen solo del verificador oficial. Hoy son los del partido de práctica; el viernes se reemplazan por los del final si cambian.

---

## Cómo tiene que sonar (lo que nos dejó la mentoría)

- **Problema → solución con un giro que se entiende solo.** El ejemplo del mentor: *apuestas online en menores* → *lotería sin pérdida, porque la plata se invierte y el premio sale de los intereses*. El giro conserva lo que la gente quiere y le saca el daño. El nuestro: **un bloqueo que llega en segundos, a todos, y dura lo que dura el partido** (como una tarjeta: vale para ese partido).
- **Del video de ejemplo (Cosecha Pay):** arranca con nombre + producto, dice "resuelve **tres problemas muy concretos**" desde el lado de las personas, y la solución en una frase ("bloquear el pago antes de que empiece el trabajo"). Donde se pierde es cuando se mete en arquitectura (Soroban, Horizon, claimable balance): eso no lo entiende nadie del público. **Nosotros no hablamos de tecnología en el escenario; la tecnología se muestra en la demo.**
- **Analogías de fútbol**, que acá las entiende todo el mundo: VAR, tarjeta, pitazo final.
- El público también mira fútbol pirata: **no los retamos**. El enemigo es el sitio trucho, no el que mira.

### Palabras que no se dicen arriba del escenario

| En vez de… | Decimos… |
|---|---|
| ISP, proveedor | "las empresas de internet, de las grandes a la cooperativa del pueblo" |
| IP | "la dirección del servidor" |
| IP compartida, CDN | "un edificio con muchos vecinos" |
| dominio, DNS | "el nombre de la página" |
| marca de agua | "una firma invisible que va dentro de la imagen del partido" |
| hash, SHA-256 | "la huella digital del expediente" |
| auditoría inalterable | "un registro que nadie puede borrar ni tocar" |
| HMAC, ASN, RPZ, Ley 27.078, Europa | Nada. Solo si preguntan (ver tabla de preguntas). |

---

## Pitch vendible (3 minutos) — ESTE es el que se dice

### 1. Gancho (0:00–0:15)
> "Levanten la mano los que alguna vez vieron un partido en una página trucha. … Tranquilos, no somos la policía. El problema no son ustedes: son las páginas. Y muchas de esas páginas, encima, te roban los datos de la tarjeta."

*(Fuente: la Justicia bajó ~300 páginas de fútbol pirata, clones de Fútbol Libre, que robaban datos bancarios — `reports/` §1.)*

### 2. El problema: tres problemas muy concretos (0:15–0:50)
> "Hoy, para cortar un partido pirata, la orden de un juez pasa de mano en mano: fiscalía, juzgado, el ENACOM, las cámaras, y recién ahí más de mil empresas de internet. El partido dura dos horas. La página pirata se muda de dirección en minutos. Eso genera tres problemas:
> **Uno: llega tarde.** Cuando se aplica el bloqueo, la página ya se mudó.
> **Dos: llega a medias.** Las empresas grandes bloquean; la cooperativa de un pueblo de la Puna ni se entera.
> **Tres: rompe cosas.** Si bloqueás mal, se cae también la página de la panadería del barrio que vivía en el mismo servidor. Y nadie sabe quién bloqueó qué, ni hasta cuándo."

### 3. La solución (0:50–1:10)
> "Por eso hicimos **el VAR de la piratería**. Igual que el VAR: la jugada llega grabada, el juez la mira, cobra, y la decisión vale en toda la cancha al mismo tiempo.
> La plataforma encuentra la página pirata y arma la prueba sola. Al juez de turno le llega al celular y firma con un toque. La orden llega a **todas** las empresas de internet a la vez, de la más grande a la más chica, y cada una contesta 'listo'.
> Y como una tarjeta, **vale para ese partido**: con el pitazo final, el bloqueo se apaga solo."

### 4. Demo en vivo (1:10–2:20)
Una persona maneja el celular del juez, proyectado. Otra narra. Frases cortas, sin tecnicismos:
1. **"Le vibra el celular al juez."** Llega `s1.pelotaya.test`. Leer las cuatro líneas en criollo: "Es nuestro partido, lo dice la firma invisible de la imagen. El video sale de acá. Se bloquea esto. Hasta el final del partido."
2. **El edificio.** Pedido de `live.golazo-libre.test`: "Esta página vive en un edificio con 11 vecinos que no hicieron nada. Cortar la dirección es cortarle la luz a todo el edificio. Nosotros apagamos solo su departamento: bloqueamos el nombre."
3. **No se equivoca.** "Este canal tiene los derechos y pasa el partido legalmente: no lo toca."
4. **Un toque, todos en verde.** Firmar los N pedidos. "Esta empresa falló: la plataforma reintentó sola. Esta otra es chiquita y solo sabe bloquear nombres: le mandamos lo que puede hacer."
5. **Cambio de turno, minuto 50** *(cortar si vamos justos de tiempo)*. "Cambia el juez de turno: el nuevo confirma con un toque."
6. **Nadie puede trucar la prueba.** Tocar una línea del registro y correr la verificación: "Si alguien cambia una coma, salta la alarma en la línea exacta."

### 5. El resultado: un número que se entiende (2:20–2:40)
> "Lo probamos en el simulador oficial del desafío. Con la solución básica que traía el desafío, **el 92 % de la gente veía el partido pirata igual**. Con la nuestra, **el 3 %**. Las 7 páginas piratas bloqueadas, en todas las empresas, en menos de un minuto cada una. Y **cero** páginas inocentes rotas."

*(Mismos números que la sección 4 del guion anterior; si la corrida del final cambia, se cambian acá.)*

### 6. Quién paga (2:40–2:52)
> "Lo paga el que pierde la plata: los dueños de los derechos del fútbol. Para el juez y para las empresas de internet es gratis. Para arrancar alcanza con un partido de prueba de la liga."

### 7. Cierre (2:52–3:00)
> "Hoy la piratería juega sin árbitro. Nosotros le pusimos uno: rápido, justo, y que llega a todos. Somos Alejo, Selene, Luciano, Rocío y Nahuel."

---

## Guion anterior (técnico) — ya no se dice entero; sirve de respaldo para las preguntas

### 1. El problema (0:00–0:30)
> "El 1 de noviembre, antes del Superclásico, la Justicia tuvo que pedir el bloqueo de 182 sitios piratas. Un partido dura dos horas; un sitio pirata cambia de servidor en minutos.
> Hoy en Argentina eso depende de una sola fiscalía y un solo juzgado. La orden sale por oficio, ENACOM o las cámaras se la reenvían a más de mil proveedores de internet, y **nadie publicó cuántos cumplieron ni cuándo**. Los chicos no llegan a tiempo, y si bloqueás una IP compartida tirás abajo la panadería y el diario del barrio."

### 2. Por qué no copiamos a Europa (0:30–0:50)
> "Europa tuvo que elegir entre rápido y con garantías. Italia bloquea en 30 minutos sin juez, y dejó a Google Drive bloqueado durante horas. Francia acaba de sacar la revisión humana. España tiene juez, pero la lista la maneja LaLiga: miles de IP por fin de semana con una sentencia que nombra unas 120. Y desde septiembre LaLiga tiene autorización para hacer lo mismo acá.
> Acá sacar al juez ni siquiera es legal: la Ley 27.078 dice que un proveedor solo puede bloquear con orden judicial. Así que no sacamos al juez: lo pusimos en el centro, de turno, en el celular."

### 3. Demo en vivo (0:50–2:10)
Una persona maneja el celular del juez, proyectado. Otra muestra el registro y el verificador.
1. **El pedido llega solo.** El celular vibra: "s1.pelotaya.test". Leer en voz alta las cuatro líneas: por qué es el partido (la marca de agua coincide), de dónde sale el video, qué se bloquea y hasta cuándo.
2. **La trampa de la CDN.** Mostrar el pedido de `live.golazo-libre.test`: "Esta IP la comparten 11 sitios legítimos. La plataforma no la bloquea: bloquea solo el nombre."
3. **Lo que no se bloquea.** "Canal Norte pasa el partido legalmente en su dominio, y los resúmenes son de otro partido: la plataforma los descarta sola."
4. **Firmar los N pedidos**, con un toque. Las casillas de los proveedores pasan a verde. Cumbre falla y se reintenta sola. FibraValle recibe el nombre porque no sabe bloquear por IP.
5. **Cambio de turno, minuto 50.** "Entra el juez Martín: ratifica con un toque y desde ahí todo sale con su firma."
6. **Evidencia que no se puede trucar.** Abrir el expediente y mostrar la huella SHA-256. Alterar una línea de la auditoría y correr la verificación: "Salta la alerta en la línea exacta."

### 4. Resultado (2:10–2:35)
> "Corrimos el verificador oficial del desafío. El cliente de ejemplo bloqueó 1 de 7 streams y dejó ver el partido pirata al 92 % de la gente. Nosotros: 7 de 7 streams bloqueados, en todos los proveedores, a menos de un minuto de cada detección. El partido pirata lo pudo ver el 3 % de la gente, contra el 92 % de antes. Cero sitios legítimos afectados, cero bloqueos al licenciatario, cero firmas fuera de turno y cero IPs bloqueadas después del partido."

*(Partido de práctica a x30 con juez automático: 3,1 %. Con un juez firmando desde la web y la base, a x10: 7 de 7 y 6,3 %, porque a x10 los 10 segundos del juez son casi 2 minutos de partido. Evidencia en `entrega/practica-juez-automatico/` y `entrega/practica-juez-humano/`. Si la corrida del final da otros números, reemplazarlos.)*

### 5. Quién paga y qué hace falta (2:35–2:50)
> "Lo paga quien pierde la plata: los titulares de derechos, que según la industria pierden cientos de millones de dólares por año solo en Argentina. El mismo problema está en Perú, México y Colombia. El juez y los proveedores lo usan sin costo. El software nunca fue lo caro: en Italia los proveedores reclaman unos 10 millones de euros por año de trabajo manual. A nosotros vigilar un partido nos cuesta centavos de dólar de nube, según nuestra estimación. Para arrancar alcanza con un piloto en un partido de la liga y una resolución del ENACOM que obligue a cada proveedor a tener un canal electrónico de órdenes. Está en nuestra propuesta normativa y en `escenarios-y-modelo.md`."

### 6. Cierre (2:50–3:00)
> "Un juez, en segundos, con evidencia, y llegando a todos. Somos Alejo, Selene, Luciano, Rocío y Nahuel."

---

## Video de respaldo (hasta 3 minutos)
Se graba sobre un partido de práctica con `--acelerar 6` (con OBS o Win+Alt+R) y se sube a Hacki. **Es también el plan B si falla el Wi-Fi en el pitch.**

| Tiempo | Pantalla | Qué se dice |
|---|---|---|
| 0:00–0:15 | Título + la frase de la idea | El problema en una oración |
| 0:15–0:40 | Simulador y plataforma arrancando; llega el primer pedido al celular | "Detección → expediente → juez" |
| 0:40–1:20 | Pantalla del juez: tarjeta de pelotaya, después la de golazo (IP compartida → nombre) | Evidencia y control de daño colateral |
| 1:20–1:50 | Firmar en lote; las casillas de órdenes pasan a verde; el reintento de Cumbre | Proveedores, confirmación, reintento |
| 1:50–2:15 | Minuto 50: cambio de turno y ratificación | Juez de turno real, firma válida |
| 2:15–2:35 | Expediente con hashes; auditoría alterada → alerta | Integridad de la evidencia |
| 2:35–2:55 | Fin del partido: las IP vencen solas. Salida de `evaluacion/verificar.py` | Vencimiento + números finales |
| 2:55–3:00 | Repo y nombres | — |

## Preguntas probables del jurado
Respuestas de 15 segundos. El detalle y las fuentes están en `coordinacion/investigacion/soluciones-parecidas.md`.

| Si preguntan | Respondemos |
|---|---|
| ¿Y el sobrebloqueo? | Si la IP es compartida (CDN u hosting), bloqueamos solo el nombre. Toda IP vence al terminar el partido. El registro público deja que cualquiera vea si su sitio cayó y reclame. |
| ¿Existe un juez de turno que firme esto un domingo a la noche? | Hoy no lo sabemos: es parte de la propuesta normativa (una acordada de turno). Sin firma no sale ninguna orden: preferimos no bloquear antes que bloquear sin juez. |
| ¿Por qué no administrativo, como Brasil o Perú, que es más rápido? | Porque el art. 57 de la Ley 27.078 exige orden judicial. Nuestro objetivo es que firmar tarde lo mismo que un aviso administrativo. |
| Se van a VPN o a DNS públicos. | Una minoría sí. Apuntamos al acceso masivo durante los 90 minutos y lo medimos con la visibilidad residual. En el Reino Unido, bloquear muchos sitios a la vez bajó la piratería un 16 a 22 %, aunque había VPN (estudio de Carnegie Mellon sobre sitios en general, no sobre fútbol en vivo). |
| ¿Hay pruebas de que el bloqueo en vivo funciona? | No hay un estudio específico, y la Comisión Europea lo admite. Por eso el registro público genera esos datos. |
| LaLiga ya tiene su orden en Argentina. ¿Para qué esto? | Esas órdenes pueden pasar por la plataforma y ganan acuse por proveedor, vencimiento y la regla anti-CDN. Somos el canal, no un competidor. |
| ¿Quién paga? Los ISP chicos no pueden. | Paga el titular de derechos. Para el proveedor es gratis y recibe el tipo de bloqueo que declaró que puede aplicar. |
| ¿No viola la neutralidad de red? | El art. 56 la garantiza y el art. 57 admite el bloqueo con orden judicial. Cada orden la tiene, con alcance y vencimiento. |
| ¿El Estado va a vigilar qué mira la gente? | No. Se detectan streams piratas, no usuarios. Los expedientes no tienen datos de abonados. |
| ¿Cuánto cuesta? | De nube, entre 20 y 60 dólares por mes para 30 partidos (estimación nuestra con precios de Vercel y Neon). Lo caro es la operación, y la cubre el titular. |
| ¿Por qué no copian a Italia o España? | Italia bloquea sin juez y rompió miles de sitios legítimos. España tiene juez, pero la lista la arma LaLiga: unas 3.000 IP por fin de semana con una sentencia que nombra 120. Y acá la Ley 27.078 (art. 57) exige orden judicial: el juez no se saca, se lo pone en el centro. |
| ¿Lo que vimos es real? | Decir qué está simulado (proveedores, firma HMAC, datos) y qué no. |

## Números que no decimos en el escenario
Se contradicen entre fuentes o los publica solo la industria:
- **% de hogares argentinos que piratean** (42,6 / 45,5 / 46 / 54,4 %): el 42,6 % parece ser el promedio de LatAm. Si hace falta: "cerca de la mitad, según la industria".
- **Pérdidas en dólares de Argentina** (258 / 571 / 590 millones): no hay cifra auditada. Decir "cientos de millones, según la industria".
- **El "60 %" de LaLiga**: son dos afirmaciones distintas, las dos autodeclaradas. No usar.
- **Costo de Piracy Shield**: va de 20 mil a 2 millones de euros según la fuente. Usar solo los ~10 M€/año que reclaman los proveedores.
- **Nuestra velocidad**: solo la que muestre el cronómetro de la demo.

## Antes de subir
- [ ] Cronómetro en pantalla durante la demo: desde la detección hasta la confirmación del último proveedor
- [x] Números reales del verificador en la sección 4 (práctica; actualizar con el final si cambian)
- [ ] Video grabado y subido a Hacki
- [ ] URL pública de Vercel funcionando desde un celular
- [ ] `entrega/` con el expediente y la auditoría del partido final, y la propuesta normativa
- [ ] Ensayado con cronómetro, dos veces
