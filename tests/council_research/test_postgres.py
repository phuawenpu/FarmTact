"""Real PostgreSQL concurrency, restart, and isolation review for council research."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import secrets
import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete,func,select,update
from sqlalchemy.exc import IntegrityError

from packages.fixtures import synthetic_farm
from packages.planner.engine import plan
from services.api.app import create_app
from services.api.conversation_store import (
    ConversationStore,conversation_events,conversation_messages,
    conversation_requests,conversations,
)
from services.api.council_research import ACTIONS,JOBS,SESSIONS
from services.api import council_research as research
from services.api.store import Store,farms,tenants


@pytest.fixture
def postgres_research(monkeypatch):
    import packages.planner.research as numerical
    monkeypatch.setattr(numerical,'plan',lambda farm,**kwargs:plan(farm,time_limit=0,**kwargs))
    store=Store('postgresql+psycopg://sprite@/farmtact_research_test?host=/tmp/farmtact-pg')
    assert store.engine.dialect.name=='postgresql'
    owned=[]
    def new_tenant():
        tenant,token=store.new_session();owned.append(tenant)
        farm=store.save_farm(tenant,synthetic_farm().model_dump(mode='json'))
        return tenant,token,farm
    yield store,new_tenant
    if owned:
        with store.engine.begin() as c:
            c.execute(delete(conversation_events).where(conversation_events.c.tenant_id.in_(owned)))
            c.execute(delete(conversation_messages).where(conversation_messages.c.tenant_id.in_(owned)))
            c.execute(delete(conversation_requests).where(conversation_requests.c.tenant_id.in_(owned)))
            c.execute(delete(conversations).where(conversations.c.tenant_id.in_(owned)))
            c.execute(delete(ACTIONS).where(ACTIONS.c.tenant_id.in_(owned)))
            c.execute(delete(JOBS).where(JOBS.c.tenant_id.in_(owned)))
            c.execute(delete(SESSIONS).where(SESSIONS.c.tenant_id.in_(owned)))
            c.execute(delete(farms).where(farms.c.tenant_id.in_(owned)))
            c.execute(delete(tenants).where(tenants.c.id.in_(owned)))
    store.engine.dispose()


def _create(client,key=None):
    response=client.post('/api/v1/council-research',json={},headers={'Idempotency-Key':key or secrets.token_hex(12)})
    assert response.status_code==201,response.text
    return response.json()


def _action(client,session,action,key=None,**body):
    return client.post(
        f"/api/v1/council-research/{session['id']}/actions",
        json=dict(action=action,revision=session['revision'],**body),
        headers={'Idempotency-Key':key or secrets.token_hex(12)},
    )


def test_postgres_serializes_concurrent_apply_and_replays_idempotently(postgres_research):
    store,new_tenant=postgres_research;tenant,token,_=new_tenant()
    with TestClient(create_app(store,start_worker=False)) as client:
        client.cookies.set('farmtact_session',token)
        session=_create(client)
        proposed=_action(client,session,'propose',operation='order_status',order_id='research-extra-order',confirmed=False).json()
        barrier=threading.Barrier(2)
        def apply(index):
            barrier.wait(timeout=10)
            return _action(client,proposed,'apply',key=f'concurrent-apply-{index}')
        with ThreadPoolExecutor(max_workers=2) as pool:
            responses=list(pool.map(apply,range(2)))
        assert sorted(response.status_code for response in responses)==[200,409]
        saved=research.get_session(store,tenant,session['id'])
        assert saved['input_version']==2
        assert saved['inputs']['unconfirmed_order_ids']==['research-extra-order']

        body=dict(action='say',revision=saved['revision'],text='Show evidence')
        barrier=threading.Barrier(2)
        def repeat(_):
            barrier.wait(timeout=10)
            return client.post(f"/api/v1/council-research/{session['id']}/actions",json=body,headers={'Idempotency-Key':'same-concurrent-action'})
        with ThreadPoolExecutor(max_workers=2) as pool:
            repeated=list(pool.map(repeat,range(2)))
        assert [response.status_code for response in repeated]==[200,200]
        assert repeated[0].json()==repeated[1].json()
        with store.connection() as c:
            count=c.execute(select(func.count()).select_from(ACTIONS).where(ACTIONS.c.tenant_id==tenant,ACTIONS.c.idempotency_key=='same-concurrent-action')).scalar_one()
        assert count==1


def test_restart_retains_frozen_job_and_late_result_is_archived(postgres_research):
    store,new_tenant=postgres_research;tenant,token,main_farm=new_tenant()
    with TestClient(create_app(store,start_worker=False)) as client:
        client.cookies.set('farmtact_session',token)
        session=_create(client)
        queued=_action(client,session,'run').json()
        with store.connection(write=True) as c:
            job=c.execute(select(JOBS).where(JOBS.c.tenant_id==tenant)).mappings().one()
            frozen=deepcopy(job['payload'])
            c.execute(update(JOBS).where(JOBS.c.id==job['id']).values(status='RUNNING'))

        restarted=Store('postgresql+psycopg://sprite@/farmtact_research_test?host=/tmp/farmtact-pg')
        try:
            research.recover(restarted)
            with restarted.engine.connect() as c:
                recovered=c.execute(select(JOBS).where(JOBS.c.id==job['id'])).mappings().one()
            assert recovered['status']=='QUEUED' and recovered['payload']==frozen

            proposed=_action(client,queued,'propose',operation='order_status',order_id='research-extra-order',confirmed=False).json()
            changed=_action(client,proposed,'apply').json()
            assert changed['input_version']==2
            research.execute(restarted,tenant,job['id'])
            saved=research.get_session(restarted,tenant,session['id'])
            assert saved['input_version']==2 and saved['inputs']['unconfirmed_order_ids']==['research-extra-order']
            assert saved['results'][0]['version']==1 and saved['results'][0]['status']=='COMPLETED'
            assert research.result_current(saved) is None and saved['chosen'] is None
            assert restarted.latest_farm(tenant)==main_farm and restarted.latest_run(tenant) is None
        finally:restarted.engine.dispose()


def test_fk_tenant_isolation_and_advisor_freezes_current_result_without_provider(postgres_research,monkeypatch):
    store,new_tenant=postgres_research;tenant_a,token_a,main_farm=new_tenant();tenant_b,token_b,_=new_tenant()
    monkeypatch.setattr(store,'reserve_calls',lambda *args,**kwargs:pytest.fail('research persistence invoked provider budget'))
    with TestClient(create_app(store,start_worker=False)) as client:
        client.cookies.set('farmtact_session',token_a)
        session=_create(client);queued=_action(client,session,'run').json()
        job=next((row for row in research.pending(store) if row.tenant_id==tenant_a),None)
        assert job is not None
        research.execute(store,job.tenant_id,job.id)
        completed=research.get_session(store,tenant_a,session['id'])
        chosen=_action(client,completed,'choose',result_version=1,policy='Balanced')
        assert chosen.status_code==200,chosen.text
        selected=chosen.json()
        response=client.post('/api/v1/conversations',json=dict(advisor='asha',snapshot_kind='research',snapshot_id=session['id'],research_version=1),headers={'Idempotency-Key':'frozen-research-advisor'})
        assert response.status_code==201,response.text
        conversation=ConversationStore(store).get_conversation(tenant_a,response.json()['id'])
        result=research.result_current(selected)
        assert conversation['snapshot_ref']['hash']==result['input_hash']==selected['chosen']['input_hash']
        assert conversation['_planning']==result['calculation']
        assert conversation['_tool_results']['research:inputs']==result['inputs']
        assert conversation['_tool_results']['research:version']==1
        assert float(conversation['_snapshot']['resources']['labour_hours_per_week'])==float(session['farm']['resources']['labour_hours_per_week'])
        assert conversation['_snapshot']['resources']['cash_sgd']==session['farm']['resources']['cash_sgd']
        assert store.latest_farm(tenant_a)==main_farm and store.latest_run(tenant_a) is None

        client.cookies.set('farmtact_session',token_b)
        assert client.get(f"/api/v1/council-research/{session['id']}").status_code==404
        assert client.post('/api/v1/conversations',json=dict(advisor='asha',snapshot_kind='research',snapshot_id=session['id'],research_version=1),headers={'Idempotency-Key':'foreign-advisor'}).status_code==404

    alien_job=dict(id=secrets.token_hex(16),session_id=session['id'],version=99,farm=session['farm'],inputs=session['inputs'],input_hash='alien')
    with pytest.raises(IntegrityError):
        with store.engine.begin() as c:
            c.execute(JOBS.insert().values(id=alien_job['id'],tenant_id=tenant_b,session_id=session['id'],version=99,status='QUEUED',payload=alien_job))
    with store.connection() as c:
        assert c.execute(select(JOBS.c.id).where(JOBS.c.id==alien_job['id'])).scalar_one_or_none() is None
