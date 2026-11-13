import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi.testclient import TestClient

from database import db_connection as db
from modules import response_service


@pytest.fixture
def api():
    from backend.main import app
    with TestClient(app) as client:
        yield client


def auth(api, role="CLIENT"):
    email = {"CLIENT": "jhan.perez@gmail.com", "AGENT": "gonzalo.caceres@smartclaim.com", "ADMIN": "admin@smartclaim.com"}[role]
    r = api.post("/api/auth/login", json={"email": email, "password": "123456"})
    assert r.status_code == 200
    return {"Authorization": "Bearer " + r.json()["token"]}


def new_claim(api, analyze=True):
    customer = auth(api)
    order = api.get("/api/orders", headers=customer).json()["items"][0]
    r = api.post("/api/claims", headers=customer, json={
        "customer_name": "Jhan Perez", "customer_email": "jhan.perez@gmail.com",
        "order_code": order["code"], "description": "Me cobraron dos veces el mismo pedido", "analyze": analyze,
    })
    assert r.status_code == 201
    return api.get("/api/claims/" + r.json()["claim"]["id"], headers=auth(api, "AGENT")).json()


def test_bf01_draft_private_in_api_and_history(api):
    claim = new_claim(api)
    rid, cid = claim["response"]["id"], claim["claim"]["id"]
    agent = auth(api, "AGENT")
    assert api.patch(f"/api/responses/{rid}", headers=agent, json={"response_text": "PRIVATE-DRAFT-MARKER"}).status_code == 200
    public = api.get(f"/api/claims/{cid}", headers=auth(api)).json()
    assert public["response"] is None and public["analysis"] is None and public["documents"] == []
    assert "PRIVATE-DRAFT-MARKER" not in json.dumps(public)
    assert "borrador" not in json.dumps(public)
    approved = api.post(f"/api/responses/{rid}/approve", headers=agent)
    assert approved.status_code == 200
    public = api.get(f"/api/claims/{cid}", headers=auth(api)).json()
    assert "PRIVATE-DRAFT-MARKER" in public["response"]["finalResponse"]
    assert "suggestedResponse" not in public["response"] and "editedResponse" not in public["response"]


def test_bf01_repeated_and_concurrent_publication_is_once(api):
    claim = new_claim(api)
    rid, cid = int(claim["response"]["id"]), int(claim["claim"]["id"])
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: response_service.publish(rid, "Reviewed response", "Agent", "audit-agent"), range(4)))
    assert results.count(True) == 1
    assert db.fetch_one("SELECT COUNT(*) AS n FROM claim_messages WHERE id_reclamo=? AND sender_type='agent'", (cid,))["n"] == 1
    assert db.fetch_one("SELECT COUNT(*) AS n FROM notificaciones WHERE id_reclamo=? AND evento='CLAIM_PUBLISHED'", (cid,))["n"] == 1
    assert db.fetch_one("SELECT COUNT(*) AS n FROM historial_estados WHERE id_reclamo=? AND accion='Envio de respuesta'", (cid,))["n"] == 1


def test_bf01_publication_rolls_back_if_notification_fails(api, monkeypatch):
    claim = new_claim(api)
    rid, cid = int(claim["response"]["id"]), int(claim["claim"]["id"])
    original = response_service.insert
    def fail(conn, query, params=()):
        if "INSERT INTO notificaciones" in query:
            raise RuntimeError("simulated failure")
        return original(conn, query, params)
    monkeypatch.setattr(response_service, "insert", fail)
    with pytest.raises(RuntimeError):
        response_service.publish(rid, "Reviewed response")
    row = db.fetch_one("SELECT estado_revision,respuesta_final FROM respuestas_sugeridas WHERE id_respuesta=?", (rid,))
    assert row == {"estado_revision": "PENDIENTE", "respuesta_final": None}
    assert db.fetch_one("SELECT COUNT(*) AS n FROM claim_messages WHERE id_reclamo=? AND sender_type='agent'", (cid,))["n"] == 0


def test_bf01_client_cannot_edit_or_publish(api):
    claim = new_claim(api)
    rid = claim["response"]["id"]
    assert api.patch(f"/api/responses/{rid}", headers=auth(api), json={"response_text": "Unauthorized response"}).status_code == 403
    assert api.post(f"/api/responses/{rid}/approve", headers=auth(api)).status_code == 403


def test_bf02_foreign_missing_and_inactive_cannot_create(api):
    owner = auth(api)
    order = api.get("/api/orders", headers=owner).json()["items"][0]
    registered = api.post("/api/auth/register", json={"name": "Other client", "email": "other@example.com", "password": "123456"})
    other = {"Authorization": "Bearer " + registered.json()["token"]}
    payload = dict(customer_name="Other client", customer_email="other@example.com", order_code=order["code"],
                   description="My complaint about another order", analyze=False)
    before = db.fetch_one("SELECT COUNT(*) AS n FROM reclamos")["n"]
    assert api.post("/api/claims", headers=other, json=payload).status_code == 404
    assert api.post("/api/claims", headers=other, json={**payload, "order_code": "MISSING"}).status_code == 404
    db.execute("UPDATE auth_users SET estado='INACTIVO' WHERE correo='other@example.com'")
    assert api.post("/api/claims", headers=other, json=payload).status_code == 401
    assert db.fetch_one("SELECT COUNT(*) AS n FROM reclamos")["n"] == before


def test_bf02_server_owns_identity_date_and_order_link(api):
    client = auth(api)
    order = api.get("/api/orders", headers=client).json()["items"][0]
    r = api.post("/api/claims", headers=client, json=dict(
        customer_name="Fake name", customer_email="jhan.perez@gmail.com", order_code=order["code"],
        order_date="2099-01-01", responsible="Arbitrary assignee", description="A legitimate separate incident", analyze=False))
    assert r.status_code == 201
    row = db.fetch_one("SELECT * FROM reclamos WHERE id_reclamo=?", (int(r.json()["claim"]["id"]),))
    assert row["id_pedido"] == int(order["id"])
    assert row["fecha_pedido"] != "2099-01-01" and row["responsable_asignado"] != "Arbitrary assignee"
    assert r.json()["claim"]["customerName"] != "Fake name"
    assert r.json()["claim"]["orderLinkStatus"] == "LINKED"


def test_bf02_reconciliation_is_non_destructive_and_dry_by_default(api):
    from database import repositories as repo
    from scripts.reconcile_claim_orders import reconcile
    client = auth(api)
    order = api.get("/api/orders", headers=client).json()["items"][0]
    customer = db.fetch_one("SELECT id_cliente FROM pedidos WHERE id_pedido=?", (int(order["id"]),))["id_cliente"]
    valid = repo.crear_reclamo(customer, order["code"], "WEB", "2020-01-01", "Historical valid claim")
    orphan = repo.crear_reclamo(customer, "HISTORICAL-UNKNOWN", "WEB", "2020-01-01", "Historical orphan preserved")
    with db.get_connection() as conn:
        report = reconcile(conn)
        assert next(x for x in report if x["claim_id"] == valid)["status"] == "MATCH_READY"
        assert conn.execute("SELECT id_pedido FROM reclamos WHERE id_reclamo=?", (valid,)).fetchone()[0] is None
        reconcile(conn, apply=True)
        conn.commit()
    assert db.fetch_one("SELECT id_pedido FROM reclamos WHERE id_reclamo=?", (valid,))["id_pedido"] == int(order["id"])
    assert db.fetch_one("SELECT descripcion,id_pedido FROM reclamos WHERE id_reclamo=?", (orphan,)) == {
        "descripcion": "Historical orphan preserved", "id_pedido": None}
    public = api.get(f"/api/claims/{orphan}", headers=client)
    assert public.status_code == 200 and public.json()["claim"]["orderLinkStatus"] == "LEGACY_UNRESOLVED"


def catalog_items(api):
    catalog = api.get('/api/catalog').json()['items']
    return catalog, [{"product_id": int(catalog[0]['products'][0]['id']), "quantity": 2}]


def order_payload(api, items):
    quote = api.post('/api/orders/quote', json={"items": items})
    assert quote.status_code == 200
    return dict(items=items, quote_hash=quote.json()['quoteHash'], payment_method='Efectivo', delivery_address='A real test address')


def test_bf03_authorized_price_snapshots_and_delivery_notes(api):
    catalog, items = catalog_items(api)
    payload = order_payload(api, items)
    quote = api.post('/api/orders/quote', json={"items": items}).json()
    created = api.post('/api/orders', headers=auth(api), json={**payload, 'delivery_notes': 'Ring the test bell'})
    assert created.status_code == 201
    order = created.json()['order']
    assert order['total'] == quote['total']
    assert order['deliveryNotes'] == 'Ring the test bell' and order['paymentVerified'] is False
    assert order['items'][0]['price'] == catalog[0]['products'][0]['price']
    db.execute("UPDATE productos SET precio=999,nombre='Changed catalog',disponible=0 WHERE id_producto=?", (items[0]['product_id'],))
    historical = api.get('/api/orders/' + order['id'], headers=auth(api)).json()['order']
    assert historical['items'] == order['items'] and historical['total'] == order['total']


@pytest.mark.parametrize('bad', [0, -1, 1.5, True, 2147483648])
def test_bf03_invalid_quantities_rejected(api, bad):
    _, items = catalog_items(api)
    assert api.post('/api/orders/quote', json={'items': [{**items[0], 'quantity': bad}]}).status_code == 422


def test_bf03_rejects_arbitrary_prices_products_and_whitespace(api):
    _, items = catalog_items(api)
    payload = order_payload(api, items)
    assert api.post('/api/orders', headers=auth(api), json={**payload, 'store_name': 'FAKE', 'items': [{**items[0], 'price': 0}]}).status_code == 422
    assert api.post('/api/orders', headers=auth(api), json={**payload, 'delivery_address': '     '}).status_code == 422
    assert api.post('/api/orders/quote', json={'items': [{'product_id': 999999, 'quantity': 1}]}).status_code == 422
    db.execute('UPDATE productos SET disponible=0 WHERE id_producto=?', (items[0]['product_id'],))
    assert api.post('/api/orders/quote', json={'items': items}).status_code == 422


def test_bf03_changed_catalog_requires_requote(api):
    _, items = catalog_items(api)
    payload = order_payload(api, items)
    before = db.fetch_one('SELECT COUNT(*) AS n FROM pedidos')['n']
    db.execute('UPDATE productos SET precio=precio+1 WHERE id_producto=?', (items[0]['product_id'],))
    assert api.post('/api/orders', headers=auth(api), json=payload).status_code == 409
    assert db.fetch_one('SELECT COUNT(*) AS n FROM pedidos')['n'] == before


def test_bf03_inactive_store_and_invalid_catalog_price_are_rejected(api):
    catalog, items = catalog_items(api)
    store_id = int(catalog[0]['id'])
    db.execute('UPDATE restaurantes SET activo=0 WHERE id_restaurante=?', (store_id,))
    assert api.post('/api/orders/quote', json={'items': items}).status_code == 422
    db.execute('UPDATE restaurantes SET activo=1 WHERE id_restaurante=?', (store_id,))
    for bad_price in [-1, float('inf')]:
        db.execute('UPDATE productos SET precio=? WHERE id_producto=?', (bad_price, items[0]['product_id']))
        assert api.post('/api/orders/quote', json={'items': items}).status_code == 422


def test_bf03_mixed_cart_is_quoted_but_not_silently_grouped(api):
    catalog, items = catalog_items(api)
    items.append({'product_id': int(catalog[1]['products'][0]['id']), 'quantity': 1})
    q = api.post('/api/orders/quote', json={'items': items}).json()
    assert len({line['restaurantId'] for line in q['items']}) == 2
    assert q['canConfirm'] is False and q['total'] is None and q['limitation']
    assert api.post('/api/orders', headers=auth(api), json={**order_payload(api, items)}).status_code == 409


def test_bf03_order_is_atomic_on_item_failure(api, monkeypatch):
    from modules import order_service
    _, items = catalog_items(api)
    payload = order_payload(api, items)
    original = order_service.insert
    before = db.fetch_one('SELECT COUNT(*) AS n FROM pedidos')['n']
    def fail(conn, query, params=()):
        if 'INSERT INTO pedido_items' in query:
            raise RuntimeError('simulated item failure')
        return original(conn, query, params)
    monkeypatch.setattr(order_service, 'insert', fail)
    with pytest.raises(RuntimeError):
        api.post('/api/orders', headers=auth(api), json=payload)
    assert db.fetch_one('SELECT COUNT(*) AS n FROM pedidos')['n'] == before


def test_bf04_local_templates_do_not_promise_unimplemented_email(api):
    from modules.rag_engine import generar_respuesta_basica, generar_respuesta_sugerida
    analysis = {'categoria': 'Cobro indebido', 'prioridad': 'Alta'}
    for text in [generar_respuesta_basica('Cliente', 'ORD-TEST', 'Cobro', analysis),
                 generar_respuesta_sugerida('Cliente', 'ORD-TEST', 'Cobro', analysis, [])]:
        assert 'correo' not in text.lower()
        assert 'conversación' in text


def test_bf05_preconditions_roles_and_close_reason(api):
    claim = new_claim(api, analyze=False)
    cid = claim['claim']['id']
    staff, customer = auth(api, 'AGENT'), auth(api)
    assert api.patch(f'/api/claims/{cid}/state', headers=customer, json={'state': 'CLOSED', 'comment': 'Not allowed'}).status_code == 403
    assert api.patch(f'/api/claims/{cid}/state', headers=staff, json={'state': 'RESPONDED'}).status_code == 409
    assert api.post(f'/api/claims/{cid}/reopen', headers=customer).status_code == 409
    assert api.post(f'/api/claims/{cid}/close', headers=staff).status_code == 422
    assert api.post(f'/api/claims/{cid}/close', headers=staff, json={'comment': '   '}).status_code == 422
    closed = api.post(f'/api/claims/{cid}/close', headers=staff, json={'comment': 'Administrative closure for test'})
    assert closed.status_code == 200 and closed.json()['claim']['closedAt'] is not None
    before = db.fetch_one('SELECT COUNT(*) AS n FROM claim_messages WHERE id_reclamo=?', (int(cid),))['n']
    assert api.post(f'/api/claims/{cid}/messages', headers=staff, json={'message': 'Cannot publish on closed claim'}).status_code == 409
    assert db.fetch_one('SELECT COUNT(*) AS n FROM claim_messages WHERE id_reclamo=?', (int(cid),))['n'] == before
    reopened = api.post(f'/api/claims/{cid}/reopen', headers=customer)
    assert reopened.status_code == 200
    assert reopened.json()['claim']['statusKey'] == 'IN_REVIEW' and reopened.json()['claim']['closedAt'] is None
    assert api.post(f'/api/claims/{cid}/reopen', headers=customer).status_code == 409


def test_bf05_closed_case_cannot_publish_or_analyze(api, monkeypatch):
    import backend.main as main
    from unittest.mock import Mock
    claim = new_claim(api)
    cid, rid = claim['claim']['id'], claim['response']['id']
    staff = auth(api, 'AGENT')
    assert api.post(f'/api/claims/{cid}/close', headers=staff, json={'comment': 'Close for audit'}).status_code == 200
    assert api.post(f'/api/responses/{rid}/approve', headers=staff).status_code == 409
    predictor = Mock(side_effect=AssertionError('Must not run'))
    monkeypatch.setattr(main, 'clasificar_reclamo', predictor)
    assert api.post(f'/api/claims/{cid}/analyze', headers=staff).status_code == 409
    predictor.assert_not_called()
    detail = api.get(f'/api/claims/{cid}', headers=auth(api)).json()
    assert detail['claim']['statusKey'] == 'CLOSED' and detail['response'] is None


def test_bf05_reanalysis_keeps_publication_and_approval_retry_keeps_closed(api):
    claim = new_claim(api)
    cid, rid = claim['claim']['id'], claim['response']['id']
    staff = auth(api, 'AGENT')
    assert api.post(f'/api/responses/{rid}/approve', headers=staff, json={'response_text': 'Published final response for customer'}).status_code == 200
    before = api.get(f'/api/claims/{cid}', headers=auth(api)).json()['response']
    analyzed = api.post(f'/api/claims/{cid}/analyze', headers=staff)
    assert analyzed.status_code == 200 and analyzed.json()['claim']['statusKey'] == 'RESPONDED'
    assert analyzed.json()['response']['status'] == 'PENDIENTE'
    assert api.get(f'/api/claims/{cid}', headers=auth(api)).json()['response'] == before
    assert api.post(f'/api/claims/{cid}/close', headers=staff, json={'comment': 'Administrative closure after response'}).status_code == 200
    retried = api.post(f'/api/responses/{rid}/approve', headers=staff)
    assert retried.status_code == 200 and retried.json()['claim']['statusKey'] == 'CLOSED'
    assert retried.json()['claim']['closedAt'] is not None


def test_bf05_close_publication_race_preserves_invariants(api):
    from database.repositories import cerrar_reclamo
    from modules.domain_errors import DomainError
    claim = new_claim(api)
    cid, rid = int(claim['claim']['id']), int(claim['response']['id'])
    def publish():
        try:
            response_service.publish(rid, 'Reviewed customer response')
        except DomainError as exc:
            assert exc.status_code == 409
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(publish), pool.submit(cerrar_reclamo, cid, 'Cerrado', 'Administrative closure')]
        for future in futures:
            future.result()
    detail = api.get(f'/api/claims/{cid}', headers=auth(api, 'AGENT')).json()
    assert detail['claim']['statusKey'] == 'CLOSED' and detail['claim']['closedAt'] is not None


def test_bf05_conversation_preserves_published_response_and_history(api):
    detail = new_claim(api)
    cid, rid = detail['claim']['id'], detail['response']['id']
    staff, client = auth(api, 'AGENT'), auth(api)
    assert api.post(f'/api/responses/{rid}/approve', headers=staff).status_code == 200
    published = api.get(f'/api/claims/{cid}', headers=client).json()['response']
    for _ in range(2):
        assert api.post(f'/api/claims/{cid}/messages', headers=client, json={'message': 'Additional information, not a new economic outcome'}).status_code == 201
    public = api.get(f'/api/claims/{cid}', headers=client).json()
    assert public['claim']['statusKey'] == 'IN_REVIEW' and public['response'] == published
    for _ in range(2):
        assert api.post(f'/api/claims/{cid}/messages', headers=staff, json={'message': 'Reviewed additional customer information'}).status_code == 201
    assert db.fetch_one("SELECT COUNT(*) AS n FROM historial_estados WHERE id_reclamo=? AND accion='Respuesta del cliente'", (int(cid),))['n'] == 2
    assert db.fetch_one("SELECT COUNT(*) AS n FROM historial_estados WHERE id_reclamo=? AND accion='Respuesta del agente'", (int(cid),))['n'] == 2


def test_bf02_migrate_and_reconcile_workspace_copy_only(tmp_path, monkeypatch):
    import sqlite3
    import subprocess
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    source = root / 'data/smartclaim.db'
    copy = tmp_path / 'historical-copy.db'
    with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as original:
        with sqlite3.connect(copy) as target:
            original.backup(target)
    monkeypatch.setattr(db, 'DB_PATH', copy)
    db.run_script(root / 'database/schema.sql')
    with sqlite3.connect(copy) as conn:
        counts = {t: conn.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]
                  for t in ['reclamos', 'pedidos', 'clientes', 'claim_messages', 'respuestas_sugeridas']}
        orphans = conn.execute('''SELECT id_reclamo FROM reclamos r WHERE NOT EXISTS
            (SELECT 1 FROM pedidos p WHERE p.codigo_pedido=r.codigo_pedido)''').fetchall()
    db.migrate_db()
    script = root / 'scripts/reconcile_claim_orders.py'
    dry = subprocess.run([sys.executable, str(script), '--sqlite', str(copy)], capture_output=True, text=True, check=True)
    dry_report = json.loads(dry.stdout)
    assert dry_report['mode'] == 'read-only'
    backup = tmp_path / 'before-reconciliation.db'
    applied = subprocess.run([sys.executable, str(script), '--sqlite', str(copy), '--apply', '--backup', str(backup)],
                             capture_output=True, text=True, check=True)
    assert json.loads(applied.stdout)['mode'] == 'apply-on-copy' and backup.exists()
    with sqlite3.connect(copy) as conn:
        assert conn.execute('PRAGMA integrity_check').fetchone()[0] == 'ok'
        assert conn.execute('PRAGMA foreign_key_check').fetchall() == []
        for table, count in counts.items():
            assert conn.execute(f'SELECT COUNT(*) FROM {table}').fetchone()[0] == count
        for (claim_id,) in orphans:
            assert conn.execute('SELECT id_pedido FROM reclamos WHERE id_reclamo=?', (claim_id,)).fetchone() == (None,)


def test_bf05_staff_transition_matrix_and_permissions(api):
    from database.transactions import transaction, lock_claim
    from modules.claim_workflow import transition
    from modules.domain_errors import DomainError
    cid = int(new_claim(api, analyze=False)['claim']['id'])
    states = db.fetch_all('SELECT id_estado,nombre FROM estados_reclamo')
    db.execute("INSERT INTO claim_messages(id_reclamo,sender_type,mensaje) VALUES (?,'agent','Existing published response')", (cid,))
    with transaction() as conn:
        for source in states:
            for target in states:
                for role in ['CLIENT', 'AGENT', 'ADMIN']:
                    conn.execute('SAVEPOINT matrix_case')
                    try:
                        conn.execute('UPDATE reclamos SET id_estado=? WHERE id_reclamo=?', (source['id_estado'], cid))
                        claim = lock_claim(conn, cid)
                        allowed = role != 'CLIENT' and source['nombre'] != 'Cerrado' and target['nombre'] not in {'Nuevo', 'Analizado por IA'}
                        if allowed:
                            changed = transition(conn, claim, target['nombre'], role=role, comment='Administrative reason')
                            updated = lock_claim(conn, cid)
                            assert updated['estado'] == target['nombre']
                            if changed:
                                assert bool(updated['fecha_cierre']) == (target['nombre'] == 'Cerrado')
                                event = conn.execute('SELECT estado_anterior,estado_nuevo FROM historial_estados WHERE id_reclamo=? ORDER BY id_historial DESC LIMIT 1', (cid,)).fetchone()
                                assert tuple(event) == (source['nombre'], target['nombre'])
                        else:
                            with pytest.raises(DomainError):
                                transition(conn, claim, target['nombre'], role=role, comment='Administrative reason')
                    finally:
                        conn.execute('ROLLBACK TO matrix_case')
                        conn.execute('RELEASE matrix_case')
