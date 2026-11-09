from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from database import db_connection as db
from database.migrations import phase2b, phase2c
from modules import claim_assignment, notification_service, response_service
from modules.claim_workflow import record_message
from modules.domain_errors import DomainError
from test_phase1_acceptance import auth, new_claim
from test_phase2b_acceptance import scenario


@pytest.fixture
def api():
    from backend.main import app
    with TestClient(app) as client:
        yield client


def key():
    return str(uuid4())


def user(role):
    return db.fetch_one("SELECT * FROM auth_users WHERE rol=? AND estado='ACTIVO' ORDER BY id_auth_user LIMIT 1", (role,))


def assign(api, detail, target=None, headers=None, **changes):
    payload = dict(assignee_id=target or user('AGENT')['id_auth_user'], expected_version=detail['claim']['assignment']['version'],
                   request_id=key(), reason='Responsabilidad para seguimiento')
    payload.update(changes)
    return api.post(f"/api/claims/{detail['claim']['id']}/assignment", headers=headers or auth(api, 'ADMIN'), json=payload)


def test_new_claim_queue_and_exactly_once_creation(api):
    client = auth(api)
    order = api.get('/api/orders', headers=client).json()['items'][0]
    payload = dict(customer_name='Cliente', customer_email='jhan.perez@gmail.com', order_code=order['code'],
                   description='Incidente sobre mi pedido registrado', analyze=False, request_id=key())
    first = api.post('/api/claims', headers=client, json=payload)
    second = api.post('/api/claims', headers=client, json=payload)
    assert first.status_code == second.status_code == 201
    cid = first.json()['claim']['id']
    assert second.json()['claim']['id'] == cid
    queue = api.get('/api/claims?assignment=UNASSIGNED', headers=auth(api, 'AGENT')).json()['items']
    assert cid in [item['id'] for item in queue]
    notes = db.fetch_all("SELECT * FROM notificaciones WHERE id_reclamo=? AND evento='CLAIM_CREATED'", (cid,))
    assert len(notes) == 2 and {row['id_destinatario'] for row in notes} == {user('AGENT')['id_auth_user'], user('ADMIN')['id_auth_user']}
    assert api.post('/api/claims', headers=client, json={**payload, 'description': 'Un contenido diferente sobre este caso'}).status_code == 409


def test_assignment_reassignment_history_and_live_ownership(api):
    detail = new_claim(api, False)
    db.execute('UPDATE reclamos SET responsable_asignado=? WHERE id_reclamo=?', ('LEGACY-RESPONSIBLE-SNAPSHOT', detail['claim']['id']))
    assigned = assign(api, detail)
    assert assigned.status_code == 200
    detail = assigned.json()
    assert detail['claim']['assignment']['id'] == user('AGENT')['id_auth_user']
    assert detail['claim']['assignment']['assignedAt']
    mine = api.get('/api/claims?assignment=MINE', headers=auth(api, 'AGENT')).json()['items']
    assert detail['claim']['id'] in [item['id'] for item in mine]
    changed = assign(api, detail, user('ADMIN')['id_auth_user'])
    assert changed.status_code == 200
    history = changed.json()['history']
    assignment_events = [event for event in history if 'Asignación' in event['action'] or 'Reasignación' in event['action']]
    assert len(assignment_events) == 2
    assert all(event['actorId'] == user('ADMIN')['id_auth_user'] for event in assignment_events)
    assert all(event['actorRole'] == 'ADMIN' for event in assignment_events)
    assert any('LEGACY-RESPONSIBLE-SNAPSHOT' in event['comment'] for event in assignment_events)
    assert 'destinatario ID' in assignment_events[0]['comment']


def test_assignment_inactive_duplicate_role_and_client_rejected(api):
    detail = new_claim(api, False)
    target = user('AGENT')['id_auth_user']
    assert assign(api, detail, headers=auth(api)).status_code == 403
    assert assign(api, detail, target=user('CLIENT')['id_auth_user']).status_code == 422
    db.execute("UPDATE auth_users SET estado='INACTIVO' WHERE id_auth_user=?", (target,))
    assert assign(api, detail, target=target).status_code == 422


def test_agent_can_assume_only_unassigned_own_case(api):
    detail = new_claim(api, False)
    assert assign(api, detail, target=user('ADMIN')['id_auth_user'], headers=auth(api, 'AGENT')).status_code == 403
    own = assign(api, detail, headers=auth(api, 'AGENT'))
    assert own.status_code == 200
    assert assign(api, own.json(), headers=auth(api, 'AGENT')).status_code == 403


def test_assignment_race_and_retry_payload(api):
    detail = new_claim(api, False)
    cid = int(detail['claim']['id'])
    admin, agent = user('ADMIN'), user('AGENT')
    def attempt(target):
        try:
            claim_assignment.assign(cid, admin, target, 0, key(), 'Asignación concurrente')
            return True
        except DomainError:
            return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(attempt, [admin['id_auth_user'], agent['id_auth_user']])) == 1
    assert db.fetch_one('SELECT version_asignacion FROM reclamos WHERE id_reclamo=?', (cid,))['version_asignacion'] == 1
    request_id = db.fetch_one('SELECT request_id FROM claim_commands WHERE id_reclamo=? AND accion=\'ASSIGN\'', (cid,))['request_id']
    saved = db.fetch_one('SELECT * FROM claim_commands WHERE request_id=?', (request_id,))
    target, version, reason = json.loads(saved['payload'])
    before = db.fetch_one('SELECT COUNT(*) AS n FROM notificaciones')['n']
    claim_assignment.assign(cid, admin, target, version, request_id, reason)
    assert db.fetch_one('SELECT COUNT(*) AS n FROM notificaciones')['n'] == before
    with pytest.raises(DomainError):
        claim_assignment.assign(cid, admin, target, version, request_id, 'Motivo cambiado')


def test_escalation_has_admin_destination_reason_history_and_no_duplicate(api):
    detail = assign(api, new_claim(api, False), headers=auth(api, 'AGENT')).json()
    cid = detail['claim']['id']
    payload = dict(expected_version=1, reason='Necesita revisión de una persona administradora', request_id=key())
    path = f'/api/claims/{cid}/escalate'
    response = api.post(path, headers=auth(api, 'AGENT'), json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data['claim']['statusKey'] == 'ESCALATED'
    assert data['claim']['closedAt'] is None
    assert data['claim']['assignment']['id'] == user('ADMIN')['id_auth_user']
    assert api.post(path, headers=auth(api, 'AGENT'), json=payload).status_code == 200
    assert api.post(path, headers=auth(api, 'AGENT'), json={**payload, 'expected_version': 2, 'request_id': key()}).status_code == 403
    assert api.post(path, headers=auth(api, 'ADMIN'), json={**payload, 'expected_version': 2, 'request_id': key()}).status_code == 409
    notifications = api.get('/api/notifications', headers=auth(api, 'ADMIN')).json()
    assert len([item for item in notifications['items'] if item['claimId'] == cid and item['event'] == 'CLAIM_ESCALATED']) == 1
    assert any('Escalamiento' in event['action'] and payload['reason'] in event['comment'] for event in data['history'])
    assert api.get('/api/claims?assignment=MINE', headers=auth(api, 'ADMIN')).json()['items'][0]['id'] == cid


def test_escalation_requires_reason_and_active_admin(api):
    detail = new_claim(api, False)
    path = f"/api/claims/{detail['claim']['id']}/escalate"
    base = dict(expected_version=0, request_id=key(), reason='   ')
    assert api.post(path, headers=auth(api, 'AGENT'), json=base).status_code == 422
    db.execute("UPDATE auth_users SET estado='INACTIVO' WHERE rol='ADMIN'")
    assert api.post(path, headers=auth(api, 'AGENT'), json={**base, 'reason': 'Revisión sensible'}).status_code == 422
    assert db.fetch_one('SELECT version_asignacion FROM reclamos WHERE id_reclamo=?', (detail['claim']['id'],))['version_asignacion'] == 0


def test_published_once_draft_silent_and_reviewer_identified(api):
    detail = new_claim(api)
    rid, cid = detail['response']['id'], detail['claim']['id']
    before = api.get('/api/notifications', headers=auth(api)).json()['unread']
    assert api.patch(f'/api/responses/{rid}', headers=auth(api, 'AGENT'), json={'response_text': 'INTERNAL-PRIVATE-TEST-DRAFT'}).status_code == 200
    assert api.get('/api/notifications', headers=auth(api)).json()['unread'] == before
    for _ in range(2):
        assert api.post(f'/api/responses/{rid}/approve', headers=auth(api, 'AGENT')).status_code == 200
    assert api.get('/api/notifications', headers=auth(api)).json()['unread'] == before + 1
    note = db.fetch_one("SELECT mensaje FROM notificaciones WHERE id_reclamo=? AND evento='CLAIM_PUBLISHED'", (cid,))
    assert 'PRIVATE' not in note['mensaje']
    assert db.fetch_one('SELECT revisor_auth_id FROM respuestas_sugeridas WHERE id_respuesta=?', (rid,))['revisor_auth_id'] == user('AGENT')['id_auth_user']


def test_message_counter_read_one_all_and_persistence(api):
    detail = new_claim(api, False)
    client, agent = auth(api), auth(api, 'AGENT')
    api.patch('/api/notifications/read', headers=client)
    cid = detail['claim']['id']
    for index in range(4):
        body = {'message': f'Mensaje de seguimiento {index}', 'request_id': key()}
        for _ in range(2):
            assert api.post(f'/api/claims/{cid}/messages', headers=agent, json=body).status_code == 201
        assert api.get('/api/notifications', headers=client).json()['unread'] == index + 1
    notes = api.get('/api/notifications', headers=auth(api)).json()
    nid = notes['items'][0]['id']
    assert api.patch(f'/api/notifications/{nid}/read', headers=client).json()['unread'] == 3
    assert api.patch(f'/api/notifications/{nid}/read', headers=client).json()['unread'] == 3
    assert api.patch('/api/notifications/read', headers=client).json()['unread'] == 0
    assert api.get('/api/notifications', headers=auth(api)).json()['unread'] == 0


def test_unread_counts_beyond_twenty_and_foreign_reads_denied(api):
    owner = user('CLIENT')
    from database.transactions import transaction
    with transaction() as conn:
        for index in range(27):
            notification_service.emit(conn, owner['correo'], 'ORDER_TEST', None, f'unit-{index}', 'Aviso de prueba', 'Sin contenido privado', order=True)
    result = api.get('/api/notifications', headers=auth(api)).json()
    assert len(result['items']) == 20 and result['unread'] >= 27
    nid = result['items'][0]['id']
    assert api.patch(f'/api/notifications/{nid}/read', headers=auth(api, 'AGENT')).status_code == 404
    assert api.patch('/api/notifications/9999999/read', headers=auth(api)).status_code == 404


def test_message_and_assignment_rollback_if_notification_fails(api, monkeypatch):
    detail = new_claim(api, False)
    cid = int(detail['claim']['id'])
    count = db.fetch_one('SELECT COUNT(*) AS n FROM claim_messages WHERE id_reclamo=?', (cid,))['n']
    def fail(*args, **kwargs):
        raise RuntimeError('Isolated notification persistence failure')
    monkeypatch.setattr(notification_service, 'emit', fail)
    with pytest.raises(RuntimeError):
        record_message(cid, 'Mensaje que debe revertirse', user('AGENT'), key())
    assert db.fetch_one('SELECT COUNT(*) AS n FROM claim_messages WHERE id_reclamo=?', (cid,))['n'] == count
    monkeypatch.setattr(claim_assignment, 'emit', fail)
    with pytest.raises(RuntimeError):
        claim_assignment.assign(cid, user('ADMIN'), user('AGENT')['id_auth_user'], 0, key(), 'Prueba de rollback')
    assert db.fetch_one('SELECT responsable_auth_id FROM reclamos WHERE id_reclamo=?', (cid,))['responsable_auth_id'] is None


def test_close_reopen_notifies_once_and_identifies_actors(api):
    detail = new_claim(api, False)
    cid = detail['claim']['id']
    agent, client = auth(api, 'AGENT'), auth(api)
    close_key, reopen_key = key(), key()
    for _ in range(2):
        assert api.post(f'/api/claims/{cid}/close', headers=agent, json={'comment': 'Cierre administrativo justificado', 'request_id': close_key}).status_code == 200
    for _ in range(2):
        assert api.post(f'/api/claims/{cid}/reopen', headers=client, json={'request_id': reopen_key}).status_code == 200
    for event in ['CLAIM_CLOSED', 'CLAIM_REOPENED']:
        assert db.fetch_one('SELECT COUNT(*) AS n FROM notificaciones WHERE id_reclamo=? AND evento=? AND id_destinatario=?', (cid, event, user('CLIENT')['id_auth_user']))['n'] == 1
    history = api.get(f'/api/claims/{cid}', headers=agent).json()['history']
    assert any(event['actorId'] == user('CLIENT')['id_auth_user'] and 'Reapertura' in event['action'] for event in history)


def test_inactive_owner_is_visible_in_queue_without_losing_history(api):
    detail = assign(api, new_claim(api, False)).json()
    target = user('AGENT')['id_auth_user']
    db.execute("UPDATE auth_users SET estado='INACTIVO' WHERE id_auth_user=?", (target,))
    data = api.get('/api/claims?assignment=UNASSIGNED', headers=auth(api, 'ADMIN')).json()['items']
    assert detail['claim']['id'] in [item['id'] for item in data]
    assert assign(api, detail, target=user('ADMIN')['id_auth_user']).status_code == 200
    assert db.fetch_one('SELECT COUNT(*) AS n FROM claim_commands WHERE id_reclamo=? AND accion=\'ASSIGN\'', (detail['claim']['id'],))['n'] == 2


def test_additive_migration_on_real_copy_preserves_history(monkeypatch, tmp_path):
    original = Path(__file__).resolve().parents[1] / 'data/smartclaim.db'
    copy = tmp_path / 'copy.db'
    with sqlite3.connect(original.as_uri() + '?mode=ro', uri=True) as source, sqlite3.connect(copy) as target:
        source.backup(target)
    monkeypatch.setattr(db, 'DB_PATH', copy)
    db.run_script(db.BASE_DIR / 'database/schema.sql')
    tables = ['reclamos', 'notificaciones', 'auth_users', 'historial_estados', 'respuestas_sugeridas']
    old = {table: db.fetch_all(f'SELECT * FROM {table} ORDER BY 1') for table in tables}
    phase2b.apply()
    phase2c.apply()
    phase2c.apply()
    for table, rows in old.items():
        now = db.fetch_all(f'SELECT * FROM {table} ORDER BY 1')
        assert [{column: row[column] for column in rows[0]} for row in now] == rows
    assert all(row['responsable_auth_id'] is None for row in db.fetch_all('SELECT responsable_auth_id FROM reclamos'))


@pytest.mark.parametrize('name', ['merchant', 'courier'])
def test_operational_roles_only_receive_authorized_order_notifications(scenario, name):
    s = scenario
    api, token = s['api'], s['tokens'][name]
    owner = s['users'][name]
    created = api.post('/api/claims', headers=s['customer'], json={
        'customer_name': 'Cliente', 'customer_email': 'jhan.perez@gmail.com', 'order_code': s['order']['code'],
        'description': 'Contexto privado del reclamo de prueba', 'analyze': False})
    assert created.status_code == 201
    cid = int(created.json()['claim']['id'])
    from database.transactions import transaction
    with transaction() as conn:
        notification_service.emit(conn, owner['correo'], 'CLAIM_ASSIGNED', cid, key(), 'Privado', 'PRIVATE-NOTIFICATION-MARKER')
    listing = api.get('/api/notifications', headers=token).json()
    assert 'PRIVATE-NOTIFICATION-MARKER' not in json.dumps(listing)
    assert all(item['claimId'] is None for item in listing['items'])
    assert api.get('/api/claim-assignees', headers=token).status_code == 403
    assert api.post('/api/claims/1/assignment', headers=token, json={
        'assignee_id': owner['id_auth_user'], 'expected_version': 0, 'request_id': key(), 'reason': 'Prohibido'}).status_code == 403
    if name == 'merchant':
        assert any(item['orderId'] == s['order']['id'] and item['event'] == 'ORDER_CREATED' for item in listing['items'])
    secret_id = db.fetch_one("SELECT id_notificacion FROM notificaciones WHERE titulo='Privado'")['id_notificacion']
    assert api.patch(f'/api/notifications/{secret_id}/read', headers=token).status_code == 404


def test_message_retries_concurrent_and_read_race_are_consistent(api):
    detail = new_claim(api, False)
    cid = int(detail['claim']['id'])
    actor = user('AGENT')
    request = key()
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda _: record_message(cid, 'Mensaje único concurrente', actor, request), range(4)))
    assert db.fetch_one("SELECT COUNT(*) AS n FROM claim_messages WHERE id_reclamo=? AND sender_type='agent'", (cid,))['n'] == 1
    assert db.fetch_one("SELECT COUNT(*) AS n FROM notificaciones WHERE id_reclamo=? AND evento='AGENT_MESSAGE'", (cid,))['n'] == 1
    target = user('CLIENT')
    nid = db.fetch_one("SELECT id_notificacion FROM notificaciones WHERE id_reclamo=? AND evento='AGENT_MESSAGE'", (cid,))['id_notificacion']
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(lambda value: notification_service.mark_read(target, value), [nid, None]))
    assert api.get('/api/notifications', headers=auth(api)).json()['unread'] == 0


def test_postgres_conflict_insert_contract_returns_none(monkeypatch):
    from database import transactions
    monkeypatch.setattr(transactions, 'using_postgres', lambda: True)
    class Cursor:
        def fetchone(self):
            return None
    class Connection:
        def execute(self, query, params):
            assert 'RETURNING id_notificacion' in query
            assert 'ON CONFLICT' in query
            return Cursor()
    assert transactions.insert(Connection(), "INSERT INTO notificaciones(clave_evento) VALUES (?) ON CONFLICT DO NOTHING", ('key',)) is None


def test_demo_seed_transaction_rolls_back_on_error(tmp_path):
    script = tmp_path / 'broken-seed.sql'
    script.write_text('CREATE TABLE seed_atomicity(id INTEGER); INSERT INTO seed_atomicity VALUES (1); INSERT INTO absent_table VALUES (1);', encoding='utf-8')
    with pytest.raises(sqlite3.OperationalError):
        db.run_script(script, transactional=True)
    assert not db.table_exists('seed_atomicity')
