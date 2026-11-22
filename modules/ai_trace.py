"""Request-local, content-free AI telemetry, persisted in the existing audit log."""
from contextvars import ContextVar
import json
import logging
from time import perf_counter

from database.repositories import registrar_log

logger = logging.getLogger(__name__)
_current = ContextVar("ai_trace", default=None)


def trace_update(**values):
    trace = _current.get()
    if trace is not None:
        trace.update(values)


def trace_append(field, value):
    trace = _current.get()
    if trace is not None and value not in trace[field]:
        trace[field].append(value)


class AITrace:
    def __init__(self, route, claim_id=None):
        self.claim_id = claim_id
        self.data = dict(version=1, route=route, ml_executed=False,
                         rag_executed=False, openai_used=False,
                         retrieval_strategy=None, category=None, document_count=0,
                         classification_category=None, classification_confidence=None,
                         human_review_required=False, generation_strategy=None,
                         fallback_reasons=[], retrieval_attempts=[])

    def __enter__(self):
        self.started = perf_counter()
        self.token = _current.set(self.data)
        return self

    def __exit__(self, exc_type, exc, tb):
        self.data["duration_ms"] = round((perf_counter() - self.started) * 1000, 3)
        self.data["outcome"] = "error" if exc_type else "ok"
        _current.reset(self.token)
        # Only controlled fields: never query text, tokens, prompts or exception bodies.
        try:
            registrar_log("Flujo IA", "request_completed", detalle=json.dumps(self.data),
                          id_reclamo=self.claim_id)
        except Exception:
            logger.warning("No se pudo persistir la métrica del flujo IA")


def traced_chat(function):
    from functools import wraps

    @wraps(function)
    def wrapped(*args, **kwargs):
        with AITrace("consulta") as trace:
            result = function(*args, **kwargs)
        # Include timing/outcome added on context exit without exposing mutable context.
        result["trace"] = dict(trace.data)
        return result
    return wrapped
