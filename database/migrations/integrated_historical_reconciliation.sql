-- Conciliación idempotente de relaciones históricas inequívocas.
-- No crea asociaciones cuando hay cero o más de un candidato.
BEGIN;

WITH unique_merchants AS (
    SELECT p.id_pedido, min(r.id_restaurante) AS id_restaurante
    FROM public.pedidos p
    JOIN public.restaurantes r
      ON lower(trim(r.nombre)) = lower(trim(p.tienda_nombre))
    WHERE p.id_restaurante IS NULL
    GROUP BY p.id_pedido
    HAVING count(*) = 1
)
UPDATE public.pedidos p
SET id_restaurante = u.id_restaurante
FROM unique_merchants u
WHERE p.id_pedido = u.id_pedido
  AND p.id_restaurante IS NULL;

WITH unique_orders AS (
    SELECT r.id_reclamo, min(p.id_pedido) AS id_pedido
    FROM public.reclamos r
    JOIN public.pedidos p
      ON p.codigo_pedido = r.codigo_pedido
     AND p.id_cliente = r.id_cliente
    WHERE r.id_pedido IS NULL
    GROUP BY r.id_reclamo
    HAVING count(*) = 1
)
UPDATE public.reclamos r
SET id_pedido = u.id_pedido
FROM unique_orders u
WHERE r.id_reclamo = u.id_reclamo
  AND r.id_pedido IS NULL;

COMMIT;
