from copy import deepcopy
import threading

from fastapi.testclient import TestClient

from packages.contracts import content_hash
from packages.fixtures import synthetic_farm
from services.api.app import create_app, create_mission, MissionRequest, Worker
from services.api.store import Store
from services.api.views import capabilities


def test_import_retries_survive_future_version_changes():
    store = Store('sqlite://')
    with TestClient(create_app(store, start_worker=False)) as c:
        initial = c.get('/api/v1/bootstrap').json()['farm']['version']
        body = {'fixture': 'synthetic_demo'}
        first = c.post('/api/v1/imports', json=body, headers={'Idempotency-Key': 'import'})
        assert first.status_code == 201 and first.json()['version'] == initial + 1
        second = c.post('/api/v1/imports', json=body, headers={'Idempotency-Key': 'new-import'})
        assert second.json()['version'] == initial + 2
        retry = c.post('/api/v1/imports', json=body, headers={'Idempotency-Key': 'import'})
        assert retry.json() == first.json()
        assert c.get('/api/v1/bootstrap').json()['farm']['version'] == initial + 2
        changed = synthetic_farm().model_dump(mode='json'); changed['name'] = 'Changed'
        assert c.post('/api/v1/imports', json={'farm': changed}, headers={'Idempotency-Key': 'import'}).status_code == 409
        assert c.post('/api/v1/imports', json=body).status_code == 422


def test_archived_probe_never_claims_current_verification(monkeypatch):
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'test-only-placeholder')
    result = capabilities()
    assert result['deepseek']['status'] == 'configured'
    assert result['deepseek']['current_verification'] == 'not_probed'
    assert result['deepseek']['historical_probe']['current_capability'] is False
    assert result['deepseek']['inference_triggered'] is False
    assert result['vision']['status'] == 'unverified'
    monkeypatch.delenv('DEEPSEEK_API_KEY')
    assert capabilities()['deepseek']['status'] == 'blocked'


def test_blocked_provider_lane_does_not_block_numerical_work(monkeypatch):
    store = Store('sqlite://'); provider_t, _ = store.new_session(); numerical_t, _ = store.new_session()
    for tenant in (provider_t, numerical_t):store.save_farm(tenant, synthetic_farm().model_dump(mode='json'))
    slow = create_mission(store, provider_t, MissionRequest(council=True), 'slow')['id']
    fast = create_mission(store, numerical_t, MissionRequest(council=False), 'fast')['id']
    entered = threading.Event(); release = threading.Event(); completed = threading.Event()
    worker = Worker(store)
    def execute(tenant, id):
        if id == slow:
            entered.set(); release.wait(5)
        elif id == fast:completed.set()
    monkeypatch.setattr(worker, 'execute', execute)
    provider = threading.Thread(target=worker.tick, args=('provider',))
    provider.start()
    try:
        assert entered.wait(2)
        worker.tick('numerical')
        assert completed.is_set() and provider.is_alive()
    finally:
        release.set(); provider.join(timeout=3)


def test_terminal_cancel_is_a_truthful_noop():
    store = Store('sqlite://'); tenant, token = store.new_session()
    store.save_farm(tenant, synthetic_farm().model_dump(mode='json'))
    id = create_mission(store, tenant, MissionRequest(council=False), 'run')['id']
    run = store.get_run(tenant, id); run['status'] = 'FAILED'; store.save_run(tenant, run)
    with TestClient(create_app(store, start_worker=False)) as c:
        c.cookies.set('farmtact_session', token)
        response = c.post(f'/api/v1/planning-runs/{id}/cancel')
        assert response.status_code == 200
        assert response.json() == dict(status='FAILED', cancelled=False, reason='already_terminal')
        assert store.get_run(tenant, id) == run
