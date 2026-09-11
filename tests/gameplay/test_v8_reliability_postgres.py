"""PostgreSQL serialization checks for V8 scenario retry and cancellation."""
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import delete

from packages.fixtures import synthetic_farm
from services.api.app import create_app
from services.api.conversation_store import (
    ConversationStore,conversation_events,conversation_messages,conversation_requests,conversations,
)
from services.api.scenarios import branches,execute_scenario,quest_progress
from services.api.store import Store,farms,now,tenants


def test_postgres_serializes_scenario_retry_and_conversation_cancel(monkeypatch):
    store=Store();assert store.engine.dialect.name=='postgresql'
    tenant,token=store.new_session();store.save_farm(tenant,synthetic_farm().model_dump(mode='json'))
    conversation_id=None
    try:
        app=create_app(store,start_worker=False)
        with TestClient(app) as client:
            client.cookies.set('farmtact_session',token)
            created=client.post('/api/v1/scenarios',json={'controls':{'cash_percent':75}},headers={'Idempotency-Key':'v8-retry-create'}).json()
            client.post(f"/api/v1/scenarios/{created['id']}/run",headers={'Idempotency-Key':'v8-run'})
            monkeypatch.setattr('services.api.scenarios.plan',lambda *_args,**_kwargs:(_ for _ in ()).throw(RuntimeError('transient')))
            execute_scenario(store,tenant,created['id'])

            def retry(_):
                return client.post(f"/api/v1/scenarios/{created['id']}/retry",headers={'Idempotency-Key':'v8-run'}).json()
            with ThreadPoolExecutor(max_workers=6) as pool:responses=list(pool.map(retry,range(6)))
            assert {row['attempt_count'] for row in responses}=={2}
            assert sum(not row.get('reused',False) for row in responses)==1

            def cancel(_):return client.post(f"/api/v1/scenarios/{created['id']}/cancel").json()
            with ThreadPoolExecutor(max_workers=6) as pool:cancelled=list(pool.map(cancel,range(6)))
            assert {row['status'] for row in cancelled}=={'CANCELLED'}
            assert sum(not row['reused'] for row in cancelled)==1

        persistence=ConversationStore(store)
        payload=dict(id='v8-conversation-'+tenant,status='OPEN',created_at=now(),updated_at=now())
        conversation,_=persistence.create_conversation(tenant,'v8-conversation-key','same',payload);conversation_id=conversation['id']
        request,_,_=persistence.create_request(tenant,conversation_id,'v8-request-key','same',dict(id='v8-request-'+tenant,conversation_id=conversation_id,status='QUEUED',roles=['demand_analyst'],created_at=now()),dict(id='v8-message-'+tenant,speaker='user',content='question',created_at=now()))
        def cancel_request(_):return persistence.cancel_request(tenant,conversation_id,request['id'])
        with ThreadPoolExecutor(max_workers=6) as pool:request_results=list(pool.map(cancel_request,range(6)))
        assert sum(changed for _,changed in request_results)==1
        assert {payload['status'] for payload,_ in request_results}=={'CANCELLED'}
    finally:
        with store.engine.begin() as connection:
            connection.execute(delete(conversation_events).where(conversation_events.c.tenant_id==tenant))
            connection.execute(delete(conversation_messages).where(conversation_messages.c.tenant_id==tenant))
            connection.execute(delete(conversation_requests).where(conversation_requests.c.tenant_id==tenant))
            connection.execute(delete(conversations).where(conversations.c.tenant_id==tenant))
            connection.execute(delete(quest_progress).where(quest_progress.c.tenant_id==tenant))
            connection.execute(delete(branches).where(branches.c.tenant_id==tenant))
            connection.execute(delete(farms).where(farms.c.tenant_id==tenant))
            connection.execute(delete(tenants).where(tenants.c.id==tenant))
        store.engine.dispose()
