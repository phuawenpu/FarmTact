from datetime import date,datetime,timezone
from pathlib import Path
import json,os
from packages.contracts import Farm

ROOT=Path(__file__).resolve().parents[2]
def crop_views(farm):
    file=ROOT/'research/crop_catalogue.json'
    if not file.exists():return []
    data=json.loads(file.read_text()); recipes={r.crop_id:r for r in farm.recipes}
    result=[]
    for c in data.get('profiles',[]):
        r=recipes.get(c['crop_id'])
        result.append(dict(id=c['crop_id'],label=c['display_name'],aliases=c['aliases'],harvested_part=', '.join(c['harvested_parts']),evidence_ids=c['evidence_ids'],warnings=[c['boundary']]+c['parameter_gaps'],popularity_rank=None,taxonomy_status=c['taxonomy_status'],recipe=dict(cycle_days=r.cycle_days,nursery_days=r.nursery_days,yield_kg_per_m2=float(r.marketable_kg_per_m2),validation_status=r.validation_status) if r else None))
    return result

def farm_view(farm):
    recipes={r.id:r for r in farm.recipes}; batches={b.bed_id:b for b in farm.batches}; day=farm.planning_date; beds=[]
    for bed in farm.beds:
        b=batches.get(bed.id); v=bed.model_dump(mode='json');v['area_m2']=float(bed.area_m2)
        v.update(stage='empty',progress=0)
        if b:
            from packages.growth import crop_state
            r=recipes[b.recipe_id]
            v.update(crop_state(b.model_dump(mode='json'),r,day))
            v.update(batch_id=b.id,transplant_date=str(b.transplant_date),crop_id=r.crop_id,sow_date=str(b.sow_date),harvest_date=str(b.harvest_date))
        beds.append(v)
    return dict(id=farm.id,name=farm.name,location=farm.location,timezone=farm.timezone,data_mode=farm.data_mode,cutoff=farm.cutoff.isoformat(),planning_date=str(farm.planning_date),horizon_days=farm.horizon_days,recipe_calendar={r.id:dict(nursery_days=r.nursery_days,grow_days=r.grow_days,sanitation_days=r.sanitation_days,shelf_life_days=r.shelf_life_days,growth_model_version='schedule-state-v2') for r in farm.recipes},beds=beds,resources=dict(area_m2=sum(float(b.area_m2) for b in farm.beds),nursery_sites=farm.resources.nursery_sites,labour_hours_per_week=float(farm.resources.labour_hours_per_week),cash_sgd=float(farm.resources.cash_sgd)),orders=[dict(id=o.id,crop_id=o.crop_id,due_date=str(o.due_date),quantity_kg=float(o.quantity_kg-o.cancelled_kg),price_sgd_per_kg=float(o.price_sgd_per_kg)) for o in farm.orders],version=farm.version)

def capabilities(store=None,tenant=None):
    report_path=ROOT/'reports/deepseek/latest.json'
    report=json.loads(report_path.read_text()) if report_path.exists() else {}
    caps=report.get('capabilities',{})
    configured_models=json.loads((ROOT/'config/deepseek_runtime.json').read_text()).get('allowed_models',[])
    text_ok=all(caps.get(k,{}).get('status')=='PASS' for k in ('flash_json','pro_json'))
    configured=bool(os.environ.get('DEEPSEEK_API_KEY'))
    last=store.latest_run(tenant) if store is not None and tenant is not None else None
    observed=None
    if last and last.get('inference_audit'):
        observed=dict(run_id=last['id'],observed_at=last.get('completed_at'),execution_status=last.get('council_status'),evidence_status=last.get('council_evidence_status'),source='stored_tenant_execution',model_ids=sorted({a.get('returned_model') for a in last['inference_audit'] if a.get('returned_model')}))
    vision=next((v for k,v in caps.items() if 'vision' in k),{})
    return dict(deepseek=dict(status='configured' if configured else 'blocked',configured=configured,current_verification='not_probed',models=configured_models,reason='Server credential configured; availability is established by an actual requested execution.' if configured else 'Server credential unavailable',overall_trial_status=report.get('overall_status','NOT_RUN'),historical_probe=dict(text_passed=text_ok,models=caps.get('model_discovery',{}).get('reviewed_models_discovered',[]),observed_at=report.get('finished_at'),source='reports/deepseek/latest.json',trial_version=report.get('trial_version'),current_capability=False),last_observed_execution=observed,inference_triggered=False),vision=dict(status='unverified',historical_probe_status=vision.get('status','NOT_RUN'),current_verification='not_probed'),data_mode='synthetic_demo',execution_mode='test')

def source_views():
    try:
        from packages.ingestion import get_public_context
        context=get_public_context(ROOT/'data').as_dict()
    except (ImportError,FileNotFoundError):return []
    names={'D01':'Rainfall · Singapore stations','D02':'Air temperature · Singapore stations','D03':'Relative humidity · Singapore stations','D04':'Next day · NEA outlook','D05':'Four-day · NEA outlook','D06':'Vegetable trade volume · SingStat','D11':'Historical climate · NASA POWER'}
    from math import cos,radians
    result=[]
    for source in context.get('sources',[]):
        id=source['source_id'];rows=[r for r in context['weather_observations'] if r['source_id']==id and id in ('D01','D02','D03')]
        row=min(rows,key=lambda r:(float(r.get('latitude') or 0)-1.43)**2+((float(r.get('longitude') or 0)-103.71)*cos(radians(1.43)))**2) if rows else None
        forecasts=[r for r in context['weather_forecasts'] if r['source_id']==id and id in ('D04','D05')]
        coverage=source.get('coverage',{})
        summary=f"{coverage.get('row_count',0)} validated observations. "
        value=None;unit=source.get('unit')
        if row:
            value=row['value'];unit=row['unit'];summary=f"{row.get('station_name',row['station_id'])}: {value} {unit}. Nearest available station to the fictional farm; context only."
        elif forecasts:
            text=next((f['value'] for f in forecasts if isinstance(f['value'],str)),None)
            summary=str(text) if text else f"{len(forecasts)} forecast fields available; valid horizon preserved."
        elif id=='D11':summary='Seven days of historical gridded climate in UTC. Not a station, on-farm sensor or forecast; release time is unknown.'
        elif id=='D06':summary='Public trade volume is market context, never customer demand or farm selling price.'
        if source.get('failure_reason'):summary=source['failure_reason']
        if source.get('data_mode')=='synthetic_contract_fixture':summary='Synthetic source-contract example; not a public observation. '+summary
        result.append(dict(id=id,name=names.get(id,id),status=source['status'],observed_at=source.get('source_time'),available_at=row.get('available_at') if row else None,retrieved_at=source.get('retrieved_at'),freshness=source.get('freshness','unknown'),origin='synthetic' if source.get('data_mode')=='synthetic_contract_fixture' else 'public',data_mode=source.get('data_mode','public_context'),execution_mode=context['execution_mode'],summary=summary,unit=unit,value=value,url=next((s['request_url'] for s in context.get('snapshots',[]) if s['snapshot_id']==source.get('snapshot_id')),None),snapshot_id=source.get('snapshot_id'),coverage=coverage,licence_state=source.get('licence_state'),availability_status=row.get('availability_status') if row else None))
    return result
