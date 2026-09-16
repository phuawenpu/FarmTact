"""Guided production decisions: durable references, bounded jobs, isolated worlds."""
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from decimal import Decimal
import os
import secrets
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, JSON, String, Table, UniqueConstraint, select, update, func
from packages.contracts import Farm, InventoryLot, content_hash
from packages.planning_contracts import CreatePlanningSession, PlanningRevision, PlanningDisruption, PlanningAdvance
from services.api.store import metadata, now
from services.api.numerical_worker import calculate

VERSION='guided-planning-v1'
# This workflow admits no external observations: four specialists plus Chair,
# with two possible repairs. The runtime absolute ceiling remains nine.
REVIEW_RESERVATION=7
SESSIONS=Table('guided_planning_sessions',metadata,
    Column('id',String,primary_key=True),Column('tenant_id',String,ForeignKey('tenants.id'),nullable=False),
    Column('status',String,nullable=False),Column('payload',JSON,nullable=False),UniqueConstraint('id','tenant_id'))
JOBS=Table('guided_planning_jobs',metadata,
    Column('id',String,primary_key=True),Column('tenant_id',String,ForeignKey('tenants.id'),nullable=False),
    Column('session_id',String,nullable=False),Column('status',String,nullable=False),Column('kind',String,nullable=False),
    Column('created_at',String,nullable=False),Column('payload',JSON,nullable=False),
    ForeignKeyConstraint(['session_id','tenant_id'],['guided_planning_sessions.id','guided_planning_sessions.tenant_id']))
VERSIONS=Table('guided_planning_versions',metadata,
    Column('id',String,primary_key=True),Column('tenant_id',String,ForeignKey('tenants.id'),nullable=False),
    Column('session_id',String,nullable=False),Column('payload',JSON,nullable=False),
    ForeignKeyConstraint(['session_id','tenant_id'],['guided_planning_sessions.id','guided_planning_sessions.tenant_id']))
RECEIPTS=Table('guided_planning_receipts',metadata,
    Column('tenant_id',String,ForeignKey('tenants.id'),primary_key=True),Column('key',String,primary_key=True),
    Column('request_hash',String,nullable=False),Column('payload',JSON,nullable=False))


def get_session(store, tenant, id):
    with store.connection() as c:
        return c.execute(select(SESSIONS.c.payload).where(SESSIONS.c.tenant_id==tenant,SESSIONS.c.id==id)).scalar_one_or_none()


def get_result(store, tenant, id):
    if not id:return None
    with store.connection() as c:
        return c.execute(select(VERSIONS.c.payload).where(VERSIONS.c.tenant_id==tenant,VERSIONS.c.id==id)).scalar_one_or_none()


def save_session(store,tenant,session):
    session['updated_at']=now()
    with store.connection(write=True) as c:
        c.execute(update(SESSIONS).where(SESSIONS.c.id==session['id'],SESSIONS.c.tenant_id==tenant).values(status=session['status'],payload=session))


def public_result(result):
    if result is None:return None
    value={k:deepcopy(v) for k,v in result.items() if not k.startswith('_') and k!='input_snapshot'}
    # Large accounting traces remain durable and are used for execution; the
    # planning screen receives the corresponding metrics and order attribution.
    for strategy in [*value.get('strategies',[]),value.get('retained_strategy')]:
        if strategy:
            for key in ('ledger','inventory_snapshots'):
                strategy.pop(key,None)
    return value


def public_session(store,tenant,session):
    from services.api.simulation import get_world,public_world
    value={k:deepcopy(v) for k,v in session.items() if not k.startswith('_')}
    value['workflow']=session.get('workflow_version')=='farmer-workflow-v1'
    value['result']=public_result(get_result(store,tenant,session.get('result_id')))
    value['farm']['planning_date']=str(Farm.model_validate(session['farm']).planning_date)
    world=get_world(store,tenant,session['world_id']) if session.get('world_id') else None
    value['simulation']=public_world(world) if world else None
    return value


def _remaining_input(store,tenant,session):
    from services.api.simulation import get_world
    result=get_result(store,tenant,session.get('result_id'))
    selected=next((s for s in (result or {}).get('strategies',[]) if s['id']==session.get('selected_strategy_id')),None)
    if selected is None:raise HTTPException(409,'Calculate a feasible saved schedule first')
    snapshot=deepcopy(session['farm']); kwargs={'retained_strategy':deepcopy(selected)}
    if session.get('world_id'):
        world=get_world(store,tenant,session['world_id'])
        if world['clock_date']:
            start=date.fromisoformat(world['clock_date'])+timedelta(days=1)
            remaining=(date.fromisoformat(world['end_date'])-start).days+1
            if remaining<7:raise HTTPException(409,'At least seven unexecuted days are required to replan')
            if len(world['plan_history'])>=12:raise HTTPException(429,'Twelve replans per world maximum')
            farm=Farm.model_validate(world['segment_farm']).model_copy(deep=True)
            recipes={r.id:r for r in farm.recipes}
            active=[dict(deepcopy(a), **({'harvest_recorded':True} if f"{a['id']}:harvest" in world['completed_task_ids'] else {})) for a in world['segment_allocations'] if date.fromisoformat(a['harvest_date'])+timedelta(days=recipes[a['recipe_id']].sanitation_days)>=start]
            locks=[dict(a,executed=True) for a in active if f"{a['id']}:sow" in world['completed_task_ids']]
            farm.cutoff=datetime.combine(start,time.min,ZoneInfo(farm.timezone));farm.horizon_days=remaining;farm.batches=[]
            farm.inventory=[InventoryLot.model_validate(lot) for lot in world['inventory']]
            farm.orders=[o for o in farm.orders if o.due_date>=start]
            if world['cash_sgd']<0:raise HTTPException(409,'Recorded cash is negative; a liquidity model is required before replanning')
            farm.resources.cash_sgd=Decimal(str(world['cash_sgd']))
            snapshot=Farm.model_validate(farm.model_dump(mode='json')).model_dump(mode='json')
            kwargs.update(locked_allocations=locks,candidate_not_before=str(start),excluded_candidate_ids=sorted({task.rsplit(':',1)[0] for task in world['completed_task_ids']}))
            locked_ids={a['id'] for a in locks}
            kwargs['retained_strategy']['allocations']=[dict(a,executed=True) if a['id'] in locked_ids else a for a in active]
    return snapshot,kwargs


def _create_world(store,tenant,session,result):
    from services.api.simulation import WORLDS,VERSION as ENGINE,append_event
    chosen=next(s for s in result['strategies'] if s['id']==session['selected_strategy_id'])
    farm=Farm.model_validate(session['farm'])
    if any(b.harvest_date<farm.planning_date for b in farm.batches):raise HTTPException(409,'Resolve overdue harvest records before simulation')
    with store.connection() as c:
        if c.execute(select(func.count()).select_from(WORLDS).where(WORLDS.c.tenant_id==tenant)).scalar_one()>=8:
            raise HTTPException(429,'Eight simulation worlds per tenant maximum')
    world=dict(id=secrets.token_hex(16),engine_version=ENGINE,revision=0,status='ACTIVE',run_id='planning-session:'+session['id'],
        created_at=now(),updated_at=now(),clock_date=None,start_date=str(farm.planning_date),end_date=str(farm.planning_date+timedelta(days=farm.horizon_days-1)),
        days_executed=0,segment_days_executed=0,input_hash=session['input_hash'],input_version=farm.version,
        segment_farm=farm.model_dump(mode='json'),segment_allocations=deepcopy(chosen['allocations']),trace=deepcopy(session.get('_approved_execution_trace',result['_execution_trace'])),
        scenario=dict(id='execution-central',yield_factor=1.,demand_factor=1.,weight=1.),strategy_id=chosen['id'],strategy_name=chosen['name'],
        plan_history=[],completed_task_ids=[],harvest_lot_origins={},event_sequence=0,
        inventory=[l.model_dump(mode='json') for l in farm.inventory if l.harvested_date<=farm.planning_date],
        opening_cash_sgd=str(farm.resources.cash_sgd),cash_sgd=float(farm.resources.cash_sgd),revenue_exact_sgd='0',cost_exact_sgd='0',revenue_sgd=0,cost_sgd=0,
        totals=dict(harvest_kg=0,delivered_kg=0,disposed_kg=0,demand_kg=0),outcome_basis='deterministic_synthetic_schedule_and_scenario',real_operations_enabled=False)
    for allocation in chosen['allocations']:
        for task,field in (('sow','sow_date'),('transplant','transplant_date'),('harvest','harvest_date')):
            if allocation.get('executed') and allocation[field]<world['start_date']:world['completed_task_ids'].append(f"{allocation['id']}:{task}")
    with store.connection(write=True) as c:c.execute(WORLDS.insert().values(id=world['id'],tenant_id=tenant,payload=world))
    append_event(store,tenant,world,'world_created',world['start_date'],planning_session_id=session['id'],strategy_hash=content_hash(chosen),inherited_task_ids=world['completed_task_ids'])
    session['world_id']=world['id']
    return world


def _apply_world_replan(store,tenant,session,result):
    from services.api.simulation import WORLDS,get_world,append_event
    world=get_world(store,tenant,session['world_id'])
    chosen=next((s for s in result['strategies'] if s['id']==session['selected_strategy_id']),None)
    if not chosen:return
    world['plan_history'].append(dict(revision=world['revision'],strategy_id=world['strategy_id'],input_hash=content_hash(world['segment_farm']),allocations_hash=content_hash(world['segment_allocations']),through_date=world['clock_date']))
    world.update(segment_farm=deepcopy(session['farm']),segment_allocations=deepcopy(chosen['allocations']),trace=deepcopy(session.get('_approved_execution_trace',result['_execution_trace'])),segment_days_executed=0,
        strategy_id=chosen['id'],strategy_name=chosen['name'],revision=world['revision']+1,updated_at=now())
    append_event(store,tenant,world,'future_replanned',str(Farm.model_validate(session['farm']).planning_date),planning_session_id=session['id'],strategy_hash=content_hash(chosen),inference_triggered=False)
    with store.connection(write=True) as c:c.execute(update(WORLDS).where(WORLDS.c.id==world['id'],WORLDS.c.tenant_id==tenant).values(payload=world))


def pending(store,lane):
    condition=JOBS.c.kind=='review' if lane=='provider' else JOBS.c.kind!='review'
    with store.connection() as c:
        return c.execute(select(JOBS.c.tenant_id,JOBS.c.id).where(JOBS.c.status=='QUEUED',condition).order_by(JOBS.c.created_at,JOBS.c.id).limit(1)).first()


def recover(store):
    with store.connection() as c:rows=c.execute(select(JOBS).where(JOBS.c.status=='RUNNING')).mappings().all()
    for row in rows:
        with store.transaction(row['tenant_id']) as c:
            job=deepcopy(row['payload']);job.update(status='FAILED',error='Worker restarted; no calculation or inference was replayed automatically',completed_at=now())
            c.execute(update(JOBS).where(JOBS.c.id==row['id'],JOBS.c.status=='RUNNING').values(status='FAILED',payload=job))
            session=get_session(store,row['tenant_id'],row['session_id'])
            if session and session.get('job',{}).get('id')==row['id']:
                session.update(job={k:v for k,v in job.items() if k!='input'},status='FAILED',stage='failed',revision=session['revision']+1)
                save_session(store,row['tenant_id'],session)


def execute_job(store,tenant,id):
    with store.transaction(tenant) as c:
        row=c.execute(select(JOBS).where(JOBS.c.id==id,JOBS.c.tenant_id==tenant).with_for_update()).mappings().first()
        if not row or row['status']!='QUEUED':return
        job=deepcopy(row['payload']);job.update(status='RUNNING',started_at=now())
        c.execute(update(JOBS).where(JOBS.c.id==id).values(status='RUNNING',payload=job))
        session=get_session(store,tenant,row['session_id']);session.update(status='RUNNING',job={k:v for k,v in job.items() if k!='input'})
        save_session(store,tenant,session)
    def cancelled():
        current=get_session(store,tenant,row['session_id'])
        return not current or current.get('job',{}).get('id')!=id or current['status']=='CANCELLED'
    def progress(stage):
        with store.transaction(tenant):
            current=get_session(store,tenant,row['session_id'])
            if current and current.get('job',{}).get('id')==id and current['status']=='RUNNING':
                current['job']['stage']=stage;save_session(store,tenant,current)
    output=None;error=None
    try:
        if job['kind']=='review':
            from runtime.deepseek_gateway import RunBudget,provider_user_id_for_tenant
            from services.api.planning_council import review_plan
            day=now()[:10]
            if not os.environ.get('DEEPSEEK_API_KEY'):
                output=dict(status='blocked',reason='DeepSeek credential unavailable',findings=[],request_count=0)
            elif not store.reserve_calls(REVIEW_RESERVATION,48,day):
                output=dict(status='blocked',reason='The full seven-request review allowance is unavailable today',findings=[],request_count=0)
            else:
                budget=RunBudget(max_requests=REVIEW_RESERVATION,max_reserved_output_tokens=16384,max_wall_seconds=300)
                try:
                    result=get_result(store,tenant,job['input']['result_id'])
                    output=review_plan(result,budget=budget,emit=lambda event,body:progress(event),cancelled=cancelled,provider_user_id=provider_user_id_for_tenant(tenant))
                finally:
                    store.release_unused_calls(REVIEW_RESERVATION-budget.request_count,day)
        else:
            output=calculate('session',job['input'],cache_scope=tenant,cancelled=cancelled,progress=progress)
    except InterruptedError as exc:error=str(exc)
    except Exception as exc:error=f'{type(exc).__name__}: {str(exc)[:400]}'
    with store.transaction(tenant) as c:
        current=get_session(store,tenant,row['session_id'])
        if cancelled():
            job.update(status='CANCELLED',completed_at=now())
            c.execute(update(JOBS).where(JOBS.c.id==id).values(status='CANCELLED',payload=job))
            return
        if not error and job['input'].get('workflow_execution_hash') is not None:
            if _task_execution_hash(store,tenant,current['id'])!=job['input']['workflow_execution_hash']:
                error='Reported work changed during calculation; refresh the proposal before recalculating'
        if not error and job['kind']=='disrupt' and current.get('world_id'):
            from services.api.simulation import get_world
            world=get_world(store,tenant,current['world_id'])
            if world['revision']!=job['input'].get('world_revision'):
                error='Recorded simulation changed during calculation; the existing plan and events were preserved'
        job.update(status='FAILED' if error else 'COMPLETED',completed_at=now(),stage='failed' if error else 'complete',error=error)
        current.update(status=job['status'],job={k:v for k,v in job.items() if k!='input'},revision=current['revision']+1)
        if not error:
            if job['kind']=='review':
                # Preserve the frozen review after a later numerical revision clears
                # the current advice. Replay must not need another provider call.
                job['review_result']=deepcopy(output)
                current.setdefault('review_history',[]).append(dict(
                    job_id=id,result_id=job['input']['result_id'],
                    completed_at=job['completed_at'],review=deepcopy(output)))
                current['review']=output;current['stage']='review'
            else:
                c.execute(VERSIONS.insert().values(id=id,tenant_id=tenant,session_id=current['id'],payload=output))
                current['history'].append(dict(result_id=id,kind=job['kind'],created_at=now(),input_hash=content_hash(output.get('input_snapshot',job['input']['farm']))))
                current.update(result_id=id,farm=deepcopy(output.get('input_snapshot',job['input']['farm'])),input_hash=content_hash(output.get('input_snapshot',job['input']['farm'])),
                    selected_strategy_id=output.get('selected_strategy_id'),assumptions=job['input']['kwargs'].get('assumptions',{}),review={'status':'not_requested','findings':[]},stage='comparison' if job['kind']=='disrupt' else 'review')
                if current.get('world_id') and current['selected_strategy_id'] and not current.get('workflow_version'):_apply_world_replan(store,tenant,current,output)
        c.execute(update(JOBS).where(JOBS.c.id==id).values(status=job['status'],payload=job))
        save_session(store,tenant,current)


def register(app,tenant):
    def receipt(request,t,body,scope):
        key=request.headers.get('Idempotency-Key','')
        if not key or len(key)>128:raise HTTPException(422,'Idempotency-Key required, maximum 128 characters')
        digest=content_hash(dict(scope=scope,body=body.model_dump(mode='json')))
        with app.state.store.connection() as c:old=c.execute(select(RECEIPTS).where(RECEIPTS.c.tenant_id==t,RECEIPTS.c.key==key)).mappings().first()
        if old and old['request_hash']!=digest:raise HTTPException(409,'Idempotency key reused with changed inputs')
        return key,digest,old['payload'] if old else None
    def finish(t,key,digest,session):
        value=public_session(app.state.store,t,session)
        with app.state.store.connection(write=True) as c:c.execute(RECEIPTS.insert().values(tenant_id=t,key=key,request_hash=digest,payload=value))
        return value
    def owned(t,id):
        value=get_session(app.state.store,t,id)
        if value is None:raise HTTPException(404,'Planning session not found')
        return value
    def ready(session,body):
        if session['revision']!=body.revision:raise HTTPException(409,'Planning revision changed; refresh before continuing')
        if session['status'] in ('QUEUED','RUNNING'):raise HTTPException(409,'A planning action is already active')
    def queue(t,session,kind,input):
        store=app.state.store
        with store.connection() as c:
            if c.execute(select(func.count()).select_from(JOBS).where(JOBS.c.tenant_id==t,JOBS.c.session_id==session['id'])).scalar_one()>=32:raise HTTPException(429,'Thirty-two planning jobs per mission maximum')
            if c.execute(select(JOBS.c.id).where(JOBS.c.tenant_id==t,JOBS.c.status.in_(['QUEUED','RUNNING']))).first():raise HTTPException(409,'Another guided planning action is active')
        job=dict(id=secrets.token_hex(16),kind=kind,status='QUEUED',stage='queued',created_at=now(),input=input)
        with store.connection(write=True) as c:c.execute(JOBS.insert().values(id=job['id'],tenant_id=t,session_id=session['id'],status=job['status'],kind=kind,created_at=job['created_at'],payload=job))
        session.update(job={k:v for k,v in job.items() if k!='input'},status='QUEUED',revision=session['revision']+1)
        save_session(store,t,session)
    @app.get('/api/v1/planning-sessions')
    def listing(request:Request):
        t=tenant(request)
        with app.state.store.connection() as c:rows=c.execute(select(SESSIONS.c.payload).where(SESSIONS.c.tenant_id==t).limit(8)).scalars().all()
        return {'sessions':[public_session(app.state.store,t,s) for s in sorted(rows,key=lambda s:s['updated_at'],reverse=True)]}
    @app.post('/api/v1/planning-sessions',status_code=201)
    def create(body:CreatePlanningSession,request:Request):
        t=tenant(request);store=app.state.store
        with store.transaction(t) as c:
            key,digest,replay=receipt(request,t,body,'create')
            if replay is not None:return replay
            if c.execute(select(func.count()).select_from(SESSIONS).where(SESSIONS.c.tenant_id==t)).scalar_one()>=8:raise HTTPException(429,'Eight planning sessions per tenant maximum')
            farm=store.latest_farm(t)
            if not farm:raise HTTPException(409,'Load farm records first')
            session=dict(id=secrets.token_hex(16),name=body.name,version=VERSION,revision=0,status='DRAFT',stage='records',created_at=now(),updated_at=now(),farm=deepcopy(farm),input_hash=content_hash(farm),result_id=None,selected_strategy_id=None,review={'status':'not_requested','findings':[]},assumptions={},world_id=None,history=[],job=None,data_mode='synthetic_demo',council_policy='advisory',real_operations_enabled=False)
            if body.workflow:session['workflow_version']='farmer-workflow-v1'
            c.execute(SESSIONS.insert().values(id=session['id'],tenant_id=t,status='DRAFT',payload=session))
            return finish(t,key,digest,session)
    @app.get('/api/v1/planning-sessions/{id}')
    def get(id:str,request:Request):
        t=tenant(request);return public_session(app.state.store,t,owned(t,id))
    @app.post('/api/v1/planning-sessions/{id}/calculate',status_code=202)
    def calculate_route(id:str,body:PlanningRevision,request:Request):
        t=tenant(request);store=app.state.store
        with store.transaction(t):
            key,digest,replay=receipt(request,t,body,'calculate:'+id)
            if replay is not None:return replay
            session=owned(t,id);ready(session,body)
            if session.get('result_id'):raise HTTPException(409,'Use a disruption to compare against the saved schedule')
            queue(t,session,'calculate',{'farm':session['farm'],'kwargs':{}})
            return finish(t,key,digest,session)
    @app.post('/api/v1/planning-sessions/{id}/review',status_code=202)
    def review(id:str,body:PlanningRevision,request:Request):
        t=tenant(request);store=app.state.store
        with store.transaction(t):
            key,digest,replay=receipt(request,t,body,'review:'+id)
            if replay is not None:return replay
            session=owned(t,id);ready(session,body)
            if not session.get('result_id'):raise HTTPException(409,'Calculate schedules before requesting Council review')
            if session.get('review',{}).get('status')=='completed':return finish(t,key,digest,session)
            queue(t,session,'review',{'result_id':session['result_id']})
            return finish(t,key,digest,session)
    @app.post('/api/v1/planning-sessions/{id}/disrupt',status_code=202)
    def disrupt(id:str,body:PlanningDisruption,request:Request):
        t=tenant(request);store=app.state.store
        with store.transaction(t):
            key,digest,replay=receipt(request,t,body,'disrupt:'+id)
            if replay is not None:return replay
            session=owned(t,id);ready(session,body)
            snapshot,kwargs=_remaining_input(store,t,session)
            try:body.assumptions.check_farm(Farm.model_validate(snapshot))
            except ValueError as exc:raise HTTPException(422,str(exc)) from None
            kwargs['assumptions']=body.assumptions.model_dump(mode='json',exclude_none=True)
            from services.api.simulation import get_world
            world=get_world(store,t,session['world_id']) if session.get('world_id') else None
            queue(t,session,'disrupt',{'farm':snapshot,'kwargs':kwargs,'world_revision':world['revision'] if world else None})
            return finish(t,key,digest,session)
    @app.post('/api/v1/planning-sessions/{id}/advance')
    def step(id:str,body:PlanningAdvance,request:Request):
        from services.api.simulation import WORLDS,get_world,advance
        t=tenant(request);store=app.state.store
        with store.transaction(t) as c:
            key,digest,replay=receipt(request,t,body,'advance:'+id)
            if replay is not None:return replay
            session=owned(t,id);ready(session,body)
            result=get_result(store,t,session.get('result_id'))
            if not result or not session.get('selected_strategy_id'):raise HTTPException(409,'A feasible selected schedule is required')
            if session.get('workflow_version') and session.get('approved_result_id')!=session.get('result_id'):
                raise HTTPException(409,'Approve the current sandbox plan and create its actions before simulation')
            world=get_world(store,t,session['world_id']) if session.get('world_id') else _create_world(store,t,session,result)
            advance(store,t,world,body.days)
            c.execute(update(WORLDS).where(WORLDS.c.id==world['id'],WORLDS.c.tenant_id==t).values(payload=world))
            session.update(revision=session['revision']+1,stage='simulation')
            save_session(store,t,session)
            return finish(t,key,digest,session)
    @app.post('/api/v1/planning-sessions/{id}/cancel')
    def cancel(id:str,body:PlanningRevision,request:Request):
        t=tenant(request);store=app.state.store
        with store.transaction(t) as c:
            key,digest,replay=receipt(request,t,body,'cancel:'+id)
            if replay is not None:return replay
            session=owned(t,id)
            if session['revision']!=body.revision:raise HTTPException(409,'Planning revision changed')
            if session['status'] not in ('QUEUED','RUNNING'):raise HTTPException(409,'No active planning job')
            session['job'].update(status='CANCELLED',stage='cancelled',completed_at=now())
            session.update(status='CANCELLED',revision=session['revision']+1)
            c.execute(update(JOBS).where(JOBS.c.id==session['job']['id'],JOBS.c.tenant_id==t).values(status='CANCELLED'))
            save_session(store,t,session)
            return finish(t,key,digest,session)


def queue_recalculation(store, tenant_id, session, changes):
    """Queue a reviewed V12 edit using the same numerical worker and input rules."""
    from packages.planning_contracts import PlanningAssumptions
    if session['status'] in ('QUEUED','RUNNING'):
        raise HTTPException(409,'A planning action is already active')
    if len(changes)!=1 or changes[0].get('kind')!='planning_assumptions':
        raise HTTPException(422,'A single reviewed planning-assumptions proposal is required')
    assumptions=PlanningAssumptions.model_validate(changes[0].get('assumptions',{}))
    snapshot,kwargs=_remaining_input(store,tenant_id,session)
    assumptions.check_farm(Farm.model_validate(snapshot))
    # User-reported completed work is an immutable constraint on later proposals.
    from services.api.farm_workflow import TASKS
    with store.connection() as c:
        recorded=list(c.execute(select(TASKS.c.payload).where(TASKS.c.tenant_id==tenant_id,TASKS.c.session_id==session['id'],TASKS.c.status.in_(['completed','recovery_required']))).scalars())
    recorded_ids={t['batch_id'] for t in recorded if t['status']=='completed' or Decimal(str(t.get('actual_quantity') or 0))>0}
    approved=get_result(store,tenant_id,session.get('approved_result_id'))
    approved_strategy=next((s for s in (approved or {}).get('strategies',[]) if s['id']==session.get('selected_strategy_id')),None)
    if approved_strategy and recorded_ids:
        locks={a['id']:a for a in kwargs.get('locked_allocations',[])}
        farm_batch_ids={b['id'] for b in snapshot['batches']}
        for allocation in approved_strategy['allocations']:
            if allocation['id'] in recorded_ids and allocation['id'] not in farm_batch_ids and allocation['harvest_date']>=str(Farm.model_validate(snapshot).planning_date):
                locks[allocation['id']]=dict(deepcopy(allocation),executed=True,completion_basis='user_reported')
        kwargs['locked_allocations']=list(locks.values())
        kwargs['excluded_candidate_ids']=sorted(set(kwargs.get('excluded_candidate_ids',[]))|recorded_ids)
    kwargs['assumptions']=assumptions.model_dump(mode='json',exclude_none=True)
    from services.api.simulation import get_world
    world=get_world(store,tenant_id,session['world_id']) if session.get('world_id') else None
    with store.connection() as c:
        if c.execute(select(JOBS.c.id).where(JOBS.c.tenant_id==tenant_id,JOBS.c.status.in_(['QUEUED','RUNNING']))).first():
            raise HTTPException(409,'Another guided planning action is active')
        if c.execute(select(func.count()).select_from(JOBS).where(JOBS.c.tenant_id==tenant_id,JOBS.c.session_id==session['id'])).scalar_one()>=32:
            raise HTTPException(429,'Thirty-two planning jobs per mission maximum')
    job=dict(id=secrets.token_hex(16),kind='disrupt',status='QUEUED',stage='queued',created_at=now(),
             input=dict(farm=snapshot,kwargs=kwargs,world_revision=world['revision'] if world else None,workflow_execution_hash=_task_execution_hash(store,tenant_id,session['id'])))
    with store.connection(write=True) as c:
        c.execute(JOBS.insert().values(id=job['id'],tenant_id=tenant_id,session_id=session['id'],status='QUEUED',kind=job['kind'],created_at=job['created_at'],payload=job))
    session.update(workflow_version='farmer-workflow-v1',job={k:v for k,v in job.items() if k!='input'},status='QUEUED',revision=session['revision']+1)
    save_session(store,tenant_id,session)
    return {k:v for k,v in job.items() if k!='input'}


def approve_result(store, tenant_id, session, proposal, result, strategy_id):
    """Explicit approval alone may replace a sandbox world's future schedule."""
    job=proposal.get('recalculation_job',{})
    if (session['status']!='COMPLETED' or session.get('result_id')!=job.get('id')
            or session.get('input_hash')!=content_hash(result.get('input_snapshot',session['farm']))):
        raise HTTPException(409,'Proposal recalculation is incomplete or its planning revision changed')
    selected=next((row for row in result.get('strategies',[]) if row['id']==strategy_id),None)
    if not selected or selected.get('status')!='FEASIBLE' or selected.get('violations'):
        raise HTTPException(409,'Only a feasible calculated strategy can be approved')
    from packages.planner.engine import simulate
    selected_farm=Farm.model_validate(result.get('input_snapshot',session['farm']))
    result=deepcopy(result)
    result['_execution_trace']=simulate(selected_farm,selected['allocations'],result['forecast']['demand'],dict(id='execution-central',yield_factor=1.,demand_factor=1.,weight=1.))
    session['_approved_execution_trace']=result['_execution_trace']
    session.update(workflow_version='farmer-workflow-v1',approved_result_id=session['result_id'],
        approved_result_hash=content_hash(get_result(store,tenant_id,session['result_id'])),selected_strategy_id=strategy_id,approved_at=now(),
        revision=session['revision']+1,stage='approved')
    if session.get('world_id'):
        _apply_world_replan(store,tenant_id,session,result)
    save_session(store,tenant_id,session)
    return session


def refresh_reported_forecast(store, tenant, session_id):
    """Recompute a labelled projection from reported quantities without rewriting history."""
    from services.api.farm_workflow import TASKS, append_event
    from packages.planner.engine import simulate
    session=get_session(store,tenant,session_id)
    if not session:return None
    result=get_result(store,tenant,session.get('approved_result_id'))
    if not result:return None
    strategy=next((s for s in result['strategies'] if s['id']==session.get('selected_strategy_id')),None)
    if not strategy:return None
    with store.connection() as c:
        tasks=list(c.execute(select(TASKS.c.payload).where(TASKS.c.tenant_id==tenant,TASKS.c.session_id==session_id)).scalars())
    harvested={t['batch_id']:t for t in tasks if t['action']=='harvest' and t.get('actual_quantity') is not None and t['status'] in ('completed','recovery_required')}
    allocations=deepcopy(strategy['allocations'])
    for allocation in allocations:
        if allocation['id'] in harvested:
            allocation['expected_kg']=float(harvested[allocation['id']]['actual_quantity'])
    farm=Farm.model_validate(result.get('input_snapshot',session['farm']))
    forecast=simulate(farm,allocations,result['forecast']['demand'],dict(id='reported-central',yield_factor=1.,demand_factor=1.,weight=1.))
    # Delivery reports replace the corresponding projected acceptance, not harvest mass.
    # Rejected quantity stays separately evidenced; it is never renamed shortfall.
    delivery_reports=[t for t in tasks if t['action']=='delivery' and t.get('actual_quantity') is not None and t.get('event_revision',0)>0]
    delivery_rows={row.get('order_id'):row for row in forecast.get('order_allocations',[]) if row.get('demand_kind')=='booked'}
    accepted_delta=Decimal(0);revenue_delta=Decimal(0);rejected_total=Decimal(0)
    for task in delivery_reports:
        row=delivery_rows.get(task.get('order_id'))
        if not row:continue
        accepted=Decimal(str(task['actual_quantity']))
        delta=accepted-Decimal(str(row['delivered_kg']))
        accepted_delta+=delta
        rejected_total+=Decimal(str(task.get('rejected_quantity') or 0))
        if row.get('price_sgd_per_kg') is not None:
            revenue_delta+=delta*Decimal(str(row['price_sgd_per_kg']))
    if delivery_reports:
        metric=forecast['metrics']
        metric['booked_delivered_kg']=float(Decimal(str(metric.get('booked_delivered_kg',0)))+accepted_delta)
        metric['booked_shortfall_kg']=max(0,float(Decimal(str(metric.get('booked_requested_kg',0)))-Decimal(str(metric['booked_delivered_kg']))))
        metric['rejected_kg']=float(rejected_total)
        metric['revenue_sgd']=float(Decimal(str(metric.get('revenue_sgd',0)))+revenue_delta)
        # Packaging was already incurred for dispatched lots; rejection reduces revenue only.
        metric['margin_sgd']=float(Decimal(str(metric.get('margin_sgd',0)))+revenue_delta)
    sources=[dict(task_id=t['id'],event_revision=t['event_revision']) for t in tasks if t.get('event_revision',0)>0]
    report=dict(version='reported-forecast-v1',basis='user_reported_projection',independently_verified=False,
        source_result_id=session['approved_result_id'],source_task_events=sources,metrics=forecast['metrics'],
        recovery_required=any(t['status']=='recovery_required' or (t.get('actual_quantity') is not None and t.get('planned_quantity') is not None and Decimal(str(t['actual_quantity']))<Decimal(str(t['planned_quantity']))) for t in tasks),
        real_operations_enabled=False)
    report['hash']=content_hash(report)
    if session.get('reported_forecast',{}).get('hash')!=report['hash']:
        session['reported_forecast']=report
        session['revision']+=1
        save_session(store,tenant,session)
        append_event(store,tenant,session_id,'reported_forecast_recalculated',report)
    return report


def _task_execution_hash(store,tenant,session_id):
    from services.api.farm_workflow import TASKS
    with store.connection() as c:
        tasks=list(c.execute(select(TASKS.c.payload).where(TASKS.c.tenant_id==tenant,TASKS.c.session_id==session_id)).scalars())
    return content_hash(sorted([dict(id=t['id'],event_revision=t.get('event_revision',0),status=t['status'],actual_quantity=t.get('actual_quantity'),rejected_quantity=t.get('rejected_quantity')) for t in tasks if t.get('event_revision',0)>0],key=lambda t:t['id']))
