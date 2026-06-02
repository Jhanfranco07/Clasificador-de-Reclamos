from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.db_connection import fetch_all, fetch_one, init_db
from database.repositories import (
    actualizar_configuracion,
    actualizar_estado_reclamo,
    actualizar_respuesta_final,
    aprobar_respuesta,
    cerrar_reclamo,
    crear_cliente,
    crear_reclamo,
    escalar_reclamo,
    get_configuracion_activa,
    guardar_analisis,
    guardar_respuesta,
    listar_documentos,
    listar_reclamos,
    marcar_respondido,
    obtener_detalle_reclamo,
)
from modules.classifier import clasificar_reclamo
from modules.metrics import (
    confianza_por_categoria,
    obtener_metricas_dashboard,
    reclamos_por_categoria,
    reclamos_por_estado,
    reclamos_por_prioridad,
    respuestas_por_estado_revision,
    tiempo_promedio_por_categoria,
)
from modules.rag_engine import (
    construir_indice_vectorial,
    generar_respuesta_basica,
    generar_respuesta_sugerida,
    obtener_resumen_indice,
    recuperar_documentos,
)


app = FastAPI(
    title="SmartClaim AI API",
    version="1.0.0",
    description="API full stack para clasificacion, RAG y gestion de reclamos.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ClaimCreate(BaseModel):
    customer_name: str = Field(..., min_length=2)
    customer_email: EmailStr
    customer_phone: str | None = None
    order_code: str = Field(..., min_length=2)
    channel: str = "WEB"
    order_date: str | None = None
    description: str = Field(..., min_length=10)
    responsible: str = "Agente de soporte"
    analyze: bool = True


class ResponseUpdate(BaseModel):
    response_text: str = Field(..., min_length=5)


class StateUpdate(BaseModel):
    state: str
    comment: str | None = None


class ConfigUpdate(BaseModel):
    confidence_threshold: float = Field(..., ge=0, le=1)
    human_review_required: bool
    use_rag: bool
    max_documents: int = Field(..., ge=1, le=10)


STATUS_TO_UI = {
    "Nuevo": "RECEIVED",
    "Analizado por IA": "ANALYZING",
    "En revision": "IN_REVIEW",
    "En revisión": "IN_REVIEW",
    "Respondido": "RESPONDED",
    "Escalado": "ESCALATED",
    "Cerrado": "CLOSED",
}

UI_TO_STATUS = {
    "RECEIVED": "Nuevo",
    "ANALYZING": "Analizado por IA",
    "IN_REVIEW": "En revisión",
    "RESPONDED": "Respondido",
    "ESCALATED": "Escalado",
    "CLOSED": "Cerrado",
}

CATEGORY_TO_UI = {
    "Cobro indebido": "INCORRECT_CHARGE",
    "Retraso de pedido": "DELAY",
    "Producto incorrecto": "WRONG_PRODUCT",
    "Producto incompleto": "WRONG_PRODUCT",
    "Problema con tarjeta": "CARD_ISSUE",
    "Fraude o seguridad": "FRAUD",
    "Soporte general": "GENERAL_SUPPORT",
    "Sin clasificar": "GENERAL_SUPPORT",
}

PRIORITY_TO_UI = {
    "Baja": "LOW",
    "Media": "MEDIUM",
    "Alta": "HIGH",
    "Crítica": "CRITICAL",
    "Critica": "CRITICAL",
    "Sin prioridad": "LOW",
}

SENTIMENT_TO_UI = {
    "POSITIVO": "POSITIVE",
    "NEUTRO": "NEUTRAL",
    "NEGATIVO": "NEGATIVE",
}


@app.on_event("startup")
def startup() -> None:
    init_db()


def _config() -> dict[str, Any]:
    row = get_configuracion_activa()
    return row or {
        "modelo_base": "modelo_ml_tfidf_logistic_regression",
        "umbral_confianza": 0.85,
        "revision_humana_obligatoria": 1,
        "usar_rag": 1,
        "max_documentos_recuperados": 3,
    }


def _to_claim_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id_reclamo"]),
        "code": row["codigo_reclamo"],
        "customerName": row.get("cliente"),
        "customerEmail": row.get("correo"),
        "orderCode": row.get("codigo_pedido"),
        "channel": row.get("canal_venta") or "WEB",
        "category": row.get("categoria") or "Sin clasificar",
        "categoryKey": CATEGORY_TO_UI.get(row.get("categoria"), "GENERAL_SUPPORT"),
        "priority": row.get("prioridad") or "Sin prioridad",
        "priorityKey": PRIORITY_TO_UI.get(row.get("prioridad"), "LOW"),
        "status": row.get("estado") or "Nuevo",
        "statusKey": STATUS_TO_UI.get(row.get("estado"), "RECEIVED"),
        "requiresHumanReview": bool(row.get("requiere_revision_humana")),
        "createdAt": row.get("fecha_creacion"),
        "updatedAt": row.get("fecha_actualizacion"),
    }


def _to_claim_detail(id_reclamo: int) -> dict[str, Any]:
    reclamo, analisis, respuesta, documentos, historial = obtener_detalle_reclamo(id_reclamo)
    if not reclamo:
        raise HTTPException(status_code=404, detail="Reclamo no encontrado")

    return {
        "claim": {
            "id": str(reclamo["id_reclamo"]),
            "code": reclamo["codigo_reclamo"],
            "customerName": reclamo["cliente"],
            "customerEmail": reclamo["correo_cliente"],
            "orderCode": reclamo["codigo_pedido"],
            "channel": reclamo["canal_venta"],
            "orderDate": reclamo.get("fecha_pedido"),
            "description": reclamo["descripcion"],
            "category": reclamo.get("categoria"),
            "categoryKey": CATEGORY_TO_UI.get(reclamo.get("categoria"), "GENERAL_SUPPORT"),
            "priority": reclamo.get("prioridad"),
            "priorityKey": PRIORITY_TO_UI.get(reclamo.get("prioridad"), "LOW"),
            "status": reclamo["estado"],
            "statusKey": STATUS_TO_UI.get(reclamo["estado"], "RECEIVED"),
            "responsible": reclamo.get("responsable_asignado"),
            "requiresHumanReview": bool(reclamo.get("requiere_revision_humana")),
            "createdAt": reclamo.get("fecha_creacion"),
            "updatedAt": reclamo.get("fecha_actualizacion"),
            "closedAt": reclamo.get("fecha_cierre"),
            "attentionMinutes": reclamo.get("tiempo_atencion_minutos"),
        },
        "analysis": _to_analysis(analisis) if analisis else None,
        "response": _to_response(respuesta) if respuesta else None,
        "documents": [_to_document_reference(doc) for doc in documentos],
        "history": [_to_history_event(item) for item in historial],
    }


def _to_analysis(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id_analisis"]),
        "category": row.get("categoria_detectada"),
        "categoryKey": CATEGORY_TO_UI.get(row.get("categoria_detectada"), "GENERAL_SUPPORT"),
        "confidence": row.get("confianza") or 0,
        "sentiment": row.get("sentimiento") or "NEUTRO",
        "sentimentKey": SENTIMENT_TO_UI.get(row.get("sentimiento"), "NEUTRAL"),
        "keywords": [p.strip() for p in str(row.get("palabras_clave") or "").split(",") if p.strip()],
        "entities": [p.strip() for p in str(row.get("entidades_detectadas") or "").split(",") if p.strip()],
        "recommendation": row.get("recomendacion"),
        "model": row.get("modelo_usado"),
        "createdAt": row.get("fecha_analisis"),
    }


def _to_response(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id_respuesta"]),
        "suggestedResponse": row.get("respuesta_generada"),
        "editedResponse": row.get("respuesta_editada"),
        "finalResponse": row.get("respuesta_final"),
        "status": row.get("estado_revision"),
        "createdAt": row.get("fecha_generacion"),
        "reviewedAt": row.get("fecha_revision"),
    }


def _to_document_reference(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id_documento")),
        "title": row.get("titulo"),
        "type": row.get("tipo_documento"),
        "category": row.get("categoria_asociada"),
        "score": row.get("score_similitud"),
        "fragment": row.get("fragmento_usado"),
    }


def _to_history_event(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row.get("id_historial")),
        "previousState": row.get("estado_anterior"),
        "newState": row.get("estado_nuevo"),
        "action": row.get("accion"),
        "comment": row.get("comentario"),
        "user": row.get("usuario_responsable"),
        "createdAt": row.get("fecha_cambio"),
    }


def _analyze_and_generate(id_reclamo: int) -> dict[str, Any]:
    reclamo = fetch_one(
        """
        SELECT r.*, c.nombre AS cliente, c.correo AS correo_cliente
        FROM reclamos r
        INNER JOIN clientes c ON c.id_cliente = r.id_cliente
        WHERE r.id_reclamo = ?
        """,
        (id_reclamo,),
    )
    if not reclamo:
        raise HTTPException(status_code=404, detail="Reclamo no encontrado")

    try:
        analisis = clasificar_reclamo(reclamo["descripcion"])
        guardar_analisis(id_reclamo, analisis)

        config = _config()
        documentos = []
        if bool(config.get("usar_rag")):
            documentos = recuperar_documentos(
                reclamo["descripcion"],
                analisis["categoria"],
                int(config.get("max_documentos_recuperados") or 3),
            )
            respuesta = generar_respuesta_sugerida(
                reclamo["cliente"],
                reclamo["codigo_pedido"],
                reclamo["descripcion"],
                analisis,
                documentos,
            )
        else:
            respuesta = generar_respuesta_basica(
                reclamo["cliente"],
                reclamo["codigo_pedido"],
                reclamo["descripcion"],
                analisis,
            )

        guardar_respuesta(id_reclamo, respuesta, documentos)
        return _to_claim_detail(id_reclamo)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo analizar el reclamo: {exc}") from exc


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/dashboard")
def dashboard() -> dict[str, Any]:
    metrics = obtener_metricas_dashboard()
    return {
        "metrics": metrics,
        "byCategory": reclamos_por_categoria(),
        "byPriority": reclamos_por_prioridad(),
        "byStatus": reclamos_por_estado(),
        "recentClaims": [_to_claim_summary(row) for row in listar_reclamos()[:5]],
    }


@app.get("/api/claims")
def claims() -> dict[str, Any]:
    return {"items": [_to_claim_summary(row) for row in listar_reclamos()]}


@app.post("/api/claims", status_code=201)
def create_claim(payload: ClaimCreate) -> dict[str, Any]:
    try:
        id_cliente = crear_cliente(
            payload.customer_name,
            payload.customer_email,
            payload.customer_phone,
        )
        id_reclamo = crear_reclamo(
            id_cliente,
            payload.order_code,
            payload.channel,
            payload.order_date or "",
            payload.description,
            payload.responsible,
        )
        if payload.analyze:
            return _analyze_and_generate(id_reclamo)
        return _to_claim_detail(id_reclamo)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo crear el reclamo: {exc}") from exc


@app.get("/api/claims/{claim_id}")
def claim_detail(claim_id: int) -> dict[str, Any]:
    return _to_claim_detail(claim_id)


@app.post("/api/claims/{claim_id}/analyze")
def analyze_claim(claim_id: int) -> dict[str, Any]:
    return _analyze_and_generate(claim_id)


@app.patch("/api/claims/{claim_id}/state")
def update_claim_state(claim_id: int, payload: StateUpdate) -> dict[str, Any]:
    state = UI_TO_STATUS.get(payload.state, payload.state)
    try:
        if state == "Respondido":
            marcar_respondido(claim_id, payload.comment)
        elif state == "Escalado":
            escalar_reclamo(claim_id, payload.comment)
        elif state == "Cerrado":
            cerrar_reclamo(claim_id, "Cerrado", payload.comment)
        else:
            actualizar_estado_reclamo(claim_id, state, "Actualizacion desde API", payload.comment)
        return _to_claim_detail(claim_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/responses/{response_id}")
def update_response(response_id: int, payload: ResponseUpdate) -> dict[str, Any]:
    actualizar_respuesta_final(response_id, payload.response_text, "EDITADA")
    row = fetch_one("SELECT id_reclamo FROM respuestas_sugeridas WHERE id_respuesta = ?", (response_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Respuesta no encontrada")
    return _to_claim_detail(row["id_reclamo"])


@app.post("/api/responses/{response_id}/approve")
def approve_response(response_id: int, payload: ResponseUpdate | None = None) -> dict[str, Any]:
    aprobar_respuesta(response_id, payload.response_text if payload else None)
    row = fetch_one("SELECT id_reclamo FROM respuestas_sugeridas WHERE id_respuesta = ?", (response_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Respuesta no encontrada")
    marcar_respondido(row["id_reclamo"], "Respuesta aprobada desde el panel full stack.")
    return _to_claim_detail(row["id_reclamo"])


@app.get("/api/documents")
def documents() -> dict[str, Any]:
    docs = [
        {
            "id": str(doc["id_documento"]),
            "title": doc["titulo"],
            "type": doc["tipo_documento"],
            "category": doc["categoria_asociada"],
            "content": doc["contenido"],
            "indexStatus": doc["estado_indexacion"],
            "updatedAt": doc["fecha_actualizacion"],
        }
        for doc in listar_documentos()
    ]
    return {"items": docs, "index": obtener_resumen_indice()}


@app.post("/api/documents/reindex")
def reindex_documents() -> dict[str, Any]:
    return construir_indice_vectorial(forzar=True)


@app.get("/api/config")
def get_config() -> dict[str, Any]:
    config = _config()
    return {
        "model": config.get("modelo_base"),
        "confidenceThreshold": float(config.get("umbral_confianza") or 0.85),
        "humanReviewRequired": bool(config.get("revision_humana_obligatoria")),
        "useRag": bool(config.get("usar_rag")),
        "maxDocuments": int(config.get("max_documentos_recuperados") or 3),
        "updatedAt": config.get("fecha_actualizacion"),
    }


@app.put("/api/config")
def put_config(payload: ConfigUpdate) -> dict[str, Any]:
    actualizar_configuracion(
        payload.confidence_threshold,
        payload.human_review_required,
        payload.use_rag,
        payload.max_documents,
    )
    return get_config()


@app.get("/api/reports")
def reports() -> dict[str, Any]:
    return {
        "metrics": obtener_metricas_dashboard(),
        "byCategory": reclamos_por_categoria(),
        "byPriority": reclamos_por_prioridad(),
        "byStatus": reclamos_por_estado(),
        "confidenceByCategory": confianza_por_categoria(),
        "responsesByReviewStatus": respuestas_por_estado_revision(),
        "attentionTimeByCategory": tiempo_promedio_por_categoria(),
    }
