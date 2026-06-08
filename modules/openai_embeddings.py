from __future__ import annotations

import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from database.repositories import listar_fragmentos_documento

BASE_DIR = Path(__file__).resolve().parent.parent
INDEX_PATH = BASE_DIR / "vector_store" / "openai_embeddings.json"
MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")


def enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY")) and os.getenv(
        "USE_OPENAI_EMBEDDINGS", "true"
    ).lower() in {"1", "true", "yes", "on"}


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def create_embeddings(texts: list[str]) -> list[list[float]]:
    if not enabled():
        raise RuntimeError("OpenAI embeddings no están habilitados.")
    from openai import OpenAI

    response = OpenAI(timeout=30.0, max_retries=1).embeddings.create(
        model=MODEL,
        input=texts,
    )
    return [[float(value) for value in item.embedding] for item in response.data]


def load_index() -> dict[str, Any]:
    if not INDEX_PATH.exists():
        return {"model": MODEL, "items": []}
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def build_index() -> dict[str, Any]:
    if not enabled():
        return {"status": "disabled", "model": MODEL, "items": 0}

    existing = {
        item["id"]: item
        for item in load_index().get("items", [])
        if item.get("model") == MODEL
    }
    fragments = listar_fragmentos_documento()
    output: list[dict[str, Any]] = []
    pending: list[tuple[dict[str, Any], str, str]] = []

    for fragment in fragments:
        text = " ".join(
            [
                str(fragment.get("titulo") or ""),
                str(fragment.get("categoria_asociada") or ""),
                str(fragment.get("texto_fragmento") or ""),
            ]
        ).strip()
        item_id = f"doc_{fragment['id_documento']}_frag_{fragment['id_fragmento']}"
        digest = content_hash(text)
        cached = existing.get(item_id)
        if cached and cached.get("content_hash") == digest:
            output.append(cached)
        else:
            pending.append((fragment, text, digest))

    for offset in range(0, len(pending), 50):
        batch = pending[offset : offset + 50]
        vectors = create_embeddings([item[1] for item in batch])
        for (fragment, text, digest), vector in zip(batch, vectors):
            output.append(
                {
                    "id": f"doc_{fragment['id_documento']}_frag_{fragment['id_fragmento']}",
                    "document_id": fragment["id_documento"],
                    "fragment_id": fragment["id_fragmento"],
                    "title": fragment.get("titulo"),
                    "category": fragment.get("categoria_asociada"),
                    "type": fragment.get("tipo_documento"),
                    "content": fragment.get("texto_fragmento"),
                    "source": "documentos_base",
                    "content_hash": digest,
                    "model": MODEL,
                    "embedding": vector,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            )

    INDEX_PATH.parent.mkdir(parents=True, exist_ok=True)
    INDEX_PATH.write_text(
        json.dumps({"model": MODEL, "items": output}, ensure_ascii=False),
        encoding="utf-8",
    )
    return {
        "status": "updated",
        "model": MODEL,
        "items": len(output),
        "generated": len(pending),
        "path": str(INDEX_PATH),
    }


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    return dot / (left_norm * right_norm) if left_norm and right_norm else 0.0


def search(query: str, top_k: int = 5, threshold: float = 0.7) -> list[dict[str, Any]]:
    index = load_index()
    items = index.get("items", [])
    if not enabled() or not items:
        return []
    query_vector = create_embeddings([query])[0]
    ranked = sorted(
        ((item, _cosine(query_vector, item["embedding"])) for item in items),
        key=lambda pair: pair[1],
        reverse=True,
    )
    return [
        {
            "id_documento": item["document_id"],
            "id_fragmento": item["fragment_id"],
            "titulo": item["title"],
            "tipo_documento": item["type"],
            "categoria_asociada": item["category"],
            "contenido": item["content"],
            "fragmento": item["content"],
            "score": round(score, 4),
            "embedding_id": item["id"],
            "modelo_embedding": item["model"],
            "vector_store": "openai_json",
        }
        for item, score in ranked[:top_k]
        if score >= threshold
    ]
