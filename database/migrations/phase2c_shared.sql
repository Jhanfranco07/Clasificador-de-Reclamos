CREATE TABLE IF NOT EXISTS claim_commands (
    request_id TEXT PRIMARY KEY,
    id_reclamo INTEGER NOT NULL REFERENCES reclamos(id_reclamo),
    actor_auth_id INTEGER REFERENCES auth_users(id_auth_user),
    accion TEXT NOT NULL,
    payload TEXT NOT NULL,
    fecha TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_notificaciones_evento ON notificaciones(clave_evento);
CREATE INDEX IF NOT EXISTS idx_notificaciones_destino ON notificaciones(id_destinatario,leida,id_notificacion);
CREATE INDEX IF NOT EXISTS idx_claim_responsable ON reclamos(responsable_auth_id);
CREATE INDEX IF NOT EXISTS idx_claim_commands_claim ON claim_commands(id_reclamo);
