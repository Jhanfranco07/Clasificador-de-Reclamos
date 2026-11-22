-- On an authorized isolated copy, during the write freeze.
-- First run without limits, then pass the five maxima from that run after migration.
\if :{?orders_max}
\else
  \set orders_max 9223372036854775807
  \set claims_max 9223372036854775807
  \set documents_max 9223372036854775807
  \set fragments_max 9223372036854775807
  \set embeddings_max 9223372036854775807
\endif

BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;
SET LOCAL TIME ZONE 'UTC';
SET LOCAL DateStyle = 'ISO, YMD';
SET LOCAL extra_float_digits = 3;

WITH base(relation, id, data) AS (
    SELECT 'pedidos', id_pedido, to_jsonb(t) - ARRAY[
        'id_restaurante','notas_entrega','subtotal','costo_delivery','costo_servicio',
        'version_operativa','recogido_at','entregado_at'
    ] FROM public.pedidos t WHERE id_pedido <= :'orders_max'::bigint
    UNION ALL
    SELECT 'reclamos', id_reclamo, to_jsonb(t) - ARRAY[
        'id_pedido','responsable_auth_id','version_asignacion','fecha_asignacion'
    ] FROM public.reclamos t WHERE id_reclamo <= :'claims_max'::bigint
    UNION ALL
    SELECT 'documentos_base', id_documento, to_jsonb(t)
    FROM public.documentos_base t WHERE id_documento <= :'documents_max'::bigint
    UNION ALL
    SELECT 'fragmentos_documento', id_fragmento, to_jsonb(t)
    FROM public.fragmentos_documento t WHERE id_fragmento <= :'fragments_max'::bigint
    UNION ALL
    SELECT 'rag_embeddings', id_embedding, to_jsonb(t)
    FROM public.rag_embeddings t WHERE id_embedding <= :'embeddings_max'::bigint
), relations(name) AS (
    VALUES ('pedidos'), ('reclamos'), ('documentos_base'), ('fragmentos_documento'), ('rag_embeddings')
)
SELECT name AS relation, count(id) AS rows, coalesce(max(id), 0) AS max_id,
       encode(sha256(convert_to(coalesce(string_agg(
           encode(sha256(convert_to(data::text, 'UTF8')), 'hex'), '' ORDER BY id
       ), ''), 'UTF8')), 'hex') AS sha256
FROM relations LEFT JOIN base ON name = relation
GROUP BY name
ORDER BY name;

ROLLBACK;
