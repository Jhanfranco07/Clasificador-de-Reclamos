import json
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from database import db_connection as db
from database import repositories as repo
from modules import rag_engine as rag
from modules.ai_trace import AITrace


@pytest.fixture
def knowledge():
    db.init_db()
    refund = repo.crear_documento_base(
        "FAQ: ¿Cómo solicito un reembolso?", "FAQ", "Cobro indebido",
        "Solicita la revisión del cobro desde el detalle de tu pedido. El equipo validará el caso antes de confirmar un reembolso.",
    )
    delay = repo.crear_documento_base(
        "Política de entrega volcánica", "POLITICA", "Retraso de pedido",
        "La entrega volcánica con retraso o demora requiere revisar el pedido con el equipo de reparto.",
    )
    charge = repo.crear_documento_base(
        "Política de pagos volcánica", "POLITICA", "Cobro indebido",
        "La entrega volcánica con cobro duplicado requiere revisar los pagos y la devolución.",
    )
    return refund, delay, charge


def test_direct_faq_skips_classifier_rag_and_openai(knowledge, monkeypatch):
    from modules import chatbot_service as chat, classifier
    from modules import openai_embeddings as embeddings
    import openai
    monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")
    classifier_spy = Mock(side_effect=AssertionError("ML must not run"))
    rag_spy = Mock(side_effect=AssertionError("RAG must not run"))
    model_spy = Mock(side_effect=AssertionError("OpenAI must not run"))
    embeddings_spy = Mock(side_effect=AssertionError("Embeddings must not run"))
    monkeypatch.setattr(classifier, "clasificar_reclamo", classifier_spy)
    monkeypatch.setattr(chat, "recuperar_documentos", rag_spy)
    monkeypatch.setattr(openai, "OpenAI", model_spy)
    monkeypatch.setattr(embeddings, "create_embeddings", embeddings_spy)
    result = chat.answer_chat("¿Cómo solicito un reembolso?")
    assert result["provider"] == "faq"
    assert result["sources"][0]["id"] == knowledge[0]
    assert result["message"] == db.fetch_one(
        "SELECT contenido FROM documentos_base WHERE id_documento = ?", (knowledge[0],)
    )["contenido"]
    assert result["trace"]["route"] == "FAQ"
    assert result["trace"]["ml_executed"] is False
    assert result["trace"]["rag_executed"] is False
    assert result["trace"]["openai_used"] is False
    classifier_spy.assert_not_called()
    rag_spy.assert_not_called()
    model_spy.assert_not_called()
    embeddings_spy.assert_not_called()
    assert result["trace"]["duration_ms"] >= 0


def test_unknown_faq_never_creates_claim_or_match(knowledge):
    from modules.chatbot_service import answer_chat
    before = repo.contar_reclamos()
    result = answer_chat("¿Cuáles son los horarios de atención en Marte?")
    assert result["provider"] != "faq"
    assert result["trace"]["ml_executed"] is False
    assert "no_confident_faq_match" in result["trace"]["fallback_reasons"]
    assert repo.contar_reclamos() == before


def test_faq_threshold_and_inactive_documents(knowledge, monkeypatch):
    from modules.faq_router import find_faq
    assert find_faq("¿Cómo solicito un reembolso?")
    repo.desactivar_documento_base(knowledge[0])
    assert find_faq("¿Cómo solicito un reembolso?") is None
    monkeypatch.setenv("FAQ_MATCH_THRESHOLD", "1.5")
    with pytest.raises(ValueError):
        find_faq("¿Cómo solicito un reembolso?")


def test_non_question_is_not_faq(knowledge):
    from modules.faq_router import find_faq
    assert find_faq("Me cobraron dos veces y solicito un reembolso") is None


@pytest.mark.parametrize("category", ["Retraso de pedido", "Cobro indebido"])
def test_tfidf_filter_applies_before_ranking(knowledge, category):
    rag.construir_indice_vectorial(forzar=True)
    with AITrace("test") as trace:
        result = rag.recuperar_documentos("entrega volcánica", category, max_docs=10, confianza=0.99)
    assert result
    assert all(doc["categoria_asociada"] == category for doc in result)
    assert trace.data["category"] == category
    assert trace.data["retrieval_strategy"] == "tfidf"
    assert all(doc["id_documento"] and doc["fragmento"] for doc in result)


@pytest.mark.parametrize("category,confidence,reason", [
    ("Retraso de pedido", 0.3, "low_classification_confidence"),
    ("Categoría inexistente", 0.99, "unknown_category"),
    ("Problema con tarjeta", 0.99, "insufficient_category_documents"),
])
def test_general_retrieval_for_ambiguous_or_missing_category(knowledge, category, confidence, reason):
    # Remove documents only in the isolated database to exercise missing coverage.
    db.execute("UPDATE documentos_base SET activo = 0 WHERE categoria_asociada = ?", ("Problema con tarjeta",))
    rag.construir_indice_vectorial(forzar=True)
    with AITrace("test") as trace:
        result = rag.recuperar_documentos("entrega volcánica", category, max_docs=20, confianza=confidence)
    assert result
    assert trace.data["category"] is None
    assert reason in trace.data["fallback_reasons"]


def test_semantic_failure_retains_tfidf_category_filter(knowledge, monkeypatch):
    from modules import openai_embeddings as embeddings
    monkeypatch.setattr(embeddings, "search", Mock(side_effect=RuntimeError("offline")))
    rag.construir_indice_vectorial(forzar=True)
    with AITrace("test") as trace:
        result = rag.recuperar_documentos("entrega volcánica", "Cobro indebido", confianza=0.99)
    assert result and all(doc["categoria_asociada"] == "Cobro indebido" for doc in result)
    assert "openai_json_unavailable" in trace.data["fallback_reasons"]


def test_empty_similarity_does_not_return_arbitrary_documents(knowledge):
    rag.construir_indice_vectorial(forzar=True)
    with AITrace("test") as trace:
        assert rag.recuperar_documentos("zzzyyyxxx", "Cobro indebido", confianza=0.99) == []
    assert "no_relevant_category_results" in trace.data["fallback_reasons"]
    assert trace.data["category"] is None


def test_json_embeddings_filter_candidates_before_scoring(knowledge, monkeypatch):
    from modules import openai_embeddings as embeddings
    monkeypatch.setenv("OPENAI_API_KEY", "fake-test-key")
    monkeypatch.setenv("USE_OPENAI_EMBEDDINGS", "true")
    def item(doc_id, category):
        return dict(id=str(doc_id), document_id=doc_id, fragment_id=doc_id,
                    title="Test", type="POLITICA", category=category, content="Test content",
                    embedding=[1.0, 0.0], model=embeddings.MODEL)
    monkeypatch.setattr(embeddings, "load_index", lambda: {"items": [
        item(knowledge[1], "Retraso de pedido"), item(knowledge[2], "Cobro indebido"),
        item(9999, "Cobro indebido"),
    ]})
    monkeypatch.setattr(embeddings, "listar_fragmentos_documento", lambda: [dict(
        id_fragmento=knowledge[2], id_documento=knowledge[2], texto_fragmento="Test content",
        titulo="Test", categoria_asociada="Cobro indebido",
    )])
    monkeypatch.setattr(embeddings, "create_embeddings", lambda texts: [[1.0, 0.0]])
    result = embeddings.search("entrega", category="Cobro indebido", document_ids=[knowledge[2]])
    assert [doc["id_documento"] for doc in result] == [knowledge[2]]


def test_pgvector_sql_is_parameterized_and_filters_active_documents(monkeypatch):
    query = Mock(return_value=[])
    monkeypatch.setattr(repo, "fetch_all", query)
    repo.buscar_embeddings_rag([0.1, 0.2], categoria="Cobro indebido", document_ids=[2, 3])
    sql, params = query.call_args.args
    assert "db.activo = 1" in sql
    assert "db.categoria_asociada = ?" in sql
    assert "db.id_documento IN (?,?)" in sql
    assert sql.index("WHERE") < sql.index("ORDER BY")
    assert "Cobro indebido" not in sql
    assert params[1:4] == ("Cobro indebido", 2, 3)


def test_pgvector_failure_retains_scope(knowledge, monkeypatch):
    from modules import openai_embeddings as embeddings
    rag.construir_indice_vectorial(forzar=True)
    monkeypatch.setattr(rag, "using_postgres", lambda: True)
    monkeypatch.setattr(rag, "_pgvector_habilitado", lambda: True)
    monkeypatch.setattr(rag, "contar_embeddings_rag", lambda: 1)
    monkeypatch.setattr(embeddings, "create_embeddings", lambda texts: [[0.1, 0.2]])
    monkeypatch.setattr(rag, "buscar_embeddings_rag", Mock(side_effect=RuntimeError("offline")))
    with AITrace("test") as trace:
        result = rag.recuperar_documentos("entrega volcánica", "Retraso de pedido", confianza=0.99)
    assert result and all(doc["categoria_asociada"] == "Retraso de pedido" for doc in result)
    assert "pgvector_unavailable" in trace.data["fallback_reasons"]


def test_telemetry_contains_no_input_or_personal_data(knowledge):
    from modules.chatbot_service import answer_chat
    result = answer_chat("¿Cómo solicito un reembolso? correo privado@example.com token-secret")
    logs = db.fetch_all("SELECT detalle FROM logs_sistema WHERE modulo = 'Flujo IA'")
    assert logs
    for log in logs:
        assert "privado@example.com" not in log["detalle"]
        assert "token-secret" not in log["detalle"]
        assert "duration_ms" in json.loads(log["detalle"])


@pytest.fixture
def api():
    from backend.main import app
    with TestClient(app) as client:
        yield client


def headers(client, role="CLIENT"):
    emails = {"CLIENT": "jhan.perez@gmail.com", "AGENT": "gonzalo.caceres@smartclaim.com",
              "ADMIN": "admin@smartclaim.com"}
    response = client.post("/api/auth/login", json={"email": emails[role], "password": "123456"})
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["token"]}


@pytest.mark.parametrize("description,category", [
    ("Mi pedido llegó con dos horas de retraso", "Retraso de pedido"),
    ("Me cobraron dos veces el mismo pedido", "Cobro indebido"),
    ("¿Cómo solicito un reembolso?", None),
])
def test_formal_claim_keeps_ml_human_review_and_evidence(api, description, category):
    response = api.post("/api/claims", headers=headers(api), json={
        "customer_name": "Jhan Perez", "customer_email": "jhan.perez@gmail.com",
        "order_code": api.get("/api/orders", headers=headers(api)).json()["items"][0]["code"], "description": description, "analyze": True,
    })
    assert response.status_code == 201
    public = response.json()
    assert public["analysis"] is None and public["response"] is None
    detail = api.get("/api/claims/" + public["claim"]["id"], headers=headers(api, "AGENT")).json()
    assert detail["analysis"] and detail["response"]
    if category:
        assert detail["analysis"]["category"] == category
    assert detail["claim"]["requiresHumanReview"] is True
    assert detail["claim"]["statusKey"] != "CLOSED"
    trace = json.loads(db.fetch_one(
        "SELECT detalle FROM logs_sistema WHERE modulo = 'Flujo IA' AND id_reclamo = ? ORDER BY id_log DESC",
        (int(detail["claim"]["id"]),),
    )["detalle"])
    assert trace["ml_executed"] is True
    assert trace["rag_executed"] is True
    assert trace["route"] == "atencion_humana"
    if detail["documents"]:
        assert db.fetch_one("SELECT COUNT(*) AS total FROM documentos_consultados")["total"] > 0


def test_admin_document_and_catalog_regression(api):
    admin = headers(api, "ADMIN")
    assert api.get("/api/catalog").json()["items"]
    created = api.post("/api/documents", headers=admin, json={
        "title": "FAQ: ¿Cuáles son los horarios de atención?", "type": "FAQ",
        "category": "Soporte general", "content": "El horario de atención de prueba es de lunes a viernes.",
    })
    assert created.status_code == 201
    chat = api.post("/api/chat", json={"message": "¿Cuáles son los horarios de atención?"})
    assert chat.status_code == 200 and chat.json()["provider"] == "faq"
    assert api.get("/api/documents", headers=admin).status_code == 200
    assert api.get("/api/dashboard", headers=admin).status_code == 200
    assert api.get("/api/reports", headers=admin).status_code == 200


def test_edit_and_deactivate_refreshes_retrieval(knowledge):
    rag.construir_indice_vectorial(forzar=True)
    repo.actualizar_documento_base(knowledge[2], "Política de pagos actualizada", "POLITICA",
                                 "Cobro indebido", "El concepto unicorniosazules requiere validación del área de pagos.")
    rag.construir_indice_vectorial(forzar=True)
    results = rag.recuperar_documentos("unicorniosazules", "Cobro indebido", confianza=0.99)
    assert results and results[0]["id_documento"] == knowledge[2]
    assert "unicorniosazules" in results[0]["contenido"]
    repo.desactivar_documento_base(knowledge[2])
    rag.construir_indice_vectorial(forzar=True)
    assert rag.recuperar_documentos("unicorniosazules", "Cobro indebido", confianza=0.99) == []


def test_claim_edit_approve_close_reopen_regression(api):
    client_headers = headers(api)
    agent_headers = headers(api, "AGENT")
    detail = api.post("/api/claims", headers=client_headers, json={
        "customer_name": "Jhan Perez", "customer_email": "jhan.perez@gmail.com",
        "order_code": api.get("/api/orders", headers=client_headers).json()["items"][0]["code"], "description": "Me cobraron dos veces el mismo pedido",
    }).json()
    claim_id = detail["claim"]["id"]
    detail = api.get(f"/api/claims/{claim_id}", headers=agent_headers).json()
    response_id = detail["response"]["id"]
    edited = "Revisaremos el cobro duplicado antes de confirmar una solución."
    assert api.patch(f"/api/responses/{response_id}", headers=client_headers,
                     json={"response_text": edited}).status_code == 403
    assert api.patch(f"/api/responses/{response_id}", headers=agent_headers,
                     json={"response_text": edited}).status_code == 200
    approved = api.post(f"/api/responses/{response_id}/approve", headers=agent_headers,
                        json={"response_text": edited})
    assert approved.status_code == 200
    assert approved.json()["claim"]["statusKey"] == "RESPONDED"
    assert "Gonzalo" in approved.json()["response"]["finalResponse"]
    assert api.post(f"/api/claims/{claim_id}/close", headers=agent_headers, json={"comment": "Cierre administrativo documentado"}).json()["claim"]["statusKey"] == "CLOSED"
    assert api.post(f"/api/claims/{claim_id}/reopen", headers=client_headers).json()["claim"]["statusKey"] != "CLOSED"


def test_pgvector_success_receives_category_and_ids(knowledge, monkeypatch):
    from modules import openai_embeddings as embeddings
    rag.construir_indice_vectorial(forzar=True)
    monkeypatch.setattr(rag, "using_postgres", lambda: True)
    monkeypatch.setattr(rag, "_pgvector_habilitado", lambda: True)
    monkeypatch.setattr(rag, "contar_embeddings_rag", lambda: 1)
    monkeypatch.setattr(embeddings, "create_embeddings", lambda texts: [[0.1, 0.2]])
    fragment = next(row for row in repo.listar_fragmentos_documento() if row["id_documento"] == knowledge[2])
    search = Mock(return_value=[{**fragment, "score": 0.92, "modelo_embedding": embeddings.MODEL}])
    monkeypatch.setattr(rag, "buscar_embeddings_rag", search)
    with AITrace("test") as trace:
        results = rag.recuperar_documentos("cobro duplicado", "Cobro indebido", confianza=0.99)
    assert results[0]["vector_store"] == "supabase_pgvector"
    assert search.call_args.kwargs["categoria"] == "Cobro indebido"
    assert knowledge[2] in search.call_args.kwargs["document_ids"]
    assert knowledge[1] not in search.call_args.kwargs["document_ids"]
    assert trace.data["retrieval_strategy"] == "pgvector"


def test_minimum_coverage_broadens_explicitly(knowledge, monkeypatch):
    monkeypatch.setenv("RAG_MIN_CATEGORY_DOCUMENTS", "100")
    rag.construir_indice_vectorial(forzar=True)
    with AITrace("test") as trace:
        result = rag.recuperar_documentos("entrega volcánica", "Cobro indebido", confianza=0.99)
    assert result
    assert trace.data["category"] is None
    assert "insufficient_category_documents" in trace.data["fallback_reasons"]
