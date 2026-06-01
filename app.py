import pandas as pd
import streamlit as st

from assets.styles import (
    load_styles,
    hero,
    kpi,
    panel_start,
    panel_end,
    priority_badge,
    status_badge,
    esc,
)
from database.db_connection import init_db
from database.repositories import listar_reclamos
from modules.metrics import obtener_metricas_dashboard, reclamos_por_categoria, reclamos_por_prioridad

st.set_page_config(page_title="SmartClaim AI", page_icon="🤖", layout="wide", initial_sidebar_state="expanded")
load_styles()
init_db()

st.title("SmartClaim AI")
st.markdown(
    '<div class="page-subtitle">Clasificador y gestor inteligente de reclamos para soporte operativo.</div>',
    unsafe_allow_html=True,
)
hero(
    "Centro de control de reclamos",
    "Supervisa volumen operativo, casos clasificados por IA, reclamos pendientes, prioridades y trazabilidad del soporte asistido.",
)

m = obtener_metricas_dashboard()
c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi("Reclamos recibidos", m["total"], "Total acumulado en el prototipo", "📥")
with c2:
    kpi("Clasificados por IA", m["analizados"], "Casos procesados automáticamente", "🧠")
with c3:
    kpi("Pendientes", m["pendientes"], "Nuevos, en revisión o escalados", "⏱️")
with c4:
    kpi("Automatización", f"{m['tasa_automatizacion']}%", "Casos con análisis generado", "⚡")

c5, c6, c7, c8 = st.columns(4)
with c5:
    kpi("Revisión humana", f"{m.get('porcentaje_revision_humana', 0)}%", "Casos que requieren agente", "👤")
with c6:
    kpi("Aprobación", f"{m.get('porcentaje_respuestas_aprobadas', 0)}%", "Respuestas aprobadas", "✅")
with c7:
    kpi("Confianza IA", f"{m.get('confianza_promedio', 0)}%", "Promedio del modelo", "📈")
with c8:
    kpi("Críticos pendientes", m.get("casos_criticos_pendientes", 0), "Prioridad crítica abierta", "🚨")

st.markdown("### Flujo operativo")
f1, f2, f3, f4 = st.columns(4)
with f1:
    panel_start("1. Registrar", "Ingresa cliente, pedido y descripción del reclamo.")
    panel_end()
with f2:
    panel_start("2. Clasificar", "La IA detecta categoría, prioridad, confianza y sentimiento.")
    panel_end()
with f3:
    panel_start("3. Sustentar", "RAG busca documentos internos si está activado.")
    panel_end()
with f4:
    panel_start("4. Revisar", "El agente edita, aprueba, responde, escala o cierra.")
    panel_end()

st.markdown("### Vista operativa")
left, right = st.columns(2)
with left:
    panel_start("Distribución por categoría", "Permite identificar los motivos de reclamo más frecuentes.")
    data_cat = pd.DataFrame(reclamos_por_categoria())
    if not data_cat.empty:
        st.bar_chart(data_cat.set_index("categoria"))
    else:
        st.info("Aún no hay reclamos registrados.")
    panel_end()

with right:
    panel_start("Distribución por prioridad", "Ayuda a controlar casos críticos y carga operativa.")
    data_pri = pd.DataFrame(reclamos_por_prioridad())
    if not data_pri.empty:
        st.bar_chart(data_pri.set_index("prioridad"))
    else:
        st.info("Aún no hay prioridades asignadas.")
    panel_end()

st.markdown("### Reclamos recientes")
reclamos = pd.DataFrame(listar_reclamos())
if reclamos.empty:
    st.info("Registra un nuevo reclamo desde el menú lateral para activar el dashboard.")
else:
    st.dataframe(
        reclamos[["codigo_reclamo", "cliente", "codigo_pedido", "categoria", "prioridad", "estado", "fecha_creacion"]],
        use_container_width=True,
        hide_index=True,
    )
    st.markdown("### Tarjetas de seguimiento")
    for _, row in reclamos.head(6).iterrows():
        st.markdown(
            f"""
            <div class="case-card">
                <div class="case-title">{esc(row["codigo_reclamo"])} · {esc(row["cliente"])}</div>
                {priority_badge(row["prioridad"])} {status_badge(row["estado"])}
                <div class="muted">
                    Pedido {esc(row["codigo_pedido"])} · Categoría: {esc(row["categoria"])} · Fecha: {esc(row["fecha_creacion"])}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
