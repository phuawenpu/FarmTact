from datetime import timedelta
from decimal import Decimal
from itertools import product

import pytest

from packages.fixtures import synthetic_farm
from packages.planner import allocate_lots,normalize_scenario_set,plan,simulate,validate_allocations
from packages.planner.engine import _objective_terms,_solve,candidates


def _empty_one_bed_farm():
    farm=synthetic_farm()
    farm.batches=[];farm.inventory=[];farm.orders=[];farm.history=[];farm.beds=farm.beds[:1]
    return farm


def test_declared_scenario_weights_change_a_constructed_optimum():
    farm=_empty_one_bed_farm()
    candidate=next(a for a in candidates(farm) if a['crop_id']=='caixin')
    demand=[dict(crop_id='caixin',week=4,date=candidate['harvest_date'],confirmed_kg=0,residual_kg=44,price_sgd_per_kg=10,price_status='forecast_price')]
    quiet_heavy=[dict(id='quiet',yield_factor=1,demand_factor=0,weight=.99),dict(id='busy',yield_factor=1,demand_factor=1,weight=.01)]
    busy_heavy=[dict(id='quiet',yield_factor=1,demand_factor=0,weight=.01),dict(id='busy',yield_factor=1,demand_factor=1,weight=.99)]

    quiet_choice,quiet_meta=_solve(farm,[candidate],[],demand,quiet_heavy,'Lean',1)
    busy_choice,busy_meta=_solve(farm,[candidate],[],demand,busy_heavy,'Lean',1)

    assert quiet_meta['status']=='OPTIMAL' and busy_meta['status']=='OPTIMAL'
    assert quiet_choice==[]
    assert [row['id'] for row in busy_choice]==[candidate['id']]


def test_scenario_weights_are_validated_normalized_and_integerized():
    normalized=normalize_scenario_set([
        dict(id='a',yield_factor=1,demand_factor=1,weight=2),
        dict(id='b',yield_factor=1,demand_factor=1,weight=1),
    ])
    assert sum(row['normalized_weight'] for row in normalized)==pytest.approx(1)
    assert sum(row['objective_weight_units'] for row in normalized)==1000
    assert normalized[0]['objective_weight_units'] in (666,667)
    with pytest.raises(ValueError,match='positive sum'):
        normalize_scenario_set([dict(id='a',yield_factor=1,demand_factor=1,weight=0)])
    with pytest.raises(ValueError,match='unique'):
        normalize_scenario_set([dict(id='a',yield_factor=1,demand_factor=1,weight=1),dict(id='a',yield_factor=1,demand_factor=1,weight=1)])


def test_resilient_is_proven_maximin_on_tiny_competing_beds():
    farm=_empty_one_bed_farm(); pool=candidates(farm)
    caixin=next(a for a in pool if a['crop_id']=='caixin' and a['harvest_date']=='2026-10-19')
    pak_choi=next(a for a in pool if a['crop_id']=='pak_choi' and a['harvest_date']=='2026-10-19')
    demand=[
        dict(crop_id='caixin',week=5,date=caixin['harvest_date'],confirmed_kg=0,residual_kg=52,price_sgd_per_kg=20,price_status='forecast_price'),
        dict(crop_id='pak_choi',week=5,date=pak_choi['harvest_date'],confirmed_kg=0,residual_kg=52,price_sgd_per_kg=1,price_status='forecast_price'),
    ]
    scenarios=normalize_scenario_set([dict(id='only',yield_factor=1,demand_factor=1,weight=1)])

    lean,lean_meta=_solve(farm,[caixin,pak_choi],[],demand,scenarios,'Lean',1)
    resilient,resilient_meta=_solve(farm,[caixin,pak_choi],[],demand,scenarios,'Resilient',1)

    assert lean_meta['status']=='OPTIMAL' and [a['crop_id'] for a in lean]==['caixin']
    assert resilient_meta['status']=='OPTIMAL' and [a['crop_id'] for a in resilient]==['pak_choi']
    assert resilient_meta['risk_optimization']=={
        'method':'lexicographic_maximin_fill_rate','resolution_basis_points':1,
        'primary_status':'OPTIMAL','primary_best_fill_rate':.5,'primary_proven_optimal':True,
        'secondary_status':'OPTIMAL','secondary_completed':True,
    }


def test_optimizer_objective_reconciles_exactly_with_fifo_replay_for_tiny_case():
    farm=_empty_one_bed_farm()
    candidate=next(a for a in candidates(farm) if a['crop_id']=='caixin')
    demand=[dict(crop_id='caixin',week=4,date=candidate['harvest_date'],confirmed_kg=0,residual_kg=44,price_sgd_per_kg=10,price_status='forecast_price')]
    scenario=normalize_scenario_set([dict(id='only',yield_factor=1,demand_factor=1,weight=1)])
    chosen,meta=_solve(farm,[candidate],[],demand,scenario,'Balanced',1)
    replay=simulate(farm,chosen,demand,scenario[0])
    terms=_objective_terms(farm,chosen,replay,'Balanced')

    assert meta['status']=='OPTIMAL'
    assert meta['objective']/meta['objective_scale']['solver_units_per_sgd']==pytest.approx(terms['policy_utility_sgd_equivalent'])
    assert sum(row['delivered_kg'] for row in replay['order_allocations'])==pytest.approx(replay['metrics']['harvest_kg'])
    assert replay['terminal_stock']['quantity_kg']==0


def test_fefo_fifo_is_optimal_over_enumerated_two_lot_perishability_cases():
    day=synthetic_farm().planning_date
    for old_g,new_g,demand_today,demand_tomorrow in product(range(1,4),repeat=4):
        lots=[
            dict(id='old',crop_id='caixin',quantity_g=old_g,harvested_date=day-timedelta(days=1),expires_date=day),
            dict(id='new',crop_id='caixin',quantity_g=new_g,harvested_date=day,expires_date=day+timedelta(days=1)),
        ]
        first=allocate_lots(lots,[dict(demand_line_id='d0',order_id='d0',demand_kind='booked',crop_id='caixin',requested_g=demand_today,price_sgd_per_kg=1,price_status='order_contract_price')],day)[0]
        disposed=sum(lot['quantity_g'] for lot in lots if lot['expires_date']<day+timedelta(days=1))
        for lot in lots:
            if lot['expires_date']<day+timedelta(days=1): lot['quantity_g']=0
        second=allocate_lots(lots,[dict(demand_line_id='d1',order_id='d1',demand_kind='booked',crop_id='caixin',requested_g=demand_tomorrow,price_sgd_per_kg=1,price_status='order_contract_price')],day+timedelta(days=1))[0]
        observed=(first['delivered_g']+second['delivered_g'],-disposed)

        feasible=[]
        for from_old in range(min(old_g,demand_today)+1):
            for from_new in range(min(new_g,demand_today-from_old)+1):
                delivered_today=from_old+from_new
                delivered_tomorrow=min(demand_tomorrow,new_g-from_new)
                feasible.append((delivered_today+delivered_tomorrow,-(old_g-from_old)))
        assert observed==max(feasible)


def test_order_level_prices_and_missing_price_state_are_explicit():
    farm=synthetic_farm(); day=farm.planning_date; original=farm.orders[0]; opening=farm.inventory[0]
    farm.horizon_days=7;farm.batches=[]
    farm.orders=[
        original.model_copy(update={'id':'low','due_date':day,'quantity_kg':Decimal('2'),'price_sgd_per_kg':Decimal('5')}),
        original.model_copy(update={'id':'high','due_date':day,'quantity_kg':Decimal('2'),'price_sgd_per_kg':Decimal('20')}),
        original.model_copy(update={'id':'cancelled','due_date':day,'quantity_kg':Decimal('9'),'cancelled_kg':Decimal('9'),'price_sgd_per_kg':Decimal('99')}),
    ]
    farm.inventory=[
        opening.model_copy(update={'id':'old','quantity_kg':Decimal('3'),'harvested_date':day-timedelta(days=1),'expires_date':day}),
        opening.model_copy(update={'id':'new','quantity_kg':Decimal('3'),'harvested_date':day,'expires_date':day+timedelta(days=2)}),
    ]
    demand=[
        dict(crop_id='caixin',week=0,date=str(day),confirmed_kg=4,residual_kg=0,price_sgd_per_kg=12.5,price_status='booked_weighted_average'),
        dict(crop_id='caixin',week=0,date=str(day+timedelta(days=1)),confirmed_kg=0,residual_kg=2,price_sgd_per_kg=0,price_status='unavailable_no_booked_price'),
    ]
    replay=simulate(farm,[],demand,dict(id='only',yield_factor=1,demand_factor=1,weight=1))

    rows={row['demand_line_id']:row for row in replay['order_allocations']}
    assert 'order:cancelled' not in rows
    assert [item['lot_id'] for item in rows['order:high']['lot_allocations']]==['old']
    assert [item['lot_id'] for item in rows['order:low']['lot_allocations']]==['old','new']
    assert rows['residual:caixin:'+str(day+timedelta(days=1))+':1']['price_sgd_per_kg'] is None
    assert replay['metrics']['unpriced_delivered_kg']==2
    assert replay['metrics']['revenue_sgd']==50
    assert replay['terminal_stock']['physical_status']=='usable_or_expiring_inventory_at_horizon_close'
    assert replay['metrics']['waste_kg']==0


def test_terminal_stock_is_live_inventory_until_an_extended_horizon_expires_it():
    farm=_empty_one_bed_farm()
    allocation=max((a for a in candidates(farm) if a['crop_id']=='caixin'),key=lambda a:a['harvest_date'])
    scenario=dict(id='only',yield_factor=1,demand_factor=1,weight=1)

    short=simulate(farm,[allocation],[],scenario)
    assert short['terminal_stock']['quantity_kg']==allocation['expected_kg']
    assert short['terminal_stock']['disposal_kg']==0
    assert short['metrics']['waste_kg']==0

    farm.horizon_days+=7
    extended=simulate(farm,[allocation],[],scenario)
    assert extended['terminal_stock']['quantity_kg']==0
    assert extended['metrics']['waste_kg']==allocation['expected_kg']


def test_optimizer_and_replay_use_an_opening_lots_explicit_expiry_date():
    farm=_empty_one_bed_farm();day=farm.planning_date;template=synthetic_farm().inventory[0]
    farm.horizon_days=7
    farm.inventory=[template.model_copy(update={'quantity_kg':Decimal('5'),'harvested_date':day-timedelta(days=1),'expires_date':day+timedelta(days=6)})]
    demand=[dict(crop_id='caixin',week=0,date=str(day+timedelta(days=5)),confirmed_kg=5,residual_kg=0,price_sgd_per_kg=6,price_status='forecast_price')]
    scenario=normalize_scenario_set([dict(id='only',yield_factor=1,demand_factor=1,weight=1)])

    chosen,meta=_solve(farm,[],[],demand,scenario,'Balanced',1)
    replay=simulate(farm,chosen,demand,scenario[0]);terms=_objective_terms(farm,chosen,replay,'Balanced')

    assert meta['status']=='OPTIMAL' and sum(row['delivered_kg'] for row in replay['order_allocations'])==5
    assert meta['objective']/meta['objective_scale']['solver_units_per_sgd']==pytest.approx(terms['policy_utility_sgd_equivalent'])


def test_replan_locks_started_work_and_blocks_retroactive_new_sowing():
    farm=synthetic_farm();farm.batches=[]
    started=next(a for a in candidates(farm) if a['crop_id']=='caixin')
    started['executed']=True
    not_before=farm.planning_date+timedelta(days=14)

    output=plan(farm,time_limit=0,locked_allocations=[started],candidate_not_before=not_before)

    for strategy in output['strategies']:
        locked=next(a for a in strategy['allocations'] if a['id']==started['id'])
        assert locked==started
        assert not validate_allocations(farm,strategy['allocations'],locked_allocations=[started])
        assert all(a.get('executed') or a['sow_date']>=str(not_before) for a in strategy['allocations'])
