// Pantalla del juez de turno (T04). Habla solo con /api/* (coordinacion/contratos.md §5).
"use strict";

const REFRESCO_MS = 2000;
const CLAVE_SESION = "sesion-coordinacion";   // la comparte demo.html
const PROVEEDORES = { aurora: "Aurora", andina: "Andina", valle: "FibraValle", cumbre: "Cumbre" };
const ESTADOS_ORDEN = {
  enviando: "Enviando", recibida: "Recibida, aplicando", aplicada: "Bloqueado", fallida: "Falló, se reintenta",
  rechazada: "Rechazada", vencida: "Venció", levantada: "Levantada",
};

const $ = (id) => document.getElementById(id);
const estado = { token: leerToken(), juez: null, minuto: 0, pendientes: [], vistos: new Set(), primeraCarga: true };
let audio = null;

// ---------------------------------------------------------------------- utilidades

// Login simple de la coordinación (decisión 43): la sesión es un token que vence a las 12 horas.
function leerToken() { try { return localStorage.getItem(CLAVE_SESION); } catch { return null; } }
function guardarToken(t) { try { t ? localStorage.setItem(CLAVE_SESION, t) : localStorage.removeItem(CLAVE_SESION); } catch { /* sin storage */ } }
function mostrarAcceso(datos) {
  let el = document.getElementById("acceso");
  if (!el) {
    el = document.createElement("p"); el.id = "acceso"; el.className = "turno";
    document.querySelector(".marcador__texto").appendChild(el);
  }
  el.replaceChildren();
  if (!datos || !datos.nombre) return;
  const span = document.createElement("span");
  span.textContent = `Sesión: ${datos.nombre}`;
  const btnSalir = document.createElement("button");
  btnSalir.type = "button";
  btnSalir.className = "btn-salir-sesion";
  btnSalir.textContent = "Cerrar sesión";
  btnSalir.addEventListener("click", () => {
    estado.token = null; guardarToken(null);
    mostrarAcceso(null);
    pedirLogin("");
  });
  el.append(span, btnSalir);
}

function nombreJuez(id) {
  if (!id) return "nadie";
  const [cargo, nombre] = id.split("-");
  const cap = (s) => (s ? s[0].toUpperCase() + s.slice(1) : "");
  return `${cap(cargo)} ${cap(nombre)}`;
}
const proveedor = (id) => PROVEEDORES[id] || id;
const min = (m) => (m == null ? "—" : `${Math.floor(m)}'`);
function listaHumana(items) {
  if (items.length <= 1) return items.join("");
  return `${items.slice(0, -1).join(", ")} y ${items[items.length - 1]}`;
}

async function api(ruta, cuerpo) {
  const opciones = { headers: { "Content-Type": "application/json" } };
  if (estado.token) opciones.headers["Authorization"] = `Bearer ${estado.token}`;
  if (cuerpo !== undefined) { opciones.method = "POST"; opciones.body = JSON.stringify(cuerpo); }
  const r = await fetch(ruta, opciones);
  let datos = null;
  try { datos = await r.json(); } catch { /* sin cuerpo */ }
  if (r.status === 401) {   // la sesión venció o no es válida: se vuelve al ingreso y se dice por qué
    estado.token = null; guardarToken(null); mostrarAcceso(null);
    pedirLogin((datos && datos.error) || "Volvé a ingresar con el usuario y la contraseña.");
    throw new Error("401");
  }
  if (!r.ok) throw new Error((datos && datos.error) || `La plataforma respondió ${r.status}`);
  return datos;
}

function aviso(texto, tipo = "info", { titulo = null, boton = null, id = null, duracion = 0 } = {}) {
  if (id) { const viejo = document.querySelector(`[data-aviso="${id}"]`); if (viejo) viejo.remove(); }
  const div = document.createElement("div");
  div.className = `aviso${tipo === "error" ? " aviso--error" : tipo === "ok" ? " aviso--ok" : ""}`;
  if (id) div.dataset.aviso = id;
  if (titulo) { const s = document.createElement("strong"); s.textContent = titulo; div.append(s); }
  const p = document.createElement("p"); p.textContent = texto; div.append(p);
  if (boton) {
    const b = document.createElement("button");
    b.type = "button"; b.className = "boton boton--firmar boton--ancho"; b.textContent = boton.texto;
    b.addEventListener("click", boton.accion); div.append(b);
  }
  $("avisos").append(div);
  if (duracion) setTimeout(() => div.remove(), duracion);
  return div;
}
const quitarAviso = (id) => { const a = document.querySelector(`[data-aviso="${id}"]`); if (a) a.remove(); };

// ---------------------------------------------------------------------- avisos de pedido nuevo

function prepararAvisos() {
  estado.interactuo = true;   // el navegador solo deja vibrar o sonar después de un toque del usuario
  try { audio = audio || new (window.AudioContext || window.webkitAudioContext)(); } catch { audio = null; }
  if ("Notification" in window && Notification.permission === "default") Notification.requestPermission().catch(() => {});
}

function avisarNuevos(n) {
  if (estado.interactuo && navigator.vibrate) navigator.vibrate([120, 80, 120]);
  if (audio) {
    const o = audio.createOscillator(), g = audio.createGain();
    o.frequency.value = 880; g.gain.setValueAtTime(0.15, audio.currentTime);
    g.gain.exponentialRampToValueAtTime(0.001, audio.currentTime + 0.35);
    o.connect(g).connect(audio.destination); o.start(); o.stop(audio.currentTime + 0.35);
  }
  if (document.hidden && "Notification" in window && Notification.permission === "granted") {
    new Notification(n === 1 ? "Llegó un pedido de bloqueo" : `Llegaron ${n} pedidos de bloqueo`,
      { body: "Abrí la pantalla del juez para revisar la evidencia y firmar." });
  }
}

// ---------------------------------------------------------------------- textos del pedido

function textoBloqueo(p) {
  const r = p.resumen;
  const porIp = p.objetivos.filter((o) => o.tipo === "ip").map((o) => proveedor(o.proveedor_id));
  const porNombre = p.objetivos.filter((o) => o.tipo === "dominio").map((o) => proveedor(o.proveedor_id));
  if (r.tipo_recomendado === "ip") {
    let t = `La IP ${r.ip} en ${listaHumana(porIp)}.`;
    if (porNombre.length) t += ` En ${listaHumana(porNombre)}, el nombre ${r.host}, porque solo bloquea por nombre.`;
    return t;
  }
  // El cerebro ya explica por qué no se toca la IP (cuántos sitios ajenos o falta de datos): no se recalcula acá.
  const span = document.createElement("span");
  span.append(`Solo el nombre ${r.host}, en los ${p.objetivos.length} proveedores. `);
  const c = document.createElement("span");
  c.className = "compartida";
  c.textContent = `${r.motivo_tipo}.`;
  span.append(c);
  return span;
}

function textoPorque(r) {
  const span = document.createElement("span");
  span.append(r.motivo_clasificacion + ". ");
  const m = document.createElement("span"); m.className = "marca"; m.textContent = `Marca de agua ${r.marca}`;
  span.append(m);
  return span;
}

// ---------------------------------------------------------------------- render

function renderEstado(e) {
  estado.minuto = e.minuto_actual;
  estado.juez = (e.jueces_de_turno || [])[0] || null;
  $("minuto").textContent = Math.floor(e.minuto_actual);
  $("partido").textContent = e.finalizado ? `Partido ${e.partido_id} terminado` : `Partido ${e.partido_id} en juego`;
  $("juez").textContent = nombreJuez(estado.juez);
  $("avance").style.width = `${Math.min(100, (100 * e.minuto_actual) / e.fin_min)}%`;
  const marca = $("marca-turno");
  if (e.proximo_cambio_turno_min != null && e.proximo_cambio_turno_min < e.fin_min) {
    marca.hidden = false;
    marca.style.left = `${(100 * e.proximo_cambio_turno_min) / e.fin_min}%`;
    $("nota-turno").textContent = `Cambio de turno en el minuto ${Math.floor(e.proximo_cambio_turno_min)}`;
  } else { marca.hidden = true; $("nota-turno").textContent = ""; }

  if (!estado.juez && !e.finalizado) {
    aviso("En este minuto no figura ningún juez de turno. Los pedidos quedan esperando hasta que entre uno.", "error",
      { id: "sin-juez", titulo: "Sin juez de turno" });
  } else quitarAviso("sin-juez");

  estado.finalizado = !!e.finalizado;
  if (e.finalizado) {
    // Sin partido en juego no hay nada para firmar: se dice claro y se ofrece arrancar uno de práctica.
    quitarAviso("desconectado");
    if (!document.querySelector('[data-aviso="sin-partido"]')) {
      aviso("El último partido ya terminó, así que no hay pedidos para firmar. Arrancá uno de práctica para probar: en unos 30 segundos aparecen los pedidos acá.",
        "info", { id: "sin-partido", titulo: "No hay partido en juego",
                  boton: { texto: "Arrancar partido de práctica", accion: arrancarPractica } });
    }
  } else {
    quitarAviso("sin-partido");
    if (!e.simulador_ok) {
      aviso("La plataforma no recibe datos del partido hace unos segundos. Los pedidos nuevos pueden demorar.", "error",
        { id: "desconectado", titulo: "Motor desconectado" });
    } else quitarAviso("desconectado");
  }

  // Tras tocar "Asumir turno" el motor tarda 1-2 s en ratificar: no se vuelve a mostrar el aviso mientras tanto.
  const recienAsumido = estado.asumido && estado.asumido.juez === estado.juez && Date.now() - estado.asumido.t < 20000;
  if (estado.juez && e.turno_ratificado === false && !e.finalizado && !recienAsumido) {
    if (!document.querySelector('[data-aviso="traspaso"]')) {
      aviso(`${nombreJuez(estado.juez)}: las órdenes que firmó el turno anterior siguen vigentes. Asumí el turno para ratificarlas; hasta entonces sus reintentos quedan en espera.`,
        "info", { id: "traspaso", titulo: "Cambió el turno", boton: { texto: "Asumir turno y ratificar órdenes", accion: asumirTurno } });
    }
  } else quitarAviso("traspaso");
}

function renderPedidos(pedidos) {
  estado.pendientes = pedidos;
  const lista = $("pedidos");
  const nuevos = pedidos.filter((p) => !estado.vistos.has(p.pedido_id));
  const ids = new Set(pedidos.map((p) => p.pedido_id));
  for (const li of [...lista.children]) if (!ids.has(li.dataset.id)) li.remove();
  for (const p of pedidos) {
    if (lista.querySelector(`[data-id="${p.pedido_id}"]`)) continue;
    lista.append(crearTarjeta(p, !estado.primeraCarga));
  }
  pedidos.forEach((p) => estado.vistos.add(p.pedido_id));
  if (nuevos.length && !estado.primeraCarga) avisarNuevos(nuevos.length);
  estado.primeraCarga = false;

  const n = pedidos.length;
  $("cuenta").textContent = n;
  $("vacio").hidden = n > 0;
  document.title = n ? `(${n}) Juez de turno` : "Juez de turno";
  const boton = $("firmar-todos");
  boton.disabled = n === 0 || !estado.juez;
  const como = estado.juez ? ` como ${nombreJuez(estado.juez)}` : "";
  boton.textContent = n === 0 ? "No hay pedidos para firmar" : n === 1 ? `Firmar el pedido${como}` : `Firmar los ${n} pedidos${como}`;
}

function crearTarjeta(p, esNuevo) {
  const r = p.resumen;
  const li = $("tpl-pedido").content.firstElementChild.cloneNode(true);
  li.dataset.id = p.pedido_id;
  if (esNuevo) li.classList.add("pedido--nuevo");
  li.querySelector(".pedido__sitio").textContent = r.host;
  li.querySelector(".pedido__cuando").textContent = `detectado ${min(r.primer_minuto)}`;
  li.querySelector(".d-porque").append(textoPorque(r));
  li.querySelector(".d-servidor").textContent =
    `Servidor ${r.ip}${r.organizacion ? `, de ${r.organizacion}` : ""}.`;
  li.querySelector(".d-bloqueo").append(textoBloqueo(p));
  li.querySelector(".d-hasta").textContent = `Minuto ${p.vence_min}, fin del partido. Después se levanta sola.`;

  const exp = li.querySelector(".expediente");
  exp.addEventListener("toggle", () => { if (exp.open) cargarExpediente(p.expediente_id, exp.querySelector(".expediente__cuerpo")); });

  const rechazo = li.querySelector(".rechazo"), acciones = li.querySelector(".b-acciones");
  li.querySelector(".b-firmar").addEventListener("click", () => firmar([p.pedido_id]));
  li.querySelector(".b-rechazar").addEventListener("click", () => {
    rechazo.hidden = false; acciones.hidden = true; rechazo.querySelector("textarea").focus();
  });
  li.querySelector(".b-cancelar").addEventListener("click", () => { rechazo.hidden = true; acciones.hidden = false; });
  li.querySelector(".b-confirmar-rechazo").addEventListener("click", () => {
    const motivo = rechazo.querySelector("textarea").value.trim();
    if (!motivo) { rechazo.querySelector("textarea").focus(); return; }
    rechazar([p.pedido_id], motivo);
  });
  return li;
}

async function cargarExpediente(id, cuerpo) {
  try {
    const e = await api(`/api/expedientes/${encodeURIComponent(id)}`);
    cuerpo.replaceChildren();
    const fila = (titulo, valor, clase) => {
      const p = document.createElement("p"); const b = document.createElement("b");
      b.textContent = `${titulo}: `; p.append(b);
      const s = document.createElement("span"); if (clase) s.className = clase; s.textContent = valor; p.append(s);
      cuerpo.append(p);
    };
    fila("Expediente", e.expediente_id);
    fila("Huella del expediente (SHA-256)", e.hash, "hash");
    for (const c of e.capturas) fila(`Captura ${c.deteccion_id}, minuto ${Math.floor(c.capturada_min)}`, c.sha256, "hash");
    fila("Sitios en la misma IP", e.caso.dominios_en_ip.length ? e.caso.dominios_en_ip.join(", ") : "sin datos");
    fila("Por qué IP o nombre", e.caso.motivo_tipo);
    if (e.promocion && e.promocion.length) {
      fila("Dónde se promocionó", e.promocion.map((x) => `${x.red}: ${x.url}`).join("  |  "));
    }
  } catch (err) {
    cuerpo.textContent = `No se pudo abrir el expediente: ${err.message}`;
  }
}

function renderOrdenes(ordenes) {
  const cont = $("ordenes");
  $("vacio-ordenes").hidden = ordenes.length > 0;
  const ultimas = new Map();   // la orden más reciente por pedido y proveedor (los reintentos reemplazan)
  for (const o of ordenes) {
    const k = `${o.pedido_id}|${o.proveedor_id}`;
    const prev = ultimas.get(k);
    if (!prev || o.intentos >= prev.intentos) ultimas.set(k, o);
  }
  const porPedido = new Map();
  for (const o of ultimas.values()) {
    if (!porPedido.has(o.pedido_id)) porPedido.set(o.pedido_id, []);
    porPedido.get(o.pedido_id).push(o);
  }
  cont.replaceChildren();
  for (const [pid, os] of [...porPedido].reverse()) {
    const fila = document.createElement("div"); fila.className = "fila-orden";
    const t = document.createElement("p"); t.className = "fila-orden__titulo";
    const porNombre = os.find((o) => o.tipo === "dominio"), porIp = os.find((o) => o.tipo === "ip");
    t.textContent = `${(porNombre || porIp).objetivo} `;
    const s = document.createElement("small");
    s.textContent = `${porIp ? `IP ${porIp.objetivo}, ` : "solo por nombre, "}firmó ${nombreJuez(os[0].juez_id)}`;
    t.append(s);
    const casillas = document.createElement("div"); casillas.className = "casillas";
    for (const o of os) {
      const c = document.createElement("div"); c.className = `casilla casilla--${o.estado}`;
      const b = document.createElement("b"); b.textContent = proveedor(o.proveedor_id); c.append(b);
      let txt = ESTADOS_ORDEN[o.estado] || o.estado;
      if (o.estado === "aplicada") txt += ` desde ${min(o.aplicada_min)}`;
      if (o.intentos > 1) txt += ` (intento ${o.intentos})`;
      c.append(txt);
      casillas.append(c);
    }
    fila.append(t, casillas);
    cont.append(fila);
  }
}

// ---------------------------------------------------------------------- acciones

function resultado(hechos, errores, verbo) {
  if (hechos.length) {
    aviso(hechos.length === 1 ? `Firmaste ${verbo} 1 pedido.` : `Firmaste ${verbo} ${hechos.length} pedidos.`, "ok",
      { duracion: 4000, titulo: verbo === "la aprobación de" ? "Órdenes en camino a los proveedores" : null });
  }
  for (const e of errores) aviso(`${e.pedido_id}: ${e.error}`, "error", { duracion: 8000, titulo: "No se pudo firmar" });
}

async function firmar(ids) {
  if (!estado.juez || !ids.length) return;
  const boton = $("firmar-todos"); boton.disabled = true;
  try {
    const r = await api("/api/pedidos/aprobar", { pedido_ids: ids, juez_id: estado.juez });
    resultado(r.aprobados, r.errores, "la aprobación de");
  } catch (err) { if (err.message !== "401") aviso(err.message, "error", { duracion: 8000, titulo: "No se pudo firmar" }); }
  await refrescar();
}

async function rechazar(ids, motivo) {
  try {
    const r = await api("/api/pedidos/rechazar", { pedido_ids: ids, juez_id: estado.juez, motivo });
    resultado(r.rechazados, r.errores, "el rechazo de");
  } catch (err) { if (err.message !== "401") aviso(err.message, "error", { duracion: 8000, titulo: "No se pudo rechazar" }); }
  await refrescar();
}

async function arrancarPractica() {
  quitarAviso("sin-partido");
  aviso("Prendiendo el partido de práctica en la nube. Tarda unos segundos.", "info", { id: "arrancando", titulo: "Arrancando…" });
  try {
    const r = await api("/api/demo/iniciar", { acelerar: 10, juez_automatico: false });
    quitarAviso("arrancando");
    aviso(`Partido de práctica en marcha (dura unos ${Math.round(r.duracion_min)} minutos). En unos 30 segundos aparecen los pedidos.`,
      "ok", { duracion: 8000, titulo: "Arrancó el partido" });
  } catch (err) {
    quitarAviso("arrancando");
    if (err.message !== "401") aviso(err.message, "error", { duracion: 15000, titulo: "No se pudo arrancar el partido" });
  }
}

async function asumirTurno() {
  try {
    const r = await api("/api/turno/asumir", { juez_id: estado.juez });
    estado.asumido = { juez: estado.juez, t: Date.now() };
    quitarAviso("traspaso");
    aviso(`Ratificaste ${r.ratificadas.length} órdenes vigentes. Desde ahora los reintentos salen con tu firma.`, "ok",
      { duracion: 5000, titulo: `Turno asumido por ${nombreJuez(r.juez_id)}` });
  } catch (err) { if (err.message !== "401") aviso(err.message, "error", { duracion: 8000, titulo: "No se pudo asumir el turno" }); }
  await refrescar();
}

// ---------------------------------------------------------------------- ciclo

let refrescando = false;
async function refrescar() {
  if (refrescando || !estado.token) return;
  refrescando = true;
  try {
    const [e, p, o] = await Promise.all([api("/api/estado"), api("/api/pedidos?estado=pendiente"), api("/api/ordenes")]);
    quitarAviso("sin-red");
    renderEstado(e);
    // Los pedidos que quedaron sin firmar en un partido terminado ya no se pueden firmar: no se muestran como pendientes.
    renderPedidos(e.finalizado ? [] : p.pedidos.sort((a, b) => a.creado_min - b.creado_min));
    $("vacio").textContent = e.finalizado
      ? "El partido terminó. Los pedidos nuevos aparecen acá cuando arranque el próximo."
      : "No hay pedidos esperando. Cuando el radar detecte un stream pirata del partido, aparece acá con su evidencia.";
    renderOrdenes(o.ordenes);
  } catch (err) {
    if (err.message !== "401") {
      aviso("Sin conexión con la plataforma. Se reintenta solo cada 2 segundos.", "error", { id: "sin-red", titulo: "Sin conexión" });
    }
  } finally { refrescando = false; }
}

function pedirLogin(error = "") {
  estado.token = null; guardarToken(null);
  $("tablero").hidden = true; $("accion").hidden = true; $("ingreso").hidden = false;
  if ($("login-error")) $("login-error").textContent = error;
  if ($("usuario")) $("usuario").focus();
}

function entrar() {
  $("ingreso").hidden = true; $("tablero").hidden = false; $("accion").hidden = false;
  if ($("login-error")) $("login-error").textContent = "";
  refrescar();
}

if ($("form-login")) {
  $("form-login").addEventListener("submit", async (ev) => {
    ev.preventDefault();
    const usuario = $("usuario").value.trim();
    const password = $("password").value.trim();
    if ($("login-error")) $("login-error").textContent = "";
    if ($("btn-login")) $("btn-login").disabled = true;
    prepararAvisos();
    try {
      const r = await fetch("/api/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ usuario, password }),
      });
      const datos = await r.json().catch(() => ({}));
      if (!r.ok) {
        if ($("login-error")) $("login-error").textContent = datos.error || "Usuario o contraseña incorrectos";
        return;
      }
      estado.token = datos.token;
      guardarToken(datos.token);
      mostrarAcceso({ nombre: datos.nombre });
      entrar();
    } catch (err) {
      if ($("login-error")) $("login-error").textContent = "No se pudo iniciar sesión: " + err.message;
    } finally {
      if ($("btn-login")) $("btn-login").disabled = false;
    }
  });
}


$("firmar-todos").addEventListener("click", () => firmar(estado.pendientes.map((p) => p.pedido_id)));
document.addEventListener("click", prepararAvisos, { once: true });

if (estado.token) api("/api/sesion").then((q) => { mostrarAcceso(q); entrar(); }).catch(() => pedirLogin());
else pedirLogin();
setInterval(refrescar, REFRESCO_MS);
