import streamlit as st
import pandas as pd

from database.db_connection import init_db
from database.repositories import listar_fragmentos_documento
from modules.rag_engine import (
    reconstruir_fragmentos_desde_documentos,
    construir_indice_vectorial,
    recuperar_documentos,
    obtener_resumen_indice
)
from assets.styles import load_styles, hero, kpi, alert, badge, esc

st.set_page_config(page_title="Motor RAG", page_icon="🔎", layout="wide")
load_styles()
init_db()

st.title("Motor RAG y base vectorial")
st.markdown('<div class="page-subtitle">Recuperación aumentada por generación usando fragmentos documentales y similitud vectorial local.</div>', unsafe_allow_html=True)

hero(
    "RAG académico funcional",
    "Esta sección muestra cómo los documentos se dividen en fragmentos, se vectorizan y se recuperan por similitud para sustentar las respuestas sugeridas."
)

resumen = obtener_resumen_indice()

c1, c2, c3, c4 = st.columns(4)
with c1:
    kpi("Documentos", resumen["documentos"], "Documentos base indexados", "📄")
with c2:
    kpi("Fragmentos", resumen["fragmentos"], "Unidades recuperables", "🧩")
with c3:
    kpi("Vectorizador", "Activo" if resumen["vectorizador"] else "Pendiente", "TF-IDF local", "🧠")
with c4:
    kpi("Matriz", "Activa" if resumen["matriz"] else "Pendiente", "Base vectorial local", "🗃️")

st.markdown("### Administración del índice")
a1, a2 = st.columns(2)

if a1.button("Regenerar fragmentos documentales", type="primary"):
    total = reconstruir_fragmentos_desde_documentos()
    alert(f"Se regeneraron {total} fragmentos documentales en SQLite.", "success")
    st.rerun()

if a2.button("Reconstruir índice vectorial"):
    resultado = construir_indice_vectorial(forzar=True)
    alert(f"Índice vectorial reconstruido. Estado: {resultado.get('status')}.", "success")
    st.rerun()

st.markdown("### Probar recuperación RAG")
categoria = st.selectbox(
    "Categoría de contexto",
    [
        "Retraso de pedido",
        "Cobro indebido",
        "Producto incorrecto",
        "Producto incompleto",
        "Problema con tarjeta",
        "Fraude o seguridad",
        "Soporte general"
    ]
)

consulta = st.text_area(
    "Consulta o reclamo de prueba",
    height=120,
    placeholder="Ejemplo: Me cobraron dos veces por un pedido que fue cancelado."
)

max_docs = st.slider("Cantidad de fragmentos a recuperar", 1, 5, 3)

if st.button("Recuperar fragmentos relevantes", type="primary"):
    if not consulta.strip():
        alert("Ingrese un texto para probar la recuperación RAG.", "warn")
    else:
        resultados = recuperar_documentos(consulta, categoria, max_docs=max_docs)

        st.markdown("### Fragmentos recuperados")
        for item in resultados:
            st.markdown(
                f"""
                <div class="doc-card">
                    <div class="doc-title">{esc(item['titulo'])}</div>
                    {badge(item['tipo_documento'], 'info')}
                    {badge(item['categoria_asociada'], 'neutral')}
                    <span class="muted">Score: {esc(item['score'])} · Fragmento: {esc(item.get('id_fragmento'))}</span>
                    <p>{esc(item['fragmento'])}</p>
                </div>
                """,
                unsafe_allow_html=True
            )

st.markdown("### Fragmentos registrados en SQLite")
fragmentos = listar_fragmentos_documento()
df = pd.DataFrame(fragmentos)

if not df.empty:
    st.dataframe(
        df[["id_fragmento", "id_documento", "titulo", "tipo_documento", "categoria_asociada", "orden_fragmento", "embedding_id"]],
        use_container_width=True,
        hide_index=True
    )

    with st.expander("Ver contenido de fragmentos"):
        for frag in fragmentos:
            st.markdown(
                f"""
                <div class="doc-card">
                    <div class="doc-title">{esc(frag['titulo'])} · Fragmento {esc(frag['orden_fragmento'])}</div>
                    <p>{esc(frag['texto_fragmento'])}</p>
                </div>
                """,
                unsafe_allow_html=True
            )
else:
    st.info("Aún no existen fragmentos. Use el botón Regenerar fragmentos documentales.")
