"""Bounded, tenant-owned data exploration. No inference and no caller-selected paths."""
from __future__ import annotations

from copy import deepcopy
import csv
from datetime import date, timedelta
import io
import json
import secrets
from typing import Literal

from fastapi import HTTPException, Query, Request, Response
from pydantic import Field, model_validator
from sqlalchemy import Column, ForeignKey, JSON, String, Table, UniqueConstraint, select

from packages.contracts import Farm, Strict, content_hash
from packages.fixtures import GENERATOR_VERSION, GeneratorSettings, synthetic_farm
from packages.models import MODEL_VERSION, ForecastSettings, forecast
from services.api.store import metadata, farms, runs, now
from services.api.views import farm_view

snapshots = Table('explorer_snapshots', metadata,
    Column('id', String, primary_key=True),
    Column('tenant_id', String, ForeignKey('tenants.id'), nullable=False),
    Column('idempotency_key', String, nullable=False),
    Column('request_hash', String, nullable=False),
    Column('content_hash', String, nullable=False),
    Column('payload', JSON, nullable=False),
    UniqueConstraint('tenant_id', 'idempotency_key'))

Dataset = Literal['beds','recipes','batches','history','orders','inventory','resources','forecast','allocations','ledger','weekly']
Policy = Literal['Lean','Balanced','Resilient']

class PreviewRequest(Strict):
    generator_settings: GeneratorSettings = Field(default_factory=GeneratorSettings)
    forecast_settings: ForecastSettings = Field(default_factory=ForecastSettings)

class SaveRequest(PreviewRequest):
    name: str = Field(default='Playground dataset', min_length=1, max_length=80)

class Filters(Strict):
    snapshot_id: str = Field(default='reference', min_length=1, max_length=100)
    dataset: Dataset = 'history'
    crop_id: Literal['caixin','pak_choi','kailan','lettuce'] | None = None
    start: date | None = None
    end: date | None = None
    q: str = Field(default='', max_length=100)
    sort: str = Field(default='id', max_length=60)
    descending: bool = False
    page: int = Field(default=1, ge=1, le=1000)
    page_size: int = Field(default=25, ge=1, le=100)
    policy: Policy = 'Balanced'
    @model_validator(mode='after')
    def ordered(self):
        if self.start and self.end and self.start > self.end:
            raise ValueError('Start date must precede end date')
        return self

# Only these flat fields are returned/exported; imported unknown keys cannot leak.
COLUMNS = {
    'beds': 'id name area_m2 system',
    'recipes': 'id crop_id system nursery_days grow_days sanitation_days density_per_m2 marketable_kg_per_m2 cost_sgd_per_m2 sow_labour_hours_per_m2 harvest_labour_hours_per_kg shelf_life_days validation_status origin',
    'batches': 'id bed_id recipe_id crop_id date sow_date transplant_date harvest_date expected_marketable_kg executed origin',
    'history': 'id crop_id date week available_at ordered_kg origin available_at_cutoff',
    'orders': 'id crop_id date booked_at due_date quantity_kg cancelled_kg net_quantity_kg price_sgd_per_kg origin available_at_cutoff',
    'inventory': 'id crop_id date quantity_kg harvested_date expires_date origin',
    'resources': 'id nursery_sites labour_hours_per_week cash_sgd',
    'forecast': 'id crop_id date week confirmed_kg residual_kg expected_kg price_sgd_per_kg history_periods history_record_ids order_record_ids',
    'allocations': 'id crop_id bed_id recipe_id date sow_date transplant_date harvest_date area_m2 expected_kg executed',
    'ledger': 'id date opening_kg harvest_kg demand_kg delivered_kg shortfall_kg disposed_kg waste_kg closing_kg balance_error',
    'weekly': 'id date week demand_kg harvest_kg delivered_kg shortfall_kg waste_kg labour_hours labour_capacity_hours nursery_peak_sites nursery_capacity_sites occupied_bed_days available_bed_days',
}
DESCRIPTIONS = {
    'id':'Stable record identifier in this frozen dataset.',
    'crop_id':'Links to the crop on its declared recipe.',
    'bed_id':'Links to beds.id, the growing space occupied by this batch or allocation.',
    'recipe_id':'Links to recipes.id, preserving declared biological timing and yield.',
    'date':'Singapore civil date for this record or the start of a weekly interval.',
    'available_at':'Time this historical input became available; values after cutoff are excluded from the forecast.',
    'available_at_cutoff':'Whether this input can contribute to the forecast at the frozen cutoff.',
    'booked_at':'Order booking timestamp; only commitments known by cutoff contribute.',
    'ordered_kg':'Generated historical weekly demand, not measured sales.',
    'quantity_kg':'Gross recorded quantity. Orders may have cancellations.',
    'net_quantity_kg':'Quantity minus cancelled kilograms.',
    'expected_marketable_kg':'Declared fresh marketable yield, already including packout.',
    'expected_kg':'Calculated demand (confirmed plus residual) or declared allocation yield; not observed outcomes.',
    'confirmed_kg':'Net orders booked by cutoff for this crop and delivery date.',
    'residual_kg':'max(0, EWMA baseline minus booked weekly orders), added once at week end.',
    'history_record_ids':'Contributing history IDs with availability on or before cutoff.',
    'order_record_ids':'Contributing orders known by cutoff in this planning week.',
    'labour_hours':'Reserved labour for this week, including the high-yield harvest allowance.',
    'labour_hours_per_week':'Declared weekly labour capacity.',
    'nursery_sites':'Declared simultaneous nursery site capacity.',
    'cash_sgd':'Declared total planning-horizon cash capacity.',
    'shortage_kg':'Unfilled demand on its due date; later harvest cannot fill it retroactively.',
    'waste_kg':'Expired stock in the simulated FIFO inventory ledger.',
    'executed':'Whether sowing is already committed at the cutoff.',
    'origin':'Source classification; fixture records remain synthetic.',
}

def field_info(dataset):
    def unit(key):
        if key.endswith('_kg_per_m2'): return 'kg/m²'
        if key.endswith('_sgd_per_kg'): return 'SGD/kg'
        if key.endswith('_sgd_per_m2'): return 'SGD/m²'
        if key.endswith('_hours_per_m2'): return 'hours/m²'
        if key.endswith('_hours_per_kg'): return 'hours/kg'
        if key.endswith('_kg'): return 'kg'
        if key.endswith('_sgd'): return 'SGD'
        if key.endswith('_m2'): return 'm²'
        if 'hours' in key: return 'hours/week' if key.endswith('_per_week') else 'hours'
        if key.endswith('_days'): return 'days'
        if 'sites' in key: return 'sites'
        return None
    return [dict(key=k,label=k.replace('_',' ').capitalize(),unit=unit(k),description=DESCRIPTIONS.get(k,k.replace('_',' ').capitalize()+(' in the declared recipe.' if dataset=='recipes' else ' in this frozen record.'))) for k in COLUMNS[dataset].split()]

def reference_payload():
    farm=synthetic_farm().model_dump(mode='json')
    config=GeneratorSettings().model_dump(mode='json'); settings=ForecastSettings().model_dump(mode='json')
    return dict(id='reference',name='Original generated dataset',kind='reference',input_snapshot=farm,generator_settings=config,generator_version=GENERATOR_VERSION,forecast_settings=settings,forecast_version=MODEL_VERSION,cutoff=farm['cutoff'],provenance=dict(origin='synthetic',description='Versioned reference fixture. Engineering assumptions, not measured farm outcomes.',comparison_root='playground:'+dataset_hash(farm,config,settings)),content_hash=dataset_hash(farm,config,settings))

def dataset_hash(farm, generator, settings, generator_version=GENERATOR_VERSION, forecast_version=MODEL_VERSION):
    return content_hash(dict(input_snapshot=farm,generator_settings=generator,generator_version=generator_version,forecast_settings=settings,forecast_version=forecast_version))


def validate_saved_payload(payload, recorded_hash):
    try:
        if payload['snapshot_schema_version']!='explorer-snapshot-v1':raise ValueError('Unsupported snapshot schema')
        Farm.model_validate(payload['input_snapshot'])
        GeneratorSettings.model_validate(payload['generator_settings'])
        ForecastSettings.model_validate(payload['forecast_settings'])
        actual=dataset_hash(payload['input_snapshot'],payload['generator_settings'],payload['forecast_settings'],payload['generator_version'],payload['forecast_version'])
        if actual!=payload['content_hash'] or actual!=recorded_hash:
            raise ValueError('Dataset hash mismatch')
        if content_hash(payload['forecast'])!=payload['forecast_hash']:
            raise ValueError('Frozen forecast mismatch')
        Farm.model_validate(payload['reference_snapshot'])
        reference=dataset_hash(payload['reference_snapshot'],payload['reference_generator_settings'],payload['reference_forecast_settings'],payload['reference_generator_version'],payload['reference_forecast_version'])
        if reference!=payload['reference_content_hash'] or reference!=payload['provenance']['reference_hash']:
            raise ValueError('Reference hash mismatch')
    except (ValueError,KeyError,TypeError):
        raise HTTPException(409,'Saved dataset integrity check failed; this snapshot cannot be used') from None
    return payload

def get_saved(store, tenant, id):
    if not id.startswith('saved:'):return None
    with store.connection() as c:
        row=c.execute(select(snapshots).where(snapshots.c.tenant_id==tenant,snapshots.c.id==id[6:])).mappings().first()
        return validate_saved_payload(row['payload'],row['content_hash']) if row else None

def resolve(store, tenant, id):
    if id=='reference':return reference_payload()
    if id.startswith('saved:'):
        payload=get_saved(store,tenant,id)
        if payload:return payload
    elif id.startswith('main:'):
        with store.connection() as c:
            row=c.execute(select(farms).where(farms.c.tenant_id==tenant,farms.c.id==id[5:])).mappings().first()
            if row:
                farm=row['payload']
                result=c.execute(select(runs.c.payload).where(runs.c.tenant_id==tenant)).scalars().all()
                result=next((r for r in reversed(result) if r.get('input_hash')==row['input_hash'] and r.get('strategies') and r['status'] not in ('CREATED','RUNNING')),None)
                return dict(id=id,name=f"Main farm · version {farm['version']}",kind='farm',input_snapshot=farm,content_hash=row['input_hash'],cutoff=farm['cutoff'],generator_settings=None,generator_version=None,forecast_settings={'alpha':.35},forecast_version=(result or {}).get('forecast',{}).get('model_version',MODEL_VERSION),result=result,provenance=dict(origin=farm['data_mode'],description='Owned farm import/version. Values reflect this snapshot; reference-generator assumptions may not apply.',comparison_root='farm:'+row['input_hash']))
    elif id.startswith('scenario:'):
        from services.api.scenarios import get_scenario
        s=get_scenario(store,tenant,id[9:])
        if s:
            return dict(id=id,name=s['name'],kind='scenario',input_snapshot=s['input_snapshot'],content_hash=s.get('numerical_input_hash',s['input_hash']),cutoff=s['input_snapshot']['cutoff'],generator_settings=s.get('generator_settings'),generator_version=s.get('generator_version'),forecast_settings=s.get('forecast_settings',{'alpha':.35}),forecast_version=s.get('forecast_version',MODEL_VERSION),scenario_id=s['id'],status=s['status'],result=s.get('result'),provenance=dict(origin='synthetic',description='Frozen numerical experiment. Results are simulated, never actual farm outcomes.',baseline_hash=s['baseline_hash'],comparison_root=s.get('comparison_root','farm:'+s['baseline_hash'])))
    raise HTTPException(404,'Explorer snapshot not found')

def record_sets(farm, computed, result=None, policy='Balanced'):
    raw=farm.model_dump(mode='json'); recipes={r.id:r for r in farm.recipes}
    records={k:deepcopy(raw.get(k,[])) for k in COLUMNS}
    records['resources']=[dict(id='resources',**raw['resources'])]
    for row in records['batches']:
        row.update(crop_id=recipes[row['recipe_id']].crop_id,date=row['harvest_date'])
    for i,row in enumerate(records['history']):
        row.update(id=f"history:{row['crop_id']}:{row['week']}:{i}",date=row['week'],available_at_cutoff=farm.history[i].available_at<=farm.cutoff and farm.history[i].week<farm.planning_date)
    for row in records['orders']:
        row.update(date=row['due_date'],net_quantity_kg=float(row['quantity_kg'])-float(row['cancelled_kg']),available_at_cutoff=True)
    for row in records['inventory']:row['date']=row['harvested_date']
    records['forecast']=deepcopy(computed['demand'])
    for row in records['forecast']:
        row.update(id=f"forecast:{row['crop_id']}:{row['date']}",history_record_ids=[h['id'] for h in records['history'] if h['crop_id']==row['crop_id'] and h['available_at_cutoff']],order_record_ids=[o['id'] for o in records['orders'] if o['crop_id']==row['crop_id'] and (date.fromisoformat(o['due_date'])-farm.planning_date).days//7==row['week']])
    chosen=next((s for s in (result or {}).get('strategies',[]) if s['name']==policy),None)
    if chosen:
        records['allocations']=deepcopy(chosen['allocations'])
        for row in records['allocations']:row['date']=row['harvest_date']
        records['ledger']=deepcopy(chosen['ledger'])
        for row in records['ledger']:row.update(id='ledger:'+row['date'],shortfall_kg=round(row['demand_kg']-row['delivered_kg'],6),waste_kg=row['disposed_kg'])
        records['weekly']=deepcopy(chosen['weekly'])
        from packages.planner.engine import resource_usage
        nursery,labour,occupancy,_=resource_usage(farm,chosen['allocations'])
        for i,row in enumerate(records['weekly']):
            w=int(row.get('week',i))
            row.update(id=f'weekly:{i}',date=str(farm.planning_date+timedelta(days=7*w)),labour_hours=round(labour.get(w,0),4),labour_capacity_hours=float(farm.resources.labour_hours_per_week),nursery_peak_sites=max((nursery.get(d,0) for d in range(w*7,min(w*7+7,farm.horizon_days))),default=0),nursery_capacity_sites=farm.resources.nursery_sites,occupied_bed_days=sum(len(v) for (_,d),v in occupancy.items() if d//7==w),available_bed_days=len(farm.beds)*min(7,farm.horizon_days-7*w),waste_kg=round(sum(r['disposed_kg'] for r in records['ledger'][w*7:w*7+7]),6))
    return {k:[{f:row[f] for f in COLUMNS[k].split() if f in row} for row in rows] for k,rows in records.items()}

def detail(payload, policy='Balanced'):
    farm=Farm.model_validate(payload['input_snapshot'])
    result=payload.get('result')
    f=(result or {}).get('forecast') or payload.get('forecast') or forecast(farm,alpha=payload.get('forecast_settings',{}).get('alpha',.35))
    records=record_sets(farm,f,result,policy)
    dates=[r['date'] for rows in records.values() for r in rows if r.get('date')]
    dates += [str(farm.planning_date),str(farm.planning_date+timedelta(days=farm.horizon_days-1))]
    response={k:deepcopy(v) for k,v in payload.items() if k not in ('input_snapshot','reference_snapshot','reference_forecast_settings','reference_forecast_version','reference_content_hash','reference_generator_settings','reference_generator_version','forecast_hash')}
    response.update(farm=farm_view(farm),records=records,fields={k:field_info(k) for k in COLUMNS},forecast=f,result=result,planning_date=str(farm.planning_date),date_extent=dict(start=min(dates),end=max(dates)),counts={k:len(v) for k,v in records.items()},unsaved=payload.get('unsaved',False),inference_calls=0)
    return response

def filtered_records(value, filters):
    rows=value['records'][filters.dataset]
    fields=value['fields'][filters.dataset]
    if filters.sort not in {f['key'] for f in fields}:raise HTTPException(422,'Unknown sort field for dataset')
    # Aggregate simulation ledgers cannot truthfully be attributed to one crop.
    if filters.crop_id and filters.dataset in ('ledger','weekly'):
        rows=[]
    else:
        rows=[r for r in rows if not filters.crop_id or r.get('crop_id')==filters.crop_id or filters.dataset in ('beds','resources')]
    rows=[r for r in rows if (not filters.start or not r.get('date') or r['date']>=str(filters.start)) and (not filters.end or not r.get('date') or r['date']<=str(filters.end)) and (not filters.q or filters.q.casefold() in json.dumps(r,ensure_ascii=False).casefold())]
    def key(row):
        v=row.get(filters.sort)
        if v is None:return (0,'')
        if isinstance(v,bool):return (1,int(v))
        try:return (1,float(v))
        except (ValueError,TypeError):return (2,str(v).casefold())
    rows=sorted(rows,key=key,reverse=filters.descending)
    return rows,fields

def safe_cell(value):
    text=json.dumps(value,ensure_ascii=False) if isinstance(value,(list,dict)) else str(value if value is not None else '')
    return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r','\n')) else text

def download(rows, fields, format, metadata=None):
    if len(rows)>5000:raise HTTPException(413,'Export exceeds 5,000 records; narrow the filters')
    if format=='json':return Response(json.dumps(dict(records=rows,fields=fields,provenance=metadata),ensure_ascii=False),media_type='application/json',headers={'Content-Disposition':'attachment; filename="farmtact-data.json"'})
    out=io.StringIO(); writer=csv.writer(out); keys=[f['key'] for f in fields]
    writer.writerow(keys)
    writer.writerows([[safe_cell(row.get(k)) for k in keys] for row in rows])
    return Response(out.getvalue(),media_type='text/csv',headers={'Content-Disposition':'attachment; filename="farmtact-data.csv"'})

def install_routes(app, tenant):
    @app.get('/api/v1/data-explorer/evaluation')
    def evaluation(request:Request):
        tenant(request)
        from services.api.views import ROOT
        # Historical report only. This is not a selected-snapshot feature source.
        report=json.loads((ROOT/'reports/numerical_evaluation.json').read_text())
        return {k:report.get(k) for k in ('status','dataset_name','fixture_hash','generator_version','generator_settings','forecast_version','forecast_settings','cutoff','evaluation_scope','forecast_evaluation','validation_status','limitations')}

    @app.get('/api/v1/data-explorer/snapshots')
    def listing(request:Request):
        t=tenant(request); store=app.state.store
        ref=reference_payload()
        rows=[{k:ref[k] for k in ('id','name','kind','cutoff','content_hash')}]
        with store.connection() as c:
            versions=c.execute(select(farms).where(farms.c.tenant_id==t).order_by(farms.c.version.desc()).limit(100)).mappings().all()
            rows += [dict(id='main:'+r['id'],name=f"Main farm · version {r['version']}",kind='farm',cutoff=r['payload']['cutoff'],content_hash=r['input_hash']) for r in versions]
            saved=c.execute(select(snapshots.c.payload).where(snapshots.c.tenant_id==t)).scalars().all()
            rows += [{k:s[k] for k in ('id','name','kind','cutoff','content_hash')} for s in sorted(saved,key=lambda p:p['created_at'],reverse=True)]
            from services.api.scenarios import branches
            scenarios=c.execute(select(branches.c.payload).where(branches.c.tenant_id==t)).scalars().all()
            rows += [dict(id='scenario:'+s['id'],name=s['name'],kind='scenario',scenario_id=s['id'],status=s['status'],cutoff=s['input_snapshot']['cutoff'],content_hash=s.get('numerical_input_hash',s['input_hash'])) for s in sorted(scenarios,key=lambda s:s['created_at'],reverse=True)[:100]]
        return dict(snapshots=rows)

    @app.get('/api/v1/data-explorer/snapshots/{id}')
    def read(id:str,request:Request,policy:Policy='Balanced'):
        return detail(resolve(app.state.store,tenant(request),id),policy)

    @app.post('/api/v1/data-explorer/preview')
    def preview(body:PreviewRequest,request:Request):
        tenant(request)
        p=generated(body)
        return detail(dict(p,id='preview',name='Unsaved playground preview',kind='preview',unsaved=True))

    @app.post('/api/v1/data-explorer/snapshots',status_code=201)
    def save(body:SaveRequest,request:Request):
        t=tenant(request); store=app.state.store
        key=request.headers.get('Idempotency-Key')
        if not key or len(key)>128:raise HTTPException(422,'Idempotency-Key required, maximum 128 characters')
        fingerprint=content_hash(body)
        with store.transaction(t) as c:
            old=c.execute(select(snapshots).where(snapshots.c.tenant_id==t,snapshots.c.idempotency_key==key)).mappings().first()
            if old:
                if old['request_hash']!=fingerprint:raise HTTPException(409,'Idempotency key reused with changed dataset')
                return dict(detail(validate_saved_payload(old['payload'],old['content_hash'])),reused=True)
            existing=c.execute(select(snapshots.c.id).where(snapshots.c.tenant_id==t)).all()
            if len(existing)>=100:raise HTTPException(409,'This session already has 100 saved datasets')
            id=secrets.token_hex(16)
            p=dict(generated(body),id='saved:'+id,name=body.name,kind='playground',created_at=now())
            c.execute(snapshots.insert().values(id=id,tenant_id=t,idempotency_key=key,request_hash=fingerprint,content_hash=p['content_hash'],payload=p))
        return detail(p)

    @app.get('/api/v1/data-explorer/records')
    def records(request:Request,filters:Filters=Query()):
        value=detail(resolve(app.state.store,tenant(request),filters.snapshot_id),filters.policy)
        rows,fields=filtered_records(value,filters); offset=(filters.page-1)*filters.page_size
        return dict(records=rows[offset:offset+filters.page_size],total=len(rows),page=filters.page,page_size=filters.page_size,fields=fields,scope='farm-wide' if filters.dataset in ('ledger','weekly','resources','beds') else 'crop',content_hash=value['content_hash'])

    @app.get('/api/v1/data-explorer/series')
    def series(request:Request,filters:Filters=Query()):
        value=detail(resolve(app.state.store,tenant(request),filters.snapshot_id),filters.policy)
        rows,fields=filtered_records(value,filters)
        return dict(records=rows,fields=fields,planning_date=value['planning_date'],content_hash=value['content_hash'],scope='farm-wide' if filters.dataset in ('ledger','weekly','resources','beds') else 'crop',inference_calls=0)

    @app.get('/api/v1/data-explorer/export')
    def export(request:Request,format:Literal['csv','json']='csv',snapshot_id:str=Query(default='reference',max_length=100),dataset:Dataset='history',crop_id:Literal['caixin','pak_choi','kailan','lettuce']|None=None,start:date|None=None,end:date|None=None,q:str=Query(default='',max_length=100),sort:str=Query(default='id',max_length=60),descending:bool=False,policy:Policy='Balanced'):
        if start and end and start>end:raise HTTPException(422,'Start date must precede end date')
        filters=Filters(snapshot_id=snapshot_id,dataset=dataset,crop_id=crop_id,start=start,end=end,q=q,sort=sort,descending=descending,policy=policy)
        value=detail(resolve(app.state.store,tenant(request),snapshot_id),policy)
        rows,fields=filtered_records(value,filters)
        return download(rows,fields,format,{k:value.get(k) for k in ('id','content_hash','cutoff','generator_version','generator_settings','forecast_version','forecast_settings','provenance')})

    def public_rows(dataset,source_id,start,end,q):
        from services.api.explorer_public import public_explorer
        if start and end and start>end:raise HTTPException(422,'Start date must precede end date')
        context=public_explorer()
        if source_id and source_id not in {s['id'] for s in context['sources']}:raise HTTPException(422,'Unknown public source')
        rows=[r for r in context['datasets'][dataset] if (not source_id or r['source_id']==source_id) and (not start or r['date']>=str(start)) and (not end or r['date']<=str(end)) and (not q or q.casefold() in json.dumps(r).casefold())]
        fields=[dict(key=k,label=k.replace('_',' ').capitalize(),unit=None,description='Curated public-source '+k.replace('_',' ')) for k in dict.fromkeys(k for r in rows for k in r)]
        return rows,fields,context

    @app.get('/api/v1/data-explorer/public/records')
    def public_records(request:Request,dataset:Literal['weather_observations','weather_forecasts','trade_observations']='weather_observations',source_id:str|None=Query(default=None,max_length=20),start:date|None=None,end:date|None=None,q:str=Query(default='',max_length=100),page:int=Query(default=1,ge=1,le=1000),page_size:int=Query(default=25,ge=1,le=100)):
        tenant(request)
        rows,fields,_=public_rows(dataset,source_id,start,end,q)
        offset=(page-1)*page_size
        return dict(records=rows[offset:offset+page_size],total=len(rows),fields=fields,page=page,page_size=page_size)

    @app.get('/api/v1/data-explorer/public/export')
    def public_export(request:Request,dataset:Literal['weather_observations','weather_forecasts','trade_observations']='weather_observations',format:Literal['csv','json']='csv',source_id:str|None=Query(default=None,max_length=20),start:date|None=None,end:date|None=None,q:str=Query(default='',max_length=100)):
        tenant(request)
        rows,fields,context=public_rows(dataset,source_id,start,end,q)
        if source_id:
            selected=next((source for source in context['sources'] if source['id']==source_id),None)
            if selected is None:raise HTTPException(404,'Source not found')
            if not selected['export_allowed']:raise HTTPException(403,'Selected source redistribution terms are unverified, including empty filtered exports.')
        if any(not r['export_allowed'] for r in rows):raise HTTPException(403,'This selection includes a source whose redistribution terms are unverified. Select a source with verified export permission.')
        return download(rows,fields,format,dict(sources=[s for s in context['sources'] if s['id'] in {r['source_id'] for r in rows}]))

    @app.get('/api/v1/data-explorer/public')
    def public(request:Request):
        tenant(request)
        from services.api.explorer_public import public_explorer
        return public_explorer()


def generated(body):
    # All playgrounds start from the same versioned reference; no imported farm is mutated.
    farm=synthetic_farm(settings=body.generator_settings).model_dump(mode='json')
    generator=body.generator_settings.model_dump(mode='json'); settings=body.forecast_settings.model_dump(mode='json')
    reference=reference_payload()
    computed=forecast(Farm.model_validate(farm),alpha=settings['alpha'])
    return dict(snapshot_schema_version='explorer-snapshot-v1',input_snapshot=farm,generator_settings=generator,generator_version=GENERATOR_VERSION,forecast_settings=settings,forecast_version=MODEL_VERSION,forecast=computed,forecast_hash=content_hash(computed),cutoff=farm['cutoff'],content_hash=dataset_hash(farm,generator,settings),reference_snapshot=reference['input_snapshot'],reference_forecast_settings=reference['forecast_settings'],reference_forecast_version=reference['forecast_version'],reference_content_hash=reference['content_hash'],reference_generator_settings=reference['generator_settings'],reference_generator_version=reference['generator_version'],provenance=dict(origin='synthetic',description='Deterministic sandbox generated from the versioned reference fixture. Repeating demand pattern is an assumption, not measured seasonality.',reference_hash=reference['content_hash'],comparison_root='playground:'+reference['content_hash']))
