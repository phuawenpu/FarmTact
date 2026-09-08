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

VERSION='daily-bed-cpsat-v1'
POLICIES={
 'Lean':dict(shortage=1,waste=9,commit=.20,capital_fraction=.65,description='Keep inputs light. Accept more uncovered demand to limit surplus.'),
 'Balanced':dict(shortage=4,waste=5,commit=.04,capital_fraction=.85,description='Balance customer coverage, growing cost and avoidable surplus.'),
 'Resilient':dict(shortage=25,waste=1,commit=0,capital_fraction=1,description='Protect delivery coverage under the shared low-yield scenario.')}

def allocations_existing(farm):
    recipes={r.id:r for r in farm.recipes}; beds={b.id:b for b in farm.beds}
    return [dict(id=b.id,bed_id=b.bed_id,crop_id=recipes[b.recipe_id].crop_id,recipe_id=b.recipe_id,sow_date=str(b.sow_date),transplant_date=str(b.transplant_date),harvest_date=str(b.harvest_date),area_m2=float(beds[b.bed_id].area_m2),expected_kg=float(b.expected_marketable_kg),executed=True) for b in farm.batches]

def candidates(farm):
    day=farm.planning_date; result=[]
    busy={b.bed_id:(b.harvest_date-day).days+next(r.sanitation_days for r in farm.recipes if r.id==b.recipe_id)+1 for b in farm.batches}
    # Sow backwards from actual weekly delivery dates: no late production allocated to earlier demand.
    for bed in farm.beds:
        for r in farm.recipes:
            if bed.system!=r.system: continue
            for harvest in sorted(set(range(6,farm.horizon_days,7)) | {(o.due_date-day).days for o in farm.orders if o.crop_id==r.crop_id and 0<=(o.due_date-day).days<farm.horizon_days}):
                sow=harvest-r.cycle_days; transplant=sow+r.nursery_days
                if sow<0 or transplant<busy.get(bed.id,0): continue
                result.append(dict(id=f'{bed.id}-{r.crop_id}-{sow}',bed_id=bed.id,crop_id=r.crop_id,recipe_id=r.id,sow_date=str(day+timedelta(days=sow)),transplant_date=str(day+timedelta(days=transplant)),harvest_date=str(day+timedelta(days=harvest)),area_m2=float(bed.area_m2),expected_kg=float(bed.area_m2*r.marketable_kg_per_m2),executed=False))
    return result

def resource_usage(farm,allocations):
    recipes={r.id:r for r in farm.recipes}; day=farm.planning_date; nursery=defaultdict(int); labour=defaultdict(float); bed_days=defaultdict(list); costs=0
    for a in allocations:
        r=recipes[a['recipe_id']]; area=Decimal(str(a['area_m2'])); sow=(date.fromisoformat(a['sow_date'])-day).days; transplant=(date.fromisoformat(a['transplant_date'])-day).days; harvest=(date.fromisoformat(a['harvest_date'])-day).days
        for d in range(max(0,sow),min(farm.horizon_days,transplant)): nursery[d]+=ceil(float(area)*r.density_per_m2)
        for d in range(max(0,transplant),min(farm.horizon_days,harvest+r.sanitation_days+1)): bed_days[(a['bed_id'],d)].append(a['id'])
        if sow>=0:
            labour[sow//7]+=float(area*r.sow_labour_hours_per_m2)
            if not a.get('executed'): costs+=ceil(float(area*r.cost_sgd_per_m2)*100)/100
        if 0<=harvest<farm.horizon_days:
            # Reserve the maximum scenario harvest labour, not just the central yield.
            labour[harvest//7]+=ceil(a['expected_kg']*1.1*float(r.harvest_labour_hours_per_kg)*60)/60
    return nursery,labour,bed_days,costs

def validate_allocations(farm,allocations):
    violations=[]; recipes={r.id:r for r in farm.recipes}; beds={b.id:b for b in farm.beds}; day=farm.planning_date
    def bad(code,entity,required,available,unit,period=None):
        violations.append(dict(constraint_code=code,entity_id=entity,period=period,required=required,available=available,unit=unit,severity='hard',repair_options=['Rebuild candidates from the frozen input']))
    ids=[a['id'] for a in allocations]
    if len(ids)!=len(set(ids)): bad('DUPLICATE_ACTION','plan',len(ids),len(set(ids)),'actions')
    locked={a['id']:a for a in allocations_existing(farm)}
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
        if not a.get('executed') and abs(a['expected_kg']-float(b.area_m2*r.marketable_kg_per_m2))>1e-6: bad('YIELD_ENDPOINT',a['id'],a['expected_kg'],float(b.area_m2*r.marketable_kg_per_m2),'marketable kg')
    if any(v['constraint_code']=='UNKNOWN_DEPENDENCY' for v in violations): return violations
    nursery,labour,occupancy,cost=resource_usage(farm,allocations)
    for d,v in nursery.items():
        if v>farm.resources.nursery_sites: bad('NURSERY_CAPACITY','nursery',v,farm.resources.nursery_sites,'sites',d)
    for w,v in labour.items():
        if v>float(farm.resources.labour_hours_per_week)+1e-6: bad('LABOUR_CAPACITY','workers',v,float(farm.resources.labour_hours_per_week),'hours',w)
    for (bed,d),values in occupancy.items():
        if len(values)>1: bad('BED_OCCUPANCY',bed,len(values),1,'batches',d)
    if cost>float(farm.resources.cash_sgd)+1e-6: bad('CASH_BUDGET','farm',cost,float(farm.resources.cash_sgd),'SGD')
    return violations

def simulate(farm,allocations,demand,scenario):
    """Daily FIFO lot ledger. Later supply never fills earlier orders; losses and carry are separate."""
    day=farm.planning_date; recipes={r.id:r for r in farm.recipes}; lots=[]; ledger=[]; weekly=[]
    for lot in farm.inventory:
        if lot.harvested_date>day: continue
        lots.append(dict(id=lot.id,crop_id=lot.crop_id,kg=float(lot.quantity_kg),expires=lot.expires_date))
    demand_by_day=defaultdict(list)
    for d in demand:
        demand_by_day[(date.fromisoformat(d['date'])-day).days].append(d)
    harvest_by_day=defaultdict(list)
    for a in allocations: harvest_by_day[(date.fromisoformat(a['harvest_date'])-day).days].append(a)
    total_revenue=0; total_delivered=0; total_demand=0; total_waste=0; total_harvest=0
    opening=sum(l['kg'] for l in lots)
    for n in range(farm.horizon_days):
        today=day+timedelta(days=n); before=sum(l['kg'] for l in lots); harvested=0; delivered=0; disposed=0; requested=0
        for l in lots:
            if l['expires']<today: disposed+=l['kg']; l['kg']=0
        for a in harvest_by_day[n]:
            kg=round(a['expected_kg']*scenario['yield_factor'],3); harvested+=kg
            lots.append(dict(id=a['id'],crop_id=a['crop_id'],kg=kg,expires=today+timedelta(days=recipes[a['recipe_id']].shelf_life_days-1)))
        for d in demand_by_day[n]:
            need=round(d['confirmed_kg']+d['residual_kg']*scenario['demand_factor'],3); requested+=need; remaining=need
            for l in sorted(lots,key=lambda x:(x['expires'],x['id'])):
                if l['crop_id']!=d['crop_id'] or l['expires']<today: continue
                take=min(remaining,l['kg']); l['kg']-=take; remaining-=take; delivered+=take; total_revenue+=take*d['price_sgd_per_kg']
        closing=sum(l['kg'] for l in lots)
        error=before+harvested-delivered-disposed-closing
        if abs(error)>1e-6: raise ValueError('inventory mass balance failed')
        ledger.append(dict(date=str(today),opening_kg=round(before,6),harvest_kg=round(harvested,6),delivered_kg=round(delivered,6),disposed_kg=round(disposed,6),closing_kg=round(closing,6),demand_kg=round(requested,6),balance_error=round(error,9)))
        total_harvest+=harvested; total_delivered+=delivered; total_waste+=disposed; total_demand+=requested
    for w in range((farm.horizon_days+6)//7):
        rows=ledger[w*7:(w+1)*7]
        weekly.append(dict(week=w,date=str(day+timedelta(days=w*7)),demand_kg=round(sum(r['demand_kg'] for r in rows),2),harvest_kg=round(sum(r['harvest_kg'] for r in rows),2),delivered_kg=round(sum(r['delivered_kg'] for r in rows),2),shortfall_kg=round(sum(r['demand_kg']-r['delivered_kg'] for r in rows),2)))
    nursery,labour,occupancy,cost=resource_usage(farm,allocations)
    actual_labour=sum(a['area_m2']*float(recipes[a['recipe_id']].sow_labour_hours_per_m2) for a in allocations if date.fromisoformat(a['sow_date'])>=day)
    actual_labour+=sum(a['expected_kg']*scenario['yield_factor']*float(recipes[a['recipe_id']].harvest_labour_hours_per_kg) for a in allocations if day<=date.fromisoformat(a['harvest_date'])<day+timedelta(days=farm.horizon_days))
    # Fixture recipe cost covers seed/nutrient/energy; labour/packing/disposal are itemized here.
    labour_cost=actual_labour*12; packing_cost=total_delivered*.3; disposal_cost=total_waste*.15
    total_cost=cost+labour_cost+packing_cost+disposal_cost
    return dict(scenario_id=scenario['id'],weekly=weekly,ledger=ledger,metrics=dict(fill_rate=round(total_delivered/total_demand,4) if total_demand else 1,margin_sgd=round(total_revenue-total_cost,2),waste_kg=round(total_waste,2),harvest_kg=round(total_harvest,2),shortfall_kg=round(total_demand-total_delivered,2),cost_sgd=round(total_cost,2),labour_hours=round(actual_labour,2),area_m2=sum(a['area_m2'] for a in allocations if not a.get('executed')),closing_stock_kg=round(sum(l['kg'] for l in lots),2),opening_stock_kg=opening,revenue_sgd=round(total_revenue,2)),cost_breakdown=dict(inputs_sgd=cost,labour_sgd=round(labour_cost,2),packing_sgd=round(packing_cost,2),disposal_sgd=round(disposal_cost,2)))

def _solve(farm,cands,existing,demand,scenario_set,policy,time_limit=4):
    m=cp_model.CpModel(); x=[m.new_bool_var(a['id']) for a in cands]; day=farm.planning_date; recipes={r.id:r for r in farm.recipes}; p=POLICIES[policy]
    fixed_n,fixed_l,fixed_o,fixed_cost=resource_usage(farm,existing)
    usages=[resource_usage(farm,[a]) for a in cands]
    for bed in farm.beds:
        for d in range(farm.horizon_days):
            terms=[x[i] for i,u in enumerate(usages) if (bed.id,d) in u[2]]
            if terms: m.add(sum(terms)+len(fixed_o.get((bed.id,d),[]))<=1)
    for d in range(farm.horizon_days):
        m.add(sum(u[0].get(d,0)*x[i] for i,u in enumerate(usages))+fixed_n.get(d,0)<=farm.resources.nursery_sites)
    for w in range((farm.horizon_days+6)//7):
        m.add(sum(ceil(u[1].get(w,0)*60)*x[i] for i,u in enumerate(usages))+ceil(fixed_l.get(w,0)*60)<=int(farm.resources.labour_hours_per_week*60))
    # Cash covers input + reserved labour + worst-case packing/disposal for existing/new work.
    fixed_cash=ceil(fixed_cost*100+sum(fixed_l.values())*1200+sum(a['expected_kg']*1.1*.45*100 for a in existing))
    new_cash=[ceil(u[3]*100+sum(u[1].values())*1200+a['expected_kg']*1.1*.45*100) for a,u in zip(cands,usages)]
    m.add(sum(c*x[i] for i,c in enumerate(new_cash))+fixed_cash<=int(farm.resources.cash_sgd*100*Decimal(str(p['capital_fraction']))))
    objective=[]
    for si,sc in enumerate(scenario_set):
        for recipe in farm.recipes:
            crop=recipe.crop_id;life=recipe.shelf_life_days
            daily={}
            for d in demand:
                if d['crop_id']==crop:daily[(date.fromisoformat(d['date'])-day).days]=d
            previous={}
            for n in range(farm.horizon_days):
                dt=day+timedelta(days=n);deliveries=[];current={}
                for age in range(life):
                    fixed=0
                    if age==0:
                        fixed=sum(round(a['expected_kg']*sc['yield_factor']*1000) for a in existing if a['crop_id']==crop and a['harvest_date']==str(dt))
                        supplied=fixed+sum(round(a['expected_kg']*sc['yield_factor']*1000)*x[i] for i,a in enumerate(cands) if a['crop_id']==crop and a['harvest_date']==str(dt))
                    else:supplied=previous.get(age-1,0)
                    if n==0:
                        # Opening lots use their explicit remaining shelf life, not an invented expiry.
                        supplied+=sum(round(float(l.quantity_kg)*1000) for l in farm.inventory if l.crop_id==crop and l.harvested_date<=day<=l.expires_date and life-1-min(life-1,(l.expires_date-day).days)==age)
                    delivered=m.new_int_var(0,100000000,f'deliver-{si}-{crop}-{n}-{age}')
                    remain=m.new_int_var(0,100000000,f'stock-{si}-{crop}-{n}-{age}')
                    m.add(delivered+remain==supplied);deliveries.append(delivered);current[age]=remain
                    if age==life-1 and n<farm.horizon_days-1:
                        objective.append(-remain*round((p['waste']+.15)*100))
                d=daily.get(n)
                need=round((d['confirmed_kg']+d['residual_kg']*sc['demand_factor'])*1000) if d else 0
                m.add(sum(deliveries)<=need)
                price=d['price_sgd_per_kg'] if d else 0
                objective.append(sum(deliveries)*round((price+p['shortage']-.3)*100))
                previous=current
    # grams * cents/kg units; cash cents times 1000 and scenario count reconciles scales.
    objective += [-round((u[3]+sum(u[1].values())*12)*(1+p['commit'])*100)*1000*len(scenario_set)*x[i] for i,u in enumerate(usages)]
    m.maximize(sum(objective)); solver=cp_model.CpSolver(); solver.parameters.max_time_in_seconds=time_limit; solver.parameters.num_search_workers=1; solver.parameters.random_seed=farm.fixture_seed
    start=time.monotonic(); status=solver.solve(m)
    meta=dict(status=solver.status_name(status),wall_seconds=round(time.monotonic()-start,3),time_limit_seconds=time_limit,objective=solver.objective_value if status in (cp_model.FEASIBLE,cp_model.OPTIMAL) else None,best_bound=solver.best_objective_bound,integer_units='grams, cents, minutes, whole beds')
    chosen=[cands[i] for i,v in enumerate(x) if solver.value(v)] if status in (cp_model.FEASIBLE,cp_model.OPTIMAL) else None
    return chosen,meta

def baseline(farm,cands,existing,demand):
    chosen=list(existing)
    # Auditable backward-scheduling fallback: largest uncovered confirmed requirements first.
    for d in sorted(demand,key=lambda x:(x['week'],-x['confirmed_kg'],x['crop_id'])):
        available=sum(a['expected_kg'] for a in chosen if a['crop_id']==d['crop_id'] and a['harvest_date']==d['date'])
        for a in cands:
            if available>=d['confirmed_kg']: break
            if a['crop_id']!=d['crop_id'] or a['harvest_date']!=d['date'] or any(a['id']==b['id'] for b in chosen): continue
            trial=chosen+[a]
            if not validate_allocations(farm,trial) and simulate(farm,trial,demand,scenarios()[2])['metrics']['cost_sgd']<=float(farm.resources.cash_sgd): chosen=trial; available+=a['expected_kg']
    return chosen

def plan(farm:Farm,time_limit=4):
    f=forecast(farm); ss=scenarios(farm.fixture_seed); existing=allocations_existing(farm); cands=candidates(farm); result=[]
    for name,p in POLICIES.items():
        chosen,solver=_solve(farm,cands,existing,f['demand'],ss,name,time_limit)
        allocations=existing+(chosen or [])
        if chosen is None:
            allocations=baseline(farm,cands,existing,f['demand']); solver['fallback']='backward-scheduling-v1'
        violations=validate_allocations(farm,allocations)
        sims=[simulate(farm,allocations,f['demand'],s) for s in ss]
        if any(s['metrics']['cost_sgd']>float(farm.resources.cash_sgd)+.01 for s in sims): violations.append(dict(constraint_code='TOTAL_CASH_BUDGET',entity_id=farm.id,period=None,required=max(s['metrics']['cost_sgd'] for s in sims),available=float(farm.resources.cash_sgd),unit='SGD',severity='hard',repair_options=['Reduce planting or increase the declared fixture budget']))
        central=sims[1]; sid=content_hash(dict(name=name,input=f['input_hash'],allocations=allocations))[:20]
        result.append(dict(id=sid,name=name,status='FEASIBLE' if not violations else 'NO_FEASIBLE_PLAN',description=p['description'],policy_parameters=p,metrics=central['metrics'],cost_breakdown=central['cost_breakdown'],allocations=allocations,weekly=central['weekly'],ledger=central['ledger'],scenario_results=[dict(scenario_id=s['scenario_id'],metrics=s['metrics']) for s in sims],scenario_set_id=content_hash(ss),scenario_seed=farm.fixture_seed,violations=violations,solver=solver,input_hash=f['input_hash'],model_version=f['model_version'],calculation_version=VERSION,assumptions=['Synthetic recipes and scenario weights; not commercial yield validation.','Fresh marketable yield includes packout once.','Future sowing cannot cover earlier deliveries.','SGD cost fixture: labour 12/hour, packing 0.30/kg delivered, disposal 0.15/kg.'],risk=dict(downside_fill_rate=min(s['metrics']['fill_rate'] for s in sims),downside_margin_sgd=min(s['metrics']['margin_sgd'] for s in sims),basis='minimum across declared scenarios; not a calibrated quantile')))
    return dict(forecast=f,scenario_set=ss,strategies=result,candidate_count=len(cands),input_hash=content_hash(farm))
