-- Additive only. Review/apply explicitly on an isolated database before deployment.
-- No historical claim is deleted or automatically linked by this migration.
ALTER TABLE reclamos ADD COLUMN IF NOT EXISTS id_pedido INTEGER REFERENCES pedidos(id_pedido);
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS id_restaurante INTEGER REFERENCES restaurantes(id_restaurante);
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS notas_entrega TEXT;
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS subtotal REAL;
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS costo_delivery REAL;
ALTER TABLE pedidos ADD COLUMN IF NOT EXISTS costo_servicio REAL;
ALTER TABLE pedido_items ADD COLUMN IF NOT EXISTS id_producto INTEGER REFERENCES productos(id_producto);
