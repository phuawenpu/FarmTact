from copy import deepcopy
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from packages.contracts import content_hash
from packages.planning_contracts import PlanningAssumptions
from services.api.app import create_app
from services.api.store import Store
from services.api.planning_sessions import execute_job,get_session,get_result,JOBS
from sqlalchemy import select

@pytest.fixture
def env():
    store=Store('sqlite://')
    with TestClient(create_app(store,start_worker=False)) as client:
        client.get('/api/v1/bootstrap')
        yield client,store,store.authenticate(client.cookies.get('farmtact_session'))

def post(client,path,body,key=None):
    return client.post('/api/v1/planning-sessions'+path,json=body,headers={'Idempotency-Key':key or uuid4().hex})

def create(client):
    result=post(client,'',{})
    assert result.status_code==201,result.text
    return result.json()

def calculate(client,store,tenant,s):
    r=post(client,f"/{s['id']}/calculate",{'revision':s['revision']})
    assert r.status_code==202,r.text
    execute_job(store,tenant,r.json()['job']['id'])
    result=client.get('/api/v1/planning-sessions/'+s['id']).json()
    assert result['status']=='COMPLETED',result.get('job')
    return result


def test_contract_rejects_overlaps_and_ambiguous_order_edits():
    with pytest.raises(ValueError):PlanningAssumptions.model_validate({'future_demand':[{'crop_id':'caixin','start_date':'2026-09-11','end_date':'2026-09-20','percent':110}]*2})
    with pytest.raises(ValueError):PlanningAssumptions.model_validate({'order_changes':[{'operation':'cancel','order_id':'one','quantity_kg':12}]})
    with pytest.raises(ValueError):PlanningAssumptions.model_validate({'seasonal':[{'crop_id':'caixin','start_date':'2026-09-11','end_date':'2026-09-20','yield_percent':80,'reason':'test','system':'outdoor'}]})


def test_creation_idempotency_revision_and_tenant_isolation(env):
    client,store,tenant=env
    r=post(client,'',{},'create-one');s=r.json()
    assert post(client,'',{},'create-one').json()==s
    assert post(client,'',{'name':'different'},'create-one').status_code==409
    assert post(client,f"/{s['id']}/calculate",{'revision':999}).status_code==409
    other,_=store.new_session()
    assert get_session(store,other,s['id']) is None
    assert client.get('/api/v1/planning-sessions/not-owned').status_code==404
    assert len(client.get('/api/v1/planning-sessions').json()['sessions'])==1


def test_numerical_mission_advance_disrupt_preserves_main_farm_and_history(env):
    client,store,tenant=env
    original=content_hash(store.latest_farm(tenant))
    s=calculate(client,store,tenant,create(client))
    assert s['selected_strategy_id'] and s['review']['status']=='not_requested'
    assert all('ledger' not in row for row in s['result']['strategies'])
    r=post(client,f"/{s['id']}/advance",{'revision':s['revision'],'days':7},'advance-once')
    assert r.status_code==200,r.text
    s=r.json();world=s['simulation'];assert world['days_executed']==7
    assert post(client,f"/{s['id']}/advance",{'revision':s['revision']-1,'days':7},'advance-once').json()==s
    history=deepcopy(s['farm']['history']);orders=deepcopy(s['farm']['orders'])
    from datetime import date,timedelta
    start=str(date.fromisoformat(world['clock_date'])+timedelta(days=1))
    assumptions={'future_demand':[{'crop_id':'caixin','start_date':start,'end_date':world['end_date'],'percent':125}]}
    r=post(client,f"/{s['id']}/disrupt",{'revision':s['revision'],'assumptions':assumptions})
    assert r.status_code==202,r.text
    execute_job(store,tenant,r.json()['job']['id'])
    s=client.get('/api/v1/planning-sessions/'+s['id']).json()
    assert s['status']=='COMPLETED',s['job']
    assert s['farm']['history']==history
    assert s['farm']['orders']==[o for o in orders if o['due_date']>=start]
    assert len(s['result']['comparisons'])==3
    assert s['result']['retained_strategy']['evaluated_without_optimization']
    assert s['simulation']['days_executed']==7
    assert s['simulation']['event_sequence']>world['event_sequence']
    assert content_hash(store.latest_farm(tenant))==original
    r=post(client,f"/{s['id']}/advance",{'revision':s['revision'],'days':7})
    assert r.status_code==200,r.text
    assert r.json()['simulation']['days_executed']==14


def test_queued_cancellation_never_executes_and_recovery_does_not_replay(env):
    client,store,tenant=env;s=create(client)
    r=post(client,f"/{s['id']}/calculate",{'revision':s['revision']});s=r.json()
    r=post(client,f"/{s['id']}/cancel",{'revision':s['revision']});assert r.status_code==200
    execute_job(store,tenant,s['job']['id'])
    assert get_session(store,tenant,s['id'])['status']=='CANCELLED'
    assert get_result(store,tenant,s['job']['id']) is None


def test_missing_provider_is_visible_and_does_not_block_numerical_use(env,monkeypatch):
    client,store,tenant=env;s=calculate(client,store,tenant,create(client))
    monkeypatch.delenv('DEEPSEEK_API_KEY',raising=False)
    r=post(client,f"/{s['id']}/review",{'revision':s['revision']})
    assert r.status_code==202
    execute_job(store,tenant,r.json()['job']['id'])
    s=client.get('/api/v1/planning-sessions/'+s['id']).json()
    assert s['review']['status']=='blocked' and s['review']['request_count']==0
    frozen=deepcopy(s['review_history'])
    assert frozen[-1]['review']==s['review']
    assert frozen[-1]['result_id']==s['result_id']
    with store.connection() as c:
        saved=c.execute(select(JOBS.c.payload).where(JOBS.c.id==r.json()['job']['id'])).scalar_one()
    assert saved['review_result']==s['review']
    advanced=post(client,f"/{s['id']}/advance",{'revision':s['revision'],'days':1})
    assert advanced.status_code==200,advanced.text
    from services.api.planning_sessions import queue_recalculation
    recalculation=queue_recalculation(store,tenant,get_session(store,tenant,s['id']),[{'kind':'planning_assumptions','assumptions':{}}])
    execute_job(store,tenant,recalculation['id'])
    s=client.get('/api/v1/planning-sessions/'+s['id']).json()
    assert s['review']['status']=='not_requested'
    assert s['review_history']==frozen
    assert s['selected_strategy_id']


def test_guided_world_cannot_be_mutated_through_legacy_routes(env):
    client,store,tenant=env;s=calculate(client,store,tenant,create(client))
    s=post(client,f"/{s['id']}/advance",{'revision':s['revision'],'days':1}).json()
    world=s['simulation']
    for operation,body in [('advance',{'revision':world['revision'],'days':1}),('replan',{'revision':world['revision']})]:
        response=client.post(f"/api/v1/simulations/{world['id']}/{operation}",json=body,headers={'Idempotency-Key':'legacy-'+operation})
        assert response.status_code==409
    assert client.get('/api/v1/planning-sessions/'+s['id']).json()['simulation']['revision']==world['revision']
