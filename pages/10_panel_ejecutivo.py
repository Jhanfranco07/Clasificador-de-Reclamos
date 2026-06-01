import streamlit as st
import pandas as pd

from database.db_connection import init_db
from modules.metrics import (
    obtener_metricas_dashboard,
    resumen_ejecutivo_reportes,
    casos_criticos_pendientes_detalle,
    reclamos_por_estado,
    reclamos_por_canal,
    distribucion_sentimiento
)
from assets.styles import load_styles, hero, kpi, panel_start, panel_end, esc

st.set_page_config(page_title="Panel ejecutivo", page_icon="📈", layout="wide")
load_styles()
init_db()

st.title("Panel ejecutivo")
st.markdown('<div class="page-subtitle">Vista resumida para supervisores y responsables de atención al cliente.</div>', unsafe_allow_html=True)

hero(
    "Indicadores clave para decisión",
    "Resume los puntos más importantes del sistema: automatización, revisión humana, confianza, aprobación, casos críticos y comportamiento del cliente."
)

m = obtener_metricas_dashboard()

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi("Automatización", f'{m["tasa_automatizacion"]}%', "Eficiencia del análisis IA", "⚡")
with c2:
    kpi("Revisión humana", f'{m["porcentaje_revision_humana"]}%', "Control requerido", "👤")
with c3:
    kpi("Confianza IA", f'{m["confianza_promedio"]}%', "Promedio del modelo", "🧠")
with c4:
    kpi("Críticos pendientes", m["casos_criticos_pendientes"], "Riesgo operativo", "🚨")

st.markdown("### Resumen de indicadores")
st.dataframe(pd.DataFrame(resumen_ejecutivo_reportes()), use_container_width=True, hide_index=True)

left, right = st.columns(2)

with left:
    panel_start("Estado del flujo", "Distribución de reclamos según avance.")
    df_estado = pd.DataFrame(reclamos_por_estado())
    if not df_estado.empty:
        st.bar_chart(df_estado.set_index("estado"))
    else:
        st.info("Sin datos.")
    panel_end()

with right:
    panel_start("Canales de ingreso", "Origen de los reclamos registrados.")
    df_canal = pd.DataFrame(reclamos_por_canal())
    if not df_canal.empty:
        st.bar_chart(df_canal.set_index("canal"))
    else:
        st.info("Sin datos.")
    panel_end()

panel_start("Sentimiento del cliente", "Distribución del tono detectado en los reclamos.")
df_sent = pd.DataFrame(distribucion_sentimiento())
if not df_sent.empty:
    st.bar_chart(df_sent.set_index("sentimiento"))
    st.dataframe(df_sent, use_container_width=True, hide_index=True)
else:
    st.info("Aún no hay análisis de sentimiento.")
panel_end()

criticos = pd.DataFrame(casos_criticos_pendientes_detalle())
st.markdown("### Casos críticos pendientes")
if not criticos.empty:
    st.warning("Hay casos críticos pendientes que requieren priorización.")
    st.dataframe(criticos, use_container_width=True, hide_index=True)
else:
    st.success("No hay casos críticos pendientes.")
