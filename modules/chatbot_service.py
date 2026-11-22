from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from typing import Any

from database.repositories import (
    listar_catalogo,
    listar_notificaciones,
    listar_pedidos_por_correo,
    listar_reclamos_por_correo,
)
from modules.rag_engine import recuperar_documentos
from modules.faq_router import find_faq, is_procedural_question
from modules.ai_trace import traced_chat, trace_update, trace_append

logger = logging.getLogger(__name__)

PERSONAL_INTENTS = {
    "order_count",
    "recent_orders",
    "orders_in_transit",
    "last_order",
    "order_status",
    "claim_count",
    "open_claims",
    "claim_status",
    "notifications",
    "cart_summary",
}

RECOMMENDATION_WORDS = ("recomiend", "sugier", "plato", "comida", "comer", "antojo", "opciones para")
FOLLOW_UP_WORDS = ("otro", "otra", "mas barato", "menos de", "y si", "prefiero", "sin ")
FILLER_WORDS = {"algo", "comer", "comida", "plato", "platos", "quiero", "busco", "para",
                "recomienda", "recomiendas", "sugiere", "opciones", "tengo", "presupuesto",
                "soles", "menos", "hasta", "barato", "barata", "dame", "puedes", "favor",
                "recomiendame", "recomendacion", "recomendaciones", "gustaria", "prefiero",
                "otro", "otra", "tipo", "mas", "con", "una", "uno", "las", "los"}


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in value if not unicodedata.combining(char))


def _conversation(context: dict[str, Any] | None) -> list[dict[str, str]]:
    raw = (context or {}).get("history")
    if not isinstance(raw, list):
        return []
    return [{"role": item["role"], "text": item["text"][:400]}
            for item in raw[-8:] if isinstance(item, dict)
            and item.get("role") in {"user", "bot"} and isinstance(item.get("text"), str)]


def _recommendations(message: str, history: list[dict[str, str]]) -> dict[str, Any] | None:
    current = _normalize(message)
    previous = next((item["text"] for item in reversed(history) if item["role"] == "user"), "")
    if not any(word in current for word in RECOMMENDATION_WORDS):
        if not previous or not any(word in current for word in FOLLOW_UP_WORDS):
            return None
        if not any(word in _normalize(previous) for word in RECOMMENDATION_WORDS):
            return None
    query = _normalize(f"{previous} {message}" if previous and any(word in current for word in FOLLOW_UP_WORDS) else message)
    money = re.findall(r"(?:s/\.?\s*(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*soles|(?:hasta|menos de)\s*(\d+(?:[.,]\d+)?))", query)
    budget = float(next(value for value in money[-1] if value).replace(",", ".")) if money else None
    query = re.sub(r"(?:s/\.?\s*\d+(?:[.,]\d+)?|\d+(?:[.,]\d+)?\s*soles|(?:hasta|menos de)\s*\d+(?:[.,]\d+)?)", " ", query)
    negatives = re.findall(r"\bsin\s+([a-z]{4,})", query)
    terms = {term for term in re.findall(r"[a-z]{4,}", query)
             if term not in FILLER_WORDS and term not in negatives and term != "sin"
             and not term.startswith(("recomiend", "recomend", "sugier"))}
    restaurants, grouped = listar_catalogo()
    candidates = []
    for restaurant in restaurants:
        for product in grouped.get(restaurant["id_restaurante"], []):
            price = float(product["precio"])
            if budget is not None and price > budget:
                continue
            description = _normalize(product.get("descripcion") or "")
            if any(f"sin {word}" not in description for word in negatives):
                continue
            searchable = _normalize(" ".join((product["nombre"], description, restaurant["categoria"])))
            score = sum(term in searchable for term in terms)
            if terms and score < len(terms):
                continue
            candidates.append((score, price, {
                "productId": str(product["id_producto"]),
                "restaurantId": str(restaurant["id_restaurante"]),
                "name": product["nombre"], "restaurant": restaurant["nombre"],
                "price": price, "description": product.get("descripcion") or "",
            }))
    candidates.sort(key=lambda item: (-item[0], item[1], item[2]["productId"]))
    products = [item[2] for item in candidates[:3]]
    if products:
        detail = f" por hasta S/ {budget:.2f}" if budget is not None else ""
        text = f"Encontré estas opciones disponibles{detail} en el catálogo. ¿Prefieres alguna o quieres ajustar el presupuesto o el tipo de comida?"
    else:
        text = "No encontré productos disponibles que cumplan esos criterios. ¿Quieres cambiar el presupuesto o indicarme otra preferencia?"
    return {"message": text, "intent": "recommendations", "provider": "catalog",
            "documents": [], "recommendations": products}


def detect_chat_intent(message: str) -> dict[str, Any]:
    text = _normalize(message)
    order_code = re.search(r"\bord-[a-z0-9-]+\b", text)
    claim_code = re.search(r"\brc-[a-z0-9-]+\b", text)

    if "cuantos pedidos" in text or "cuantas pedidos" in text:
        intent = "order_count"
    elif "ultimos pedidos" in text or "pedidos recientes" in text:
        intent = "recent_orders"
    elif "pedidos en camino" in text or "pedido en camino" in text:
        intent = "orders_in_transit"
    elif "ultimo pedido" in text or "gaste en mi ultimo" in text:
        intent = "last_order"
    elif order_code or ("estado" in text and "pedido" in text):
        intent = "order_status"
    elif "cuantos reclamos" in text:
        intent = "claim_count"
    elif "reclamos abiertos" in text or "reclamo abierto" in text:
        intent = "open_claims"
    elif claim_code or ("estado" in text and "reclamo" in text):
        intent = "claim_status"
    elif "notificaciones" in text or "avisos" in text:
        intent = "notifications"
    elif "carrito" in text and any(word in text for word in ["tengo", "cuantos", "productos", "subtotal"]):
        intent = "cart_summary"
    elif any(phrase in text for phrase in ["como hago un pedido", "como comprar", "finalizo mi compra"]):
        intent = "how_to_order"
    elif any(phrase in text for phrase in ["como creo un reclamo", "como reporto", "tengo un problema"]):
        intent = "how_to_claim"
    elif any(phrase in text for phrase in ["cobraron dos veces", "pedido incompleto", "entregado pero no"]):
        intent = "sensitive_problem"
    elif "cierro sesion" in text:
        intent = "logout_help"
    elif "contacto con soporte" in text or "contactar soporte" in text:
        intent = "support_help"
    else:
        intent = "general"
    return {
        "name": intent,
        "order_code": order_code.group(0).upper() if order_code else None,
        "claim_code": claim_code.group(0).upper() if claim_code else None,
        "requires_auth": intent in PERSONAL_INTENTS,
    }


def build_user_context(user: dict[str, Any], intent: dict[str, Any], client_context: dict[str, Any] | None = None) -> dict[str, Any]:
    orders = listar_pedidos_por_correo(user["correo"])
    claims = listar_reclamos_por_correo(user["correo"])
    notifications = listar_notificaciones(user["correo"])
    open_claims = [item for item in claims if item.get("estado") != "Cerrado"]
    in_transit = [item for item in orders if item.get("estado") == "IN_TRANSIT"]
    context = {
        "user_name": user["nombre"],
        "total_orders": len(orders),
        "orders_in_transit": len(in_transit),
        "recent_orders": orders[:3],
        "last_order": orders[0] if orders else None,
        "total_claims": len(claims),
        "open_claims": len(open_claims),
        "recent_open_claim": open_claims[0] if open_claims else None,
        "last_claim": claims[0] if claims else None,
        "total_notifications": len(notifications),
        "unread_notifications": sum(1 for item in notifications if not item.get("leida")),
        "cart": (client_context or {}).get("cart"),
    }
    if intent.get("order_code"):
        context["matched_order"] = next(
            (item for item in orders if item.get("codigo_pedido", "").upper() == intent["order_code"]),
            None,
        )
    if intent.get("claim_code"):
        context["matched_claim"] = next(
            (item for item in claims if item.get("codigo_reclamo", "").upper() == intent["claim_code"]),
            None,
        )
    return context


def deterministic_response(intent: dict[str, Any], context: dict[str, Any]) -> str | None:
    name = str(context.get("user_name") or "Cliente").split()[0]
    kind = intent["name"]
    if kind == "order_count":
        total = context["total_orders"]
        return f"{name}, has realizado {total} pedido{'s' if total != 1 else ''} en la plataforma." if total else "No tienes pedidos registrados todavía. Puedes empezar explorando Restaurantes."
    if kind == "recent_orders":
        orders = context["recent_orders"]
        return "Tus pedidos más recientes son: " + ", ".join(f"{item['codigo_pedido']} de {item['tienda_nombre']}" for item in orders) + "." if orders else "No tienes pedidos registrados todavía."
    if kind == "orders_in_transit":
        total = context["orders_in_transit"]
        return f"Tienes {total} pedido{'s' if total != 1 else ''} en camino." if total else "No tienes pedidos en camino actualmente."
    if kind == "last_order":
        order = context["last_order"]
        return f"Tu último pedido fue {order['codigo_pedido']} de {order['tienda_nombre']}, por S/ {float(order['total']):.2f}, y su estado es {order['estado']}." if order else "No tienes pedidos registrados todavía."
    if kind == "order_status":
        order = context.get("matched_order") if intent.get("order_code") else context["last_order"]
        return f"El pedido {order['codigo_pedido']} de {order['tienda_nombre']} está en estado {order['estado']}." if order else "No encontré un pedido tuyo que coincida con esa consulta."
    if kind == "claim_count":
        return f"{name}, tienes {context['total_claims']} reclamo{'s' if context['total_claims'] != 1 else ''} registrado{'s' if context['total_claims'] != 1 else ''}."
    if kind == "open_claims":
        claim = context["recent_open_claim"]
        return f"Tienes {context['open_claims']} reclamo{'s' if context['open_claims'] != 1 else ''} abierto{'s' if context['open_claims'] != 1 else ''}. El más reciente es {claim['codigo_reclamo']} y está en estado {claim['estado']}." if claim else "Tienes 0 reclamos abiertos actualmente."
    if kind == "claim_status":
        claim = context.get("matched_claim") or context["last_claim"]
        return f"Tu reclamo {claim['codigo_reclamo']}, asociado al pedido {claim['codigo_pedido']}, está en estado {claim['estado']}." if claim else "No encontré reclamos registrados para esa consulta."
    if kind == "notifications":
        return f"Tienes {context['unread_notifications']} notificación{'es' if context['unread_notifications'] != 1 else ''} sin leer. Puedes abrirlas desde la campana superior."
    if kind == "cart_summary":
        cart = context.get("cart")
        if cart is None:
            return "No pude acceder al carrito desde esta consulta. Abre la sección Carrito para revisarlo."
        quantity = int(cart.get("quantity") or 0)
        subtotal = float(cart.get("subtotal") or 0)
        return f"Tienes {quantity} producto{'s' if quantity != 1 else ''} en el carrito, con subtotal de S/ {subtotal:.2f}." if quantity else "Tu carrito está vacío."
    if kind == "how_to_order":
        return "Abre Restaurantes, agrega productos al carrito y entra a Carrito para continuar al pago."
    if kind == "how_to_claim":
        return "Desde Mis pedidos abre el pedido afectado y selecciona reportar problema. También puedes entrar a Mis reclamos y crear uno nuevo."
    if kind == "sensitive_problem":
        return "Te recomiendo crear o continuar un reclamo con soporte. El equipo debe validar el pedido y no se confirmarán devoluciones automáticamente."
    if kind == "logout_help":
        return "Puedes cerrar sesión desde el botón Salir o desde el menú de tu avatar."
    if kind == "support_help":
        return "Puedes contactar a soporte creando un reclamo o respondiendo dentro de la conversación de un reclamo abierto."
    return None


@traced_chat
def answer_chat(message: str, user: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
    history = _conversation(context)
    recommended = _recommendations(message, history)
    if recommended:
        return recommended
    intent = detect_chat_intent(message)
    procedural = is_procedural_question(message)
    # A question about how to consult a status is not a request for personal status.
    if procedural and not intent["order_code"] and not intent["claim_code"]:
        faq = find_faq(message)
        if faq:
            trace_update(route="FAQ", retrieval_strategy="faq_terms", document_count=1)
            return {"message": faq["contenido"], "intent": "faq", "provider": "faq",
                    "documents": [faq["titulo"]],
                    "sources": [{"id": faq["id_documento"], "title": faq["titulo"],
                                 "score": faq["score"]}]}
        trace_append("fallback_reasons", "no_confident_faq_match")
        if intent["requires_auth"]:
            intent = {**intent, "name": "general", "requires_auth": False}
    if intent["requires_auth"] and not user:
        trace_append("fallback_reasons", "authentication_required")
        return {
            "message": "Para consultar tus pedidos, reclamos, carrito o notificaciones necesitas iniciar sesión.",
            "intent": intent["name"],
            "provider": "local",
            "documents": [],
        }

    user_context = build_user_context(user, intent, context) if user else {}
    direct = deterministic_response(intent, user_context)
    if direct:
        trace_update(route="atencion_humana" if intent["name"] == "sensitive_problem" else "consulta_directa")
        if intent["name"] == "sensitive_problem":
            trace_update(human_review_required=True)
            trace_append("fallback_reasons", "sensitive_problem")
        return {"message": direct, "intent": intent["name"], "provider": "local", "documents": []}

    documents = recuperar_documentos(message, None, max_docs=3)
    fallback = "Puedo recomendar platos del catálogo, orientarte para comprar o ayudarte con tus pedidos. ¿Qué te gustaría hacer?"
    if not os.getenv("OPENAI_API_KEY"):
        trace_append("fallback_reasons", "openai_not_configured")
        return {"message": fallback, "intent": intent["name"], "provider": "local", "documents": []}

    try:
        from openai import OpenAI

        safe_context = json.dumps(user_context, ensure_ascii=False, default=str)
        conversation = json.dumps(history, ensure_ascii=False)
        knowledge = "\n\n".join(
            f"{doc.get('titulo')}: {doc.get('fragmento') or doc.get('contenido')}"
            for doc in documents
        )
        trace_update(openai_used=True)
        response = OpenAI(timeout=20.0, max_retries=1).responses.create(
            model=os.getenv("OPENAI_CHAT_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini")),
            instructions=(
                "Eres el asistente virtual de SmartClaim AI. Responde de forma clara, breve y amable. "
                "Usa únicamente los datos del contexto entregado por el backend. No inventes cantidades, "
                "estados, nombres, montos ni fechas. No uses placeholders. Si faltan datos, dilo claramente. "
                "No prometas devoluciones, cupones ni compensaciones automáticas."
                " No confirmes pagos o entregas reales ni comunicaciones automáticas: esta es una demostración sin esas integraciones."
            ),
            input=f"Consulta: {message}\nHistorial reciente: {conversation}\nDatos reales: {safe_context}\nDocumentos internos:\n{knowledge}",
        )
        text = response.output_text.strip()
        if "[" in text and "]" in text:
            return {"message": fallback, "intent": intent["name"], "provider": "local_fallback", "documents": []}
        trace_update(generation_strategy="openai")
        return {"message": text, "intent": intent["name"], "provider": "openai", "documents": [doc.get("titulo") for doc in documents]}
    except Exception:
        trace_append("fallback_reasons", "chat_generation_unavailable")
        logger.warning("Generación del chatbot no disponible; se utiliza respuesta local")
        return {"message": fallback, "intent": intent["name"], "provider": "local_fallback", "documents": []}
