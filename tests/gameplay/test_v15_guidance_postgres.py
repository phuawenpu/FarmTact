"""Guidance shares a planning identity but cannot race or alter the farm revision."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from uuid import uuid4
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select
from packages.fixtures import synthetic_farm
from services.api.app import create_app
from services.api.planning_sessions import SESSIONS, RECEIPTS, get_session
from services.api.store import Store, farms, tenants


def test_guidance_concurrent_retry_and_restart_preserve_planning_revision():
    store = Store()
    assert store.engine.dialect.name == 'postgresql'
    tenant, token = store.new_session()
    store.save_farm(tenant, synthetic_farm().model_dump(mode='json'))
    try:
        with TestClient(create_app(store, start_worker=False)) as client:
            client.cookies.set('farmtact_session', token)
            response = client.post('/api/v1/planning-sessions', json={'workflow': True},
                                   headers={'Idempotency-Key': uuid4().hex})
            assert response.status_code == 201
            session = response.json()
            baseline = deepcopy(get_session(store, tenant, session['id']))
            path = f"/api/v1/planning-sessions/{session['id']}/guidance"
            body = {'revision': 0, 'step':'compare', 'skipped':True}
            def retry(_):
                return client.post(path, json=body, headers={'Idempotency-Key':'same-guidance'} )
            with ThreadPoolExecutor(max_workers=4) as pool:
                results = list(pool.map(retry, range(4)))
            assert all(result.status_code == 200 for result in results)
            assert all(result.json() == results[0].json() for result in results)
            assert results[0].json()['guidance']['revision'] == 1
            assert results[0].json()['revision'] == session['revision']
            with store.connection() as connection:
                assert connection.execute(select(func.count()).select_from(RECEIPTS).where(
                    RECEIPTS.c.tenant_id == tenant, RECEIPTS.c.key == 'same-guidance')).scalar_one() == 1
            def conflict(_):
                return client.post(path, json={**body, 'revision':1,'skipped':False},
                                   headers={'Idempotency-Key':uuid4().hex}).status_code
            with ThreadPoolExecutor(max_workers=4) as pool:
                statuses = list(pool.map(conflict, range(4)))
            assert statuses.count(200) == 1 and statuses.count(409) == 3
        restarted = Store()
        try:
            restored = get_session(restarted, tenant, session['id'])
            assert restored['guidance']['revision'] == 2
            assert restored['guidance']['skipped'] is False
            assert restored['revision'] == session['revision']
            assert restored['farm'] == baseline['farm']
            assert restored['input_hash'] == baseline['input_hash']
            assert restored['history'] == baseline['history']
        finally:
            restarted.engine.dispose()
    finally:
        with store.connection(write=True) as connection:
            connection.execute(delete(RECEIPTS).where(RECEIPTS.c.tenant_id == tenant))
            connection.execute(delete(SESSIONS).where(SESSIONS.c.tenant_id == tenant))
            connection.execute(delete(farms).where(farms.c.tenant_id == tenant))
            connection.execute(delete(tenants).where(tenants.c.id == tenant))
        store.engine.dispose()


def test_farm_transition_concurrent_receipt_and_conflicting_reviews():
    store = Store()
    assert store.engine.dialect.name == 'postgresql'
    tenant, token = store.new_session()
    initial = store.save_farm(tenant, synthetic_farm().model_dump(mode='json'))
    try:
        with TestClient(create_app(store, start_worker=False)) as client:
            client.cookies.set('farmtact_session', token)
            body = {'expected_farm_version': initial['version'], 'fixture':'synthetic_demo'}
            def send(key, version):
                return client.post('/api/v1/planning-sessions/import',
                    json={**body, 'expected_farm_version':version},
                    headers={'Idempotency-Key':key})
            with ThreadPoolExecutor(max_workers=4) as pool:
                responses = list(pool.map(lambda _:send('same-transition',initial['version']),range(4)))
            assert all(r.status_code == 201 for r in responses)
            assert all(r.json() == responses[0].json() for r in responses)
            current = store.latest_farm(tenant)
            assert current['version'] == initial['version'] + 1
            with ThreadPoolExecutor(max_workers=4) as pool:
                responses = list(pool.map(lambda _:send(uuid4().hex,current['version']),range(4)))
            assert [r.status_code for r in responses].count(201) == 1
            assert [r.status_code for r in responses].count(409) == 3
            with store.connection() as c:
                assert c.execute(select(func.count()).select_from(SESSIONS).where(SESSIONS.c.tenant_id==tenant)).scalar_one() == 2
            restarted = Store()
            try:
                assert restarted.latest_farm(tenant)['version'] == initial['version'] + 2
            finally:
                restarted.engine.dispose()
    finally:
        with store.connection(write=True) as c:
            c.execute(delete(RECEIPTS).where(RECEIPTS.c.tenant_id==tenant))
            c.execute(delete(SESSIONS).where(SESSIONS.c.tenant_id==tenant))
            c.execute(delete(farms).where(farms.c.tenant_id==tenant))
            c.execute(delete(tenants).where(tenants.c.id==tenant))
        store.engine.dispose()
