"""Offline safety probes and validation of real local paths vs deterministic stubs."""
import json
import socket
from types import SimpleNamespace
from unittest.mock import Mock

import joblib
import pytest
from fastapi.testclient import TestClient
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression

from database import db_connection as db
from database import repositories as repo
from modules import classifier, rag_engine as rag
from modules.ai_trace import AITrace


@pytest.mark.parametrize("name", ["OpenAI", "AsyncOpenAI", "Client", "AsyncClient", "AzureOpenAI", "AsyncAzureOpenAI"])
def test_all_model_clients_are_blocked(name, external_guard):
    import openai
    with external_guard.expect_blocked("model_client"):
        getattr(openai, name)(api_key="fake-test-key")


@pytest.mark.parametrize("name", ["connect", "Connection", "AsyncConnection"])
def test_postgres_connections_are_blocked(name, external_guard):
    import psycopg
    method = psycopg.connect if name == "connect" else getattr(psycopg, name).connect
    with external_guard.expect_blocked("postgres"):
        method("postgresql://test.invalid/isolated")


def test_dns_is_blocked(external_guard):
    with external_guard.expect_blocked("dns"):
        socket.getaddrinfo("test.invalid", 443)


@pytest.mark.parametrize("method", ["connect", "connect_ex"])
def test_direct_sockets_are_blocked(method, external_guard):
    with socket.socket() as sock, external_guard.expect_blocked("socket"):
        getattr(sock, method)(("192.0.2.1", 443))


def test_sync_http_transport_is_blocked(external_guard):
    import httpx
    with external_guard.expect_blocked("http"):
        httpx.HTTPTransport().handle_request(httpx.Request("GET", "https://test.invalid"))


def test_async_http_transport_is_blocked(external_guard):
    import httpx
    with external_guard.expect_blocked("http_async"):
        httpx.AsyncHTTPTransport().handle_async_request(httpx.Request("GET", "https://test.invalid"))


def test_real_model_artifact_contains_tfidf_and_logistic_regression():
    model = joblib.load(classifier.MODEL_PATH)
    assert isinstance(model.named_steps["tfidf"], TfidfVectorizer)
    assert isinstance(model.named_steps["clf"], LogisticRegression)
    result = classifier._predict_with_ml("Me cobraron dos veces el mismo pedido")
    assert result is not None
    assert result[0] in model.classes_
    assert 0 <= result[1] <= 1
    assert abs(sum(model.predict_proba(["cobro duplicado"])[0]) - 1) < 1e-9


@pytest.mark.parametrize("text,category,priority", [
    ("Mi pedido llegó con dos horas de retraso", "Retraso de pedido", "Alta"),
    ("Me cobraron dos veces el mismo pedido", "Cobro indebido", "Alta"),
    ("No reconozco un cobro y reporto fraude en mi cuenta", "Fraude o seguridad", "Crítica"),
])
def test_real_classification_and_priority(text, category, priority):
    result = classifier.clasificar_reclamo(text)
    assert result["categoria"] == category
    assert result["prioridad"] == priority
    assert result["modelo_usado"] != "modelo_reglas_mejorado"


def test_local_template_and_trace_without_model_provider():
    db.init_db()
    analysis = classifier.clasificar_reclamo("Me cobraron dos veces el mismo pedido")
    with AITrace("clasificacion") as trace:
        docs = rag.recuperar_documentos("cobro duplicado", "Cobro indebido", confianza=0.99)
        response = rag.generar_respuesta_sugerida("Cliente de prueba", "ORD-OFFLINE", "Cobro duplicado", analysis, docs)
    assert docs and "ORD-OFFLINE" in response
    assert "documento interno" in response
    assert trace.data["retrieval_strategy"] == "tfidf"
    assert trace.data["generation_strategy"] == "local_template"
    assert trace.data["openai_used"] is False
    saved = json.loads(db.fetch_one("SELECT detalle FROM logs_sistema WHERE modulo = 'Flujo IA' ORDER BY id_log DESC")["detalle"])
    assert saved["generation_strategy"] == "local_template"


@pytest.mark.parametrize("failing", [False, True])
def test_response_generation_with_deterministic_stub(monkeypatch, failing):
    import openai
    db.init_db()
    monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")
    create = Mock(side_effect=RuntimeError("simulated provider failure")) if failing else Mock(
        return_value=SimpleNamespace(output_text="Respuesta simulada para revisión humana."))
    client = Mock(return_value=SimpleNamespace(responses=SimpleNamespace(create=create)))
    monkeypatch.setattr(openai, "OpenAI", client)
    with AITrace("clasificacion") as trace:
        text = rag.generar_respuesta_sugerida("Prueba", "ORD-STUB", "Cobro duplicado",
                                             {"categoria": "Cobro indebido", "prioridad": "Alta"}, [])
    create.assert_called_once()
    assert trace.data["generation_strategy"] == ("local_template" if failing else "openai")
    if failing:
        assert "generation_unavailable" in trace.data["fallback_reasons"]
        assert "ORD-STUB" in text
    else:
        assert text == "Respuesta simulada para revisión humana."


def test_json_index_with_deterministic_embedding_stub(monkeypatch):
    import openai
    from modules import openai_embeddings as embeddings
    db.init_db()
    rag.reconstruir_fragmentos_desde_documentos()
    monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")
    monkeypatch.setenv("USE_OPENAI_EMBEDDINGS", "true")

    def create(*, model, input):
        return SimpleNamespace(data=[SimpleNamespace(embedding=[1.0, 0.0]) for _ in input])

    fake = Mock(side_effect=create)
    monkeypatch.setattr(openai, "OpenAI", Mock(return_value=SimpleNamespace(embeddings=SimpleNamespace(create=fake))))
    result = embeddings.build_index()
    assert result["items"] > 0
    rows = embeddings.search("cobro duplicado", category="Cobro indebido")
    assert rows and all(row["categoria_asociada"] == "Cobro indebido" for row in rows)
    assert all(abs(row["score"] - 1.0) < 1e-9 for row in rows)
    assert fake.call_count >= 2


def test_faq_via_http_bypasses_all_ai(monkeypatch):
    import openai
    import backend.main as backend
    from modules import chatbot_service as chat, openai_embeddings as embeddings
    with TestClient(backend.app) as api:
        repo.crear_documento_base("FAQ: ¿Cómo solicito un reembolso?", "FAQ", "Cobro indebido",
                                 "Solicita revisión desde el detalle del pedido. Un agente validará el cobro.")
        monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")
        spies = [Mock(side_effect=AssertionError("Forbidden on FAQ")) for _ in range(5)]
        monkeypatch.setattr(backend, "clasificar_reclamo", spies[0])
        monkeypatch.setattr(classifier, "_predict_with_ml", spies[1])
        monkeypatch.setattr(chat, "recuperar_documentos", spies[2])
        monkeypatch.setattr(embeddings, "create_embeddings", spies[3])
        monkeypatch.setattr(openai, "OpenAI", spies[4])
        response = api.post("/api/chat", json={"message": "¿Cómo solicito un reembolso?"})
        assert response.status_code == 200 and response.json()["provider"] == "faq"
        assert response.json()["trace"]["ml_executed"] is False
        assert response.json()["trace"]["rag_executed"] is False
        assert response.json()["trace"]["openai_used"] is False
        for spy in spies:
            spy.assert_not_called()
