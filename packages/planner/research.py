"""Isolated deterministic controls for playable council research scenarios."""
from __future__ import annotations

from copy import deepcopy
from datetime import date,timedelta
from decimal import Decimal

from packages.contracts import Farm,content_hash
from packages.planner.engine import VERSION,_reservation_windows,allocations_existing,plan

RESEARCH_VERSION='council-research-v1'


def validate_research_inputs(
    farm: Farm,
    reservations: list[dict],
    unconfirmed_order_ids: list[str],
    labour_percent: int=100,
) -> dict:
    """Validate bounded controls without running forecast or optimisation."""
    if isinstance(labour_percent,bool) or not isinstance(labour_percent,int) or not 50<=labour_percent<=100:
        raise ValueError('labour_percent must be a whole number from 50 to 100')
    if len(unconfirmed_order_ids)!=len(set(unconfirmed_order_ids)):
        raise ValueError('unconfirmed_order_ids must be unique')
    excluded=set(unconfirmed_order_ids)
    known_orders={order.id for order in farm.orders}; unknown=sorted(excluded-known_orders)
    if unknown: raise ValueError(f'unknown unconfirmed order IDs: {", ".join(unknown)}')

    windows=_reservation_windows(farm,reservations)
    for allocation in allocations_existing(farm):
        recipe=next(r for r in farm.recipes if r.id==allocation['recipe_id'])
        start=(date.fromisoformat(allocation['transplant_date'])-farm.planning_date).days
        end=(date.fromisoformat(allocation['harvest_date'])-farm.planning_date).days+recipe.sanitation_days
        if any(r['bed_id']==allocation['bed_id'] and start<=r['end'] and r['start']<=end for r in windows):
            raise ValueError(f'reservation conflicts with executed batch {allocation["id"]}')

    return dict(
        reservations=[{key:r[key] for key in ('bed_id','start_date','end_date')} for r in windows],
        unconfirmed_order_ids=sorted(unconfirmed_order_ids),
        confirmed_order_ids=sorted(known_orders-excluded),
        labour_percent=labour_percent,
    )


def calculate_research(
    farm: Farm,
    reservations: list[dict],
    unconfirmed_order_ids: list[str],
    labour_percent: int=100,
) -> dict:
    """Calculate three policies on a copy while retaining explicit research controls."""
    controls=validate_research_inputs(farm,reservations,unconfirmed_order_ids,labour_percent)

    calculation_farm=deepcopy(farm)
    excluded=set(controls['unconfirmed_order_ids'])
    calculation_farm.orders=[order for order in calculation_farm.orders if order.id not in excluded]
    calculation_farm.resources.labour_hours_per_week=(calculation_farm.resources.labour_hours_per_week*Decimal(labour_percent)/Decimal(100))
    normalized=controls['reservations']
    result=plan(calculation_farm,reservations=normalized)
    research_input_hash=content_hash(dict(
        version=RESEARCH_VERSION,
        farm_input_hash=content_hash(farm),
        numerical_input_hash=result['numerical_input_hash'],
        reservations=normalized,
        unconfirmed_order_ids=sorted(unconfirmed_order_ids),
        labour_percent=labour_percent,
    ))
    metadata=dict(
        version=RESEARCH_VERSION,
        calculation_version=VERSION,
        base_farm_input_hash=content_hash(farm),
        research_input_hash=research_input_hash,
        planning_date=str(farm.planning_date),
        horizon_end=str(farm.planning_date+timedelta(days=farm.horizon_days-1)),
        reservations=normalized,
        unconfirmed_order_ids=sorted(unconfirmed_order_ids),
        confirmed_order_ids=controls['confirmed_order_ids'],
        labour_percent=labour_percent,
    )
    result['research_metadata']=metadata
    for strategy in result['strategies']: strategy['research_input_hash']=research_input_hash
    return result
