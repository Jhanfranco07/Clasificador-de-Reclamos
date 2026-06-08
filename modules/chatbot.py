from __future__ import annotations

import os
from typing import Any

from modules.rag_engine import recuperar_documentos


def answer_chat(message: str, user: dict[str, Any] | None = None, context: dict[str, Any] | None = None) -> dict[str, Any]:
    documents = recuperar_documentos(message, "Soporte general", max_docs=3)
    authenticated = bool(user)
    fallback = (
        "Puedo orientarte sobre pedidos, pagos y reclamos. "
        + (
            "Desde Mis pedidos puedes revisar un pedido y reportar un problema."
            if authenticated
            else "Para consultar un pedido o registrar un reclamo, inicia sesión."
        )
    )
    if not os.getenv("OPENAI_API_KEY"):
        return {"message": fallback, "documents": [], "provider": "local"}

    try:
        from openai import OpenAI

        knowledge = "\n\n".join(
            f"{doc.get('titulo')}: {doc.get('fragmento') or doc.get('contenido')}"
            for doc in documents
        )
        response = OpenAI(timeout=20.0, max_retries=1).responses.create(
            model=os.getenv("OPENAI_CHAT_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini")),
            instructions=(
                "Eres el asistente de ayuda de una plataforma de delivery. Responde breve y claramente. "
                "No prometas reembolsos, cupones ni compensaciones. No pidas datos sensibles. "
                "Si el usuario necesita consultar datos personales y no está autenticado, pídele iniciar sesión."
            ),
            input=(
                f"Usuario autenticado: {authenticated}\n"
                f"Consulta: {message}\n"
                f"Contexto adicional: {context or {}}\n"
                f"Documentos internos:\n{knowledge or 'Sin contexto documental.'}"
            ),
        )
        return {
            "message": response.output_text.strip(),
            "documents": [doc.get("titulo") for doc in documents],
            "provider": "openai",
        }
    except Exception:
        return {"message": fallback, "documents": [], "provider": "local_fallback"}
