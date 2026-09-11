from copy import deepcopy
from datetime import date
import secrets

from fastapi.testclient import TestClient
import pytest

from packages.contracts import Farm
from packages.fixtures import synthetic_farm
from packages.growth import crop_state
from packages.planner import plan
from services.api.app import create_app, create_mission, MissionRequest
from services.api.store import Store


@pytest.fixture(scope='module')
def accepted_plan():
    farm = synthetic_farm()
    return farm, plan(farm, time_limit=1)


def setup_world(accepted_plan):
    farm, result = accepted_plan
    store = Store('sqlite://'); tenant, token = store.new_session()
    store.save_farm(tenant, farm.model_dump(mode='json'))
    run = create_mission(store, tenant, MissionRequest(council=False), 'mission')
    run = store.get_run(tenant, run['id']); run.update(deepcopy(result))
    strategy = next(s for s in result['strategies'] if s['name'] == 'Balanced')
    assert strategy['status'] == 'FEASIBLE'
    run.update(status='ACCEPTED_FOR_SIMULATION', accepted_strategy_id=strategy['id'])
    store.save_run(tenant, run)
    client = TestClient(create_app(store, start_worker=False)); client.cookies.set('farmtact_session', token)
    return client, store, tenant, run, strategy


def post(client, path, body, key=None):
    response = client.post(path, json=body, headers={'Idempotency-Key': key or secrets.token_hex(12)})
    assert response.status_code in (200, 201), response.text
    return response.json()


def test_clock_execution_reconciles_projection_and_retry_is_exact(accepted_plan):
    client, store, tenant, run, strategy = setup_world(accepted_plan)
    with client:
        first = post(client, '/api/v1/simulations', {'run_id': run['id']}, 'new')
        state = first
        assert state['clock_date'] is None and state['days_executed'] == 0
        original_farm = deepcopy(store.latest_farm(tenant))
        body = dict(revision=0, days=14)
        once = post(client, f"/api/v1/simulations/{state['id']}/advance", body, 'advance-first')
        state = once
        for _ in range(3):
            state = post(client, f"/api/v1/simulations/{state['id']}/advance", dict(revision=state['revision'], days=14))
        assert state['status'] == 'COMPLETED' and state['days_executed'] == 56
        assert state['clock_date'] == state['end_date']
        assert post(client, '/api/v1/simulations', {'run_id': run['id']}, 'new') == first
        assert post(client, f"/api/v1/simulations/{state['id']}/advance", body, 'advance-first') == once
        assert client.get(f"/api/v1/simulations/{state['id']}").json() == state
        assert store.latest_farm(tenant) == original_farm  # world isolation
        for output, metric in (('delivered_kg', 'delivered_kg'), ('harvest_kg', 'harvest_kg'), ('disposed_kg', 'disposed_kg')):
            assert state['totals'][output] == pytest.approx(sum(row[metric] for row in strategy['ledger']))
        assert state['cost_sgd'] == pytest.approx(strategy['metrics']['cost_sgd'], abs=.01)
        assert state['revenue_sgd'] == pytest.approx(strategy['metrics']['revenue_sgd'], abs=.01)
        assert sum(float(l['quantity_kg']) for l in state['inventory']) == pytest.approx(strategy['terminal_stock']['quantity_kg'])
        rows = []; after = 0
        while True:
            page = client.get(f"/api/v1/simulations/{state['id']}/events?after={after}&limit=23").json()
            rows.extend(page['events'])
            if page['next_cursor'] is None: break
            after = page['next_cursor']
        closed = [e for e in rows if e['type'] == 'day_closed']
        assert len(closed) == 56 and len({e['date'] for e in closed}) == 56
        tasks = [e['task_id'] for e in rows if e['type'] == 'task_completed']
        assert len(set(tasks)) == len(tasks)
        assert all(e['ledger']['balance_error'] == 0 for e in closed)
        assert client.post(f"/api/v1/simulations/{state['id']}/advance", json={'revision': 0, 'days': 1}, headers={'Idempotency-Key': 'stale'}).status_code == 409
        assert client.post(f"/api/v1/simulations/{state['id']}/advance", json={'revision': state['revision'], 'days': 1}, headers={'Idempotency-Key': 'over'}).status_code == 422
        other, token = store.new_session(); client.cookies.set('farmtact_session', token)
        assert client.get(f"/api/v1/simulations/{state['id']}").status_code == 404
        assert client.get(f"/api/v1/simulations/{state['id']}/events").status_code == 404


def test_replan_preserves_executed_tasks_and_inventory(accepted_plan):
    client, store, tenant, run, _ = setup_world(accepted_plan)
    with client:
        state = post(client, '/api/v1/simulations', {'run_id': run['id']})
        state = post(client, f"/api/v1/simulations/{state['id']}/advance", dict(revision=state['revision'], days=7))
        before = deepcopy(state)
        state = post(client, f"/api/v1/simulations/{state['id']}/replan", dict(revision=state['revision']), 'replan')
        assert state['inventory'] == before['inventory']
        assert state['completed_task_ids'] == before['completed_task_ids']
        assert state['cash_sgd'] == before['cash_sgd']
        assert state['clock_date'] == before['clock_date']
        state = post(client, f"/api/v1/simulations/{state['id']}/advance", dict(revision=state['revision'], days=1))
        assert state['days_executed'] == 8
        assert set(before['completed_task_ids']) <= set(state['completed_task_ids'])
        assert state['totals']['delivered_kg'] >= before['totals']['delivered_kg']


def test_growth_states_distinguish_schedule_from_recorded_harvest():
    a = dict(sow_date='2026-09-01', transplant_date='2026-09-08', harvest_date='2026-09-29')
    recipe = dict(sanitation_days=2)
    assert crop_state(a, recipe, '2026-08-31')['stage'] == 'empty'
    assert crop_state(a, recipe, '2026-09-07')['stage'] == 'nursery'
    assert crop_state(a, recipe, '2026-09-08')['stage'] == 'growing'
    assert crop_state(a, recipe, '2026-09-29')['stage'] == 'ready'
    assert crop_state(a, recipe, '2026-10-02')['stage'] == 'ready'  # no harvest event
    assert crop_state(a, recipe, '2026-09-29', harvested=True)['stage'] == 'harvested'
    assert crop_state(a, recipe, '2026-10-01', harvested=True)['stage'] == 'sanitation'
    assert crop_state(a, recipe, '2026-10-02', harvested=True)['stage'] == 'empty'
    assert crop_state(a, recipe, '2026-10-01', projection=True)['stage'] == 'sanitation'


def test_explicit_sqlite_adapter_keeps_transactions_atomic_with_polling_workers(accepted_plan):
    client, store, tenant, run, _ = setup_world(accepted_plan)
    token=client.cookies.get('farmtact_session')
    with TestClient(create_app(store,start_worker=True)) as c:
        c.cookies.set('farmtact_session',token)
        created=post(c,'/api/v1/simulations',{'run_id':run['id']})
        assert c.get(f"/api/v1/simulations/{created['id']}").json()==created
        state=created
        for _ in range(4):
            state=post(c,f"/api/v1/simulations/{state['id']}/advance",dict(revision=state['revision'],days=14))
            assert c.get(f"/api/v1/simulations/{state['id']}").json()==state
        assert state['days_executed']==56
