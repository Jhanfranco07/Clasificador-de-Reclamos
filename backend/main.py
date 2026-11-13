from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from starlette.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.db_connection import (allows_automatic_database_setup, ensure_hosted_postgres_identity,
                                    ensure_pgvector_embedding_dimension,
                                    fetch_all, fetch_one, init_db, using_postgres)
from database.repositories import (
    DuplicateDocument,
    get_categoria_id,
    actualizar_configuracion,
    actualizar_perfil_usuario,
    actualizar_documento_base,
    actualizar_estado_reclamo,
    actualizar_respuesta_final,
    asegurar_pedidos_demo_base,
    asegurar_usuarios_auth_base,
    aprobar_respuesta,
    cerrar_reclamo,
    crear_comentario_agente,
    crear_documento_base,
    crear_notificacion,
    crear_pedido_cliente,
    crear_reclamo,
    crear_mensaje_reclamo,
    registrar_cliente_publico,
    desactivar_documento_base,
    escalar_reclamo,
    get_configuracion_activa,
    guardar_analisis,
    guardar_respuesta,
    listar_catalogo,
    listar_comentarios_agente,
    listar_pedidos_por_correo,
    listar_documentos,
    listar_notificaciones,
    listar_mensajes_reclamo,
    listar_reclamos,
    listar_reclamos_por_correo,
    marcar_notificaciones_leidas,
    marcar_respondido,
    obtener_pedido,
    obtener_detalle_reclamo,
    obtener_usuario_auth_por_correo,
    obtener_usuario_auth_por_id,
    reabrir_reclamo,
)
from modules.classifier import clasificar_reclamo
from modules.metrics import (
    confianza_por_categoria,
    obtener_metricas_dashboard,
    reclamos_por_categoria,
    reclamos_por_estado,
    reclamos_por_prioridad,
    respuestas_por_estado_revision,
    evolucion_reclamos_por_fecha,
    tiempo_primera_respuesta_por_categoria,
    tiempo_promedio_por_categoria,
)
from modules.rag_engine import (
    construir_indice_vectorial,
    generar_respuesta_basica,
    generar_respuesta_sugerida,
    obtener_resumen_indice,
    recuperar_documentos,
)
from modules.pdf_documents import PDF_MAX_BYTES, PDF_MAX_TEXT, extract_pdf_text
from modules.security import create_token, decode_token, hash_password, verify_password
from modules.chatbot_service import answer_chat
from modules.config import allow_vercel_previews, cors_origins, is_production, validate_runtime_config
from modules.ai_trace import AITrace, trace_update, trace_append
from modules.domain_errors import DomainError


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_runtime_config()
    if is_production():
        ensure_hosted_postgres_identity()
    if os.getenv("SMARTCLAIM_BOOTSTRAP_DEMO") == "1":
        if using_postgres() or not allows_automatic_database_setup():
            raise RuntimeError("Bootstrap demo permitido solamente en SQLite de desarrollo")
        init_db()
        asegurar_usuarios_auth_base()
        asegurar_pedidos_demo_base()
        construir_indice_vectorial(forzar=True)
    elif using_postgres():
        ensure_pgvector_embedding_dimension()
    yield


app = FastAPI(
    title="SmartClaim AI API",
    version="1.0.0",
    description="API full stack para clasificacion, RAG y gestion de reclamos.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins(),
    allow_origin_regex=r"https://.*\.vercel\.app" if allow_vercel_previews() else None,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def domain_error_handler(request, exc):
    return JSONResponse(status_code=exc.status_code, content={"detail": str(exc)})


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1)


class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2)
    email: EmailStr
    phone: str | None = None
    password: str = Field(..., min_length=6)


class PasswordResetRequest(BaseModel):
    email: EmailStr


class ProfileUpdate(BaseModel):
    name: str = Field(..., min_length=2, max_length=120)
    phone: str | None = Field(default=None, max_length=30)


class OrderItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    product_id: int = Field(..., gt=0, strict=True)
    quantity: int = Field(..., ge=1, le=2147483647, strict=True)


class OrderQuote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: list[OrderItemCreate] = Field(..., min_length=1)


class OrderCreate(OrderQuote):
    request_id: str | None = Field(None, min_length=8, max_length=100)
    quote_hash: str = Field(..., min_length=64, max_length=64)
    payment_method: Literal['Tarjeta', 'Yape', 'Plin', 'Efectivo']
    delivery_address: str = Field(..., min_length=5, max_length=500)
    delivery_notes: str | None = Field(default=None, max_length=500)

    @field_validator('delivery_address', 'delivery_notes', mode='before')
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value


class OperationalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    request_id: str = Field(..., min_length=8, max_length=100)


class OrderTransition(OperationalRequest):
    state: str
    expected_version: int = Field(..., ge=0, strict=True)
    reason: str | None = Field(None, max_length=1000)


class CourierAssignment(OperationalRequest):
    courier_id: int = Field(..., gt=0, strict=True)
    expected_version: int = Field(..., ge=0, strict=True)
    reason: str = Field(..., min_length=1, max_length=1000)


class DelayReport(OperationalRequest):
    expected_version: int = Field(..., ge=0, strict=True)
    reason: str = Field(..., min_length=1, max_length=1000)


class UserRoleUpdate(OperationalRequest):
    role: Literal['CLIENT', 'AGENT', 'ADMIN', 'MERCHANT', 'COURIER']
    active: bool
    reason: str = Field(..., min_length=1, max_length=1000)


class OperatorGrant(OperationalRequest):
    user_id: int = Field(..., gt=0, strict=True)
    active: bool
    edit_products: bool = False
    reason: str = Field(..., min_length=1, max_length=1000)


class CourierAvailability(OperationalRequest):
    available: bool


class ProductUpdate(OperationalRequest):
    name: str = Field(..., min_length=1, max_length=150)
    price: float = Field(..., ge=0, allow_inf_nan=False)
    available: bool


class RestaurantUpdate(OperationalRequest):
    address: str = Field(..., min_length=1, max_length=500)
    responsible: str = Field(..., min_length=1, max_length=150)
    active: bool


class ClaimCreate(BaseModel):
    request_id: str | None = Field(None, min_length=8, max_length=100)
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
    request_id: str | None = Field(None, min_length=8, max_length=100)
    expected_version: int | None = Field(None, ge=0, strict=True)


class CloseRequest(BaseModel):
    request_id: str | None = Field(None, min_length=8, max_length=100)
    comment: str = Field(..., min_length=1, max_length=2000)

    @field_validator('comment')
    @classmethod
    def nonempty_comment(cls, value):
        if not value.strip():
            raise ValueError('Indica un motivo de cierre administrativo')
        return value.strip()


class ConfigUpdate(BaseModel):
    config_id: int = Field(..., gt=0, strict=True)
    confidence_threshold: float = Field(..., ge=0, le=1)
    human_review_required: bool
    use_rag: bool
    max_documents: int = Field(..., ge=1, le=10, strict=True)


class DocumentPayload(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(..., min_length=3, max_length=250)
    type: str = Field(..., pattern="^(POLITICA|FAQ|PROCEDIMIENTO|MANUAL)$")
    category: str = Field(..., min_length=3)
    content: str = Field(..., min_length=20, max_length=PDF_MAX_TEXT)


class AgentCommentPayload(BaseModel):
    comment: str = Field(..., min_length=3)
    type: str = Field("INTERNO", pattern="^(INTERNO|SEGUIMIENTO|ESCALAMIENTO|CIERRE)$")


class ClaimMessagePayload(BaseModel):
    message: str = Field(..., min_length=2, max_length=4000)
    request_id: str | None = Field(None, min_length=8, max_length=100)


class ClaimAssignmentPayload(OperationalRequest):
    assignee_id: int = Field(..., gt=0, strict=True)
    expected_version: int = Field(..., ge=0, strict=True)
    reason: str = Field(..., min_length=1, max_length=1000)


class ClaimEscalationPayload(OperationalRequest):
    assignee_id: int | None = Field(None, gt=0, strict=True)
    expected_version: int = Field(..., ge=0, strict=True)
    reason: str = Field(..., min_length=1, max_length=1000)


class ClaimRetryPayload(BaseModel):
    request_id: str | None = Field(None, min_length=8, max_length=100)


class ChatPayload(BaseModel):
    message: str = Field(..., min_length=2, max_length=2000)
    session_id: str | None = None
    context: dict[str, Any] | None = None


STATUS_TO_UI = {
    "Nuevo": "RECEIVED",
    "Analizado por IA": "ANALYZING",
    "En revision": "IN_REVIEW",
    "En revisión": "IN_REVIEW",
    "Respondido": "RESPONDED",
    "Escalado": "ESCALATED",
    "Cerrado": "CLOSED",
}


def _firmar_respuesta_agente(texto: str, nombre_agente: str) -> str:
    """Replace template signatures and guarantee the authenticated agent signs."""
    respuesta = str(texto or "").strip()
    agente = str(nombre_agente or "Agente de soporte").strip()
    firma = f"Saludos cordiales,\n{agente}\nServicio de Atención al Cliente"

    marcador = re.compile(r"\[(?:nombre\s+del\s+agente|nombre\s+agente|agente|nombre)\]", re.IGNORECASE)
    if marcador.search(respuesta):
        return marcador.sub(agente, respuesta)

    if agente.lower() in respuesta.lower():
        return respuesta

    firma_generica = re.compile(
        r"(?is)\n+(?:saludos cordiales|atentamente),?\s*\n+"
        r"(?:equipo de soporte|servicio de atenci[oó]n al cliente|smartclaim ai)\s*$"
    )
    if firma_generica.search(respuesta):
        return firma_generica.sub(f"\n\n{firma}", respuesta)

    return f"{respuesta}\n\n{firma}"

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


def _to_user(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id_auth_user"]),
        "name": row["nombre"],
        "email": row["correo"],
        "phone": row.get("telefono"),
        "role": row["rol"],
        "createdAt": row.get("fecha_creacion"),
    }


def _auth_response(row: dict[str, Any]) -> dict[str, Any]:
    user = _to_user(row)
    token = create_token({
        "sub": user["id"],
        "email": user["email"],
        "role": user["role"],
        "name": user["name"],
    })
    return {"user": user, "token": token}


def get_current_user(authorization: str | None = Header(default=None)) -> dict[str, Any]:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Sesión requerida")
    payload = decode_token(authorization.split(" ", 1)[1].strip())
    if not payload:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    user = obtener_usuario_auth_por_id(payload.get("sub"))
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user


def require_staff(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user["rol"] not in {"AGENT", "ADMIN"}:
        raise HTTPException(status_code=403, detail="No tienes permisos para esta acción")
    return user


def require_admin(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user["rol"] != "ADMIN":
        raise HTTPException(status_code=403, detail="Esta acción requiere permisos de administrador")
    return user


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
        "assignment": _assignment(row),
    }


def _assignment(row):
    identity = fetch_one("SELECT rol,estado FROM auth_users WHERE id_auth_user=?", (row.get("responsable_auth_id"),))
    return {"id": row.get("responsable_auth_id"), "name": row.get("responsable_asignado"),
            "active": bool(identity and identity["estado"] == "ACTIVO" and identity["rol"] in {"AGENT", "ADMIN"}),
            "version": row.get("version_asignacion", 0), "assignedAt": row.get("fecha_asignacion")}


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
            "orderLinkStatus": "LINKED" if reclamo.get("id_pedido") else "LEGACY_UNRESOLVED",
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
            "assignment": _assignment(reclamo),
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


def _detail_for_user(claim_id, user):
    from modules.order_workflow import require_role
    require_role(user, {"CLIENT", "AGENT", "ADMIN"})
    detail = _to_claim_detail(claim_id)
    if user["rol"] != "CLIENT":
        return detail
    if detail["claim"]["customerEmail"].lower() != user["correo"].lower():
        raise HTTPException(status_code=403, detail="No tienes acceso a este reclamo")
    published = fetch_one("""SELECT * FROM respuestas_sugeridas WHERE id_reclamo=?
        AND estado_revision IN ('APROBADA','ENVIADA') AND respuesta_final IS NOT NULL
        ORDER BY id_respuesta DESC LIMIT 1""", (claim_id,))
    detail["analysis"] = None
    detail["claim"].pop("assignment", None)
    detail["documents"] = []
    detail["response"] = ({key: value for key, value in _to_response(published).items()
                           if key not in {"suggestedResponse", "editedResponse"}} if published else None)
    public_history = []
    for event in detail["history"]:
        action = event["action"]
        if action == "Escalamiento asignado":
            action = "Escalamiento de reclamo"
        if action in {"Edición de borrador", "Edición de respuesta"} or action.startswith("Generaci"):
            continue
        public_history.append({"id": event["id"], "newState": event["newState"],
            "action": action if action in {"Registro de reclamo", "Envio de respuesta", "Cierre de reclamo", "Reapertura de reclamo", "Escalamiento de reclamo"}
                      else "Actualización del caso", "createdAt": event["createdAt"]})
    detail["history"] = public_history
    return detail


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
        "actorId": row.get("actor_auth_id"),
        "actorRole": row.get("actor_rol"),
        "createdAt": row.get("fecha_cambio"),
    }


def _to_order(row: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": str(row["id_pedido"]),
        "code": row["codigo_pedido"],
        "userId": str(row["id_cliente"]),
        "storeName": row["tienda_nombre"],
        "storeImage": row.get("tienda_imagen"),
        "status": row["estado"],
        "total": float(row.get("total") or 0),
        "subtotal": row.get("subtotal"),
        "deliveryFee": row.get("costo_delivery"),
        "serviceFee": row.get("costo_servicio"),
        "deliveryNotes": row.get("notas_entrega"),
        "paymentVerified": False,
        "paymentMethod": row.get("metodo_pago"),
        "deliveryAddress": row.get("direccion_entrega"),
        "deliveryDriver": row.get("repartidor"),
        "items": [
            {
                "id": str(item["id_item"]),
                "name": item["nombre_producto"],
                "quantity": int(item["cantidad"]),
                "price": float(item["precio"]),
                "image": item.get("imagen"),
            }
            for item in items
        ],
        "createdAt": row.get("fecha_creacion"),
        "estimatedDelivery": row.get("fecha_entrega_estimada"),
    }


def _to_notification(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id_notificacion"]),
        "claimId": str(row["id_reclamo"]) if row.get("id_reclamo") else None,
        "orderId": str(row["id_pedido"]) if row.get("id_pedido") else None,
        "event": row.get("evento") or "LEGACY",
        "title": row["titulo"],
        "message": row["mensaje"],
        "type": row["tipo"],
        "read": bool(row["leida"]),
        "createdAt": row["fecha_creacion"],
    }


def _to_message(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id_mensaje"]),
        "claimId": str(row["id_reclamo"]),
        "senderType": row["sender_type"],
        "senderId": row.get("sender_id"),
        "message": row["mensaje"],
        "isInternal": bool(row.get("is_internal")),
        "createdAt": row["fecha_creacion"],
        "readAt": row.get("read_at"),
    }


def _to_comment(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id_comentario"]),
        "claimId": str(row["id_reclamo"]),
        "comment": row["comentario"],
        "type": row["tipo_comentario"],
        "user": row["usuario_responsable"],
        "createdAt": row["fecha_comentario"],
    }


def _to_document(doc: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(doc["id_documento"]),
        "title": doc["titulo"],
        "type": doc["tipo_documento"],
        "category": doc["categoria_asociada"],
        "content": doc["contenido"],
        "indexStatus": doc["estado_indexacion"],
        "updatedAt": doc["fecha_actualizacion"],
    }


def _order_detail_or_404(order_id: int, user: dict[str, Any]) -> dict[str, Any]:
    row, items = obtener_pedido(order_id)
    if not row:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    from database.db_connection import get_connection
    from modules.order_workflow import authorize_order, events
    with get_connection() as conn:
        authorize_order(conn, row, user)
    result = _to_order(row, items)
    restaurant = fetch_one("SELECT direccion FROM restaurantes WHERE id_restaurante=?", (row.get("id_restaurante"),))
    assignment = fetch_one("SELECT id_courier FROM pedido_asignaciones WHERE id_pedido=?", (order_id,))
    result.update(restaurantId=row.get("id_restaurante"), version=row["version_operativa"],
                  driverVerified=assignment is not None,
                  pickupAddress=restaurant["direccion"] if restaurant else None,
                  pickedUpAt=row.get("recogido_at"), deliveredAt=row.get("entregado_at"),
                  events=events(order_id, user["rol"] in {"ADMIN", "AGENT"}),
                  reconciliationRequired=row.get("id_restaurante") is None or row["estado"] == "DELAYED")
    if user["rol"] == "COURIER":
        # Courier DTO contains only dispatch context. No finance, customer email or claim drafts.
        result = {key: result[key] for key in ("id", "code", "storeName", "status", "deliveryAddress",
            "deliveryNotes", "version", "pickedUpAt", "deliveredAt", "events", "restaurantId", "createdAt", "pickupAddress")}
    return result


def _pydantic_data(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def _analyze_and_generate(id_reclamo: int) -> dict[str, Any]:
    with AITrace("clasificacion", claim_id=id_reclamo):
        return _analyze_and_generate_traced(id_reclamo)


def _analyze_and_generate_traced(id_reclamo: int) -> dict[str, Any]:
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
    closed = fetch_one("SELECT id_estado FROM estados_reclamo WHERE nombre='Cerrado'")
    if closed and reclamo['id_estado'] == closed['id_estado']:
        raise DomainError("Reabre el reclamo antes de analizarlo")

    try:
        analisis = clasificar_reclamo(reclamo["descripcion"])
        trace_update(classification_category=analisis["categoria"],
                     classification_model=analisis["modelo_usado"],
                     classification_confidence=analisis["confianza"])
        guardar_analisis(id_reclamo, analisis)

        config = _config()
        threshold = float(config.get("umbral_confianza", 0.85))
        if (analisis["confianza"] < threshold
                or analisis["prioridad"] in {"Alta", "Crítica", "Critica"}
                or bool(config.get("revision_humana_obligatoria"))):
            trace_update(route="atencion_humana", human_review_required=True)
            trace_append("fallback_reasons", "human_review_required")
        documentos = []
        if bool(config.get("usar_rag")):
            documentos = recuperar_documentos(
                reclamo["descripcion"],
                analisis["categoria"],
                int(config.get("max_documentos_recuperados") or 3),
                confianza=analisis["confianza"],
                umbral_confianza=threshold,
            )
            respuesta = generar_respuesta_sugerida(
                reclamo["cliente"],
                reclamo["codigo_pedido"],
                reclamo["descripcion"],
                analisis,
                documentos,
                historial=listar_mensajes_reclamo(id_reclamo),
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
    except DomainError:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo analizar el reclamo: {exc}") from exc


@app.get("/health")
def health() -> dict[str, Any]:
    try:
        fetch_one("SELECT 1 AS ok")
        database_status = "ok"
    except Exception:
        logger.exception("La verificación de salud no pudo consultar la base de datos")
        database_status = "error"
    try:
        rag_enabled = bool((_config() or {}).get("usar_rag"))
    except Exception:
        rag_enabled = False
    return {
        "status": "ok" if database_status == "ok" else "degraded",
        "database": database_status,
        "databaseProvider": "postgres" if using_postgres() else "sqlite",
        "ragEnabled": rag_enabled,
    }


@app.post("/api/chat")
def chat(payload: ChatPayload, authorization: str | None = Header(default=None)) -> dict[str, Any]:
    user = None
    if authorization and authorization.lower().startswith("bearer "):
        token_data = decode_token(authorization.split(" ", 1)[1].strip())
        if token_data:
            user = obtener_usuario_auth_por_id(token_data.get("sub"))
    return answer_chat(payload.message, user=user, context=payload.context)


@app.post("/api/auth/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    user = obtener_usuario_auth_por_correo(payload.email)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    return _auth_response(user)


@app.post("/api/auth/register", status_code=201)
def register(payload: RegisterRequest) -> dict[str, Any]:
    user = registrar_cliente_publico(
        payload.name, payload.email, hash_password(payload.password), payload.phone,
    )
    return _auth_response(user)


@app.post("/api/auth/password-reset/request")
def request_password_reset(payload: PasswordResetRequest) -> dict[str, Any]:
    # Academic prototype: simulated delivery, no real email provider configured.
    return {
        "ok": True,
        "message": f"Si {payload.email} esta registrado, se generaria un enlace de recuperacion.",
    }


@app.get("/api/auth/me")
def me(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {"user": _to_user(user)}


@app.patch("/api/auth/me")
def update_me(payload: ProfileUpdate, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    updated = actualizar_perfil_usuario(user["id_auth_user"], payload.name, payload.phone)
    return {"user": _to_user(updated)}


@app.get("/api/catalog")
def catalog() -> dict[str, Any]:
    restaurantes, productos_por_restaurante = listar_catalogo()
    return {
        "items": [
            {
                "id": str(restaurant["id_restaurante"]),
                "name": restaurant["nombre"],
                "category": restaurant["categoria"],
                "rating": float(restaurant["rating"] or 0),
                "time": restaurant["tiempo_entrega"],
                "delivery": float(restaurant["costo_delivery"] or 0),
                "image": restaurant.get("imagen"),
                "products": [
                    {
                        "id": str(product["id_producto"]),
                        "name": product["nombre"],
                        "description": product.get("descripcion") or "",
                        "price": float(product["precio"] or 0),
                        "image": product.get("imagen"),
                    }
                    for product in productos_por_restaurante.get(restaurant["id_restaurante"], [])
                ],
            }
            for restaurant in restaurantes
        ]
    }


@app.get("/api/notifications")
def notifications(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    from modules.notification_service import listing
    rows, unread = listing(user)
    return {"items": [_to_notification(row) for row in rows], "unread": unread}


@app.patch("/api/notifications/read")
def read_notifications(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    from modules.notification_service import mark_read
    mark_read(user)
    return notifications(user)


@app.patch("/api/notifications/{notification_id}/read")
def read_one_notification(notification_id: int, user=Depends(get_current_user)):
    from modules.notification_service import mark_read
    mark_read(user, notification_id)
    return notifications(user)


@app.get("/api/orders")
def orders(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    from modules.order_workflow import visible_order_ids
    return {"items": [_order_detail_or_404(row["id_pedido"], user) for row in visible_order_ids(user)]}


@app.post("/api/orders", status_code=201)
def create_order(payload: OrderCreate, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user["rol"] != "CLIENT":
        raise HTTPException(status_code=403, detail="Solo una cuenta cliente puede crear pedidos")
    from modules.order_service import create_catalog_order
    order_id = create_catalog_order(user, [_pydantic_data(item) for item in payload.items],
        payload.quote_hash, payload.payment_method, payload.delivery_address, payload.delivery_notes, payload.request_id)
    return {"order": _order_detail_or_404(order_id, user)}


@app.post("/api/orders/quote")
def quote_order(payload: OrderQuote) -> dict[str, Any]:
    from modules.order_service import quote_order as quote
    return quote([_pydantic_data(item) for item in payload.items])


@app.get("/api/orders/{order_id}")
def order_detail(order_id: int, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return {"order": _order_detail_or_404(order_id, user)}


@app.get("/api/dashboard")
def dashboard(user: dict[str, Any] = Depends(require_staff)) -> dict[str, Any]:
    metrics = obtener_metricas_dashboard()
    return {
        "metrics": metrics,
        "byCategory": reclamos_por_categoria(),
        "byPriority": reclamos_por_prioridad(),
        "byStatus": reclamos_por_estado(),
        "recentClaims": [_to_claim_summary(row) for row in listar_reclamos()[:5]],
    }


@app.post("/api/orders/{order_id}/transition")
def transition_order(order_id: int, payload: OrderTransition, user=Depends(get_current_user)):
    from modules.order_workflow import transition
    transition(order_id, user, payload.state, payload.expected_version, payload.request_id, payload.reason)
    return {"order": _order_detail_or_404(order_id, user)}


@app.post("/api/orders/{order_id}/assignment")
def assign_courier(order_id: int, payload: CourierAssignment, user=Depends(require_admin)):
    from modules.order_workflow import assign
    assign(order_id, user, payload.courier_id, payload.expected_version, payload.request_id, payload.reason)
    return {"order": _order_detail_or_404(order_id, user)}


@app.post("/api/orders/{order_id}/delay")
def order_delay(order_id: int, payload: DelayReport, user=Depends(get_current_user)):
    from modules.order_workflow import report_delay
    report_delay(order_id, user, payload.expected_version, payload.request_id, payload.reason)
    return {"order": _order_detail_or_404(order_id, user)}


@app.get("/api/operations/admin")
def operations_overview(user=Depends(require_admin)):
    from modules.operations_admin import overview
    return overview(user)


@app.patch("/api/operations/users/{user_id}")
def operations_user(user_id: int, payload: UserRoleUpdate, user=Depends(require_admin)):
    from modules.operations_admin import update_user
    update_user(user, user_id, payload.role, payload.active, payload.request_id, payload.reason)
    # A self-demotion takes effect immediately, including for the next request.
    return {"ok": True}


@app.put("/api/operations/restaurants/{restaurant_id}/operator")
def operations_grant(restaurant_id: int, payload: OperatorGrant, user=Depends(require_admin)):
    from modules.operations_admin import grant
    grant(user, restaurant_id, payload.user_id, payload.active, payload.edit_products, payload.request_id, payload.reason)
    return {"ok": True}


@app.patch("/api/operations/restaurants/{restaurant_id}")
def operations_restaurant(restaurant_id: int, payload: RestaurantUpdate, user=Depends(require_admin)):
    from modules.operations_admin import update_restaurant
    update_restaurant(user, restaurant_id, payload.address, payload.responsible, payload.active, payload.request_id)
    return {"ok": True}


@app.get("/api/operations/products")
def operations_products(user=Depends(get_current_user)):
    from modules.operations_admin import products
    return {"items": products(user)}


@app.patch("/api/operations/products/{product_id}")
def operations_product(product_id: int, payload: ProductUpdate, user=Depends(get_current_user)):
    from modules.operations_admin import update_product
    update_product(user, product_id, payload.name, payload.price, payload.available, payload.request_id)
    return {"ok": True}


@app.get("/api/operations/availability")
def courier_availability(user=Depends(get_current_user)):
    from modules.order_workflow import require_role
    require_role(user, {"COURIER"})
    row = fetch_one("SELECT disponible FROM courier_profiles WHERE id_auth_user=?", (user["id_auth_user"],))
    return {"available": bool(row and row["disponible"])}


@app.put("/api/operations/availability")
def set_courier_availability(payload: CourierAvailability, user=Depends(get_current_user)):
    from modules.operations_admin import availability
    availability(user, payload.available, payload.request_id)
    return {"available": payload.available}


@app.get("/api/claims/{claim_id}/order-context")
def claim_order_context(claim_id: int, user=Depends(require_staff)):
    claim = fetch_one("SELECT id_pedido FROM reclamos WHERE id_reclamo=?", (claim_id,))
    if not claim:
        raise HTTPException(404, "Reclamo no encontrado")
    return {"order": _order_detail_or_404(claim["id_pedido"], user) if claim["id_pedido"] else None,
            "financialStatus": "Pago y devoluciones no verificados"}


@app.get("/api/claims")
def claims(
    user: dict[str, Any] = Depends(get_current_user),
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    assignment: Literal["ALL", "UNASSIGNED", "MINE", "ESCALATED"] = "ALL",
    search: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
) -> dict[str, Any]:
    from modules.order_workflow import require_role
    require_role(user, {"CLIENT", "AGENT", "ADMIN"})
    rows = listar_reclamos_por_correo(user["correo"]) if user["rol"] == "CLIENT" else listar_reclamos()
    items = [_to_claim_summary(row) for row in rows]
    query = (search or "").strip().lower()
    filtered = [
        item for item in items
        if (not date_from or item["createdAt"][:10] >= date_from)
        and (not date_to or item["createdAt"][:10] <= date_to)
        and (not status or status == "ALL" or item["statusKey"] == status)
        and (
            not query
            or any(query in str(item.get(key, "")).lower() for key in (
                "code", "customerName", "customerEmail", "orderCode", "category", "priority"
            ))
        )
    ]
    if user["rol"] in {"AGENT", "ADMIN"}:
        if assignment == "UNASSIGNED":
            filtered = [item for item in filtered if not item["assignment"]["active"] and item["statusKey"] != "CLOSED"]
        elif assignment == "MINE":
            filtered = [item for item in filtered if item["assignment"]["id"] == user["id_auth_user"]]
        elif assignment == "ESCALATED":
            filtered = [item for item in filtered if item["statusKey"] == "ESCALATED"]
    else:
        for item in filtered:
            item.pop("assignment", None)
    total = len(filtered)
    start = (page - 1) * page_size
    return {
        "items": filtered[start:start + page_size],
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "total": total,
            "totalPages": max(1, (total + page_size - 1) // page_size),
        },
    }


@app.post("/api/claims", status_code=201)
def create_claim(payload: ClaimCreate, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    from modules.order_workflow import require_role
    require_role(user, {"CLIENT", "AGENT", "ADMIN"})
    if user["rol"] == "CLIENT" and payload.customer_email.lower() != user["correo"].lower():
        raise HTTPException(status_code=403, detail="No puedes registrar reclamos para otro cliente")
    owner_email = user["correo"] if user["rol"] == "CLIENT" else str(payload.customer_email)
    order = fetch_one("""SELECT p.*, c.nombre AS cliente, c.correo, c.telefono
        FROM pedidos p JOIN clientes c ON c.id_cliente=p.id_cliente
        WHERE p.codigo_pedido=? AND lower(c.correo)=lower(?)""",
        (payload.order_code.strip(), owner_email))
    if not order:
        raise HTTPException(status_code=404, detail="Pedido no encontrado o no disponible para esta cuenta")
    try:
        id_reclamo = crear_reclamo(
            order["id_cliente"],
            order["codigo_pedido"],
            payload.channel,
            str(order["fecha_creacion"]),
            payload.description,
            "Pendiente de asignación",
            id_pedido=order["id_pedido"], actor=user, request_id=payload.request_id,
        )
        if payload.analyze:
            try:
                _analyze_and_generate(id_reclamo)
            except HTTPException:
                pass
        return _detail_for_user(id_reclamo, user)
    except DomainError:
        raise
    except Exception as exc:
        logger.exception("No se pudo crear el reclamo")
        raise HTTPException(status_code=500, detail="No se pudo crear el reclamo.") from exc


@app.get("/api/claims/{claim_id}")
def claim_detail(claim_id: int, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    return _detail_for_user(claim_id, user)


@app.get("/api/claim-assignees")
def claim_assignees(user=Depends(require_staff)):
    rows = fetch_all("SELECT id_auth_user,nombre,rol FROM auth_users WHERE estado='ACTIVO' AND rol IN ('AGENT','ADMIN') ORDER BY id_auth_user")
    return {"items": [{"id": row["id_auth_user"], "name": row["nombre"], "role": row["rol"]} for row in rows]}


@app.post("/api/claims/{claim_id}/assignment")
def assign_claim(claim_id: int, payload: ClaimAssignmentPayload, user=Depends(require_staff)):
    from modules.claim_assignment import assign
    assign(claim_id, user, payload.assignee_id, payload.expected_version, payload.request_id, payload.reason)
    return _to_claim_detail(claim_id)


@app.post("/api/claims/{claim_id}/escalate")
def escalate_claim(claim_id: int, payload: ClaimEscalationPayload, user=Depends(require_staff)):
    from modules.claim_assignment import assign
    assign(claim_id, user, payload.assignee_id, payload.expected_version, payload.request_id, payload.reason, escalate=True)
    return _to_claim_detail(claim_id)


@app.get("/api/claims/{claim_id}/messages")
def claim_messages(claim_id: int, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    _detail_for_user(claim_id, user)
    detail = _to_claim_detail(claim_id)
    if user["rol"] == "CLIENT" and detail["claim"]["customerEmail"].lower() != user["correo"].lower():
        raise HTTPException(status_code=403, detail="No tienes acceso a este reclamo")
    messages = listar_mensajes_reclamo(claim_id, incluir_internos=user["rol"] in {"AGENT", "ADMIN"})
    if not messages:
        crear_mensaje_reclamo(claim_id, "client", detail["claim"]["customerEmail"], detail["claim"]["description"])
        messages = listar_mensajes_reclamo(claim_id, incluir_internos=user["rol"] in {"AGENT", "ADMIN"})
    return {
        "items": [
            _to_message(row)
            for row in messages
        ]
    }


@app.post("/api/claims/{claim_id}/messages", status_code=201)
def add_claim_message(
    claim_id: int,
    payload: ClaimMessagePayload,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    _detail_for_user(claim_id, user)
    detail = _to_claim_detail(claim_id)
    if user["rol"] == "CLIENT" and detail["claim"]["customerEmail"].lower() != user["correo"].lower():
        raise HTTPException(status_code=403, detail="No tienes acceso a este reclamo")
    if detail["claim"]["statusKey"] == "CLOSED":
        raise HTTPException(status_code=409, detail="El reclamo está cerrado. Reábrelo antes de responder.")

    from modules.claim_workflow import record_message
    record_message(claim_id, payload.message, user, payload.request_id)
    return claim_messages(claim_id, user)


@app.post("/api/claims/{claim_id}/close")
def close_claim(claim_id: int, payload: CloseRequest, user: dict[str, Any] = Depends(require_staff)) -> dict[str, Any]:
    from modules.claim_workflow import change_state
    change_state(claim_id, user, "Cerrado", payload.comment, request_id=payload.request_id)
    return _to_claim_detail(claim_id)


@app.post("/api/claims/{claim_id}/reopen")
def reopen_claim(claim_id: int, payload: ClaimRetryPayload | None = None, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    _detail_for_user(claim_id, user)
    detail = _to_claim_detail(claim_id)
    if user["rol"] == "CLIENT" and detail["claim"]["customerEmail"].lower() != user["correo"].lower():
        raise HTTPException(status_code=403, detail="No tienes acceso a este reclamo")
    from modules.claim_workflow import change_state
    change_state(claim_id, user, "En revision", reopen=True, request_id=payload.request_id if payload else None)
    return _detail_for_user(claim_id, user)


@app.get("/api/claims/{claim_id}/comments")
def claim_comments(claim_id: int, user: dict[str, Any] = Depends(require_staff)) -> dict[str, Any]:
    _to_claim_detail(claim_id)
    return {"items": [_to_comment(row) for row in listar_comentarios_agente(claim_id)]}


@app.post("/api/claims/{claim_id}/comments", status_code=201)
def add_claim_comment(
    claim_id: int,
    payload: AgentCommentPayload,
    user: dict[str, Any] = Depends(require_staff),
) -> dict[str, Any]:
    _to_claim_detail(claim_id)
    crear_comentario_agente(claim_id, payload.comment, payload.type, user["nombre"], user["id_auth_user"])
    return {"items": [_to_comment(row) for row in listar_comentarios_agente(claim_id)]}


@app.post("/api/claims/{claim_id}/analyze")
def analyze_claim(claim_id: int, user: dict[str, Any] = Depends(require_staff)) -> dict[str, Any]:
    return _analyze_and_generate(claim_id)


@app.patch("/api/claims/{claim_id}/state")
def update_claim_state(claim_id: int, payload: StateUpdate, user: dict[str, Any] = Depends(require_staff)) -> dict[str, Any]:
    state = UI_TO_STATUS.get(payload.state, payload.state)
    if state == "En revisión":
        state = "En revision"
    try:
        if state == "Respondido":
            marcar_respondido(claim_id, payload.comment, actor=user)
        elif state == "Escalado":
            from uuid import uuid4
            from modules.claim_assignment import assign
            current = fetch_one("SELECT version_asignacion FROM reclamos WHERE id_reclamo=?", (claim_id,))
            if not current:
                raise HTTPException(404, "Reclamo no encontrado")
            assign(claim_id, user, None, payload.expected_version if payload.expected_version is not None else current["version_asignacion"],
                   payload.request_id or str(uuid4()), payload.comment or "", escalate=True)
        elif state == "Cerrado":
            from modules.claim_workflow import change_state
            change_state(claim_id, user, "Cerrado", payload.comment, request_id=payload.request_id)
        else:
            actualizar_estado_reclamo(claim_id, state, "Actualizacion desde API", payload.comment, actor=user)
        return _to_claim_detail(claim_id)
    except DomainError:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.patch("/api/responses/{response_id}")
def update_response(response_id: int, payload: ResponseUpdate, user: dict[str, Any] = Depends(require_staff)) -> dict[str, Any]:
    actualizar_respuesta_final(response_id, payload.response_text, "EDITADA", actor=user["nombre"], actor_id=user["id_auth_user"])
    row = fetch_one("SELECT id_reclamo FROM respuestas_sugeridas WHERE id_respuesta = ?", (response_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Respuesta no encontrada")
    return _to_claim_detail(row["id_reclamo"])


@app.post("/api/responses/{response_id}/approve")
def approve_response(response_id: int, payload: ResponseUpdate | None = None, user: dict[str, Any] = Depends(require_staff)) -> dict[str, Any]:
    row = fetch_one(
        "SELECT id_reclamo, respuesta_generada, respuesta_editada FROM respuestas_sugeridas WHERE id_respuesta = ?",
        (response_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Respuesta no encontrada")
    texto_base = payload.response_text if payload and payload.response_text.strip() else row["respuesta_editada"] or row["respuesta_generada"]
    respuesta_firmada = _firmar_respuesta_agente(texto_base, user["nombre"])
    aprobar_respuesta(response_id, respuesta_firmada, user["nombre"], user["id_auth_user"])
    return _to_claim_detail(row["id_reclamo"])


@app.get("/api/documents")
def documents(user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    docs = [_to_document(doc) for doc in listar_documentos()]
    return {"items": docs, "index": obtener_resumen_indice()}


@app.post("/api/documents/pdf-preview")
async def preview_document_pdf(request: Request, user: dict[str, Any] = Depends(require_admin)) -> dict[str, str]:
    if request.headers.get("content-type", "").split(";")[0].lower() != "application/pdf":
        raise HTTPException(415, "Selecciona un archivo PDF.")
    data = bytearray()
    async for chunk in request.stream():
        if len(data) + len(chunk) > PDF_MAX_BYTES:
            raise HTTPException(413, "El PDF supera el tamaño permitido.")
        data.extend(chunk)
    try:
        return {"content": await run_in_threadpool(extract_pdf_text, bytes(data))}
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc


def require_document_maintenance():
    if not allows_automatic_database_setup():
        raise HTTPException(
            503, "El mantenimiento documental debe ejecutarse mediante una migración controlada."
        )


@app.post("/api/documents", status_code=201)
def create_document(payload: DocumentPayload, user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    require_document_maintenance()
    if get_categoria_id(payload.category) is None:
        raise HTTPException(422, "Selecciona una categoría documental válida.")
    try:
        crear_documento_base(payload.title, payload.type, payload.category, payload.content)
    except DuplicateDocument as exc:
        raise HTTPException(409, str(exc)) from exc
    construir_indice_vectorial(forzar=True)
    return documents(user)


@app.put("/api/documents/{document_id}")
def update_document(document_id: int, payload: DocumentPayload, user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    require_document_maintenance()
    if get_categoria_id(payload.category) is None:
        raise HTTPException(422, "Selecciona una categoría documental válida.")
    try:
        actualizar_documento_base(document_id, payload.title, payload.type, payload.category, payload.content)
    except DuplicateDocument as exc:
        raise HTTPException(409, str(exc)) from exc
    construir_indice_vectorial(forzar=True)
    return documents(user)


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: int, user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    require_document_maintenance()
    desactivar_documento_base(document_id)
    construir_indice_vectorial(forzar=True)
    return documents(user)


@app.post("/api/documents/reindex")
def reindex_documents(user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    require_document_maintenance()
    return construir_indice_vectorial(forzar=True)


@app.get("/api/config")
def get_config(user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    from modules.ai_status import execution_status
    config = get_configuracion_activa()
    if not config:
        raise DomainError("No existe una configuración activa editable.")
    count = fetch_one("SELECT COUNT(*) AS n FROM configuracion_modelo_ia WHERE activo=1")['n']
    return {
        "id": config['id_configuracion'],
        "activeCount": count,
        "selectionPolicy": "highest_active_id",
        "model": config.get("modelo_base"),
        "runtime": execution_status(),
        "confidenceThreshold": float(config["umbral_confianza"]),
        "humanReviewRequired": bool(config.get("revision_humana_obligatoria")),
        "useRag": bool(config.get("usar_rag")),
        "maxDocuments": int(config.get("max_documentos_recuperados") or 3),
        "updatedAt": config.get("fecha_actualizacion"),
    }


@app.put("/api/config")
def put_config(payload: ConfigUpdate, user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    actualizar_configuracion(
        payload.confidence_threshold,
        payload.human_review_required,
        payload.use_rag,
        payload.max_documents,
        payload.config_id,
    )
    return get_config(user)


@app.get("/api/reports")
def reports(
    user: dict[str, Any] = Depends(require_admin),
    date_from: str | None = None,
    date_to: str | None = None,
    status: str | None = None,
    category: str | None = None,
    priority: str | None = None,
) -> dict[str, Any]:
    rows = [_to_claim_summary(row) for row in listar_reclamos()]
    scoped = [
        item for item in rows
        if (not date_from or item["createdAt"][:10] >= date_from)
        and (not date_to or item["createdAt"][:10] <= date_to)
        and (not status or status == "ALL" or item["statusKey"] == status)
        and (not category or category == "ALL" or item["category"] == category)
        and (not priority or priority == "ALL" or item["priorityKey"] == priority)
    ]

    def distribution(key: str, label: str) -> list[dict[str, Any]]:
        counts: dict[str, int] = {}
        for item in scoped:
            value = str(item.get(key) or "Sin clasificar")
            counts[value] = counts.get(value, 0) + 1
        return [{label: value, "total": total} for value, total in sorted(counts.items(), key=lambda pair: pair[1], reverse=True)]

    metrics = obtener_metricas_dashboard()
    metrics.update({
        "total": len(scoped),
        "reclamos_abiertos": sum(item["statusKey"] != "CLOSED" for item in scoped),
        "reclamos_cerrados": sum(item["statusKey"] == "CLOSED" for item in scoped),
        "casos_escalados": sum(item["statusKey"] == "ESCALATED" for item in scoped),
        "porcentaje_criticos": round(sum(item["priorityKey"] == "CRITICAL" for item in scoped) * 100 / len(scoped), 1) if scoped else 0,
    })
    evolution: dict[str, int] = {}
    for item in scoped:
        day = item["createdAt"][:10]
        evolution[day] = evolution.get(day, 0) + 1
    return {
        "metrics": metrics,
        "byCategory": distribution("category", "categoria"),
        "byPriority": distribution("priority", "prioridad"),
        "byStatus": distribution("status", "estado"),
        "confidenceByCategory": confianza_por_categoria(),
        "responsesByReviewStatus": respuestas_por_estado_revision(),
        "attentionTimeByCategory": tiempo_promedio_por_categoria(),
        "firstResponseTimeByCategory": tiempo_primera_respuesta_por_categoria(),
        "claimsEvolution": [{"fecha": day, "total": evolution[day]} for day in sorted(evolution)],
        "filters": {
            "dateFrom": date_from,
            "dateTo": date_to,
            "status": status,
            "category": category,
            "priority": priority,
        },
    }
