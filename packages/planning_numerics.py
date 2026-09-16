"""Pure V11 planning-session numerical orchestration.

This module changes only frozen synthetic inputs, invokes the existing planner,
and evaluates a retained schedule without optimizing or repairing it.
"""
from __future__ import annotations

from decimal import Decimal
import time

from packages.contracts import Farm, content_hash
from packages.planner.engine import (
    POLICIES,
    apply_seasonal_assumptions,
    normalize_scenario_set,
    plan,
    simulate,
    validate_allocations,
)
from packages.planning_contracts import PlanningAssumptions


def _elapsed(start: float) -> float:
    return round(time.monotonic() - start, 6)


def _changed_farm(farm: Farm, changes: list[dict]) -> Farm:
    """Return a validated Farm revision containing only explicit order edits."""
    if not changes:
        return farm
    payload=farm.model_dump(mode='json')
    orders={row['id']:dict(row) for row in payload['orders']}
    for change in changes:
        operation=change['operation']; order_id=change['order_id']
        if operation=='add':
            if order_id in orders: raise ValueError(f'order already exists: {order_id}')
            orders[order_id]=dict(
                id=order_id,crop_id=change['crop_id'],booked_at=farm.cutoff.isoformat(),due_date=change['due_date'],
                quantity_kg=change['quantity_kg'],price_sgd_per_kg=change['price_sgd_per_kg'],cancelled_kg='0',origin='synthetic',
            )
        else:
            if order_id not in orders: raise ValueError(f'unknown order: {order_id}')
            if operation=='cancel':
                orders[order_id]['cancelled_kg']=orders[order_id]['quantity_kg']
            else:
                for field in ('crop_id','due_date','quantity_kg','price_sgd_per_kg'):
                    if field in change: orders[order_id][field]=change[field]
                if Decimal(str(orders[order_id].get('cancelled_kg',0)))>Decimal(str(orders[order_id]['quantity_kg'])):
                    raise ValueError(f'amended quantity is below already-cancelled quantity for {order_id}')
    payload['orders']=sorted(orders.values(),key=lambda row:row['id'])
    payload['version']=farm.version+1
    return Farm.model_validate(payload)


def _central_simulations(farm: Farm, allocations: list[dict], demand: list[dict], scenario_set: list[dict]):
    simulations=[simulate(farm,allocations,demand,scenario) for scenario in scenario_set]
    central=next((item for item in simulations if item['scenario_id']=='central'),simulations[max(range(len(scenario_set)),key=lambda i:scenario_set[i]['normalized_weight'])])
    return central,simulations


def _allocation_changes(retained: list[dict], proposed: list[dict]) -> dict:
    before={item['id']:item for item in retained}; after={item['id']:item for item in proposed}
    fields=('bed_id','crop_id','recipe_id','sow_date','transplant_date','harvest_date','expected_kg','area_m2')
    changed=[]
    for allocation_id in sorted(before.keys()&after.keys()):
        differences={field:dict(before=before[allocation_id].get(field),after=after[allocation_id].get(field)) for field in fields if before[allocation_id].get(field)!=after[allocation_id].get(field)}
        if differences: changed.append(dict(allocation_id=allocation_id,fields=differences))
    return dict(
        added=[after[key] for key in sorted(after.keys()-before.keys())],
        removed=[before[key] for key in sorted(before.keys()-after.keys())],
        changed=changed,
    )


def _metric_delta(baseline: dict, scenario: dict) -> dict:
    keys=('fill_rate','booked_requested_kg','booked_delivered_kg','shortfall_kg','waste_kg','closing_stock_kg','margin_sgd','cost_sgd','revenue_sgd','labour_hours','area_m2','harvest_kg')
    return {key:round(float(scenario.get(key,0))-float(baseline.get(key,0)),6) for key in keys}


def calculate_session(
    farm_snapshot: dict,
    *,
    assumptions: dict | None = None,
    retained_strategy: dict | None = None,
    locked_allocations: list | None = None,
    candidate_not_before: str | None = None,
    excluded_candidate_ids: list | None = None,
) -> dict:
    """Calculate V11 alternatives and an unchanged retained-schedule baseline."""
    overall=time.monotonic(); stages=[]
    stage=time.monotonic()
    original=Farm.model_validate(farm_snapshot)
    parsed=PlanningAssumptions.model_validate(assumptions or {})
    parsed.check_farm(original)
    normalized=parsed.model_dump(mode='json',exclude_none=True)
    changed=_changed_farm(original,normalized['order_changes'])
    if normalized.get('capacity'):
        payload=changed.model_dump(mode='json')
        payload['resources'].update(normalized['capacity'])
        changed=Farm.model_validate(payload)
    reservations=normalized.get('reservations',[])
    stages.append(dict(stage='validate_and_version_inputs',seconds=_elapsed(stage)))

    stage=time.monotonic()
    numerical_stages=[]
    calculated=plan(
        changed,reservations=reservations,
        locked_allocations=locked_allocations or (),
        candidate_not_before=candidate_not_before,
        excluded_candidate_ids=excluded_candidate_ids or (),
        demand_adjustments=normalized['future_demand'],
        seasonal_assumptions=normalized['seasonal'],
        timing_stages=numerical_stages,
    )
    stages.extend(numerical_stages)
    stages.append(dict(stage='forecast_and_optimize_strategies_total',seconds=_elapsed(stage)))

    retained_result=None; comparisons=[]
    if retained_strategy is not None:
        stage=time.monotonic()
        raw_allocations=retained_strategy.get('allocations')
        if not isinstance(raw_allocations,list): raise ValueError('retained_strategy requires an allocations list')
        retained_allocations=apply_seasonal_assumptions(changed,raw_allocations,normalized['seasonal'])
        violations=validate_allocations(
            changed,retained_allocations,reservations=reservations,locked_allocations=locked_allocations or (),
            scenario_set=calculated['scenario_set'],seasonal_assumptions=normalized['seasonal'],
        )
        central,all_simulations=_central_simulations(changed,retained_allocations,calculated['forecast']['demand'],calculated['scenario_set'])
        worst_cost=max(item['metrics']['cost_sgd'] for item in all_simulations)
        if worst_cost>float(changed.resources.cash_sgd)+.01:
            violations.append(dict(
                constraint_code='TOTAL_CASH_BUDGET',entity_id=changed.id,period=None,
                required=worst_cost,available=float(changed.resources.cash_sgd),unit='SGD',severity='hard',
                repair_options=['Retained schedule is infeasible under the changed inputs; do not repair it implicitly'],
            ))
        retained_result=dict(
            id=retained_strategy.get('id'),name=retained_strategy.get('name','Saved schedule'),
            status='FEASIBLE' if not violations else 'NO_FEASIBLE_PLAN',evaluated_without_optimization=True,
            metrics=central['metrics'],cost_breakdown=central['cost_breakdown'],allocations=retained_allocations,
            weekly=central['weekly'],ledger=central['ledger'],order_allocations=central['order_allocations'],
            inventory_snapshots=central['inventory_snapshots'],terminal_stock=central['terminal_stock'],violations=violations,
            scenario_results=[dict(scenario_id=item['scenario_id'],metrics=item['metrics'],terminal_stock=item['terminal_stock']) for item in all_simulations],
            input_hash=content_hash(changed),numerical_input_hash=calculated['numerical_input_hash'],calculation_version='daily-bed-cpsat-v3',
        )
        for strategy in calculated['strategies']:
            comparisons.append(dict(
                policy=strategy['name'],strategy_id=strategy['id'],retained_strategy_id=retained_result['id'],
                baseline_status=retained_result['status'],scenario_status=strategy['status'],
                baseline_metrics=retained_result['metrics'],scenario_metrics=strategy['metrics'],
                deltas=_metric_delta(retained_result['metrics'],strategy['metrics']),
                allocation_changes=_allocation_changes(retained_allocations,strategy['allocations']),
            ))
        stages.append(dict(stage='evaluate_retained_schedule',seconds=_elapsed(stage)))

    stages.append(dict(stage='assemble_comparisons',seconds=0.0))
    calculated.update(
        input_snapshot=changed.model_dump(mode='json'),assumptions=normalized,
        retained_strategy=retained_result,comparisons=comparisons,
        stages=stages,timings=dict(total_seconds=_elapsed(overall),stage_seconds={item['stage']:item['seconds'] for item in stages}),
        calculation_contract='guided-planning-v12',
        tentative_demand=normalized.get('tentative_orders',[]),
        tentative_demand_policy='Unconfirmed interest is disclosed separately and excluded from booked commitments; explicit confirmation is required',
    )
    return calculated
