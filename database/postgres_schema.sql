CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS categorias_reclamo (
    id_categoria SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    descripcion TEXT,
    es_critica INTEGER NOT NULL DEFAULT 0 CHECK (es_critica IN (0, 1)),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prioridades (
    id_prioridad SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    nivel INTEGER NOT NULL UNIQUE,
    descripcion TEXT,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS estados_reclamo (
    id_estado SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    descripcion TEXT,
    es_final INTEGER NOT NULL DEFAULT 0 CHECK (es_final IN (0, 1)),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    correo TEXT NOT NULL UNIQUE,
    rol TEXT NOT NULL CHECK (rol IN ('AGENTE', 'SUPERVISOR', 'ADMINISTRADOR')),
    estado TEXT NOT NULL DEFAULT 'ACTIVO' CHECK (estado IN ('ACTIVO', 'INACTIVO')),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clientes (
    id_cliente SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    correo TEXT NOT NULL,
    telefono TEXT,
    estado TEXT NOT NULL DEFAULT 'ACTIVO' CHECK (estado IN ('ACTIVO', 'INACTIVO')),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auth_users (
    id_auth_user SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    correo TEXT NOT NULL UNIQUE,
    telefono TEXT,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('CLIENT', 'AGENT', 'ADMIN')),
    estado TEXT NOT NULL DEFAULT 'ACTIVO' CHECK (estado IN ('ACTIVO', 'INACTIVO')),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pedidos (
    id_pedido SERIAL PRIMARY KEY,
    codigo_pedido TEXT NOT NULL UNIQUE,
    id_cliente INTEGER NOT NULL REFERENCES clientes(id_cliente),
    tienda_nombre TEXT NOT NULL,
    tienda_imagen TEXT,
    estado TEXT NOT NULL DEFAULT 'PREPARING'
        CHECK (estado IN ('DELIVERED', 'IN_TRANSIT', 'CANCELLED', 'DELAYED', 'PREPARING')),
    total REAL NOT NULL DEFAULT 0,
    metodo_pago TEXT NOT NULL DEFAULT 'Tarjeta',
    direccion_entrega TEXT NOT NULL,
    repartidor TEXT,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_entrega_estimada TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pedido_items (
    id_item SERIAL PRIMARY KEY,
    id_pedido INTEGER NOT NULL REFERENCES pedidos(id_pedido) ON DELETE CASCADE,
    nombre_producto TEXT NOT NULL,
    cantidad INTEGER NOT NULL DEFAULT 1,
    precio REAL NOT NULL DEFAULT 0,
    imagen TEXT
);

CREATE TABLE IF NOT EXISTS restaurantes (
    id_restaurante SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL,
    categoria TEXT NOT NULL,
    rating REAL NOT NULL DEFAULT 4.5,
    tiempo_entrega TEXT NOT NULL DEFAULT '25-35 min',
    costo_delivery REAL NOT NULL DEFAULT 4.9,
    imagen TEXT,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS productos (
    id_producto SERIAL PRIMARY KEY,
    id_restaurante INTEGER NOT NULL REFERENCES restaurantes(id_restaurante) ON DELETE CASCADE,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    precio REAL NOT NULL DEFAULT 0,
    imagen TEXT,
    disponible INTEGER NOT NULL DEFAULT 1 CHECK (disponible IN (0, 1)),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reclamos (
    id_reclamo SERIAL PRIMARY KEY,
    codigo_reclamo TEXT NOT NULL UNIQUE,
    id_cliente INTEGER NOT NULL REFERENCES clientes(id_cliente),
    codigo_pedido TEXT NOT NULL,
    canal_venta TEXT NOT NULL,
    fecha_pedido TEXT,
    descripcion TEXT NOT NULL,
    id_categoria INTEGER REFERENCES categorias_reclamo(id_categoria),
    id_prioridad INTEGER REFERENCES prioridades(id_prioridad),
    id_estado INTEGER NOT NULL REFERENCES estados_reclamo(id_estado),
    id_usuario_asignado INTEGER REFERENCES usuarios(id_usuario),
    responsable_asignado TEXT,
    requiere_revision_humana INTEGER NOT NULL DEFAULT 1 CHECK (requiere_revision_humana IN (0, 1)),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_cierre TIMESTAMP,
    tiempo_atencion_minutos INTEGER
);

CREATE TABLE IF NOT EXISTS notificaciones (
    id_notificacion SERIAL PRIMARY KEY,
    correo_cliente TEXT NOT NULL,
    id_reclamo INTEGER REFERENCES reclamos(id_reclamo) ON DELETE SET NULL,
    titulo TEXT NOT NULL,
    mensaje TEXT NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'INFO' CHECK (tipo IN ('INFO', 'RESPUESTA', 'ALERTA')),
    leida INTEGER NOT NULL DEFAULT 0 CHECK (leida IN (0, 1)),
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS claim_messages (
    id_mensaje SERIAL PRIMARY KEY,
    id_reclamo INTEGER NOT NULL REFERENCES reclamos(id_reclamo) ON DELETE CASCADE,
    sender_type TEXT NOT NULL CHECK (sender_type IN ('client', 'agent', 'ai', 'system')),
    sender_id TEXT,
    mensaje TEXT NOT NULL,
    is_internal INTEGER NOT NULL DEFAULT 0 CHECK (is_internal IN (0, 1)),
    read_at TIMESTAMP,
    metadata_json JSONB,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS analisis_ia (
    id_analisis SERIAL PRIMARY KEY,
    id_reclamo INTEGER NOT NULL UNIQUE REFERENCES reclamos(id_reclamo) ON DELETE CASCADE,
    categoria_detectada TEXT,
    confianza REAL NOT NULL DEFAULT 0 CHECK (confianza >= 0 AND confianza <= 1),
    sentimiento TEXT CHECK (sentimiento IN ('POSITIVO', 'NEUTRO', 'NEGATIVO')),
    palabras_clave TEXT,
    entidades_detectadas TEXT,
    recomendacion TEXT,
    modelo_usado TEXT DEFAULT 'modelo_simulado_reglas',
    fecha_analisis TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documentos_base (
    id_documento SERIAL PRIMARY KEY,
    titulo TEXT NOT NULL,
    tipo_documento TEXT NOT NULL CHECK (tipo_documento IN ('POLITICA', 'FAQ', 'PROCEDIMIENTO', 'MANUAL')),
    categoria_asociada TEXT,
    contenido TEXT NOT NULL,
    ruta_archivo TEXT,
    estado_indexacion TEXT NOT NULL DEFAULT 'INDEXADO' CHECK (estado_indexacion IN ('PENDIENTE', 'INDEXADO', 'ERROR')),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fragmentos_documento (
    id_fragmento SERIAL PRIMARY KEY,
    id_documento INTEGER NOT NULL REFERENCES documentos_base(id_documento) ON DELETE CASCADE,
    texto_fragmento TEXT NOT NULL,
    orden_fragmento INTEGER NOT NULL DEFAULT 1,
    embedding_id TEXT,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS rag_embeddings (
    id_embedding SERIAL PRIMARY KEY,
    id_fragmento INTEGER NOT NULL UNIQUE REFERENCES fragmentos_documento(id_fragmento) ON DELETE CASCADE,
    id_documento INTEGER NOT NULL REFERENCES documentos_base(id_documento) ON DELETE CASCADE,
    modelo_embedding TEXT NOT NULL,
    dimension INTEGER NOT NULL,
    embedding vector(1536) NOT NULL,
    texto_fragmento TEXT NOT NULL,
    titulo TEXT,
    tipo_documento TEXT,
    categoria_asociada TEXT,
    fecha_creacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_rag_embeddings_vector
ON rag_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE TABLE IF NOT EXISTS respuestas_sugeridas (
    id_respuesta SERIAL PRIMARY KEY,
    id_reclamo INTEGER NOT NULL REFERENCES reclamos(id_reclamo) ON DELETE CASCADE,
    respuesta_generada TEXT NOT NULL,
    respuesta_editada TEXT,
    respuesta_final TEXT,
    estado_revision TEXT NOT NULL DEFAULT 'PENDIENTE'
        CHECK (estado_revision IN ('PENDIENTE', 'EDITADA', 'APROBADA', 'RECHAZADA', 'ENVIADA')),
    id_usuario_revision INTEGER REFERENCES usuarios(id_usuario),
    fecha_generacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_revision TIMESTAMP
);

CREATE TABLE IF NOT EXISTS documentos_consultados (
    id_documento_consultado SERIAL PRIMARY KEY,
    id_respuesta INTEGER NOT NULL REFERENCES respuestas_sugeridas(id_respuesta) ON DELETE CASCADE,
    id_documento INTEGER NOT NULL REFERENCES documentos_base(id_documento),
    score_similitud REAL,
    fragmento_usado TEXT,
    fecha_consulta TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS configuracion_modelo_ia (
    id_configuracion SERIAL PRIMARY KEY,
    nombre_configuracion TEXT NOT NULL UNIQUE,
    modelo_base TEXT NOT NULL DEFAULT 'modelo_simulado_reglas',
    umbral_confianza REAL NOT NULL DEFAULT 0.85 CHECK (umbral_confianza >= 0 AND umbral_confianza <= 1),
    revision_humana_obligatoria INTEGER NOT NULL DEFAULT 1 CHECK (revision_humana_obligatoria IN (0, 1)),
    usar_rag INTEGER NOT NULL DEFAULT 1 CHECK (usar_rag IN (0, 1)),
    max_documentos_recuperados INTEGER NOT NULL DEFAULT 3,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    fecha_actualizacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS historial_estados (
    id_historial SERIAL PRIMARY KEY,
    id_reclamo INTEGER NOT NULL REFERENCES reclamos(id_reclamo) ON DELETE CASCADE,
    estado_anterior TEXT,
    estado_nuevo TEXT NOT NULL,
    accion TEXT NOT NULL,
    comentario TEXT,
    usuario_responsable TEXT DEFAULT 'Agente de soporte',
    fecha_cambio TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS comentarios_agente (
    id_comentario SERIAL PRIMARY KEY,
    id_reclamo INTEGER NOT NULL REFERENCES reclamos(id_reclamo) ON DELETE CASCADE,
    comentario TEXT NOT NULL,
    tipo_comentario TEXT NOT NULL DEFAULT 'INTERNO'
        CHECK (tipo_comentario IN ('INTERNO', 'SEGUIMIENTO', 'ESCALAMIENTO', 'CIERRE')),
    usuario_responsable TEXT DEFAULT 'Agente de soporte',
    fecha_comentario TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS evaluacion_respuesta (
    id_evaluacion SERIAL PRIMARY KEY,
    id_respuesta INTEGER NOT NULL REFERENCES respuestas_sugeridas(id_respuesta) ON DELETE CASCADE,
    claridad INTEGER NOT NULL CHECK (claridad BETWEEN 1 AND 5),
    utilidad INTEGER NOT NULL CHECK (utilidad BETWEEN 1 AND 5),
    tono INTEGER NOT NULL CHECK (tono BETWEEN 1 AND 5),
    fundamentacion INTEGER NOT NULL CHECK (fundamentacion BETWEEN 1 AND 5),
    requiere_mejora INTEGER NOT NULL DEFAULT 0 CHECK (requiere_mejora IN (0, 1)),
    observacion TEXT,
    usuario_evaluador TEXT DEFAULT 'Supervisor de soporte',
    fecha_evaluacion TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS dataset_entrenamiento (
    id_dataset SERIAL PRIMARY KEY,
    texto TEXT NOT NULL,
    categoria TEXT NOT NULL,
    fuente TEXT NOT NULL DEFAULT 'dataset_simulado',
    usado_entrenamiento INTEGER NOT NULL DEFAULT 1 CHECK (usado_entrenamiento IN (0, 1)),
    fecha_registro TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logs_sistema (
    id_log SERIAL PRIMARY KEY,
    modulo TEXT NOT NULL,
    accion TEXT NOT NULL,
    nivel TEXT NOT NULL DEFAULT 'INFO' CHECK (nivel IN ('INFO', 'WARNING', 'ERROR')),
    detalle TEXT,
    id_reclamo INTEGER REFERENCES reclamos(id_reclamo) ON DELETE SET NULL,
    fecha_log TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_historial_reclamo ON historial_estados(id_reclamo);
CREATE INDEX IF NOT EXISTS idx_historial_fecha ON historial_estados(fecha_cambio);
CREATE INDEX IF NOT EXISTS idx_comentarios_reclamo ON comentarios_agente(id_reclamo);
CREATE INDEX IF NOT EXISTS idx_evaluacion_respuesta ON evaluacion_respuesta(id_respuesta);
CREATE INDEX IF NOT EXISTS idx_dataset_categoria ON dataset_entrenamiento(categoria);
CREATE INDEX IF NOT EXISTS idx_logs_modulo ON logs_sistema(modulo);
CREATE INDEX IF NOT EXISTS idx_logs_reclamo ON logs_sistema(id_reclamo);
CREATE INDEX IF NOT EXISTS idx_auth_users_correo ON auth_users(correo);
CREATE INDEX IF NOT EXISTS idx_pedidos_cliente ON pedidos(id_cliente);
CREATE INDEX IF NOT EXISTS idx_pedido_items_pedido ON pedido_items(id_pedido);
CREATE INDEX IF NOT EXISTS idx_productos_restaurante ON productos(id_restaurante);
CREATE INDEX IF NOT EXISTS idx_notificaciones_correo ON notificaciones(correo_cliente);
CREATE INDEX IF NOT EXISTS idx_claim_messages_reclamo ON claim_messages(id_reclamo, fecha_creacion);
