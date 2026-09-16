from datetime import date,timedelta

import pytest

from packages.fixtures import synthetic_farm
from packages.planner import plan,validate_allocations
from packages.planner.engine import candidates
from packages.planner.research import calculate_research,validate_research_inputs


def _reservation(farm,bed='bed-09',start=0,end=55):
    day=farm.planning_date
    return dict(bed_id=bed,start_date=str(day+timedelta(days=start)),end_date=str(day+timedelta(days=end)))


def test_reservation_excludes_new_occupancy_including_sanitation():
    farm=synthetic_farm()
    target=next(a for a in candidates(farm) if a['bed_id']=='bed-09')
    harvest=(date.fromisoformat(target['harvest_date'])-farm.planning_date).days
    reservation=_reservation(farm,start=harvest+1,end=harvest+1)
    filtered=candidates(farm,reservations=[reservation])
    assert target not in filtered
    assert 'BED_RESERVATION' in {v['constraint_code'] for v in validate_allocations(farm,[target],reservations=[reservation])}


def test_reservation_conflicting_with_executed_batch_is_rejected():
    farm=synthetic_farm(); batch=farm.batches[0]
    recipe=next(r for r in farm.recipes if r.id==batch.recipe_id)
    sanitation_end=batch.harvest_date+timedelta(days=recipe.sanitation_days)
    reservation=dict(bed_id=batch.bed_id,start_date=str(sanitation_end),end_date=str(sanitation_end))
    with pytest.raises(ValueError,match='conflicts with executed batch'):
        calculate_research(farm,[reservation],[])


def test_unconfirmed_order_changes_commitments_but_not_original_farm():
    farm=synthetic_farm(); before=farm.model_dump(mode='json'); order=farm.orders[-1]
    baseline=calculate_research(farm,[],[],labour_percent=100)
    changed=calculate_research(farm,[],[order.id],labour_percent=100)
    assert changed['research_metadata']['unconfirmed_order_ids']==[order.id]
    assert changed['research_metadata']['research_input_hash']!=baseline['research_metadata']['research_input_hash']
    assert changed['numerical_input_hash']!=baseline['numerical_input_hash']
    assert sum(row['confirmed_kg'] for row in changed['forecast']['demand'])<sum(row['confirmed_kg'] for row in baseline['forecast']['demand'])
    assert farm.model_dump(mode='json')==before


def test_research_inputs_and_forecasts_repeat_and_default_planning_has_parity():
    farm=synthetic_farm(); ordinary=plan(farm,time_limit=0)
    direct=plan(farm,time_limit=0,reservations=[])
    assert ordinary['numerical_input_hash']==direct['numerical_input_hash']
    assert [s['allocations'] for s in ordinary['strategies']]==[s['allocations'] for s in direct['strategies']]
    first=calculate_research(farm,[_reservation(farm)],['order-0-7'],labour_percent=80)
    second=calculate_research(farm,[_reservation(farm)],['order-0-7'],labour_percent=80)
    assert first['research_metadata']['research_input_hash']==second['research_metadata']['research_input_hash']
    assert first['numerical_input_hash']==second['numerical_input_hash']
    assert first['forecast']==second['forecast']
    # A wall-clock-limited CP-SAT solve may stop at different feasible incumbents
    # under CPU contention. Replay returns the stored result; recomputation is not
    # an identical-schedule contract. Both solutions must retain the hard boundary.
    for result in (first,second):
        assert all(s['status']=='FEASIBLE' and not s['violations'] for s in result['strategies'])
        assert all(not any(a['bed_id']=='bed-09' and not a['executed'] for a in s['allocations']) for s in result['strategies'])


def test_research_validates_bounds_ids_and_labour():
    farm=synthetic_farm()
    with pytest.raises(ValueError,match='unknown reservation bed'): calculate_research(farm,[_reservation(farm,bed='missing')],[])
    with pytest.raises(ValueError,match='planning horizon'): calculate_research(farm,[_reservation(farm,start=0,end=56)],[])
    with pytest.raises(ValueError,match='unknown unconfirmed'): calculate_research(farm,[],['missing'])
    with pytest.raises(ValueError,match='whole number'): calculate_research(farm,[],[],labour_percent=49)
    assert validate_research_inputs(farm,[],[],50)['labour_percent']==50
