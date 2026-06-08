from __future__ import annotations

import json
import logging
import os
import re
import unicodedata
from typing import Any

from database.repositories import (
    listar_notificaciones,
    listar_pedidos_por_correo,
    listar_reclamos_por_correo,
)
from modules.rag_engine import recuperar_documentos

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


def _normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in value if not unicodedata.combining(char))


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
        order = context.get("matched_order") or context["last_order"]
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


def answer_chat(message: str, user: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
    intent = detect_chat_intent(message)
    if intent["requires_auth"] and not user:
        return {
            "message": "Para consultar tus pedidos, reclamos, carrito o notificaciones necesitas iniciar sesión.",
            "intent": intent["name"],
            "provider": "local",
            "documents": [],
        }

    user_context = build_user_context(user, intent, context) if user else {}
    direct = deterministic_response(intent, user_context)
    if direct:
        return {"message": direct, "intent": intent["name"], "provider": "local", "documents": []}

    documents = recuperar_documentos(message, "Soporte general", max_docs=3)
    fallback = "Puedo ayudarte con pedidos, pagos, reclamos y uso de la plataforma."
    if not os.getenv("OPENAI_API_KEY"):
        return {"message": fallback, "intent": intent["name"], "provider": "local", "documents": []}

    try:
        from openai import OpenAI

        safe_context = json.dumps(user_context, ensure_ascii=False, default=str)
        knowledge = "\n\n".join(
            f"{doc.get('titulo')}: {doc.get('fragmento') or doc.get('contenido')}"
            for doc in documents
        )
        response = OpenAI(timeout=20.0, max_retries=1).responses.create(
            model=os.getenv("OPENAI_CHAT_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini")),
            instructions=(
                "Eres el asistente virtual de SmartClaim AI. Responde de forma clara, breve y amable. "
                "Usa únicamente los datos del contexto entregado por el backend. No inventes cantidades, "
                "estados, nombres, montos ni fechas. No uses placeholders. Si faltan datos, dilo claramente. "
                "No prometas devoluciones, cupones ni compensaciones automáticas."
            ),
            input=f"Consulta: {message}\nDatos reales: {safe_context}\nDocumentos internos:\n{knowledge}",
        )
        text = response.output_text.strip()
        if "[" in text and "]" in text:
            return {"message": fallback, "intent": intent["name"], "provider": "local_fallback", "documents": []}
        return {"message": text, "intent": intent["name"], "provider": "openai", "documents": [doc.get("titulo") for doc in documents]}
    except Exception:
        logger.exception("Falló la respuesta OpenAI del chatbot; se utilizará respuesta local")
        return {"message": fallback, "intent": intent["name"], "provider": "local_fallback", "documents": []}
