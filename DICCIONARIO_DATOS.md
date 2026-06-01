# Diccionario de datos - SmartClaim AI

## categorias_reclamo
| Campo | Tipo | Descripción |
|---|---|---|
| id_categoria | INTEGER | Identificador único de la categoría. |
| nombre | TEXT | Nombre de la categoría del reclamo. |
| descripcion | TEXT | Descripción funcional de la categoría. |
| es_critica | INTEGER | Indica si la categoría requiere mayor control. |
| activo | INTEGER | Indica si la categoría está disponible. |
| fecha_creacion | TEXT | Fecha de creación del registro. |

## prioridades
| Campo | Tipo | Descripción |
|---|---|---|
| id_prioridad | INTEGER | Identificador único de prioridad. |
| nombre | TEXT | Nombre del nivel de prioridad. |
| nivel | INTEGER | Valor numérico para ordenar severidad. |
| descripcion | TEXT | Descripción del nivel de atención. |
| activo | INTEGER | Indica si la prioridad está activa. |

## estados_reclamo
| Campo | Tipo | Descripción |
|---|---|---|
| id_estado | INTEGER | Identificador único del estado. |
| nombre | TEXT | Nombre del estado del reclamo. |
| descripcion | TEXT | Descripción del estado. |
| es_final | INTEGER | Indica si el estado finaliza el flujo. |
| activo | INTEGER | Indica si el estado está activo. |

## usuarios
| Campo | Tipo | Descripción |
|---|---|---|
| id_usuario | INTEGER | Identificador del usuario interno. |
| nombre | TEXT | Nombre del agente, supervisor o administrador. |
| correo | TEXT | Correo del usuario interno. |
| rol | TEXT | Rol: AGENTE, SUPERVISOR o ADMINISTRADOR. |
| estado | TEXT | Estado del usuario. |
| fecha_creacion | TEXT | Fecha de creación. |

## clientes
| Campo | Tipo | Descripción |
|---|---|---|
| id_cliente | INTEGER | Identificador del cliente. |
| nombre | TEXT | Nombre del cliente que presenta el reclamo. |
| correo | TEXT | Correo del cliente. |
| telefono | TEXT | Teléfono opcional. |
| estado | TEXT | Estado del cliente. |
| fecha_creacion | TEXT | Fecha de creación. |

## reclamos
| Campo | Tipo | Descripción |
|---|---|---|
| id_reclamo | INTEGER | Identificador único del reclamo. |
| codigo_reclamo | TEXT | Código visible del reclamo. |
| id_cliente | INTEGER | Cliente asociado. |
| codigo_pedido | TEXT | Código del pedido reclamado. |
| canal_venta | TEXT | Canal de venta o atención. |
| fecha_pedido | TEXT | Fecha del pedido. |
| descripcion | TEXT | Texto original del reclamo. |
| id_categoria | INTEGER | Categoría asignada por IA o agente. |
| id_prioridad | INTEGER | Prioridad asignada. |
| id_estado | INTEGER | Estado actual del reclamo. |
| id_usuario_asignado | INTEGER | Agente responsable. |
| requiere_revision_humana | INTEGER | Indica si debe pasar por revisión. |
| fecha_creacion | TEXT | Fecha de registro. |
| fecha_actualizacion | TEXT | Fecha de última actualización. |

## analisis_ia
| Campo | Tipo | Descripción |
|---|---|---|
| id_analisis | INTEGER | Identificador del análisis. |
| id_reclamo | INTEGER | Reclamo analizado. |
| categoria_detectada | TEXT | Categoría detectada por el modelo. |
| confianza | REAL | Nivel de confianza entre 0 y 1. |
| sentimiento | TEXT | Sentimiento: POSITIVO, NEUTRO o NEGATIVO. |
| palabras_clave | TEXT | Palabras clave detectadas. |
| entidades_detectadas | TEXT | Entidades relevantes extraídas. |
| recomendacion | TEXT | Acción recomendada por el sistema. |
| modelo_usado | TEXT | Modelo o estrategia utilizada. |
| fecha_analisis | TEXT | Fecha del análisis. |

## documentos_base
| Campo | Tipo | Descripción |
|---|---|---|
| id_documento | INTEGER | Identificador del documento. |
| titulo | TEXT | Título del documento. |
| tipo_documento | TEXT | POLITICA, FAQ, PROCEDIMIENTO o MANUAL. |
| categoria_asociada | TEXT | Categoría de reclamo asociada. |
| contenido | TEXT | Contenido documental usado por RAG. |
| ruta_archivo | TEXT | Ruta opcional del archivo fuente. |
| estado_indexacion | TEXT | Estado de indexación vectorial. |
| activo | INTEGER | Indica si el documento está activo. |
| fecha_actualizacion | TEXT | Fecha de actualización. |

## fragmentos_documento
| Campo | Tipo | Descripción |
|---|---|---|
| id_fragmento | INTEGER | Identificador del fragmento. |
| id_documento | INTEGER | Documento de origen. |
| texto_fragmento | TEXT | Fragmento usado para recuperación. |
| orden_fragmento | INTEGER | Orden del fragmento. |
| embedding_id | TEXT | Referencia del vector en ChromaDB/FAISS. |
| fecha_creacion | TEXT | Fecha de creación. |

## respuestas_sugeridas
| Campo | Tipo | Descripción |
|---|---|---|
| id_respuesta | INTEGER | Identificador de la respuesta. |
| id_reclamo | INTEGER | Reclamo relacionado. |
| respuesta_generada | TEXT | Respuesta propuesta por IA. |
| respuesta_final | TEXT | Respuesta editada/aprobada por agente. |
| estado_revision | TEXT | PENDIENTE, EDITADA, APROBADA, RECHAZADA o ENVIADA. |
| id_usuario_revision | INTEGER | Usuario que revisó la respuesta. |
| fecha_generacion | TEXT | Fecha de generación. |
| fecha_revision | TEXT | Fecha de revisión. |

## documentos_consultados
| Campo | Tipo | Descripción |
|---|---|---|
| id_documento_consultado | INTEGER | Identificador del registro. |
| id_respuesta | INTEGER | Respuesta asociada. |
| id_documento | INTEGER | Documento usado como evidencia. |
| score_similitud | REAL | Puntaje de similitud documental. |
| fragmento_usado | TEXT | Fragmento consultado para la respuesta. |
| fecha_consulta | TEXT | Fecha de consulta. |

## configuracion_modelo_ia
| Campo | Tipo | Descripción |
|---|---|---|
| id_configuracion | INTEGER | Identificador de configuración. |
| nombre_configuracion | TEXT | Nombre de la configuración. |
| modelo_base | TEXT | Modelo o estrategia activa. |
| umbral_confianza | REAL | Umbral mínimo para confianza. |
| revision_humana_obligatoria | INTEGER | Control de revisión humana. |
| usar_rag | INTEGER | Indica si se usa RAG. |
| max_documentos_recuperados | INTEGER | Máximo de documentos consultados. |
| activo | INTEGER | Configuración activa. |
| fecha_actualizacion | TEXT | Fecha de actualización. |
