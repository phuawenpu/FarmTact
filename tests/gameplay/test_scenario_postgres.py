"""Real PostgreSQL serialization and restart persistence for additive gameplay tables."""
from concurrent.futures import ThreadPoolExecutor
import secrets
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from services.api.app import create_app
from services.api.store import Store, farms, tenants
from services.api.scenarios import branches, quest_progress, get_scenario
from packages.fixtures import synthetic_farm


def test_concurrent_create_and_run_keep_single_durable_branch():
    store=Store();assert store.engine.dialect.name=='postgresql'
    tenant,token=store.new_session();store.save_farm(tenant,synthetic_farm().model_dump(mode='json'))
    try:
        app=create_app(store,start_worker=False)
        with TestClient(app) as c:
            c.cookies.set('farmtact_session',token)
            def create(_):
                return c.post('/api/v1/scenarios',json={'controls':{'cash_percent':75}},headers={'Idempotency-Key':'concurrent'}).json()
            with ThreadPoolExecutor(max_workers=6) as pool:rows=list(pool.map(create,range(6)))
            assert len({r['id'] for r in rows})==1
            id=rows[0]['id']
            def run(_):return c.post(f'/api/v1/scenarios/{id}/run',headers={'Idempotency-Key':'run'}).json()
            with ThreadPoolExecutor(max_workers=6) as pool:runs=list(pool.map(run,range(6)))
            assert all(r['status']=='QUEUED' for r in runs)
            assert sum(not r.get('reused',False) for r in runs)==1
        restarted=Store()
        try:
            saved=get_scenario(restarted,tenant,id)
            assert saved['status']=='QUEUED' and saved['controls']['cash_percent']==75
            assert restarted.latest_farm(tenant)['resources']['cash_sgd']==synthetic_farm().model_dump(mode='json')['resources']['cash_sgd']
        finally:restarted.engine.dispose()
    finally:
        with store.engine.begin() as c:
            c.execute(delete(quest_progress).where(quest_progress.c.tenant_id==tenant))
            c.execute(delete(branches).where(branches.c.tenant_id==tenant))
            c.execute(delete(farms).where(farms.c.tenant_id==tenant))
            c.execute(delete(tenants).where(tenants.c.id==tenant))
        store.engine.dispose()
