from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import re
import sys
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from database.db_connection import fetch_all, fetch_one, init_db, using_postgres
from database.repositories import (
    actualizar_configuracion,
    actualizar_documento_base,
    actualizar_estado_reclamo,
    actualizar_respuesta_final,
    asegurar_pedidos_demo_base,
    asegurar_usuarios_auth_base,
    aprobar_respuesta,
    cerrar_reclamo,
    crear_cliente,
    crear_comentario_agente,
    crear_documento_base,
    crear_notificacion,
    crear_pedido_cliente,
    crear_reclamo,
    crear_mensaje_reclamo,
    crear_usuario_auth,
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
from modules.security import create_token, decode_token, hash_password, verify_password
from modules.chatbot_service import answer_chat
from modules.config import allow_vercel_previews, cors_origins, validate_runtime_config


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    validate_runtime_config()
    init_db()
    asegurar_usuarios_auth_base()
    asegurar_pedidos_demo_base()
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


class OrderItemCreate(BaseModel):
    name: str = Field(..., min_length=1)
    quantity: int = Field(..., ge=1)
    price: float = Field(..., ge=0)
    image: str | None = None


class OrderCreate(BaseModel):
    store_name: str = Field(..., min_length=2)
    store_image: str | None = None
    payment_method: str = Field(..., min_length=2)
    delivery_address: str = Field(..., min_length=5)
    items: list[OrderItemCreate] = Field(..., min_length=1)


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


class DocumentPayload(BaseModel):
    title: str = Field(..., min_length=3)
    type: str = Field(..., pattern="^(POLITICA|FAQ|PROCEDIMIENTO|MANUAL)$")
    category: str = Field(..., min_length=3)
    content: str = Field(..., min_length=20)


class AgentCommentPayload(BaseModel):
    comment: str = Field(..., min_length=3)
    type: str = Field("INTERNO", pattern="^(INTERNO|SEGUIMIENTO|ESCALAMIENTO|CIERRE)$")


class ClaimMessagePayload(BaseModel):
    message: str = Field(..., min_length=2, max_length=4000)


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


def _to_order(row: dict[str, Any], items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "id": str(row["id_pedido"]),
        "code": row["codigo_pedido"],
        "userId": str(row["id_cliente"]),
        "storeName": row["tienda_nombre"],
        "storeImage": row.get("tienda_imagen"),
        "status": row["estado"],
        "total": float(row.get("total") or 0),
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
    if user["rol"] == "CLIENT" and row["correo_cliente"].lower() != user["correo"].lower():
        raise HTTPException(status_code=403, detail="No tienes acceso a este pedido")
    return _to_order(row, items)


def _pydantic_data(model: BaseModel) -> dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


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
    if obtener_usuario_auth_por_correo(payload.email):
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con este correo")
    user_id = crear_usuario_auth(
        payload.name,
        payload.email,
        hash_password(payload.password),
        "CLIENT",
        payload.phone,
    )
    crear_cliente(payload.name, payload.email, payload.phone)
    user = obtener_usuario_auth_por_id(user_id)
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
    items = [_to_notification(row) for row in listar_notificaciones(user["correo"])]
    return {"items": items, "unread": sum(1 for item in items if not item["read"])}


@app.patch("/api/notifications/read")
def read_notifications(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    marcar_notificaciones_leidas(user["correo"])
    return notifications(user)


@app.get("/api/orders")
def orders(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user["rol"] != "CLIENT":
        return {"items": []}
    rows = listar_pedidos_por_correo(user["correo"])
    items = []
    for row in rows:
        order, order_items = obtener_pedido(row["id_pedido"])
        items.append(_to_order(order, order_items))
    return {"items": items}


@app.post("/api/orders", status_code=201)
def create_order(payload: OrderCreate, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user["rol"] != "CLIENT":
        raise HTTPException(status_code=403, detail="Solo una cuenta cliente puede crear pedidos")
    order_id = crear_pedido_cliente(
        user["correo"],
        user["nombre"],
        user.get("telefono"),
        payload.store_name,
        payload.store_image,
        payload.payment_method,
        payload.delivery_address,
        [_pydantic_data(item) for item in payload.items],
        "PREPARING",
    )
    return {"order": _order_detail_or_404(order_id, user)}


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


@app.get("/api/claims")
def claims(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    rows = listar_reclamos_por_correo(user["correo"]) if user["rol"] == "CLIENT" else listar_reclamos()
    return {"items": [_to_claim_summary(row) for row in rows]}


@app.post("/api/claims", status_code=201)
def create_claim(payload: ClaimCreate, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user["rol"] == "CLIENT" and payload.customer_email.lower() != user["correo"].lower():
        raise HTTPException(status_code=403, detail="No puedes registrar reclamos para otro cliente")
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
            try:
                return _analyze_and_generate(id_reclamo)
            except HTTPException:
                return _to_claim_detail(id_reclamo)
        return _to_claim_detail(id_reclamo)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"No se pudo crear el reclamo: {exc}") from exc


@app.get("/api/claims/{claim_id}")
def claim_detail(claim_id: int, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    detail = _to_claim_detail(claim_id)
    if user["rol"] == "CLIENT" and detail["claim"]["customerEmail"].lower() != user["correo"].lower():
        raise HTTPException(status_code=403, detail="No tienes acceso a este reclamo")
    return detail


@app.get("/api/claims/{claim_id}/messages")
def claim_messages(claim_id: int, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
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
    detail = _to_claim_detail(claim_id)
    if user["rol"] == "CLIENT" and detail["claim"]["customerEmail"].lower() != user["correo"].lower():
        raise HTTPException(status_code=403, detail="No tienes acceso a este reclamo")
    if detail["claim"]["statusKey"] == "CLOSED":
        raise HTTPException(status_code=409, detail="El reclamo está cerrado. Reábrelo antes de responder.")

    sender_type = "client" if user["rol"] == "CLIENT" else "agent"
    crear_mensaje_reclamo(claim_id, sender_type, user["id_auth_user"], payload.message)
    if sender_type == "client":
        try:
            actualizar_estado_reclamo(
                claim_id,
                "En revision",
                "Respuesta del cliente",
                "El cliente agregó información al reclamo.",
            )
        except Exception:
            logger.exception("No se pudo actualizar el estado del reclamo %s tras el mensaje del cliente", claim_id)
        try:
            staff_members = fetch_all("SELECT correo FROM auth_users WHERE rol IN ('AGENT', 'ADMIN') AND estado = 'ACTIVO'")
            for staff in staff_members:
                try:
                    crear_notificacion(
                        staff["correo"],
                        "Cliente respondió un reclamo",
                        f"El cliente agregó un mensaje al reclamo {detail['claim']['code']}.",
                        "ALERTA",
                        claim_id,
                    )
                except Exception:
                    logger.exception("No se pudo notificar a %s sobre el reclamo %s", staff["correo"], claim_id)
        except Exception:
            logger.exception("No se pudieron consultar agentes para notificar sobre el reclamo %s", claim_id)
    else:
        try:
            marcar_respondido(claim_id, "El agente respondió dentro de la conversación.")
        except Exception:
            logger.exception("No se pudo marcar como respondido el reclamo %s", claim_id)
        try:
            crear_notificacion(
                detail["claim"]["customerEmail"],
                "Nuevo mensaje de soporte",
                f"Soporte respondió en tu reclamo {detail['claim']['code']}.",
                "RESPUESTA",
                claim_id,
            )
        except Exception:
            logger.exception("No se pudo notificar al cliente sobre el reclamo %s", claim_id)
    return claim_messages(claim_id, user)


@app.post("/api/claims/{claim_id}/close")
def close_claim(claim_id: int, user: dict[str, Any] = Depends(require_staff)) -> dict[str, Any]:
    cerrar_reclamo(claim_id, "Cerrado", "El agente cerró el reclamo.")
    return _to_claim_detail(claim_id)


@app.post("/api/claims/{claim_id}/reopen")
def reopen_claim(claim_id: int, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    detail = _to_claim_detail(claim_id)
    if user["rol"] == "CLIENT" and detail["claim"]["customerEmail"].lower() != user["correo"].lower():
        raise HTTPException(status_code=403, detail="No tienes acceso a este reclamo")
    reabrir_reclamo(claim_id)
    return _to_claim_detail(claim_id)


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
    crear_comentario_agente(claim_id, payload.comment, payload.type, user["nombre"])
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
def update_response(response_id: int, payload: ResponseUpdate, user: dict[str, Any] = Depends(require_staff)) -> dict[str, Any]:
    actualizar_respuesta_final(response_id, payload.response_text, "EDITADA")
    row = fetch_one("SELECT id_reclamo FROM respuestas_sugeridas WHERE id_respuesta = ?", (response_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Respuesta no encontrada")
    return _to_claim_detail(row["id_reclamo"])


@app.post("/api/responses/{response_id}/approve")
def approve_response(response_id: int, payload: ResponseUpdate | None = None, user: dict[str, Any] = Depends(require_staff)) -> dict[str, Any]:
    row = fetch_one(
        "SELECT id_reclamo, respuesta_generada FROM respuestas_sugeridas WHERE id_respuesta = ?",
        (response_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="Respuesta no encontrada")
    texto_base = payload.response_text if payload and payload.response_text.strip() else row["respuesta_generada"]
    respuesta_firmada = _firmar_respuesta_agente(texto_base, user["nombre"])
    aprobar_respuesta(response_id, respuesta_firmada)
    marcar_respondido(row["id_reclamo"], "Respuesta enviada al cliente desde el panel de soporte.")
    return _to_claim_detail(row["id_reclamo"])


@app.get("/api/documents")
def documents(user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    docs = [_to_document(doc) for doc in listar_documentos()]
    return {"items": docs, "index": obtener_resumen_indice()}


@app.post("/api/documents", status_code=201)
def create_document(payload: DocumentPayload, user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    crear_documento_base(payload.title, payload.type, payload.category, payload.content)
    construir_indice_vectorial(forzar=True)
    return documents(user)


@app.put("/api/documents/{document_id}")
def update_document(document_id: int, payload: DocumentPayload, user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    actualizar_documento_base(document_id, payload.title, payload.type, payload.category, payload.content)
    construir_indice_vectorial(forzar=True)
    return documents(user)


@app.delete("/api/documents/{document_id}")
def delete_document(document_id: int, user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    desactivar_documento_base(document_id)
    construir_indice_vectorial(forzar=True)
    return documents(user)


@app.post("/api/documents/reindex")
def reindex_documents(user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return construir_indice_vectorial(forzar=True)


@app.get("/api/config")
def get_config(user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
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
def put_config(payload: ConfigUpdate, user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    actualizar_configuracion(
        payload.confidence_threshold,
        payload.human_review_required,
        payload.use_rag,
        payload.max_documents,
    )
    return get_config()


@app.get("/api/reports")
def reports(user: dict[str, Any] = Depends(require_admin)) -> dict[str, Any]:
    return {
        "metrics": obtener_metricas_dashboard(),
        "byCategory": reclamos_por_categoria(),
        "byPriority": reclamos_por_prioridad(),
        "byStatus": reclamos_por_estado(),
        "confidenceByCategory": confianza_por_categoria(),
        "responsesByReviewStatus": respuestas_por_estado_revision(),
        "attentionTimeByCategory": tiempo_promedio_por_categoria(),
        "firstResponseTimeByCategory": tiempo_primera_respuesta_por_categoria(),
        "claimsEvolution": evolucion_reclamos_por_fecha(),
    }
