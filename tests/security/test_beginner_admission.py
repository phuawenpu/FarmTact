"""Journey routes inherit admission before lookup, parsing, or planning work."""
from uuid import uuid4

from fastapi.testclient import TestClient

from services.api.app import create_app
from services.api.security import WRITE_TENANT
from services.api.store import Store


def test_new_journey_mutations_cannot_bypass_durable_session_limit():
    store = Store('sqlite://')
    app = create_app(store, start_worker=False)
    with TestClient(app) as client:
        client.get('/api/v1/bootstrap')
        tenant = store.authenticate(client.cookies.get('farmtact_session'))
        for _ in range(WRITE_TENANT.limit):
            app.state.abuse_limits.consume([(WRITE_TENANT, tenant)])
        response = client.post('/api/v1/beginner-journeys/not-owned/actions',
                               content=b'not even valid json',
                               headers={'Idempotency-Key': uuid4().hex})
        assert response.status_code == 429
        assert response.json()['limit'] == 'write_session'
        assert int(response.headers['Retry-After']) > 0
        assert client.get('/api/v1/beginner-journeys').json()['journeys'] == []


def test_new_journey_creation_requires_session_and_same_origin():
    store = Store('sqlite://')
    with TestClient(create_app(store, start_worker=False)) as client:
        response = client.post('/api/v1/beginner-journeys', json={},
                               headers={'Idempotency-Key': uuid4().hex})
        assert response.status_code == 401
        client.get('/api/v1/bootstrap')
        response = client.post('/api/v1/beginner-journeys', json={},
                               headers={'Idempotency-Key': uuid4().hex,
                                        'Origin': 'https://unrelated.invalid'})
        assert response.status_code == 403


def test_new_journey_routes_fail_closed_when_admission_is_unavailable(monkeypatch):
    store = Store('sqlite://')
    app = create_app(store, start_worker=False)
    with TestClient(app) as client:
        client.get('/api/v1/bootstrap')

        def unavailable(*_args, **_kwargs):
            raise ConnectionError('test admission outage')

        monkeypatch.setattr(app.state.abuse_limits, 'consume', unavailable)
        response = client.post('/api/v1/beginner-journeys', json={},
                               headers={'Idempotency-Key': uuid4().hex})
        assert response.status_code == 503
        assert response.json()['detail'] == 'Request admission temporarily unavailable'
