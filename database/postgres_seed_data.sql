INSERT INTO categorias_reclamo (id_categoria, nombre, descripcion, es_critica) VALUES
(1, 'Retraso de pedido', 'Demoras en la entrega o cambios excesivos en el tiempo estimado.', 0),
(2, 'Cobro indebido', 'Montos incorrectos, doble cobro o cargos no reconocidos.', 1),
(3, 'Producto incorrecto', 'El cliente recibio un producto diferente al solicitado.', 0),
(4, 'Producto incompleto', 'El pedido llego con productos faltantes.', 0),
(5, 'Problema con tarjeta', 'Fallos al pagar, registrar o validar un metodo de pago.', 1),
(6, 'Fraude o seguridad', 'Accesos no reconocidos, uso indebido de cuenta o actividad sospechosa.', 1),
(7, 'Soporte general', 'Consultas o solicitudes que no pertenecen a categorias criticas.', 0)
ON CONFLICT (id_categoria) DO NOTHING;

INSERT INTO prioridades (id_prioridad, nombre, nivel, descripcion) VALUES
(1, 'Baja', 1, 'Consulta o incidencia sin impacto urgente.'),
(2, 'Media', 2, 'Caso que requiere atencion, pero no es critico.'),
(3, 'Alta', 3, 'Caso sensible con posible impacto economico o reputacional.'),
(4, 'Crítica', 4, 'Caso relacionado con fraude, seguridad, perdida o riesgo alto.')
ON CONFLICT (id_prioridad) DO NOTHING;

INSERT INTO estados_reclamo (id_estado, nombre, descripcion, es_final) VALUES
(1, 'Nuevo', 'Reclamo registrado y pendiente de analisis.', 0),
(2, 'Analizado por IA', 'Reclamo procesado por el modulo de IA.', 0),
(3, 'En revisión', 'Caso pendiente de validacion por agente humano.', 0),
(4, 'Respondido', 'Respuesta enviada o aprobada para el cliente.', 1),
(5, 'Escalado', 'Caso derivado a un nivel superior de atencion.', 0),
(6, 'Cerrado', 'Reclamo finalizado.', 1)
ON CONFLICT (id_estado) DO NOTHING;

INSERT INTO usuarios (id_usuario, nombre, correo, rol) VALUES
(1, 'Ana Torres', 'ana.torres@smartclaim.local', 'AGENTE'),
(2, 'Luis Herrera', 'luis.herrera@smartclaim.local', 'SUPERVISOR'),
(3, 'Maria Salas', 'maria.salas@smartclaim.local', 'ADMINISTRADOR')
ON CONFLICT (id_usuario) DO NOTHING;

INSERT INTO configuracion_modelo_ia
(id_configuracion, nombre_configuracion, modelo_base, umbral_confianza, revision_humana_obligatoria, usar_rag, max_documentos_recuperados)
VALUES
(1, 'Configuración principal', 'modelo_simulado_reglas', 0.85, 1, 1, 3)
ON CONFLICT (id_configuracion) DO NOTHING;

INSERT INTO documentos_base (id_documento, titulo, tipo_documento, categoria_asociada, contenido, estado_indexacion) VALUES
(1, 'Politica de reembolsos por retraso', 'POLITICA', 'Retraso de pedido',
'Cuando el pedido presenta un retraso considerable, el agente debe revisar el tiempo estimado, la evidencia del pedido y el historial del cliente. El reembolso o compensacion solo procede si la politica vigente lo permite y debe ser validado por un agente.',
'INDEXADO'),
(2, 'Procedimiento para cobros indebidos', 'PROCEDIMIENTO', 'Cobro indebido',
'Ante un reclamo por doble cobro o cargo no reconocido, se debe solicitar validacion del codigo de pedido, monto cobrado y medio de pago. Estos casos requieren revision humana obligatoria antes de emitir una respuesta final.',
'INDEXADO'),
(3, 'FAQ sobre productos incorrectos o incompletos', 'FAQ', 'Producto incorrecto',
'Si el cliente recibe un producto distinto o incompleto, el agente debe verificar el detalle del pedido, solicitar evidencia si corresponde y ofrecer una solucion segun las politicas internas.',
'INDEXADO'),
(4, 'Manual de atencion por fraude o seguridad', 'MANUAL', 'Fraude o seguridad',
'Los casos de acceso no reconocido, pedidos no autorizados o sospecha de fraude deben escalarse inmediatamente al area de seguridad. No se debe confirmar informacion sensible por canales no verificados.',
'INDEXADO'),
(5, 'Guia de soporte general', 'FAQ', 'Soporte general',
'Para consultas generales, el agente debe brindar una respuesta clara, cordial y orientada a resolver la duda del cliente. Si la solicitud no corresponde al area, debe derivarse al canal adecuado.',
'INDEXADO'),
(6, 'Procedimiento para problemas con tarjeta', 'PROCEDIMIENTO', 'Problema con tarjeta',
'Cuando el cliente reporta problemas con tarjeta, validacion de pago o rechazo de transaccion, el agente debe verificar el estado del pedido, el medio de pago y evitar solicitar datos sensibles completos.',
'INDEXADO')
ON CONFLICT (id_documento) DO NOTHING;

INSERT INTO fragmentos_documento (id_documento, texto_fragmento, orden_fragmento, embedding_id)
SELECT id_documento, contenido, 1, 'emb_doc_' || id_documento
FROM documentos_base
WHERE id_documento NOT IN (SELECT id_documento FROM fragmentos_documento);
