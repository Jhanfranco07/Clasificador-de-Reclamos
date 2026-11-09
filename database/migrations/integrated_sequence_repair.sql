-- Run with the writers and old pool connections drained, as the sequence owner.
BEGIN;
SET LOCAL lock_timeout = '5s';
SELECT pg_advisory_xact_lock(20261106);

DO $repair$
DECLARE
    item record;
    max_id numeric;
    last_id numeric;
    called boolean;
    next_id numeric;
BEGIN
    FOR item IN
        SELECT tbl.oid::regclass AS relation, col.attname AS column_name,
               seq.oid::regclass AS sequence, spec.seqincrement, spec.seqmax, spec.seqcycle
        FROM pg_catalog.pg_depend dep
        JOIN pg_catalog.pg_class seq ON seq.oid = dep.objid AND seq.relkind = 'S'
        JOIN pg_catalog.pg_sequence spec ON spec.seqrelid = seq.oid
        JOIN pg_catalog.pg_class tbl ON tbl.oid = dep.refobjid AND tbl.relkind IN ('r', 'p')
        JOIN pg_catalog.pg_attribute col ON col.attrelid = tbl.oid AND col.attnum = dep.refobjsubid
        WHERE dep.classid = 'pg_class'::regclass AND dep.refclassid = 'pg_class'::regclass
          AND dep.deptype IN ('a', 'i') AND tbl.relnamespace = 'public'::regnamespace
          AND NOT EXISTS (
              SELECT FROM pg_catalog.pg_depend extension_member
              WHERE extension_member.classid = 'pg_class'::regclass
                AND extension_member.objid = tbl.oid AND extension_member.deptype = 'e'
          )
        ORDER BY tbl.oid, col.attnum
    LOOP
        IF item.seqincrement <> 1 OR item.seqcycle THEN
            RAISE EXCEPTION 'Secuencia requiere revisión manual: %', item.sequence;
        END IF;
        EXECUTE format('LOCK TABLE %s IN SHARE ROW EXCLUSIVE MODE', item.relation);
        EXECUTE format('SELECT max(%I) FROM %s', item.column_name, item.relation) INTO max_id;
        EXECUTE format('SELECT last_value, is_called FROM %s', item.sequence) INTO last_id, called;
        next_id := last_id + called::int;
        IF max_id IS NOT NULL AND next_id <= max_id THEN
            next_id := max_id + 1;
            IF next_id > item.seqmax THEN
                RAISE EXCEPTION 'Secuencia agotada: %', item.sequence;
            END IF;
            -- RESTART rolls back with this transaction. setval does not.
            EXECUTE format('ALTER SEQUENCE %s RESTART WITH %s', item.sequence, next_id);
        END IF;
    END LOOP;
END
$repair$;
COMMIT;
