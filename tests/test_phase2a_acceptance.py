import json

import pytest
from fastapi.testclient import TestClient

from database import db_connection as db


@pytest.fixture
def api():
    from backend.main import app
    with TestClient(app) as client:
        yield client


def auth(api, role='ADMIN'):
    email = {'ADMIN': 'admin@smartclaim.com', 'AGENT': 'gonzalo.caceres@smartclaim.com', 'CLIENT': 'jhan.perez@gmail.com'}[role]
    result = api.post('/api/auth/login', json={'email': email, 'password': '123456'})
    assert result.status_code == 200
    return {'Authorization': 'Bearer ' + result.json()['token']}


def desired(config, **changes):
    return dict(config_id=config['id'], confidence_threshold=.6, human_review_required=False,
                use_rag=False, max_documents=1, **changes)


@pytest.mark.parametrize('threshold,max_docs', [(0, 1), (1, 10), (.6, 1), (.8532, 7)])
def test_bf14_roundtrip_stable_id_and_renamed_configuration(api, threshold, max_docs):
    headers = auth(api)
    config = api.get('/api/config', headers=headers).json()
    db.execute('UPDATE configuracion_modelo_ia SET nombre_configuracion=? WHERE id_configuracion=?', ('Nombre elegido por usuario', config['id']))
    payload = desired(config)
    payload.update(confidence_threshold=threshold, max_documents=max_docs)
    saved = api.put('/api/config', headers=headers, json=payload)
    assert saved.status_code == 200
    reread = api.get('/api/config', headers=headers).json()
    assert reread['id'] == config['id'] and reread['confidenceThreshold'] == pytest.approx(threshold)
    assert reread['maxDocuments'] == max_docs and not reread['humanReviewRequired'] and not reread['useRag']
    assert db.fetch_one('SELECT nombre_configuracion FROM configuracion_modelo_ia WHERE id_configuracion=?', (config['id'],))['nombre_configuracion'] == 'Nombre elegido por usuario'


def test_bf14_multiple_active_rows_remain_intact_and_stale_id_is_rejected(api):
    headers = auth(api)
    old = api.get('/api/config', headers=headers).json()
    before = db.fetch_one('SELECT * FROM configuracion_modelo_ia WHERE id_configuracion=?', (old['id'],))
    new_id = db.execute("INSERT INTO configuracion_modelo_ia(nombre_configuracion) VALUES ('Otra activa heredada')")
    active = api.get('/api/config', headers=headers).json()
    assert active['id'] == new_id and active['activeCount'] >= 2
    assert active['selectionPolicy'] == 'highest_active_id'
    assert api.put('/api/config', headers=headers, json=desired(old)).status_code == 409
    assert api.put('/api/config', headers=headers, json=desired(active)).status_code == 200
    assert db.fetch_one('SELECT * FROM configuracion_modelo_ia WHERE id_configuracion=?', (old['id'],)) == before


def test_bf14_workspace_configuration_copy_preserves_other_rows(tmp_path, monkeypatch):
    import sqlite3
    from pathlib import Path
    from database.repositories import get_configuracion_activa, actualizar_configuracion
    source = Path(__file__).resolve().parents[1] / 'data/smartclaim.db'
    copy = tmp_path / 'config-copy.db'
    original = sqlite3.connect(source.as_uri() + '?mode=ro', uri=True)
    target = sqlite3.connect(copy)
    try:
        original.backup(target)
    finally:
        target.close()
        original.close()
    monkeypatch.setattr(db, 'DB_PATH', copy)
    before = db.fetch_all('SELECT * FROM configuracion_modelo_ia ORDER BY id_configuracion')
    active = get_configuracion_activa()
    assert active is not None
    actualizar_configuracion(.6, False, False, 1, active['id_configuracion'])
    after = db.fetch_all('SELECT * FROM configuracion_modelo_ia ORDER BY id_configuracion')
    assert len(before) == len(after)
    assert [row for row in before if row['id_configuracion'] != active['id_configuracion']] == [row for row in after if row['id_configuracion'] != active['id_configuracion']]
    assert get_configuracion_activa()['umbral_confianza'] == .6


def test_bf14_no_active_row_or_wrong_id_never_reports_saved(api):
    headers = auth(api)
    config = api.get('/api/config', headers=headers).json()
    assert api.put('/api/config', headers=headers, json={**desired(config), 'config_id': 999999}).status_code == 409
    db.execute('UPDATE configuracion_modelo_ia SET activo=0')
    assert api.get('/api/config', headers=headers).status_code == 409
    assert api.put('/api/config', headers=headers, json=desired(config)).status_code == 409


@pytest.mark.parametrize('role', ['CLIENT', 'AGENT'])
def test_bf14_admin_permissions_are_preserved(api, role):
    headers = auth(api, role)
    assert api.get('/api/config', headers=headers).status_code == 403
    assert api.put('/api/config', headers=headers, json=desired({'id': 1})).status_code == 403


@pytest.mark.parametrize('changes', [{'confidence_threshold': -0.1}, {'confidence_threshold': 1.1}, {'max_documents': 0}, {'max_documents': 11}, {'max_documents': True}, {'config_id': True}])
def test_bf14_rejects_invalid_values(api, changes):
    headers = auth(api)
    config = api.get('/api/config', headers=headers).json()
    assert api.put('/api/config', headers=headers, json={**desired(config), **changes}).status_code == 422


@pytest.mark.parametrize('trigger', [
    "CREATE TRIGGER test_ignore_config BEFORE UPDATE ON configuracion_modelo_ia BEGIN SELECT RAISE(IGNORE); END",
    "CREATE TRIGGER test_override_config AFTER UPDATE ON configuracion_modelo_ia BEGIN UPDATE configuracion_modelo_ia SET usar_rag=1 WHERE id_configuracion=NEW.id_configuracion; END",
])
def test_bf14_zero_updates_or_failed_readback_rolls_back(api, trigger):
    headers = auth(api)
    config = api.get('/api/config', headers=headers).json()
    db.execute(trigger)
    assert api.put('/api/config', headers=headers, json=desired(config)).status_code == 409
    assert api.get('/api/config', headers=headers).json()['confidenceThreshold'] == config['confidenceThreshold']


def test_bf14_runtime_uses_trace_evidence_and_does_not_train(api, monkeypatch, tmp_path):
    from modules import classifier
    headers = auth(api)
    monkeypatch.setattr(classifier, 'MODEL_PATH', tmp_path / 'absent.joblib')
    monkeypatch.setattr(classifier, '_train_model_if_needed', lambda: pytest.fail('Status must never train'))
    initial = api.get('/api/config', headers=headers).json()
    assert initial['runtime'] == {'classifierArtifactPresent': False, 'lastExecution': None}
    assert initial['model'] == db.fetch_one('SELECT modelo_base FROM configuracion_modelo_ia WHERE id_configuracion=?', (initial['id'],))['modelo_base']
    from database.repositories import registrar_log
    registrar_log('Flujo IA', 'request_completed', detalle=json.dumps({'classification_model': 'modelo_reglas_mejorado', 'generation_strategy': 'basic_template', 'openai_used': False, 'outcome': 'ok'}))
    actual = api.get('/api/config', headers=headers).json()['runtime']['lastExecution']
    assert actual['classifierModel'] == 'modelo_reglas_mejorado' and actual['openaiUsed'] is False
    assert actual['generationStrategy'] == 'basic_template'


def test_bf14_new_claim_records_the_actual_classifier(api):
    customer = auth(api, 'CLIENT')
    order = api.get('/api/orders', headers=customer).json()['items'][0]
    result = api.post('/api/claims', headers=customer, json=dict(customer_name='Jhan Perez', customer_email='jhan.perez@gmail.com',
        order_code=order['code'], description='Me cobraron dos veces el mismo pedido', analyze=True))
    assert result.status_code == 201
    staff = auth(api)
    detail = api.get('/api/claims/' + result.json()['claim']['id'], headers=staff).json()
    runtime = api.get('/api/config', headers=staff).json()['runtime']['lastExecution']
    assert runtime['classifierModel'] == detail['analysis']['model']
    assert runtime['openaiUsed'] is False


def test_bf14_postgres_lock_contract_with_isolated_sqlite_stub(api, monkeypatch):
    from modules import config_service
    config = api.get('/api/config', headers=auth(api)).json()
    actual_one, queries = config_service.one, []
    def adapted(conn, query, params=()):
        queries.append(query)
        return actual_one(conn, query.replace(' FOR UPDATE', ''), params)
    monkeypatch.setattr(config_service, 'using_postgres', lambda: True)
    monkeypatch.setattr(config_service, 'one', adapted)
    result = config_service.save_active_config(config['id'], .6, False, False, 1)
    assert result['umbral_confianza'] == .6
    assert any(query.endswith(' FOR UPDATE') for query in queries)
