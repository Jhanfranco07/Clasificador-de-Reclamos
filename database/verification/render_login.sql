-- Execute through the proposed Render connection on isolated staging.
-- No row contents or credentials are returned.
BEGIN READ ONLY;

DO $check$
DECLARE
    item record;
BEGIN
    IF current_user <> 'smartclaim_backend' OR session_user <> current_user
       OR EXISTS (
           SELECT FROM pg_roles WHERE rolname = current_user
             AND (NOT rolcanlogin OR rolsuper OR rolbypassrls OR rolcreaterole
                  OR rolcreatedb OR rolreplication OR rolinherit)
       )
       OR EXISTS (SELECT FROM pg_auth_members WHERE member = current_user::regrole)
       OR NOT has_schema_privilege(current_user, 'public', 'USAGE')
       OR has_schema_privilege(current_user, 'public', 'CREATE')
       OR EXISTS (
           SELECT FROM pg_class WHERE relnamespace = 'public'::regnamespace
             AND relowner = current_user::regrole
       ) THEN
        RAISE EXCEPTION 'Unexpected PostgreSQL service identity or privileges';
    END IF;

    FOR item IN SELECT * FROM (VALUES
        ('auth_users', 'SELECT,INSERT,UPDATE'),
        ('pedidos', 'SELECT,INSERT,UPDATE'),
        ('reclamos', 'SELECT,INSERT,UPDATE'),
        ('documentos_base', 'SELECT'),
        ('fragmentos_documento', 'SELECT'),
        ('rag_embeddings', 'SELECT')
    ) AS checks(relation, privileges)
    LOOP
        IF EXISTS (
            SELECT FROM unnest(string_to_array(item.privileges, ',')) AS required(privilege)
            WHERE NOT has_table_privilege(current_user, 'public.' || item.relation, required.privilege)
        ) OR NOT EXISTS (
            SELECT FROM pg_class WHERE oid = to_regclass('public.' || item.relation)
              AND relrowsecurity AND relforcerowsecurity
        ) THEN
            RAISE EXCEPTION 'Missing runtime privilege or RLS for %', item.relation;
        END IF;
    END LOOP;

    IF has_table_privilege(current_user, 'public.documentos_base', 'INSERT,UPDATE,DELETE,TRUNCATE')
       OR has_table_privilege(current_user, 'public.fragmentos_documento', 'INSERT,UPDATE,DELETE,TRUNCATE')
       OR has_table_privilege(current_user, 'public.rag_embeddings', 'INSERT,UPDATE,DELETE,TRUNCATE')
       OR has_table_privilege(current_user, 'public.reclamos', 'DELETE,TRUNCATE')
       OR has_sequence_privilege(current_user, pg_get_serial_sequence('public.pedidos', 'id_pedido'), 'UPDATE') THEN
        RAISE EXCEPTION 'Excess runtime privileges';
    END IF;

    IF has_sequence_privilege(current_user, pg_get_serial_sequence('public.pedidos', 'id_pedido'), 'USAGE') IS DISTINCT FROM true
       OR NOT EXISTS (
           SELECT FROM pg_attribute WHERE attrelid = 'public.rag_embeddings'::regclass
             AND attname = 'embedding' AND format_type(atttypid, atttypmod) = 'vector(1536)'
       ) THEN
        RAISE EXCEPTION 'Order sequence or vector type is incompatible';
    END IF;

    PERFORM id_pedido FROM public.pedidos WHERE false;
    PERFORM id_reclamo FROM public.reclamos WHERE false;
    PERFORM id_documento FROM public.documentos_base WHERE false;
END
$check$;

SELECT current_user AS verified_role;
ROLLBACK;
