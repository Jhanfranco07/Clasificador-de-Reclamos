-- Run after 2C. Keep historic claims with no confirmed order link.
BEGIN;
SET LOCAL lock_timeout = '5s';
SET LOCAL search_path = public, pg_catalog;
SELECT pg_advisory_xact_lock(20261106);

CREATE INDEX IF NOT EXISTS idx_pedidos_restaurante ON public.pedidos(id_restaurante);
CREATE INDEX IF NOT EXISTS idx_reclamos_pedido ON public.reclamos(id_pedido);
CREATE INDEX IF NOT EXISTS idx_comercio_operadores_user
    ON public.comercio_operadores(id_auth_user, id_restaurante);
CREATE UNIQUE INDEX IF NOT EXISTS idx_pedidos_id_cliente
    ON public.pedidos(id_pedido, id_cliente);

DO $integrity$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conrelid = 'public.reclamos'::regclass
          AND conname = 'reclamos_pedido_cliente_fk'
    ) THEN
        ALTER TABLE public.reclamos ADD CONSTRAINT reclamos_pedido_cliente_fk
            FOREIGN KEY (id_pedido, id_cliente) REFERENCES public.pedidos(id_pedido, id_cliente);
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conrelid = 'public.reclamos'::regclass
          AND conname = 'reclamos_pedido_cliente_fk' AND convalidated
          AND contype = 'f' AND confrelid = 'public.pedidos'::regclass
          AND pg_get_constraintdef(oid) = 'FOREIGN KEY (id_pedido, id_cliente) REFERENCES pedidos(id_pedido, id_cliente)'
    ) THEN
        RAISE EXCEPTION 'La FK reclamos_pedido_cliente_fk requiere revisión manual';
    END IF;
END
$integrity$;
COMMIT;
