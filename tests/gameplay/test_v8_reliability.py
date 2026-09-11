from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from packages.contracts import content_hash
from packages.fixtures import synthetic_farm
from packages.planner.engine import allocations_existing
from services.api.app import create_app
from services.api.conversation_store import ConversationStore
from services.api.scenarios import cancel_scenario,computed_impacts,execute_scenario
from services.api.store import Store,now


def _minimal_plan(farm):
    allocations=allocations_existing(farm)
    strategies=[]
    for index,name in enumerate(('Lean','Balanced','Resilient')):
        strategies.append(dict(id=name.lower(),name=name,status='FEASIBLE',metrics={'fill_rate':1,'margin_sgd':100-index},violations=[],allocations=deepcopy(allocations),ledger=[],order_allocations=[]))
    return dict(input_hash=content_hash(farm),strategies=strategies,forecast={'demand':[],'harvest':[]},scenario_set=[])


@pytest.fixture
def env():
    store=Store('sqlite://');app=create_app(store,start_worker=False)
    with TestClient(app) as client:
        client.get('/api/v1/bootstrap')
        yield client,store,store.authenticate(client.cookies.get('farmtact_session'))


def _create(client,key='scenario',**body):
    return client.post('/api/v1/scenarios',json=body,headers={'Idempotency-Key':key})


def test_failed_scenario_retries_same_key_once_with_attempt_history(env,monkeypatch):
    client,store,tenant=env;calls=0
    def flaky(farm,**kwargs):
        nonlocal calls;calls+=1
        if calls==1:raise RuntimeError('transient fixture failure')
        return _minimal_plan(farm)
    monkeypatch.setattr('services.api.scenarios.plan',flaky)
    scenario=_create(client).json();key={'Idempotency-Key':'run'}
    assert client.post(f"/api/v1/scenarios/{scenario['id']}/run",headers=key).status_code==202
    execute_scenario(store,tenant,scenario['id'])
    failed=client.get(f"/api/v1/scenarios/{scenario['id']}").json()
    assert failed['status']=='FAILED' and failed['attempt_count']==1 and failed['attempts'][0]['status']=='FAILED'

    retry=client.post(f"/api/v1/scenarios/{scenario['id']}/retry",headers=key)
    assert retry.status_code==202 and retry.json()['attempt_count']==2
    duplicate=client.post(f"/api/v1/scenarios/{scenario['id']}/run",headers=key).json()
    assert duplicate['reused'] and duplicate['attempt_count']==2
    assert client.post(f"/api/v1/scenarios/{scenario['id']}/retry",headers={'Idempotency-Key':'stale'}).status_code==409
    execute_scenario(store,tenant,scenario['id'])
    completed=client.get(f"/api/v1/scenarios/{scenario['id']}").json()
    assert completed['status']=='COMPLETED' and [row['status'] for row in completed['attempts']]==['FAILED','COMPLETED']


def test_cancelled_scenario_retries_and_cancellation_wins_after_numerical_work(env,monkeypatch):
    client,store,tenant=env;scenario=_create(client,key='cancel-create').json();run_key={'Idempotency-Key':'cancel-run'}
    client.post(f"/api/v1/scenarios/{scenario['id']}/run",headers=run_key)
    cancelled=client.post(f"/api/v1/scenarios/{scenario['id']}/cancel").json()
    assert cancelled['status']=='CANCELLED' and not cancelled['reused']
    assert client.post(f"/api/v1/scenarios/{scenario['id']}/cancel").json()['reused']
    assert client.post(f"/api/v1/scenarios/{scenario['id']}/retry",headers=run_key).json()['status']=='QUEUED'

    def cancel_after_work(farm,**kwargs):
        result=_minimal_plan(farm)
        cancel_scenario(store,tenant,scenario['id'])
        return result
    monkeypatch.setattr('services.api.scenarios.plan',cancel_after_work)
    execute_scenario(store,tenant,scenario['id'])
    saved=client.get(f"/api/v1/scenarios/{scenario['id']}").json()
    assert saved['status']=='CANCELLED' and saved.get('accepted_strategy_id') is None
    assert [row['status'] for row in saved['attempts']]==['CANCELLED','CANCELLED']


def test_scenario_quota_and_cursor_listing_are_bounded(env):
    client,_,_=env
    created=[]
    for index in range(30):
        response=_create(client,key=f'quota-{index}',name=f'Scenario {index}')
        assert response.status_code==201
        created.append(response.json())
    assert _create(client,key='over-quota').status_code==429
    assert _create(client,key='quota-0',name='Scenario 0').json()['reused']
    page=client.get('/api/v1/scenarios',params={'limit':2}).json()['scenarios']
    assert len(page)==2 and page[0]['created_at']>=page[1]['created_at']
    older=client.get('/api/v1/scenarios',params={'limit':2,'before':page[-1]['created_at']}).json()['scenarios']
    assert len(older)<=2 and all(row['created_at']<page[-1]['created_at'] for row in older)
    assert client.get('/api/v1/scenarios',params={'limit':31}).status_code==422


def test_exact_computed_impacts_use_order_attribution_across_policies():
    def strategy(name,delivered):
        return dict(name=name,allocations=[],ledger=[],order_allocations=[dict(demand_line_id='order:o1',order_id='o1',crop_id='caixin',date='2026-09-10',requested_kg=5,delivered_kg=delivered,shortfall_kg=5-delivered,price_sgd_per_kg=8,price_status='order_contract_price')])
    result=computed_impacts(dict(
        baseline={'strategies':[strategy('Balanced',2)]},result={'strategies':[strategy('Balanced',5)]},
        baseline_snapshot={'orders':[]},input_snapshot={'orders':[]},
    ))
    assert result['affected_deliveries']==[dict(order_id='o1',crop_id='caixin',due_date='2026-09-10',demand_line_id='order:o1',policy_impacts=[dict(policy='Balanced',baseline_requested_kg=5,baseline_delivered_kg=2,baseline_lot_allocations=[],scenario_requested_kg=5,scenario_delivered_kg=5,scenario_shortfall_kg=0,scenario_lot_allocations=[],price_status='order_contract_price')])]
    assert result['affected_basis'].startswith('Exact per-order')


def test_conversation_store_quota_bounded_list_and_atomic_cancel(env):
    _,store,tenant=env;persistence=ConversationStore(store)
    for index in range(30):
        payload=dict(id=f'conversation-{index}',status='OPEN',created_at=now(),updated_at=now())
        assert persistence.create_conversation(tenant,f'key-{index}',f'hash-{index}',payload)[1]
    with pytest.raises(ValueError,match='Thirty conversations'):
        persistence.create_conversation(tenant,'key-over','hash-over',dict(id='over',status='OPEN',created_at=now(),updated_at=now()))
    assert len(persistence.list_conversations(tenant,limit=3))==3
    conversation=persistence.get_conversation(tenant,'conversation-0')
    request,_,_=persistence.create_request(tenant,conversation['id'],'message-key','message-hash',dict(id='request-0',conversation_id=conversation['id'],status='QUEUED',roles=['demand_analyst'],created_at=now()),dict(id='message-0',speaker='user',content='question',created_at=now()))
    cancelled,changed=persistence.cancel_request(tenant,conversation['id'],request['id'])
    assert changed and cancelled['status']=='CANCELLED' and persistence.is_cancelled(tenant,request['id'])
    repeated,changed=persistence.cancel_request(tenant,conversation['id'],request['id'])
    assert not changed and repeated==cancelled
