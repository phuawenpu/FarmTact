"""Real PostgreSQL admission and concurrent receipts for beginner attempts."""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from services.api.app import create_app
from services.api.planning_sessions import JOBS
from services.api.store import Store


def test_beginner_create_and_calculate_are_exactly_once_across_connections():
    store = Store()
    assert store.engine.dialect.name == 'postgresql'
    with TestClient(create_app(store, start_worker=False)) as client:
        client.get('/api/v1/bootstrap')
        token = client.cookies.get('farmtact_session')
    tenant = store.authenticate(token)
    key = uuid4().hex

    def request_create(_):
        own = Store()
        try:
            with TestClient(create_app(own, start_worker=False)) as client:
                client.cookies.set('farmtact_session', token)
                response = client.post('/api/v1/beginner-journeys', json={}, headers={'Idempotency-Key': key})
                return response.status_code, response.json()
        finally:
            own.engine.dispose()

    with ThreadPoolExecutor(max_workers=4) as pool:
        created = list(pool.map(request_create, range(4)))
    assert all(status == 201 for status, _ in created), created
    assert all(body == created[0][1] for _, body in created)
    journey = created[0][1]
    calculate_key = uuid4().hex

    def request_calculate(_):
        own = Store()
        try:
            with TestClient(create_app(own, start_worker=False)) as client:
                client.cookies.set('farmtact_session', token)
                response = client.post(f'/api/v1/beginner-journeys/{journey["id"]}/actions',
                    json={'revision': journey['revision'], 'action_id': 'calculate_choices'},
                    headers={'Idempotency-Key': calculate_key})
                return response.status_code, response.json()
        finally:
            own.engine.dispose()

    with ThreadPoolExecutor(max_workers=4) as pool:
        calculated = list(pool.map(request_calculate, range(4)))
    assert all(status in (200, 202) for status, _ in calculated), calculated
    assert all(body == calculated[0][1] for _, body in calculated)
    with store.connection() as connection:
        jobs = connection.execute(select(JOBS.c.id).where(JOBS.c.tenant_id == tenant, JOBS.c.session_id == journey['id'])).scalars().all()
    assert len(jobs) == 1

    # Reopening connections preserves the same queue and revision; stale actions
    # cannot bypass the teaching checkpoints through the older API.
    with TestClient(create_app(store, start_worker=False)) as client:
        client.cookies.set('farmtact_session', token)
        fresh = client.get(f'/api/v1/beginner-journeys/{journey["id"]}').json()
        assert fresh['stage'] == 'CALCULATING'
        response = client.post(f'/api/v1/planning-sessions/{journey["id"]}/advance',
            json={'revision': fresh['revision'], 'days': 7}, headers={'Idempotency-Key': uuid4().hex})
        assert response.status_code == 409
        assert 'beginner season' in response.json()['detail']
    store.engine.dispose()
