from database.db_connection import fetch_all, fetch_one

def _safe_number(value, decimals=1):
    if value is None:
        return 0
    try:
        return round(float(value), decimals)
    except Exception:
        return 0

def obtener_metricas_dashboard():
    total = fetch_one("SELECT COUNT(*) AS total FROM reclamos")["total"]

    analizados = fetch_one("SELECT COUNT(*) AS total FROM analisis_ia")["total"]

    pendientes = fetch_one("""
        SELECT COUNT(*) AS total
        FROM reclamos r
        INNER JOIN estados_reclamo e ON e.id_estado = r.id_estado
        WHERE e.nombre IN ('Nuevo', 'En revisión', 'Escalado')
    """)["total"]

    respondidos = fetch_one("""
        SELECT COUNT(*) AS total
        FROM reclamos r
        INNER JOIN estados_reclamo e ON e.id_estado = r.id_estado
        WHERE e.nombre IN ('Respondido', 'Cerrado')
    """)["total"]

    revision_humana = fetch_one("""
        SELECT COUNT(*) AS total
        FROM reclamos
        WHERE requiere_revision_humana = 1
    """)["total"]

    respuestas_total = fetch_one("SELECT COUNT(*) AS total FROM respuestas_sugeridas")["total"]

    respuestas_aprobadas = fetch_one("""
        SELECT COUNT(*) AS total
        FROM respuestas_sugeridas
        WHERE estado_revision IN ('APROBADA', 'ENVIADA')
    """)["total"]

    casos_criticos_pendientes = fetch_one("""
        SELECT COUNT(*) AS total
        FROM reclamos r
        INNER JOIN prioridades p ON p.id_prioridad = r.id_prioridad
        INNER JOIN estados_reclamo e ON e.id_estado = r.id_estado
        WHERE p.nombre = 'Crítica'
        AND e.nombre NOT IN ('Respondido', 'Cerrado')
    """)["total"]

    confianza_promedio = fetch_one("""
        SELECT AVG(confianza) AS promedio
        FROM analisis_ia
    """)["promedio"]

    tiempo_promedio = fetch_one("""
        SELECT AVG(tiempo_atencion_minutos) AS promedio
        FROM reclamos
        WHERE tiempo_atencion_minutos IS NOT NULL
    """)["promedio"]

    return {
        "total": total,
        "analizados": analizados,
        "pendientes": pendientes,
        "respondidos": respondidos,
        "tasa_automatizacion": round((analizados / total) * 100, 1) if total else 0,
        "revision_humana": revision_humana,
        "porcentaje_revision_humana": round((revision_humana / total) * 100, 1) if total else 0,
        "respuestas_total": respuestas_total,
        "respuestas_aprobadas": respuestas_aprobadas,
        "porcentaje_respuestas_aprobadas": round((respuestas_aprobadas / respuestas_total) * 100, 1) if respuestas_total else 0,
        "tiempo_promedio_atencion": _safe_number(tiempo_promedio),
        "casos_criticos_pendientes": casos_criticos_pendientes,
        "confianza_promedio": round(float(confianza_promedio) * 100, 1) if confianza_promedio is not None else 0
    }

def reclamos_por_categoria():
    return fetch_all("""
        SELECT COALESCE(c.nombre, 'Sin clasificar') AS categoria, COUNT(*) AS total
        FROM reclamos r
        LEFT JOIN categorias_reclamo c ON c.id_categoria = r.id_categoria
        GROUP BY COALESCE(c.nombre, 'Sin clasificar')
        ORDER BY total DESC
    """)

def reclamos_por_prioridad():
    return fetch_all("""
        SELECT COALESCE(p.nombre, 'Sin prioridad') AS prioridad, COUNT(*) AS total
        FROM reclamos r
        LEFT JOIN prioridades p ON p.id_prioridad = r.id_prioridad
        GROUP BY COALESCE(p.nombre, 'Sin prioridad')
        ORDER BY
            CASE COALESCE(p.nombre, 'Sin prioridad')
                WHEN 'Crítica' THEN 1
                WHEN 'Alta' THEN 2
                WHEN 'Media' THEN 3
                WHEN 'Baja' THEN 4
                ELSE 5
            END
    """)

def reclamos_por_estado():
    return fetch_all("""
        SELECT e.nombre AS estado, COUNT(*) AS total
        FROM reclamos r
        INNER JOIN estados_reclamo e ON e.id_estado = r.id_estado
        GROUP BY e.nombre
        ORDER BY total DESC
    """)

def reclamos_por_canal():
    return fetch_all("""
        SELECT COALESCE(canal_venta, 'Sin canal') AS canal, COUNT(*) AS total
        FROM reclamos
        GROUP BY COALESCE(canal_venta, 'Sin canal')
        ORDER BY total DESC
    """)

def distribucion_sentimiento():
    return fetch_all("""
        SELECT COALESCE(sentimiento, 'Sin análisis') AS sentimiento, COUNT(*) AS total
        FROM analisis_ia
        GROUP BY COALESCE(sentimiento, 'Sin análisis')
        ORDER BY total DESC
    """)

def confianza_por_categoria():
    rows = fetch_all("""
        SELECT
            COALESCE(ai.categoria_detectada, 'Sin clasificar') AS categoria,
            AVG(ai.confianza) AS confianza_promedio,
            COUNT(*) AS total
        FROM analisis_ia ai
        GROUP BY COALESCE(ai.categoria_detectada, 'Sin clasificar')
        ORDER BY confianza_promedio DESC
    """)
    return [
        {
            "categoria": row["categoria"],
            "confianza_promedio": _safe_number((row["confianza_promedio"] or 0) * 100),
            "total": row["total"],
        }
        for row in rows
    ]

def revision_humana_por_categoria():
    return fetch_all("""
        SELECT
            COALESCE(c.nombre, 'Sin clasificar') AS categoria,
            SUM(CASE WHEN r.requiere_revision_humana = 1 THEN 1 ELSE 0 END) AS con_revision,
            COUNT(*) AS total,
            ROUND((SUM(CASE WHEN r.requiere_revision_humana = 1 THEN 1 ELSE 0 END) * 100.0) / COUNT(*), 1) AS porcentaje
        FROM reclamos r
        LEFT JOIN categorias_reclamo c ON c.id_categoria = r.id_categoria
        GROUP BY COALESCE(c.nombre, 'Sin clasificar')
        ORDER BY porcentaje DESC
    """)

def respuestas_por_estado_revision():
    return fetch_all("""
        SELECT estado_revision, COUNT(*) AS total
        FROM respuestas_sugeridas
        GROUP BY estado_revision
        ORDER BY total DESC
    """)

def tiempo_promedio_atencion():
    row = fetch_one("""
        SELECT AVG(tiempo_atencion_minutos) AS promedio
        FROM reclamos
        WHERE tiempo_atencion_minutos IS NOT NULL
    """)
    return round(row["promedio"], 1) if row and row["promedio"] is not None else 0

def tiempo_promedio_por_categoria():
    rows = fetch_all("""
        SELECT
            COALESCE(c.nombre, 'Sin clasificar') AS categoria,
            AVG(r.tiempo_atencion_minutos) AS tiempo_promedio_min,
            COUNT(*) AS total
        FROM reclamos r
        LEFT JOIN categorias_reclamo c ON c.id_categoria = r.id_categoria
        WHERE r.tiempo_atencion_minutos IS NOT NULL
        GROUP BY COALESCE(c.nombre, 'Sin clasificar')
        ORDER BY tiempo_promedio_min DESC
    """)
    return [
        {
            "categoria": row["categoria"],
            "tiempo_promedio_min": _safe_number(row["tiempo_promedio_min"]),
            "total": row["total"],
        }
        for row in rows
    ]

def casos_criticos_pendientes_detalle():
    return fetch_all("""
        SELECT
            r.codigo_reclamo,
            c.nombre AS cliente,
            r.codigo_pedido,
            COALESCE(cat.nombre, 'Sin clasificar') AS categoria,
            p.nombre AS prioridad,
            e.nombre AS estado,
            r.fecha_creacion,
            COALESCE(r.responsable_asignado, 'Sin asignar') AS responsable
        FROM reclamos r
        INNER JOIN clientes c ON c.id_cliente = r.id_cliente
        LEFT JOIN categorias_reclamo cat ON cat.id_categoria = r.id_categoria
        INNER JOIN prioridades p ON p.id_prioridad = r.id_prioridad
        INNER JOIN estados_reclamo e ON e.id_estado = r.id_estado
        WHERE p.nombre = 'Crítica'
        AND e.nombre NOT IN ('Respondido', 'Cerrado')
        ORDER BY r.fecha_creacion ASC
    """)

def reclamos_por_responsable():
    return fetch_all("""
        SELECT COALESCE(responsable_asignado, 'Sin asignar') AS responsable, COUNT(*) AS total
        FROM reclamos
        GROUP BY COALESCE(responsable_asignado, 'Sin asignar')
        ORDER BY total DESC
    """)

def evaluacion_promedio_respuestas():
    row = fetch_one("""
        SELECT
            AVG(claridad) AS claridad,
            AVG(utilidad) AS utilidad,
            AVG(tono) AS tono,
            AVG(fundamentacion) AS fundamentacion
        FROM evaluacion_respuesta
    """)
    if not row:
        return {"claridad": 0, "utilidad": 0, "tono": 0, "fundamentacion": 0}

    return {
        "claridad": round(row["claridad"] or 0, 1),
        "utilidad": round(row["utilidad"] or 0, 1),
        "tono": round(row["tono"] or 0, 1),
        "fundamentacion": round(row["fundamentacion"] or 0, 1)
    }

def reclamos_cerrados_vs_abiertos():
    return fetch_all("""
        SELECT
            CASE WHEN fecha_cierre IS NULL THEN 'Abiertos' ELSE 'Cerrados' END AS tipo,
            COUNT(*) AS total
        FROM reclamos
        GROUP BY CASE WHEN fecha_cierre IS NULL THEN 'Abiertos' ELSE 'Cerrados' END
    """)

def resumen_ejecutivo_reportes():
    m = obtener_metricas_dashboard()
    return [
        {"indicador": "Total de reclamos", "valor": m["total"]},
        {"indicador": "Tasa de automatización", "valor": f'{m["tasa_automatizacion"]}%'},
        {"indicador": "Casos con revisión humana", "valor": f'{m["porcentaje_revision_humana"]}%'},
        {"indicador": "Respuestas aprobadas", "valor": f'{m["porcentaje_respuestas_aprobadas"]}%'},
        {"indicador": "Tiempo promedio de atención", "valor": f'{m["tiempo_promedio_atencion"]} min'},
        {"indicador": "Casos críticos pendientes", "valor": m["casos_criticos_pendientes"]},
        {"indicador": "Confianza promedio del modelo", "valor": f'{m["confianza_promedio"]}%'}
    ]
