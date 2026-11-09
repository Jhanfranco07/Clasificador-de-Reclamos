-- Dedicated SmartClaim public schema. Run after phase 2C, with psql ON_ERROR_STOP.
-- This is an operator migration. No password is provisioned by this file.
BEGIN;
SET LOCAL lock_timeout = '5s';
SELECT pg_advisory_xact_lock(20261106);

CREATE TABLE IF NOT EXISTS public.documentos_importados (
    external_id TEXT PRIMARY KEY,
    id_documento INTEGER NOT NULL UNIQUE REFERENCES public.documentos_base(id_documento),
    metadata TEXT NOT NULL
);

DO $security$
DECLARE
    item record;
    target regclass;
    operation text;
    rule_name text;
    table_columns text;
    sequence_name regclass;
    exposed_role text;
BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'smartclaim_backend') THEN
        CREATE ROLE smartclaim_backend LOGIN NOINHERIT NOBYPASSRLS NOSUPERUSER
            NOCREATEROLE NOCREATEDB NOREPLICATION;
    END IF;
    IF NOT EXISTS (
        SELECT FROM pg_roles
        WHERE rolname = 'smartclaim_backend' AND rolcanlogin
          AND NOT (rolsuper OR rolbypassrls OR rolcreaterole OR rolcreatedb OR rolreplication OR rolinherit)
    ) OR EXISTS (
        SELECT FROM pg_auth_members WHERE member = 'smartclaim_backend'::regrole
    ) THEN
        RAISE EXCEPTION 'smartclaim_backend debe ser un login dedicado sin privilegios ni membresías';
    END IF;

    REVOKE ALL ON SCHEMA public FROM PUBLIC, anon, authenticated, smartclaim_backend;
    GRANT USAGE ON SCHEMA public TO smartclaim_backend;
    IF to_regnamespace('extensions') IS NOT NULL THEN
        GRANT USAGE ON SCHEMA extensions TO smartclaim_backend;
    END IF;
    FOREACH exposed_role IN ARRAY ARRAY['anon', 'authenticated', 'authenticator', 'service_role'] LOOP
        IF pg_has_role(exposed_role, 'smartclaim_backend', 'MEMBER') THEN
            RAISE EXCEPTION 'El rol % puede asumir smartclaim_backend', exposed_role;
        END IF;
    END LOOP;
    IF has_schema_privilege('anon', 'public', 'USAGE')
       OR has_schema_privilege('authenticated', 'public', 'USAGE') THEN
        RAISE EXCEPTION 'Persiste acceso efectivo a public por membresía';
    END IF;

    -- Each operation needs both its grant and its own policy. FastAPI owns
    -- application authorization, while this login can only run the required SQL.
    FOR item IN SELECT * FROM (VALUES
        ('categorias_reclamo', 'SELECT'),
        ('prioridades', 'SELECT'),
        ('estados_reclamo', 'SELECT'),
        ('usuarios', ''),
        ('clientes', 'SELECT,INSERT,UPDATE'),
        ('auth_users', 'SELECT,INSERT,UPDATE'),
        ('restaurantes', 'SELECT,UPDATE'),
        ('productos', 'SELECT,UPDATE'),
        ('pedidos', 'SELECT,INSERT,UPDATE'),
        ('pedido_items', 'SELECT,INSERT'),
        ('reclamos', 'SELECT,INSERT,UPDATE'),
        ('notificaciones', 'SELECT,INSERT,UPDATE'),
        ('claim_messages', 'SELECT,INSERT'),
        ('analisis_ia', 'SELECT,INSERT,DELETE'),
        ('documentos_base', 'SELECT'),
        ('fragmentos_documento', 'SELECT'),
        ('rag_embeddings', 'SELECT'),
        ('respuestas_sugeridas', 'SELECT,INSERT,UPDATE'),
        ('documentos_consultados', 'SELECT,INSERT'),
        ('configuracion_modelo_ia', 'SELECT,UPDATE'),
        ('historial_estados', 'SELECT,INSERT'),
        ('comentarios_agente', 'SELECT,INSERT'),
        ('evaluacion_respuesta', 'SELECT'),
        ('dataset_entrenamiento', ''),
        ('logs_sistema', 'SELECT,INSERT'),
        ('schema_migrations', ''),
        ('comercio_operadores', 'SELECT,INSERT,UPDATE'),
        ('courier_profiles', 'SELECT,INSERT,UPDATE'),
        ('pedido_asignaciones', 'SELECT,INSERT,UPDATE'),
        ('pedido_eventos', 'SELECT,INSERT'),
        ('operaciones_auditoria', 'SELECT,INSERT'),
        ('claim_commands', 'SELECT,INSERT'),
        ('documentos_importados', '')
    ) AS manifest(table_name, operations)
    LOOP
        target := format('public.%I', item.table_name)::regclass;
        IF EXISTS (
            SELECT FROM pg_class
            WHERE oid = target AND (relkind <> 'r' OR relowner = 'smartclaim_backend'::regrole)
        ) OR EXISTS (
            SELECT FROM pg_policy WHERE polrelid = target AND polname NOT IN
                ('smartclaim_select', 'smartclaim_insert', 'smartclaim_update', 'smartclaim_delete')
        ) THEN
            RAISE EXCEPTION 'Objeto con propietario, tipo o políticas inesperadas: %', target;
        END IF;

        EXECUTE format(
            'REVOKE ALL ON TABLE %s FROM PUBLIC, anon, authenticated, service_role, smartclaim_backend', target
        );
        SELECT string_agg(quote_ident(attname), ', ' ORDER BY attnum) INTO table_columns
        FROM pg_attribute WHERE attrelid = target AND attnum > 0 AND NOT attisdropped;
        EXECUTE format(
            'REVOKE ALL (%s) ON TABLE %s FROM PUBLIC, anon, authenticated, service_role, smartclaim_backend',
            table_columns, target
        );
        EXECUTE format('ALTER TABLE %s ENABLE ROW LEVEL SECURITY', target);
        EXECUTE format('ALTER TABLE %s FORCE ROW LEVEL SECURITY', target);

        FOREACH operation IN ARRAY ARRAY['SELECT', 'INSERT', 'UPDATE', 'DELETE'] LOOP
            rule_name := 'smartclaim_' || lower(operation);
            EXECUTE format('DROP POLICY IF EXISTS %I ON %s', rule_name, target);
            IF operation = ANY (string_to_array(item.operations, ',')) THEN
                EXECUTE format('GRANT %s ON TABLE %s TO smartclaim_backend', operation, target);
                EXECUTE format(
                    'CREATE POLICY %I ON %s FOR %s TO smartclaim_backend %s',
                    rule_name, target, operation,
                    CASE operation
                        WHEN 'INSERT' THEN 'WITH CHECK (true)'
                        WHEN 'UPDATE' THEN 'USING (true) WITH CHECK (true)'
                        ELSE 'USING (true)'
                    END
                );
            END IF;
        END LOOP;

        FOR sequence_name IN
            SELECT pg_get_serial_sequence(target::text, attname)::regclass
            FROM pg_attribute WHERE attrelid = target AND attnum > 0 AND NOT attisdropped
        LOOP
            IF sequence_name IS NULL THEN
                CONTINUE;
            END IF;
            EXECUTE format(
                'REVOKE ALL ON SEQUENCE %s FROM PUBLIC, anon, authenticated, service_role, smartclaim_backend',
                sequence_name
            );
            IF 'INSERT' = ANY (string_to_array(item.operations, ',')) THEN
                EXECUTE format('GRANT USAGE ON SEQUENCE %s TO smartclaim_backend', sequence_name);
            END IF;
            FOREACH exposed_role IN ARRAY ARRAY['anon', 'authenticated', 'service_role'] LOOP
                IF has_sequence_privilege(exposed_role, sequence_name, 'USAGE,SELECT,UPDATE') THEN
                    RAISE EXCEPTION 'Permisos efectivos de % en %', exposed_role, sequence_name;
                END IF;
            END LOOP;
        END LOOP;

        FOREACH exposed_role IN ARRAY ARRAY['anon', 'authenticated', 'service_role'] LOOP
            IF has_table_privilege(exposed_role, target, 'SELECT,INSERT,UPDATE,DELETE,TRUNCATE,REFERENCES,TRIGGER')
               OR has_any_column_privilege(exposed_role, target, 'SELECT,INSERT,UPDATE,REFERENCES') THEN
                RAISE EXCEPTION 'Permisos efectivos de % en %', exposed_role, target;
            END IF;
        END LOOP;
    END LOOP;
END
$security$;

-- These defaults affect objects created by the executing migration owner.
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE ALL ON TABLES FROM PUBLIC, anon, authenticated, service_role;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    REVOKE ALL ON SEQUENCES FROM PUBLIC, anon, authenticated, service_role;
COMMIT;
