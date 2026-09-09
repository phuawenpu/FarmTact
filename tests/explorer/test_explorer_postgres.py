"""Additive snapshot persistence on real PostgreSQL, including numerical restart."""
from concurrent.futures import ThreadPoolExecutor
from fastapi.testclient import TestClient
from sqlalchemy import delete,select
from services.api.app import create_app
from services.api.store import Store,farms,tenants
from services.api.data_explorer import snapshots,get_saved
from services.api.scenarios import branches,save_scenario,get_scenario,interrupt_scenarios,execute_scenario
from packages.fixtures import synthetic_farm
from packages.planner import plan


def test_snapshot_concurrency_reload_and_interrupted_worker(monkeypatch):
    import services.api.scenarios as module
    monkeypatch.setattr(module,'plan',lambda farm,**kwargs:plan(farm,time_limit=0,**kwargs))
    store=Store();assert store.engine.dialect.name=='postgresql'
    tenant,token=store.new_session();original=store.save_farm(tenant,synthetic_farm().model_dump(mode='json'))
    try:
        with TestClient(create_app(store,start_worker=False)) as client:
            client.cookies.set('farmtact_session',token)
            def create(_):
                r=client.post('/api/v1/data-explorer/snapshots',json={'forecast_settings':{'alpha':.7}},headers={'Idempotency-Key':'concurrent'})
                assert r.status_code==201,r.text
                return r.json()
            with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(create,range(4)))
            assert len({r['id'] for r in results})==1
            id=results[0]['id']
            r=client.post('/api/v1/scenarios',json={'explorer_snapshot_id':id},headers={'Idempotency-Key':'scenario'})
            assert r.status_code==201,r.text
            branch=r.json();branch['status']='RUNNING';branch['run_key']='run'
            save_scenario(store,tenant,branch)
        restarted=Store()
        try:
            frozen=get_saved(restarted,tenant,id)
            assert frozen['forecast_settings']=={'alpha':.7}
            interrupt_scenarios(restarted)
            assert get_scenario(restarted,tenant,branch['id'])['status']=='QUEUED'
            execute_scenario(restarted,tenant,branch['id'])
            result=get_scenario(restarted,tenant,branch['id'])
            assert result['status']=='COMPLETED'
            assert result['result']['forecast']['forecast_settings']=={'alpha':.7}
            assert restarted.latest_farm(tenant)==original
            assert restarted.latest_run(tenant) is None
            assert get_saved(restarted,tenant,id)==frozen
        finally:restarted.engine.dispose()
    finally:
        with store.connection(write=True) as c:
            c.execute(delete(branches).where(branches.c.tenant_id==tenant))
            c.execute(delete(snapshots).where(snapshots.c.tenant_id==tenant))
            c.execute(delete(farms).where(farms.c.tenant_id==tenant))
            c.execute(delete(tenants).where(tenants.c.id==tenant))
        store.engine.dispose()
