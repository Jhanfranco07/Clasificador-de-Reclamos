import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def api_client(monkeypatch, tmp_path, request):
    import database.db_connection as db_connection

    monkeypatch.setattr(db_connection, "DB_PATH", tmp_path / "smartclaim_api_test.db")


    if getattr(request, 'param', 'sqlite') == 'postgres':
        request.getfixturevalue('vector_db')
        from modules.rag_engine import construir_indice_tfidf
        construir_indice_tfidf(forzar=True)

    from backend.main import app

    with TestClient(app) as client:
        yield client


@pytest.mark.parametrize("api_client", ["sqlite", "postgres"], indirect=True)
def test_auth_orders_claims_and_roles(api_client):
    login = api_client.post(
        "/api/auth/login",
        json={"email": "jhan.perez@gmail.com", "password": "123456"},
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
            "customer_name": "Jhan Perez",
            "customer_email": "jhan.perez@gmail.com",
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


@pytest.mark.parametrize("api_client", ["sqlite", "postgres"], indirect=True)
def test_claim_continuous_conversation(api_client):
    client_login = api_client.post(
        "/api/auth/login",
        json={"email": "jhan.perez@gmail.com", "password": "123456"},
    )
    client_headers = {"Authorization": f"Bearer {client_login.json()['token']}"}
    claim = api_client.post(
        "/api/claims",
        headers=client_headers,
        json={
            "customer_name": "Jhan Perez",
            "customer_email": "jhan.perez@gmail.com",
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
        json={"email": "gonzalo.caceres@smartclaim.com", "password": "123456"},
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
        json={"email": "jhan.perez@gmail.com", "password": "123456"},
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
        json={"email": "jhan.perez@gmail.com", "password": "123456"},
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
        json={"email": "jhan.perez@gmail.com", "password": "123456"},
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
        "Gonzalo Caceres",
    )

    assert "[Nombre del agente]" not in response
    assert "Gonzalo Caceres" in response


def test_agent_signature_is_added_when_missing():
    from backend.main import _firmar_respuesta_agente

    response = _firmar_respuesta_agente("Estamos revisando tu reclamo.", "Admin System")

    assert response.endswith("Saludos cordiales,\nAdmin System\nServicio de Atención al Cliente")


def test_client_message_succeeds_when_notification_fails(api_client, monkeypatch):
    client_login = api_client.post(
        "/api/auth/login",
        json={"email": "jhan.perez@gmail.com", "password": "123456"},
    )
    client_headers = {"Authorization": f"Bearer {client_login.json()['token']}"}
    claim = api_client.post(
        "/api/claims",
        headers=client_headers,
        json={
            "customer_name": "Jhan Perez",
            "customer_email": "jhan.perez@gmail.com",
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


@pytest.mark.parametrize("api_client", ["sqlite", "postgres"], indirect=True)
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
        json={"email": "gonzalo.caceres@smartclaim.com", "password": "123456"},
    )
    headers = {"Authorization": f"Bearer {agent_login.json()['token']}"}

    assert api_client.get("/api/config", headers=headers).status_code == 403
    assert api_client.get("/api/documents", headers=headers).status_code == 403
    assert api_client.get("/api/reports", headers=headers).status_code == 403
    assert api_client.post("/api/documents/reindex", headers=headers).status_code == 403


def test_agent_keeps_operational_claim_access(api_client):
    agent_login = api_client.post(
        "/api/auth/login",
        json={"email": "gonzalo.caceres@smartclaim.com", "password": "123456"},
    )
    headers = {"Authorization": f"Bearer {agent_login.json()['token']}"}

    assert api_client.get("/api/dashboard", headers=headers).status_code == 200
    assert api_client.get("/api/claims", headers=headers).status_code == 200


def test_profile_update_and_claim_pagination(api_client):
    login = api_client.post(
        "/api/auth/login",
        json={"email": "jhan.perez@gmail.com", "password": "123456"},
    )
    headers = {"Authorization": f"Bearer {login.json()['token']}"}

    updated = api_client.patch(
        "/api/auth/me",
        headers=headers,
        json={"name": "Jhan Perez Demo", "phone": "+51 999 888 777"},
    )
    assert updated.status_code == 200
    assert updated.json()["user"]["name"] == "Jhan Perez Demo"
    assert updated.json()["user"]["phone"] == "+51 999 888 777"

    claims = api_client.get("/api/claims?page=1&page_size=1", headers=headers)
    assert claims.status_code == 200
    assert claims.json()["pagination"]["pageSize"] == 1
    assert len(claims.json()["items"]) <= 1


@pytest.mark.parametrize("api_client", ["sqlite", "postgres"], indirect=True)
def test_document_pdf_preview_requires_admin_and_can_be_saved(api_client):
    import io
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    def headers(email):
        response = api_client.post("/api/auth/login", json={"email": email, "password": "123456"})
        return {"Authorization": f"Bearer {response.json()['token']}"}

    path = "/api/documents/pdf-preview"
    admin = headers("admin@smartclaim.com")
    client = headers("jhan.perez@gmail.com")
    assert api_client.post(path, content=b"bad").status_code == 401
    assert api_client.post(path, content=b"bad", headers=client).status_code == 403
    assert api_client.post(path, content=b"bad", headers=admin).status_code == 415
    pdf_headers = {**admin, "Content-Type": "application/pdf"}
    assert api_client.post(path, content=b"%PDF-1.7\ntruncated", headers=pdf_headers).status_code == 422

    writer = PdfWriter()
    page = writer.add_blank_page(300, 300)
    buffer = io.BytesIO()
    writer.write(buffer)
    assert api_client.post(path, content=buffer.getvalue(), headers=pdf_headers).status_code == 422

    font = DictionaryObject({
        NameObject("/Type"): NameObject("/Font"),
        NameObject("/Subtype"): NameObject("/Type1"),
        NameObject("/BaseFont"): NameObject("/Helvetica"),
    })
    page[NameObject("/Resources")] = DictionaryObject({
        NameObject("/Font"): DictionaryObject({NameObject("/F1"): font}),
    })
    stream = DecodedStreamObject()
    stream.set_data(b"BT /F1 12 Tf 20 200 Td (Revisar recibo y pedido incompleto.) Tj ET")
    page[NameObject("/Contents")] = writer._add_object(stream)
    buffer = io.BytesIO()
    writer.write(buffer)
    preview = api_client.post(path, content=buffer.getvalue(), headers=pdf_headers)
    assert preview.json() == {"content": "Revisar recibo y pedido incompleto."}
    document = {"title": "PDF de prueba", "type": "FAQ", "category": "Producto incompleto", **preview.json()}
    saved = api_client.post("/api/documents", json=document, headers=admin)
    assert saved.status_code == 201
    registered = next(item for item in saved.json()["items"] if item["title"] == document["title"])
    edited_text = "Guía sobre recibos incompletos con el marcador auditoría cuarzo."
    edited = api_client.put(f"/api/documents/{registered['id']}",
                            json={**document, "content": edited_text}, headers=admin)
    assert edited.status_code == 200
    first = api_client.post("/api/documents/reindex", headers=admin)
    second = api_client.post("/api/documents/reindex", headers=admin)
    assert first.status_code == second.status_code == 200
    assert first.json()["fragmentos"] == second.json()["fragmentos"]

    from modules.rag_engine import recuperar_documentos_tfidf

    hits = recuperar_documentos_tfidf("marcador auditoría cuarzo", document["category"])
    assert str(hits[0]["id_documento"]) == registered["id"]
    assert hits[0]["fragmento"] == edited_text



def test_pdf_limits_multipage_encryption_and_image_only(api_client, monkeypatch):
    import io
    from pypdf import PdfWriter
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject, NumberObject
    from modules import pdf_documents
    from backend import main

    def pdf(texts=(), *, image=False, encrypted=False):
        writer = PdfWriter()
        for text in texts or ("",):
            page = writer.add_blank_page(300, 300)
            if image:
                xobject = DecodedStreamObject()
                xobject.set_data(b"\xff\xff\xff")
                xobject.update({NameObject("/Type"): NameObject("/XObject"),
                                NameObject("/Subtype"): NameObject("/Image"),
                                NameObject("/Width"): NumberObject(1), NameObject("/Height"): NumberObject(1),
                                NameObject("/ColorSpace"): NameObject("/DeviceRGB"),
                                NameObject("/BitsPerComponent"): NumberObject(8)})
                resources = {NameObject("/XObject"): DictionaryObject({NameObject("/Im0"): writer._add_object(xobject)})}
                command = b"q 100 0 0 100 10 10 cm /Im0 Do Q"
            else:
                font = DictionaryObject({
                    NameObject("/Type"): NameObject("/Font"),
                    NameObject("/Subtype"): NameObject("/Type1"),
                    NameObject("/BaseFont"): NameObject("/Helvetica"),
                    NameObject("/Encoding"): NameObject("/WinAnsiEncoding"),
                })
                resources = {NameObject("/Font"): DictionaryObject({NameObject("/F1"): font})}
                encoded = text.encode("cp1252")
                command = b"BT /F1 12 Tf 20 200 Td (" + encoded + b") Tj ET"
            page[NameObject("/Resources")] = DictionaryObject(resources)
            stream = DecodedStreamObject()
            stream.set_data(command)
            page[NameObject("/Contents")] = writer._add_object(stream)
        if encrypted:
            writer.encrypt("demo-password")
        buffer = io.BytesIO()
        writer.write(buffer)
        return buffer.getvalue()

    login = api_client.post("/api/auth/login", json={"email": "admin@smartclaim.com", "password": "123456"})
    headers = {"Authorization": f"Bearer {login.json()['token']}", "Content-Type": "application/pdf"}
    path = "/api/documents/pdf-preview"
    pages = ["Primera página: número y acentuación.", "Segunda página: revisión del pedido."]
    valid = pdf(pages)
    assert api_client.post(path, content=valid, headers=headers).json() == {"content": "\n\n".join(pages)}
    for data, error in (
        (pdf(pages, encrypted=True), "contraseña"),
        (pdf(image=True), "texto legible"),
        (b"PK\x03\x04", "cabecera PDF"),
    ):
        response = api_client.post(path, content=data, headers=headers)
        assert response.status_code == 422
        assert error in response.json()["detail"]
    monkeypatch.setattr(pdf_documents, "PDF_MAX_PAGES", 1)
    assert "límite de páginas" in api_client.post(path, content=valid, headers=headers).json()["detail"]
    monkeypatch.setattr(main, "PDF_MAX_BYTES", len(valid) - 1)
    assert api_client.post(path, content=valid, headers=headers).status_code == 413


def test_document_api_rejects_duplicates_and_agent_writes(api_client):
    def headers(email):
        response = api_client.post("/api/auth/login", json={"email": email, "password": "123456"})
        return {"Authorization": f"Bearer {response.json()['token']}"}

    agent = headers("gonzalo.caceres@smartclaim.com")
    admin = headers("admin@smartclaim.com")
    document = {"title": "Política de prueba documental", "type": "FAQ", "category": "Producto incompleto",
                "content": "Revisar los artículos del pedido según el comprobante indicado."}
    for method, path in (
        ("POST", "/api/documents"), ("POST", "/api/documents/pdf-preview"),
        ("PUT", "/api/documents/4"), ("DELETE", "/api/documents/4"),
        ("POST", "/api/documents/reindex"),
    ):
        assert api_client.request(method, path, json=document, headers=agent).status_code == 403
    assert api_client.post("/api/documents", json={**document, "category": "Otra"}, headers=admin).status_code == 422
    assert api_client.post("/api/documents", json=document, headers=admin).status_code == 201
    assert api_client.post("/api/documents", json={**document, "title": document["title"].upper(),
                                                   "content": "Una variante distinta del texto de la política."},
                           headers=admin).status_code == 409
    assert api_client.post("/api/documents", json={**document, "title": "Título nuevo para contenido repetido"},
                           headers=admin).status_code == 409



@pytest.mark.parametrize("api_client", ["sqlite", "postgres"], indirect=True)
def test_claim_rag_draft_edit_escalation_and_send(api_client):
    def headers(email):
        auth = api_client.post("/api/auth/login", json={"email": email, "password": "123456"})
        return {"Authorization": f"Bearer {auth.json()['token']}"}

    client = headers("jhan.perez@gmail.com")
    agent = headers("gonzalo.caceres@smartclaim.com")
    assert api_client.get("/api/catalog").status_code == 200
    claim = api_client.post("/api/claims", headers=client, json={
        "customer_name": "Cliente demo",
        "customer_email": "jhan.perez@gmail.com",
        "order_code": "ORD-DRAFT-001",
        "description": "Recibí un pedido incompleto. Faltan productos pagados y tengo el recibo.",
        "analyze": False,
    })
    assert claim.status_code == 201
    claim_id = claim.json()["claim"]["id"]
    analyzed = api_client.post(f"/api/claims/{claim_id}/analyze", headers=agent).json()
    assert analyzed["analysis"]
    assert analyzed["documents"]
    response_id = analyzed["response"]["id"]
    escalation = api_client.patch(f"/api/claims/{claim_id}/state", headers=agent,
                                  json={"state": "Escalado", "comment": "Revisión de un pedido incompleto."})
    assert escalation.status_code == 200
    assert len(escalation.json()["history"]) > len(analyzed["history"])
    text = "Confirmamos la recepción de tu reclamo y revisaremos el comprobante."
    payload = {"response_text": text}
    edited = api_client.patch(f"/api/responses/{response_id}", headers=agent, json=payload)
    assert edited.json()["response"]["editedResponse"] == text
    assert edited.json()["response"]["finalResponse"] is None
    private = api_client.get(f"/api/claims/{claim_id}", headers=client).json()
    assert private["response"] is None and private["documents"] == []
    assert all(event["action"] != "Edición de respuesta" for event in private["history"])
    sent = api_client.post(f"/api/responses/{response_id}/approve", headers=agent, json=payload)
    assert sent.status_code == 200
    assert text in sent.json()["response"]["finalResponse"]
    visible = api_client.get(f"/api/claims/{claim_id}", headers=client).json()
    assert text in visible["response"]["finalResponse"]
    assert visible["response"]["editedResponse"] is None
    assert [event["action"] for event in visible["history"]].count("Envio de respuesta") == 1
    assert all(event["action"] != "Marcado como respondido" for event in visible["history"])
    assert len(sent.json()["history"]) > len(escalation.json()["history"])


def test_production_startup_does_not_create_demo_accounts(monkeypatch, tmp_path):
    from backend.main import app
    from database import db_connection as db

    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("AUTH_SECRET", "test-only-production-secret-longer-than-32")
    monkeypatch.setenv("DATABASE_URL", "")
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "startup.db")
    db.init_db()
    with TestClient(app):
        assert db.fetch_one("SELECT COUNT(*) AS total FROM auth_users")["total"] == 0
        assert db.fetch_one("SELECT COUNT(*) AS total FROM pedidos")["total"] == 0

def test_hosted_startup_and_document_mutations_leave_database_intact(api_client, monkeypatch):
    from backend import main
    from database import db_connection as db

    admin = api_client.post("/api/auth/login", json={"email": "admin@smartclaim.com", "password": "123456"})
    headers = {"Authorization": f"Bearer {admin.json()['token']}"}
    before = db.fetch_all("SELECT * FROM fragmentos_documento ORDER BY id_fragmento")

    def forbidden(*args, **kwargs):
        pytest.fail("El entorno alojado intentó modificar el catálogo automáticamente")

    monkeypatch.setenv("RENDER", "true")
    for name in ("init_db", "asegurar_usuarios_auth_base", "asegurar_pedidos_demo_base", "construir_indice_vectorial"):
        monkeypatch.setattr(main, name, forbidden)
    payload = {"title": "Documento de auditoría", "type": "FAQ", "category": "Soporte general",
               "content": "Contenido académico para verificar los controles de escritura."}
    with TestClient(main.app) as hosted:
        assert hosted.get("/api/documents", headers=headers).status_code == 200
        for method, path in (
            ("POST", "/api/documents"), ("PUT", "/api/documents/4"),
            ("DELETE", "/api/documents/4"), ("POST", "/api/documents/reindex"),
        ):
            assert hosted.request(method, path, headers=headers, json=payload).status_code == 503
    assert db.fetch_all("SELECT * FROM fragmentos_documento ORDER BY id_fragmento") == before


@pytest.mark.parametrize("dsn", [
    "host=example.invalid dbname=smartclaim",
    "host=127.0.0.1 hostaddr=198.51.100.1 dbname=smartclaim",
    "host=127.0.0.1 service=external dbname=smartclaim",
])
def test_remote_database_disables_automatic_setup(monkeypatch, dsn):
    from database.db_connection import allows_automatic_database_setup

    monkeypatch.setenv("DB_PROVIDER", "postgres")
    monkeypatch.setenv("DATABASE_URL", dsn)
    assert not allows_automatic_database_setup()
