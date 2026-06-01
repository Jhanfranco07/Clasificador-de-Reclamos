import streamlit as st
import pandas as pd
from database.db_connection import init_db
from database.repositories import listar_documentos, listar_fragmentos_documento
from assets.styles import load_styles, hero, badge

st.set_page_config(page_title="Base documental", page_icon="📚", layout="wide")
load_styles()
init_db()

st.title("Base documental")
st.markdown('<div class="page-subtitle">Documentos internos usados para recuperación de contexto y generación de respuestas.</div>', unsafe_allow_html=True)
hero("Motor RAG & Embeddings activos", "Los documentos internos actúan como base de conocimiento para fundamentar las respuestas sugeridas.")

df = pd.DataFrame(listar_documentos())
if df.empty:
    st.info("No hay documentos cargados.")
    st.stop()

tipo = st.selectbox("Filtrar por tipo", ["Todos"] + sorted(df["tipo_documento"].unique().tolist()))
vista = df if tipo == "Todos" else df[df["tipo_documento"] == tipo]

st.dataframe(vista[["id_documento", "titulo", "tipo_documento", "categoria_asociada", "estado_indexacion", "fecha_actualizacion"]], use_container_width=True, hide_index=True)

st.markdown("### Documentos disponibles")
for _, doc in vista.iterrows():
    st.markdown(
        f"""
        <div class="doc-card">
            <b>{doc['titulo']}</b><br>
            {badge(doc['tipo_documento'], 'info')} {badge(doc['estado_indexacion'], 'low')}
            <div class="small-muted">Categoría asociada: {doc['categoria_asociada']} · Actualizado: {doc['fecha_actualizacion']}</div>
            <p>{doc['contenido']}</p>
        </div>
        """,
        unsafe_allow_html=True
    )


st.markdown("### Fragmentos usados por el motor RAG")
fragmentos = listar_fragmentos_documento()
if fragmentos:
    df_frag = pd.DataFrame(fragmentos)
    st.dataframe(
        df_frag[["id_fragmento", "titulo", "categoria_asociada", "orden_fragmento", "embedding_id"]],
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("Los fragmentos se generan desde la página Motor RAG o al ejecutar scripts/build_rag_index.py.")
