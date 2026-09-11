from __future__ import annotations
import asyncio,json,os,secrets,threading,time
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Literal
from fastapi import FastAPI,Request,HTTPException,Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse,StreamingResponse,FileResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from packages.contracts import Farm,Strict,content_hash
from packages.fixtures import synthetic_farm
from packages.agents import COUNCIL_VERSION, COUNCIL_MAX_REQUESTS, council_review_issues, council_statuses
from packages.planner import validate_allocations
from services.api.numerical_worker import plan
from services.api.store import Store,now
from services.api.views import ROOT,farm_view,crop_views,source_views,capabilities

class MissionRequest(Strict):
    council: bool = True
    with_vision: bool = False
    council_policy: Literal['required','advisory'] = 'required'
class ReplanRequest(Strict):
    council: bool | None = None
    disruption: Literal['crop_delay'] = 'crop_delay'
    batch_id: str | None = Field(default=None,max_length=100)
    delay_days: int = Field(default=7,ge=0,le=14,strict=True)
    yield_percent: int = Field(default=80,ge=50,le=100,strict=True)
    input_version: int | None = Field(default=None,ge=1)
class ImportRequest(Strict):
    fixture: Literal['synthetic_demo'] | None = None
    farm: Farm | None = None
class AcceptanceRequest(Strict):
    input_version: int
    strategy_id: str

def create_mission(store,t,body,key,parent=None,disruption=None,replan_request=None):
    snapshot=store.latest_farm(t);fingerprint=content_hash(dict(snapshot=snapshot,request=body.model_dump(),parent=parent,disruption=disruption,replan_request=replan_request))
    if not key or len(key)>128:raise HTTPException(422,'Idempotency-Key required, maximum 128 characters')
    r=dict(id=secrets.token_hex(16),status='CREATED',created_at=now(),input_version=snapshot['version'],input_hash=content_hash(snapshot),input_snapshot=snapshot,source_snapshot=source_views(),evidence_version=content_hash((ROOT/'research/evidence_register.json').read_text()) if (ROOT/'research/evidence_register.json').exists() else None,execution_mode='test',data_mode='synthetic_demo',development_phase='autonomous_development',decision_policy='automatic_development',council_requested=body.council,with_vision=body.with_vision,council_status='pending' if body.council else 'not_run',strategies=[],claims=[],events=[],warnings=[],parent_run_id=parent,disruption=disruption,replan_request=replan_request)
    from services.api.market_signals import summarize_signals
    r['council_version']=COUNCIL_VERSION
    r['council_policy']=body.council_policy if body.council else 'not_requested'
    r['workflow_type']='planning_council' if body.council else 'numerical_planning'
    from services.api.provenance import runtime_provenance
    r['runtime_provenance']=runtime_provenance()
    r['market_signals']=summarize_signals(snapshot)
    from packages.news import freeze_for_farm
    parent_record=store.get_run(t,parent) if parent else None
    if parent and not parent_record:raise HTTPException(404,'Parent mission not found')
    from copy import deepcopy
    r['news_context']=deepcopy(parent_record.get('news_context')) if parent_record else freeze_for_farm(snapshot,r['created_at'])
    try:result,created=store.create_run(t,key,fingerprint,r)
    except ValueError as e:raise HTTPException(409,str(e))
    return dict(id=result['id'],status=result['status'],reused=not created)

class Worker:
    def __init__(self,store):self.store=store;self.stop=threading.Event();self.thread=None;self.provider_thread=None
    def start(self):
        from services.api.planning_sessions import recover as recover_planning
        recover_planning(self.store)
        self.store.interrupt_abandoned()
        from services.api.scenarios import interrupt_scenarios
        interrupt_scenarios(self.store)
        from services.api.council_research import recover
        recover(self.store)
        from services.api.conversation_store import ConversationStore
        ConversationStore(self.store).interrupt_abandoned()
        self.thread=threading.Thread(target=self.loop,args=('numerical',),daemon=True,name='farmtact-numerical')
        self.provider_thread=threading.Thread(target=self.loop,args=('provider',),daemon=True,name='farmtact-provider')
        self.thread.start();self.provider_thread.start()
    def loop(self,lane='numerical'):
        """One provider lane cannot monopolize the independent local calculation lane.

        Each cycle handles at most one job per class, preventing a branch backlog
        from draining in front of every research calculation. Claims remain atomic.
        """
        while not self.stop.wait(.1):
            try:self.tick(lane)
            except Exception as exc:
                import logging
                logging.getLogger(__name__).error('Worker lane %s iteration failed (%s)',lane,type(exc).__name__)
                self.stop.wait(1)
    def tick(self,lane):
        from services.api.planning_sessions import pending as pending_planning, execute_job
        guided = pending_planning(self.store,lane)
        if guided: execute_job(self.store,*guided)
        if self.stop.is_set():return
        for tenant,id in self.store.pending(council_requested=lane=='provider'):
            record=self.store.get_run(tenant,id)
            if bool(record.get('council_requested'))!=(lane=='provider'):continue
            if self.store.claim(tenant,id):self.execute(tenant,id)
            break
        if self.stop.is_set():return
        if lane=='numerical':
            from services.api.scenarios import pending_scenarios,execute_scenario
            jobs=pending_scenarios(self.store)
            if jobs:execute_scenario(self.store,*jobs[0])
            if self.stop.is_set():return
            from services.api.council_research import pending,execute
            jobs=pending(self.store)
            if jobs:execute(self.store,*jobs[0])
        else:
            from services.api.conversation_store import ConversationStore
            from services.api.conversations import execute_conversation_job
            conversations=ConversationStore(self.store)
            for tenant,id in conversations.pending():
                if conversations.claim(tenant,id):execute_conversation_job(self.store,tenant,id)
                break
    def execute(self,tenant,id):
        store=self.store;r=store.get_run(tenant,id)
        if r.get('cancel_requested'):
            r['status']='CANCELLED';store.save_run(tenant,r);return
        r['status']='RUNNING';store.save_run(tenant,r)
        def emit(type,body):store.append_event(tenant,id,type,body)
        def cancelled():return store.get_run(tenant,id).get('cancel_requested',False)
        emit('run_started',dict(message='Freezing the synthetic farm and checking available inputs.'))
        try:
            farm=Farm.model_validate(r['input_snapshot'])
            emit('tool_started',dict(tool='forecast_and_optimize',message='Calculating crop timing, demand and resource-feasible alternatives.'))
            computed=plan(farm)
            r['strategies']=computed['strategies'];r['forecast']=computed['forecast'];r['scenario_set']=computed['scenario_set'];r['scenario_set_id']=content_hash(computed['scenario_set'])
            emit('tool_completed',dict(tool='forecast_and_optimize',candidate_count=computed['candidate_count']))
            for s in r['strategies']:emit('strategy_ready',dict(id=s['id'],name=s['name'],status=s['status']))
            claims=[];audits=[]
            reservation_day=now()[:10]
            if r['council_requested']:
                if not os.environ.get('DEEPSEEK_API_KEY'):
                    r['council_status']='blocked';r['warnings'].append('DeepSeek environment credential unavailable. Numerical baseline remains available; no agent discussion was generated.')
                elif not store.reserve_calls(COUNCIL_MAX_REQUESTS + int(bool(r.get('with_vision'))),48,reservation_day):
                    r['council_status']='blocked';r['warnings'].append('Daily development inference budget reached; no additional paid requests were made.')
                else:
                    from runtime.deepseek_gateway import RunBudget,provider_user_id_for_tenant
                    class AuditedBudget(RunBudget):
                        def reserve(self,output_tokens):
                            super().reserve(output_tokens)
                            emit('inference_request_reserved',dict(request_index=self.request_count,reserved_output_tokens=output_tokens))
                    reserved_calls=COUNCIL_MAX_REQUESTS + int(bool(r.get('with_vision')))
                    call_budget=AuditedBudget(max_requests=reserved_calls,max_reserved_output_tokens=16384,max_wall_seconds=300)
                    try:
                        from services.api.council import council
                        progress={}
                        visual=None
                        if r.get('with_vision'):
                            from services.api.vision import observe_fixture
                            emit('tool_started',dict(tool='vision_observation',role='visual_observer'))
                            visual=observe_fixture(id,budget=call_budget,provider_user_id=provider_user_id_for_tenant(tenant));r['visual_observation']=visual
                            emit('tool_completed',dict(tool='vision_observation',role='visual_observer',asset_id=visual['asset_id'],review_status=visual['review_status']))
                        claims,audits=council(computed,id,emit,cancelled,visual=visual,progress=progress,budget=call_budget,provider_user_id=provider_user_id_for_tenant(tenant),market_signals=r.get('market_signals'),news_context=r.get('news_context'),council_policy=r.get('council_policy','required'))
                        r['council_status']='completed' if not council_review_issues(claims) else 'claims_rejected'
                    except Exception as exc:
                        # No raw provider/transport message or request may enter public records.
                        claims=progress.get('claims',[]) if 'progress' in locals() else [];audits=progress.get('audits',[]) if 'progress' in locals() else []
                        from runtime.deepseek_gateway import DeepSeekGatewayError
                        detail=str(exc) if isinstance(exc,DeepSeekGatewayError) else type(exc).__name__
                        r['council_status']='failed';r['warnings'].append(f'DeepSeek council incomplete ({detail}); deterministic validation is available. No provider fallback was used.')
                        emit('input_warning',dict(message=r['warnings'][-1]))
                    finally:
                        unused=reserved_calls-call_budget.request_count
                        store.release_unused_calls(unused,reservation_day)
                        r['inference_budget']=dict(reserved_calls=reserved_calls,requests_consumed=call_budget.request_count,unused_released=unused,reserved_output_tokens=call_budget.reserved_output_tokens)
            else:r['council_status']='not_run'
            r['claims']=claims;r['inference_audit']=audits
            dimensions=council_statuses(claims)
            r.update(council_execution_status=dimensions['execution_status'] if claims else r['council_status'],council_evidence_status=dimensions['evidence_status'],council_decision_influence=dimensions['decision_influence'])
            if cancelled():r['status']='CANCELLED';store.save_run(tenant,r);emit('run_failed',dict(message='Mission cancelled; no plan accepted.'));return
            with store.transaction(tenant):
                current=store.latest_farm(tenant)
                if current['version']!=r['input_version'] or content_hash(current)!=r['input_hash']:
                    r['status']='STALE_INPUT';r['warnings'].append('Farm changed during calculation. Acceptance invalidated; numerical validation automatically restarts on the current version.')
                    store.save_run(tenant,r)
                    refreshed=create_mission(store,tenant,MissionRequest(council=False),f'refresh:{id}:{current["version"]}',parent=id)
                    r['superseded_by']=refreshed['id']
                    emit('input_refreshed',dict(next_run_id=refreshed['id'],execution_mode='test',council_status='not_run'))
                else:
                    eligible=[s for s in r['strategies'] if s['status']=='FEASIBLE' and not validate_allocations(farm,s['allocations'])]
                    ranked=sorted(eligible,key=lambda candidate:(candidate['name']!='Balanced',-float(candidate['metrics'].get('fill_rate',0)),-float(candidate['metrics'].get('margin_sgd',0)),candidate['id']))
                    chosen=ranked[0] if ranked else None
                    r['selection_ranking']=dict(policy='balanced-service-margin-id-v1',strategy_ids=[candidate['id'] for candidate in ranked])
                    review_issues=council_review_issues(claims) if claims else []
                    if r.get('council_policy')=='required' and r['council_status']!='completed':
                        review_issues.append('Required Council did not complete with supported findings; automatic selection is withheld.')
                    gate_issues=review_issues if r.get('council_policy')!='advisory' else []
                    r['evidence_validation']=dict(version='council-evidence-gate-v2',status='withheld' if gate_issues else ('advisory_issues' if review_issues else 'passed'),basis='seven-agent-findings' if claims else 'numerical-baseline',issues=review_issues,qualitative_prose_verified=False)
                    if review_issues:r['warnings'].extend(review_issues)
                    if gate_issues:
                        chosen=None
                    if chosen:
                        emit('acceptance_validating',dict(strategy_id=chosen['id']))
                        r['accepted_strategy_id']=chosen['id'];r['status']='ACCEPTED_FOR_SIMULATION'
                        r['acceptance']=dict(actor='development-policy-service',policy_version='automatic-development-v3',council_policy=r.get('council_policy','legacy_advisory'),input_hash=r['input_hash'],input_version=r['input_version'],strategy_id=chosen['id'],strategy_hash=content_hash(chosen),validation_report_id=content_hash(chosen['violations']),occurred_at=now(),simulation_only=True)
                        r['simulated_outcome']=dict(origin='synthetic',scenario_seed=farm.fixture_seed,ledger=chosen['ledger'],metrics=chosen['metrics'],work=[a for a in chosen['allocations'] if not a.get('executed')])
                        emit('accepted_for_simulation',r['acceptance'])
                    else:r['status']='REVIEW_WITHHELD' if eligible and gate_issues else 'NO_FEASIBLE_PLAN'
                r['completed_at']=now();r['events']=store.get_events(tenant,id)
                store.save_run(tenant,r);emit('run_completed',dict(status=r['status'],council_status=r['council_status']))
        except Exception as exc:
            r['status']='FAILED';r['warnings'].append(f'Planning failed ({type(exc).__name__}); no plan was accepted.')
            store.save_run(tenant,r);emit('run_failed',dict(message=r['warnings'][-1]))

def create_app(store=None,start_worker=True):
    @asynccontextmanager
    async def lifespan(app):
        app.state.store=store or Store();app.state.worker=Worker(app.state.store)
        from services.api.security import AbuseLimits
        app.state.abuse_limits=AbuseLimits(app.state.store)
        if start_worker:app.state.worker.start()
        yield
        app.state.worker.stop.set()
    app=FastAPI(title='FarmTact',version='0.1.0',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
    @app.middleware('http')
    async def boundaries(request,call_next):
        # Only the next unpublished edition is addressable in an unsealed local checkout.
        if not os.environ.get('FARMTACT_EDITION'):
            from services.api.release_registry import registry
            next_edition = 'v'+str(max(int(e['id'][1:]) for e in registry()['editions'])+1)
            prefix='/'+next_edition
            path=request.scope['path']
            if path==prefix or path.startswith(prefix+'/'):
                request.scope['path']=path[len(prefix):] or '/'
                request.scope['raw_path']=request.scope['path'].encode()
        if request.method not in ('GET','HEAD','OPTIONS'):
            origin=request.headers.get('origin')
            if origin:
                from urllib.parse import urlsplit
                if urlsplit(origin).netloc!=request.headers.get('host'):return JSONResponse({'detail':'Cross-origin write rejected'},403)
            try:declared=int(request.headers.get('content-length','0') or '0')
            except ValueError:return JSONResponse({'detail':'Invalid Content-Length'},400)
            if declared<0:return JSONResponse({'detail':'Invalid Content-Length'},400)
            if declared>1048576:return JSONResponse({'detail':'Upload exceeds 1 MiB'},413)
            # Enforce the cap while consuming a chunked upload, before allocation/parsing.
            chunks=[];received=0
            try:
                async with asyncio.timeout(15):
                    async for chunk in request.stream():
                        received+=len(chunk)
                        if received>1048576:return JSONResponse({'detail':'Upload exceeds 1 MiB'},413)
                        chunks.append(chunk)
            except TimeoutError:return JSONResponse({'detail':'Request body timed out'},408)
            request._body=b''.join(chunks)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        response.headers['Cache-Control']='no-store' if request.url.path.startswith('/api') else 'public, max-age=60'
        return response
    from services.api.security import AbuseMiddleware
    app.add_middleware(AbuseMiddleware)
    from services.api.edition_ingress import EditionIngress
    app.add_middleware(EditionIngress)
    @app.exception_handler(RequestValidationError)
    async def invalid(request,exc):return JSONResponse({'detail':'Invalid request schema','errors':[{'loc':e['loc'],'type':e['type']} for e in exc.errors()]},422)
    def tenant(request):
        t=app.state.store.authenticate(request.cookies.get('farmtact_session'))
        if not t:raise HTTPException(401,'Development session required')
        return t
    def getrun(request,id):
        t=tenant(request);r=app.state.store.get_run(t,id)
        if not r:raise HTTPException(404,'Mission not found')
        return t,r
    def public_run(t,r):
        result={k:v for k,v in r.items() if k not in ('input_snapshot','request_hash')};result['events']=app.state.store.get_events(t,r['id'])
        current=app.state.store.latest_farm(t)
        if current and current['version']!=r['input_version']:
            result['acceptance_stale']=True
        return result
    @app.get('/api/v1/health')
    def health():
        result = {'status':'ok','development_phase':'autonomous_development'}
        if os.environ.get('FARMTACT_EDITION'):
            source = ROOT/'config/build-source.txt'
            result.update(edition=os.environ['FARMTACT_EDITION'],source_commit=source.read_text().strip() if source.is_file() else 'development')
        return result
    @app.get('/api/v1/bootstrap')
    def bootstrap(request:Request,response:Response):
        t=app.state.store.authenticate(request.cookies.get('farmtact_session'))
        if not t:
            t,token=app.state.store.new_session();response.set_cookie('farmtact_session',token,httponly=True,samesite='strict',secure=request.url.scheme=='https' or os.environ.get('FARMTACT_SECURE_COOKIES')=='true',max_age=86400)
            app.state.store.save_farm(t,synthetic_farm().model_dump(mode='json'))
        farm=Farm.model_validate(app.state.store.latest_farm(t));r=app.state.store.latest_run(t)
        return dict(farm=farm_view(farm),crops=crop_views(farm),sources=source_views(),capabilities=capabilities(app.state.store,t),latest_run=public_run(t,r) if r else None)
    @app.get('/api/v1/demo/replay')
    def recorded_demo(request:Request):
        tenant(request)
        file=ROOT/'data/fixtures/deepseek_demo_replay.json'
        if not file.exists():raise HTTPException(404,'No verified demo recording available')
        replay=json.loads(file.read_text())
        if replay.get('data_mode')!='synthetic_demo' or replay.get('execution_mode')!='replay':raise HTTPException(409,'Demo recording has invalid provenance')
        return replay
    @app.get('/api/v1/crops')
    def crops(request:Request):return crop_views(Farm.model_validate(app.state.store.latest_farm(tenant(request))))
    @app.get('/api/v1/crops/{id}/evidence')
    def evidence(id:str,request:Request):
        t=tenant(request);profiles=crop_views(Farm.model_validate(app.state.store.latest_farm(t)));c=next((c for c in profiles if c['id']==id),None)
        if not c:raise HTTPException(404,'Crop not found')
        file=ROOT/'research/evidence_register.json';registry=json.loads(file.read_text()) if file.exists() else {}
        records=registry.get('documents',registry.get('records',registry.get('publications',[]))) if isinstance(registry,dict) else registry
        return {'crop':c,'evidence':[e for e in records if e.get('evidence_id',e.get('id')) in c['evidence_ids']]}
    @app.get('/api/v1/sources')
    def sources(request:Request):tenant(request);return source_views()
    @app.get('/api/v1/farms/{id}/snapshot')
    def snapshot(id:str,request:Request):
        t=tenant(request)
        if id!='demo-farm':raise HTTPException(404,'Farm not found')
        return app.state.store.latest_farm(t)
    @app.post('/api/v1/imports',status_code=201)
    def imports(body:ImportRequest,request:Request):
        t=tenant(request)
        if bool(body.fixture)==bool(body.farm):raise HTTPException(422,'Supply one fixture or farm')
        key=request.headers.get('Idempotency-Key','')
        if not key or len(key)>128:raise HTTPException(422,'Idempotency-Key required, maximum 128 characters')
        from services.api.store import mutation_receipts
        from sqlalchemy import select
        digest=content_hash(dict(operation='farm_import',body=body.model_dump(mode='json')))
        farm=body.farm or synthetic_farm()
        with app.state.store.transaction(t) as c:
            old=c.execute(select(mutation_receipts).where(mutation_receipts.c.tenant_id==t,mutation_receipts.c.idempotency_key==key)).mappings().first()
            if old:
                if old['request_hash']!=digest:raise HTTPException(409,'Idempotency key reused with changed import inputs')
                return old['payload']
            previous=app.state.store.latest_run(t)
            payload=app.state.store.save_farm(t,farm.model_dump(mode='json'))
            refresh=None
            if previous and previous['status'] not in ('CREATED','RUNNING'):
                refresh=create_mission(app.state.store,t,MissionRequest(council=False),f'import:{payload["version"]}',parent=previous['id'])
            result=dict(id=content_hash(payload)[:20],status='validated',version=payload['version'],planning_run=refresh,rows=dict(beds=len(farm.beds),orders=len(farm.orders),batches=len(farm.batches)),origin='synthetic')
            c.execute(mutation_receipts.insert().values(tenant_id=t,idempotency_key=key,request_hash=digest,payload=result))
        return result
    @app.post('/api/v1/planning-runs',status_code=202)
    def mission(body:MissionRequest,request:Request):return create_mission(app.state.store,tenant(request),body,request.headers.get('Idempotency-Key'))
    @app.get('/api/v1/planning-runs/{id}')
    def run(id:str,request:Request):
        t,r=getrun(request,id);return public_run(t,r)
    @app.get('/api/v1/planning-runs/{id}/events')
    async def stream(id:str,request:Request):
        t,r=getrun(request,id)
        try:after=max(0,int(request.headers.get('last-event-id',request.query_params.get('after','0'))))
        except ValueError:raise HTTPException(422,'Invalid event cursor')
        async def generate():
            nonlocal after
            while not await request.is_disconnected():
                rows=app.state.store.get_events(t,id,after)
                for e in rows:
                    after=e['sequence'];yield f"id: {after}\ndata: {json.dumps(e)}\n\n"
                r=app.state.store.get_run(t,id)
                if r['status'] not in ('CREATED','RUNNING'):break
                if not rows:yield ': keep-alive\n\n'
                await asyncio.sleep(.5)
        return StreamingResponse(generate(),media_type='text/event-stream')
    @app.post('/api/v1/planning-runs/{id}/cancel')
    def cancel(id:str,request:Request):
        t,r=getrun(request,id)
        if r['status'] not in ('CREATED','RUNNING'):return dict(status=r['status'],cancelled=False,reason='already_terminal')
        r['cancel_requested']=True;app.state.store.save_run(t,r)
        return dict(status='cancel_requested',cancelled=False)
    @app.get('/api/v1/planning-runs/{id}/replay')
    def replay(id:str,request:Request):
        t,r=getrun(request,id)
        if r['status'] in ('CREATED','RUNNING'):raise HTTPException(409,'Mission still running')
        return dict(public_run(t,r),execution_mode='replay',original_execution_mode=r['execution_mode'],inference_origin='stored_events',replay_of=id)
    @app.post('/api/v1/planning-runs/{id}/replan',status_code=202)
    def replan(id:str,body:ReplanRequest,request:Request):
        t,r=getrun(request,id)
        key=request.headers.get('Idempotency-Key')
        if not key or len(key)>128:raise HTTPException(422,'Idempotency-Key required, maximum 128 characters')
        from services.api.store import runs
        from sqlalchemy import select
        with app.state.store.engine.connect() as c:
            old=c.execute(select(runs.c.payload).where(runs.c.tenant_id==t,runs.c.idempotency_key==key)).scalar_one_or_none()
        if old:
            if old.get('parent_run_id')!=id or old.get('replan_request')!=body.model_dump():raise HTTPException(409,'Idempotency key belongs to different replan inputs')
            return dict(id=old['id'],status=old['status'],reused=True)
        if r['status']!='ACCEPTED_FOR_SIMULATION':raise HTTPException(409,'An accepted simulation is required')
        with app.state.store.transaction(t) as connection:
            old=connection.execute(select(runs.c.payload).where(runs.c.tenant_id==t,runs.c.idempotency_key==key)).scalar_one_or_none()
            if old:
                if old.get('parent_run_id')!=id or old.get('replan_request')!=body.model_dump():raise HTTPException(409,'Idempotency key belongs to different replan inputs')
                return dict(id=old['id'],status=old['status'],reused=True)
            current=app.state.store.latest_farm(t)
            if current['version']!=r['input_version'] or (body.input_version is not None and body.input_version!=current['version']):raise HTTPException(409,'Parent mission is stale')
            farm=Farm.model_validate(current)
            # This is a synthetic observation update, not changing executed sow/transplant work.
            b=next((batch for batch in farm.batches if batch.id==body.batch_id),None) if body.batch_id else next(iter(farm.batches),None)
            if b is None:raise HTTPException(422,'Select an existing batch for the disruption')
            b.harvest_date+=timedelta(days=body.delay_days);b.expected_marketable_kg*=__import__('decimal').Decimal(body.yield_percent)/100
            app.state.store.save_farm(t,farm.model_dump(mode='json'))
            return create_mission(app.state.store,t,MissionRequest(council=r['council_requested'] if body.council is None else body.council,council_policy=r.get('council_policy','required') if r.get('council_policy') in ('required','advisory') else 'required'),request.headers.get('Idempotency-Key'),parent=id,disruption=dict(type='crop_delay',origin='synthetic',batch_id=b.id,delay_days=body.delay_days,yield_factor=body.yield_percent/100,observed_at=now()),replan_request=body.model_dump())
    @app.post('/api/v1/strategies/{id}/accept-for-simulation')
    def service_only(id:str,request:Request):tenant(request);raise HTTPException(403,'Acceptance is a backend policy operation')
    @app.get('/api/v1/planning-runs/{id}/worklist.csv')
    def worklist(id:str,request:Request):
        t,r=getrun(request,id)
        chosen=next((s for s in r['strategies'] if s['id']==r.get('accepted_strategy_id')),None)
        if not chosen:raise HTTPException(409,'No accepted simulation worklist')
        current=app.state.store.latest_farm(t)
        if current['version']!=r['input_version']:raise HTTPException(409,'Worklist acceptance is stale')
        import csv,io
        out=io.StringIO();writer=csv.writer(out)
        writer.writerow(['mode','input_version','strategy','bed','crop','sow_date','transplant_date','harvest_date','area_m2','marketable_kg','executed_at_cutoff'])
        def cell(v):
            text=str(v)
            return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r')) else text
        for a in chosen['allocations']:
            writer.writerow([cell(v) for v in ['SIMULATION_ONLY',r['input_version'],chosen['name'],a['bed_id'],a['crop_id'],a['sow_date'],a['transplant_date'],a['harvest_date'],a['area_m2'],a['expected_kg'],a['executed']]])
        return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="farmtact-simulation-worklist.csv"'})
    @app.get('/api/v1/reports/{id}')
    def report(id:str,request:Request):
        t,r=getrun(request,id);return public_run(t,r)
    @app.get('/api/v1/strategies/{id}')
    def strategy(id:str,request:Request):
        t=tenant(request)
        from services.api.store import runs
        from sqlalchemy import select
        with app.state.store.engine.connect() as c:
            allruns=c.execute(select(runs.c.payload).where(runs.c.tenant_id==t)).scalars().all()
        for r in allruns:
            for s in r['strategies']:
                if s['id']==id:return s
        raise HTTPException(404,'Strategy not found')
    from services.api.market_signals import install_routes as install_market_signals
    install_market_signals(app,tenant)
    from services.api.news import install_routes as install_news
    install_news(app,tenant)
    from services.api.data_explorer import install_routes as install_explorer
    install_explorer(app,tenant)
    from services.api.scenarios import install_routes
    install_routes(app,tenant)
    from services.api.conversations import install_routes as install_conversations
    install_conversations(app,tenant)
    from services.api.council_research import install_routes as install_research
    install_research(app,tenant)
    from services.api.planning_sessions import register as install_planning
    install_planning(app,tenant)
    from services.api.simulation import register as install_simulations
    install_simulations(app,tenant)
    from services.api.reviews import install_routes as install_reviews
    install_reviews(app)
    dist=ROOT/'apps/web/dist'
    if dist.exists():
        app.mount('/assets',StaticFiles(directory=dist/'assets'),name='assets')
        if (dist/'art').exists():app.mount('/art',StaticFiles(directory=dist/'art'),name='art')
        if (dist/'review-evidence').exists():app.mount('/review-evidence',StaticFiles(directory=dist/'review-evidence'),name='review-evidence')
        if (dist/'research-evidence').exists():app.mount('/research-evidence',StaticFiles(directory=dist/'research-evidence'),name='research-evidence')
        if (dist/'audio').exists():app.mount('/audio',StaticFiles(directory=dist/'audio'),name='audio')
        @app.get('/research/')
        def research_canonical():return RedirectResponse('/research',status_code=307)
        @app.get('/research')
        @app.get('/changes')
        @app.get('/changes/')
        @app.get('/review')
        @app.get('/review/')
        @app.get('/')
        def index():return FileResponse(dist/'index.html')
    return app

app=create_app()
