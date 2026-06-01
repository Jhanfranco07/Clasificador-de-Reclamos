import streamlit as st

from database.db_connection import init_db
from database.repositories import get_configuracion_activa, actualizar_configuracion
from assets.styles import load_styles, hero

st.set_page_config(page_title="Configuración IA", page_icon="⚙️", layout="wide")
load_styles()
init_db()

st.title("Configuración del modelo IA")
st.markdown(
    '<div class="page-subtitle">Parámetros básicos de confianza, revisión humana y recuperación documental.</div>',
    unsafe_allow_html=True,
)
hero(
    "Parámetros del prototipo",
    "Configura el umbral de confianza, el uso de RAG y la cantidad de documentos recuperados.",
)

config = get_configuracion_activa()
if not config:
    st.error("No se encontró configuración activa.")
    st.stop()

with st.form("config_ia"):
    st.text_input("Modelo base", value=config["modelo_base"], disabled=True)
    umbral = st.slider("Umbral de confianza", 0.0, 1.0, float(config["umbral_confianza"]), 0.01)
    revision = st.checkbox("Revisión humana obligatoria", value=bool(config["revision_humana_obligatoria"]))
    usar_rag = st.checkbox("Usar contexto RAG", value=bool(config["usar_rag"]))
    max_docs = st.number_input(
        "Máximo de documentos recuperados",
        min_value=1,
        max_value=10,
        value=int(config["max_documentos_recuperados"]),
    )
    guardar = st.form_submit_button("Guardar configuración", type="primary")

if guardar:
    try:
        actualizar_configuracion(umbral, revision, usar_rag, max_docs)
        st.success("Configuración actualizada correctamente.")
        st.info("El cambio de RAG se aplicará en el siguiente análisis o regeneración de respuesta.")
    except Exception as exc:
        st.error(f"No se pudo actualizar la configuración: {exc}")
