"""Frozen, tenant-owned experiments. Numerical work never mutates the main farm."""
from copy import deepcopy
from datetime import timedelta
from decimal import Decimal
import secrets
from typing import Literal
from fastapi import HTTPException, Request
from pydantic import Field, model_validator
from sqlalchemy import Table, Column, String, JSON, ForeignKey, UniqueConstraint, select, update
from packages.contracts import Strict, Farm, content_hash
from packages.planner import plan, validate_allocations
from services.api.store import metadata, now

branches = Table('scenario_branches', metadata,
    Column('id', String, primary_key=True), Column('tenant_id', String, ForeignKey('tenants.id'), nullable=False),
    Column('idempotency_key', String, nullable=False), Column('request_hash', String, nullable=False),
    Column('status', String, nullable=False), Column('payload', JSON, nullable=False),
    UniqueConstraint('tenant_id', 'idempotency_key'), UniqueConstraint('id','tenant_id'))
quest_progress = Table('quest_progress', metadata,
    Column('tenant_id', String, ForeignKey('tenants.id'), primary_key=True),
    Column('quest_id', String, primary_key=True), Column('payload', JSON, nullable=False))

QuestId = Literal['late_harvest', 'busy_market', 'short_handed_week', 'tight_budget']
class Controls(Strict):
    batch_id: str | None = Field(default=None, max_length=100)
    delay_days: int = Field(default=0, ge=0, le=14, strict=True)
    yield_percent: int = Field(default=100, ge=50, le=100, strict=True)
    demand_crop_id: Literal['caixin','pak_choi','kailan','lettuce'] | None = None
    demand_percent: int = Field(default=100, ge=50, le=150, strict=True)
    labour_percent: int = Field(default=100, ge=50, le=150, strict=True)
    cash_percent: int = Field(default=100, ge=50, le=150, strict=True)
    @model_validator(mode='after')
    def targets(self):
        if (self.delay_days or self.yield_percent != 100) and not self.batch_id:
            raise ValueError('A batch is required for harvest changes')
        if self.demand_percent != 100 and not self.demand_crop_id:
            raise ValueError('A crop is required for demand changes')
        return self
class ScenarioRequest(Strict):
    name: str = Field(default='Sandbox experiment', min_length=1, max_length=80)
    parent_scenario_id: str | None = Field(default=None, max_length=64)
    source_conversation_id: str | None = Field(default=None, max_length=64)
    explorer_snapshot_id: str | None = Field(default=None, max_length=100)
    controls: Controls = Field(default_factory=Controls)
    quest_id: QuestId | None = None
    @model_validator(mode='after')
    def quest_assumption(self):
        if self.explorer_snapshot_id and (self.parent_scenario_id or self.source_conversation_id):
            raise ValueError("Choose one snapshot source for a new experiment")
        c=self.controls
        changed={
            'late_harvest':bool(c.delay_days or c.yield_percent!=100),
            'busy_market':c.demand_percent!=100,
            'short_handed_week':c.labour_percent!=100,
            'tight_budget':c.cash_percent!=100,
        }
        if self.quest_id and not changed[self.quest_id]:raise ValueError('Change the assumption relevant to this quest before running it')
        return self
class InspectRequest(Strict):
    scenario_id: str = Field(min_length=1, max_length=64)

QUESTS = [
    dict(id='late_harvest', name='Late harvest', advisor='mei', briefing='A harvest is running late. Explore how a delay and lower marketable yield change deliveries.', objective='Run a harvest experiment and inspect its tradeoffs.'),
    dict(id='busy_market', name='Busy market', advisor='ravi', briefing='Explore a change in simulated demand for an existing crop. Buyer quantities change only inside this branch.', objective='Run a demand experiment and inspect its tradeoffs.'),
    dict(id='short_handed_week', name='Short-handed week', advisor='ben', briefing='Explore a different weekly labour allowance across this planning horizon.', objective='Run a labour experiment and inspect its tradeoffs.'),
    dict(id='tight_budget', name='Tight budget', advisor='ben', briefing='Explore a different cash allowance without borrowing from the main farm.', objective='Run a cash experiment and inspect its tradeoffs.'),
]

def get_scenario(store, tenant, id):
    with store.connection() as c:
        return c.execute(select(branches.c.payload).where(branches.c.tenant_id==tenant, branches.c.id==id)).scalar_one_or_none()

def save_scenario(store, tenant, payload):
    with store.connection(write=True) as c:
        c.execute(update(branches).where(branches.c.tenant_id==tenant, branches.c.id==payload['id']).values(status=payload['status'], payload=payload))

def apply_controls(snapshot, controls):
    farm=Farm.model_validate(snapshot).model_copy(deep=True)
    batch=next((b for b in farm.batches if b.id==controls.batch_id),None)
    if controls.batch_id and not batch: raise HTTPException(422,'Unknown batch in frozen snapshot')
    if batch:
        batch.harvest_date += timedelta(days=controls.delay_days)
        batch.expected_marketable_kg *= Decimal(controls.yield_percent)/100
    if controls.demand_crop_id:
        if controls.demand_crop_id not in {r.crop_id for r in farm.recipes}:raise HTTPException(422,'Crop has no simulated recipe')
        factor=Decimal(controls.demand_percent)/100
        for order in farm.orders:
            if order.crop_id==controls.demand_crop_id:
                order.quantity_kg *= factor; order.cancelled_kg *= factor
        for row in farm.history:
            if row.crop_id==controls.demand_crop_id:row.ordered_kg *= factor
    farm.resources.labour_hours_per_week *= Decimal(controls.labour_percent)/100
    farm.resources.cash_sgd *= Decimal(controls.cash_percent)/100
    return Farm.model_validate(farm.model_dump(mode='json')).model_dump(mode='json')

def pending_scenarios(store):
    with store.connection() as c:
        return c.execute(select(branches.c.tenant_id, branches.c.id).where(branches.c.status=='QUEUED')).all()

def execute_scenario(store, tenant, id):
    with store.connection(write=True) as c:
        claimed=c.execute(update(branches).where(branches.c.tenant_id==tenant,branches.c.id==id,branches.c.status=='QUEUED').values(status='RUNNING')).rowcount
    if not claimed:return
    s=get_scenario(store,tenant,id);s['status']='RUNNING';save_scenario(store,tenant,s)
    try:
        from packages.models import MODEL_VERSION
        from packages.planner.engine import VERSION
        if s.get('forecast_version',MODEL_VERSION)!=MODEL_VERSION or s.get('baseline_forecast_version',MODEL_VERSION)!=MODEL_VERSION or s.get('calculation_version',VERSION)!=VERSION:
            s['warnings'].append('The frozen forecast or planner version is unavailable. Saved inputs are preserved; this worker did not substitute a different numerical model.')
            raise ValueError('Frozen numerical version is not supported by this worker')
        if s.get('comparison_root','').startswith('playground:') and not s.get('baseline'):
            with store.connection() as c:
                prior=c.execute(select(branches.c.payload).where(branches.c.tenant_id==tenant,branches.c.status=='COMPLETED')).scalars().all()
                s['baseline']=next((p['baseline'] for p in prior if p.get('comparison_root')==s['comparison_root'] and p.get('calculation_version',VERSION)==s.get('calculation_version',VERSION)),None)
        # Legacy main-farm branches retain their existing default call and hashes.
        baseline_args={'alpha':s['baseline_forecast_settings']['alpha']} if s.get('baseline_forecast_settings') else {}
        forecast_args={'alpha':s['forecast_settings']['alpha']} if s.get('forecast_settings') else {}
        s['baseline']=s.get('baseline') or plan(Farm.model_validate(s['baseline_snapshot']),**baseline_args)
        same=s['input_hash']==s['baseline_hash'] and s.get('forecast_settings',{'alpha':.35})==s.get('baseline_forecast_settings',{'alpha':.35})
        s['result']=deepcopy(s['baseline']) if same else plan(Farm.model_validate(s['input_snapshot']),**forecast_args)
        s['policy_comparisons']=policy_comparisons(s['baseline'],s['result'])
        farm=Farm.model_validate(s['input_snapshot'])
        eligible=[r for r in s['result']['strategies'] if r['status']=='FEASIBLE' and not validate_allocations(farm,r['allocations'])]
        chosen=next((r for r in eligible if r['name']=='Balanced'),eligible[0] if eligible else None)
        s['status']='COMPLETED'
        s['simulation_status']='ACCEPTED_FOR_SIMULATION' if chosen else 'NO_FEASIBLE_PLAN'
        s['accepted_strategy_id']=chosen['id'] if chosen else None
        s['acceptance']=dict(actor='development-policy-service', policy_version='scenario-simulation-v1',input_hash=s['input_hash'],input_version=farm.version,strategy_id=chosen['id'],strategy_hash=content_hash(chosen),validation_report_id=content_hash(chosen['violations']),decision_policy='automatic_development',execution_mode='test',data_mode='synthetic_demo',simulation_only=True,occurred_at=now()) if chosen else None
        s['completed_at']=now()
        s.update(computed_impacts(s))
    except Exception as exc:
        s['status']='FAILED';s['warnings'].append(f'Numerical experiment failed ({type(exc).__name__}). Inputs were preserved; no inference was used.')
    with store.transaction(tenant):
        save_scenario(store,tenant,s)
        if s['status']=='COMPLETED' and s.get('quest_id'):
            _progress(store,tenant,s['quest_id'],s['id'],False)

def policy_comparisons(baseline, result):
    """Exact same-policy deltas, computed locally from validated planning output."""
    rows=[]
    for after in result['strategies']:
        before=next(s for s in baseline['strategies'] if s['name']==after['name'])
        deltas={key:round(value-before['metrics'][key],6) for key,value in after['metrics'].items() if isinstance(value,(int,float)) and isinstance(before['metrics'].get(key),(int,float))}
        rows.append(dict(policy=after['name'],baseline_strategy_id=before['id'],scenario_strategy_id=after['id'],baseline_status=before['status'],scenario_status=after['status'],baseline_metrics=before['metrics'],scenario_metrics=after['metrics'],deltas=deltas,violations=after['violations']))
    return rows

def computed_impacts(s):
    """Compare declared allocations and daily totals; do not infer per-order fulfilment."""
    changed_beds=set(); changed_dates=set()
    for after in s['result']['strategies']:
        before=next(row for row in s['baseline']['strategies'] if row['name']==after['name'])
        def by_bed(strategy):
            grouped={}
            for allocation in strategy['allocations']:
                grouped.setdefault(allocation['bed_id'],[]).append(content_hash(allocation))
            return {bed:sorted(values) for bed,values in grouped.items()}
        old,new=by_bed(before),by_bed(after)
        changed_beds.update(bed for bed in old.keys()|new.keys() if old.get(bed)!=new.get(bed))
        old_days={row['date']:(row['demand_kg'],row['delivered_kg']) for row in before['ledger']}
        new_days={row['date']:(row['demand_kg'],row['delivered_kg']) for row in after['ledger']}
        changed_dates.update(day for day in old_days.keys()|new_days.keys() if old_days.get(day)!=new_days.get(day))
    old_orders={row['id']:row for row in s['baseline_snapshot']['orders']}
    deliveries=[dict(crop_id=row['crop_id'],due_date=row['due_date'],order_id=row['id']) for row in s['input_snapshot']['orders'] if row['due_date'] in changed_dates or old_orders.get(row['id'])!=row]
    return dict(affected_bed_ids=sorted(changed_beds),affected_deliveries=deliveries,affected_basis='Changed allocations across policies; deliveries to inspect on dates with changed aggregate demand or delivery totals, or changed order inputs. This is not per-order fulfilment attribution.')

def interrupt_scenarios(store):
    # Numerical jobs may safely resume after restart; no inference side effects exist.
    with store.connection(write=True) as c:
        rows=c.execute(select(branches.c.payload).where(branches.c.status=='RUNNING')).scalars().all()
        for s in rows:
            s['status']='QUEUED'
            c.execute(update(branches).where(branches.c.id==s['id']).values(status='QUEUED',payload=s))

def _progress(store,tenant,quest,id,inspect):
    with store.connection(write=True) as c:
        p=c.execute(select(quest_progress.c.payload).where(quest_progress.c.tenant_id==tenant,quest_progress.c.quest_id==quest)).scalar_one_or_none()
        old=bool(p)
        p=deepcopy(p) if p else dict(experiment_ids=[],inspected_ids=[],badges=[],status='available')
        if id not in p['experiment_ids']:p['experiment_ids'].append(id)
        if inspect and id not in p['inspected_ids']:p['inspected_ids'].append(id)
        p['status']='completed' if p['inspected_ids'] else 'experiment_complete'
        p['badges']=['Experiment explorer']+(['Tradeoff discovered'] if p['inspected_ids'] else [])
        p['updated_at']=now()
        if old:c.execute(update(quest_progress).where(quest_progress.c.tenant_id==tenant,quest_progress.c.quest_id==quest).values(payload=p))
        else:c.execute(quest_progress.insert().values(tenant_id=tenant,quest_id=quest,payload=p))
    return p

def install_routes(app,tenant):
    def owned(request,id):
        t=tenant(request);s=get_scenario(app.state.store,t,id)
        if not s:raise HTTPException(404,'Scenario not found')
        return t,s
    def key(request):
        k=request.headers.get('Idempotency-Key')
        if not k or len(k)>128:raise HTTPException(422,'Idempotency-Key required, maximum 128 characters')
        return k
    @app.get('/api/v1/scenarios')
    def listing(request:Request):
        t=tenant(request)
        with app.state.store.connection() as c:rows=c.execute(select(branches.c.payload).where(branches.c.tenant_id==t)).scalars().all()
        # Return full persisted branches so reopening never requires a recalculation.
        return dict(scenarios=sorted(rows,key=lambda x:x['created_at'],reverse=True))
    @app.post('/api/v1/scenarios',status_code=201)
    def create(body:ScenarioRequest,request:Request):
        t=tenant(request);k=key(request);store=app.state.store;fingerprint=content_hash(body)
        with store.transaction(t) as c:
            old=c.execute(select(branches).where(branches.c.tenant_id==t,branches.c.idempotency_key==k)).mappings().first()
            if old:
                if old['request_hash']!=fingerprint:raise HTTPException(409,'Idempotency key reused with changed inputs')
                return dict(old['payload'],reused=True)
            parent=get_scenario(store,t,body.parent_scenario_id) if body.parent_scenario_id else None
            if body.parent_scenario_id and not parent:raise HTTPException(404,'Parent scenario not found')
            if parent and parent['status']!='COMPLETED':raise HTTPException(409,'Complete the parent experiment first')
            conversation=None
            if body.source_conversation_id:
                from services.api.conversation_store import ConversationStore
                conversation=ConversationStore(store).get_conversation(t,body.source_conversation_id)
                if not conversation:raise HTTPException(404,'Source conversation not found')
                if parent and parent['input_hash']!=conversation['snapshot_ref']['hash']:raise HTTPException(409,'Conversation and parent refer to different snapshots')
                if not parent and conversation.get('_scenario'):
                    parent=get_scenario(store,t,conversation['_scenario']['id'])
            explorer=None
            if body.explorer_snapshot_id:
                from services.api.data_explorer import get_saved
                explorer=get_saved(store,t,body.explorer_snapshot_id)
                if not explorer:raise HTTPException(404,'Saved explorer dataset not found')
            source=explorer['input_snapshot'] if explorer else (conversation['_snapshot'] if conversation else (parent['input_snapshot'] if parent else store.latest_farm(t)))
            if not source:raise HTTPException(409,'Import a farm before creating a scenario')
            snapshot=apply_controls(source,body.controls)
            if body.quest_id and content_hash(snapshot)==content_hash(source):raise HTTPException(422,'This quest must change its frozen inputs')
            controls=body.controls.model_dump()
            crop_ids=set()
            if controls['batch_id'] and (controls['delay_days'] or controls['yield_percent']!=100):
                batch=next(b for b in snapshot['batches'] if b['id']==controls['batch_id'])
                crop_ids.add(next(r['crop_id'] for r in snapshot['recipes'] if r['id']==batch['recipe_id']))
            if controls['demand_crop_id'] and controls['demand_percent']!=100:crop_ids.add(controls['demand_crop_id'])
            if controls['cash_percent']!=100 or controls['labour_percent']!=100:crop_ids.update(r['crop_id'] for r in snapshot['recipes'])
            affected=[b['bed_id'] for b in snapshot['batches'] if next(r['crop_id'] for r in snapshot['recipes'] if r['id']==b['recipe_id']) in crop_ids]
            s=dict(id=secrets.token_hex(16),name=body.name,created_at=now(),status='DRAFT',controls=controls,quest_id=body.quest_id,parent_scenario_id=parent['id'] if parent else None,source_conversation_id=body.source_conversation_id,input_snapshot=snapshot,input_hash=content_hash(snapshot),baseline_snapshot=parent['baseline_snapshot'] if parent else source,baseline=parent.get('baseline') if parent else None,result=None,affected_bed_ids=affected,affected_crop_ids=sorted(crop_ids),affected_deliveries=[],warnings=[],data_mode='synthetic_demo',execution_mode='test',inference_calls=0)
            if explorer:
                from services.api.data_explorer import reference_payload
                ref=reference_payload()
                if explorer.get('reference_snapshot'):
                    ref.update(input_snapshot=explorer['reference_snapshot'],forecast_settings=explorer['reference_forecast_settings'],forecast_version=explorer['reference_forecast_version'],content_hash=explorer['reference_content_hash'])
                s.update(explorer_snapshot_id=explorer['id'],generator_settings=explorer['generator_settings'],generator_version=explorer['generator_version'],forecast_settings=explorer['forecast_settings'],forecast_version=explorer['forecast_version'],dataset_hash=explorer['content_hash'],baseline_snapshot=ref['input_snapshot'],baseline_forecast_settings=ref['forecast_settings'],baseline_forecast_version=ref['forecast_version'],comparison_root='playground:'+ref['content_hash'])
            elif parent:
                for field in ('explorer_snapshot_id','generator_settings','generator_version','forecast_settings','forecast_version','dataset_hash','baseline_forecast_settings','baseline_forecast_version','comparison_root'):
                    if field in parent:s[field]=deepcopy(parent[field])
            s['baseline_hash']=content_hash(s['baseline_snapshot'])
            s.setdefault('comparison_root','farm:'+s['baseline_hash'])
            from packages.planner.engine import VERSION
            s['calculation_version']=VERSION
            if s.get('forecast_settings'):
                s['numerical_input_hash']=content_hash(dict(input_hash=s['input_hash'],configuration_hash=content_hash(dict(model_version=s['forecast_version'],forecast_settings=s['forecast_settings']))))
            c.execute(branches.insert().values(id=s['id'],tenant_id=t,idempotency_key=k,request_hash=fingerprint,status=s['status'],payload=s))
        return s
    @app.get('/api/v1/scenarios/compare')
    def compare(request:Request,ids:str):
        chosen=ids.split(',')
        if not 1<=len(chosen)<=3 or len(set(chosen))!=len(chosen):raise HTTPException(422,'Compare one to three distinct branches')
        rows=[owned(request,id)[1] for id in chosen]
        if any(s['status']!='COMPLETED' for s in rows):raise HTTPException(409,'Complete experiments before comparing')
        if len({(s.get('comparison_root','farm:'+s['baseline_hash']),s['baseline_hash'],content_hash(s.get('baseline_forecast_settings',{'alpha':.35})),s.get('calculation_version',s['result']['strategies'][0].get('calculation_version'))) for s in rows})!=1:raise HTTPException(409,'Branches must share the same frozen baseline')
        return dict(baseline=rows[0]['baseline'],baseline_hash=rows[0]['baseline_hash'],scenarios=rows)
    @app.get('/api/v1/scenarios/{id}')
    def read(id:str,request:Request):return owned(request,id)[1]
    @app.post('/api/v1/scenarios/{id}/run',status_code=202)
    def run(id:str,request:Request):
        t,_=owned(request,id);k=key(request);store=app.state.store
        with store.transaction(t):
            s=get_scenario(store,t,id)
            if s.get('run_key') and s['run_key']!=k:raise HTTPException(409,'This frozen experiment already has a run; continue it in a new branch')
            if s.get('run_key'):return dict(s,reused=True)
            s['run_key']=k;s['status']='QUEUED';save_scenario(store,t,s)
        return s
    @app.get('/api/v1/quests')
    def quests(request:Request):
        t=tenant(request)
        with app.state.store.connection() as c:rows=dict(c.execute(select(quest_progress.c.quest_id,quest_progress.c.payload).where(quest_progress.c.tenant_id==t)).all())
        return dict(quests=[dict(q,**rows.get(q['id'],dict(status='available',badges=[],experiment_ids=[],inspected_ids=[]))) for q in QUESTS])
    @app.post('/api/v1/quests/{id}/inspect')
    def inspect(id:QuestId,body:InspectRequest,request:Request):
        t,s=owned(request,body.scenario_id)
        if s['quest_id']!=id or s['status']!='COMPLETED':raise HTTPException(409,'Complete an experiment for this quest first')
        with app.state.store.transaction(t):return _progress(app.state.store,t,id,s['id'],True)
