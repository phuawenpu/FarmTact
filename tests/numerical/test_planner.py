from datetime import timedelta
from decimal import Decimal
import copy
import pytest
from packages.fixtures import synthetic_farm
from packages.models import forecast,scenarios
from packages.planner import plan,validate_allocations,simulate
from packages.planner.engine import allocations_existing,candidates

@pytest.fixture(scope='module')
def planned():
    f=synthetic_farm();return f,plan(f,time_limit=2)

def test_strategies_feasible_comparable_and_different(planned):
    f,p=planned
    assert {s['name'] for s in p['strategies']}=={'Lean','Balanced','Resilient'}
    assert len({s['scenario_set_id'] for s in p['strategies']})==1
    for s in p['strategies']:
        assert s['status']=='FEASIBLE'
        assert not validate_allocations(f,s['allocations'])
        assert s['metrics']['cost_sgd']<=float(f.resources.cash_sgd)
        assert s['solver']['status'] in ('FEASIBLE','OPTIMAL')
    signatures={tuple(a['id'] for a in s['allocations']) for s in p['strategies']}
    assert len(signatures)==3

def test_early_shortage_is_not_solved_by_new_sowing(planned):
    f,p=planned
    for s in p['strategies']:
        assert s['weekly'][1]['shortfall_kg']>0
        for a in s['allocations']:
            if not a['executed']:assert a['harvest_date']>str(f.cutoff.date()+timedelta(days=7))

def test_all_daily_mass_balances_and_costs_reconcile(planned):
    f,p=planned
    for s in p['strategies']:
        for row in s['ledger']:
            assert abs(row['opening_kg']+row['harvest_kg']-row['delivered_kg']-row['disposed_kg']-row['closing_kg'])<1e-5
        assert s['metrics']['margin_sgd']==pytest.approx(s['metrics']['revenue_sgd']-s['metrics']['cost_sgd'],abs=.011)
        assert sum(s['cost_breakdown'].values())==pytest.approx(s['metrics']['cost_sgd'],abs=.021)

def test_locked_work_and_lead_times_fail_independent_validation(planned):
    f,p=planned;a=copy.deepcopy(p['strategies'][0]['allocations']);a[0]['sow_date']='2026-09-08'
    codes={x['constraint_code'] for x in validate_allocations(f,a)}
    assert 'EXECUTED_ACTION_CHANGED' in codes and 'BIOLOGICAL_LEAD_TIME' in codes

def test_occupancy_nursery_and_labour_are_independent():
    f=synthetic_farm();a=candidates(f)[0];b=dict(a,id='duplicate-location')
    assert 'BED_OCCUPANCY' in {v['constraint_code'] for v in validate_allocations(f,allocations_existing(f)+[a,b])}
    f.resources.nursery_sites=0
    assert 'NURSERY_CAPACITY' in {v['constraint_code'] for v in validate_allocations(f,allocations_existing(f)+[a])}
    f.resources.labour_hours_per_week=Decimal('0')
    assert 'LABOUR_CAPACITY' in {v['constraint_code'] for v in validate_allocations(f,allocations_existing(f))}

def test_marketable_yield_not_reduced_twice():
    f=synthetic_farm();a=allocations_existing(f);s=simulate(f,a,forecast(f)['demand'],scenarios()[1])
    assert s['metrics']['harvest_kg']==sum(x['expected_kg'] for x in a)

def test_timeout_uses_explicit_baseline_and_zero_budget_is_infeasible():
    f=synthetic_farm();p=plan(f,time_limit=0)
    assert all(s['solver'].get('fallback')=='backward-scheduling-v1' for s in p['strategies'])
    f.resources.cash_sgd=Decimal('0');p=plan(f,time_limit=.1)
    assert all(s['status']=='NO_FEASIBLE_PLAN' for s in p['strategies'])

def test_zero_demand_fill_rate_defined():
    f=synthetic_farm();f.orders=[];f.history=[]
    s=simulate(f,allocations_existing(f),forecast(f)['demand'],scenarios()[1])
    assert s['metrics']['fill_rate']==1


def test_downside_uses_each_metric_minimum_across_shared_scenarios(planned):
    _,output=planned
    for strategy in output['strategies']:
        margins=[s['metrics']['margin_sgd'] for s in strategy['scenario_results']]
        fills=[s['metrics']['fill_rate'] for s in strategy['scenario_results']]
        assert strategy['risk']['downside_margin_sgd']==min(margins)
        assert strategy['risk']['downside_fill_rate']==min(fills)
