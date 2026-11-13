"""Lightweight FAQ matching over the existing active knowledge documents."""
import os

from database.db_connection import fetch_all
from modules.text_processing import normalizar_texto

_STOP = set("como puedo puede podemos cual cuales que el la los las un una unos unas de del "
            "a al en por para con mi mis me se es son y o sobre faq preguntas frecuentes "
            "solicitar solicito solicitarlo hacer hago consultar consulto saber obtener".split())


def _terms(text):
    aliases = {"reembols": "reembolso", "devoluc": "reembolso", "horari": "horario",
               "contact": "contacto", "comunicar": "contacto"}
    result = set()
    for word in normalizar_texto(text).split():
        if word in _STOP or len(word) < 3:
            continue
        result.add(next((value for prefix, value in aliases.items() if word.startswith(prefix)), word))
    return result


def is_procedural_question(message):
    text = normalizar_texto(message).strip()
    return text.startswith(("como ", "cuales son ", "cual es el horario", "que horarios", "donde puedo "))


def find_faq(message):
    """Return verbatim knowledge and provenance only above the configured threshold."""
    if not is_procedural_question(message):
        return None
    query = _terms(message)
    if not query:
        return None
    threshold = float(os.getenv("FAQ_MATCH_THRESHOLD", "0.85"))
    if not 0 <= threshold <= 1:
        raise ValueError("FAQ_MATCH_THRESHOLD debe estar entre 0 y 1")
    documents = fetch_all("""
        SELECT id_documento, titulo, contenido, categoria_asociada
        FROM documentos_base WHERE activo = 1 AND tipo_documento = 'FAQ'
        ORDER BY id_documento
    """)
    best = None
    for doc in documents:
        title_terms = _terms(doc["titulo"])
        content_terms = title_terms | _terms(doc["contenido"])
        score = (0.75 * len(query & content_terms) + 0.25 * len(query & title_terms)) / len(query)
        if score >= threshold and (best is None or score > best["score"]):
            best = {**doc, "score": round(score, 4)}
    return best
