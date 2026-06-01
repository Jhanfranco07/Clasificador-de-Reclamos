import streamlit as st
import pandas as pd

from database.db_connection import init_db
from modules.metrics import (
    obtener_metricas_dashboard,
    reclamos_por_categoria,
    reclamos_por_prioridad,
    reclamos_por_estado,
    reclamos_por_canal,
    distribucion_sentimiento,
    confianza_por_categoria,
    revision_humana_por_categoria,
    respuestas_por_estado_revision,
    tiempo_promedio_por_categoria,
    casos_criticos_pendientes_detalle,
    reclamos_por_responsable,
    evaluacion_promedio_respuestas,
    reclamos_cerrados_vs_abiertos,
    resumen_ejecutivo_reportes
)
from assets.styles import load_styles, hero, kpi, panel_start, panel_end, badge, esc

st.set_page_config(page_title="Reportes avanzados", page_icon="📊", layout="wide")
load_styles()
init_db()

st.title("Reportes y métricas avanzadas")
st.markdown(
    '<div class="page-subtitle">Panel analítico para toma de decisiones sobre reclamos, IA, revisión humana y desempeño operativo.</div>',
    unsafe_allow_html=True
)

hero(
    "Analítica ejecutiva de SmartClaim AI",
    "Este tablero permite evaluar categorías, prioridades, estados, canales, revisión humana, respuestas aprobadas, tiempo de atención, casos críticos, confianza del modelo y sentimiento del cliente."
)

m = obtener_metricas_dashboard()
eval_prom = evaluacion_promedio_respuestas()

st.markdown("### Indicadores principales")
c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi("Reclamos", m["total"], "Total registrados", "📥")
with c2:
    kpi("Automatización", f'{m["tasa_automatizacion"]}%', "Casos analizados por IA", "⚡")
with c3:
    kpi("Revisión humana", f'{m["porcentaje_revision_humana"]}%', "Casos que requieren agente", "👤")
with c4:
    kpi("Aprobación", f'{m["porcentaje_respuestas_aprobadas"]}%', "Respuestas aprobadas", "✅")

c5, c6, c7, c8 = st.columns(4)
with c5:
    kpi("Tiempo prom.", f'{m["tiempo_promedio_atencion"]} min', "Reclamos cerrados", "⏱️")
with c6:
    kpi("Críticos pendientes", m["casos_criticos_pendientes"], "Prioridad crítica abierta", "🚨")
with c7:
    kpi("Confianza IA", f'{m["confianza_promedio"]}%', "Promedio del modelo", "🧠")
with c8:
    kpi("Fundamentación", eval_prom["fundamentacion"], "Evaluación de respuestas", "📚")

st.markdown("### Resumen ejecutivo")
resumen_df = pd.DataFrame(resumen_ejecutivo_reportes())
st.dataframe(resumen_df, use_container_width=True, hide_index=True)

st.markdown("### Distribución de reclamos")
r1, r2 = st.columns(2)

with r1:
    panel_start("Reclamos por categoría", "Identifica qué tipo de reclamo se presenta con mayor frecuencia.")
    df_cat = pd.DataFrame(reclamos_por_categoria())
    if not df_cat.empty:
        st.bar_chart(df_cat.set_index("categoria"))
        st.dataframe(df_cat, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay reclamos registrados.")
    panel_end()

with r2:
    panel_start("Reclamos por prioridad", "Permite observar la severidad de la carga operativa.")
    df_pri = pd.DataFrame(reclamos_por_prioridad())
    if not df_pri.empty:
        st.bar_chart(df_pri.set_index("prioridad"))
        st.dataframe(df_pri, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay prioridades asignadas.")
    panel_end()

r3, r4 = st.columns(2)

with r3:
    panel_start("Reclamos por estado", "Muestra el avance del flujo de atención.")
    df_estado = pd.DataFrame(reclamos_por_estado())
    if not df_estado.empty:
        st.bar_chart(df_estado.set_index("estado"))
        st.dataframe(df_estado, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay estados registrados.")
    panel_end()

with r4:
    panel_start("Reclamos por canal", "Ayuda a identificar desde dónde ingresan más casos.")
    df_canal = pd.DataFrame(reclamos_por_canal())
    if not df_canal.empty:
        st.bar_chart(df_canal.set_index("canal"))
        st.dataframe(df_canal, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay canales registrados.")
    panel_end()

st.markdown("### Métricas de IA y revisión humana")
ia1, ia2 = st.columns(2)

with ia1:
    panel_start("Confianza promedio por categoría", "Permite revisar en qué categorías el modelo clasifica con mayor seguridad.")
    df_conf = pd.DataFrame(confianza_por_categoria())
    if not df_conf.empty:
        st.bar_chart(df_conf.set_index("categoria")["confianza_promedio"])
        st.dataframe(df_conf, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay análisis IA registrados.")
    panel_end()

with ia2:
    panel_start("Distribución de sentimiento", "Ayuda a medir el tono de los reclamos procesados.")
    df_sent = pd.DataFrame(distribucion_sentimiento())
    if not df_sent.empty:
        st.bar_chart(df_sent.set_index("sentimiento"))
        st.dataframe(df_sent, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay sentimientos detectados.")
    panel_end()

ia3, ia4 = st.columns(2)

with ia3:
    panel_start("Revisión humana por categoría", "Muestra qué categorías requieren mayor intervención del agente.")
    df_rev = pd.DataFrame(revision_humana_por_categoria())
    if not df_rev.empty:
        st.bar_chart(df_rev.set_index("categoria")["porcentaje"])
        st.dataframe(df_rev, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay datos de revisión humana.")
    panel_end()

with ia4:
    panel_start("Respuestas por estado de revisión", "Permite evaluar aprobación, edición o rechazo de respuestas.")
    df_resp = pd.DataFrame(respuestas_por_estado_revision())
    if not df_resp.empty:
        st.bar_chart(df_resp.set_index("estado_revision"))
        st.dataframe(df_resp, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay respuestas sugeridas.")
    panel_end()

st.markdown("### Desempeño operativo")
op1, op2 = st.columns(2)

with op1:
    panel_start("Tiempo promedio por categoría", "Calculado sobre reclamos cerrados con tiempo de atención registrado.")
    df_tiempo = pd.DataFrame(tiempo_promedio_por_categoria())
    if not df_tiempo.empty:
        st.bar_chart(df_tiempo.set_index("categoria")["tiempo_promedio_min"])
        st.dataframe(df_tiempo, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay reclamos cerrados con tiempo de atención calculado.")
    panel_end()

with op2:
    panel_start("Reclamos por responsable", "Permite monitorear la carga asignada por agente o supervisor.")
    df_respble = pd.DataFrame(reclamos_por_responsable())
    if not df_respble.empty:
        st.bar_chart(df_respble.set_index("responsable"))
        st.dataframe(df_respble, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay responsables asignados.")
    panel_end()

op3, op4 = st.columns(2)

with op3:
    panel_start("Abiertos vs cerrados", "Indicador general de avance de atención.")
    df_cierre = pd.DataFrame(reclamos_cerrados_vs_abiertos())
    if not df_cierre.empty:
        st.bar_chart(df_cierre.set_index("tipo"))
        st.dataframe(df_cierre, use_container_width=True, hide_index=True)
    else:
        st.info("Aún no hay datos de cierre.")
    panel_end()

with op4:
    panel_start("Evaluación promedio de respuestas", "Calidad percibida de respuestas revisadas.")
    eval_df = pd.DataFrame([
        {"criterio": "Claridad", "puntaje": eval_prom["claridad"]},
        {"criterio": "Utilidad", "puntaje": eval_prom["utilidad"]},
        {"criterio": "Tono", "puntaje": eval_prom["tono"]},
        {"criterio": "Fundamentación", "puntaje": eval_prom["fundamentacion"]}
    ])
    st.bar_chart(eval_df.set_index("criterio"))
    st.dataframe(eval_df, use_container_width=True, hide_index=True)
    panel_end()

st.markdown("### Casos críticos pendientes")
criticos = pd.DataFrame(casos_criticos_pendientes_detalle())

if not criticos.empty:
    st.warning("Existen casos críticos pendientes de atención. Se recomienda priorizarlos.")
    st.dataframe(criticos, use_container_width=True, hide_index=True)
else:
    st.success("No existen casos críticos pendientes.")

st.markdown("### Lectura rápida para toma de decisiones")
if m["casos_criticos_pendientes"] > 0:
    st.markdown(
        f"""
        <div class="alert-warn">
            Hay {esc(m["casos_criticos_pendientes"])} caso(s) crítico(s) pendiente(s). 
            Se recomienda revisar la bandeja de historial y asignar responsable.
        </div>
        """,
        unsafe_allow_html=True
    )
elif m["porcentaje_revision_humana"] >= 70 and m["total"] > 0:
    st.markdown(
        f"""
        <div class="alert-warn">
            El porcentaje de revisión humana es alto ({esc(m["porcentaje_revision_humana"])}%). 
            Se recomienda revisar el umbral de confianza o mejorar el dataset del clasificador.
        </div>
        """,
        unsafe_allow_html=True
    )
else:
    st.markdown(
        """
        <div class="alert-success">
            El sistema no registra alertas críticas en este momento. Los indicadores pueden usarse para sustentar el impacto operativo del prototipo.
        </div>
        """,
        unsafe_allow_html=True
    )
