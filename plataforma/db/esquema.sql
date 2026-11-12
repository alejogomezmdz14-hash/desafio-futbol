-- Estado vivo del partido: lo escribe el motor en cada ciclo (~1 s), lo lee la web.
CREATE TABLE IF NOT EXISTS partidos (
  partido_id     TEXT PRIMARY KEY,
  datos          JSONB NOT NULL,        -- la forma de GET /api/estado (contratos §5)
  actualizado_ts TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS casos (
  partido_id TEXT NOT NULL, caso_id TEXT NOT NULL,
  clasificacion TEXT, datos JSONB NOT NULL,
  PRIMARY KEY (partido_id, caso_id)
);

CREATE TABLE IF NOT EXISTS expedientes (
  partido_id TEXT NOT NULL, expediente_id TEXT NOT NULL,
  hash TEXT NOT NULL, datos JSONB NOT NULL,
  PRIMARY KEY (partido_id, expediente_id)
);

-- La decisión del juez va en columnas propias: la web solo toca esas.
CREATE TABLE IF NOT EXISTS pedidos (
  partido_id TEXT NOT NULL, pedido_id TEXT NOT NULL,
  estado TEXT NOT NULL DEFAULT 'pendiente',   -- pendiente | aprobado | rechazado
  juez_id TEXT, juzgado_id TEXT, decidido_min REAL, motivo_rechazo TEXT,
  despachado BOOLEAN NOT NULL DEFAULT FALSE,  -- lo pone el motor al tomarlo
  datos JSONB NOT NULL,                       -- el resto del Pedido (contratos §4)
  PRIMARY KEY (partido_id, pedido_id)
);

CREATE TABLE IF NOT EXISTS ordenes (
  partido_id TEXT NOT NULL, orden_id TEXT NOT NULL,
  pedido_id TEXT, proveedor_id TEXT, estado TEXT,
  datos JSONB NOT NULL,
  PRIMARY KEY (partido_id, orden_id)
);

CREATE TABLE IF NOT EXISTS reclamos (
  partido_id TEXT NOT NULL, reclamo_id TEXT NOT NULL,
  estado TEXT, datos JSONB NOT NULL,
  PRIMARY KEY (partido_id, reclamo_id)
);

-- Pedidos de la web al motor que no son aprobar o rechazar: asumir turno y levantar por reclamo.
CREATE TABLE IF NOT EXISTS solicitudes (
  partido_id TEXT NOT NULL, solicitud_id TEXT NOT NULL,
  tipo TEXT NOT NULL,                  -- asumir_turno | levantar
  datos JSONB NOT NULL,                -- el body del POST
  creada_ts TEXT NOT NULL,
  resultado JSONB,                     -- lo completa el motor; NULL = pendiente
  PRIMARY KEY (partido_id, solicitud_id)
);

-- Solo el motor escribe acá. La cadena de hashes la calcula evidencia (T03).
CREATE TABLE IF NOT EXISTS auditoria (
  partido_id TEXT NOT NULL, seq INTEGER NOT NULL,
  hash TEXT NOT NULL, hash_prev TEXT NOT NULL,
  datos JSONB NOT NULL,                -- el EventoAuditoria completo (contratos §7)
  PRIMARY KEY (partido_id, seq)
);

-- Salida de evaluacion/verificar.py de los partidos de demo (T12).
CREATE TABLE IF NOT EXISTS verificaciones (
  partido_id TEXT PRIMARY KEY, salida TEXT NOT NULL, creada_ts TEXT NOT NULL
);

-- Quién firmó cada decisión (T13): el nombre del link del juez, o "Coordinación (PIN)".
CREATE TABLE IF NOT EXISTS firmas (
  partido_id TEXT NOT NULL, pedido_id TEXT NOT NULL,
  firmado_por TEXT NOT NULL, via TEXT NOT NULL, creada_ts TEXT NOT NULL,
  PRIMARY KEY (partido_id, pedido_id)
);

-- Ajustes de la plataforma (T13): por ejemplo, la generación de accesos que permite cortarlos todos.
CREATE TABLE IF NOT EXISTS ajustes (
  clave TEXT PRIMARY KEY, valor TEXT NOT NULL
);

-- Usuarios de jueces para login con usuario/correo y contraseña (T14).
CREATE TABLE IF NOT EXISTS usuarios (
  usuario       TEXT PRIMARY KEY,
  nombre        TEXT NOT NULL,
  password_hash TEXT NOT NULL,
  creado_ts     TEXT NOT NULL
);
