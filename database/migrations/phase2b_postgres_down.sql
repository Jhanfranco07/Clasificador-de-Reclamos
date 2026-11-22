-- Operator-reviewed rollback. Preserve extension columns, tables and audit records.
-- Run as one script with psql ON_ERROR_STOP against an isolated copy first.
BEGIN;
SELECT pg_advisory_xact_lock(20261106);
LOCK TABLE auth_users,pedidos IN ACCESS EXCLUSIVE MODE;
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM auth_users WHERE rol IN ('MERCHANT','COURIER'))
       OR EXISTS (SELECT 1 FROM pedidos WHERE estado IN ('RECEIVED','ACCEPTED','READY_FOR_PICKUP')) THEN
        RAISE EXCEPTION 'Rollback incompatible con datos nuevos. Conservar datos y revisar backup';
    END IF;
END $$;
ALTER TABLE auth_users DROP CONSTRAINT auth_users_rol_check;
ALTER TABLE auth_users ADD CONSTRAINT auth_users_rol_check CHECK (rol IN ('CLIENT','AGENT','ADMIN'));
ALTER TABLE pedidos DROP CONSTRAINT pedidos_estado_check;
ALTER TABLE pedidos ADD CONSTRAINT pedidos_estado_check CHECK (estado IN ('DELIVERED','IN_TRANSIT','CANCELLED','DELAYED','PREPARING'));
DELETE FROM schema_migrations WHERE version='20261106_phase2b';
COMMIT;
