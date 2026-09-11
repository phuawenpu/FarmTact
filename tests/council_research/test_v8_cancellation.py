import secrets
from fastapi.testclient import TestClient
from services.api.app import create_app
from services.api.store import Store
from services.api import council_research as r


def test_queued_cancel_retry_and_original_action_replay():
    store=Store('sqlite://')
    with TestClient(create_app(store,start_worker=False)) as c:
        c.get('/api/v1/bootstrap')
        s=c.post('/api/v1/council-research',json={},headers={'Idempotency-Key':'new'}).json()
        def act(kind,key=None,body=None):
            nonlocal s
            response=c.post(f"/api/v1/council-research/{s['id']}/actions",json=body or dict(action=kind,revision=s['revision']),headers={'Idempotency-Key':key or secrets.token_hex(8)})
            assert response.status_code==200,response.text
            s=response.json();return s
        act('run');queued=dict(s)
        act('cancel_calculation')
        assert s['results'][-1]['status']=='CANCELLED'
        assert r.pending(store)==[]
        original_body=dict(action='retry_calculation',revision=s['revision'])
        first=act('retry_calculation','retry',original_body)
        assert s['results'][-1]['status']=='QUEUED' and s['results'][-1]['attempt']==2
        act('cancel_calculation')
        current=dict(s)
        assert act('retry_calculation','retry',original_body)==first
        assert c.get(f"/api/v1/council-research/{s['id']}").json()==current
        assert r.pending(store)==[]  # old receipt did not restart cancelled work


def test_cancel_during_calculation_discards_output(monkeypatch):
    store=Store('sqlite://')
    with TestClient(create_app(store,start_worker=False)) as c:
        c.get('/api/v1/bootstrap')
        s=c.post('/api/v1/council-research',json={},headers={'Idempotency-Key':'new'}).json()
        s=c.post(f"/api/v1/council-research/{s['id']}/actions",json=dict(action='run',revision=s['revision']),headers={'Idempotency-Key':'run'}).json()
        tenant,job=r.pending(store)[0]
        def calculate(*args,**kwargs):
            current=c.get(f"/api/v1/council-research/{s['id']}").json()
            response=c.post(f"/api/v1/council-research/{s['id']}/actions",json=dict(action='cancel_calculation',revision=current['revision']),headers={'Idempotency-Key':'cancel-running'})
            assert response.status_code==200
            return {'must_not_be_applied':True}
        # Inject at the API process boundary; numerical children are isolated.
        import services.api.numerical_worker as numerical
        monkeypatch.setattr(numerical,'calculate_research',calculate)
        r.execute(store,tenant,job)
        current=c.get(f"/api/v1/council-research/{s['id']}").json()
        result=current['results'][-1]
        assert result['status']=='CANCELLED' and 'calculation' not in result
        assert current['numerical_calculation_status']=='cancelled'
        assert not current['milestones'].get('calculated')
