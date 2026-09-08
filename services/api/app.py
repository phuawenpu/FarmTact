from __future__ import annotations
import asyncio,json,os,secrets,threading,time
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Literal
from fastapi import FastAPI,Request,HTTPException,Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse,StreamingResponse,FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import Field
from packages.contracts import Farm,Strict,content_hash
from packages.fixtures import synthetic_farm
from packages.planner import plan,validate_allocations
from services.api.store import Store,now
from services.api.views import ROOT,farm_view,crop_views,source_views,capabilities

class MissionRequest(Strict):
    council: bool = True
    with_vision: bool = False
class ReplanRequest(Strict):
    council: bool | None = None
    disruption: Literal['crop_delay'] = 'crop_delay'
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
    try:result,created=store.create_run(t,key,fingerprint,r)
    except ValueError as e:raise HTTPException(409,str(e))
    return dict(id=result['id'],status=result['status'],reused=not created)

class Worker:
    def __init__(self,store):self.store=store;self.stop=threading.Event();self.thread=None
    def start(self):
        self.store.interrupt_abandoned()
        self.thread=threading.Thread(target=self.loop,daemon=True);self.thread.start()
    def loop(self):
        while not self.stop.wait(.3):
            for tenant,id in self.store.pending():
                if self.store.claim(tenant,id):self.execute(tenant,id)
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
            if r['council_requested']:
                if not os.environ.get('DEEPSEEK_API_KEY'):
                    r['council_status']='blocked';r['warnings'].append('DeepSeek environment credential unavailable. Numerical baseline remains available; no agent discussion was generated.')
                elif not store.reserve_calls(9 if r.get('with_vision') else 8):
                    r['council_status']='blocked';r['warnings'].append('Daily development inference budget reached; no additional paid requests were made.')
                else:
                    from runtime.deepseek_gateway import RunBudget
                    class AuditedBudget(RunBudget):
                        def reserve(self,output_tokens):
                            super().reserve(output_tokens)
                            emit('inference_request_reserved',dict(request_index=self.request_count,reserved_output_tokens=output_tokens))
                    reserved_calls=9 if r.get('with_vision') else 8
                    call_budget=AuditedBudget(max_requests=reserved_calls,max_reserved_output_tokens=16384,max_wall_seconds=300)
                    try:
                        from services.api.council import council
                        progress={}
                        visual=None
                        if r.get('with_vision'):
                            from services.api.vision import observe_fixture
                            emit('tool_started',dict(tool='vision_observation',role='visual_observer'))
                            visual=observe_fixture(id,budget=call_budget);r['visual_observation']=visual
                            emit('tool_completed',dict(tool='vision_observation',role='visual_observer',asset_id=visual['asset_id'],review_status=visual['review_status']))
                        claims,audits=council(computed,id,emit,cancelled,visual=visual,progress=progress,budget=call_budget)
                        r['council_status']='completed' if all(c['status']=='validated' for c in claims) else 'claims_rejected'
                    except Exception as exc:
                        # No raw provider/transport message or request may enter public records.
                        claims=progress.get('claims',[]) if 'progress' in locals() else [];audits=progress.get('audits',[]) if 'progress' in locals() else []
                        from runtime.deepseek_gateway import DeepSeekGatewayError
                        detail=str(exc) if isinstance(exc,DeepSeekGatewayError) else type(exc).__name__
                        r['council_status']='failed';r['warnings'].append(f'DeepSeek council incomplete ({detail}); deterministic validation is available. No provider fallback was used.')
                        emit('input_warning',dict(message=r['warnings'][-1]))
                    finally:
                        unused=reserved_calls-call_budget.request_count
                        store.release_unused_calls(unused)
                        r['inference_budget']=dict(reserved_calls=reserved_calls,requests_consumed=call_budget.request_count,unused_released=unused,reserved_output_tokens=call_budget.reserved_output_tokens)
            else:r['council_status']='not_run'
            r['claims']=claims;r['inference_audit']=audits
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
                    chosen=next((s for s in eligible if s['name']=='Balanced'),eligible[0] if eligible else None)
                    critic=next((c for c in claims if c['role']=='independent_critic'),None)
                    if critic and (critic['status']!='validated' or critic['recommendation']!='proceed_simulation'):
                        chosen=None;r['warnings'].append('Independent critic did not clear the plan. Evidence remains available; acceptance withheld.')
                    if chosen:
                        emit('acceptance_validating',dict(strategy_id=chosen['id']))
                        r['accepted_strategy_id']=chosen['id'];r['status']='ACCEPTED_FOR_SIMULATION'
                        r['acceptance']=dict(actor='development-policy-service',policy_version='automatic-development-v1',input_hash=r['input_hash'],input_version=r['input_version'],strategy_id=chosen['id'],strategy_hash=content_hash(chosen),validation_report_id=content_hash(chosen['violations']),occurred_at=now(),simulation_only=True)
                        r['simulated_outcome']=dict(origin='synthetic',scenario_seed=farm.fixture_seed,ledger=chosen['ledger'],metrics=chosen['metrics'],work=[a for a in chosen['allocations'] if not a.get('executed')])
                        emit('accepted_for_simulation',r['acceptance'])
                    else:r['status']='NO_FEASIBLE_PLAN'
                r['completed_at']=now();r['events']=store.get_events(tenant,id)
                store.save_run(tenant,r);emit('run_completed',dict(status=r['status'],council_status=r['council_status']))
        except Exception as exc:
            r['status']='FAILED';r['warnings'].append(f'Planning failed ({type(exc).__name__}); no plan was accepted.')
            store.save_run(tenant,r);emit('run_failed',dict(message=r['warnings'][-1]))

def create_app(store=None,start_worker=True):
    @asynccontextmanager
    async def lifespan(app):
        app.state.store=store or Store();app.state.worker=Worker(app.state.store)
        if start_worker:app.state.worker.start()
        yield
        app.state.worker.stop.set()
    app=FastAPI(title='FarmTact',version='0.1.0',lifespan=lifespan,docs_url=None,redoc_url=None)
    @app.middleware('http')
    async def boundaries(request,call_next):
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
            async for chunk in request.stream():
                received+=len(chunk)
                if received>1048576:return JSONResponse({'detail':'Upload exceeds 1 MiB'},413)
                chunks.append(chunk)
            request._body=b''.join(chunks)
        response=await call_next(request)
        response.headers['X-Content-Type-Options']='nosniff'
        response.headers['Referrer-Policy']='same-origin'
        response.headers['Content-Security-Policy']="default-src 'self'; img-src 'self' data:; style-src 'self' 'unsafe-inline'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'; base-uri 'self'"
        response.headers['Cache-Control']='no-store' if request.url.path.startswith('/api') else 'public, max-age=60'
        return response
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
    def health():return {'status':'ok','development_phase':'autonomous_development'}
    @app.get('/api/v1/bootstrap')
    def bootstrap(request:Request,response:Response):
        t=app.state.store.authenticate(request.cookies.get('farmtact_session'))
        if not t:
            t,token=app.state.store.new_session();response.set_cookie('farmtact_session',token,httponly=True,samesite='strict',secure=request.url.scheme=='https' or os.environ.get('FARMTACT_SECURE_COOKIES')=='true',max_age=86400)
            app.state.store.save_farm(t,synthetic_farm().model_dump(mode='json'))
        farm=Farm.model_validate(app.state.store.latest_farm(t));r=app.state.store.latest_run(t)
        return dict(farm=farm_view(farm),crops=crop_views(farm),sources=source_views(),capabilities=capabilities(),latest_run=public_run(t,r) if r else None)
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
        farm=body.farm or synthetic_farm()
        with app.state.store.transaction(t):
            previous=app.state.store.latest_run(t)
            payload=app.state.store.save_farm(t,farm.model_dump(mode='json'))
            refresh=None
            if previous and previous['status'] not in ('CREATED','RUNNING'):
                refresh=create_mission(app.state.store,t,MissionRequest(council=False),f'import:{payload["version"]}',parent=previous['id'])
        return dict(id=content_hash(payload)[:20],status='validated',version=payload['version'],planning_run=refresh,rows=dict(beds=len(farm.beds),orders=len(farm.orders),batches=len(farm.batches)),origin='synthetic')
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
        if r['status'] in ('CREATED','RUNNING'):r['cancel_requested']=True;app.state.store.save_run(t,r)
        return {'status':'cancel_requested'}
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
            if current['version']!=r['input_version']:raise HTTPException(409,'Parent mission is stale')
            farm=Farm.model_validate(current)
            # This is a synthetic observation update, not changing executed sow/transplant work.
            b=farm.batches[0]; b.harvest_date+=timedelta(days=7);b.expected_marketable_kg*=__import__('decimal').Decimal('.8')
            app.state.store.save_farm(t,farm.model_dump(mode='json'))
            return create_mission(app.state.store,t,MissionRequest(council=r['council_requested'] if body.council is None else body.council),request.headers.get('Idempotency-Key'),parent=id,disruption=dict(type='crop_delay',origin='synthetic',batch_id=b.id,delay_days=7,yield_factor=.8,observed_at=now()),replan_request=body.model_dump())
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
    dist=ROOT/'apps/web/dist'
    if dist.exists():
        app.mount('/assets',StaticFiles(directory=dist/'assets'),name='assets')
        @app.get('/')
        def index():return FileResponse(dist/'index.html')
    return app

app=create_app()
