from copy import deepcopy
import secrets
from fastapi.testclient import TestClient
from sqlalchemy import select
from services.api.app import create_app
from services.api.store import Store
from services.api import council_research as r


def test_action_retry_returns_original_revision_and_challenge_revalidates():
    store=Store('sqlite://')
    with TestClient(create_app(store,start_worker=False)) as c:
        c.get('/api/v1/bootstrap')
        s=c.post('/api/v1/council-research',json={},headers={'Idempotency-Key':'create'}).json()
        first_body=dict(action='challenge',revision=s['revision'],text='Why rainfall?')
        first=c.post(f"/api/v1/council-research/{s['id']}/actions",json=first_body,headers={'Idempotency-Key':'challenge'}).json()
        def action(state,kind,**kwargs):
            response=c.post(f"/api/v1/council-research/{state['id']}/actions",json=dict(action=kind,revision=state['revision'],**kwargs),headers={'Idempotency-Key':secrets.token_hex(8)})
            assert response.status_code==200,response.text
            return response.json()
        s=action(first,'resolve',resolution='corrected')
        s=action(s,'propose',operation='labour',labour_percent=75)
        s=action(s,'apply')
        assert s['challenge']['status']=='unresolved'
        assert s['challenge']['input_version']==s['input_version']==2
        assert s['challenge']['revalidation_of']==first['challenge']['id']
        retry=c.post(f"/api/v1/council-research/{s['id']}/actions",json=first_body,headers={'Idempotency-Key':'challenge'})
        assert retry.json()==first
        assert c.get(f"/api/v1/council-research/{s['id']}").json()==s
        history=c.get(f"/api/v1/council-research/{s['id']}/history?limit=2").json()
        assert len(history['revisions'])==2 and history['next_cursor']==1
        assert history['inference_triggered'] is False


def test_bounded_current_view_keeps_complete_append_only_history():
    store=Store('sqlite://');tenant,_=store.new_session()
    s=r.new_session(r.NewSession())
    with store.transaction(tenant) as c:
        c.execute(r.SESSIONS.insert().values(id=s['id'],tenant_id=tenant,idempotency_key='new',request_hash='new',payload=s))
        r.record_revision(store,tenant,s)
    expected={0:deepcopy(s)}
    for i in range(1,271):
        with store.transaction(tenant):
            r.append(s,'Farmer',f'History message {i}');r.event(s,'history_test',number=i)
            s['revision']=i;r.save(store,tenant,s)
        if i in (1,120,240,270):expected[i]=deepcopy(s)
    assert len(s['messages'])==120 and len(s['events'])==240
    for revision,snapshot in expected.items():assert r.revision_snapshot(store,tenant,s['id'],revision)==snapshot
    with store.connection() as c:
        rows=c.execute(select(r.HISTORY.c.payload)).scalars().all()
    assert sum(len(row['messages']) for row in rows)==271
    assert sum(len(row['events']) for row in rows)==271
    other,_=store.new_session()
    assert r.revision_snapshot(store,other,s['id'],270) is None
