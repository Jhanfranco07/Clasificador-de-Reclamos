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
