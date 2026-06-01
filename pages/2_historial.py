import streamlit as st
import pandas as pd

from database.db_connection import init_db
from database.repositories import (
    listar_reclamos,
    obtener_detalle_reclamo,
    actualizar_estado_reclamo,
    guardar_analisis,
    guardar_respuesta,
    get_configuracion_activa,
    actualizar_respuesta_final,
    aprobar_respuesta,
    marcar_respondido,
    escalar_reclamo,
    asignar_responsable,
    cerrar_reclamo,
    crear_comentario_agente,
    listar_comentarios_agente,
    crear_evaluacion_respuesta,
    listar_evaluaciones_respuesta,
)
from modules.classifier import clasificar_reclamo
from modules.rag_engine import recuperar_documentos, generar_respuesta_sugerida, generar_respuesta_basica
from assets.styles import (
    load_styles,
    hero,
    alert,
    priority_badge,
    status_badge,
    sentiment_badge,
    badge,
    esc,
)

st.set_page_config(page_title="Historial de reclamos", page_icon="📋", layout="wide")
load_styles()
init_db()


def usar_rag_activo(config):
    return bool(config and int(config.get("usar_rag", 1)) == 1)


def preparar_respuesta(reclamo, analisis_dict):
    config = get_configuracion_activa()
    documentos = []
    if usar_rag_activo(config):
        max_docs = int(config["max_documentos_recuperados"]) if config else 3
        documentos = recuperar_documentos(reclamo["descripcion"], analisis_dict["categoria"], max_docs=max_docs)
        respuesta = generar_respuesta_sugerida(
            reclamo["cliente"],
            reclamo["codigo_pedido"],
            reclamo["descripcion"],
            analisis_dict,
            documentos,
        )
        accion = "Generación de respuesta con RAG"
    else:
        respuesta = generar_respuesta_basica(
            reclamo["cliente"],
            reclamo["codigo_pedido"],
            reclamo["descripcion"],
            analisis_dict,
        )
        accion = "Generación de respuesta sin RAG"
    return respuesta, documentos, accion


def analisis_db_a_dict(analisis, reclamo):
    return {
        "categoria": analisis["categoria_detectada"],
        "prioridad": reclamo["prioridad"],
        "confianza": analisis["confianza"],
        "sentimiento": analisis["sentimiento"],
        "palabras_clave": analisis["palabras_clave"].split(", ") if analisis["palabras_clave"] else [],
        "entidades": analisis["entidades_detectadas"].split(", ") if analisis["entidades_detectadas"] else [],
        "recomendacion": analisis["recomendacion"],
    }


st.title("Historial de reclamos")
st.markdown(
    '<div class="page-subtitle">Gestión de casos, acciones del agente y trazabilidad de cambios.</div>',
    unsafe_allow_html=True,
)
hero(
    "Bandeja operativa de atención",
    "Desde esta vista puedes analizar reclamos, regenerar respuestas, aprobarlas, marcarlas como respondidas, escalarlas y revisar el historial de estados.",
)

df = pd.DataFrame(listar_reclamos())
if df.empty:
    st.info("Aún no existen reclamos registrados.")
    st.stop()

st.markdown("### Filtros")
f1, f2, f3, f4 = st.columns([1, 1, 1, 1.2])
categoria = f1.selectbox("Categoría", ["Todas"] + sorted(df["categoria"].dropna().unique().tolist()))
prioridad = f2.selectbox("Prioridad", ["Todas"] + sorted(df["prioridad"].dropna().unique().tolist()))
estado = f3.selectbox("Estado", ["Todos"] + sorted(df["estado"].dropna().unique().tolist()))
busqueda = f4.text_input("Buscar por cliente, código o pedido")

filtrado = df.copy()
if categoria != "Todas":
    filtrado = filtrado[filtrado["categoria"] == categoria]
if prioridad != "Todas":
    filtrado = filtrado[filtrado["prioridad"] == prioridad]
if estado != "Todos":
    filtrado = filtrado[filtrado["estado"] == estado]
if busqueda.strip():
    term = busqueda.lower().strip()
    filtrado = filtrado[
        filtrado["cliente"].str.lower().str.contains(term, na=False)
        | filtrado["codigo_reclamo"].str.lower().str.contains(term, na=False)
        | filtrado["codigo_pedido"].str.lower().str.contains(term, na=False)
    ]

st.dataframe(
    filtrado[
        [
            "id_reclamo",
            "codigo_reclamo",
            "cliente",
            "codigo_pedido",
            "categoria",
            "prioridad",
            "estado",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
    ],
    use_container_width=True,
    hide_index=True,
)

if filtrado.empty:
    st.warning("No hay reclamos que coincidan con los filtros seleccionados.")
    st.stop()

st.markdown("## Detalle del caso")
id_reclamo = st.selectbox("Seleccione un reclamo", filtrado["id_reclamo"].tolist())
reclamo, analisis, respuesta, documentos, historial = obtener_detalle_reclamo(id_reclamo)
comentarios = listar_comentarios_agente(id_reclamo)
evaluaciones = listar_evaluaciones_respuesta(respuesta["id_respuesta"]) if respuesta else []

st.markdown(
    f"""
    <div class="panel">
        <div class="panel-title">{esc(reclamo['codigo_reclamo'])} · {esc(reclamo['cliente'])}</div>
        {priority_badge(reclamo['prioridad'])} {status_badge(reclamo['estado'])}
        <p><b>Correo:</b> {esc(reclamo['correo_cliente'])}<br>
        <b>Pedido:</b> {esc(reclamo['codigo_pedido'])}<br>
        <b>Canal:</b> {esc(reclamo['canal_venta'])}<br>
        <b>Fecha de pedido:</b> {esc(reclamo['fecha_pedido'])}<br>
        <b>Fecha de registro:</b> {esc(reclamo['fecha_creacion'])}<br>
        <b>Última actualización:</b> {esc(reclamo['fecha_actualizacion'])}<br>
        <b>Responsable:</b> {esc(reclamo.get('responsable_asignado') or 'Sin asignar')}<br>
        <b>Fecha de cierre:</b> {esc(reclamo.get('fecha_cierre') or 'Pendiente')}<br>
        <b>Tiempo de atención:</b> {esc(str(reclamo.get('tiempo_atencion_minutos') or 'Pendiente'))} min</p>
        <p><b>Descripción original:</b><br>{esc(reclamo['descripcion'])}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("## Acciones del agente")
a1, a2, a3, a4, a5 = st.columns(5)

if a1.button("Analizar con IA", type="primary"):
    try:
        nuevo_analisis = clasificar_reclamo(reclamo["descripcion"])
        guardar_analisis(id_reclamo, nuevo_analisis)
        nueva_respuesta, nuevos_docs, accion = preparar_respuesta(reclamo, nuevo_analisis)
        guardar_respuesta(id_reclamo, nueva_respuesta, nuevos_docs, accion=accion)
        alert("El reclamo fue analizado con IA y se generó una respuesta sugerida.", "success")
        st.rerun()
    except Exception as exc:
        alert(f"No se pudo analizar el reclamo: {exc}", "error")

if a2.button("Regenerar respuesta"):
    if not analisis:
        alert("Primero debes analizar el reclamo con IA.", "warn")
    else:
        try:
            nueva, docs, accion = preparar_respuesta(reclamo, analisis_db_a_dict(analisis, reclamo))
            guardar_respuesta(id_reclamo, nueva, docs, accion=accion.replace("Generación", "Regeneración"))
            alert("Respuesta sugerida regenerada correctamente.", "success")
            st.rerun()
        except Exception as exc:
            alert(f"No se pudo regenerar la respuesta: {exc}", "error")

if a3.button("Marcar respondido"):
    try:
        marcar_respondido(id_reclamo)
        alert("El reclamo fue marcado como Respondido.", "success")
        st.rerun()
    except Exception as exc:
        alert(f"No se pudo marcar el reclamo como respondido: {exc}", "error")

if a4.button("Escalar reclamo"):
    try:
        escalar_reclamo(id_reclamo)
        alert("El reclamo fue escalado para revisión superior.", "warn")
        st.rerun()
    except Exception as exc:
        alert(f"No se pudo escalar el reclamo: {exc}", "error")

if a5.button("Cerrar reclamo"):
    try:
        cerrar_reclamo(id_reclamo, "Cerrado", "Cierre realizado desde la bandeja operativa.")
        alert("El reclamo fue cerrado y se calculó el tiempo de atención.", "success")
        st.rerun()
    except Exception as exc:
        alert(f"No se pudo cerrar el reclamo: {exc}", "error")

if analisis:
    st.markdown("### Ficha de análisis IA")
    st.markdown(
        f"""
        <div class="panel">
            {badge(analisis['categoria_detectada'], 'info')}
            {priority_badge(reclamo['prioridad'])}
            {sentiment_badge(analisis['sentimiento'])}
            <p><b>Confianza:</b> {analisis['confianza'] * 100:.0f}%</p>
            <p><b>Palabras clave:</b> {esc(analisis['palabras_clave'])}</p>
            <p><b>Entidades detectadas:</b> {esc(analisis['entidades_detectadas'])}</p>
            <p><b>Recomendación:</b> {esc(analisis['recomendacion'])}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
else:
    alert("Este reclamo todavía no tiene análisis IA. Usa el botón Analizar con IA.", "warn")

st.markdown("### Respuesta sugerida y edición final")
if respuesta:
    texto_base = respuesta["respuesta_final"] if respuesta["respuesta_final"] else respuesta["respuesta_generada"]
    respuesta_editada = st.text_area("Editar respuesta final", value=texto_base, height=240)

    r1, r2 = st.columns(2)
    if r1.button("Guardar edición de respuesta"):
        if not respuesta_editada.strip():
            alert("La respuesta final no puede quedar vacía.", "warn")
        else:
            try:
                actualizar_respuesta_final(respuesta["id_respuesta"], respuesta_editada, "EDITADA")
                alert("Respuesta final editada y guardada correctamente.", "success")
                st.rerun()
            except Exception as exc:
                alert(f"No se pudo guardar la respuesta editada: {exc}", "error")

    if r2.button("Aprobar respuesta"):
        if not respuesta_editada.strip():
            alert("La respuesta final no puede aprobarse vacía.", "warn")
        else:
            try:
                aprobar_respuesta(respuesta["id_respuesta"], respuesta_editada)
                alert("Respuesta aprobada correctamente.", "success")
                st.rerun()
            except Exception as exc:
                alert(f"No se pudo aprobar la respuesta: {exc}", "error")

    st.markdown("#### Vista de respuesta")
    st.markdown(f'<div class="response-box">{esc(texto_base)}</div>', unsafe_allow_html=True)
else:
    alert("Todavía no existe una respuesta sugerida. Analiza el reclamo o regenera una respuesta.", "warn")

st.markdown("### Documentos consultados")
if documentos:
    for doc in documentos:
        st.markdown(
            f"""
            <div class="doc-card">
                <div class="doc-title">{esc(doc['titulo'])}</div>
                {badge(doc['tipo_documento'], 'info')}
                <span class="muted">Score: {esc(doc['score_similitud'])}</span>
                <p>{esc(doc['fragmento_usado'])}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
elif respuesta:
    st.info("Esta respuesta fue generada sin RAG o no registró documentos consultados.")
else:
    st.info("Aún no hay documentos consultados para este reclamo.")

st.markdown("### Responsable y comentarios internos")
r1, r2 = st.columns([1, 2])
responsable_nuevo = r1.text_input("Responsable asignado", value=reclamo.get("responsable_asignado") or "Agente de soporte")
if r1.button("Asignar responsable"):
    if not responsable_nuevo.strip():
        alert("Ingrese un responsable antes de guardar.", "warn")
    else:
        try:
            asignar_responsable(id_reclamo, responsable_nuevo)
            alert("Responsable asignado correctamente.", "success")
            st.rerun()
        except Exception as exc:
            alert(f"No se pudo asignar responsable: {exc}", "error")

tipo_comentario = r2.selectbox("Tipo de comentario", ["INTERNO", "SEGUIMIENTO", "ESCALAMIENTO", "CIERRE"])
comentario = st.text_area("Agregar comentario interno", height=90, placeholder="Ej. Se validó evidencia del cliente y se deriva a supervisor.")
if st.button("Guardar comentario"):
    if comentario.strip():
        try:
            crear_comentario_agente(id_reclamo, comentario, tipo_comentario)
            alert("Comentario registrado correctamente.", "success")
            st.rerun()
        except Exception as exc:
            alert(f"No se pudo guardar el comentario: {exc}", "error")
    else:
        alert("Ingrese un comentario antes de guardar.", "warn")

if comentarios:
    st.markdown("#### Comentarios registrados")
    for c in comentarios:
        st.markdown(
            f"""
            <div class="case-card">
                <div class="case-title">{esc(c['tipo_comentario'])} · {esc(c['usuario_responsable'])}</div>
                <div class="muted">{esc(c['fecha_comentario'])}</div>
                <p>{esc(c['comentario'])}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

if respuesta:
    st.markdown("### Evaluación de calidad de respuesta")
    ev1, ev2, ev3, ev4 = st.columns(4)
    claridad = ev1.slider("Claridad", 1, 5, 4)
    utilidad = ev2.slider("Utilidad", 1, 5, 4)
    tono = ev3.slider("Tono", 1, 5, 4)
    fundamentacion = ev4.slider("Fundamentación", 1, 5, 4)
    requiere_mejora = st.checkbox("Requiere mejora")
    obs_eval = st.text_input("Observación de evaluación", placeholder="Ej. Respuesta clara, pero requiere mayor sustento documental.")
    if st.button("Guardar evaluación"):
        try:
            crear_evaluacion_respuesta(
                respuesta["id_respuesta"],
                claridad,
                utilidad,
                tono,
                fundamentacion,
                requiere_mejora,
                obs_eval,
            )
            alert("Evaluación de respuesta registrada correctamente.", "success")
            st.rerun()
        except Exception as exc:
            alert(f"No se pudo guardar la evaluación: {exc}", "error")

    if evaluaciones:
        st.markdown("#### Evaluaciones registradas")
        for ev in evaluaciones:
            st.markdown(
                f"""
                <div class="case-card">
                    <div class="case-title">Evaluación · {esc(ev['usuario_evaluador'])}</div>
                    <div class="muted">{esc(ev['fecha_evaluacion'])}</div>
                    <p>
                    Claridad: {esc(ev['claridad'])}/5 · Utilidad: {esc(ev['utilidad'])}/5 ·
                    Tono: {esc(ev['tono'])}/5 · Fundamentación: {esc(ev['fundamentacion'])}/5
                    </p>
                    <p>{esc(ev['observacion'] or '')}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )

st.markdown("### Cambio manual de estado")
c1, c2 = st.columns([1, 2])
nuevo_estado = c1.selectbox("Nuevo estado", ["Nuevo", "Analizado por IA", "En revisión", "Respondido", "Escalado", "Cerrado"])
comentario_estado = c2.text_input("Comentario del cambio", placeholder="Ej. Validado por agente de soporte")
if st.button("Guardar cambio de estado"):
    try:
        actualizar_estado_reclamo(id_reclamo, nuevo_estado, "Cambio manual de estado", comentario_estado)
        alert("Estado actualizado correctamente.", "success")
        st.rerun()
    except Exception as exc:
        alert(f"No se pudo actualizar el estado: {exc}", "error")

st.markdown("## Historial de cambios de estado")
if historial:
    for h in historial:
        st.markdown(
            f"""
            <div class="case-card">
                <div class="case-title">{esc(h['accion'])}</div>
                {status_badge(h['estado_nuevo'])}
                <div class="muted">
                    Anterior: {esc(h['estado_anterior'] or 'Sin estado anterior')} · Nuevo: {esc(h['estado_nuevo'])}<br>
                    Usuario: {esc(h['usuario_responsable'])} · Fecha: {esc(h['fecha_cambio'])}
                </div>
                <p>{esc(h['comentario'] or '')}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
else:
    st.info("Este reclamo aún no tiene historial registrado.")
