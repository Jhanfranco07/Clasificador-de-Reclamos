import streamlit as st
import pandas as pd

from database.db_connection import init_db
from database.repositories import (
    obtener_metricas_bd, listar_logs_sistema, importar_dataset_entrenamiento_desde_csv,
    obtener_tiempos_atencion
)
from modules.metrics import (
    tiempo_promedio_atencion, reclamos_por_responsable,
    evaluacion_promedio_respuestas, reclamos_cerrados_vs_abiertos
)
from assets.styles import load_styles, hero, kpi, alert, badge, esc

st.set_page_config(page_title="Base de datos", page_icon="🗄️", layout="wide")
load_styles()
init_db()

st.title("Base de datos y trazabilidad")
st.markdown('<div class="page-subtitle">Control de tablas, dataset de entrenamiento, logs y métricas de atención.</div>', unsafe_allow_html=True)

hero(
    "Modelo de datos fortalecido",
    "Esta vista muestra las nuevas tablas de trazabilidad, evaluación, comentarios, logs y tiempos de atención incorporadas al prototipo."
)

metricas_tablas = pd.DataFrame(obtener_metricas_bd())
promedio = tiempo_promedio_atencion()
evaluacion = evaluacion_promedio_respuestas()

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi("Tablas controladas", len(metricas_tablas), "Modelo transaccional ampliado", "🗄️")
with c2:
    kpi("Tiempo promedio", f"{promedio} min", "Reclamos cerrados", "⏱️")
with c3:
    kpi("Claridad prom.", evaluacion["claridad"], "Evaluación de respuesta", "⭐")
with c4:
    kpi("Fundamentación prom.", evaluacion["fundamentacion"], "Uso de sustento documental", "📚")

st.markdown("### Registros por tabla")
st.dataframe(metricas_tablas, use_container_width=True, hide_index=True)

st.markdown("### Importar dataset de entrenamiento a SQLite")
if st.button("Importar dataset CSV a tabla dataset_entrenamiento", type="primary"):
    total = importar_dataset_entrenamiento_desde_csv()
    alert(f"Dataset disponible en SQLite. Registros actuales: {total}.", "success")
    st.rerun()

st.markdown("### Reclamos abiertos vs cerrados")
cerrados_df = pd.DataFrame(reclamos_cerrados_vs_abiertos())
if not cerrados_df.empty:
    st.bar_chart(cerrados_df.set_index("tipo"))
    st.dataframe(cerrados_df, use_container_width=True, hide_index=True)

st.markdown("### Reclamos por responsable")
resp_df = pd.DataFrame(reclamos_por_responsable())
if not resp_df.empty:
    st.bar_chart(resp_df.set_index("responsable"))
    st.dataframe(resp_df, use_container_width=True, hide_index=True)

st.markdown("### Tiempos de atención")
tiempos = pd.DataFrame(obtener_tiempos_atencion())
if not tiempos.empty:
    st.dataframe(tiempos, use_container_width=True, hide_index=True)
else:
    st.info("Aún no hay reclamos registrados.")

st.markdown("### Logs del sistema")
logs = pd.DataFrame(listar_logs_sistema(150))
if not logs.empty:
    st.dataframe(logs, use_container_width=True, hide_index=True)
else:
    st.info("Aún no existen logs registrados.")
