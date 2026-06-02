from datetime import datetime, timedelta
from database.db_connection import execute, fetch_all, fetch_one, get_connection
from modules.security import hash_password

def get_estado_id(nombre):
    row = fetch_one("SELECT id_estado FROM estados_reclamo WHERE nombre = ?", (nombre,))
    return row["id_estado"] if row else None

def get_estado_nombre_by_id(id_estado):
    row = fetch_one("SELECT nombre FROM estados_reclamo WHERE id_estado = ?", (id_estado,))
    return row["nombre"] if row else None

def get_categoria_id(nombre):
    row = fetch_one("SELECT id_categoria FROM categorias_reclamo WHERE nombre = ?", (nombre,))
    return row["id_categoria"] if row else None

def get_prioridad_id(nombre):
    row = fetch_one("SELECT id_prioridad FROM prioridades WHERE nombre = ?", (nombre,))
    return row["id_prioridad"] if row else None

def get_configuracion_activa():
    return fetch_one("SELECT * FROM configuracion_modelo_ia WHERE activo = 1 ORDER BY id_configuracion DESC LIMIT 1")

def registrar_historial_estado(id_reclamo, estado_anterior, estado_nuevo, accion, comentario=None, usuario="Agente de soporte"):
    return execute("""
        INSERT INTO historial_estados (
            id_reclamo, estado_anterior, estado_nuevo, accion, comentario, usuario_responsable
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (id_reclamo, estado_anterior, estado_nuevo, accion, comentario, usuario))

def crear_cliente(nombre, correo, telefono=None):
    existente = fetch_one("SELECT id_cliente FROM clientes WHERE lower(correo) = lower(?) LIMIT 1", (correo.strip(),))
    if existente:
        return existente["id_cliente"]
    return execute(
        "INSERT INTO clientes (nombre, correo, telefono) VALUES (?, ?, ?)",
        (nombre.strip(), correo.strip(), telefono.strip() if telefono else None)
    )

def crear_usuario_auth(nombre, correo, password_hash, rol="CLIENT", telefono=None):
    return execute("""
        INSERT INTO auth_users (nombre, correo, telefono, password_hash, rol)
        VALUES (?, ?, ?, ?, ?)
    """, (nombre.strip(), correo.strip().lower(), telefono.strip() if telefono else None, password_hash, rol))

def obtener_usuario_auth_por_correo(correo):
    return fetch_one("""
        SELECT *
        FROM auth_users
        WHERE lower(correo) = lower(?) AND estado = 'ACTIVO'
        LIMIT 1
    """, (correo.strip(),))

def obtener_usuario_auth_por_id(id_auth_user):
    return fetch_one("""
        SELECT *
        FROM auth_users
        WHERE id_auth_user = ? AND estado = 'ACTIVO'
        LIMIT 1
    """, (id_auth_user,))

def asegurar_usuarios_auth_base():
    usuarios = [
        ("Maria Gonzalez", "maria.gonzalez@email.com", "CLIENT", "+51 900 111 222"),
        ("Laura Martinez", "laura.martinez@smartclaim.com", "AGENT", None),
        ("Admin System", "admin@smartclaim.com", "ADMIN", None),
    ]
    for nombre, correo, rol, telefono in usuarios:
        if not obtener_usuario_auth_por_correo(correo):
            crear_usuario_auth(nombre, correo, hash_password("123456"), rol, telefono)

def generar_codigo_pedido():
    total = fetch_one("SELECT COUNT(*) AS total FROM pedidos")["total"] + 1
    return f"ORD-{datetime.now().strftime('%Y%m%d')}-{total:04d}"

def crear_pedido_cliente(correo_cliente, nombre_cliente, telefono, tienda_nombre, tienda_imagen, metodo_pago, direccion_entrega, items, estado="PREPARING"):
    id_cliente = crear_cliente(nombre_cliente, correo_cliente, telefono)
    codigo = generar_codigo_pedido()
    total = sum(float(item["price"]) * int(item["quantity"]) for item in items)
    fecha_estimada = (datetime.now() + timedelta(minutes=35)).isoformat(timespec="seconds")
    id_pedido = execute("""
        INSERT INTO pedidos (
            codigo_pedido, id_cliente, tienda_nombre, tienda_imagen, estado, total,
            metodo_pago, direccion_entrega, repartidor, fecha_entrega_estimada
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        codigo,
        id_cliente,
        tienda_nombre.strip(),
        tienda_imagen,
        estado,
        total,
        metodo_pago.strip(),
        direccion_entrega.strip(),
        "Repartidor por asignar",
        fecha_estimada,
    ))

    for item in items:
        execute("""
            INSERT INTO pedido_items (id_pedido, nombre_producto, cantidad, precio, imagen)
            VALUES (?, ?, ?, ?, ?)
        """, (
            id_pedido,
            item["name"].strip(),
            int(item["quantity"]),
            float(item["price"]),
            item.get("image"),
        ))

    return id_pedido

def listar_pedidos_por_correo(correo_cliente):
    return fetch_all("""
        SELECT p.*, c.nombre AS cliente, c.correo AS correo_cliente
        FROM pedidos p
        INNER JOIN clientes c ON c.id_cliente = p.id_cliente
        WHERE lower(c.correo) = lower(?)
        ORDER BY p.id_pedido DESC
    """, (correo_cliente.strip(),))

def obtener_pedido(id_pedido):
    pedido = fetch_one("""
        SELECT p.*, c.nombre AS cliente, c.correo AS correo_cliente
        FROM pedidos p
        INNER JOIN clientes c ON c.id_cliente = p.id_cliente
        WHERE p.id_pedido = ?
    """, (id_pedido,))
    if not pedido:
        return None, []
    items = fetch_all("""
        SELECT *
        FROM pedido_items
        WHERE id_pedido = ?
        ORDER BY id_item
    """, (id_pedido,))
    return pedido, items

def asegurar_pedidos_demo_base():
    usuario = obtener_usuario_auth_por_correo("maria.gonzalez@email.com")
    if not usuario:
        return
    existentes = listar_pedidos_por_correo(usuario["correo"])
    if existentes:
        return
    crear_pedido_cliente(
        usuario["correo"],
        usuario["nombre"],
        usuario.get("telefono"),
        "Burger Palace",
        "https://images.unsplash.com/photo-1586190848861-99aa4a171e90?w=400",
        "Tarjeta de credito",
        "Av. Primavera 123, Lima",
        [
            {"name": "Combo clasico", "quantity": 1, "price": 24.5, "image": "https://images.unsplash.com/photo-1568901346375-23c9450c58cd?w=400"},
            {"name": "Papas bacon cheddar", "quantity": 1, "price": 15.9, "image": "https://images.unsplash.com/photo-1630384060421-cb20d0e0649d?w=400"},
        ],
        "DELIVERED",
    )
    crear_pedido_cliente(
        usuario["correo"],
        usuario["nombre"],
        usuario.get("telefono"),
        "Sushi Express",
        "https://images.unsplash.com/photo-1579584425555-c3ce17fd4351?w=400",
        "Yape",
        "Av. Primavera 123, Lima",
        [
            {"name": "Combo makis", "quantity": 1, "price": 45.8, "image": "https://images.unsplash.com/photo-1553621042-f6e147245754?w=400"},
        ],
        "DELAYED",
    )

def generar_codigo_reclamo():
    total = fetch_one("SELECT COUNT(*) AS total FROM reclamos")["total"] + 1
    return f"RC-{datetime.now().strftime('%Y%m%d')}-{total:04d}"

def crear_reclamo(id_cliente, codigo_pedido, canal_venta, fecha_pedido, descripcion, responsable_asignado='Agente de soporte'):
    codigo = generar_codigo_reclamo()
    estado_nuevo_id = get_estado_id("Nuevo")
    id_reclamo = execute("""
        INSERT INTO reclamos (
            codigo_reclamo, id_cliente, codigo_pedido, canal_venta, fecha_pedido,
            descripcion, id_estado, responsable_asignado
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (codigo, id_cliente, codigo_pedido.strip(), canal_venta, str(fecha_pedido), descripcion.strip(), estado_nuevo_id, responsable_asignado))
    registrar_historial_estado(id_reclamo, None, "Nuevo", "Registro de reclamo", "El reclamo fue guardado en estado Nuevo.")
    return id_reclamo

def obtener_reclamo_basico(id_reclamo):
    return fetch_one("""
        SELECT r.*, c.nombre AS cliente, c.correo AS correo_cliente
        FROM reclamos r
        INNER JOIN clientes c ON c.id_cliente = r.id_cliente
        WHERE r.id_reclamo = ?
    """, (id_reclamo,))

def guardar_analisis(id_reclamo, analisis):
    reclamo_actual = fetch_one("""
        SELECT r.id_estado, e.nombre AS estado
        FROM reclamos r
        INNER JOIN estados_reclamo e ON e.id_estado = r.id_estado
        WHERE r.id_reclamo = ?
    """, (id_reclamo,))
    estado_anterior = reclamo_actual["estado"] if reclamo_actual else None

    config = get_configuracion_activa() or {"umbral_confianza": 0.85, "revision_humana_obligatoria": 1}
    requiere = int(
        analisis["confianza"] < float(config["umbral_confianza"])
        or analisis["prioridad"] in ["Alta", "Crítica"]
        or int(config["revision_humana_obligatoria"]) == 1
    )
    estado_nuevo = "En revisión" if requiere else "Analizado por IA"
    estado_id = get_estado_id(estado_nuevo)

    with get_connection() as conn:
        conn.execute("""
            UPDATE reclamos
            SET id_categoria = ?, id_prioridad = ?, id_estado = ?, requiere_revision_humana = ?,
                fecha_actualizacion = CURRENT_TIMESTAMP
            WHERE id_reclamo = ?
        """, (get_categoria_id(analisis["categoria"]), get_prioridad_id(analisis["prioridad"]), estado_id, requiere, id_reclamo))

        conn.execute("DELETE FROM analisis_ia WHERE id_reclamo = ?", (id_reclamo,))
        conn.execute("""
            INSERT INTO analisis_ia (
                id_reclamo, categoria_detectada, confianza, sentimiento, palabras_clave,
                entidades_detectadas, recomendacion, modelo_usado
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            id_reclamo,
            analisis["categoria"],
            analisis["confianza"],
            analisis["sentimiento"],
            ", ".join(analisis["palabras_clave"]),
            ", ".join(analisis["entidades"]),
            analisis["recomendacion"],
            analisis.get("modelo_usado", "modelo_ml_tfidf_logistic_regression")
        ))
        conn.commit()

    registrar_historial_estado(
        id_reclamo,
        estado_anterior,
        estado_nuevo,
        "Análisis IA",
        f"El reclamo fue clasificado como {analisis['categoria']} con prioridad {analisis['prioridad']}."
    )

def guardar_respuesta(id_reclamo, respuesta, documentos=None, accion="Generación de respuesta"):
    documentos = documentos or []
    id_respuesta = execute("""
        INSERT INTO respuestas_sugeridas (id_reclamo, respuesta_generada)
        VALUES (?, ?)
    """, (id_reclamo, respuesta))

    for doc in documentos:
        execute("""
            INSERT INTO documentos_consultados (id_respuesta, id_documento, score_similitud, fragmento_usado)
            VALUES (?, ?, ?, ?)
        """, (id_respuesta, doc["id_documento"], doc["score"], doc["contenido"][:350]))

    registrar_historial_estado(
        id_reclamo,
        obtener_estado_actual(id_reclamo),
        obtener_estado_actual(id_reclamo),
        accion,
        "Se generó una respuesta sugerida con documentos RAG consultados."
        if documentos else
        "Se generó una respuesta sugerida sin consulta RAG."
    )
    return id_respuesta

def obtener_estado_actual(id_reclamo):
    row = fetch_one("""
        SELECT e.nombre
        FROM reclamos r
        INNER JOIN estados_reclamo e ON e.id_estado = r.id_estado
        WHERE r.id_reclamo = ?
    """, (id_reclamo,))
    return row["nombre"] if row else None

def listar_reclamos():
    return fetch_all("""
        SELECT r.id_reclamo, r.codigo_reclamo, c.nombre AS cliente, c.correo, r.codigo_pedido, r.canal_venta,
               COALESCE(cat.nombre, 'Sin clasificar') AS categoria,
               COALESCE(p.nombre, 'Sin prioridad') AS prioridad,
               e.nombre AS estado, r.requiere_revision_humana, r.fecha_creacion, r.fecha_actualizacion
        FROM reclamos r
        INNER JOIN clientes c ON c.id_cliente = r.id_cliente
        LEFT JOIN categorias_reclamo cat ON cat.id_categoria = r.id_categoria
        LEFT JOIN prioridades p ON p.id_prioridad = r.id_prioridad
        INNER JOIN estados_reclamo e ON e.id_estado = r.id_estado
        ORDER BY r.id_reclamo DESC
    """)

def listar_reclamos_por_correo(correo_cliente):
    return fetch_all("""
        SELECT r.id_reclamo, r.codigo_reclamo, c.nombre AS cliente, c.correo, r.codigo_pedido, r.canal_venta,
               COALESCE(cat.nombre, 'Sin clasificar') AS categoria,
               COALESCE(p.nombre, 'Sin prioridad') AS prioridad,
               e.nombre AS estado, r.requiere_revision_humana, r.fecha_creacion, r.fecha_actualizacion
        FROM reclamos r
        INNER JOIN clientes c ON c.id_cliente = r.id_cliente
        LEFT JOIN categorias_reclamo cat ON cat.id_categoria = r.id_categoria
        LEFT JOIN prioridades p ON p.id_prioridad = r.id_prioridad
        INNER JOIN estados_reclamo e ON e.id_estado = r.id_estado
        WHERE lower(c.correo) = lower(?)
        ORDER BY r.id_reclamo DESC
    """, (correo_cliente.strip(),))

def obtener_detalle_reclamo(id_reclamo):
    reclamo = fetch_one("""
        SELECT r.*, c.nombre AS cliente, c.correo AS correo_cliente,
               COALESCE(cat.nombre, 'Sin clasificar') AS categoria,
               COALESCE(p.nombre, 'Sin prioridad') AS prioridad,
               e.nombre AS estado
        FROM reclamos r
        INNER JOIN clientes c ON c.id_cliente = r.id_cliente
        LEFT JOIN categorias_reclamo cat ON cat.id_categoria = r.id_categoria
        LEFT JOIN prioridades p ON p.id_prioridad = r.id_prioridad
        INNER JOIN estados_reclamo e ON e.id_estado = r.id_estado
        WHERE r.id_reclamo = ?
    """, (id_reclamo,))
    analisis = fetch_one("SELECT * FROM analisis_ia WHERE id_reclamo = ?", (id_reclamo,))
    respuesta = fetch_one("""
        SELECT * FROM respuestas_sugeridas
        WHERE id_reclamo = ?
        ORDER BY id_respuesta DESC
        LIMIT 1
    """, (id_reclamo,))
    documentos = []
    if respuesta:
        documentos = fetch_all("""
            SELECT dc.*, db.titulo, db.tipo_documento, db.categoria_asociada
            FROM documentos_consultados dc
            INNER JOIN documentos_base db ON db.id_documento = dc.id_documento
            WHERE dc.id_respuesta = ?
            ORDER BY dc.score_similitud DESC
        """, (respuesta["id_respuesta"],))
    historial = listar_historial_estados(id_reclamo)
    return reclamo, analisis, respuesta, documentos, historial

def listar_documentos():
    return fetch_all("""
        SELECT id_documento, titulo, tipo_documento, categoria_asociada,
               estado_indexacion, fecha_actualizacion, contenido
        FROM documentos_base
        ORDER BY id_documento
    """)

def actualizar_estado_reclamo(id_reclamo, estado, accion="Actualización de estado", comentario=None):
    estado_anterior = obtener_estado_actual(id_reclamo)
    estado_id = get_estado_id(estado)
    if estado_id is None:
        raise ValueError(f"Estado de reclamo no válido: {estado}")
    execute("""
        UPDATE reclamos
        SET id_estado = ?, fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id_reclamo = ?
    """, (estado_id, id_reclamo))
    registrar_historial_estado(id_reclamo, estado_anterior, estado, accion, comentario)

def actualizar_respuesta_final(id_respuesta, respuesta_final, estado_revision="EDITADA"):
    respuesta = fetch_one("SELECT id_reclamo FROM respuestas_sugeridas WHERE id_respuesta = ?", (id_respuesta,))
    execute("""
        UPDATE respuestas_sugeridas
        SET respuesta_editada = ?, respuesta_final = ?, estado_revision = ?, fecha_revision = CURRENT_TIMESTAMP
        WHERE id_respuesta = ?
    """, (respuesta_final, respuesta_final, estado_revision, id_respuesta))
    if respuesta:
        registrar_historial_estado(
            respuesta["id_reclamo"],
            obtener_estado_actual(respuesta["id_reclamo"]),
            obtener_estado_actual(respuesta["id_reclamo"]),
            "Edición de respuesta",
            f"La respuesta fue actualizada con estado de revisión {estado_revision}."
        )

def aprobar_respuesta(id_respuesta, respuesta_final=None):
    respuesta = fetch_one("""
        SELECT id_reclamo, respuesta_generada
        FROM respuestas_sugeridas
        WHERE id_respuesta = ?
    """, (id_respuesta,))
    if not respuesta:
        return
    final = respuesta_final if respuesta_final is not None and respuesta_final.strip() else respuesta["respuesta_generada"]
    execute("""
        UPDATE respuestas_sugeridas
        SET respuesta_final = ?, estado_revision = 'APROBADA', fecha_revision = CURRENT_TIMESTAMP
        WHERE id_respuesta = ?
    """, (final, id_respuesta))
    registrar_historial_estado(
        respuesta["id_reclamo"],
        obtener_estado_actual(respuesta["id_reclamo"]),
        obtener_estado_actual(respuesta["id_reclamo"]),
        "Aprobación de respuesta",
        "El agente aprobó la respuesta final."
    )

def marcar_respondido(id_reclamo, comentario=None):
    actualizar_estado_reclamo(
        id_reclamo,
        "Respondido",
        "Marcado como respondido",
        comentario or "El reclamo fue marcado como respondido por el agente."
    )

def escalar_reclamo(id_reclamo, comentario=None):
    actualizar_estado_reclamo(
        id_reclamo,
        "Escalado",
        "Escalamiento de reclamo",
        comentario or "El reclamo fue escalado para revisión superior."
    )

def listar_historial_estados(id_reclamo):
    return fetch_all("""
        SELECT *
        FROM historial_estados
        WHERE id_reclamo = ?
        ORDER BY fecha_cambio DESC, id_historial DESC
    """, (id_reclamo,))

def actualizar_configuracion(umbral, revision_humana, usar_rag, max_docs):
    execute("""
        UPDATE configuracion_modelo_ia
        SET umbral_confianza = ?, revision_humana_obligatoria = ?, usar_rag = ?,
            max_documentos_recuperados = ?, fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE nombre_configuracion = 'Configuración principal'
    """, (umbral, int(revision_humana), int(usar_rag), int(max_docs)))


def eliminar_fragmentos_documento():
    execute("DELETE FROM fragmentos_documento")

def crear_fragmento_documento(id_documento, texto_fragmento, orden_fragmento, embedding_id=None):
    return execute("""
        INSERT INTO fragmentos_documento (id_documento, texto_fragmento, orden_fragmento, embedding_id)
        VALUES (?, ?, ?, ?)
    """, (id_documento, texto_fragmento, orden_fragmento, embedding_id))

def listar_fragmentos_documento():
    return fetch_all("""
        SELECT
            fd.id_fragmento,
            fd.id_documento,
            fd.texto_fragmento,
            fd.orden_fragmento,
            fd.embedding_id,
            db.titulo,
            db.tipo_documento,
            db.categoria_asociada,
            db.estado_indexacion,
            db.fecha_actualizacion
        FROM fragmentos_documento fd
        INNER JOIN documentos_base db ON db.id_documento = fd.id_documento
        WHERE db.activo = 1
        ORDER BY fd.id_documento, fd.orden_fragmento
    """)

def contar_fragmentos_documento():
    row = fetch_one("SELECT COUNT(*) AS total FROM fragmentos_documento")
    return row["total"] if row else 0

def actualizar_estado_indexacion_documento(id_documento, estado):
    execute("""
        UPDATE documentos_base
        SET estado_indexacion = ?, fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id_documento = ?
    """, (estado, id_documento))


def calcular_tiempo_atencion_minutos(id_reclamo):
    row = fetch_one("""
        SELECT
            CAST((julianday(COALESCE(fecha_cierre, CURRENT_TIMESTAMP)) - julianday(fecha_creacion)) * 24 * 60 AS INTEGER) AS minutos
        FROM reclamos
        WHERE id_reclamo = ?
    """, (id_reclamo,))
    return row["minutos"] if row and row["minutos"] is not None else None

def cerrar_reclamo(id_reclamo, estado_final="Cerrado", comentario=None):
    estado_anterior = obtener_estado_actual(id_reclamo)
    estado_id = get_estado_id(estado_final)
    if estado_id is None:
        raise ValueError(f"Estado de reclamo no válido: {estado_final}")
    execute("""
        UPDATE reclamos
        SET id_estado = ?,
            fecha_cierre = CURRENT_TIMESTAMP,
            tiempo_atencion_minutos = CAST((julianday(CURRENT_TIMESTAMP) - julianday(fecha_creacion)) * 24 * 60 AS INTEGER),
            fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id_reclamo = ?
    """, (estado_id, id_reclamo))
    registrar_historial_estado(
        id_reclamo,
        estado_anterior,
        estado_final,
        "Cierre de reclamo",
        comentario or "El reclamo fue cerrado y se calculó el tiempo de atención."
    )
    registrar_log("Reclamos", "Cierre de reclamo", "INFO", f"Reclamo cerrado con estado {estado_final}.", id_reclamo)

def asignar_responsable(id_reclamo, responsable):
    execute("""
        UPDATE reclamos
        SET responsable_asignado = ?, fecha_actualizacion = CURRENT_TIMESTAMP
        WHERE id_reclamo = ?
    """, (responsable, id_reclamo))
    registrar_historial_estado(
        id_reclamo,
        obtener_estado_actual(id_reclamo),
        obtener_estado_actual(id_reclamo),
        "Asignación de responsable",
        f"Responsable asignado: {responsable}."
    )
    registrar_log("Reclamos", "Asignación de responsable", "INFO", f"Responsable asignado: {responsable}.", id_reclamo)

def crear_comentario_agente(id_reclamo, comentario, tipo_comentario="INTERNO", usuario="Agente de soporte"):
    id_comentario = execute("""
        INSERT INTO comentarios_agente (id_reclamo, comentario, tipo_comentario, usuario_responsable)
        VALUES (?, ?, ?, ?)
    """, (id_reclamo, comentario, tipo_comentario, usuario))
    registrar_log("Comentarios", "Comentario agregado", "INFO", f"Tipo: {tipo_comentario}.", id_reclamo)
    return id_comentario

def listar_comentarios_agente(id_reclamo):
    return fetch_all("""
        SELECT *
        FROM comentarios_agente
        WHERE id_reclamo = ?
        ORDER BY fecha_comentario DESC, id_comentario DESC
    """, (id_reclamo,))

def crear_evaluacion_respuesta(id_respuesta, claridad, utilidad, tono, fundamentacion, requiere_mejora=0, observacion=None, usuario="Supervisor de soporte"):
    id_eval = execute("""
        INSERT INTO evaluacion_respuesta (
            id_respuesta, claridad, utilidad, tono, fundamentacion, requiere_mejora, observacion, usuario_evaluador
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (id_respuesta, claridad, utilidad, tono, fundamentacion, int(requiere_mejora), observacion, usuario))

    respuesta = fetch_one("SELECT id_reclamo FROM respuestas_sugeridas WHERE id_respuesta = ?", (id_respuesta,))
    if respuesta:
        registrar_log("Evaluación", "Evaluación de respuesta", "INFO", "Se evaluó la calidad de una respuesta sugerida.", respuesta["id_reclamo"])
    return id_eval

def listar_evaluaciones_respuesta(id_respuesta):
    return fetch_all("""
        SELECT *
        FROM evaluacion_respuesta
        WHERE id_respuesta = ?
        ORDER BY fecha_evaluacion DESC, id_evaluacion DESC
    """, (id_respuesta,))

def registrar_log(modulo, accion, nivel="INFO", detalle=None, id_reclamo=None):
    return execute("""
        INSERT INTO logs_sistema (modulo, accion, nivel, detalle, id_reclamo)
        VALUES (?, ?, ?, ?, ?)
    """, (modulo, accion, nivel, detalle, id_reclamo))

def listar_logs_sistema(limite=100):
    return fetch_all("""
        SELECT *
        FROM logs_sistema
        ORDER BY fecha_log DESC, id_log DESC
        LIMIT ?
    """, (int(limite),))

def importar_dataset_entrenamiento_desde_csv():
    import csv
    from pathlib import Path

    base_dir = Path(__file__).resolve().parent.parent
    dataset_path = base_dir / "data" / "reclamos_entrenamiento.csv"

    if not dataset_path.exists():
        return 0

    actual = fetch_one("SELECT COUNT(*) AS total FROM dataset_entrenamiento")
    if actual and actual["total"] > 0:
        return actual["total"]

    total = 0
    with dataset_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            execute("""
                INSERT INTO dataset_entrenamiento (texto, categoria, fuente, usado_entrenamiento)
                VALUES (?, ?, ?, ?)
            """, (row.get("texto"), row.get("categoria"), "csv_reclamos_entrenamiento", 1))
            total += 1

    registrar_log("Dataset", "Importación de dataset", "INFO", f"Se importaron {total} registros al dataset de entrenamiento.", None)
    return total

def obtener_metricas_bd():
    tablas = [
        "reclamos", "clientes", "analisis_ia", "respuestas_sugeridas",
        "documentos_base", "fragmentos_documento", "historial_estados",
        "comentarios_agente", "evaluacion_respuesta", "dataset_entrenamiento",
        "logs_sistema"
    ]

    data = []
    for tabla in tablas:
        try:
            row = fetch_one(f"SELECT COUNT(*) AS total FROM {tabla}")
            data.append({"tabla": tabla, "registros": row["total"] if row else 0})
        except Exception:
            data.append({"tabla": tabla, "registros": 0})

    return data

def obtener_tiempos_atencion():
    return fetch_all("""
        SELECT
            r.codigo_reclamo,
            c.nombre AS cliente,
            e.nombre AS estado,
            r.fecha_creacion,
            r.fecha_cierre,
            r.tiempo_atencion_minutos,
            r.responsable_asignado
        FROM reclamos r
        INNER JOIN clientes c ON c.id_cliente = r.id_cliente
        INNER JOIN estados_reclamo e ON e.id_estado = r.id_estado
        ORDER BY r.fecha_creacion DESC
    """)


def contar_reclamos():
    row = fetch_one("SELECT COUNT(*) AS total FROM reclamos")
    return row["total"] if row else 0

def limpiar_datos_prueba():
    """
    Limpia datos transaccionales para regenerar escenarios de prueba.
    Mantiene catálogos, documentos, configuración, dataset de entrenamiento e índice RAG.
    """
    with get_connection() as conn:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("DELETE FROM documentos_consultados;")
        conn.execute("DELETE FROM evaluacion_respuesta;")
        conn.execute("DELETE FROM respuestas_sugeridas;")
        conn.execute("DELETE FROM analisis_ia;")
        conn.execute("DELETE FROM comentarios_agente;")
        conn.execute("DELETE FROM historial_estados;")
        conn.execute("DELETE FROM logs_sistema WHERE modulo IN ('Datos de prueba', 'Generador');")
        conn.execute("DELETE FROM reclamos;")
        conn.execute("DELETE FROM pedido_items;")
        conn.execute("DELETE FROM pedidos;")
        conn.execute("DELETE FROM clientes;")
        conn.commit()

def obtener_ultimo_id_respuesta(id_reclamo):
    row = fetch_one("""
        SELECT id_respuesta
        FROM respuestas_sugeridas
        WHERE id_reclamo = ?
        ORDER BY id_respuesta DESC
        LIMIT 1
    """, (id_reclamo,))
    return row["id_respuesta"] if row else None

def listar_reclamos_simples():
    return fetch_all("""
        SELECT
            r.id_reclamo,
            r.codigo_reclamo,
            c.nombre AS cliente,
            r.codigo_pedido,
            COALESCE(cat.nombre, 'Sin clasificar') AS categoria,
            COALESCE(p.nombre, 'Sin prioridad') AS prioridad,
            e.nombre AS estado,
            r.fecha_creacion,
            r.fecha_cierre,
            r.tiempo_atencion_minutos
        FROM reclamos r
        INNER JOIN clientes c ON c.id_cliente = r.id_cliente
        LEFT JOIN categorias_reclamo cat ON cat.id_categoria = r.id_categoria
        LEFT JOIN prioridades p ON p.id_prioridad = r.id_prioridad
        INNER JOIN estados_reclamo e ON e.id_estado = r.id_estado
        ORDER BY r.id_reclamo DESC
    """)
