"""Reviewed farm transitions commit farm and owning workflow together."""
from copy import deepcopy
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from services.api.app import create_app
from services.api.planning_sessions import SESSIONS
from services.api.store import Store


def test_transition_replay_stale_review_and_session_limit_preserve_farm():
    store = Store('sqlite://')
    with TestClient(create_app(store, start_worker=False)) as client:
        client.get('/api/v1/bootstrap')
        tenant = store.authenticate(client.cookies.get('farmtact_session'))
        original = deepcopy(store.latest_farm(tenant))
        old = client.post('/api/v1/planning-sessions', json={'workflow': True},
                          headers={'Idempotency-Key': uuid4().hex}).json()
        body = {'expected_farm_version': original['version'], 'fixture': 'synthetic_demo'}
        headers = {'Idempotency-Key': 'reviewed-transition'}
        response = client.post('/api/v1/planning-sessions/import', json=body, headers=headers)
        assert response.status_code == 201, response.text
        new = response.json()
        assert new['workflow'] and new['farm']['version'] == original['version'] + 1
        assert new['id'] != old['id']
        assert client.get('/api/v1/planning-sessions/'+old['id']).json() == old
        assert client.post('/api/v1/planning-sessions/import', json=body, headers=headers).json() == new
        saved = deepcopy(store.latest_farm(tenant))
        assert client.post('/api/v1/planning-sessions/import', json=body,
                           headers={'Idempotency-Key': uuid4().hex}).status_code == 409
        assert store.latest_farm(tenant) == saved
        with store.connection(write=True) as c:
            for i in range(6):
                c.execute(SESSIONS.insert().values(id=f'limit-{i}', tenant_id=tenant,
                          status='DRAFT', payload={}))
        limited = client.post('/api/v1/planning-sessions/import',
            json={**body, 'expected_farm_version': saved['version']},
            headers={'Idempotency-Key': uuid4().hex})
        assert limited.status_code == 429
        assert store.latest_farm(tenant) == saved
        with store.connection() as c:
            assert c.execute(select(func.count()).select_from(SESSIONS)).scalar_one() == 8


def test_transition_rolls_back_if_session_cannot_be_saved(monkeypatch):
    store = Store('sqlite://')
    with TestClient(create_app(store, start_worker=False), raise_server_exceptions=False) as client:
        client.get('/api/v1/bootstrap')
        tenant = store.authenticate(client.cookies.get('farmtact_session'))
        original = deepcopy(store.latest_farm(tenant))
        save = store.save_farm
        def interrupted(tenant, payload):
            save(tenant, payload)
            raise RuntimeError('Simulated interruption before creating workflow')
        monkeypatch.setattr(store, 'save_farm', interrupted)
        body = {'expected_farm_version': original['version'], 'farm': original}
        headers = {'Idempotency-Key': 'retry-interrupted-transition'}
        assert client.post('/api/v1/planning-sessions/import', json=body, headers=headers).status_code == 500
        assert store.latest_farm(tenant) == original
        monkeypatch.setattr(store, 'save_farm', save)
        assert client.post('/api/v1/planning-sessions/import', json=body, headers=headers).status_code == 201
        assert store.latest_farm(tenant)['version'] == original['version'] + 1
