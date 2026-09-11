from copy import deepcopy
from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from packages.contracts import Farm,content_hash
from packages.fixtures import synthetic_farm
from packages.planner import plan
from services.api.app import create_app
from services.api.store import Store
from services.api.scenarios import Controls, apply_controls, execute_scenario, interrupt_scenarios, save_scenario, get_scenario

@pytest.fixture
def env(monkeypatch):
    import services.api.scenarios as module
    monkeypatch.setattr(module,'plan',lambda farm:plan(farm,time_limit=.03))
    store=Store('sqlite://')
    with TestClient(create_app(store,start_worker=False)) as c:
        c.get('/api/v1/bootstrap')
        yield c,store,store.authenticate(c.cookies.get('farmtact_session'))

def create(c,key='branch',**body):
    return c.post('/api/v1/scenarios',json=body,headers={'Idempotency-Key':key})

def run(c,s,t,id,key='run'):
    response=c.post(f'/api/v1/scenarios/{id}/run',headers={'Idempotency-Key':key})
    assert response.status_code==202,response.text
    execute_scenario(s,t,id)
    return c.get(f'/api/v1/scenarios/{id}').json()

def test_all_controls_are_frozen_and_local():
    base=synthetic_farm().model_dump(mode='json');before=deepcopy(base)
    batch=base['batches'][0];crop=base['recipes'][0]['crop_id']
    changed=apply_controls(base,Controls(batch_id=batch['id'],delay_days=14,yield_percent=50,demand_crop_id=crop,demand_percent=150,labour_percent=50,cash_percent=150))
    assert base==before
    f=Farm.model_validate(changed);original=Farm.model_validate(base)
    assert (f.batches[0].harvest_date-original.batches[0].harvest_date).days==14
    assert f.batches[0].expected_marketable_kg==original.batches[0].expected_marketable_kg/2
    assert f.resources.labour_hours_per_week==original.resources.labour_hours_per_week/2
    assert f.resources.cash_sgd==original.resources.cash_sgd*Decimal('1.5')
    assert next(o for o in f.orders if o.crop_id==crop).quantity_kg==next(o for o in original.orders if o.crop_id==crop).quantity_kg*Decimal('1.5')
    assert f.cutoff==original.cutoff and f.version==original.version

def test_map_highlights_only_changed_controls_not_idle_selectors(env):
    c,s,t=env
    farm=s.latest_farm(t)
    controls={'batch_id':farm['batches'][0]['id'],'demand_crop_id':'lettuce'}
    unchanged=create(c,key='unchanged-map',controls=controls).json()
    assert unchanged['affected_bed_ids']==[]
    demand=create(c,key='demand-map',controls={**controls,'demand_percent':130}).json()
    assert demand['affected_crop_ids']==['lettuce']
    lettuce_recipes={r['id'] for r in farm['recipes'] if r['crop_id']=='lettuce'}
    assert set(demand['affected_bed_ids'])=={b['bed_id'] for b in farm['batches'] if b['recipe_id'] in lettuce_recipes}

@pytest.mark.parametrize('controls',[{'delay_days':15},{'yield_percent':49},{'demand_percent':151},{'cash_percent':49},{'labour_percent':151},{'delay_days':True},{'batch_id':'missing'},{'demand_crop_id':'bayam'},{'delay_days':1},{'demand_percent':101}])
def test_control_bounds_and_targets(env,controls):
    c,_,_=env
    assert create(c,controls=controls).status_code==422

def test_branch_job_isolation_idempotency_persistence_and_quest(env,monkeypatch):
    c,s,t=env
    monkeypatch.setattr(s,'reserve_calls',lambda *a:pytest.fail('Numerical branch made inference reservation'))
    farm=deepcopy(s.latest_farm(t));main=s.latest_run(t)
    body=dict(name='Labour lesson',quest_id='short_handed_week',controls={'labour_percent':50})
    first=create(c,**body).json()
    assert create(c,**body).json()['id']==first['id']
    assert create(c,name='changed').status_code==409
    result=run(c,s,t,first['id'])
    assert result['status']=='COMPLETED' and result['result']['strategies']
    assert result['inference_calls']==0
    if result['acceptance']:
        chosen=next(row for row in result['result']['strategies'] if row['id']==result['accepted_strategy_id'])
        assert result['acceptance']['strategy_hash']==content_hash(chosen)
        assert result['acceptance']['validation_report_id']==content_hash(chosen['violations'])
        assert result['acceptance']['simulation_only'] is True
    assert s.latest_farm(t)==farm and s.latest_run(t)==main
    again=c.post(f"/api/v1/scenarios/{first['id']}/run",headers={'Idempotency-Key':'run'}).json()
    assert again['reused'] and again['result']==result['result']
    assert c.post(f"/api/v1/scenarios/{first['id']}/run",headers={'Idempotency-Key':'new'}).status_code==409
    assert c.get('/api/v1/scenarios').json()['scenarios'][0]['result']==result['result']
    p=c.post('/api/v1/quests/short_handed_week/inspect',json={'scenario_id':first['id']}).json()
    assert p['status']=='completed' and len(p['badges'])==2
    assert c.post('/api/v1/quests/tight_budget/inspect',json={'scenario_id':first['id']}).status_code==409
    assert c.get('/api/v1/scenarios/compare',params={'ids':first['id']}).json()['baseline']==result['baseline']


def test_tenant_isolation_all_routes(env):
    c,s,t=env
    one=create(c).json();run(c,s,t,one['id'])
    c.cookies.clear();assert c.get('/api/v1/scenarios').status_code==401
    c.get('/api/v1/bootstrap')
    assert c.get('/api/v1/scenarios').json()=={'scenarios':[]}
    assert c.get(f"/api/v1/scenarios/{one['id']}").status_code==404
    assert c.post(f"/api/v1/scenarios/{one['id']}/run",headers={'Idempotency-Key':'run'}).status_code==404
    assert create(c,parent_scenario_id=one['id']).status_code==404
    assert c.get('/api/v1/scenarios/compare',params={'ids':one['id']}).status_code==404


def test_continue_compare_requires_same_frozen_root_and_limit(env):
    c,s,t=env
    one=run(c,s,t,create(c,controls={'cash_percent':90}).json()['id'])
    child=run(c,s,t,create(c,'child',parent_scenario_id=one['id'],controls={'cash_percent':90}).json()['id'])
    assert Decimal(child['input_snapshot']['resources']['cash_sgd'])==Decimal(one['input_snapshot']['resources']['cash_sgd'])*Decimal('.9')
    assert child['baseline_hash']==one['baseline_hash']
    assert c.get('/api/v1/scenarios/compare',params={'ids':one['id']+','+child['id']}).status_code==200
    assert c.get('/api/v1/scenarios/compare',params={'ids':','.join([one['id']]*4)}).status_code==422
    changed=deepcopy(s.latest_farm(t));changed['resources']['cash_sgd']='10000';s.save_farm(t,changed)
    other=run(c,s,t,create(c,'other').json()['id'])
    assert c.get('/api/v1/scenarios/compare',params={'ids':one['id']+','+other['id']}).status_code==409


def test_infeasible_experiment_still_completes_learning(env):
    c,s,t=env
    farm=deepcopy(s.latest_farm(t));farm['resources']['labour_hours_per_week']='0';s.save_farm(t,farm)
    one=run(c,s,t,create(c,quest_id='short_handed_week',controls={'labour_percent':50}).json()['id'])
    assert one['status']=='COMPLETED' and one['simulation_status']=='NO_FEASIBLE_PLAN'
    assert all(r['violations'] for r in one['result']['strategies'])
    assert c.post('/api/v1/quests/short_handed_week/inspect',json={'scenario_id':one['id']}).json()['status']=='completed'


def test_restart_only_requeues_numerical_work(env):
    c,s,t=env;one=create(c).json();one['status']='RUNNING';save_scenario(s,t,one)
    interrupt_scenarios(s)
    assert get_scenario(s,t,one['id'])['status']=='QUEUED'
    execute_scenario(s,t,one['id'])
    assert get_scenario(s,t,one['id'])['status']=='COMPLETED'

@pytest.mark.parametrize('quest,controls',[
    ('late_harvest',{'delay_days':7,'yield_percent':65}),
    ('busy_market',{'demand_crop_id':'caixin','demand_percent':150}),
])
def test_harvest_and_market_experiments_compute_changed_forecasts(env,quest,controls):
    c,s,t=env
    if quest=='late_harvest':controls=dict(controls,batch_id=s.latest_farm(t)['batches'][0]['id'])
    scenario=run(c,s,t,create(c,quest_id=quest,controls=controls).json()['id'])
    base=scenario['baseline']['forecast'];after=scenario['result']['forecast']
    assert scenario['result']['input_hash']==scenario['input_hash']
    assert scenario['affected_deliveries']
    if quest=='late_harvest':
        before=next(r for r in base['harvest'] if r['batch_id']==controls['batch_id'])
        changed=next(r for r in after['harvest'] if r['batch_id']==controls['batch_id'])
        assert changed['harvest_date']>before['harvest_date']
        assert changed['marketable_kg']<before['marketable_kg']
    else:
        before=sum(r['expected_kg'] for r in base['demand'] if r['crop_id']=='caixin')
        changed=sum(r['expected_kg'] for r in after['demand'] if r['crop_id']=='caixin')
        assert changed>before
    for strategy in scenario['result']['strategies']:
        assert all(abs(row['balance_error'])<1e-6 for row in strategy['ledger'])
    assert c.post(f'/api/v1/quests/{quest}/inspect',json={'scenario_id':scenario['id']}).json()['status']=='completed'


def test_branch_cannot_replace_accepted_main_worklist(env,monkeypatch):
    c,s,t=env
    import services.api.app as app_module
    monkeypatch.setattr(app_module,'plan',lambda farm:plan(farm,time_limit=.03))
    mission=c.post('/api/v1/planning-runs',json={'council':False},headers={'Idempotency-Key':'main'}).json()
    app_module.Worker(s).execute(t,mission['id'])
    original=c.get('/api/v1/planning-runs/'+mission['id']).json()
    assert original['status']=='ACCEPTED_FOR_SIMULATION'
    csv=c.get('/api/v1/planning-runs/'+mission['id']+'/worklist.csv').text
    branch=run(c,s,t,create(c,controls={'cash_percent':50}).json()['id'])
    assert branch['status']=='COMPLETED'
    assert c.get('/api/v1/bootstrap').json()['latest_run']['id']==mission['id']
    assert c.get('/api/v1/planning-runs/'+mission['id']+'/worklist.csv').text==csv
    assert c.get('/api/v1/planning-runs/'+mission['id']).json()==original


def test_proposed_experiment_uses_exact_conversation_snapshot(env):
    c,s,t=env
    original=deepcopy(s.latest_farm(t))
    conversation=c.post('/api/v1/conversations',json={'advisor':'ben'},headers={'Idempotency-Key':'conversation'}).json()
    changed=deepcopy(original);changed['resources']['cash_sgd']='12345';s.save_farm(t,changed)
    branch=create(c,source_conversation_id=conversation['id'],controls={'cash_percent':50}).json()
    assert branch['baseline_snapshot']==original
    assert Decimal(branch['input_snapshot']['resources']['cash_sgd'])==Decimal(original['resources']['cash_sgd'])/2
    assert s.latest_farm(t)['resources']['cash_sgd']=='12345'
    c.cookies.clear();c.get('/api/v1/bootstrap')
    assert create(c,source_conversation_id=conversation['id']).status_code==404

@pytest.mark.parametrize('quest,controls',[
    ('late_harvest',{}),
    ('busy_market',{'cash_percent':75}),
    ('short_handed_week',{'demand_crop_id':'caixin','demand_percent':150}),
    ('tight_budget',{'labour_percent':50}),
])
def test_quest_requires_its_own_changed_assumption(env,quest,controls):
    c,_,_=env
    assert create(c,quest_id=quest,controls=controls).status_code==422
    assert c.get('/api/v1/scenarios').json()['scenarios']==[]
    assert all(q['status']=='available' for q in c.get('/api/v1/quests').json()['quests'])


def test_scenario_without_imported_farm_returns_recoverable_conflict(env):
    c,s,_=env
    _,token=s.new_session();c.cookies.clear();c.cookies.set('farmtact_session',token)
    result=create(c)
    assert result.status_code==409 and 'Import a farm' in result.json()['detail']


def test_legacy_computed_impacts_include_empty_beds_and_changed_delivery_dates():
    from services.api.scenarios import computed_impacts
    baseline={'name':'Balanced','allocations':[],'ledger':[{'date':'2026-09-10','demand_kg':10,'delivered_kg':5},{'date':'2026-09-11','demand_kg':10,'delivered_kg':5}]}
    after=deepcopy(baseline);after['allocations']=[{'id':'new-plan','bed_id':'bed-09','crop_id':'caixin'}];after['ledger'][1]['delivered_kg']=8
    orders=[{'id':'early','crop_id':'caixin','due_date':'2026-09-10'},{'id':'changed','crop_id':'lettuce','due_date':'2026-09-11'}]
    result=computed_impacts({'baseline':{'strategies':[baseline]},'result':{'strategies':[after]},'baseline_snapshot':{'orders':orders},'input_snapshot':{'orders':orders}})
    assert result['affected_bed_ids']==['bed-09']
    assert [row['order_id'] for row in result['affected_deliveries']]==['changed']
    assert 'Legacy frozen strategies without order allocations' in result['affected_basis']


def test_no_change_sandbox_reuses_frozen_baseline_exactly(env):
    c,s,t=env
    result=run(c,s,t,create(c,controls={}).json()['id'])
    assert result['result']==result['baseline']
    assert all(value==0 for row in result['policy_comparisons'] for value in row['deltas'].values())
    assert result['affected_bed_ids']==[] and result['affected_deliveries']==[]
