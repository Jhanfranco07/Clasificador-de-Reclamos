CREATE TABLE IF NOT EXISTS schema_migrations (version TEXT PRIMARY KEY, applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP);
ALTER TABLE auth_users DROP CONSTRAINT IF EXISTS auth_users_rol_check;
ALTER TABLE auth_users ADD CONSTRAINT auth_users_rol_check CHECK (rol IN ('CLIENT','AGENT','ADMIN','MERCHANT','COURIER'));
ALTER TABLE pedidos DROP CONSTRAINT IF EXISTS pedidos_estado_check;
ALTER TABLE pedidos ADD CONSTRAINT pedidos_estado_check CHECK (estado IN ('DELIVERED','IN_TRANSIT','CANCELLED','DELAYED','PREPARING','RECEIVED','ACCEPTED','READY_FOR_PICKUP'));
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS version_operativa INTEGER NOT NULL DEFAULT 0;
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS recogido_at TEXT;
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS entregado_at TEXT;
ALTER TABLE restaurantes ADD COLUMN IF NOT EXISTS direccion TEXT;
ALTER TABLE restaurantes ADD COLUMN IF NOT EXISTS responsable TEXT;
CREATE TABLE IF NOT EXISTS comercio_operadores (
    id_restaurante INTEGER NOT NULL REFERENCES restaurantes(id_restaurante),
    id_auth_user INTEGER NOT NULL REFERENCES auth_users(id_auth_user),
    puede_editar_productos INTEGER NOT NULL DEFAULT 0 CHECK (puede_editar_productos IN (0,1)),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0,1)),
    PRIMARY KEY (id_restaurante,id_auth_user)
);
CREATE TABLE IF NOT EXISTS courier_profiles (
    id_auth_user INTEGER PRIMARY KEY REFERENCES auth_users(id_auth_user),
    disponible INTEGER NOT NULL DEFAULT 0 CHECK (disponible IN (0,1))
);
CREATE TABLE IF NOT EXISTS pedido_asignaciones (
    id_pedido INTEGER PRIMARY KEY REFERENCES pedidos(id_pedido),
    id_courier INTEGER NOT NULL REFERENCES auth_users(id_auth_user),
    asignado_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS pedido_eventos (
    request_id TEXT PRIMARY KEY,
    id_pedido INTEGER NOT NULL REFERENCES pedidos(id_pedido),
    actor_id INTEGER NOT NULL REFERENCES auth_users(id_auth_user),
    actor_nombre TEXT NOT NULL,
    actor_rol TEXT NOT NULL,
    accion TEXT NOT NULL,
    estado_anterior TEXT,
    estado_nuevo TEXT NOT NULL,
    motivo TEXT,
    courier_id INTEGER REFERENCES auth_users(id_auth_user),
    payload_json TEXT NOT NULL,
    version_operativa INTEGER NOT NULL,
    fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (id_pedido,version_operativa)
);
CREATE INDEX IF NOT EXISTS idx_pedido_eventos_order ON pedido_eventos(id_pedido,fecha);
CREATE INDEX IF NOT EXISTS idx_asignaciones_courier ON pedido_asignaciones(id_courier);
CREATE TABLE IF NOT EXISTS operaciones_auditoria (
    request_id TEXT PRIMARY KEY,
    actor_id INTEGER NOT NULL REFERENCES auth_users(id_auth_user),
    actor_nombre TEXT NOT NULL,
    actor_rol TEXT NOT NULL,
    accion TEXT NOT NULL,
    recurso_id INTEGER NOT NULL,
    detalle TEXT NOT NULL,
    fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO schema_migrations(version) VALUES ('20261106_phase2b') ON CONFLICT (version) DO NOTHING;
