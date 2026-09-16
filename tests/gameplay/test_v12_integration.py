from copy import deepcopy
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from services.api.app import create_app
from services.api.store import Store,tenants
from services.api.planning_sessions import execute_job


def test_nested_transaction_rolls_back_entire_mutation():
    store=Store('sqlite://')
    with pytest.raises(RuntimeError):
        with store.transaction():
            tenant,_=store.new_session()
            with store.transaction(tenant):
                raise RuntimeError('fail before receipt')
    with store.connection() as c:assert not c.execute(select(tenants)).first()


def post(client,path,body,key=None):
    return client.post('/api/v1'+path,json=body,headers={'Idempotency-Key':key or uuid4().hex})


def test_v12_actual_routes_calculate_propose_approve_task_and_replay():
    store=Store('sqlite://')
    with TestClient(create_app(store,start_worker=False)) as client:
        client.get('/api/v1/bootstrap')
        tenant=store.authenticate(client.cookies.get('farmtact_session'))
        response=post(client,'/planning-sessions',{'workflow':True})
        assert response.status_code==201,response.text
        session=response.json();path='/planning-sessions/'+session['id']
        response=post(client,path+'/calculate',{'revision':session['revision']})
        execute_job(store,tenant,response.json()['job']['id'])
        session=client.get('/api/v1'+path).json()
        assert session['status']=='COMPLETED',session.get('job')
        conversation=post(client,'/conversations',{'advisor':'ravi','snapshot_kind':'planning','snapshot_id':session['id']})
        assert conversation.status_code in (200,201),conversation.text
        conversation=client.get('/api/v1/conversations/'+conversation.json()['id']).json()
        assert conversation['snapshot_ref']['kind']=='planning'
        assert session['result_id'] in conversation['snapshot_ref']['id']
        assert post(client,path+'/advance',{'revision':session['revision'],'days':1}).status_code==409
        response=post(client,'/farm-workflow/proposals',dict(session_id=session['id'],base_revision=session['revision'],changes=[{'kind':'planning_assumptions','assumptions':{}}],idempotency_key='proposal-1'))
        assert response.status_code==201,response.text
        proposal=response.json()
        response=post(client,'/farm-workflow/proposals/'+proposal['id']+'/apply',dict(proposal_id=proposal['id'],expected_base_revision=proposal['base_revision'],idempotency_key='apply-1'))
        assert response.status_code==202,response.text
        proposal=response.json()
        approval=dict(proposal_id=proposal['id'],proposal_revision=proposal['proposal_revision'],idempotency_key='approve-1')
        endpoint='/farm-workflow/proposals/'+proposal['id']+'/approve-actions'
        assert post(client,endpoint,approval).status_code==409
        execute_job(store,tenant,proposal['recalculation_job']['id'])
        response=post(client,endpoint,approval)
        assert response.status_code==200,response.text
        approved=response.json()
        assert approved['tasks']
        assert post(client,endpoint,approval).json()==approved
        session=client.get('/api/v1'+path).json()
        assert session['approved_result_id']==proposal['recalculation_job']['id']
        task=next(task for task in approved['tasks'] if task['action']=='sow')
        result=dict(expected_status='pending',result_status='completed',checklist_completed=task['checklist'])
        response=post(client,'/farm-workflow/tasks/'+task['id']+'/result',result)
        assert response.status_code==200,response.text
        assert post(client,'/farm-workflow/tasks/'+task['id']+'/result',result).status_code==409
        replay=client.get('/api/v1/farm-workflow').json()
        assert any(t['id']==task['id'] and t['status']=='completed' for t in replay['tasks'])
        latest=client.get('/api/v1'+path).json()
        assert latest['reported_forecast']['basis']=='user_reported_projection'
        assert latest['reported_forecast']['source_task_events'][0]['task_id']==task['id']
