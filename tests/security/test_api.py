import uuid
import pytest
from fastapi.testclient import TestClient
from services.api.app import create_app
from services.api.store import Store

@pytest.fixture
def env():
    s=Store('sqlite://');app=create_app(s,start_worker=False)
    with TestClient(app) as client:
        client.get('/api/v1/bootstrap')
        yield client,app

def start(client,key='mission',council=False):
    return client.post('/api/v1/planning-runs',json={'council':council},headers={'Idempotency-Key':key})

def test_auth_tenant_isolation_and_no_operational_acceptance(env):
    c,app=env;r=start(c).json()
    assert c.post('/api/v1/strategies/unknown/accept-for-simulation').status_code==403
    token=c.cookies.get('farmtact_session');c.cookies.clear()
    assert c.get('/api/v1/planning-runs/'+r['id']).status_code==401
    c.get('/api/v1/bootstrap')
    assert c.get('/api/v1/planning-runs/'+r['id']).status_code==404

def test_idempotency_and_schema_cannot_override_provider_or_phase(env):
    c,app=env;one=start(c);two=start(c)
    assert one.json()['id']==two.json()['id'] and two.json()['reused']
    assert start(c,council=True).status_code==409
    # Space schema probes across rate windows; abuse rejection has separate tests.
    import time
    tick=[time.time()]
    app.state.abuse_limits.clock=lambda:tick[0]
    for field in ('provider','model','tenant_id','development_phase','execution_mode','decision_policy'):
        tick[0]+=61
        assert c.post('/api/v1/planning-runs',json={'council':False,field:'attacker'},headers={'Idempotency-Key':field}).status_code==422

def test_cross_origin_and_upload_limits(env):
    c,app=env
    assert c.post('/api/v1/imports',json={'fixture':'synthetic_demo'},headers={'Origin':'https://evil.example'}).status_code==403
    assert c.post('/api/v1/imports',content=b'x'*1048577).status_code==413
    r=c.post('/api/v1/imports',json={'farm':{'secret':'should-not-be-echoed'}})
    assert r.status_code==422 and 'should-not-be-echoed' not in r.text

def test_worker_acceptance_replay_and_replan_idempotency(env):
    c,app=env;r=start(c).json();t=app.state.store.authenticate(c.cookies.get('farmtact_session'))
    app.state.store.claim(t,r['id']);app.state.worker.execute(t,r['id'])
    run=c.get('/api/v1/planning-runs/'+r['id']).json()
    assert run['status']=='ACCEPTED_FOR_SIMULATION'
    assert run['council_status']=='not_run' and run['claims']==[]
    replay=c.get('/api/v1/planning-runs/'+r['id']+'/replay').json()
    assert replay['execution_mode']=='replay' and replay['strategies']==run['strategies']
    assert 'input_snapshot' not in replay
    params=dict(json={'disruption':'crop_delay'},headers={'Idempotency-Key':'shock'})
    first=c.post('/api/v1/planning-runs/'+r['id']+'/replan',**params)
    second=c.post('/api/v1/planning-runs/'+r['id']+'/replan',**params)
    assert first.status_code==202 and second.status_code==202
    assert first.json()['id']==second.json()['id']
    assert c.get('/api/v1/bootstrap').json()['farm']['version']==2
    app.state.store.claim(t,first.json()['id']);app.state.worker.execute(t,first.json()['id'])
    new=c.get('/api/v1/planning-runs/'+first.json()['id']).json()
    assert new['input_version']==2 and new['disruption']['origin']=='synthetic'
    orig=app.state.store.get_run(t,r['id'])['input_snapshot']
    after=app.state.store.get_run(t,new['id'])['input_snapshot']
    assert [b['sow_date'] for b in orig['batches']]==[b['sow_date'] for b in after['batches']]
    assert [b['transplant_date'] for b in orig['batches']]==[b['transplant_date'] for b in after['batches']]

def test_cancel_queued_never_calls_provider(env,monkeypatch):
    c,app=env;r=start(c,council=True).json();c.post('/api/v1/planning-runs/'+r['id']+'/cancel')
    t=app.state.store.authenticate(c.cookies.get('farmtact_session'))
    monkeypatch.setattr(app.state.store,'reserve_calls',lambda *a:pytest.fail('Cancelled run reserved paid calls'))
    app.state.store.claim(t,r['id']);app.state.worker.execute(t,r['id'])
    assert c.get('/api/v1/planning-runs/'+r['id']).json()['status']=='CANCELLED'


def test_shared_replay_read_only_and_worklist_version_guard(env,monkeypatch):
    c,app=env
    monkeypatch.setattr(app.state.store,'reserve_calls',lambda *a:pytest.fail('Read-only replay reserved inference'))
    before=app.state.store.pending()
    replay=c.get('/api/v1/demo/replay')
    assert replay.status_code==200
    assert replay.json()['shared_demo'] and replay.json()['execution_mode']=='replay'
    assert replay.json()['data_mode']=='synthetic_demo'
    assert app.state.store.pending()==before
    assert c.post('/api/v1/planning-runs/'+replay.json()['id']+'/replan',json={},headers={'Idempotency-Key':'shared'}).status_code==404
    r=start(c).json();t=app.state.store.authenticate(c.cookies.get('farmtact_session'))
    app.state.store.claim(t,r['id']);app.state.worker.execute(t,r['id'])
    csv=c.get('/api/v1/planning-runs/'+r['id']+'/worklist.csv')
    assert csv.status_code==200 and 'SIMULATION_ONLY' in csv.text
    imported=c.post('/api/v1/imports',json={'fixture':'synthetic_demo'},headers={'Idempotency-Key':'import-refresh'})
    assert imported.status_code==201 and imported.json()['planning_run']['id']!=r['id']
    assert c.get('/api/v1/planning-runs/'+r['id']+'/worklist.csv').status_code==409


def test_changed_replan_body_rejects_reused_key(env):
    c,app=env;r=start(c).json();t=app.state.store.authenticate(c.cookies.get('farmtact_session'))
    app.state.store.claim(t,r['id']);app.state.worker.execute(t,r['id'])
    path='/api/v1/planning-runs/'+r['id']+'/replan';headers={'Idempotency-Key':'replan-body'}
    assert c.post(path,json={'council':False},headers=headers).status_code==202
    assert c.post(path,json={'council':True},headers=headers).status_code==409


def test_inputs_changed_during_planning_restart_validation_automatically(env,monkeypatch):
    from packages.fixtures import synthetic_farm
    import services.api.app as module
    c,app=env;r=start(c).json();t=app.state.store.authenticate(c.cookies.get('farmtact_session'))
    original=module.plan
    def changing(farm):
        result=original(farm)
        app.state.store.save_farm(t,synthetic_farm().model_dump(mode='json'))
        return result
    monkeypatch.setattr(module,'plan',changing)
    app.state.store.claim(t,r['id']);app.state.worker.execute(t,r['id'])
    stale=app.state.store.get_run(t,r['id'])
    assert stale['status']=='STALE_INPUT' and 'acceptance' not in stale
    refreshed=app.state.store.get_run(t,stale['superseded_by'])
    assert refreshed['input_version']==2 and refreshed['council_requested'] is False
    monkeypatch.setattr(module,'plan',original)
    app.state.store.claim(t,refreshed['id']);app.state.worker.execute(t,refreshed['id'])
    assert app.state.store.get_run(t,refreshed['id'])['status']=='ACCEPTED_FOR_SIMULATION'


def test_chunked_upload_stops_at_limit_and_invalid_length_is_client_error(env):
    c,_=env
    def chunks():
        for _ in range(17):yield b'x'*65536
    assert c.post('/api/v1/imports',content=chunks()).status_code==413
    assert c.post('/api/v1/imports',content=b'{}',headers={'Content-Length':'bad'}).status_code==400


def test_tls_terminated_deployment_forces_secure_session_cookie(monkeypatch):
    monkeypatch.setenv('FARMTACT_SECURE_COOKIES','true')
    with TestClient(create_app(Store('sqlite://'),start_worker=False)) as client:
        response=client.get('/api/v1/bootstrap')
        assert response.status_code==200
        assert all(cookie.secure for cookie in client.cookies.jar)
        assert 'HttpOnly' in response.headers['set-cookie']
        assert 'SameSite=strict' in response.headers['set-cookie']
