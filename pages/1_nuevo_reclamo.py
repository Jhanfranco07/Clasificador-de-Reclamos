import re

import streamlit as st

from database.db_connection import init_db
from database.repositories import (
    crear_cliente,
    crear_reclamo,
    guardar_analisis,
    guardar_respuesta,
    get_configuracion_activa,
)
from modules.classifier import clasificar_reclamo
from modules.rag_engine import (
    recuperar_documentos,
    generar_respuesta_sugerida,
    generar_respuesta_basica,
)
from assets.styles import (
    load_styles,
    hero,
    alert,
    analysis_grid,
    priority_badge,
    sentiment_badge,
    badge,
    esc,
)

st.set_page_config(page_title="Nuevo reclamo", page_icon="📝", layout="wide")
load_styles()
init_db()


def correo_valido(valor):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", valor.strip()) is not None


def usar_rag_activo(config):
    return bool(config and int(config.get("usar_rag", 1)) == 1)


st.title("Registro de nuevo reclamo")
st.markdown(
    '<div class="page-subtitle">Punto de entrada para guardar un caso o iniciar el análisis inteligente.</div>',
    unsafe_allow_html=True,
)
hero(
    "Crear caso de atención",
    "Ahora puedes guardar el reclamo como Nuevo o analizarlo inmediatamente con IA para generar una respuesta sugerida.",
)

with st.form("form_nuevo_reclamo", clear_on_submit=False):
    st.markdown("### 1. Información del cliente")
    c1, c2, c3 = st.columns([1.2, 1.2, 0.8])
    nombre = c1.text_input("Nombre completo", placeholder="Ej. Andrea López")
    correo = c2.text_input("Correo electrónico", placeholder="cliente@email.com")
    telefono = c3.text_input("Teléfono opcional", placeholder="999 999 999")

    st.markdown("### 2. Información del pedido")
    p1, p2, p3 = st.columns(3)
    codigo_pedido = p1.text_input("Código de pedido", placeholder="ORD-2026-001")
    canal_venta = p2.selectbox("Canal de atención", ["App móvil", "Web", "WhatsApp", "Marketplace", "Otro"])
    fecha_pedido = p3.date_input("Fecha del pedido")

    st.markdown("### 3. Descripción del reclamo")
    descripcion = st.text_area(
        "Detalle del problema",
        height=175,
        placeholder="Ejemplo: Mi pedido llegó tarde, la comida estaba fría y solicito un reembolso.",
    )

    st.markdown("### 4. Acción")
    a1, a2 = st.columns(2)
    guardar_sin_analizar = a1.form_submit_button("Guardar reclamo sin analizar")
    guardar_y_analizar = a2.form_submit_button("Guardar y analizar con IA", type="primary")

if guardar_sin_analizar or guardar_y_analizar:
    errores = []
    if not nombre.strip():
        errores.append("Debe ingresar el nombre del cliente.")
    if not correo.strip():
        errores.append("Debe ingresar el correo del cliente.")
    elif not correo_valido(correo):
        errores.append("El correo ingresado no tiene un formato válido.")
    if not codigo_pedido.strip():
        errores.append("Debe ingresar el código de pedido.")
    if not descripcion.strip() or len(descripcion.strip()) < 15:
        errores.append("La descripción debe tener mayor detalle para registrar el reclamo.")

    if errores:
        for e in errores:
            alert(e, "error")
    else:
        try:
            id_cliente = crear_cliente(nombre, correo, telefono)
            id_reclamo = crear_reclamo(id_cliente, codigo_pedido, canal_venta, fecha_pedido, descripcion)

            if guardar_sin_analizar:
                alert(
                    "Reclamo guardado correctamente en estado Nuevo. Puedes analizarlo luego desde Historial.",
                    "success",
                )
                st.markdown(
                    f"""
                    <div class="panel">
                        <div class="panel-title">Caso registrado</div>
                        <p><b>Cliente:</b> {esc(nombre)}</p>
                        <p><b>Pedido:</b> {esc(codigo_pedido)}</p>
                        <p><b>Estado:</b> Nuevo</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            if guardar_y_analizar:
                analisis = clasificar_reclamo(descripcion)
                guardar_analisis(id_reclamo, analisis)

                config = get_configuracion_activa()
                documentos = []
                if usar_rag_activo(config):
                    max_docs = int(config["max_documentos_recuperados"]) if config else 3
                    documentos = recuperar_documentos(descripcion, analisis["categoria"], max_docs=max_docs)
                    respuesta = generar_respuesta_sugerida(nombre, codigo_pedido, descripcion, analisis, documentos)
                    accion_respuesta = "Generación de respuesta con RAG"
                else:
                    respuesta = generar_respuesta_basica(nombre, codigo_pedido, descripcion, analisis)
                    accion_respuesta = "Generación de respuesta sin RAG"

                guardar_respuesta(id_reclamo, respuesta, documentos, accion=accion_respuesta)

                alert("Reclamo registrado, analizado y guardado correctamente.", "success")

                st.markdown("## Resultado del análisis IA")
                analysis_grid(
                    [
                        ("Categoría detectada", analisis["categoria"]),
                        ("Prioridad asignada", analisis["prioridad"]),
                        ("Confianza", f"{analisis['confianza'] * 100:.0f}%"),
                        ("Sentimiento", analisis["sentimiento"]),
                    ]
                )

                st.markdown(
                    f"""
                    <div class="panel">
                        <div class="panel-title">Ficha de análisis del reclamo</div>
                        {priority_badge(analisis['prioridad'])}
                        {badge(analisis['categoria'], 'info')}
                        {sentiment_badge(analisis['sentimiento'])}
                        <p><b>Palabras clave:</b> {esc(", ".join(analisis["palabras_clave"]) or "No detectadas")}</p>
                        <p><b>Entidades detectadas:</b> {esc(", ".join(analisis["entidades"]) or "No detectadas")}</p>
                        <p><b>Recomendación:</b> {esc(analisis["recomendacion"])}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                docs_html = "".join(
                    f"""
                    <div class="doc-card">
                        <div class="doc-title">{esc(doc['titulo'])}</div>
                        {badge(doc['tipo_documento'], 'info')}
                        <span class="muted">Score: {esc(doc['score'])}</span>
                        <p>{esc(doc['contenido'])}</p>
                    </div>
                    """
                    for doc in documentos
                ) or "<p>Respuesta generada sin RAG. No se consultaron documentos internos.</p>"

                st.markdown("## Panel de respuesta sugerida")
                st.markdown(
                    f"""
                    <div class="response-panel">
                        <div class="panel">
                            <div class="panel-title">Resumen del caso</div>
                            <p><b>Cliente:</b> {esc(nombre)}</p>
                            <p><b>Pedido:</b> {esc(codigo_pedido)}</p>
                            <p><b>Canal:</b> {esc(canal_venta)}</p>
                            {priority_badge(analisis['prioridad'])}
                        </div>
                        <div class="response-box">{esc(respuesta)}</div>
                        <div class="panel">
                            <div class="panel-title">Documentos usados</div>
                            {docs_html}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        except Exception as exc:
            alert(f"No se pudo completar la operación: {exc}", "error")
