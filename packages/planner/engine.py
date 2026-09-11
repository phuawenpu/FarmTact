"""Auditable CP-SAT bed scheduling. Integer grams/cents/minutes, daily occupancy.

Fresh marketable yields already include packout. No second survival multiplier.
Demand scenario factors affect residual demand only; booked commitments never shrink.
"""
from __future__ import annotations
from collections import defaultdict
from datetime import date,timedelta
from decimal import Decimal
from math import ceil
import time
from ortools.sat.python import cp_model
from packages.contracts import Farm,content_hash
from packages.models import forecast,scenarios
from packages.planner.accounting import allocate_lots,demand_line_sort_key,demand_lines

VERSION='daily-bed-cpsat-v3'
SCENARIO_WEIGHT_SCALE=1000
POLICIES={
 'Lean':dict(shortage=1,waste=9,terminal_stock=.50,commit=.20,capital_fraction=.65,objective='weighted_policy_utility',description='Keep inputs light. Accept more uncovered demand to limit surplus.'),
 'Balanced':dict(shortage=4,waste=5,terminal_stock=.20,commit=.04,capital_fraction=.85,objective='weighted_policy_utility',description='Balance customer coverage, growing cost and avoidable surplus.'),
 'Resilient':dict(shortage=25,waste=1,terminal_stock=.05,commit=0,capital_fraction=1,objective='maximin_fill_then_weighted_policy_utility',description='Maximize the worst declared scenario fill rate, then improve weighted policy utility.')}


def _allocation_id(*,bed_id,crop_id,recipe_id,sow_date,transplant_date,harvest_date):
    """Return a fixed-length identity for one absolute crop-cycle allocation."""
    identity=dict(kind='crop_cycle_allocation',bed_id=bed_id,crop_id=crop_id,recipe_id=recipe_id,
                  sow_date=str(sow_date),transplant_date=str(transplant_date),harvest_date=str(harvest_date))
    return 'allocation-'+content_hash(identity)[:32]


def _harvest_lot_id(allocation,used_ids):
    """Derive a bounded lot ID without trusting caller-controlled ID namespaces."""
    identity=dict(kind='harvest_lot',allocation_id=allocation['id'],bed_id=allocation['bed_id'],
                  crop_id=allocation['crop_id'],recipe_id=allocation['recipe_id'],
                  sow_date=allocation['sow_date'],harvest_date=allocation['harvest_date'])
    used={str(value) for value in used_ids}
    for ordinal in range(len(used)+1):
        candidate='harvest-'+content_hash(dict(identity,collision_ordinal=ordinal))[:32]
        if candidate not in used:return candidate
    raise ValueError('unable to derive a unique harvest lot ID')


def normalize_scenario_set(scenario_set):
    """Validate scenario factors and convert declared weights to integer shares."""
    if not scenario_set: raise ValueError('scenario_set must contain at least one scenario')
    if len(scenario_set)>100: raise ValueError('scenario_set supports at most 100 declared scenarios')
    if len({str(s.get('id')) for s in scenario_set})!=len(scenario_set): raise ValueError('scenario IDs must be unique')
    parsed=[]; total=Decimal('0')
    for scenario in scenario_set:
        try:
            weight=Decimal(str(scenario['weight'])); yield_factor=Decimal(str(scenario['yield_factor'])); demand_factor=Decimal(str(scenario['demand_factor']))
        except (KeyError,ValueError,TypeError) as exc: raise ValueError('scenario requires finite weight, yield_factor and demand_factor') from exc
        if not all(value.is_finite() for value in (weight,yield_factor,demand_factor)): raise ValueError('scenario values must be finite')
        if weight<0 or yield_factor<0 or demand_factor<0: raise ValueError('scenario values must be non-negative')
        total+=weight; parsed.append((dict(scenario),weight))
    if total<=0: raise ValueError('scenario weights must have a positive sum')
    exact=[weight/total*SCENARIO_WEIGHT_SCALE for _,weight in parsed]
    units=[max(1,int(value)) if parsed[i][1]>0 else 0 for i,value in enumerate(exact)]
    remainder=SCENARIO_WEIGHT_SCALE-sum(units)
    order=sorted(range(len(units)),key=lambda i:(-(exact[i]-units[i]),str(parsed[i][0]['id'])))
    if remainder>0:
        for i in order[:remainder]: units[i]+=1
    elif remainder<0:
        for i in reversed(order):
            if remainder==0: break
            removable=min(units[i]-(1 if parsed[i][1]>0 else 0),-remainder)
            units[i]-=removable;remainder+=removable
    result=[]
    for (scenario,weight),unit in zip(parsed,units):
        scenario['weight']=float(weight)
        scenario['normalized_weight']=float(weight/total)
        scenario['objective_weight_units']=unit
        result.append(scenario)
    return result

def allocations_existing(farm):
    recipes={r.id:r for r in farm.recipes}; beds={b.id:b for b in farm.beds}
    return [dict(id=b.id,bed_id=b.bed_id,crop_id=recipes[b.recipe_id].crop_id,recipe_id=b.recipe_id,sow_date=str(b.sow_date),transplant_date=str(b.transplant_date),harvest_date=str(b.harvest_date),area_m2=float(beds[b.bed_id].area_m2),expected_kg=float(b.expected_marketable_kg),executed=True) for b in farm.batches]


def normalize_seasonal_assumptions(farm, assumptions=()):
    """Validate scoped synthetic yield/delay sensitivities.

    Applicability is decided from the nominal harvest date. Windows are inclusive
    and may not overlap for one crop/production-system pair.
    """
    crops={r.crop_id for r in farm.recipes}; systems={b.system for b in farm.beds}
    parsed=[]
    for index,item in enumerate(assumptions or ()):
        try:
            crop_id=str(item['crop_id']); system=str(item['system'])
            start=date.fromisoformat(str(item['start_date'])); end=date.fromisoformat(str(item['end_date']))
            yield_percent=int(item['yield_percent']); delay_days=int(item['delay_days'])
            reason=str(item['reason']).strip(); provenance=str(item['provenance'])
        except (KeyError,TypeError,ValueError) as exc:
            raise ValueError('seasonal assumption requires crop, system, ISO date window, integer yield/delay, reason and provenance') from exc
        if crop_id not in crops: raise ValueError(f'unknown seasonal crop: {crop_id}')
        if system not in systems: raise ValueError(f'unknown seasonal system: {system}')
        if start>end: raise ValueError('seasonal start_date must not follow end_date')
        if not 50<=yield_percent<=100: raise ValueError('seasonal yield_percent must be between 50 and 100')
        if not 0<=delay_days<=14: raise ValueError('seasonal delay_days must be between 0 and 14')
        if not reason: raise ValueError('seasonal reason must not be blank')
        if provenance!='synthetic_assumption': raise ValueError('seasonal provenance must be synthetic_assumption')
        parsed.append(dict(id=str(item.get('id') or f'seasonal-{index}'),crop_id=crop_id,system=system,start_date=str(start),end_date=str(end),yield_percent=yield_percent,delay_days=delay_days,reason=reason,provenance=provenance))
    ordered=sorted(parsed,key=lambda x:(x['crop_id'],x['system'],x['start_date'],x['end_date'],x['id']))
    for previous,current in zip(ordered,ordered[1:]):
        if previous['crop_id']==current['crop_id'] and previous['system']==current['system'] and current['start_date']<=previous['end_date']:
            raise ValueError(f'overlapping seasonal assumptions for {current["crop_id"]}/{current["system"]}')
    return ordered


def apply_seasonal_assumptions(farm, allocations, assumptions=()):
    """Return allocation copies with one applicable synthetic effect applied."""
    normalized=normalize_seasonal_assumptions(farm,assumptions)
    recipes={r.id:r for r in farm.recipes}; beds={b.id:b for b in farm.beds}; result=[]
    for source in allocations:
        allocation=dict(source)
        # A recorded harvest is history, including the effective projection that
        # produced it. Changed assumptions may affect only unrecorded outcomes.
        if allocation.get('harvest_recorded') is True:
            result.append(allocation)
            continue
        # Always derive from explicit nominal values so repeated application is stable.
        nominal_harvest=str(allocation.get('nominal_harvest_date',allocation['harvest_date']))
        nominal_kg=float(allocation.get('nominal_expected_kg',allocation['expected_kg']))
        recipe=recipes.get(allocation['recipe_id']); bed=beds.get(allocation['bed_id'])
        matching=[]
        if recipe and bed:
            matching=[item for item in normalized if item['crop_id']==allocation['crop_id'] and item['system']==bed.system and item['start_date']<=nominal_harvest<=item['end_date']]
        allocation.pop('effective_projection',None)
        allocation.pop('nominal_harvest_date',None)
        allocation.pop('nominal_expected_kg',None)
        if matching:
            effect=matching[0]; effective=date.fromisoformat(nominal_harvest)+timedelta(days=effect['delay_days'])
            allocation['nominal_harvest_date']=nominal_harvest
            allocation['nominal_expected_kg']=nominal_kg
            allocation['harvest_date']=str(effective)
            allocation['expected_kg']=round(nominal_kg*effect['yield_percent']/100,6)
            allocation['effective_projection']=dict(seasonal_assumption_id=effect['id'],nominal_harvest_date=nominal_harvest,effective_harvest_date=str(effective),nominal_expected_kg=nominal_kg,effective_expected_kg=allocation['expected_kg'],yield_percent=effect['yield_percent'],delay_days=effect['delay_days'],provenance='synthetic_assumption')
        else:
            allocation['harvest_date']=nominal_harvest
            allocation['expected_kg']=nominal_kg
        result.append(allocation)
    return result


def apply_future_demand_adjustments(farm, demand, adjustments=()):
    """Scale residual forecast only; confirmed/booked demand is unchanged."""
    crops={r.crop_id for r in farm.recipes}; normalized=[]
    for item in adjustments or ():
        try:
            crop_id=str(item['crop_id']); start=date.fromisoformat(str(item['start_date'])); end=date.fromisoformat(str(item['end_date'])); percent=int(item['percent'])
        except (KeyError,TypeError,ValueError) as exc: raise ValueError('future demand adjustment requires crop, ISO date window and integer percent') from exc
        if crop_id not in crops: raise ValueError(f'unknown future-demand crop: {crop_id}')
        if start>end: raise ValueError('future-demand start_date must not follow end_date')
        if start<farm.planning_date: raise ValueError('future-demand window must not begin before planning date')
        if not 50<=percent<=150: raise ValueError('future-demand percent must be between 50 and 150')
        normalized.append(dict(crop_id=crop_id,start_date=str(start),end_date=str(end),percent=percent))
    output=[]
    for source in demand:
        row=dict(source); multiplier=Decimal('1')
        for item in normalized:
            if item['crop_id']==row['crop_id'] and item['start_date']<=str(row['date'])<=item['end_date']:
                multiplier*=Decimal(item['percent'])/Decimal(100)
        row['residual_kg']=round(float(Decimal(str(row.get('residual_kg',0)))*multiplier),3)
        row['expected_kg']=round(float(Decimal(str(row.get('confirmed_kg',0)))+Decimal(str(row['residual_kg']))),3)
        output.append(row)
    return output,normalized

def _reservation_windows(farm,reservations=()):
    """Return validated inclusive reservation windows as horizon-relative days."""
    day=farm.planning_date; last=day+timedelta(days=farm.horizon_days-1); bed_ids={b.id for b in farm.beds}; result=[]
    for reservation in reservations:
        try:
            bed_id=reservation['bed_id']; start=reservation['start_date']; end=reservation['end_date']
        except (KeyError,TypeError) as exc:
            raise ValueError('reservation requires bed_id, start_date and end_date') from exc
        start=date.fromisoformat(start) if isinstance(start,str) else start
        end=date.fromisoformat(end) if isinstance(end,str) else end
        if bed_id not in bed_ids: raise ValueError(f'unknown reservation bed: {bed_id}')
        if type(start) is not date or type(end) is not date: raise ValueError('reservation dates must be ISO dates')
        if start>end: raise ValueError('reservation start_date must not follow end_date')
        if start<day or end>last: raise ValueError('reservation must be within the planning horizon')
        result.append(dict(bed_id=bed_id,start_date=str(start),end_date=str(end),start=(start-day).days,end=(end-day).days))
    ordered=sorted(result,key=lambda x:(x['bed_id'],x['start'],x['end']))
    for previous,current in zip(ordered,ordered[1:]):
        if previous['bed_id']==current['bed_id'] and current['start']<=previous['end']:
            raise ValueError(f'overlapping reservations for {current["bed_id"]}')
    return ordered

def _allocation_occupancy(farm,allocation):
    recipe=next(r for r in farm.recipes if r.id==allocation['recipe_id']); day=farm.planning_date
    start=(date.fromisoformat(allocation['transplant_date'])-day).days
    end=(date.fromisoformat(allocation['harvest_date'])-day).days+recipe.sanitation_days
    return start,end

def _reservation_conflicts(farm,allocation,windows):
    start,end=_allocation_occupancy(farm,allocation)
    return [r for r in windows if r['bed_id']==allocation['bed_id'] and start<=r['end'] and r['start']<=end]

def candidates(farm,*,reservations=(),candidate_not_before=None,seasonal_assumptions=()):
    day=farm.planning_date; result=[]
    not_before=date.fromisoformat(candidate_not_before) if isinstance(candidate_not_before,str) else candidate_not_before
    if not_before is not None and type(not_before) is not date: raise ValueError('candidate_not_before must be an ISO date')
    not_before=max(day,not_before) if not_before is not None else day
    windows=_reservation_windows(farm,reservations)
    busy={b.bed_id:(b.harvest_date-day).days+next(r.sanitation_days for r in farm.recipes if r.id==b.recipe_id)+1 for b in farm.batches}
    # Sow backwards from actual weekly delivery dates: no late production allocated to earlier demand.
    for bed in farm.beds:
        for r in farm.recipes:
            if bed.system!=r.system: continue
            for harvest in sorted(set(range(6,farm.horizon_days,7)) | {(o.due_date-day).days for o in farm.orders if o.crop_id==r.crop_id and 0<=(o.due_date-day).days<farm.horizon_days}):
                sow=harvest-r.cycle_days; transplant=sow+r.nursery_days
                if sow<0 or day+timedelta(days=sow)<not_before or transplant<busy.get(bed.id,0): continue
                sow_date=day+timedelta(days=sow);transplant_date=day+timedelta(days=transplant);harvest_date=day+timedelta(days=harvest)
                candidate=dict(id=_allocation_id(bed_id=bed.id,crop_id=r.crop_id,recipe_id=r.id,sow_date=sow_date,transplant_date=transplant_date,harvest_date=harvest_date),bed_id=bed.id,crop_id=r.crop_id,recipe_id=r.id,sow_date=str(sow_date),transplant_date=str(transplant_date),harvest_date=str(harvest_date),area_m2=float(bed.area_m2),expected_kg=float(bed.area_m2*r.marketable_kg_per_m2),executed=False)
                candidate=apply_seasonal_assumptions(farm,[candidate],seasonal_assumptions)[0]
                if not _reservation_conflicts(farm,candidate,windows): result.append(candidate)
    return result

def resource_usage(farm,allocations,*,harvest_yield_factor=1.1):
    harvest_yield_factor=Decimal(str(harvest_yield_factor))
    if not harvest_yield_factor.is_finite() or harvest_yield_factor<0:raise ValueError('harvest_yield_factor must be finite and non-negative')
    recipes={r.id:r for r in farm.recipes}; day=farm.planning_date; nursery=defaultdict(int); labour=defaultdict(float); bed_days=defaultdict(list); costs=0
    for a in allocations:
        r=recipes[a['recipe_id']]; area=Decimal(str(a['area_m2'])); sow=(date.fromisoformat(a['sow_date'])-day).days; transplant=(date.fromisoformat(a['transplant_date'])-day).days; harvest=(date.fromisoformat(a['harvest_date'])-day).days
        for d in range(max(0,sow),min(farm.horizon_days,transplant)): nursery[d]+=ceil(float(area)*r.density_per_m2)
        for d in range(max(0,transplant),min(farm.horizon_days,harvest+r.sanitation_days+1)): bed_days[(a['bed_id'],d)].append(a['id'])
        if sow>=0:
            labour[sow//7]+=float(area*r.sow_labour_hours_per_m2)
            if not a.get('executed'): costs+=ceil(float(area*r.cost_sgd_per_m2)*100)/100
        if not a.get('harvest_recorded') and 0<=harvest<farm.horizon_days:
            labour[harvest//7]+=ceil(Decimal(str(a['expected_kg']))*harvest_yield_factor*r.harvest_labour_hours_per_kg*60)/60
    return nursery,labour,bed_days,costs

def validate_allocations(farm,allocations,*,reservations=(),locked_allocations=(),scenario_set=None,seasonal_assumptions=()):
    violations=[]; recipes={r.id:r for r in farm.recipes}; beds={b.id:b for b in farm.beds}; day=farm.planning_date
    reserve_yield=max((Decimal(str(s['yield_factor'])) for s in normalize_scenario_set(scenario_set)),default=Decimal('1.1')) if scenario_set is not None else Decimal('1.1')
    windows=_reservation_windows(farm,reservations)
    def bad(code,entity,required,available,unit,period=None):
        violations.append(dict(constraint_code=code,entity_id=entity,period=period,required=required,available=available,unit=unit,severity='hard',repair_options=['Rebuild candidates from the frozen input']))
    ids=[a['id'] for a in allocations]
    if len(ids)!=len(set(ids)): bad('DUPLICATE_ACTION','plan',len(ids),len(set(ids)),'actions')
    locked={a['id']:a for a in apply_seasonal_assumptions(farm,allocations_existing(farm),seasonal_assumptions)}
    for allocation in apply_seasonal_assumptions(farm,locked_allocations,seasonal_assumptions):
        if allocation['id'] in locked and locked[allocation['id']]!=allocation: bad('LOCK_ID_COLLISION',allocation['id'],1,0,'unique locked action')
        locked[allocation['id']]=allocation
    actual={a['id']:a for a in allocations}
    for id,a in locked.items():
        if actual.get(id)!=a: bad('EXECUTED_ACTION_CHANGED',id,1,0,'unchanged action')
    for a in allocations:
        r=recipes.get(a['recipe_id']); b=beds.get(a['bed_id'])
        if not r or not b: bad('UNKNOWN_DEPENDENCY',a['id'],1,0,'reference'); continue
        if r.crop_id!=a['crop_id'] or r.system!=b.system: bad('CROP_SYSTEM_MISMATCH',a['id'],1,0,'compatible recipe')
        if a['area_m2']<=0 or Decimal(str(a['area_m2']))!=b.area_m2: bad('BED_AREA',a['id'],a['area_m2'],float(b.area_m2),'m2')
        sow=date.fromisoformat(a['sow_date']); transplant=date.fromisoformat(a['transplant_date']); harvest=date.fromisoformat(a['harvest_date'])
        if (transplant-sow).days<r.nursery_days or (harvest-transplant).days<r.grow_days: bad('BIOLOGICAL_LEAD_TIME',a['id'],r.cycle_days,(harvest-sow).days,'days')
        if not a.get('executed') and sow<day: bad('SOW_IN_PAST',a['id'],0,(sow-day).days,'days')
        expected_endpoint=float(b.area_m2*r.marketable_kg_per_m2)
        if a.get('effective_projection'):
            expected_endpoint=round(float(a['effective_projection']['nominal_expected_kg'])*float(a['effective_projection']['yield_percent'])/100,6)
            if harvest>day+timedelta(days=farm.horizon_days-1): bad('SEASONAL_HORIZON_OVERRUN',a['id'],str(harvest),str(day+timedelta(days=farm.horizon_days-1)),'date')
        if not a.get('executed') and abs(a['expected_kg']-expected_endpoint)>1e-6: bad('YIELD_ENDPOINT',a['id'],a['expected_kg'],expected_endpoint,'marketable kg')
        for reservation in _reservation_conflicts(farm,a,windows):
            code='RESERVATION_EXECUTED_CONFLICT' if a.get('executed') else 'BED_RESERVATION'
            bad(code,a['id'],1,0,'available bed',f'{reservation["start_date"]}/{reservation["end_date"]}')
    if any(v['constraint_code']=='UNKNOWN_DEPENDENCY' for v in violations): return violations
    nursery,labour,occupancy,cost=resource_usage(farm,allocations,harvest_yield_factor=reserve_yield)
    for d,v in nursery.items():
        if v>farm.resources.nursery_sites: bad('NURSERY_CAPACITY','nursery',v,farm.resources.nursery_sites,'sites',d)
    for w,v in labour.items():
        if v>float(farm.resources.labour_hours_per_week)+1e-6: bad('LABOUR_CAPACITY','workers',v,float(farm.resources.labour_hours_per_week),'hours',w)
    for (bed,d),values in occupancy.items():
        if len(values)>1: bad('BED_OCCUPANCY',bed,len(values),1,'batches',d)
    if cost>float(farm.resources.cash_sgd)+1e-6: bad('CASH_BUDGET','farm',cost,float(farm.resources.cash_sgd),'SGD')
    return violations

def simulate(farm,allocations,demand,scenario):
    """Replay a plan with integer-gram FEFO/FIFO and order-level attribution."""
    day=farm.planning_date; recipes={r.id:r for r in farm.recipes}; lots=[]; ledger=[]; weekly=[]; snapshots=[]
    for lot in farm.inventory:
        if lot.harvested_date>day: continue
        lots.append(dict(id=lot.id,crop_id=lot.crop_id,quantity_g=round(float(lot.quantity_kg)*1000),harvested_date=lot.harvested_date,expires_date=lot.expires_date))
    lines=demand_lines(farm,demand,scenario); demand_by_day=defaultdict(list)
    for line in lines: demand_by_day[(date.fromisoformat(line['date'])-day).days].append(line)
    harvest_by_day=defaultdict(list)
    for a in allocations:
        if not a.get('harvest_recorded'):
            harvest_by_day[(date.fromisoformat(a['harvest_date'])-day).days].append(a)
    total_revenue=Decimal('0'); total_delivered=0; total_demand=0; total_waste=0; total_harvest=0; order_results=[];lot_origins={}
    booked_demand=0; booked_delivered=0; residual_demand=0; residual_delivered=0; unpriced_requested=0; unpriced_delivered=0
    opening=sum(l['quantity_g'] for l in lots)
    for n in range(farm.horizon_days):
        today=day+timedelta(days=n); before=sum(l['quantity_g'] for l in lots); harvested=0; disposed=0
        for lot in lots:
            if date.fromisoformat(str(lot['expires_date']))<today:
                disposed+=lot['quantity_g']; lot['quantity_g']=0
        for a in harvest_by_day[n]:
            quantity_g=round(a['expected_kg']*scenario['yield_factor']*1000); harvested+=quantity_g
            lot_id=_harvest_lot_id(a,(lot['id'] for lot in lots));lot_origins[lot_id]=a['id']
            lots.append(dict(id=lot_id,crop_id=a['crop_id'],quantity_g=quantity_g,harvested_date=today,expires_date=today+timedelta(days=recipes[a['recipe_id']].shelf_life_days-1)))
        allocated=allocate_lots(lots,demand_by_day[n],today)
        requested=sum(row['requested_g'] for row in allocated); delivered=sum(row['delivered_g'] for row in allocated)
        day_revenue=Decimal('0')
        for row in allocated:
            if row['demand_kind']=='booked': booked_demand+=row['requested_g']; booked_delivered+=row['delivered_g']
            else: residual_demand+=row['requested_g']; residual_delivered+=row['delivered_g']
            if row['price_sgd_per_kg'] is None:
                unpriced_requested+=row['requested_g']; unpriced_delivered+=row['delivered_g']
            else: day_revenue+=Decimal(row['delivered_g'])*Decimal(str(row['price_sgd_per_kg']))/Decimal(1000)
            lot_allocations=[]
            for item in row['lot_allocations']:
                detail=dict(lot_id=item['lot_id'],quantity_kg=round(item['quantity_g']/1000,3),harvested_date=item['harvested_date'],expires_date=item['expires_date'])
                if item['lot_id'] in lot_origins:detail['source_allocation_id']=lot_origins[item['lot_id']]
                lot_allocations.append(detail)
            order_results.append(dict(
                demand_line_id=row['demand_line_id'],order_id=row['order_id'],demand_kind=row['demand_kind'],crop_id=row['crop_id'],date=row['date'],
                requested_kg=round(row['requested_g']/1000,3),delivered_kg=round(row['delivered_g']/1000,3),shortfall_kg=round(row['shortfall_g']/1000,3),
                price_sgd_per_kg=row['price_sgd_per_kg'],price_status=row['price_status'],
                lot_allocations=lot_allocations,
            ))
        total_revenue+=day_revenue
        closing=sum(l['quantity_g'] for l in lots)
        error=before+harvested-delivered-disposed-closing
        if error: raise ValueError('inventory mass balance failed')
        booked_rows=[r for r in allocated if r['demand_kind']=='booked']; residual_rows=[r for r in allocated if r['demand_kind']=='residual']
        ledger.append(dict(
            date=str(today),opening_kg=round(before/1000,6),harvest_kg=round(harvested/1000,6),delivered_kg=round(delivered/1000,6),disposed_kg=round(disposed/1000,6),closing_kg=round(closing/1000,6),demand_kg=round(requested/1000,6),balance_error=0,
            booked_demand_kg=round(sum(r['requested_g'] for r in booked_rows)/1000,6),booked_delivered_kg=round(sum(r['delivered_g'] for r in booked_rows)/1000,6),
            residual_demand_kg=round(sum(r['requested_g'] for r in residual_rows)/1000,6),residual_delivered_kg=round(sum(r['delivered_g'] for r in residual_rows)/1000,6),
            revenue_sgd=round(float(day_revenue),2),packing_cost_sgd=round(delivered/1000*.30,2),disposal_cost_sgd=round(disposed/1000*.15,2),
        ))
        snapshots.append(dict(date=str(today),closing_lots=[dict(id=l['id'],crop_id=l['crop_id'],quantity_kg=round(l['quantity_g']/1000,3),harvested_date=str(l['harvested_date']),expires_date=str(l['expires_date']),origin='synthetic') for l in sorted(lots,key=lambda x:(x['crop_id'],str(x['expires_date']),str(x['harvested_date']),x['id'])) if l['quantity_g']>0]))
        total_harvest+=harvested; total_delivered+=delivered; total_waste+=disposed; total_demand+=requested
    for w in range((farm.horizon_days+6)//7):
        rows=ledger[w*7:(w+1)*7]
        weekly.append(dict(week=w,date=str(day+timedelta(days=w*7)),demand_kg=round(sum(r['demand_kg'] for r in rows),2),harvest_kg=round(sum(r['harvest_kg'] for r in rows),2),delivered_kg=round(sum(r['delivered_kg'] for r in rows),2),shortfall_kg=round(sum(r['demand_kg']-r['delivered_kg'] for r in rows),2)))
    nursery,labour,occupancy,cost=resource_usage(farm,allocations)
    actual_labour=sum(a['area_m2']*float(recipes[a['recipe_id']].sow_labour_hours_per_m2) for a in allocations if date.fromisoformat(a['sow_date'])>=day)
    actual_labour+=sum(a['expected_kg']*scenario['yield_factor']*float(recipes[a['recipe_id']].harvest_labour_hours_per_kg) for a in allocations if not a.get('harvest_recorded') and day<=date.fromisoformat(a['harvest_date'])<day+timedelta(days=farm.horizon_days))
    total_delivered_kg=total_delivered/1000; total_demand_kg=total_demand/1000; total_waste_kg=total_waste/1000
    labour_cost=actual_labour*12; packing_cost=total_delivered_kg*.3; disposal_cost=total_waste_kg*.15
    total_cost=cost+labour_cost+packing_cost+disposal_cost; closing_g=sum(l['quantity_g'] for l in lots)
    return dict(
        scenario_id=scenario['id'],weekly=weekly,ledger=ledger,order_allocations=order_results,inventory_snapshots=snapshots,
        resource_reserve_yield_factor=float(Decimal(str(scenario['yield_factor']))),
        harvest_lot_origins=[dict(lot_id=lot_id,source_allocation_id=allocation_id) for lot_id,allocation_id in sorted(lot_origins.items())],
        terminal_stock=dict(quantity_kg=round(closing_g/1000,3),physical_status='usable_or_expiring_inventory_at_horizon_close',salvage_value_sgd=0,disposal_kg=0),
        metrics=dict(fill_rate=round(total_delivered_kg/total_demand_kg,4) if total_demand_kg else 1,margin_sgd=round(float(total_revenue)-total_cost,2),waste_kg=round(total_waste_kg,2),harvest_kg=round(total_harvest/1000,2),shortfall_kg=round(total_demand_kg-total_delivered_kg,2),cost_sgd=round(total_cost,2),labour_hours=round(actual_labour,2),area_m2=sum(a['area_m2'] for a in allocations if not a.get('executed')),closing_stock_kg=round(closing_g/1000,2),opening_stock_kg=round(opening/1000,3),revenue_sgd=round(float(total_revenue),2),booked_requested_kg=round(booked_demand/1000,3),booked_delivered_kg=round(booked_delivered/1000,3),residual_requested_kg=round(residual_demand/1000,3),residual_delivered_kg=round(residual_delivered/1000,3),unpriced_requested_kg=round(unpriced_requested/1000,3),unpriced_delivered_kg=round(unpriced_delivered/1000,3)),
        cost_breakdown=dict(inputs_sgd=cost,labour_sgd=round(labour_cost,2),packing_sgd=round(packing_cost,2),disposal_sgd=round(disposal_cost,2)),
    )

def _solve(farm,cands,existing,demand,scenario_set,policy,time_limit=4,*,reservations=()):
    if any('objective_weight_units' not in scenario for scenario in scenario_set): scenario_set=normalize_scenario_set(scenario_set)
    m=cp_model.CpModel(); x=[m.new_bool_var(a['id']) for a in cands]; day=farm.planning_date; recipes={r.id:r for r in farm.recipes}; p=POLICIES[policy]
    reserve_yield=max(Decimal(str(s['yield_factor'])) for s in scenario_set)
    fixed_n,fixed_l,fixed_o,fixed_cost=resource_usage(farm,existing,harvest_yield_factor=reserve_yield)
    usages=[resource_usage(farm,[a],harvest_yield_factor=reserve_yield) for a in cands]
    windows=_reservation_windows(farm,reservations)
    for i,a in enumerate(cands):
        if _reservation_conflicts(farm,a,windows): m.add(x[i]==0)
    for bed in farm.beds:
        for d in range(farm.horizon_days):
            terms=[x[i] for i,u in enumerate(usages) if (bed.id,d) in u[2]]
            if terms: m.add(sum(terms)+len(fixed_o.get((bed.id,d),[]))<=1)
    for d in range(farm.horizon_days):
        m.add(sum(u[0].get(d,0)*x[i] for i,u in enumerate(usages))+fixed_n.get(d,0)<=farm.resources.nursery_sites)
    for w in range((farm.horizon_days+6)//7):
        m.add(sum(ceil(u[1].get(w,0)*60)*x[i] for i,u in enumerate(usages))+ceil(fixed_l.get(w,0)*60)<=int(farm.resources.labour_hours_per_week*60))
    # Cash covers input + reserved labour + worst-case packing/disposal for existing/new work.
    fixed_cash=ceil(Decimal(str(fixed_cost))*100+Decimal(str(sum(fixed_l.values())))*1200+sum((Decimal(str(a['expected_kg']))*reserve_yield*Decimal('.45')*100 for a in existing),Decimal(0)))
    new_cash=[ceil(Decimal(str(u[3]))*100+Decimal(str(sum(u[1].values())))*1200+Decimal(str(a['expected_kg']))*reserve_yield*Decimal('.45')*100) for a,u in zip(cands,usages)]
    m.add(sum(c*x[i] for i,c in enumerate(new_cash))+fixed_cash<=int(farm.resources.cash_sgd*100*Decimal(str(p['capital_fraction']))))
    objective=[]; scenario_delivery_totals=[]; scenario_demands=[]
    for si,sc in enumerate(scenario_set):
        lines=demand_lines(farm,demand,sc); lines_by_day_crop=defaultdict(list)
        for line in lines: lines_by_day_crop[((date.fromisoformat(line['date'])-day).days,line['crop_id'])].append(line)
        scenario_deliveries=[]; scenario_demand=sum(line['requested_g'] for line in lines)
        for crop in sorted({r.crop_id for r in farm.recipes}):
            recipe=next(r for r in farm.recipes if r.crop_id==crop)
            opening_life=max(((lot.expires_date-day).days+1 for lot in farm.inventory if lot.crop_id==crop and lot.harvested_date<=day<=lot.expires_date),default=0)
            life=max(recipe.shelf_life_days,opening_life)
            previous={}
            for n in range(farm.horizon_days):
                dt=day+timedelta(days=n);current={}; supplied_by_age={}
                if n>0:
                    expired=previous.get(0)
                    if expired is not None: objective.append(-expired*round((p['waste']+.15)*100)*sc['objective_weight_units'])
                for age in range(life):
                    supplied=previous.get(age+1,0)
                    if age==recipe.shelf_life_days-1:
                        fixed=sum(round(a['expected_kg']*sc['yield_factor']*1000) for a in existing if a['crop_id']==crop and a['harvest_date']==str(dt))
                        supplied+=fixed+sum(round(a['expected_kg']*sc['yield_factor']*1000)*x[i] for i,a in enumerate(cands) if a['crop_id']==crop and a['harvest_date']==str(dt))
                    if n==0:
                        # Buckets are civil days remaining through the explicit expiry date.
                        supplied+=sum(round(float(l.quantity_kg)*1000) for l in farm.inventory if l.crop_id==crop and l.harvested_date<=day<=l.expires_date and (l.expires_date-day).days==age)
                    supplied_by_age[age]=supplied
                    remain=m.new_int_var(0,100000000,f'stock-{si}-{crop}-{n}-{age}')
                    current[age]=remain
                day_lines=sorted(lines_by_day_crop[(n,crop)],key=demand_line_sort_key); deliveries_by_age=defaultdict(list); line_totals=[]
                for li,line in enumerate(day_lines):
                    by_age=[]
                    for age in range(life):
                        delivered=m.new_int_var(0,line['requested_g'],f'deliver-{si}-{crop}-{n}-{li}-{age}')
                        by_age.append(delivered); deliveries_by_age[age].append(delivered)
                    total=sum(by_age); line_totals.append(total); scenario_deliveries.extend(by_age)
                    shortfall=m.new_int_var(0,line['requested_g'],f'shortfall-{si}-{crop}-{n}-{li}')
                    m.add(total+shortfall==line['requested_g'])
                    price=0 if line['price_sgd_per_kg'] is None else line['price_sgd_per_kg']
                    objective.append(total*round((price-.3)*100)*sc['objective_weight_units'])
                    objective.append(-shortfall*round(p['shortage']*100)*sc['objective_weight_units'])
                    if li:
                        used=m.new_bool_var(f'use-line-{si}-{crop}-{n}-{li}')
                        m.add(total<=line['requested_g']*used);m.add(total>=used)
                        for higher,higher_line in zip(line_totals[:li],day_lines[:li]): m.add(higher==higher_line['requested_g']).only_enforce_if(used)
                for age in range(life):
                    m.add(sum(deliveries_by_age[age])+current[age]==supplied_by_age[age])
                    if deliveries_by_age[age]:
                        used=m.new_bool_var(f'use-age-{si}-{crop}-{n}-{age}')
                        m.add(sum(deliveries_by_age[age])<=100000000*used);m.add(sum(deliveries_by_age[age])>=used)
                        # A later-expiring bucket is touched only after earlier expiry buckets are empty.
                        for older in range(age): m.add(current[older]==0).only_enforce_if(used)
                if n==farm.horizon_days-1:
                    for remain in current.values(): objective.append(-remain*round(p['terminal_stock']*100)*sc['objective_weight_units'])
                previous=current
        scenario_delivery_totals.append(sum(scenario_deliveries)); scenario_demands.append(scenario_demand)
    # Scenario-independent commitment cost is charged once at full normalized weight.
    objective += [-round((u[3]+sum(u[1].values())*12)*(1+p['commit'])*100)*1000*SCENARIO_WEIGHT_SCALE*x[i] for i,u in enumerate(usages)]
    solver=cp_model.CpSolver(); solver.parameters.max_time_in_seconds=time_limit; solver.parameters.num_search_workers=1
    start=time.monotonic(); risk_meta=None; chosen_override=None; objective_kind='weighted_policy_utility'
    if policy=='Resilient':
        worst_fill_bp=m.new_int_var(0,10000,'worst-scenario-fill-bp'); constrained=0
        for delivered,total in zip(scenario_delivery_totals,scenario_demands):
            if total>0: m.add(worst_fill_bp*total<=delivered*10000); constrained+=1
        if not constrained: m.add(worst_fill_bp==10000)
        m.maximize(worst_fill_bp); status=solver.solve(m)
        first_status=solver.status_name(status); achieved=solver.value(worst_fill_bp) if status in (cp_model.FEASIBLE,cp_model.OPTIMAL) else None
        risk_meta=dict(method='lexicographic_maximin_fill_rate',resolution_basis_points=1,primary_status=first_status,primary_best_fill_rate=(achieved/10000 if achieved is not None else None),primary_proven_optimal=status==cp_model.OPTIMAL)
        if status==cp_model.OPTIMAL:
            primary_chosen=[cands[i] for i,v in enumerate(x) if solver.value(v)]
            m.add(worst_fill_bp==achieved);m.maximize(sum(objective));status=solver.solve(m)
            risk_meta['secondary_status']=solver.status_name(status)
            risk_meta['secondary_completed']=status in (cp_model.FEASIBLE,cp_model.OPTIMAL)
            if status not in (cp_model.FEASIBLE,cp_model.OPTIMAL):
                chosen_override=primary_chosen;status=cp_model.FEASIBLE;objective_kind='maximin_fill_only_secondary_unfinished'
        else: objective_kind='maximin_fill_basis_points'
    else:
        m.maximize(sum(objective));status=solver.solve(m)
    utility_objective=solver.objective_value if status in (cp_model.FEASIBLE,cp_model.OPTIMAL) and objective_kind=='weighted_policy_utility' else None
    meta=dict(status=solver.status_name(status),wall_seconds=round(time.monotonic()-start,3),time_limit_seconds=time_limit,objective=utility_objective,best_bound=solver.best_objective_bound if utility_objective is not None else None,objective_kind=objective_kind,integer_units='grams, cents/kg, minutes, whole beds; scenario weights normalized to 1000 integer units',objective_scale=dict(scenario_weight_units=SCENARIO_WEIGHT_SCALE,solver_units_per_sgd=SCENARIO_WEIGHT_SCALE*100000),risk_optimization=risk_meta)
    chosen=chosen_override if chosen_override is not None else ([cands[i] for i,v in enumerate(x) if solver.value(v)] if status in (cp_model.FEASIBLE,cp_model.OPTIMAL) else None)
    return chosen,meta

def baseline(farm,cands,existing,demand,*,reservations=(),scenario_set=None,locked_allocations=(),seasonal_assumptions=()):
    chosen=list(existing)
    # Auditable backward-scheduling fallback: largest uncovered confirmed requirements first.
    for d in sorted(demand,key=lambda x:(x['week'],-x['confirmed_kg'],x['crop_id'])):
        available=sum(a['expected_kg'] for a in chosen if a['crop_id']==d['crop_id'] and a['harvest_date']==d['date'])
        for a in cands:
            if available>=d['confirmed_kg']: break
            if a['crop_id']!=d['crop_id'] or a['harvest_date']!=d['date'] or any(a['id']==b['id'] for b in chosen): continue
            trial=chosen+[a]
            worst_cost=max(simulate(farm,trial,demand,s)['metrics']['cost_sgd'] for s in (scenario_set or normalize_scenario_set(scenarios())))
            if not validate_allocations(farm,trial,reservations=reservations,locked_allocations=locked_allocations,scenario_set=scenario_set,seasonal_assumptions=seasonal_assumptions) and worst_cost<=float(farm.resources.cash_sgd): chosen=trial; available+=a['expected_kg']
    return chosen

def _objective_terms(farm,allocations,simulation,policy,*,harvest_yield_factor=None):
    if harvest_yield_factor is None: harvest_yield_factor=simulation.get('resource_reserve_yield_factor',1.1)
    p=POLICIES[policy]; new=[a for a in allocations if not a.get('executed')]; _,labour,_,inputs=resource_usage(farm,new,harvest_yield_factor=harvest_yield_factor)
    commitment=(inputs+sum(labour.values())*12)*(1+p['commit'])
    metrics=simulation['metrics']; shortage=metrics['shortfall_kg']*p['shortage']; avoidable_waste=metrics['waste_kg']*p['waste']; terminal=metrics['closing_stock_kg']*p['terminal_stock']
    score=metrics['revenue_sgd']-metrics['cost_sgd']+simulation['cost_breakdown']['inputs_sgd']+simulation['cost_breakdown']['labour_sgd']-shortage-avoidable_waste-terminal-commitment
    return dict(
        scenario_id=simulation['scenario_id'],revenue_sgd=metrics['revenue_sgd'],packing_cost_sgd=simulation['cost_breakdown']['packing_sgd'],disposal_cost_sgd=simulation['cost_breakdown']['disposal_sgd'],
        shortage_kg=metrics['shortfall_kg'],shortage_policy_sgd_per_kg=p['shortage'],shortage_policy_penalty_sgd=round(shortage,2),
        disposed_kg=metrics['waste_kg'],waste_policy_sgd_per_kg=p['waste'],waste_policy_penalty_sgd=round(avoidable_waste,2),
        terminal_stock_kg=metrics['closing_stock_kg'],terminal_salvage_value_sgd=0,terminal_policy_sgd_per_kg=p['terminal_stock'],terminal_policy_penalty_sgd=round(terminal,2),
        new_work_commitment_cost_sgd=round(commitment,2),policy_utility_sgd_equivalent=round(score,2),
    )


def plan(farm:Farm,time_limit=4,*,alpha=.35,reservations=(),scenario_set=None,locked_allocations=(),candidate_not_before=None,excluded_candidate_ids=(),demand_adjustments=(),seasonal_assumptions=(),timing_stages=None):
    timing_stages=timing_stages if timing_stages is not None else []
    windows=_reservation_windows(farm,reservations)
    if isinstance(excluded_candidate_ids,(str,bytes)):raise ValueError('excluded_candidate_ids must be a collection of IDs')
    excluded=[]
    for candidate_id in excluded_candidate_ids:
        if len(excluded)==10000 or not isinstance(candidate_id,str):raise ValueError('excluded_candidate_ids must contain at most 10000 string IDs')
        excluded.append(candidate_id)
    stage_start=time.monotonic(); seasonal=normalize_seasonal_assumptions(farm,seasonal_assumptions)
    f=forecast(farm,alpha=alpha); adjusted_demand,normalized_demand=apply_future_demand_adjustments(farm,f['demand'],demand_adjustments); f=dict(f,demand=adjusted_demand)
    if normalized_demand or seasonal:
        f['numerical_input_hash']=content_hash(dict(base=f['numerical_input_hash'],future_demand=normalized_demand,seasonal=seasonal))
    ss=normalize_scenario_set(scenario_set or scenarios(farm.fixture_seed)); farm_existing=apply_seasonal_assumptions(farm,allocations_existing(farm),seasonal)
    timing_stages.append(dict(stage='forecast_and_normalize_inputs',seconds=round(time.monotonic()-stage_start,6)))
    supplied_locks=apply_seasonal_assumptions(farm,[dict(allocation) for allocation in locked_allocations],seasonal)
    if len({a['id'] for a in supplied_locks})!=len(supplied_locks): raise ValueError('locked allocation IDs must be unique')
    if {a['id'] for a in farm_existing}&{a['id'] for a in supplied_locks}: raise ValueError('locked allocations must not duplicate Farm batches')
    existing=farm_existing+supplied_locks
    lock_ids={a['id'] for a in existing}
    excluded_ids=set(excluded)
    stage_start=time.monotonic(); cands=[a for a in candidates(farm,reservations=windows,candidate_not_before=candidate_not_before,seasonal_assumptions=seasonal) if a['id'] not in lock_ids|excluded_ids]; result=[]
    timing_stages.append(dict(stage='generate_candidates',seconds=round(time.monotonic()-stage_start,6)))
    for name,p in POLICIES.items():
        stage_start=time.monotonic()
        chosen,solver=_solve(farm,cands,existing,f['demand'],ss,name,time_limit,reservations=windows)
        timing_stages.append(dict(stage=f'solve_{name.lower()}',seconds=round(time.monotonic()-stage_start,6)))
        allocations=existing+(chosen or [])
        if chosen is None:
            allocations=baseline(farm,cands,existing,f['demand'],reservations=windows,scenario_set=ss,locked_allocations=supplied_locks,seasonal_assumptions=seasonal); solver['fallback']='backward-scheduling-v1'
        violations=validate_allocations(farm,allocations,reservations=windows,locked_allocations=supplied_locks,scenario_set=ss,seasonal_assumptions=seasonal)
        stage_start=time.monotonic(); sims=[simulate(farm,allocations,f['demand'],s) for s in ss]
        timing_stages.append(dict(stage=f'replay_{name.lower()}',seconds=round(time.monotonic()-stage_start,6)))
        if any(s['metrics']['cost_sgd']>float(farm.resources.cash_sgd)+.01 for s in sims): violations.append(dict(constraint_code='TOTAL_CASH_BUDGET',entity_id=farm.id,period=None,required=max(s['metrics']['cost_sgd'] for s in sims),available=float(farm.resources.cash_sgd),unit='SGD',severity='hard',repair_options=['Reduce planting or increase the declared fixture budget']))
        central=next((s for s in sims if s['scenario_id']=='central'),sims[max(range(len(ss)),key=lambda i:ss[i]['normalized_weight'])]); sid=content_hash(dict(name=name,input=f['numerical_input_hash'],allocations=allocations,scenario_set=ss,candidate_not_before=candidate_not_before,excluded_candidate_ids=sorted(excluded_ids)))[:20]
        reserve_yield=max(Decimal(str(s['yield_factor'])) for s in ss)
        terms=[_objective_terms(farm,allocations,s,name,harvest_yield_factor=reserve_yield) for s in sims]; weighted_score=sum(t['policy_utility_sgd_equivalent']*s['normalized_weight'] for t,s in zip(terms,ss))
        result.append(dict(id=sid,name=name,status='FEASIBLE' if not violations else 'NO_FEASIBLE_PLAN',description=p['description'],policy_parameters=p,metrics=central['metrics'],cost_breakdown=central['cost_breakdown'],allocations=allocations,weekly=central['weekly'],ledger=central['ledger'],order_allocations=central['order_allocations'],inventory_snapshots=central['inventory_snapshots'],terminal_stock=central['terminal_stock'],objective_terms=dict(unit='SGD-equivalent policy utility; coefficients are declared preferences, not forecast costs',scenario_terms=terms,weighted_policy_utility_sgd_equivalent=round(weighted_score,2),scenario_independent_new_work_charged_once=True),scenario_results=[dict(scenario_id=s['scenario_id'],metrics=s['metrics'],terminal_stock=s['terminal_stock']) for s in sims],scenario_set_id=content_hash(ss),scenario_seed=None,violations=violations,solver=solver,input_hash=f['input_hash'],numerical_input_hash=f['numerical_input_hash'],configuration_hash=f['configuration_hash'],forecast_settings=f['forecast_settings'],model_version=f['model_version'],calculation_version=VERSION,assumptions=['Synthetic recipes and declared scenarios; not commercial yield validation.','Scenario weights are validated, normalized and consumed by the weighted objective. No random scenario sampling is performed.','Fresh marketable yield includes packout once.','Future sowing cannot cover earlier deliveries.','Order service uses booked-before-residual, then known higher price and stable ID because buyer/grade priority fields are absent.','Closing stock remains physical inventory with zero salvage value and a declared policy penalty; it is not counted as waste.','SGD cost fixture: labour 12/hour, packing 0.30/kg delivered, disposal 0.15/kg.'],risk=dict(downside_fill_rate=min(s['metrics']['fill_rate'] for s in sims),downside_margin_sgd=min(s['metrics']['margin_sgd'] for s in sims),basis=('lexicographic maximin fill-rate across declared scenarios before weighted utility tie-break' if name=='Resilient' else 'reported minimum across declared scenarios; not a calibrated quantile'),optimization_proven=bool(solver.get('risk_optimization',{}).get('primary_proven_optimal')) if name=='Resilient' else None)))
    return dict(forecast=f,scenario_set=ss,strategies=result,candidate_count=len(cands),excluded_candidate_ids=sorted(excluded_ids),input_hash=f['input_hash'],numerical_input_hash=f['numerical_input_hash'],configuration_hash=f['configuration_hash'],forecast_settings=f['forecast_settings'])
