import streamlit as st
import pandas as pd
from pathlib import Path

from database.db_connection import init_db
from modules.classifier import clasificar_reclamo, MODEL_PATH, DATASET_PATH
from assets.styles import load_styles, hero, kpi, alert, analysis_grid, priority_badge, sentiment_badge, badge, esc

st.set_page_config(page_title="Modelo IA", page_icon="🤖", layout="wide")
load_styles()
init_db()

st.title("Modelo IA de clasificación")
st.markdown('<div class="page-subtitle">Clasificador real con Scikit-learn usando TF-IDF y Logistic Regression.</div>', unsafe_allow_html=True)

hero(
    "Clasificador Machine Learning",
    "Esta sección permite evidenciar que el prototipo no solo usa reglas, sino un modelo entrenado con dataset de reclamos de ejemplo."
)

df = pd.read_csv(DATASET_PATH)

c1, c2, c3 = st.columns(3)
with c1:
    kpi("Registros dataset", len(df), "Casos usados para entrenamiento", "📄")
with c2:
    kpi("Categorías", df["categoria"].nunique(), "Clases de reclamo", "🧠")
with c3:
    kpi("Modelo guardado", "Sí" if MODEL_PATH.exists() else "Se genera al clasificar", "Archivo joblib", "💾")

st.markdown("### Distribución del dataset")
dist = df.groupby("categoria").size().reset_index(name="total")
st.bar_chart(dist.set_index("categoria"))
st.dataframe(dist, use_container_width=True, hide_index=True)

st.markdown("### Probar clasificador")
texto = st.text_area(
    "Ingrese un reclamo de prueba",
    height=140,
    placeholder="Ejemplo: Me cobraron dos veces por el mismo pedido y necesito devolución."
)

if st.button("Clasificar texto", type="primary"):
    if not texto.strip():
        alert("Ingrese un texto para clasificar.", "warn")
    else:
        resultado = clasificar_reclamo(texto)

        analysis_grid([
            ("Categoría", resultado["categoria"]),
            ("Prioridad", resultado["prioridad"]),
            ("Confianza", f"{resultado['confianza'] * 100:.0f}%"),
            ("Sentimiento", resultado["sentimiento"])
        ])

        st.markdown(
            f"""
            <div class="panel">
                <div class="panel-title">Resultado del clasificador ML</div>
                {badge(resultado['categoria'], 'info')}
                {priority_badge(resultado['prioridad'])}
                {sentiment_badge(resultado['sentimiento'])}
                <p><b>Modelo usado:</b> {esc(resultado.get('modelo_usado'))}</p>
                <p><b>Palabras clave:</b> {esc(", ".join(resultado["palabras_clave"]))}</p>
                <p><b>Entidades:</b> {esc(", ".join(resultado["entidades"]))}</p>
                <p><b>Recomendación:</b> {esc(resultado["recomendacion"])}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

st.markdown("### Vista previa del dataset")
st.dataframe(df.head(30), use_container_width=True, hide_index=True)
