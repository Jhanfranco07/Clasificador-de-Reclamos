BEGIN;
SELECT pg_advisory_xact_lock(20261107);
ALTER TABLE reclamos ADD COLUMN IF NOT EXISTS responsable_auth_id INTEGER REFERENCES auth_users(id_auth_user);
ALTER TABLE reclamos ADD COLUMN IF NOT EXISTS version_asignacion INTEGER NOT NULL DEFAULT 0;
ALTER TABLE reclamos ADD COLUMN IF NOT EXISTS fecha_asignacion TEXT;
ALTER TABLE historial_estados ADD COLUMN IF NOT EXISTS actor_auth_id INTEGER REFERENCES auth_users(id_auth_user);
ALTER TABLE historial_estados ADD COLUMN IF NOT EXISTS actor_rol TEXT;
ALTER TABLE respuestas_sugeridas ADD COLUMN IF NOT EXISTS revisor_auth_id INTEGER REFERENCES auth_users(id_auth_user);
ALTER TABLE comentarios_agente ADD COLUMN IF NOT EXISTS actor_auth_id INTEGER REFERENCES auth_users(id_auth_user);
ALTER TABLE notificaciones ADD COLUMN IF NOT EXISTS id_destinatario INTEGER REFERENCES auth_users(id_auth_user);
ALTER TABLE notificaciones ADD COLUMN IF NOT EXISTS id_pedido INTEGER REFERENCES pedidos(id_pedido);
ALTER TABLE notificaciones ADD COLUMN IF NOT EXISTS evento TEXT;
ALTER TABLE notificaciones ADD COLUMN IF NOT EXISTS clave_evento TEXT;
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

INSERT INTO schema_migrations(version) VALUES ('20261106_phase2c') ON CONFLICT (version) DO NOTHING;
COMMIT;
