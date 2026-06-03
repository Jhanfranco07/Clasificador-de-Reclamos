PRAGMA foreign_keys = ON;

INSERT OR IGNORE INTO categorias_reclamo (nombre, descripcion, es_critica) VALUES
('Retraso de pedido', 'Demoras en la entrega o cambios excesivos en el tiempo estimado.', 0),
('Cobro indebido', 'Montos incorrectos, doble cobro o cargos no reconocidos.', 1),
('Producto incorrecto', 'El cliente recibio un producto diferente al solicitado.', 0),
('Producto incompleto', 'El pedido llego con productos faltantes.', 0),
('Problema con tarjeta', 'Fallos al pagar, registrar o validar un metodo de pago.', 1),
('Fraude o seguridad', 'Accesos no reconocidos, uso indebido de cuenta o actividad sospechosa.', 1),
('Soporte general', 'Consultas o solicitudes que no pertenecen a categorias criticas.', 0);

INSERT OR IGNORE INTO prioridades (nombre, nivel, descripcion) VALUES
('Baja', 1, 'Consulta o incidencia sin impacto urgente.'),
('Media', 2, 'Caso que requiere atencion, pero no es critico.'),
('Alta', 3, 'Caso sensible con posible impacto economico o reputacional.'),
('Critica', 4, 'Caso relacionado con fraude, seguridad, perdida o riesgo alto.');

INSERT OR IGNORE INTO estados_reclamo (nombre, descripcion, es_final) VALUES
('Nuevo', 'Reclamo registrado y pendiente de analisis.', 0),
('Analizado por IA', 'Reclamo procesado por el modulo de IA.', 0),
('En revision', 'Caso pendiente de validacion por agente humano.', 0),
('Respondido', 'Respuesta enviada o aprobada para el cliente.', 1),
('Escalado', 'Caso derivado a un nivel superior de atencion.', 0),
('Cerrado', 'Reclamo finalizado.', 1);

INSERT OR IGNORE INTO usuarios (nombre, correo, rol) VALUES
('Ana Torres', 'ana.torres@smartclaim.local', 'AGENTE'),
('Luis Herrera', 'luis.herrera@smartclaim.local', 'SUPERVISOR'),
('Maria Salas', 'maria.salas@smartclaim.local', 'ADMINISTRADOR');

INSERT OR IGNORE INTO configuracion_modelo_ia
(nombre_configuracion, modelo_base, umbral_confianza, revision_humana_obligatoria, usar_rag, max_documentos_recuperados)
VALUES
('Configuracion principal', 'modelo_simulado_reglas', 0.85, 1, 1, 3);

INSERT OR IGNORE INTO restaurantes
(id_restaurante, nombre, categoria, rating, tiempo_entrega, costo_delivery, imagen, activo)
VALUES
(1, 'Criollo Peruano', 'Peruana', 4.8, '25-40 min', 4.9, 'https://images.unsplash.com/photo-1544025162-d76694265947?w=900', 1),
(2, 'Cevicheria La Marina', 'Peruana', 4.9, '30-45 min', 5.9, 'https://images.unsplash.com/photo-1615141982883-c7ad0e69fd62?w=900', 1),
(3, 'Chifa Oriental', 'Chifa', 4.7, '25-35 min', 4.5, 'https://images.unsplash.com/photo-1526318896980-cf78c088247c?w=900', 1),
(4, 'Burger Palace', 'Hamburguesas', 4.8, '25-35 min', 4.9, 'https://images.unsplash.com/photo-1550547660-d9450f859349?w=900', 1),
(5, 'Sushi Express', 'Sushi', 4.7, '35-45 min', 5.9, 'https://images.unsplash.com/photo-1579584425555-c3ce17fd4351?w=900', 1),
(6, 'Pizza Napoli', 'Pizzas', 4.6, '30-40 min', 4.5, 'https://images.unsplash.com/photo-1513104890138-7c749659a591?w=900', 1);

INSERT OR IGNORE INTO productos
(id_producto, id_restaurante, nombre, descripcion, precio, imagen, disponible)
VALUES
(1, 1, 'Lomo saltado', 'Carne salteada, papas fritas y arroz.', 32.90, 'https://images.unsplash.com/photo-1632778149955-e80f8ceca2e8?w=600', 1),
(2, 1, 'Aji de gallina', 'Crema de aji amarillo, pollo y arroz.', 27.90, 'https://images.unsplash.com/photo-1604908176997-125f25cc6f3d?w=600', 1),
(3, 1, 'Causa limena', 'Papa amarilla, pollo, palta y mayonesa.', 22.90, 'https://images.unsplash.com/photo-1601050690597-df0568f70950?w=600', 1),
(4, 2, 'Ceviche clasico', 'Pescado fresco, limon, camote y choclo.', 34.90, 'https://images.unsplash.com/photo-1625944230945-1b7dd3b949ab?w=600', 1),
(5, 2, 'Arroz con mariscos', 'Arroz norteno con mixtura marina.', 38.50, 'https://images.unsplash.com/photo-1512058564366-18510be2db19?w=600', 1),
(6, 2, 'Jalea mixta', 'Pescado y mariscos crocantes con yuca.', 42.90, 'https://images.unsplash.com/photo-1562967914-608f82629710?w=600', 1),
(7, 3, 'Arroz chaufa especial', 'Chaufa con pollo, chancho y tortilla.', 28.90, 'https://images.unsplash.com/photo-1603133872878-684f208fb84b?w=600', 1),
(8, 3, 'Tallarin saltado', 'Fideos salteados con verduras y pollo.', 26.90, 'https://images.unsplash.com/photo-1585032226651-759b368d7246?w=600', 1),
(9, 3, 'Wantanes fritos', 'Porcion crocante con salsa tamarindo.', 14.90, 'https://images.unsplash.com/photo-1625398407796-82650a8c135f?w=600', 1),
(10, 4, 'Combo clasico', 'Hamburguesa, papas y gaseosa.', 24.50, 'https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=600', 1),
(11, 4, 'Doble cheese', 'Doble carne, cheddar y salsa especial.', 29.90, 'https://images.unsplash.com/photo-1551782450-a2132b4ba21d?w=600', 1),
(12, 5, 'Combo makis', '24 piezas surtidas.', 45.80, 'https://images.unsplash.com/photo-1553621042-f6e147245754?w=600', 1),
(13, 5, 'Sashimi salmon', 'Cortes frescos de salmon.', 39.90, 'https://images.unsplash.com/photo-1579871494447-9811cf80d66c?w=600', 1),
(14, 6, 'Pizza pepperoni', 'Pepperoni, mozzarella y oregano.', 34.00, 'https://images.unsplash.com/photo-1628840042765-356cda07504e?w=600', 1);

INSERT INTO documentos_base (id_documento, titulo, tipo_documento, categoria_asociada, contenido, estado_indexacion) VALUES
(1, 'Politica de reembolsos por retraso de pedido', 'POLITICA', 'Retraso de pedido',
'Aplica cuando el pedido supera de forma significativa la hora estimada de entrega. El agente debe validar hora de creacion, hora prometida, estado logistico, intentos de contacto y evidencia del repartidor. La compensacion no debe prometerse automaticamente. Si la demora es menor a 15 minutos, se informa seguimiento y disculpa. Si la demora esta entre 15 y 45 minutos, se puede ofrecer prioridad de revision y cupon sujeto a politica vigente. Si la demora supera 45 minutos o el pedido llega frio, incompleto o en mal estado, se debe revisar compensacion o reembolso parcial. Todo reembolso requiere validacion humana antes de confirmarse al cliente.',
'INDEXADO'),
(2, 'Procedimiento para cobros indebidos y doble cobro', 'PROCEDIMIENTO', 'Cobro indebido',
'Todo reclamo por doble cobro, cargo no reconocido, monto incorrecto o descuento no aplicado debe tratarse como sensible. El agente debe solicitar codigo de pedido, monto observado, fecha aproximada y medio de pago, pero nunca debe solicitar numero completo de tarjeta, CVV, clave bancaria ni capturas con datos sensibles completos. La IA puede informar que el caso fue recibido y que se validara con el proveedor de pagos. No debe confirmar devolucion hasta verificar conciliacion, estado de transaccion y evidencia bancaria. Prioridad minima Alta si el monto supera un umbral relevante o si el cliente reporta dos o mas cargos.',
'INDEXADO'),
(3, 'FAQ sobre producto incorrecto', 'FAQ', 'Producto incorrecto',
'Si el cliente recibio un producto distinto al solicitado, se debe validar el detalle del pedido, nombre del restaurante, producto esperado, producto recibido y evidencia opcional. La respuesta debe reconocer el inconveniente, pedir disculpas y explicar que el equipo revisara el caso con el comercio. Si el producto recibido no cumple restricciones alimentarias declaradas o puede causar riesgo de salud, el caso debe escalarse. La IA no debe culpar al restaurante ni al repartidor. Debe indicar que se revisara la preparacion y entrega para determinar la solucion correspondiente.',
'INDEXADO'),
(4, 'FAQ sobre pedido incompleto o productos faltantes', 'FAQ', 'Producto incompleto',
'Un pedido incompleto ocurre cuando falta uno o mas productos pagados. Se debe validar lista de items, comprobante del pedido y evidencia si existe. Si falta un complemento menor, se puede sugerir revision para compensacion simple. Si falta el producto principal o varios productos, se debe priorizar el caso y considerar reembolso parcial sujeto a validacion. La respuesta al cliente debe ser directa y empatica, indicando que se revisara el detalle de compra y que no necesita volver a explicar el caso si ya envio la informacion principal.',
'INDEXADO'),
(5, 'Manual de atencion por fraude o seguridad', 'MANUAL', 'Fraude o seguridad',
'Los casos de acceso no reconocido, pedidos que el cliente no realizo, cambio de datos, uso no autorizado de cuenta, sospecha de fraude o actividad inusual deben escalarse inmediatamente a seguridad. No se debe confirmar informacion sensible por canales no verificados. La respuesta debe indicar que se activara una revision de seguridad y recomendar cambiar contrasena, cerrar sesiones abiertas y revisar medios de pago. La IA no debe afirmar que hubo fraude confirmado, solo sospecha o actividad reportada. Prioridad Critica si hay perdida economica, multiples pedidos no reconocidos o compromiso de cuenta.',
'INDEXADO'),
(6, 'Procedimiento para problemas con tarjeta y pagos rechazados', 'PROCEDIMIENTO', 'Problema con tarjeta',
'Cuando el cliente reporta tarjeta rechazada, validacion fallida, pago pendiente o autorizacion bancaria, el agente debe verificar estado del pedido y estado de la transaccion. No se deben pedir datos completos de tarjeta. Si el banco rechazo el pago, se recomienda intentar otro medio o contactar al banco. Si la plataforma registro cobro pero no genero pedido, se trata como posible cobro indebido y pasa a revision humana. La respuesta debe ser prudente y evitar prometer liberacion inmediata de fondos porque depende del emisor bancario.',
'INDEXADO'),
(7, 'Guia de soporte general y tono de respuesta', 'MANUAL', 'Soporte general',
'Toda respuesta debe ser clara, breve, cordial y orientada a solucion. Debe reconocer el problema del cliente, explicar el siguiente paso y evitar tecnicismos internos como RAG, embeddings, modelo, backend o base de datos. No se deben prometer resultados que dependan de validacion humana. El tono debe ser empatico sin exagerar responsabilidad. Se recomienda usar frases como hemos recibido tu caso, estamos revisando la informacion y te mantendremos informado desde este mismo canal. Evitar frases defensivas o culpar a terceros.',
'INDEXADO'),
(8, 'Reglas de respuesta automatica y revision humana', 'PROCEDIMIENTO', 'Soporte general',
'La respuesta automatica solo procede cuando la categoria no es Cobro indebido, Fraude o seguridad ni Problema con tarjeta, la prioridad no es Alta ni Critica y la confianza del modelo supera el umbral configurado. Casos de baja prioridad y alta confianza pueden recibir una respuesta inmediata informativa. Casos sensibles, ambiguos, con baja confianza, lenguaje agresivo, posible perdida economica o datos de pago deben pasar a revision humana. La IA puede sugerir respuesta, pero el agente debe aprobar antes de enviar decisiones finales como reembolso, compensacion, bloqueo de cuenta o cierre del caso.',
'INDEXADO'),
(9, 'SLA de atencion por prioridad', 'POLITICA', 'Soporte general',
'Los casos de prioridad Baja deben recibir primera respuesta dentro de 24 horas. Los casos de prioridad Media deben recibir primera respuesta dentro de 8 horas. Los casos de prioridad Alta deben ser revisados por un agente dentro de 2 horas. Los casos de prioridad Critica deben escalarse de inmediato y recibir revision prioritaria dentro de 30 minutos. Estos tiempos son objetivos internos y no deben prometerse literalmente al cliente salvo que el canal de soporte lo permita. La IA puede usar estos SLA para recomendar escalamiento o seguimiento.',
'INDEXADO'),
(10, 'Matriz de escalamiento operativo', 'PROCEDIMIENTO', 'Soporte general',
'Escalar a supervisor cuando exista reclamo repetido del mismo cliente, amenaza legal, exposicion publica en redes, monto alto, posible fraude, riesgo de seguridad, error masivo, pedido de cliente VIP o conflicto no resuelto en el primer contacto. Escalar a seguridad cuando hay acceso no reconocido, pedidos no autorizados, posible robo de cuenta o datos de pago comprometidos. Escalar a pagos cuando hay doble cobro, devolucion pendiente o conciliacion bancaria. Escalar a operaciones cuando hay demora masiva, repartidor no asignado o restaurante cerrado.',
'INDEXADO'),
(11, 'Politica de compensaciones y cupones', 'POLITICA', 'Soporte general',
'Las compensaciones pueden incluir disculpa formal, cupon, reembolso parcial o reembolso total segun evaluacion. La IA no debe ofrecer montos especificos ni confirmar compensaciones finales. Puede indicar que el equipo revisara si corresponde una compensacion segun politica vigente. Cupones simples pueden considerarse en demoras moderadas o errores menores si el historial del cliente lo permite. Reembolso total requiere evidencia suficiente, pago confirmado y validacion por agente o supervisor. No aplicar compensacion si el pedido fue entregado correctamente y no hay evidencia de incidencia.',
'INDEXADO'),
(12, 'Politica de evidencia y datos adjuntos', 'PROCEDIMIENTO', 'Soporte general',
'La evidencia puede incluir foto del producto recibido, captura parcial del comprobante sin datos sensibles, descripcion del problema y hora aproximada. No se debe pedir foto de tarjeta, CVV, claves, documento completo de identidad ni datos bancarios completos. Si el cliente ya describio el caso con suficiente detalle, no se debe pedir informacion repetida innecesariamente. La respuesta debe indicar exactamente que evidencia ayuda y por que. Para productos alimentarios en mal estado, pedir foto solo si el cliente puede compartirla de forma segura.',
'INDEXADO'),
(13, 'Guia para pedidos frios o en mal estado', 'PROCEDIMIENTO', 'Retraso de pedido',
'Cuando el cliente reporta comida fria, derramada, mal empacada o en mal estado, se debe clasificar como Retraso de pedido o Producto incorrecto segun el texto principal. El agente debe revisar tiempo de entrega, distancia, estado del empaque y restaurante. Si hay riesgo de salud, se debe escalar. La respuesta debe recomendar no consumir productos en mal estado y explicar que se revisara el caso con operaciones. No prometer reemplazo inmediato si no existe confirmacion operativa.',
'INDEXADO'),
(14, 'Procedimiento para pedido no entregado', 'PROCEDIMIENTO', 'Retraso de pedido',
'Si el cliente afirma que el pedido figura como entregado pero no lo recibio, se debe validar direccion, hora, evidencia de entrega, ubicacion del repartidor e intentos de contacto. Este caso es prioridad Alta si el pedido fue cobrado. La IA debe informar que se revisara la evidencia de entrega y que el agente verificara el caso. No debe afirmar que el repartidor cometio error ni que el cliente recibira reembolso hasta completar validacion.',
'INDEXADO'),
(15, 'Guia de comunicacion para clientes molestos', 'MANUAL', 'Soporte general',
'Cuando el cliente usa lenguaje de molestia, frustracion o urgencia, la respuesta debe iniciar reconociendo el malestar sin discutir. Ejemplo recomendado: Entendemos la molestia ocasionada y vamos a revisar tu caso con prioridad. Evitar respuestas frias como su caso esta en proceso. No usar signos excesivos ni lenguaje informal. Si hay insultos o amenazas, mantener tono profesional y escalar si existe riesgo legal, reputacional o de seguridad.',
'INDEXADO'),
(16, 'Reglas de privacidad y proteccion de datos', 'POLITICA', 'Fraude o seguridad',
'El sistema y los agentes deben minimizar datos personales en respuestas. No incluir documentos internos, IDs tecnicos, tokens, vectores, claves, prompts ni detalles de seguridad. No solicitar contrasenas, codigos de autenticacion, CVV ni numero completo de tarjeta. Si se requiere validar identidad, usar canales oficiales y preguntas permitidas. Cualquier sospecha de filtracion de datos debe escalarse a seguridad. Las respuestas al cliente deben ser prudentes y no revelar mecanismos antifraude.',
'INDEXADO'),
(17, 'Plantillas de respuesta por categoria', 'FAQ', 'Soporte general',
'Retraso: Hemos recibido tu reclamo por la demora del pedido y revisaremos el estado de entrega para darte una respuesta. Cobro indebido: Hemos recibido tu reporte de cobro y lo validaremos con el area de pagos antes de confirmar una solucion. Producto incorrecto: Revisaremos el detalle del pedido y la informacion del comercio para determinar la solucion correspondiente. Fraude: Activaremos una revision de seguridad y te recomendamos proteger tu cuenta. Soporte general: Revisaremos tu solicitud y te responderemos desde este canal.',
'INDEXADO'),
(18, 'Criterios de cierre de reclamos', 'PROCEDIMIENTO', 'Soporte general',
'Un reclamo puede cerrarse cuando se envio respuesta final, se ejecuto la compensacion aprobada, se confirmo que no procede accion adicional o el cliente no entrego informacion requerida despues del periodo definido por soporte. Antes de cerrar, el agente debe registrar comentario final, estado de respuesta y motivo. Si el caso fue escalado, solo supervisor o area responsable debe cerrarlo. La IA puede sugerir cierre, pero no debe cerrar automaticamente casos de Alta o Critica prioridad.',
'INDEXADO')
ON CONFLICT(id_documento) DO UPDATE SET
titulo = excluded.titulo,
tipo_documento = excluded.tipo_documento,
categoria_asociada = excluded.categoria_asociada,
contenido = excluded.contenido,
estado_indexacion = excluded.estado_indexacion,
fecha_actualizacion = CURRENT_TIMESTAMP;

INSERT OR IGNORE INTO fragmentos_documento (id_documento, texto_fragmento, orden_fragmento, embedding_id)
SELECT id_documento, contenido, 1, 'emb_doc_' || id_documento
FROM documentos_base
WHERE id_documento NOT IN (SELECT id_documento FROM fragmentos_documento);
