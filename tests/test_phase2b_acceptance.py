from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from database import db_connection as db
from database.migrations import phase2b
from modules import order_workflow as workflow
from modules.domain_errors import DomainError


def key():
    return str(uuid4())


def login(api, email):
    result = api.post('/api/auth/login', json={'email': email, 'password': '123456'})
    assert result.status_code == 200
    return {'Authorization': 'Bearer ' + result.json()['token']}


@pytest.fixture
def scenario():
    from backend.main import app
    with TestClient(app) as api:
        admin = login(api, 'admin@smartclaim.com')
        customer = login(api, 'jhan.perez@gmail.com')
        agent = login(api, 'gonzalo.caceres@smartclaim.com')
        users, tokens = {}, {}
        for name, role in [('merchant', 'MERCHANT'), ('foreign', 'MERCHANT'), ('courier', 'COURIER'), ('othercourier', 'COURIER')]:
            response = api.post('/api/auth/register', json={'name': name, 'email': name + '@example.com', 'password': '123456'})
            uid = int(response.json()['user']['id'])
            assert api.patch(f'/api/operations/users/{uid}', headers=admin, json={
                'role': role, 'active': True, 'reason': 'Aceptación aislada', 'request_id': key()}).status_code == 200
            tokens[name] = login(api, name + '@example.com')
            users[name] = db.fetch_one('SELECT * FROM auth_users WHERE id_auth_user=?', (uid,))
        restaurant = db.fetch_one('SELECT * FROM restaurantes ORDER BY id_restaurante LIMIT 1')['id_restaurante']
        assert api.put(f'/api/operations/restaurants/{restaurant}/operator', headers=admin, json={
            'user_id': users['merchant']['id_auth_user'], 'active': True, 'edit_products': False,
            'reason': 'Autorización específica', 'request_id': key()}).status_code == 200
        product = db.fetch_one('SELECT * FROM productos WHERE id_restaurante=? AND disponible=1 LIMIT 1', (restaurant,))
        items = [{'product_id': product['id_producto'], 'quantity': 2}]
        quote = api.post('/api/orders/quote', json={'items': items}).json()
        response = api.post('/api/orders', headers=customer, json={'items': items, 'quote_hash': quote['quoteHash'],
            'payment_method': 'Efectivo', 'delivery_address': 'Dirección ficticia 123'})
        assert response.status_code == 201, response.text
        yield dict(api=api, admin=admin, customer=customer, agent=agent, users=users, tokens=tokens,
                   order=response.json()['order'], restaurant=restaurant, product=product)


def advance(s, state, token='merchant', reason=None):
    api, oid = s['api'], s['order']['id']
    headers = s['admin'] if token == 'admin' else s['tokens'][token]
    order = api.get(f'/api/orders/{oid}', headers=headers).json()['order']
    response = api.post(f'/api/orders/{oid}/transition', headers=headers, json={
        'state': state, 'expected_version': order['version'], 'request_id': key(), 'reason': reason})
    assert response.status_code == 200, response.text
    s['order'] = response.json()['order']
    return s['order']


def ready(s):
    for state in ['ACCEPTED', 'PREPARING', 'READY_FOR_PICKUP']:
        advance(s, state)


def assign(s, name='courier'):
    api = s['api']
    assert api.put('/api/operations/availability', headers=s['tokens'][name], json={'available': True, 'request_id': key()}).status_code == 200
    result = api.post(f"/api/orders/{s['order']['id']}/assignment", headers=s['admin'], json={
        'courier_id': s['users'][name]['id_auth_user'], 'expected_version': s['order']['version'],
        'reason': 'Despacho autorizado', 'request_id': key()})
    assert result.status_code == 200, result.text
    s['order'] = result.json()['order']


def test_full_five_role_journey(scenario):
    s = scenario
    assert s['order']['status'] == 'RECEIVED'
    assert s['order']['driverVerified'] is False
    listed = s['api'].get('/api/orders', headers=s['tokens']['merchant']).json()['items']
    assert s['order']['id'] in [o['id'] for o in listed]
    ready(s)
    assign(s)
    advance(s, 'IN_TRANSIT', 'courier')
    final = advance(s, 'DELIVERED', 'courier')
    assert final['pickedUpAt'] and final['deliveredAt']
    assert 'total' not in final and 'items' not in final and 'userId' not in final
    public = s['api'].get(f"/api/orders/{final['id']}", headers=s['customer']).json()['order']
    assert public['driverVerified'] is True
    assert len(public['events']) == 7
    assert all('actor_id' not in e and 'motivo' not in e for e in public['events'])
    claim = s['api'].post('/api/claims', headers=s['customer'], json={
        'customer_name': 'Cliente', 'customer_email': 'jhan.perez@gmail.com', 'order_code': public['code'],
        'description': 'El producto recibido era diferente al solicitado', 'analyze': True})
    assert claim.status_code == 201
    cid = claim.json()['claim']['id']
    context = s['api'].get(f'/api/claims/{cid}/order-context', headers=s['agent']).json()
    assert context['order']['status'] == 'DELIVERED'
    assert context['order']['events'][-1]['actor_rol'] == 'COURIER'
    detail = s['api'].get(f'/api/claims/{cid}', headers=s['agent']).json()
    assert detail['analysis'] and detail['response']
    assert s['api'].post(f"/api/responses/{detail['response']['id']}/approve", headers=s['agent']).status_code == 200
    assert s['api'].get(f'/api/claims/{cid}', headers=s['customer']).json()['response']['finalResponse']


@pytest.mark.parametrize('name', ['foreign', 'othercourier'])
def test_cross_tenant_access_and_write_denied(scenario, name):
    s = scenario
    assert s['api'].get(f"/api/orders/{s['order']['id']}", headers=s['tokens'][name]).status_code == 403
    assert s['api'].get('/api/orders', headers=s['tokens'][name]).json()['items'] == []
    assert s['api'].post(f"/api/orders/{s['order']['id']}/transition", headers=s['tokens'][name], json={
        'state': 'ACCEPTED', 'expected_version': 0, 'request_id': key()}).status_code == 403


@pytest.mark.parametrize('role', ['customer', 'agent'])
def test_readonly_roles_cannot_operate(scenario, role):
    s = scenario
    assert s['api'].post(f"/api/orders/{s['order']['id']}/transition", headers=s[role], json={
        'state': 'ACCEPTED', 'expected_version': 0, 'request_id': key()}).status_code == 403
    assert s['api'].post(f"/api/orders/{s['order']['id']}/assignment", headers=s[role], json={
        'courier_id': s['users']['courier']['id_auth_user'], 'expected_version': 0, 'request_id': key(), 'reason': 'test'}).status_code == 403


def test_merchant_and_courier_cannot_read_private_claims(scenario):
    s = scenario
    for token in s['tokens'].values():
        assert s['api'].get('/api/claims', headers=token).status_code == 403
        for suffix in ['', '/messages', '/order-context']:
            assert s['api'].get('/api/claims/1' + suffix, headers=token).status_code == 403
        assert s['api'].post('/api/claims/1/messages', headers=token, json={'message': 'Access attempt'}).status_code == 403
        assert s['api'].get('/api/config', headers=token).status_code == 403


def test_invalid_transitions_retries_and_final_state(scenario):
    s = scenario
    oid = int(s['order']['id'])
    merchant = s['users']['merchant']
    request = key()
    with pytest.raises(DomainError):
        workflow.transition(oid, merchant, 'DELIVERED', 0, key())
    workflow.transition(oid, merchant, 'ACCEPTED', 0, request)
    workflow.transition(oid, merchant, 'ACCEPTED', 0, request)
    with pytest.raises(DomainError):
        workflow.transition(oid, merchant, 'PREPARING', 1, request)
    assert db.fetch_one('SELECT COUNT(*) AS n FROM pedido_eventos WHERE id_pedido=?', (oid,))['n'] == 2
    advance(s, 'CANCELLED', 'admin', 'Cliente solicitó cancelar')
    with pytest.raises(DomainError):
        workflow.transition(oid, merchant, 'ACCEPTED', s['order']['version'], key())


def test_concurrent_incompatible_transitions(scenario):
    s = scenario
    def attempt(state):
        try:
            workflow.transition(int(s['order']['id']), s['users']['merchant'], state, 0, key(), 'Rechazo justificado')
            return 200
        except DomainError:
            return 409
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, ['ACCEPTED', 'CANCELLED'])) == [200, 409]
    assert db.fetch_one('SELECT version_operativa FROM pedidos WHERE id_pedido=?', (s['order']['id'],))['version_operativa'] == 1


def test_assignment_requires_ready_available_and_active_and_tracks_reassignment(scenario):
    s = scenario
    payload = {'courier_id': s['users']['courier']['id_auth_user'], 'expected_version': 0, 'request_id': key(), 'reason': 'Asignación'}
    path = f"/api/orders/{s['order']['id']}/assignment"
    assert s['api'].post(path, headers=s['admin'], json=payload).status_code == 409
    ready(s)
    payload['expected_version'] = s['order']['version']
    assert s['api'].post(path, headers=s['admin'], json=payload).status_code == 409
    assign(s)
    assign(s, 'othercourier')
    assert s['api'].get(f"/api/orders/{s['order']['id']}", headers=s['tokens']['courier']).status_code == 403
    assignments = db.fetch_all("SELECT * FROM pedido_eventos WHERE accion='ASSIGN'")
    assert len(assignments) == 2
    advance(s, 'IN_TRANSIT', 'othercourier')
    payload['expected_version'] = s['order']['version']
    payload['request_id'] = key()
    assert s['api'].post(path, headers=s['admin'], json=payload).status_code == 409


def test_admin_reason_last_admin_and_live_role_revocation(scenario):
    s = scenario
    assert s['api'].post(f"/api/orders/{s['order']['id']}/transition", headers=s['admin'], json={
        'state': 'ACCEPTED', 'expected_version': 0, 'request_id': key()}).status_code == 422
    uid = db.fetch_one("SELECT id_auth_user FROM auth_users WHERE rol='ADMIN'")['id_auth_user']
    assert s['api'].patch(f'/api/operations/users/{uid}', headers=s['admin'], json={
        'role': 'CLIENT', 'active': True, 'request_id': key(), 'reason': 'Cambio'}).status_code == 409
    assert s['api'].patch(f"/api/operations/users/{s['users']['merchant']['id_auth_user']}", headers=s['admin'], json={
        'role': 'CLIENT', 'active': True, 'request_id': key(), 'reason': 'Revocar rol'}).status_code == 200
    assert s['api'].get('/api/auth/me', headers=s['tokens']['merchant']).json()['user']['role'] == 'CLIENT'
    assert s['api'].get(f"/api/orders/{s['order']['id']}", headers=s['tokens']['merchant']).status_code == 403
    assert db.fetch_one('SELECT activo FROM comercio_operadores WHERE id_auth_user=?', (s['users']['merchant']['id_auth_user'],))['activo'] == 0
    assert s['api'].patch(f"/api/operations/users/{s['users']['merchant']['id_auth_user']}", headers=s['admin'], json={
        'role': 'MERCHANT', 'active': True, 'request_id': key(), 'reason': 'Restaurar solamente rol'}).status_code == 200
    assert s['api'].get(f"/api/orders/{s['order']['id']}", headers=s['tokens']['merchant']).status_code == 403


def test_product_grant_and_historical_snapshot(scenario):
    s = scenario
    path = f"/api/operations/products/{s['product']['id_producto']}"
    payload = {'name': 'Producto cambiado', 'price': 99, 'available': False, 'request_id': key()}
    assert s['api'].patch(path, headers=s['tokens']['merchant'], json=payload).status_code == 403
    assert s['api'].patch(path, headers=s['tokens']['courier'], json=payload).status_code == 403
    assert s['api'].put(f"/api/operations/restaurants/{s['restaurant']}/operator", headers=s['admin'], json={
        'user_id': s['users']['merchant']['id_auth_user'], 'active': True, 'edit_products': True,
        'reason': 'Autorización productos', 'request_id': key()}).status_code == 200
    assert s['api'].patch(path, headers=s['tokens']['merchant'], json=payload).status_code == 200
    saved = s['api'].get(f"/api/orders/{s['order']['id']}", headers=s['customer']).json()['order']
    assert saved['items'] == s['order']['items']
    assert saved['total'] == s['order']['total']


def test_migration_preserves_real_copy_and_rollback(monkeypatch, tmp_path):
    original = Path(__file__).resolve().parents[1] / 'data/smartclaim.db'
    copy = tmp_path / 'historical-copy.db'
    with sqlite3.connect(original.as_uri() + '?mode=ro', uri=True) as source, sqlite3.connect(copy) as target:
        source.backup(target)
    monkeypatch.setattr(db, 'DB_PATH', copy)
    db.run_script(db.BASE_DIR / 'database/schema.sql')
    tables = ['auth_users', 'pedidos', 'pedido_items', 'reclamos', 'clientes']
    before = {table: db.fetch_all(f'SELECT * FROM {table} ORDER BY 1') for table in tables}
    phase2b.apply()
    phase2b.apply()
    for table, rows in before.items():
        after = db.fetch_all(f'SELECT * FROM {table} ORDER BY 1')
        assert [{field: row[field] for field in rows[0]} for row in after] == rows
    phase2b.rollback_sqlite()
    phase2b.apply()
    assert len(db.fetch_all('SELECT * FROM pedidos')) == len(before['pedidos'])


def test_migration_rollback_refuses_new_role(scenario):
    with pytest.raises(RuntimeError, match='roles nuevos'):
        phase2b.rollback_sqlite()
    assert db.fetch_one('SELECT version FROM schema_migrations WHERE version=?', (phase2b.VERSION,))


def test_normal_startup_does_not_seed_or_migrate(monkeypatch):
    from backend import main
    monkeypatch.delenv('SMARTCLAIM_BOOTSTRAP_DEMO', raising=False)
    def forbidden():
        raise AssertionError('No automatic data mutation on normal startup')
    for name in ['init_db', 'asegurar_usuarios_auth_base', 'asegurar_pedidos_demo_base']:
        monkeypatch.setattr(main, name, forbidden)
    with TestClient(main.app) as api:
        assert api.get('/openapi.json').status_code == 200


def test_order_creation_retry_and_changed_payload(scenario):
    s = scenario
    items = [{'product_id': s['product']['id_producto'], 'quantity': 1}]
    quote = s['api'].post('/api/orders/quote', json={'items': items}).json()
    payload = {'items': items, 'quote_hash': quote['quoteHash'], 'payment_method': 'Efectivo',
               'delivery_address': 'Dirección de prueba', 'request_id': key()}
    first = s['api'].post('/api/orders', headers=s['customer'], json=payload)
    assert first.status_code == 201
    second = s['api'].post('/api/orders', headers=s['customer'], json=payload)
    assert second.status_code == 201 and second.json()['order']['id'] == first.json()['order']['id']
    assert s['api'].post('/api/orders', headers=s['customer'], json={**payload, 'delivery_address': 'Otra dirección'}).status_code == 409


def test_delay_keeps_operational_phase_and_actor_snapshot(scenario):
    s = scenario
    path = f"/api/orders/{s['order']['id']}/delay"
    payload = {'expected_version': 0, 'request_id': key(), 'reason': 'Demora informada por cocina'}
    assert s['api'].post(path, headers=s['tokens']['merchant'], json=payload).status_code == 200
    assert s['api'].post(path, headers=s['tokens']['merchant'], json=payload).status_code == 200
    order = s['api'].get(f"/api/orders/{s['order']['id']}", headers=s['admin']).json()['order']
    assert order['status'] == 'RECEIVED' and order['version'] == 1
    event = order['events'][-1]
    db.execute("UPDATE auth_users SET nombre='Nombre cambiado' WHERE id_auth_user=?", (s['users']['merchant']['id_auth_user'],))
    assert event['actor_nombre'] == s['users']['merchant']['nombre']
    assert event['actor_id'] == s['users']['merchant']['id_auth_user']
    assert event['accion'] == 'DELAY_REPORTED'


def test_concurrent_assignment_and_pickup(scenario):
    s = scenario
    ready(s)
    for name in ['courier', 'othercourier']:
        s['api'].put('/api/operations/availability', headers=s['tokens'][name], json={'available': True, 'request_id': key()})
    admin = db.fetch_one("SELECT * FROM auth_users WHERE rol='ADMIN'")
    def attempt(name):
        try:
            workflow.assign(int(s['order']['id']), admin, s['users'][name]['id_auth_user'], s['order']['version'], key(), 'Despacho')
            return 200
        except DomainError:
            return 409
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(attempt, ['courier', 'othercourier'])) == [200, 409]
    version = s['order']['version'] + 1
    def pickup(name):
        try:
            workflow.transition(int(s['order']['id']), s['users'][name], 'IN_TRANSIT', version, key())
            return 200
        except DomainError:
            return 403
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(pickup, ['courier', 'othercourier'])) == [200, 403]


def test_vector_mismatch_never_deletes_or_reindexes(monkeypatch):
    monkeypatch.setattr(db, 'using_postgres', lambda: True)
    monkeypatch.setattr(db, 'fetch_one', lambda *args: {'vector_type': 'vector(3)'})
    monkeypatch.setattr(db, 'execute', lambda *args: pytest.fail('No destructive automatic vector resizing'))
    with pytest.raises(RuntimeError, match='migración explícita'):
        db.ensure_pgvector_embedding_dimension()
