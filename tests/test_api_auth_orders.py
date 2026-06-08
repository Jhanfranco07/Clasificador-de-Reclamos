import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api_client(monkeypatch, tmp_path):
    import database.db_connection as db_connection
    import modules.rag_engine as rag_engine

    monkeypatch.setattr(db_connection, "DB_PATH", tmp_path / "smartclaim_api_test.db")

    vector_dir = tmp_path / "vector_store"
    monkeypatch.setattr(rag_engine, "VECTOR_DIR", vector_dir)
    monkeypatch.setattr(rag_engine, "VECTORIZER_PATH", vector_dir / "rag_tfidf_vectorizer.joblib")
    monkeypatch.setattr(rag_engine, "MATRIX_PATH", vector_dir / "rag_tfidf_matrix.joblib")
    monkeypatch.setattr(rag_engine, "METADATA_PATH", vector_dir / "rag_metadata.joblib")

    from backend.main import app

    with TestClient(app) as client:
        yield client


def test_auth_orders_claims_and_roles(api_client):
    login = api_client.post(
        "/api/auth/login",
        json={"email": "maria.gonzalez@email.com", "password": "123456"},
    )
    assert login.status_code == 200
    token = login.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    forbidden = api_client.get("/api/dashboard", headers=headers)
    assert forbidden.status_code == 403

    order = api_client.post(
        "/api/orders",
        headers=headers,
        json={
            "store_name": "Burger Palace",
            "store_image": "https://example.com/burger.jpg",
            "payment_method": "Tarjeta",
            "delivery_address": "Av. Primavera 123, Lima",
            "items": [{"name": "Combo clasico", "quantity": 1, "price": 24.5}],
        },
    )
    assert order.status_code == 201
    order_code = order.json()["order"]["code"]

    orders = api_client.get("/api/orders", headers=headers)
    assert orders.status_code == 200
    assert any(item["code"] == order_code for item in orders.json()["items"])

    claim = api_client.post(
        "/api/claims",
        headers=headers,
        json={
            "customer_name": "Maria Gonzalez",
            "customer_email": "maria.gonzalez@email.com",
            "customer_phone": "+51 900 111 222",
            "order_code": order_code,
            "channel": "WEB",
            "description": "Mi pedido llego con mucha demora y necesito una respuesta.",
            "analyze": True,
        },
    )
    assert claim.status_code == 201
    assert claim.json()["claim"]["orderCode"] == order_code

    admin_login = api_client.post(
        "/api/auth/login",
        json={"email": "admin@smartclaim.com", "password": "123456"},
    )
    assert admin_login.status_code == 200
    admin_headers = {"Authorization": f"Bearer {admin_login.json()['token']}"}

    dashboard = api_client.get("/api/dashboard", headers=admin_headers)
    assert dashboard.status_code == 200
    assert dashboard.json()["metrics"]["total"] >= 1


def test_register_creates_client_account(api_client):
    register = api_client.post(
        "/api/auth/register",
        json={
            "name": "Cliente Nuevo",
            "email": "cliente.nuevo@example.com",
            "phone": "+51 955 000 111",
            "password": "123456",
        },
    )
    assert register.status_code == 201
    assert register.json()["user"]["role"] == "CLIENT"

    login = api_client.post(
        "/api/auth/login",
        json={"email": "cliente.nuevo@example.com", "password": "123456"},
    )
    assert login.status_code == 200


def test_claim_continuous_conversation(api_client):
    client_login = api_client.post(
        "/api/auth/login",
        json={"email": "maria.gonzalez@email.com", "password": "123456"},
    )
    client_headers = {"Authorization": f"Bearer {client_login.json()['token']}"}
    claim = api_client.post(
        "/api/claims",
        headers=client_headers,
        json={
            "customer_name": "Maria Gonzalez",
            "customer_email": "maria.gonzalez@email.com",
            "order_code": "ORD-CONVERSATION-001",
            "description": "Mi pedido llegó incompleto y necesito ayuda con el producto faltante.",
            "analyze": False,
        },
    )
    claim_id = claim.json()["claim"]["id"]
    initial = api_client.get(f"/api/claims/{claim_id}/messages", headers=client_headers)
    assert initial.status_code == 200
    assert initial.json()["items"][0]["senderType"] == "client"

    agent_login = api_client.post(
        "/api/auth/login",
        json={"email": "laura.martinez@smartclaim.com", "password": "123456"},
    )
    agent_headers = {"Authorization": f"Bearer {agent_login.json()['token']}"}
    agent_reply = api_client.post(
        f"/api/claims/{claim_id}/messages",
        headers=agent_headers,
        json={"message": "Estamos revisando el producto faltante de tu pedido."},
    )
    assert agent_reply.status_code == 201

    client_reply = api_client.post(
        f"/api/claims/{claim_id}/messages",
        headers=client_headers,
        json={"message": "Gracias. El producto faltante fue una bebida."},
    )
    assert client_reply.status_code == 201
    assert len(client_reply.json()["items"]) == 3


def test_chatbot_works_without_openai_key(api_client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    response = api_client.post("/api/chat", json={"message": "¿Cómo creo un reclamo?"})
    assert response.status_code == 200
    assert response.json()["provider"] == "local"


def test_chatbot_returns_real_authenticated_order_count(api_client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    login = api_client.post(
        "/api/auth/login",
        json={"email": "maria.gonzalez@email.com", "password": "123456"},
    )
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    orders = api_client.get("/api/orders", headers=headers).json()["items"]
    response = api_client.post(
        "/api/chat",
        headers=headers,
        json={"message": "¿Cuántos pedidos he realizado?"},
    )
    text = response.json()["message"]
    assert response.status_code == 200
    assert str(len(orders)) in text
    assert "[" not in text


def test_chatbot_requires_login_for_personal_data(api_client):
    response = api_client.post("/api/chat", json={"message": "¿Cuántos pedidos he realizado?"})
    assert response.status_code == 200
    assert "iniciar sesión" in response.json()["message"]


def test_chatbot_returns_real_open_claim_count(api_client, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    login = api_client.post(
        "/api/auth/login",
        json={"email": "maria.gonzalez@email.com", "password": "123456"},
    )
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    claims = api_client.get("/api/claims", headers=headers).json()["items"]
    open_count = sum(1 for claim in claims if claim["statusKey"] != "CLOSED")
    response = api_client.post(
        "/api/chat",
        headers=headers,
        json={"message": "¿Tengo reclamos abiertos?"},
    )
    assert response.status_code == 200
    assert str(open_count) in response.json()["message"]


def test_chatbot_uses_real_cart_context(api_client):
    login = api_client.post(
        "/api/auth/login",
        json={"email": "maria.gonzalez@email.com", "password": "123456"},
    )
    headers = {"Authorization": f"Bearer {login.json()['token']}"}
    response = api_client.post(
        "/api/chat",
        headers=headers,
        json={
            "message": "¿Cuántos productos tengo en el carrito?",
            "context": {"cart": {"quantity": 3, "subtotal": 47.5}},
        },
    )
    assert response.status_code == 200
    assert "3 productos" in response.json()["message"]
    assert "47.50" in response.json()["message"]


def test_agent_signature_replaces_template_placeholder():
    from backend.main import _firmar_respuesta_agente

    response = _firmar_respuesta_agente(
        "Gracias por contactarnos.\n\nSaludos cordiales,\n[Nombre del agente]\nServicio de Atención al Cliente",
        "Laura Martinez",
    )

    assert "[Nombre del agente]" not in response
    assert "Laura Martinez" in response


def test_agent_signature_is_added_when_missing():
    from backend.main import _firmar_respuesta_agente

    response = _firmar_respuesta_agente("Estamos revisando tu reclamo.", "Admin System")

    assert response.endswith("Saludos cordiales,\nAdmin System\nServicio de Atención al Cliente")


def test_client_message_succeeds_when_notification_fails(api_client, monkeypatch):
    client_login = api_client.post(
        "/api/auth/login",
        json={"email": "maria.gonzalez@email.com", "password": "123456"},
    )
    client_headers = {"Authorization": f"Bearer {client_login.json()['token']}"}
    claim = api_client.post(
        "/api/claims",
        headers=client_headers,
        json={
            "customer_name": "Maria Gonzalez",
            "customer_email": "maria.gonzalez@email.com",
            "order_code": "ORD-NOTIFICATION-FAILURE",
            "description": "Necesito información adicional sobre la respuesta de soporte.",
            "analyze": False,
        },
    )
    claim_id = claim.json()["claim"]["id"]

    import backend.main as backend_main

    def fail_notification(*args, **kwargs):
        raise RuntimeError("Notification provider unavailable")

    monkeypatch.setattr(backend_main, "crear_notificacion", fail_notification)
    response = api_client.post(
        f"/api/claims/{claim_id}/messages",
        headers=client_headers,
        json={"message": "¿Podrían explicarme con mayor detalle la solución propuesta?"},
    )

    assert response.status_code == 201
    assert response.json()["items"][-1]["message"].startswith("¿Podrían explicarme")


def test_reports_expose_operational_and_ai_metrics(api_client):
    admin_login = api_client.post(
        "/api/auth/login",
        json={"email": "admin@smartclaim.com", "password": "123456"},
    )
    headers = {"Authorization": f"Bearer {admin_login.json()['token']}"}

    response = api_client.get("/api/reports", headers=headers)

    assert response.status_code == 200
    report = response.json()
    assert "firstResponseTimeByCategory" in report
    assert "claimsEvolution" in report
    assert "reclamos_abiertos" in report["metrics"]
    assert "reclamos_cerrados" in report["metrics"]
    assert "casos_escalados" in report["metrics"]
    assert report["metrics"]["tiempo_promedio_primera_respuesta"] >= 0


def test_health_reports_database_status(api_client):
    response = api_client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["database"] == "ok"
    assert response.json()["databaseProvider"] == "sqlite"


def test_production_runtime_rejects_insecure_secret(monkeypatch):
    from modules.config import validate_runtime_config

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET", "smartclaim-dev-secret-change-me")

    with pytest.raises(RuntimeError, match="AUTH_SECRET"):
        validate_runtime_config()


def test_agent_cannot_access_admin_configuration(api_client):
    agent_login = api_client.post(
        "/api/auth/login",
        json={"email": "laura.martinez@smartclaim.com", "password": "123456"},
    )
    headers = {"Authorization": f"Bearer {agent_login.json()['token']}"}

    assert api_client.get("/api/config", headers=headers).status_code == 403
    assert api_client.get("/api/documents", headers=headers).status_code == 403
    assert api_client.get("/api/reports", headers=headers).status_code == 403
    assert api_client.post("/api/documents/reindex", headers=headers).status_code == 403


def test_agent_keeps_operational_claim_access(api_client):
    agent_login = api_client.post(
        "/api/auth/login",
        json={"email": "laura.martinez@smartclaim.com", "password": "123456"},
    )
    headers = {"Authorization": f"Bearer {agent_login.json()['token']}"}

    assert api_client.get("/api/dashboard", headers=headers).status_code == 200
    assert api_client.get("/api/claims", headers=headers).status_code == 200


def test_profile_update_and_claim_pagination(api_client):
    login = api_client.post(
        "/api/auth/login",
        json={"email": "maria.gonzalez@email.com", "password": "123456"},
    )
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    updated = api_client.patch(
        "/api/auth/me",
        headers=headers,
        json={"name": "Maria Gonzalez Demo", "phone": "+51 999 888 777"},
    )
    assert updated.status_code == 200
    assert updated.json()["user"]["name"] == "Maria Gonzalez Demo"
    assert updated.json()["user"]["phone"] == "+51 999 888 777"

    claims = api_client.get("/api/claims?page=1&page_size=1", headers=headers)
    assert claims.status_code == 200
    assert claims.json()["pagination"]["pageSize"] == 1
    assert len(claims.json()["items"]) <= 1
