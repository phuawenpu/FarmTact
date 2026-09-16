from datetime import date,timedelta

import pytest
from pydantic import ValidationError

from packages.fixtures import synthetic_farm
from packages.planner.engine import apply_seasonal_assumptions,candidates,resource_usage,simulate
from packages.planning_contracts import PlanningAssumptions
from packages.planning_numerics import calculate_session


@pytest.fixture(scope='module')
def base_session():
    farm=synthetic_farm()
    return farm,calculate_session(farm.model_dump(mode='json'))


def test_zero_assumptions_preserve_existing_inputs_and_planner_contract(base_session):
    farm,result=base_session
    assert result['input_snapshot']==farm.model_dump(mode='json')
    assert result['input_hash']==result['forecast']['input_hash']
    assert result["assumptions"] == {
        "future_demand": [],
        "seasonal": [],
        "order_changes": [],
        "reservations": [],
        "tentative_orders": [],
    }
    assert [row['name'] for row in result['strategies']]==['Lean','Balanced','Resilient']
    assert result['retained_strategy'] is None and result['comparisons']==[]
    assert result['stages'][0]['stage']=='validate_and_version_inputs'


def test_demand_adjustment_changes_only_residual_and_explicit_order_change_versions_input(base_session):
    farm,base=base_session; day=farm.planning_date; crop='caixin'
    retained=base['strategies'][1]
    added=dict(operation='add',order_id='v11-explicit-order',crop_id=crop,due_date=str(day+timedelta(days=20)),quantity_kg='7.5',price_sgd_per_kg='8.25')
    assumptions=dict(
        future_demand=[dict(crop_id=crop,start_date=str(day),end_date=str(day+timedelta(days=farm.horizon_days-1)),percent=150)],
        seasonal=[],order_changes=[added],
    )
    result=calculate_session(farm.model_dump(mode='json'),assumptions=assumptions,retained_strategy=retained)

    assert result['input_snapshot']['history']==farm.model_dump(mode='json')['history']
    original_orders={row.id:row.model_dump(mode='json') for row in farm.orders}
    changed_orders={row['id']:row for row in result['input_snapshot']['orders']}
    assert all(changed_orders[key]==value for key,value in original_orders.items())
    assert changed_orders['v11-explicit-order']['quantity_kg']=='7.5'
    assert result['input_snapshot']['version']==farm.version+1

    base_rows={(row['crop_id'],row['date']):row for row in base['forecast']['demand']}
    changed_rows={(row['crop_id'],row['date']):row for row in result['forecast']['demand']}
    for key,row in base_rows.items():
        if key not in changed_rows: continue
        assert changed_rows[key]['confirmed_kg']>=row['confirmed_kg']
        if key[0]!=crop: assert changed_rows[key]['residual_kg']==row['residual_kg']
    assert result['retained_strategy']['evaluated_without_optimization'] is True
    assert result['retained_strategy']['allocations']==retained['allocations']
    assert {row['policy'] for row in result['comparisons']}=={'Lean','Balanced','Resilient'}
    assert all(row['baseline_metrics']==result['retained_strategy']['metrics'] for row in result['comparisons'])


def test_seasonal_projection_is_once_only_and_preserves_allocation_identity():
    farm=synthetic_farm(); allocation=next(a for a in candidates(farm) if a['crop_id']=='caixin')
    nominal_date=allocation['harvest_date']; nominal_kg=allocation['expected_kg']
    assumption=dict(id='wet-window',crop_id='caixin',system='sheltered_hydroponic',start_date=nominal_date,end_date=nominal_date,yield_percent=75,delay_days=3,reason='Synthetic sensitivity',provenance='synthetic_assumption')

    once=apply_seasonal_assumptions(farm,[allocation],[assumption])[0]
    twice=apply_seasonal_assumptions(farm,[once],[assumption])[0]

    assert once==twice
    assert once['id']==allocation['id']
    assert once['harvest_date']==str(timedelta(days=3)+date.fromisoformat(nominal_date))
    assert once['expected_kg']==pytest.approx(nominal_kg*.75)
    assert once['effective_projection']['nominal_harvest_date']==nominal_date
    _,_,occupancy,_=resource_usage(farm,[once])
    assert max(day for bed,day in occupancy if bed==once['bed_id'])>=(date.fromisoformat(once['harvest_date'])-farm.planning_date).days

    removed=apply_seasonal_assumptions(farm,[once],[])[0]
    replacement=dict(assumption,id='dry-window',yield_percent=60,delay_days=1)
    replaced=apply_seasonal_assumptions(farm,[once],[replacement])[0]
    assert removed['harvest_date']==nominal_date and removed['expected_kg']==nominal_kg
    assert 'effective_projection' not in removed
    assert replaced['harvest_date']==str(date.fromisoformat(nominal_date)+timedelta(days=1))
    assert replaced['expected_kg']==pytest.approx(nominal_kg*.6)


def test_noop_retained_evaluation_has_exact_input_and_mass_parity(base_session):
    farm,base=base_session; retained=base['strategies'][1]
    result=calculate_session(farm.model_dump(mode='json'),retained_strategy=retained)
    evaluated=result['retained_strategy']

    assert evaluated['input_hash']==result['input_hash']==retained['input_hash']
    assert evaluated['numerical_input_hash']==result['numerical_input_hash']==retained['numerical_input_hash']
    assert evaluated['metrics']==retained['metrics']
    assert evaluated['order_allocations']==retained['order_allocations']
    assert evaluated['terminal_stock']==retained['terminal_stock']
    assert all(row['balance_error']==0 for row in evaluated['ledger'])
    assert all(row['baseline_metrics']==evaluated['metrics'] for row in result['comparisons'])


def test_advanced_world_lock_remains_exact_and_excludes_retroactive_work():
    farm=synthetic_farm(); farm.batches=[]
    locked=next(item for item in candidates(farm) if item['crop_id']=='caixin')
    locked=dict(locked,executed=True)
    not_before=farm.planning_date+timedelta(days=14)
    retained=dict(id='advanced-saved',name='Saved advanced schedule',allocations=[locked])

    result=calculate_session(
        farm.model_dump(mode='json'),retained_strategy=retained,locked_allocations=[locked],
        candidate_not_before=str(not_before),excluded_candidate_ids=['historical-allocation'],
    )

    assert result['retained_strategy']['allocations']==[locked]
    assert result['retained_strategy']['evaluated_without_optimization'] is True
    assert result['retained_strategy']['status']=='FEASIBLE'
    for strategy in result['strategies']:
        assert next(item for item in strategy['allocations'] if item['id']==locked['id'])==locked
        assert all(item.get('executed') or item['sow_date']>=str(not_before) for item in strategy['allocations'])
    assert result['excluded_candidate_ids']==['historical-allocation']


def test_recorded_harvest_is_frozen_and_never_replayed_by_new_assumptions():
    farm=synthetic_farm(); farm.batches=[]; farm.inventory=[]; farm.orders=[]; farm.history=[]
    allocation=next(item for item in candidates(farm) if item['crop_id']=='caixin')
    historical=dict(allocation,executed=True,harvest_recorded=True,effective_projection={
        'seasonal_assumption_id':'old-observation','nominal_harvest_date':allocation['harvest_date'],
        'effective_harvest_date':allocation['harvest_date'],'nominal_expected_kg':allocation['expected_kg'],
        'effective_expected_kg':allocation['expected_kg'],'yield_percent':100,'delay_days':0,
        'provenance':'synthetic_assumption',
    })
    changed=dict(id='new-window',crop_id='caixin',system='sheltered_hydroponic',start_date=allocation['harvest_date'],end_date=allocation['harvest_date'],yield_percent=50,delay_days=14,reason='New sensitivity after recorded harvest',provenance='synthetic_assumption')

    assert apply_seasonal_assumptions(farm,[historical],[changed])==[historical]
    replay=simulate(farm,[historical],[],dict(id='central',yield_factor=1,demand_factor=1,weight=1))
    assert replay['metrics']['harvest_kg']==0
    assert all(row['harvest_kg']==0 for row in replay['ledger'])


def test_overlapping_assumptions_and_bad_order_changes_are_rejected():
    farm=synthetic_farm(); day=farm.planning_date
    common=dict(crop_id='caixin',system='sheltered_hydroponic',yield_percent=90,delay_days=2,reason='Synthetic',provenance='synthetic_assumption')
    with pytest.raises(ValidationError,match='Overlapping assumptions'):
        PlanningAssumptions.model_validate(dict(seasonal=[dict(common,start_date=day,end_date=day+timedelta(days=4)),dict(common,start_date=day+timedelta(days=4),end_date=day+timedelta(days=8))]))
    with pytest.raises(ValueError,match='unknown order'):
        calculate_session(farm.model_dump(mode='json'),assumptions=dict(order_changes=[dict(operation='cancel',order_id='missing')]))
