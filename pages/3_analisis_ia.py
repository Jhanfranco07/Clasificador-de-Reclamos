import streamlit as st
import pandas as pd

from database.db_connection import init_db
from database.repositories import listar_reclamos, obtener_detalle_reclamo
from assets.styles import load_styles, hero, kpi, priority_badge, sentiment_badge, badge, esc

st.set_page_config(page_title="Análisis IA", page_icon="🧠", layout="wide")
load_styles()
init_db()

st.title("Resultado del análisis IA")
st.markdown(
    '<div class="page-subtitle">Clasificación, confianza, sentimiento y recomendación de atención.</div>',
    unsafe_allow_html=True,
)
hero(
    "Interpretación automática del reclamo",
    "Esta vista muestra cómo SmartClaim AI entiende el caso antes de generar una respuesta.",
)

df = pd.DataFrame(listar_reclamos())
if df.empty:
    st.info("Primero registra un reclamo.")
    st.stop()

id_reclamo = st.selectbox("Seleccione reclamo", df["id_reclamo"].tolist())
reclamo, analisis, respuesta, documentos, historial = obtener_detalle_reclamo(id_reclamo)

if not analisis:
    st.warning("Este reclamo todavía no tiene análisis IA.")
    st.stop()

st.markdown('<div class="section-card">', unsafe_allow_html=True)
st.subheader("Texto original")
st.write(reclamo["descripcion"])
st.markdown("</div>", unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi("Categoría", analisis["categoria_detectada"], "Resultado de clasificación", "🏷️")
with c2:
    kpi("Prioridad", reclamo["prioridad"], "Severidad del caso", "🚦")
with c3:
    kpi("Confianza", f"{analisis['confianza'] * 100:.0f}%", "Seguridad del análisis", "🧠")
with c4:
    kpi("Sentimiento", analisis["sentimiento"], "Tono detectado", "💬")

st.markdown(
    f"""
    <div class="status-box">
        {priority_badge(reclamo['prioridad'])} {badge(analisis['categoria_detectada'], 'info')}
        <br><br>
        <b>Palabras clave:</b> {esc(analisis['palabras_clave'])}<br>
        <b>Entidades detectadas:</b> {esc(analisis['entidades_detectadas'])}<br>
        <b>Recomendación:</b> {esc(analisis['recomendacion'])}
    </div>
    """,
    unsafe_allow_html=True,
)

if respuesta:
    if documentos:
        st.success(f"La respuesta sugerida registra {len(documentos)} documento(s) consultado(s) por RAG.")
    else:
        st.info("La respuesta sugerida fue generada sin RAG o no registra documentos consultados.")

if reclamo["requiere_revision_humana"]:
    st.warning("Este caso requiere revisión humana antes de enviar una respuesta final.")
else:
    st.success("Este caso puede continuar con respuesta sugerida.")
