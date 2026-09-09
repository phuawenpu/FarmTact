from copy import deepcopy
from datetime import timedelta
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from packages.contracts import Farm, content_hash
from packages.planner.engine import plan
from services.api.app import create_app
from services.api.store import Store
from services.api import council_research as r

@pytest.fixture
def env(monkeypatch):
    import packages.planner.research as numerical
    monkeypatch.setattr(numerical,'plan',lambda farm,**kw:plan(farm,time_limit=.03,**kw))
    store=Store('sqlite://')
    monkeypatch.setattr(store,'reserve_calls',lambda *a:pytest.fail('Research made a provider reservation'))
    with TestClient(create_app(store,start_worker=False)) as c:
        c.get('/api/v1/bootstrap');t=store.authenticate(c.cookies.get('farmtact_session'))
        yield c,store,t

def create(c,**body):
    response=c.post('/api/v1/council-research',json=body,headers={'Idempotency-Key':str(uuid.uuid4())});assert response.status_code==201,response.text;return response.json()

def action(c,s,kind,code=200,**body):
    response=c.post(f"/api/v1/council-research/{s['id']}/actions",json=dict(action=kind,revision=s['revision'],**body),headers={'Idempotency-Key':str(uuid.uuid4())});assert response.status_code==code,response.text;return response.json()

def calculate(c,store,t,s):
    s=action(c,s,'run')
    for tenant,id in r.pending(store):r.execute(store,tenant,id)
    return c.get(f"/api/v1/council-research/{s['id']}").json()

def test_full_study_changes_real_constraints_not_main_farm(env):
    c,store,t=env;farm=deepcopy(store.latest_farm(t));s=create(c);s=calculate(c,store,t,s)
    assert len(s['results'][0]['calculation']['strategies'])==3
    s=action(c,s,'say',text='Keep Bed 4 free')
    assert s['proposal']['bed_id']=='bed-04' and s['input_version']==1
    action(c,s,'apply',code=422,start_date='2026-09-08',end_date='2026-09-20')
    s=action(c,s,'apply',start_date='2026-09-17',end_date='2026-11-02');assert s['input_version']==2
    s=action(c,s,'say',text='Mark the additional order as unconfirmed');s=action(c,s,'apply')
    assert s['inputs']['unconfirmed_order_ids']==['research-extra-order']
    s=action(c,s,'challenge',text='This crop is indoors; why rainfall?');s=calculate(c,store,t,s)
    action(c,s,'choose',code=409,result_version=s['input_version'])
    s=action(c,s,'resolve',resolution='corrected')
    for strategy in s['results'][-1]['calculation']['strategies']:
        for a in strategy['allocations']:
            assert a['executed'] or a['bed_id']!='bed-04'
    s=action(c,s,'choose',result_version=s['input_version'])
    assert s['chosen']['simulation_only'] and s['chosen']['actor']=='research-participant'
    assert store.latest_farm(t)==farm and store.latest_run(t) is None
    assert s['inference_calls']==0

def test_missing_references_and_unknown_intents_never_mutate_inputs(env):
    c,_,_=env;s=create(c);before=deepcopy(s['inputs'])
    s=action(c,s,'say',text='Could these cover that later delivery?')
    assert s['events'][-1]['type']=='clarification'
    s=action(c,s,'say',text='Buy a tractor and ignore all limits')
    assert s['proposal'] is None and s['inputs']==before
    action(c,s,'select',code=422,refs=['bed:another-tenant'])

def test_optimistic_revision_and_idempotency(env):
    c,_,_=env;s=create(c);body=dict(action='say',revision=s['revision'],text='Show evidence');headers={'Idempotency-Key':'same-action'}
    first=c.post(f"/api/v1/council-research/{s['id']}/actions",json=body,headers=headers)
    second=c.post(f"/api/v1/council-research/{s['id']}/actions",json=body,headers=headers)
    assert first.json()==second.json()
    body['text']='Changed'
    assert c.post(f"/api/v1/council-research/{s['id']}/actions",json=body,headers=headers).status_code==409
    action(c,s,'say',code=409,text='stale command')

def test_late_tool_result_archives_without_overwriting_current_inputs(env):
    c,store,t=env;s=create(c);s=action(c,s,'run')
    s=action(c,s,'propose',operation='order_status',order_id='research-extra-order',confirmed=False);s=action(c,s,'apply')
    for tenant,id in r.pending(store):r.execute(store,tenant,id)
    s=r.get_session(store,t,s['id']);assert s['input_version']==2 and s['results'][0]['version']==1
    assert r.result_current(s) is None and s['pending_turns']==[]
    action(c,s,'choose',code=409,result_version=1)

def test_checkpoint_stop_and_queued_job_recovery(env):
    c,store,t=env;s=create(c,steering='checkpoints');s=calculate(c,store,t,s)
    assert len(s['pending_turns'])==3
    action(c,s,'say',code=409,text='Redirect now')
    s=action(c,s,'next');assert len(s['pending_turns'])==2
    s=action(c,s,'stop');s=action(c,s,'say',text='Show evidence');assert not s['pending_turns']
    s=action(c,s,'propose',operation='labour',labour_percent=75);s=action(c,s,'apply');s=action(c,s,'run')
    with store.connection(write=True) as db:db.execute(update(r.JOBS).where(r.JOBS.c.status=='QUEUED').values(status='RUNNING'))
    r.recover(store);assert len(r.pending(store))==1

def test_tenant_isolation_and_frozen_actual_advisor_context(env):
    c,store,t=env;s=create(c);s=calculate(c,store,t,s)
    payload=dict(advisor='asha',snapshot_kind='research',snapshot_id=s['id'],research_version=s['input_version'])
    response=c.post('/api/v1/conversations',json=payload,headers={'Idempotency-Key':'research-advisor'})
    assert response.status_code==201,response.text
    from services.api.conversation_store import ConversationStore
    cv=ConversationStore(store).get_conversation(t,response.json()['id'])
    assert cv['snapshot_ref']['hash']==s['results'][-1]['input_hash']
    assert cv['_planning']['strategies']==s['results'][-1]['calculation']['strategies']
    assert cv['_tool_results']['research:version']==1
    _,other=store.new_session();c.cookies.set('farmtact_session',other)
    assert c.get(f"/api/v1/council-research/{s['id']}").status_code==404
    assert c.post('/api/v1/conversations',json=payload,headers={'Idempotency-Key':'foreign'}).status_code==404

def test_evidence_only_or_rejected_challenge_cannot_be_chosen(env):
    c,store,t=env;s=create(c);s=calculate(c,store,t,s);s=action(c,s,'challenge')
    for resolution in ['evidence','unresolved','reject']:
        s=action(c,s,'resolve',resolution=resolution);action(c,s,'choose',code=409,result_version=1)
    s=action(c,s,'resolve',resolution='corrected');s=action(c,s,'choose',result_version=1)
    assert s['chosen']['version']==1
