"""Explorer contracts, isolation, reproducibility and preview/worker agreement."""
from copy import deepcopy
from datetime import timedelta
import csv
import io

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select

from packages.contracts import Farm,content_hash
from packages.fixtures import synthetic_farm
from packages.planner import plan
from services.api.app import create_app
from services.api.data_explorer import snapshots
from services.api.scenarios import execute_scenario,interrupt_scenarios
from services.api.store import Store

@pytest.fixture
def env(monkeypatch):
    import services.api.scenarios as scenarios
    monkeypatch.setattr(scenarios,'plan',lambda farm,**kwargs:plan(farm,time_limit=0,**kwargs))
    store=Store('sqlite://')
    monkeypatch.setattr(store,'reserve_calls',lambda *a,**k:pytest.fail('Numerical explorer reserved inference'))
    with TestClient(create_app(store,start_worker=False)) as client:
        client.get('/api/v1/bootstrap')
        yield client,store,store.authenticate(client.cookies.get('farmtact_session'))


def save(c,key='saved',**body):
    r=c.post('/api/v1/data-explorer/snapshots',json=body,headers={'Idempotency-Key':key})
    assert r.status_code==201,r.text
    return r.json()


def scenario(c,s,t,key='branch',**body):
    r=c.post('/api/v1/scenarios',json=body,headers={'Idempotency-Key':key})
    assert r.status_code==201,r.text
    id=r.json()['id']
    r=c.post(f'/api/v1/scenarios/{id}/run',headers={'Idempotency-Key':'run-'+key})
    assert r.status_code==202,r.text
    execute_scenario(s,t,id)
    r=c.get(f'/api/v1/scenarios/{id}').json()
    assert r['status']=='COMPLETED',r
    return r


def test_reference_and_preview_default_parity(env):
    c,s,t=env
    farm=deepcopy(s.latest_farm(t))
    ref=c.get('/api/v1/data-explorer/snapshots/reference').json()
    prev=c.post('/api/v1/data-explorer/preview',json={}).json()
    assert prev['unsaved'] and not ref['unsaved']
    assert ref['records']==prev['records'] and ref['forecast']==prev['forecast']
    assert ref['content_hash']==prev['content_hash']
    assert ref['counts']['history']==48 and ref['counts']['orders']==32
    assert ref['counts']['beds']==16 and ref['counts']['recipes']==4
    assert ref['result'] is None and ref['counts']['allocations']==0
    assert ref['records']['history'][0]['ordered_kg']=='27'
    assert s.latest_farm(t)==farm and s.latest_run(t) is None


@pytest.mark.parametrize('body',[
    {'generator_settings':{'history_multiplier':.49}},
    {'generator_settings':{'history_trend':.31}},
    {'generator_settings':{'pattern_amplitude':2.01}},
    {'generator_settings':{'orders_multiplier':1.51}},
    {'generator_settings':{'price_multiplier':.49}},
    {'forecast_settings':{'alpha':.049}},
    {'forecast_settings':{'alpha':.951}},
    {'forecast_settings':{'alpha':True}},
    {'generator_settings':{'path':'/etc/passwd'}},
    {'cutoff':'2050-01-01'},
])
def test_bounded_preview(env,body):
    c,_,_=env
    assert c.post('/api/v1/data-explorer/preview',json=body).status_code==422


def test_freeze_idempotency_hashes_and_save_reload(env):
    c,s,t=env
    body={'name':'Larger demand','generator_settings':{'history_multiplier':1.4},'forecast_settings':{'alpha':.7}}
    a=save(c,**body);b=save(c,**body)
    assert a['id']==b['id'] and b['reused']
    assert c.post('/api/v1/data-explorer/snapshots',json={},headers={'Idempotency-Key':'saved'}).status_code==409
    fresh=c.get('/api/v1/data-explorer/snapshots/'+a['id']).json()
    assert fresh==a
    other=save(c,key='different-alpha',generator_settings=body['generator_settings'],forecast_settings={'alpha':.1})
    assert other['content_hash']!=a['content_hash']
    assert other['records']['history']==a['records']['history']
    with s.connection() as connection:
        frozen=connection.execute(select(snapshots.c.payload).where(snapshots.c.tenant_id==t)).scalars().all()
    assert next(row for row in frozen if row['id']==a['id'])['forecast_settings']=={'alpha':.7}
    assert len(frozen)==2


def test_alpha_preview_agrees_with_worker_and_continuation(env):
    c,s,t=env;main=deepcopy(s.latest_farm(t))
    body={'generator_settings':{'history_trend':.3},'forecast_settings':{'alpha':.8}}
    preview=c.post('/api/v1/data-explorer/preview',json=body).json()
    saved=save(c,**body)
    a=scenario(c,s,t,explorer_snapshot_id=saved['id'])
    assert a['result']['forecast']==preview['forecast']
    assert a['baseline']['forecast']['forecast_settings']=={'alpha':.35}
    assert a['forecast_settings']=={'alpha':.8}
    assert a['baseline_snapshot']==synthetic_farm().model_dump(mode='json')
    continued=scenario(c,s,t,key='child',parent_scenario_id=a['id'],controls={'labour_percent':50})
    assert continued['forecast_settings']==a['forecast_settings']
    assert continued['baseline']==a['baseline']
    assert continued['generator_settings']==a['generator_settings']
    replay=c.get('/api/v1/data-explorer/snapshots/scenario:'+continued['id']).json()
    assert replay['forecast']==continued['result']['forecast']
    assert replay['result']==continued['result']
    assert s.latest_farm(t)==main and s.latest_run(t) is None
    assert c.get('/api/v1/scenarios/compare',params={'ids':a['id']+','+continued['id']}).status_code==200


def test_smoothing_only_change_is_not_replaced_by_baseline(env):
    c,s,t=env
    a=scenario(c,s,t,explorer_snapshot_id=save(c,forecast_settings={'alpha':.95})['id'])
    assert a['input_hash']==a['baseline_hash']
    assert a['result']['forecast']['demand']!=a['baseline']['forecast']['demand']
    assert a['result']['numerical_input_hash']!=a['baseline']['numerical_input_hash']


def test_unrelated_roots_rejected_even_identical_raw_records(env):
    c,s,t=env
    a=scenario(c,s,t,explorer_snapshot_id=save(c)['id'])
    b=scenario(c,s,t,key='farm')
    assert a['baseline_hash']==b['baseline_hash']
    assert c.get('/api/v1/scenarios/compare',params={'ids':a['id']+','+b['id']}).status_code==409
    assert c.post('/api/v1/scenarios',json={'explorer_snapshot_id':save(c,key='c')['id'],'parent_scenario_id':b['id']},headers={'Idempotency-Key':'bad-source'}).status_code==422


def test_filters_pagination_numeric_sort_download_and_relationships(env):
    c,_,_=env
    params={'dataset':'history','crop_id':'caixin','start':'2026-07-01','end':'2026-08-31','sort':'ordered_kg','descending':'true','page_size':3}
    data=c.get('/api/v1/data-explorer/records',params=params).json()
    assert data['total']==8 and len(data['records'])==3
    assert all(r['crop_id']=='caixin' for r in data['records'])
    assert [float(r['ordered_kg']) for r in data['records']]==[33,33,31]
    rows=c.get('/api/v1/data-explorer/export',params={**{k:v for k,v in params.items() if k!='page_size'},'format':'json'}).json()['records']
    assert len(rows)==8 and rows[:3]==data['records']
    csv_data=c.get('/api/v1/data-explorer/export',params={'dataset':'batches'}).text
    parsed=list(csv.DictReader(io.StringIO(csv_data)))
    assert parsed[0]['bed_id']=='bed-01' and parsed[0]['recipe_id']=='caixin-demo-v1'
    empty=c.get('/api/v1/data-explorer/records',params={'q':'definitely-not-a-record'}).json()
    assert empty['total']==0
    forecast=c.get('/api/v1/data-explorer/records',params={'dataset':'forecast','crop_id':'caixin'}).json()
    assert len(forecast['records'][0]['history_record_ids'])==12
    assert forecast['records'][0]['order_record_ids']==['order-0-0']


@pytest.mark.parametrize('params',[
    {'dataset':'../../etc/passwd'},{'sort':'not_a_field'},{'page_size':10000},
    {'start':'2026-09-09','end':'2026-08-01'},{'crop_id':'unknown'},{'q':'x'*101},
])
def test_bounded_record_queries(env,params):
    c,_,_=env
    assert c.get('/api/v1/data-explorer/records',params=params).status_code==422


def test_imported_farm_cutoff_and_csv_injection(env):
    c,s,t=env
    f=synthetic_farm();f.history[0].available_at=f.cutoff+timedelta(days=1)
    f.beds[0].name=' =IMPORTXML("http://example.invalid")';f.orders[0].quantity_kg=__import__('decimal').Decimal('123')
    s.save_farm(t,f.model_dump(mode='json'))
    listing=c.get('/api/v1/data-explorer/snapshots').json()['snapshots']
    selected=next(r for r in listing if r['name']=='Main farm · version 2')
    d=c.get('/api/v1/data-explorer/snapshots/'+selected['id']).json()
    assert d['generator_settings'] is None
    assert d['records']['orders'][0]['quantity_kg']=='123'
    assert not d['records']['history'][0]['available_at_cutoff']
    assert d['forecast']['demand'][0]['history_periods']==11
    assert d['records']['history'][0]['id'] not in d['records']['forecast'][0]['history_record_ids']
    exported=c.get('/api/v1/data-explorer/export',params={'snapshot_id':selected['id'],'dataset':'beds'}).text
    assert list(csv.DictReader(io.StringIO(exported)))[0]['name'].startswith("' =")
    assert c.get('/api/v1/data-explorer/snapshots/reference').json()['records']['orders'][0]['quantity_kg']=='22'


def test_tenant_isolation_read_write_and_no_foreign_branch(env):
    c,s,t=env
    saved=save(c); branch=scenario(c,s,t,explorer_snapshot_id=saved['id'])
    main=next(r['id'] for r in c.get('/api/v1/data-explorer/snapshots').json()['snapshots'] if r['kind']=='farm')
    c.cookies.clear()
    assert c.get('/api/v1/data-explorer/snapshots').status_code==401
    c.get('/api/v1/bootstrap')
    assert len(c.get('/api/v1/data-explorer/snapshots').json()['snapshots'])==2
    for id in (saved['id'],main,'scenario:'+branch['id']):
        assert c.get('/api/v1/data-explorer/snapshots/'+id).status_code==404
        assert c.get('/api/v1/data-explorer/records',params={'snapshot_id':id}).status_code==404
        assert c.get('/api/v1/data-explorer/export',params={'snapshot_id':id}).status_code==404
    assert c.post('/api/v1/scenarios',json={'explorer_snapshot_id':saved['id']},headers={'Idempotency-Key':'foreign'}).status_code==404


def test_preview_rate_limit_durable_session_and_ip(env):
    c,s,t=env
    for _ in range(30):assert c.post('/api/v1/data-explorer/preview',json={}).status_code==200
    r=c.post('/api/v1/data-explorer/preview',json={})
    assert r.status_code==429 and r.json()['limit']=='explorer_preview_session'
    assert int(r.headers['Retry-After'])>0
    from services.api.security import AbuseLimits,PREVIEW_IP,Limited
    limits=AbuseLimits(s)
    with pytest.raises(Limited):limits.consume([(PREVIEW_IP,'unresolved-peer')]*30)


def test_infeasible_results_inspectable_and_aggregate_scope(env):
    c,s,t=env
    a=scenario(c,s,t,explorer_snapshot_id=save(c)['id'],controls={'labour_percent':50,'cash_percent':50})
    assert a['result']['strategies']
    d=c.get('/api/v1/data-explorer/snapshots/scenario:'+a['id'],params={'policy':'Lean'}).json()
    assert len(d['records']['weekly'])==8
    assert all('labour_capacity_hours' in row for row in d['records']['weekly'])
    scope=c.get('/api/v1/data-explorer/records',params={'snapshot_id':'scenario:'+a['id'],'dataset':'weekly','crop_id':'caixin'}).json()
    assert scope['scope']=='farm-wide' and scope['total']==0


def test_advisor_uses_frozen_scenario_settings_without_inference_on_open(env):
    c,s,t=env
    a=scenario(c,s,t,explorer_snapshot_id=save(c,forecast_settings={'alpha':.8})['id'])
    r=c.post('/api/v1/conversations',json={'advisor':'asha','snapshot_kind':'scenario','snapshot_id':a['id']},headers={'Idempotency-Key':'advisor'})
    assert r.status_code==201,r.text
    from services.api.conversation_store import ConversationStore
    conversation=ConversationStore(s).get_conversation(t,r.json()['id'])
    assert conversation['_scenario']['result']['forecast']['forecast_settings']=={'alpha':.8}
    assert conversation['_snapshot']==a['input_snapshot']
    assert conversation['snapshot_ref']['hash']==a['input_hash']


def test_saved_forecast_replay_does_not_recompute(env,monkeypatch):
    c,_,_=env
    saved=save(c,forecast_settings={'alpha':.7})
    import services.api.data_explorer as module
    monkeypatch.setattr(module,'forecast',lambda *a,**k:pytest.fail('Saved forecast was recomputed'))
    reread=c.get('/api/v1/data-explorer/snapshots/'+saved['id'])
    assert reread.status_code==200
    assert reread.json()['forecast']==saved['forecast']


def test_public_export_enforces_reuse_and_evaluation_is_original(env):
    c,_,_=env
    context=c.get('/api/v1/data-explorer/public').json()
    assert len(context['sources'])==23
    assert any(s['status']=='metadata_only' and s['record_count']==0 for s in context['sources'])
    assert c.get('/api/v1/data-explorer/public/export',params={'source_id':'D11'}).status_code==403
    assert c.get('/api/v1/data-explorer/public/export',params={'source_id':'D01'}).status_code==200
    assert c.get('/api/v1/data-explorer/public/records',params={'page_size':101}).status_code==422
    evaluation=c.get('/api/v1/data-explorer/evaluation').json()
    assert evaluation['forecast_settings']=={'alpha':.35}
    assert evaluation['fixture_hash']==content_hash(synthetic_farm())
    assert evaluation['dataset_name']=='Original generated dataset'
