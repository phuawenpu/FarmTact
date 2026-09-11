"""Isolated playable council study: scripted dialogue, actual numerical scenarios.

No free-form text executes tools. The bounded interpreter proposes typed edits;
explicit apply freezes a new research version, never changes the main farm.
"""
from copy import deepcopy
from datetime import date, timedelta
import re
import secrets
from typing import Literal
from fastapi import HTTPException, Request
from pydantic import Field
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, Table, UniqueConstraint, select, update
from packages.contracts import Strict, Farm, Order, content_hash
from packages.fixtures import synthetic_farm
from services.api.store import metadata, now

VERSION='council-research-v1'
SESSIONS=Table('council_research_sessions',metadata,
    Column('id',String,primary_key=True),Column('tenant_id',String,ForeignKey('tenants.id'),nullable=False),
    Column('idempotency_key',String,nullable=False),Column('request_hash',String,nullable=False),Column('payload',JSON,nullable=False),
    UniqueConstraint('tenant_id','idempotency_key'),UniqueConstraint('id','tenant_id'))
JOBS=Table('council_research_jobs',metadata,
    Column('id',String,primary_key=True),Column('tenant_id',String,ForeignKey('tenants.id'),nullable=False),
    Column('session_id',String,ForeignKey('council_research_sessions.id'),nullable=False),
    Column('version',Integer,nullable=False),Column('status',String,nullable=False),Column('payload',JSON,nullable=False),
    UniqueConstraint('session_id','version'),
    ForeignKeyConstraint(['session_id','tenant_id'],['council_research_sessions.id','council_research_sessions.tenant_id'],name='research_job_tenant_fk'))
ACTIONS=Table('council_research_actions',metadata,
    Column('id',String,primary_key=True),Column('tenant_id',String,ForeignKey('tenants.id'),nullable=False),
    Column('session_id',String,ForeignKey('council_research_sessions.id'),nullable=False),
    Column('idempotency_key',String,nullable=False),Column('request_hash',String,nullable=False),
    UniqueConstraint('tenant_id','idempotency_key'),
    ForeignKeyConstraint(['session_id','tenant_id'],['council_research_sessions.id','council_research_sessions.tenant_id'],name='research_action_tenant_fk'))

HISTORY=Table('council_research_history',metadata,
    Column('session_id',String,primary_key=True),Column('revision',Integer,primary_key=True),
    Column('tenant_id',String,ForeignKey('tenants.id'),nullable=False),Column('payload',JSON,nullable=False),
    ForeignKeyConstraint(['session_id','tenant_id'],['council_research_sessions.id','council_research_sessions.tenant_id'],name='research_history_tenant_fk',ondelete='CASCADE'))


def record_revision(store,tenant,s,previous=None):
    """Append immutable deltas; large frozen results are stored only when changed."""
    previous=previous or {}
    if previous:
        with store.connection() as c:
            has_history=c.execute(select(HISTORY.c.revision).where(HISTORY.c.session_id==s['id'],HISTORY.c.tenant_id==tenant).limit(1)).first()
        if not has_history:record_revision(store,tenant,previous)
    delta={k:deepcopy(v) for k,v in s.items() if k not in ('messages','events') and (k not in previous or previous[k]!=v)}
    old_messages={m['id'] for m in previous.get('messages',[])}
    old_events={e.get('id') or content_hash(e) for e in previous.get('events',[])}
    payload=dict(changes=delta,messages=[deepcopy(m) for m in s['messages'] if m['id'] not in old_messages],
                 events=[deepcopy(e) for e in s['events'] if (e.get('id') or content_hash(e)) not in old_events],at=now())
    with store.connection(write=True) as c:
        c.execute(HISTORY.insert().values(session_id=s['id'],revision=s['revision'],tenant_id=tenant,payload=payload))


def revision_snapshot(store,tenant,id,revision):
    with store.connection() as c:
        rows=c.execute(select(HISTORY.c.payload).where(HISTORY.c.session_id==id,HISTORY.c.tenant_id==tenant,HISTORY.c.revision<=revision).order_by(HISTORY.c.revision)).scalars().all()
    if not rows:return None
    state=dict(messages=[],events=[])
    for row in rows:
        state.update(deepcopy(row['changes']));state['messages']+=deepcopy(row['messages']);state['events']+=deepcopy(row['events'])
    state['messages']=state['messages'][-120:];state['events']=state['events'][-240:]
    return state

RECEIPTS=Table('council_research_action_receipts',metadata,
    Column('action_id',String,ForeignKey('council_research_actions.id',ondelete='CASCADE'),primary_key=True),
    Column('tenant_id',String,ForeignKey('tenants.id'),nullable=False),Column('revision',Integer,nullable=False))

class NewSession(Strict):
    concept:Literal['inline','sheet','cards']='sheet'
    steering:Literal['continuous','checkpoints']='continuous'

class Action(Strict):
    action:Literal['say','select','propose','apply','discard','run','cancel_calculation','retry_calculation','challenge','resolve','choose','configure','stop','next']
    revision:int=Field(ge=0)
    text:str=Field(default='',max_length=1000)
    refs:list[str]=Field(default_factory=list,max_length=8)
    operation:Literal['reserve_bed','order_status','labour']|None=None
    bed_id:str|None=Field(default=None,max_length=64)
    order_id:str|None=Field(default=None,max_length=64)
    start_date:date|None=None
    end_date:date|None=None
    confirmed:bool|None=None
    labour_percent:int|None=Field(default=None,ge=50,le=100,strict=True)
    policy:Literal['Lean','Balanced','Resilient']='Balanced'
    result_version:int|None=Field(default=None,ge=1)
    concept:Literal['inline','sheet','cards']|None=None
    steering:Literal['continuous','checkpoints']|None=None
    selection_mode:Literal['chips','cards']|None=None
    animation:Literal['static','transition']|None=None
    resolution:Literal['evidence','corrected','unresolved','reject']|None=None
    advisor:Literal['Demand','Weather','Market','Production','Supply Chain','Profit','Planner']='Planner'


def get_session(store,tenant,id):
    with store.connection() as c:return c.execute(select(SESSIONS.c.payload).where(SESSIONS.c.id==id,SESSIONS.c.tenant_id==tenant)).scalar_one_or_none()

def save(store,tenant,s):
    previous=get_session(store,tenant,s['id'])
    record_revision(store,tenant,s,previous)
    with store.connection(write=True) as c:c.execute(update(SESSIONS).where(SESSIONS.c.id==s['id'],SESSIONS.c.tenant_id==tenant).values(payload=s))

def append(s,speaker,text,refs=None,kind='scripted'):
    s['messages'].append(dict(id=secrets.token_hex(8),speaker=speaker,text=text,refs=refs or [],kind=kind,input_version=s['input_version'],created_at=now()))
    s['messages']=s['messages'][-120:]

def event(s,kind,**details):
    s['event_sequence']=s.get('event_sequence',len(s['events']))+1
    s['events'].append(dict(id=secrets.token_hex(12),sequence=s['event_sequence'],type=kind,at=now(),input_version=s['input_version'],**details));s['events']=s['events'][-240:]

def all_refs(s):
    f=s['farm'];return {f"bed:{x['id']}" for x in f['beds']}|{f"order:{x['id']}" for x in f['orders']}|{f"batch:{x['id']}" for x in f['batches']}|{f"crop:{x['crop_id']}" for x in f['recipes']}

def result_current(s):return next((r for r in s['results'] if r['version']==s['input_version'] and r['status']=='COMPLETED'),None)

def eligible(s,result,policy):
    row=next((r for r in result['calculation']['strategies'] if r['name']==policy),None)
    return row if row and row['status']=='FEASIBLE' and not row['violations'] else None

def propose(s,a):
    op=a.operation
    if not op:raise HTTPException(422,'Choose a supported research operation')
    p=dict(operation=op,base_version=s['input_version'])
    if op=='reserve_bed':
        if a.bed_id not in {b['id'] for b in s['farm']['beds']}:raise HTTPException(422,'Select a bed in this research snapshot')
        p.update(bed_id=a.bed_id,start_date=str(a.start_date) if a.start_date else None,end_date=str(a.end_date) if a.end_date else None)
        append(s,'Production','Specify the reservation dates. Existing crops and their sanitation period remain protected.',[f'bed:{a.bed_id}'])
    elif op=='order_status':
        if a.order_id not in {o['id'] for o in s['farm']['orders']} or a.confirmed is None:raise HTTPException(422,'Choose an order and its confirmation state')
        p.update(order_id=a.order_id,confirmed=a.confirmed)
        append(s,'Demand','This proposal changes booked commitments only inside the research scenario. Unconfirmed demand stays visible as a possibility.',[f'order:{a.order_id}'])
    else:
        if a.labour_percent is None:raise HTTPException(422,'Specify a labour allowance from 50 to 100 percent')
        p['labour_percent']=a.labour_percent
        append(s,'Profit','Review the proposed labour ceiling before applying it. No extra labour will be created.')
    s['proposal']=p;event(s,'edit_proposed',operation=op)

def say(s,a):
    text=a.text.strip()
    if not text:raise HTTPException(422,'Enter a message')
    append(s,'Farmer',text,s['selected_refs'],'user')
    lower=text.lower()
    if re.search(r'\b(reserve|keep|free)\b',lower) and ('bed' in lower or any(r.startswith('bed:') for r in s['selected_refs'])):
        if re.search(r"\b(do not|don't|don’t|never|not)\b",lower):
            append(s,'Planner','I have not proposed a reservation. Please clarify whether you want to discard a pending proposal or describe a different reservation.');event(s,'clarification',reason='negated_reservation');return
        matches=re.findall(r'\bbed\s*0?(\d{1,2})\b',lower)
        if len(matches)>1 or re.search(r'\b(?:and|or)\s+\d',lower):
            append(s,'Planner','Several beds were named. Select one bed and its interval for each proposal; no bed has been chosen automatically.');event(s,'clarification',reason='multiple_beds');return
        ids=[f'bed-{int(matches[0]):02d}'] if matches else [r[4:] for r in s['selected_refs'] if r.startswith('bed:')]
        if len(ids)!=1:append(s,'Planner','Which bed do you mean? Select one bed, then specify a start and end date.');event(s,'clarification',reason='bed_reference');return
        propose(s,Action(action='propose',revision=a.revision,operation='reserve_bed',bed_id=ids[0]));return
    if any(w in lower for w in ['unconfirmed','confirms','confirmed']):
        if re.search(r"\b(do not|don't|don’t|never)\b",lower):
            append(s,'Planner','Please choose the intended order confirmation state explicitly. I will not infer it from a negated instruction.');event(s,'clarification',reason='negated_order_action');return
        ids=[r[6:] for r in s['selected_refs'] if r.startswith('order:')]
        if 'additional' in lower:ids=['research-extra-order']
        if len(ids)!=1:append(s,'Planner','Which order do you mean? Select one order; confirmation changes its booked commitment.');event(s,'clarification',reason='order_reference');return
        propose(s,Action(action='propose',revision=a.revision,operation='order_status',order_id=ids[0],confirmed=not bool(re.search(r"unconfirmed|not\s+(?:yet\s+)?confirmed|hasn['’]?t\s+confirmed",lower))));return
    if 'labour' in lower or 'labor' in lower:
        if 'without extra' in lower or 'no extra' in lower:
            propose(s,Action(action='propose',revision=a.revision,operation='labour',labour_percent=100));return
        amounts=re.findall(r'\b(\d{1,3})\s*(?:%|percent)',lower)
        if len(amounts)==1 and 50<=int(amounts[0])<=100 and not re.search(r"\b(by|not|don't|don’t|never)\b",lower):
            propose(s,Action(action='propose',revision=a.revision,operation='labour',labour_percent=int(amounts[0])));return
        append(s,'Profit','Which labour ceiling should the research scenario use? Say, for example, “Use 75% labour”, from 50–100 percent of the declared allowance. This sets a ceiling, not a percentage reduction.');event(s,'clarification',reason='labour_value');return
    if any(w in lower for w in ['rain','indoors','indoor','assumption','challenge']):
        challenge(s,a);return
    if any(w in lower for w in ['these','this batch','that delivery','later delivery']) and not s['selected_refs']:
        append(s,'Planner','Select the beds, crops or orders you mean. I will not guess which objects your question refers to.');event(s,'clarification',reason='missing_context');return
    current=result_current(s)
    if not current:
        append(s,a.advisor,'Ask the numerical tool to calculate this frozen version before discussing quantities. Use Calculate plan; dialogue alone does not run analysis.');return
    if any(w in lower for w in ['why','evidence','compare','cover','risk','less','plan']):
        append(s,a.advisor,'Inspect the same-policy comparison and allocation dates below. Quantities come from the completed numerical tool; selected objects are references, not a claim of per-order fulfilment.',s['selected_refs']);event(s,'explanation_requested',advisor=a.advisor,result_version=current['version']);return
    append(s,'Planner','This scripted research interpreter supports reserving a bed, changing order confirmation, labour limits and evidence challenges. Use an action control or rephrase; this is not an unrestricted AI answer.')
    event(s,'clarification',reason='unsupported_intent')

def challenge(s,a):
    text=a.text or 'Why would outdoor rainfall affect this sheltered crop?'
    category='rainfall' if any(word in text.lower() for word in ['rain','indoor','shelter']) else 'other'
    if s.get('challenge'):s.setdefault('challenge_history',[]).append(deepcopy(s['challenge']))
    s['challenge']=dict(id=secrets.token_hex(12),status='unresolved',category=category,text=text,input_version=s['input_version'])
    s['chosen']=None
    s['milestones'].pop('chosen',None)
    s['milestones'].pop('challenge',None)
    if category=='rainfall':
        append(s,'Weather','The declared system is sheltered hydroponic. Outdoor rainfall is public context, not a numerical yield input in this model. A rainfall-based yield claim would be unsupported.',['evidence:weather-boundary'])
    else:
        append(s,'Planner','This scripted study has no verified answer to that challenge. Keep it unresolved or reject the recommendation; do not treat a stock reply as evidence.')
    append(s,'Planner','Review the evidence and record whether the specific challenge was resolved. Agreement between advisers is not evidence.')
    event(s,'assumption_challenged',category=category)


def apply(s,a):
    p=s['proposal']
    if not p or p['base_version']!=s['input_version']:raise HTTPException(409,'No current proposal; create it again against this version')
    inputs=deepcopy(s['inputs'])
    if p['operation']=='reserve_bed':
        start=str(a.start_date) if a.start_date else p.get('start_date');end=str(a.end_date) if a.end_date else p.get('end_date')
        if not start or not end:raise HTTPException(422,'Specify both reservation dates')
        item=dict(bed_id=p['bed_id'],start_date=start,end_date=end)
        inputs['reservations']=[r for r in inputs['reservations'] if r['bed_id']!=p['bed_id']]+[item]
    elif p['operation']=='order_status':
        ids=set(inputs['unconfirmed_order_ids']);ids.discard(p['order_id']) if p['confirmed'] else ids.add(p['order_id']);inputs['unconfirmed_order_ids']=sorted(ids)
    else:inputs['labour_percent']=p['labour_percent']
    from packages.planner.research import validate_research_inputs
    try:validate_research_inputs(Farm.model_validate(s['farm']),inputs['reservations'],inputs['unconfirmed_order_ids'],inputs['labour_percent'])
    except ValueError as exc:raise HTTPException(422,str(exc))
    s['inputs']=inputs;s['input_version']+=1;s['proposal']=None;s['chosen']=None;s['pending_turns']=[]
    s['milestones'].pop('chosen',None)
    if s.get('challenge'):
        s.setdefault('challenge_history',[]).append(deepcopy(s['challenge']))
        s['challenge']=dict(s['challenge'],id=secrets.token_hex(12),status='unresolved',input_version=s['input_version'],revalidation_of=s['challenge'].get('id'))
        s['milestones'].pop('challenge',None)
        append(s,'Planner','The input changed. Review the challenge again against this new version before choosing.')
    append(s,'Planner','The edit is applied to a new research version. Earlier results remain inspectable but cannot be selected as the current plan.')
    event(s,'inputs_changed',operation=p['operation']);s['milestones'][p['operation']]=True


def new_session(body):
    farm=synthetic_farm();farm.orders.append(Order(id='research-extra-order',crop_id='lettuce',booked_at=farm.cutoff,due_date=farm.planning_date+timedelta(days=48),quantity_kg=18,price_sgd_per_kg=9))
    s=dict(id=secrets.token_hex(16),created_at=now(),revision=0,input_version=1,schema_version=VERSION,concept=body.concept,steering=body.steering,selection_mode='chips',animation='static',farm=farm.model_dump(mode='json'),inputs=dict(reservations=[],unconfirmed_order_ids=[],labour_percent=100),selected_refs=[],proposal=None,challenge=None,chosen=None,messages=[],pending_turns=[],results=[],events=[],milestones={},inference_calls=0,dialogue_mode='scripted_research',operational_execution=False)
    s.update(workflow_type='scripted_research',inference_origin='local_rules',model_call_status='not_called',numerical_calculation_status='not_run')
    from services.api.provenance import runtime_provenance
    s['runtime_provenance']=runtime_provenance()
    append(s,'Planner','Welcome to the council study. Dialogue here is scripted; the planner calculates actual synthetic outcomes. Ask for a plan, reserve Bed 4, change the additional order, challenge an assumption and choose a simulated result.')
    event(s,'session_started',concept=body.concept);return s


def pending(store):
    with store.connection() as c:return c.execute(select(JOBS.c.tenant_id,JOBS.c.id).where(JOBS.c.status=='QUEUED')).all()

def recover(store):
    with store.connection(write=True) as c:c.execute(update(JOBS).where(JOBS.c.status=='RUNNING').values(status='QUEUED'))

def execute(store,tenant,id):
    with store.connection(write=True) as c:
        if not c.execute(update(JOBS).where(JOBS.c.id==id,JOBS.c.tenant_id==tenant,JOBS.c.status=='QUEUED').values(status='RUNNING')).rowcount:return
        j=c.execute(select(JOBS.c.payload).where(JOBS.c.id==id,JOBS.c.tenant_id==tenant)).scalar_one()
    baseline_record=None
    class CalculationCancelled(Exception):pass
    def check_cancelled():
        with store.connection() as c:
            latest=c.execute(select(JOBS.c.payload).where(JOBS.c.id==id,JOBS.c.tenant_id==tenant)).scalar_one()
        if latest.get('cancellation_requested'):raise CalculationCancelled()
    try:
        check_cancelled()
        from packages.planner.research import calculate_research
        from packages.models import MODEL_VERSION
        from packages.planner.engine import VERSION as PLANNER_VERSION
        if j.get('schema_version')!=VERSION or j.get('forecast_version')!=MODEL_VERSION or j.get('planner_version')!=PLANNER_VERSION:raise ValueError('Unsupported frozen numerical version')
        if content_hash(dict(farm=j['farm'],inputs=j['inputs'],version=VERSION))!=j['input_hash']:raise ValueError('Frozen research input hash mismatch')
        existing=get_session(store,tenant,j['session_id'])
        if j['version']>1 and not any(r['version']==1 and r['status']=='COMPLETED' for r in existing['results']):
            original=dict(reservations=[],unconfirmed_order_ids=[],labour_percent=100)
            baseline_record=dict(version=1,status='COMPLETED',input_hash=content_hash(dict(farm=j['farm'],inputs=original,version=VERSION)),inputs=original,calculation=calculate_research(Farm.model_validate(j['farm']),**original),completed_at=now(),origin='unchanged study reference')
        check_cancelled()
        result=calculate_research(Farm.model_validate(j['farm']),**j['inputs'])
        record=dict(version=j['version'],status='COMPLETED',input_hash=j['input_hash'],inputs=j['inputs'],calculation=result,completed_at=now())
    except Exception as exc:
        record=dict(version=j['version'],status='CANCELLED' if isinstance(exc,CalculationCancelled) else 'FAILED',input_hash=j['input_hash'],inputs=j['inputs'],error='Numerical calculation cancelled; frozen inputs are preserved.' if isinstance(exc,CalculationCancelled) else f'Numerical calculation failed ({type(exc).__name__}); frozen inputs are preserved.')
    with store.transaction(tenant) as c:
        s=get_session(store,tenant,j['session_id'])
        latest=c.execute(select(JOBS.c.payload).where(JOBS.c.id==id,JOBS.c.tenant_id==tenant)).scalar_one()
        if latest.get('cancellation_requested'):
            baseline_record=None
            record=dict(version=j['version'],status='CANCELLED',input_hash=j['input_hash'],inputs=j['inputs'],error='Numerical calculation cancelled; computed output was not applied.')
        if baseline_record:s['results']=[r for r in s['results'] if r['version']!=1]+[baseline_record]
        s['results']=sorted([r for r in s['results'] if r['version']!=j['version']]+[record],key=lambda r:r['version'])
        s['revision']+=1
        if j['version']==s['input_version']:
            s['numerical_calculation_status']=record['status'].lower()
            if record['status']=='COMPLETED':
                s['milestones']['calculated']=True
                earlier=sorted([r for r in s['results'] if r['version']<j['version'] and r['status']=='COMPLETED'],key=lambda x:x['version'])
                previous=earlier[-1]['inputs'] if earlier else None
                turns=[]
                if previous is None or previous['reservations']!=j['inputs']['reservations']:
                    turns.append(dict(speaker='Production',text='Bed occupancy changed or needs its first review. Allocations preserve existing batches and test reservations against new occupancy.',refs=[f"bed:{r['bed_id']}" for r in j['inputs']['reservations']]))
                if previous is None or previous['unconfirmed_order_ids']!=j['inputs']['unconfirmed_order_ids']:
                    turns.append(dict(speaker='Demand',text='Booked commitments need review. Unconfirmed orders are excluded from booked demand; the separate statistical baseline may still predict unbooked demand.',refs=['order:research-extra-order']))
                if previous is not None and previous['labour_percent']!=j['inputs']['labour_percent']:
                    turns.append(dict(speaker='Profit',text='The labour ceiling changed. Compare labour and margin from the numerical results; unused roles do not repeat unchanged findings.',refs=[]))
                turns.append(dict(speaker='Planner',text='The comparison is ready. Only roles with changed inputs or an initial review contributed. Inspect one policy, its violations and numerical differences before choosing this simulated version.',refs=[]))
                s['pending_turns']=turns
                append(s,'Tool','Calculation completed. Numerical results below belong to this frozen input version.',kind='tool')
            else:append(s,'Tool',record['error'],kind='tool')
        else:append(s,'Tool','An earlier calculation completed. Its result is archived; current inputs were not overwritten.',kind='tool')
        event(s,'tool_completed' if record['status']=='COMPLETED' else 'tool_failed',result_version=j['version'])
        c.execute(update(JOBS).where(JOBS.c.id==id,JOBS.c.tenant_id==tenant).values(status=record['status']));save(store,tenant,s)


def install_routes(app,tenant):
    def key(request):
        k=request.headers.get('Idempotency-Key','')
        if not k or len(k)>128:raise HTTPException(422,'Idempotency-Key required, maximum 128 characters')
        return k
    def owned(t,id):
        s=get_session(app.state.store,t,id)
        if not s:raise HTTPException(404,'Research session not found')
        return deepcopy(s)
    @app.get('/api/v1/council-research')
    def listing(request:Request):
        t=tenant(request)
        with app.state.store.connection() as c:rows=c.execute(select(SESSIONS.c.payload).where(SESSIONS.c.tenant_id==t).limit(30)).scalars().all()
        return dict(sessions=[{k:s[k] for k in ['id','created_at','concept','input_version','revision']} for s in sorted(rows,key=lambda x:x['created_at'],reverse=True)])
    @app.post('/api/v1/council-research',status_code=201)
    def create(body:NewSession,request:Request):
        t=tenant(request);k=key(request);store=app.state.store;h=content_hash(body)
        with store.transaction(t) as c:
            old=c.execute(select(SESSIONS).where(SESSIONS.c.tenant_id==t,SESSIONS.c.idempotency_key==k)).mappings().first()
            if old:
                if old['request_hash']!=h:raise HTTPException(409,'Idempotency key changed')
                return old['payload']
            if len(c.execute(select(SESSIONS.c.id).where(SESSIONS.c.tenant_id==t)).all())>=30:raise HTTPException(429,'Research session limit reached for this temporary workspace')
            s=new_session(body);c.execute(SESSIONS.insert().values(id=s['id'],tenant_id=t,idempotency_key=k,request_hash=h,payload=s));record_revision(store,t,s);return s
    @app.get('/api/v1/council-research/report')
    def report(request:Request):
        tenant(request)
        from pathlib import Path
        root=Path(__file__).resolve().parents[2]
        documents=[]
        for title,path in [('Research synthesis','docs/research/council-participation.md'),('Latest-release audit','reports/v7/baseline_audit.md'),('Concept evaluation and recommendations','reports/v7/recommendations.md')]:
            file=root/path
            if file.is_file():documents.append(dict(title=title,markdown=file.read_text()[:90000]))
        sources=[
            ('Co-STORM · Jiang et al., 2024','https://aclanthology.org/2024.emnlp-main.554/'),
            ('Façade · Mateas and Stern, 2005','https://users.soe.ucsc.edu/~michaelm/publications/mateas-aiide2005.pdf'),
            ('DataBreeze · Srinivasan et al., 2020','https://arxiv.org/abs/2004.10428'),
            ('TalkToModel · Slack et al., 2023','https://arxiv.org/abs/2207.04154'),
            ('Grounded explanation · Madumal et al., 2019','https://arxiv.org/abs/1903.02409'),
            ('Mixed initiative · Horvitz, 1999','https://erichorvitz.com/chi99horvitz.pdf'),
            ('Animated transitions · Heer and Robertson, 2007','https://www.microsoft.com/en-us/research/publication/animated-transitions-in-statistical-data-graphics/'),
            ('W3C · Animation from interactions','https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html'),
        ]
        return dict(title='Playable council research',documents=documents,sources=[dict(title=t,url=u) for t,u in sources],screenshots=[dict(title='Baseline '+name.replace('.png','').replace('-',' '),url='/research-evidence/'+name) for name in ['farm-board-390.png','bed-conversation-390.png','scenario-lab-390.png','bed-conversation-1280.png']])
    @app.get('/api/v1/council-research/{id}/history')
    def history(id:str,request:Request,after:int=-1,limit:int=20):
        t=tenant(request);owned(t,id)
        if after < -1 or not 1<=limit<=50:raise HTTPException(422,'Invalid history cursor or page size')
        with app.state.store.connection() as c:
            rows=c.execute(select(HISTORY.c.revision,HISTORY.c.payload).where(HISTORY.c.session_id==id,HISTORY.c.tenant_id==t,HISTORY.c.revision>after).order_by(HISTORY.c.revision).limit(limit+1)).all()
        page=rows[:limit]
        return dict(revisions=[dict(revision=r,payload=p) for r,p in page],next_cursor=page[-1][0] if len(rows)>limit else None,origin='recorded_scripted_and_numerical_events',inference_triggered=False)
    @app.get('/api/v1/council-research/{id}')
    def detail(id:str,request:Request):return owned(tenant(request),id)
    @app.post('/api/v1/council-research/{id}/actions')
    def action(id:str,body:Action,request:Request):
        t=tenant(request);k=key(request);store=app.state.store;h=content_hash(dict(id=id,body=body.model_dump(mode='json')))
        with store.transaction(t) as c:
            s=owned(t,id)
            old=c.execute(select(ACTIONS).where(ACTIONS.c.tenant_id==t,ACTIONS.c.idempotency_key==k)).mappings().first()
            if old:
                if old['request_hash']!=h:raise HTTPException(409,'Idempotency key changed')
                with store.connection() as receipts:
                    revision=receipts.execute(select(RECEIPTS.c.revision).where(RECEIPTS.c.action_id==old['id'],RECEIPTS.c.tenant_id==t)).scalar_one_or_none()
                return revision_snapshot(store,t,id,revision) if revision is not None else dict(s,replay_scope='legacy_current_state')
            if body.revision!=s['revision']:raise HTTPException(409,'Research session changed; refresh and review before retrying')
            if len(c.execute(select(ACTIONS.c.id).where(ACTIONS.c.session_id==id,ACTIONS.c.tenant_id==t)).all())>=400:raise HTTPException(429,'Research action limit reached; start a fresh study')
            a=body.action
            if a=='select':
                if any(r not in all_refs(s) for r in body.refs):raise HTTPException(422,'Selection is outside this frozen study')
                s['selected_refs']=list(dict.fromkeys(body.refs));event(s,'selection_changed',refs=s['selected_refs'])
            elif a=='say':
                if s['steering']=='checkpoints' and s['pending_turns']:raise HTTPException(409,'Use Pause discussion to intervene at this checkpoint')
                say(s,body)
            elif a=='propose':propose(s,body)
            elif a=='apply':apply(s,body)
            elif a=='discard':s['proposal']=None;event(s,'proposal_discarded')
            elif a=='challenge':challenge(s,body)
            elif a=='resolve':
                if not s['challenge'] or body.resolution is None:raise HTTPException(422,'Open a challenge and choose its resolution')
                if s['challenge']['input_version']!=s['input_version']:raise HTTPException(409,'Challenge belongs to an earlier input version; challenge the current result again')
                if body.resolution=='corrected' and s['challenge'].get('category')!='rainfall':raise HTTPException(409,'This challenge has no verified resolution in the scripted study')
                if body.resolution!='evidence':s['challenge']['status']=body.resolution
                s['chosen']=None
                s['milestones'].pop('chosen',None)
                append(s,'Planner','Challenge status recorded. Unresolved or rejected recommendations cannot be chosen; evidence inspection alone does not resolve a challenge.')
                event(s,'challenge_reviewed',resolution=body.resolution);s['milestones']['challenge']=True
            elif a=='configure':
                for field in ['concept','steering','selection_mode','animation']:
                    if getattr(body,field) is not None:s[field]=getattr(body,field)
                event(s,'presentation_changed',concept=s['concept'],steering=s['steering'])
            elif a=='stop':s['pending_turns']=[];append(s,'Planner','Further scripted contributions stopped. Any numerical calculation already running continues and remains inspectable.');event(s,'discussion_stopped')
            elif a=='next':
                if s['pending_turns']:
                    turn=s['pending_turns'].pop(0);append(s,**turn);event(s,'scripted_turn_shown',speaker=turn['speaker'])
            elif a=='cancel_calculation':
                row=c.execute(select(JOBS).where(JOBS.c.session_id==id,JOBS.c.tenant_id==t,JOBS.c.version==s['input_version'])).mappings().first()
                if row is None:raise HTTPException(409,'No current numerical calculation exists')
                if row['status'] in ('QUEUED','RUNNING'):
                    job=dict(row['payload'],cancellation_requested=True)
                    status='CANCELLED' if row['status']=='QUEUED' else 'RUNNING'
                    c.execute(update(JOBS).where(JOBS.c.id==row['id'],JOBS.c.tenant_id==t).values(status=status,payload=job))
                    if status=='CANCELLED':
                        for result in s['results']:
                            if result['version']==s['input_version']:result.update(status='CANCELLED',error='Numerical calculation cancelled before claim.')
                    s['numerical_calculation_status']='cancelled' if status=='CANCELLED' else 'cancellation_requested'
                    append(s,'Tool','Cancellation requested. A calculation in progress stops at the next safe numerical boundary; its result cannot be applied.',kind='tool')
                    event(s,'calculation_cancellation_requested',result_version=s['input_version'])
                else:event(s,'calculation_cancellation_noop',status=row['status'])
            elif a=='retry_calculation':
                row=c.execute(select(JOBS).where(JOBS.c.session_id==id,JOBS.c.tenant_id==t,JOBS.c.version==s['input_version'])).mappings().first()
                if not row or row['status'] not in ('FAILED','CANCELLED'):raise HTTPException(409,'Only a failed or cancelled current calculation can be retried')
                if c.execute(select(JOBS.c.id).where(JOBS.c.tenant_id==t,JOBS.c.status.in_(['QUEUED','RUNNING']))).first():raise HTTPException(409,'A research calculation is already active')
                job=deepcopy(row['payload']);attempt=job.get('attempt',1)+1
                if attempt>3:raise HTTPException(429,'Three attempts per numerical version maximum')
                job.update(attempt=attempt,cancellation_requested=False)
                c.execute(update(JOBS).where(JOBS.c.id==row['id'],JOBS.c.tenant_id==t).values(status='QUEUED',payload=job))
                for result in s['results']:
                    if result['version']==s['input_version']:
                        result.update(status='QUEUED',attempt=attempt)
                        result.pop('error',None)
                s['numerical_calculation_status']='queued'
                event(s,'calculation_retried',result_version=s['input_version'],attempt=attempt)
            elif a=='run':
                if s['proposal']:raise HTTPException(409,'Apply or discard the pending proposal before calculating')
                existing_job=c.execute(select(JOBS.c.id).where(JOBS.c.session_id==id,JOBS.c.version==s['input_version'])).first()
                if existing_job:
                    # A no-op still records its exact response revision for retries.
                    s['revision']+=1;event(s,'existing_calculation_reused',result_version=s['input_version'])
                    action_id=secrets.token_hex(16)
                    c.execute(ACTIONS.insert().values(id=action_id,session_id=id,tenant_id=t,idempotency_key=k,request_hash=h))
                    c.execute(RECEIPTS.insert().values(action_id=action_id,tenant_id=t,revision=s['revision']))
                    save(store,t,s);return s
                if c.execute(select(JOBS.c.id).where(JOBS.c.tenant_id==t,JOBS.c.status.in_(['QUEUED','RUNNING']))).first():raise HTTPException(409,'One research calculation may run per workspace; wait for completion')
                if len(s['results'])>=12:raise HTTPException(429,'Twelve numerical versions per study; start a fresh study')
                from packages.models import MODEL_VERSION
                from packages.planner.engine import VERSION as PLANNER_VERSION
                j=dict(schema_version=VERSION,forecast_version=MODEL_VERSION,planner_version=PLANNER_VERSION,id=secrets.token_hex(16),session_id=id,version=s['input_version'],farm=s['farm'],inputs=deepcopy(s['inputs']),input_hash=content_hash(dict(farm=s['farm'],inputs=s['inputs'],version=VERSION)),attempt=1,cancellation_requested=False)
                s['numerical_calculation_status']='queued'
                c.execute(JOBS.insert().values(id=j['id'],tenant_id=t,session_id=id,version=j['version'],status='QUEUED',payload=j));s['results'].append(dict(version=j['version'],status='QUEUED',input_hash=j['input_hash'],inputs=j['inputs']));append(s,'Tool','Numerical work queued. Farm time does not advance while the worker calculates.',kind='tool');event(s,'tool_queued',result_version=j['version'])
            elif a=='choose':
                r=result_current(s)
                if body.result_version!=s['input_version'] or not r:raise HTTPException(409,'Calculate and review the current version first')
                if s['proposal'] or (s['challenge'] and (s['challenge']['status']!='corrected' or s['challenge']['input_version']!=s['input_version'])):raise HTTPException(409,'Resolve pending edits and challenges before choosing')
                chosen=eligible(s,r,body.policy)
                if not chosen:raise HTTPException(409,'This policy has unresolved numerical violations or is infeasible')
                s['chosen']=dict(version=s['input_version'],policy=body.policy,strategy_id=chosen['id'],input_hash=r['input_hash'],actor='research-participant',simulation_only=True,chosen_at=now());append(s,'Planner','You chose this version for the study. No operational commitment or main-farm change was made.');event(s,'simulated_version_chosen',policy=body.policy);s['milestones']['chosen']=True
            s['revision']+=1
            action_id=secrets.token_hex(16)
            c.execute(ACTIONS.insert().values(id=action_id,session_id=id,tenant_id=t,idempotency_key=k,request_hash=h))
            c.execute(RECEIPTS.insert().values(action_id=action_id,tenant_id=t,revision=s['revision']))
            save(store,t,s);return s
