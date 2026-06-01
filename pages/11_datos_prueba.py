import streamlit as st
import pandas as pd

from database.db_connection import init_db
from database.repositories import contar_reclamos, listar_reclamos_simples, limpiar_datos_prueba, registrar_log
from scripts.generate_sample_data import generar_reclamos
from assets.styles import load_styles, hero, kpi, alert, badge, esc

st.set_page_config(page_title="Datos de prueba", page_icon="🧪", layout="wide")
load_styles()
init_db()

st.title("Datos de prueba")
st.markdown('<div class="page-subtitle">Generador de reclamos simulados para alimentar dashboard, reportes y pruebas funcionales.</div>', unsafe_allow_html=True)

hero(
    "Generador de escenarios simulados",
    "Crea reclamos por categoría para que el prototipo tenga datos suficientes y los reportes muestren indicadores útiles."
)

total_actual = contar_reclamos()

c1, c2, c3 = st.columns(3)
with c1:
    kpi("Reclamos actuales", total_actual, "Datos transaccionales", "📥")
with c2:
    kpi("Categorías base", 5, "Retraso, cobro, fraude, incompleto y soporte", "🏷️")
with c3:
    kpi("Volumen sugerido", 250, "50 reclamos por categoría", "🧪")

st.markdown("### Configuración de generación")
cantidad = st.slider("Cantidad por categoría", 5, 100, 50, step=5)
limpiar = st.checkbox("Limpiar reclamos existentes antes de generar", value=True)

st.warning("Si activas la limpieza, se eliminarán reclamos, clientes, análisis, respuestas, comentarios y trazabilidad transaccional. No se eliminan catálogos, documentos, modelos ni configuración.")

g1, g2 = st.columns(2)

if g1.button("Generar datos de prueba", type="primary"):
    total = generar_reclamos(cantidad_por_categoria=cantidad, limpiar=limpiar)
    alert(f"Datos de prueba generados correctamente. Reclamos creados o disponibles: {total}.", "success")
    st.rerun()

if g2.button("Limpiar datos transaccionales"):
    limpiar_datos_prueba()
    registrar_log("Datos de prueba", "Limpieza de datos", "WARNING", "Se limpiaron los datos transaccionales desde la interfaz.", None)
    alert("Datos transaccionales eliminados correctamente.", "warn")
    st.rerun()

st.markdown("### Distribución esperada")
esperado = pd.DataFrame([
    {"categoria": "Retraso de pedido", "cantidad": cantidad},
    {"categoria": "Cobro indebido", "cantidad": cantidad},
    {"categoria": "Fraude o seguridad", "cantidad": cantidad},
    {"categoria": "Producto incompleto", "cantidad": cantidad},
    {"categoria": "Soporte general", "cantidad": cantidad},
])
st.dataframe(esperado, use_container_width=True, hide_index=True)

st.markdown("### Reclamos actuales")
reclamos = pd.DataFrame(listar_reclamos_simples())
if not reclamos.empty:
    st.dataframe(reclamos, use_container_width=True, hide_index=True)

    st.markdown("### Resumen por categoría")
    resumen = reclamos.groupby("categoria").size().reset_index(name="total").sort_values("total", ascending=False)
    st.bar_chart(resumen.set_index("categoria"))
    st.dataframe(resumen, use_container_width=True, hide_index=True)
else:
    st.info("Aún no hay reclamos. Usa el botón Generar datos de prueba.")
