PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO categorias_reclamo (nombre, descripcion, es_critica) VALUES
('Retraso de pedido', 'Demoras en la entrega o cambios excesivos en el tiempo estimado.', 0),
('Cobro indebido', 'Montos incorrectos, doble cobro o cargos no reconocidos.', 1),
('Producto incorrecto', 'El cliente recibió un producto diferente al solicitado.', 0),
('Producto incompleto', 'El pedido llegó con productos faltantes.', 0),
('Problema con tarjeta', 'Fallos al pagar, registrar o validar un método de pago.', 1),
('Fraude o seguridad', 'Accesos no reconocidos, uso indebido de cuenta o actividad sospechosa.', 1),
('Soporte general', 'Consultas o solicitudes que no pertenecen a categorías críticas.', 0);

INSERT OR IGNORE INTO prioridades (nombre, nivel, descripcion) VALUES
('Baja', 1, 'Consulta o incidencia sin impacto urgente.'),
('Media', 2, 'Caso que requiere atención, pero no es crítico.'),
('Alta', 3, 'Caso sensible con posible impacto económico o reputacional.'),
('Crítica', 4, 'Caso relacionado con fraude, seguridad, pérdida o riesgo alto.');

INSERT OR IGNORE INTO estados_reclamo (nombre, descripcion, es_final) VALUES
('Nuevo', 'Reclamo registrado y pendiente de análisis.', 0),
('Analizado por IA', 'Reclamo procesado por el módulo de IA.', 0),
('En revisión', 'Caso pendiente de validación por agente humano.', 0),
('Respondido', 'Respuesta enviada o aprobada para el cliente.', 1),
('Escalado', 'Caso derivado a un nivel superior de atención.', 0),
('Cerrado', 'Reclamo finalizado.', 1);

INSERT OR IGNORE INTO usuarios (nombre, correo, rol) VALUES
('Ana Torres', 'ana.torres@smartclaim.local', 'AGENTE'),
('Luis Herrera', 'luis.herrera@smartclaim.local', 'SUPERVISOR'),
('María Salas', 'maria.salas@smartclaim.local', 'ADMINISTRADOR');

INSERT OR IGNORE INTO configuracion_modelo_ia
(nombre_configuracion, modelo_base, umbral_confianza, revision_humana_obligatoria, usar_rag, max_documentos_recuperados)
VALUES
('Configuración principal', 'modelo_simulado_reglas', 0.85, 1, 1, 3);

INSERT OR IGNORE INTO documentos_base (id_documento, titulo, tipo_documento, categoria_asociada, contenido, estado_indexacion) VALUES
(1, 'Política de reembolsos por retraso', 'POLITICA', 'Retraso de pedido',
'Cuando el pedido presenta un retraso considerable, el agente debe revisar el tiempo estimado, la evidencia del pedido y el historial del cliente. El reembolso o compensación solo procede si la política vigente lo permite y debe ser validado por un agente.',
'INDEXADO'),
(2, 'Procedimiento para cobros indebidos', 'PROCEDIMIENTO', 'Cobro indebido',
'Ante un reclamo por doble cobro o cargo no reconocido, se debe solicitar validación del código de pedido, monto cobrado y medio de pago. Estos casos requieren revisión humana obligatoria antes de emitir una respuesta final.',
'INDEXADO'),
(3, 'FAQ sobre productos incorrectos o incompletos', 'FAQ', 'Producto incorrecto',
'Si el cliente recibe un producto distinto o incompleto, el agente debe verificar el detalle del pedido, solicitar evidencia si corresponde y ofrecer una solución según las políticas internas.',
'INDEXADO'),
(4, 'Manual de atención por fraude o seguridad', 'MANUAL', 'Fraude o seguridad',
'Los casos de acceso no reconocido, pedidos no autorizados o sospecha de fraude deben escalarse inmediatamente al área de seguridad. No se debe confirmar información sensible por canales no verificados.',
'INDEXADO'),
(5, 'Guía de soporte general', 'FAQ', 'Soporte general',
'Para consultas generales, el agente debe brindar una respuesta clara, cordial y orientada a resolver la duda del cliente. Si la solicitud no corresponde al área, debe derivarse al canal adecuado.',
'INDEXADO'),
(6, 'Procedimiento para problemas con tarjeta', 'PROCEDIMIENTO', 'Problema con tarjeta',
'Cuando el cliente reporta problemas con tarjeta, validación de pago o rechazo de transacción, el agente debe verificar el estado del pedido, el medio de pago y evitar solicitar datos sensibles completos.',
'INDEXADO');

INSERT OR IGNORE INTO fragmentos_documento (id_documento, texto_fragmento, orden_fragmento, embedding_id)
SELECT id_documento, contenido, 1, 'emb_doc_' || id_documento
FROM documentos_base
WHERE id_documento NOT IN (SELECT id_documento FROM fragmentos_documento);
