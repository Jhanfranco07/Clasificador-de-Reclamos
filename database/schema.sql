PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS categorias_reclamo (
    id_categoria INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    descripcion TEXT,
    es_critica INTEGER NOT NULL DEFAULT 0 CHECK (es_critica IN (0, 1)),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prioridades (
    id_prioridad INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    nivel INTEGER NOT NULL UNIQUE,
    descripcion TEXT,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS estados_reclamo (
    id_estado INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL UNIQUE,
    descripcion TEXT,
    es_final INTEGER NOT NULL DEFAULT 0 CHECK (es_final IN (0, 1)),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    correo TEXT NOT NULL UNIQUE,
    rol TEXT NOT NULL CHECK (rol IN ('AGENTE', 'SUPERVISOR', 'ADMINISTRADOR')),
    estado TEXT NOT NULL DEFAULT 'ACTIVO' CHECK (estado IN ('ACTIVO', 'INACTIVO')),
    fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS clientes (
    id_cliente INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    correo TEXT NOT NULL,
    telefono TEXT,
    estado TEXT NOT NULL DEFAULT 'ACTIVO' CHECK (estado IN ('ACTIVO', 'INACTIVO')),
    fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS auth_users (
    id_auth_user INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    correo TEXT NOT NULL UNIQUE,
    telefono TEXT,
    password_hash TEXT NOT NULL,
    rol TEXT NOT NULL CHECK (rol IN ('CLIENT', 'AGENT', 'ADMIN')),
    estado TEXT NOT NULL DEFAULT 'ACTIVO' CHECK (estado IN ('ACTIVO', 'INACTIVO')),
    fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS pedidos (
    id_pedido INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_pedido TEXT NOT NULL UNIQUE,
    id_cliente INTEGER NOT NULL,
    tienda_nombre TEXT NOT NULL,
    tienda_imagen TEXT,
    estado TEXT NOT NULL DEFAULT 'PREPARING'
        CHECK (estado IN ('DELIVERED', 'IN_TRANSIT', 'CANCELLED', 'DELAYED', 'PREPARING')),
    total REAL NOT NULL DEFAULT 0,
    metodo_pago TEXT NOT NULL DEFAULT 'Tarjeta',
    direccion_entrega TEXT NOT NULL,
    repartidor TEXT,
    fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_entrega_estimada TEXT,
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente)
);

CREATE TABLE IF NOT EXISTS pedido_items (
    id_item INTEGER PRIMARY KEY AUTOINCREMENT,
    id_pedido INTEGER NOT NULL,
    nombre_producto TEXT NOT NULL,
    cantidad INTEGER NOT NULL DEFAULT 1,
    precio REAL NOT NULL DEFAULT 0,
    imagen TEXT,
    FOREIGN KEY (id_pedido) REFERENCES pedidos(id_pedido) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS restaurantes (
    id_restaurante INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre TEXT NOT NULL,
    categoria TEXT NOT NULL,
    rating REAL NOT NULL DEFAULT 4.5,
    tiempo_entrega TEXT NOT NULL DEFAULT '25-35 min',
    costo_delivery REAL NOT NULL DEFAULT 4.9,
    imagen TEXT,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS productos (
    id_producto INTEGER PRIMARY KEY AUTOINCREMENT,
    id_restaurante INTEGER NOT NULL,
    nombre TEXT NOT NULL,
    descripcion TEXT,
    precio REAL NOT NULL DEFAULT 0,
    imagen TEXT,
    disponible INTEGER NOT NULL DEFAULT 1 CHECK (disponible IN (0, 1)),
    fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_restaurante) REFERENCES restaurantes(id_restaurante) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reclamos (
    id_reclamo INTEGER PRIMARY KEY AUTOINCREMENT,
    codigo_reclamo TEXT NOT NULL UNIQUE,
    id_cliente INTEGER NOT NULL,
    codigo_pedido TEXT NOT NULL,
    canal_venta TEXT NOT NULL,
    fecha_pedido TEXT,
    descripcion TEXT NOT NULL,
    id_categoria INTEGER,
    id_prioridad INTEGER,
    id_estado INTEGER NOT NULL,
    id_usuario_asignado INTEGER,
    responsable_asignado TEXT,
    requiere_revision_humana INTEGER NOT NULL DEFAULT 1 CHECK (requiere_revision_humana IN (0, 1)),
    fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_cierre TEXT,
    tiempo_atencion_minutos INTEGER,
    FOREIGN KEY (id_cliente) REFERENCES clientes(id_cliente),
    FOREIGN KEY (id_categoria) REFERENCES categorias_reclamo(id_categoria),
    FOREIGN KEY (id_prioridad) REFERENCES prioridades(id_prioridad),
    FOREIGN KEY (id_estado) REFERENCES estados_reclamo(id_estado),
    FOREIGN KEY (id_usuario_asignado) REFERENCES usuarios(id_usuario)
);

CREATE TABLE IF NOT EXISTS notificaciones (
    id_notificacion INTEGER PRIMARY KEY AUTOINCREMENT,
    correo_cliente TEXT NOT NULL,
    id_reclamo INTEGER,
    titulo TEXT NOT NULL,
    mensaje TEXT NOT NULL,
    tipo TEXT NOT NULL DEFAULT 'INFO' CHECK (tipo IN ('INFO', 'RESPUESTA', 'ALERTA')),
    leida INTEGER NOT NULL DEFAULT 0 CHECK (leida IN (0, 1)),
    fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_reclamo) REFERENCES reclamos(id_reclamo) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS claim_messages (
    id_mensaje INTEGER PRIMARY KEY AUTOINCREMENT,
    id_reclamo INTEGER NOT NULL,
    sender_type TEXT NOT NULL CHECK (sender_type IN ('client', 'agent', 'ai', 'system')),
    sender_id TEXT,
    mensaje TEXT NOT NULL,
    is_internal INTEGER NOT NULL DEFAULT 0 CHECK (is_internal IN (0, 1)),
    read_at TEXT,
    metadata_json TEXT,
    fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_reclamo) REFERENCES reclamos(id_reclamo) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS analisis_ia (
    id_analisis INTEGER PRIMARY KEY AUTOINCREMENT,
    id_reclamo INTEGER NOT NULL UNIQUE,
    categoria_detectada TEXT,
    confianza REAL NOT NULL DEFAULT 0 CHECK (confianza >= 0 AND confianza <= 1),
    sentimiento TEXT CHECK (sentimiento IN ('POSITIVO', 'NEUTRO', 'NEGATIVO')),
    palabras_clave TEXT,
    entidades_detectadas TEXT,
    recomendacion TEXT,
    modelo_usado TEXT DEFAULT 'modelo_simulado_reglas',
    fecha_analisis TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_reclamo) REFERENCES reclamos(id_reclamo) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS documentos_base (
    id_documento INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT NOT NULL,
    tipo_documento TEXT NOT NULL CHECK (tipo_documento IN ('POLITICA', 'FAQ', 'PROCEDIMIENTO', 'MANUAL')),
    categoria_asociada TEXT,
    contenido TEXT NOT NULL,
    ruta_archivo TEXT,
    estado_indexacion TEXT NOT NULL DEFAULT 'INDEXADO' CHECK (estado_indexacion IN ('PENDIENTE', 'INDEXADO', 'ERROR')),
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    fecha_actualizacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS fragmentos_documento (
    id_fragmento INTEGER PRIMARY KEY AUTOINCREMENT,
    id_documento INTEGER NOT NULL,
    texto_fragmento TEXT NOT NULL,
    orden_fragmento INTEGER NOT NULL DEFAULT 1,
    embedding_id TEXT,
    fecha_creacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_documento) REFERENCES documentos_base(id_documento) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS respuestas_sugeridas (
    id_respuesta INTEGER PRIMARY KEY AUTOINCREMENT,
    id_reclamo INTEGER NOT NULL,
    respuesta_generada TEXT NOT NULL,
    respuesta_editada TEXT,
    respuesta_final TEXT,
    estado_revision TEXT NOT NULL DEFAULT 'PENDIENTE'
        CHECK (estado_revision IN ('PENDIENTE', 'EDITADA', 'APROBADA', 'RECHAZADA', 'ENVIADA')),
    id_usuario_revision INTEGER,
    fecha_generacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    fecha_revision TEXT,
    FOREIGN KEY (id_reclamo) REFERENCES reclamos(id_reclamo) ON DELETE CASCADE,
    FOREIGN KEY (id_usuario_revision) REFERENCES usuarios(id_usuario)
);

CREATE TABLE IF NOT EXISTS documentos_consultados (
    id_documento_consultado INTEGER PRIMARY KEY AUTOINCREMENT,
    id_respuesta INTEGER NOT NULL,
    id_documento INTEGER NOT NULL,
    score_similitud REAL,
    fragmento_usado TEXT,
    fecha_consulta TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_respuesta) REFERENCES respuestas_sugeridas(id_respuesta) ON DELETE CASCADE,
    FOREIGN KEY (id_documento) REFERENCES documentos_base(id_documento)
);

CREATE TABLE IF NOT EXISTS configuracion_modelo_ia (
    id_configuracion INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_configuracion TEXT NOT NULL UNIQUE,
    modelo_base TEXT NOT NULL DEFAULT 'modelo_simulado_reglas',
    umbral_confianza REAL NOT NULL DEFAULT 0.85 CHECK (umbral_confianza >= 0 AND umbral_confianza <= 1),
    revision_humana_obligatoria INTEGER NOT NULL DEFAULT 1 CHECK (revision_humana_obligatoria IN (0, 1)),
    usar_rag INTEGER NOT NULL DEFAULT 1 CHECK (usar_rag IN (0, 1)),
    max_documentos_recuperados INTEGER NOT NULL DEFAULT 3,
    activo INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1)),
    fecha_actualizacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);


CREATE TABLE IF NOT EXISTS historial_estados (
    id_historial INTEGER PRIMARY KEY AUTOINCREMENT,
    id_reclamo INTEGER NOT NULL,
    estado_anterior TEXT,
    estado_nuevo TEXT NOT NULL,
    accion TEXT NOT NULL,
    comentario TEXT,
    usuario_responsable TEXT DEFAULT 'Agente de soporte',
    fecha_cambio TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_reclamo) REFERENCES reclamos(id_reclamo) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_historial_reclamo ON historial_estados(id_reclamo);
CREATE INDEX IF NOT EXISTS idx_historial_fecha ON historial_estados(fecha_cambio);


CREATE TABLE IF NOT EXISTS comentarios_agente (
    id_comentario INTEGER PRIMARY KEY AUTOINCREMENT,
    id_reclamo INTEGER NOT NULL,
    comentario TEXT NOT NULL,
    tipo_comentario TEXT NOT NULL DEFAULT 'INTERNO'
        CHECK (tipo_comentario IN ('INTERNO', 'SEGUIMIENTO', 'ESCALAMIENTO', 'CIERRE')),
    usuario_responsable TEXT DEFAULT 'Agente de soporte',
    fecha_comentario TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_reclamo) REFERENCES reclamos(id_reclamo) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS evaluacion_respuesta (
    id_evaluacion INTEGER PRIMARY KEY AUTOINCREMENT,
    id_respuesta INTEGER NOT NULL,
    claridad INTEGER NOT NULL CHECK (claridad BETWEEN 1 AND 5),
    utilidad INTEGER NOT NULL CHECK (utilidad BETWEEN 1 AND 5),
    tono INTEGER NOT NULL CHECK (tono BETWEEN 1 AND 5),
    fundamentacion INTEGER NOT NULL CHECK (fundamentacion BETWEEN 1 AND 5),
    requiere_mejora INTEGER NOT NULL DEFAULT 0 CHECK (requiere_mejora IN (0, 1)),
    observacion TEXT,
    usuario_evaluador TEXT DEFAULT 'Supervisor de soporte',
    fecha_evaluacion TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_respuesta) REFERENCES respuestas_sugeridas(id_respuesta) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dataset_entrenamiento (
    id_dataset INTEGER PRIMARY KEY AUTOINCREMENT,
    texto TEXT NOT NULL,
    categoria TEXT NOT NULL,
    fuente TEXT NOT NULL DEFAULT 'dataset_simulado',
    usado_entrenamiento INTEGER NOT NULL DEFAULT 1 CHECK (usado_entrenamiento IN (0, 1)),
    fecha_registro TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS logs_sistema (
    id_log INTEGER PRIMARY KEY AUTOINCREMENT,
    modulo TEXT NOT NULL,
    accion TEXT NOT NULL,
    nivel TEXT NOT NULL DEFAULT 'INFO' CHECK (nivel IN ('INFO', 'WARNING', 'ERROR')),
    detalle TEXT,
    id_reclamo INTEGER,
    fecha_log TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (id_reclamo) REFERENCES reclamos(id_reclamo) ON DELETE SET NULL
);

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
