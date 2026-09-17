"""Tenant-owned synthetic execution worlds with a durable civil-date clock.

Daily transition arithmetic comes from the same FEFO allocator as planning. A
forecast is not an execution event: only advance commits tasks, lots and money.
Replanning freezes a new future trace from the actual synthetic closing state.
"""
from copy import deepcopy
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
import secrets
from zoneinfo import ZoneInfo

from fastapi import HTTPException, Request
from pydantic import Field
from sqlalchemy import Column, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, Table, UniqueConstraint, select, update

from packages.contracts import Farm, InventoryLot, Strict, content_hash
from packages.growth import crop_state
from services.api.numerical_worker import plan
from packages.planner.engine import simulate
from services.api.store import metadata, now

VERSION = 'synthetic-execution-v1'
WORLDS = Table('simulation_worlds', metadata,
    Column('id', String, primary_key=True), Column('tenant_id', String, ForeignKey('tenants.id'), nullable=False),
    Column('payload', JSON, nullable=False), UniqueConstraint('id', 'tenant_id'))
EVENTS = Table('simulation_events', metadata,
    Column('world_id', String, primary_key=True), Column('sequence', Integer, primary_key=True),
    Column('tenant_id', String, ForeignKey('tenants.id'), nullable=False), Column('payload', JSON, nullable=False),
    ForeignKeyConstraint(['world_id', 'tenant_id'], ['simulation_worlds.id', 'simulation_worlds.tenant_id'], ondelete='CASCADE'))
RECEIPTS = Table('simulation_receipts', metadata,
    Column('tenant_id', String, ForeignKey('tenants.id'), primary_key=True), Column('key', String, primary_key=True),
    Column('request_hash', String, nullable=False), Column('payload', JSON, nullable=False))


class CreateWorld(Strict):
    run_id: str = Field(min_length=1, max_length=100)


class AdvanceWorld(Strict):
    revision: int = Field(ge=0)
    days: int = Field(default=1, ge=1, le=14)


class ReplanWorld(Strict):
    revision: int = Field(ge=0)


def cents(value):
    return int((Decimal(str(value)) * 100).quantize(Decimal('1'), rounding=ROUND_HALF_UP))


def get_world(store, tenant, id):
    with store.connection() as c:
        return c.execute(select(WORLDS.c.payload).where(WORLDS.c.tenant_id == tenant, WORLDS.c.id == id)).scalar_one_or_none()


def public_world(world):
    result = {k: deepcopy(v) for k, v in world.items() if k not in ('trace', 'segment_farm', 'segment_allocations')}
    farm = Farm.model_validate(world['segment_farm'])
    recipes = {r.id: r for r in farm.recipes}
    harvested = set(world['completed_task_ids'])
    day = world['clock_date'] or world['start_date']
    beds = []
    for bed in farm.beds:
        allocations = [a for a in world['segment_allocations'] if a['bed_id'] == bed.id]
        states = [(a, crop_state(a, recipes[a['recipe_id']], day, harvested=f"{a['id']}:harvest" in harvested)) for a in allocations]
        active = [(a, state) for a, state in states if state['stage'] != 'empty']
        active.sort(key=lambda pair: (pair[1]['stage'] == 'nursery', pair[0]['sow_date'], pair[0]['id']))
        item = dict(id=bed.id, name=bed.name, area_m2=float(bed.area_m2), stage='empty', progress=0)
        if active:
            a, state = active[0]
            item.update(state, allocation_id=a['id'], crop_id=a['crop_id'], sow_date=a['sow_date'],
                        transplant_date=a['transplant_date'], harvest_date=a['harvest_date'])
        item['nursery_allocations'] = [a['id'] for a, state in active if state['stage'] == 'nursery']
        beds.append(item)
    result['beds'] = beds
    result['simulation_only'] = True
    result['inference_triggered'] = False
    result['state_hash'] = content_hash({k: world[k] for k in ('revision','clock_date','inventory','completed_task_ids','totals','cash_sgd','segment_farm','segment_allocations')} | {'harvest_lot_origins': world.get('harvest_lot_origins', {})})
    return result


def append_event(store, tenant, world, kind, civil_date, **body):
    world['event_sequence'] += 1
    event = dict(sequence=world['event_sequence'], type=kind, date=str(civil_date),
                 recorded_at=now(), origin='synthetic', engine_version=VERSION, **body)
    with store.connection(write=True) as c:
        c.execute(EVENTS.insert().values(world_id=world['id'], sequence=event['sequence'], tenant_id=tenant, payload=event))
    return event


def day_costs(farm, allocations, day, row, scenario):
    recipes = {r.id: r for r in farm.recipes}
    inputs = Decimal(0); labour = Decimal(0)
    for a in allocations:
        recipe = recipes[a['recipe_id']]; area = Decimal(str(a['area_m2']))
        if a['sow_date'] == day:
            labour += area * recipe.sow_labour_hours_per_m2 * 12
            if not a.get('executed'):
                # Planner reserves inputs rounded upward per full-bed action.
                from math import ceil
                inputs += Decimal(ceil(area * recipe.cost_sgd_per_m2 * 100)) / 100
        if a['harvest_date'] == day:
            labour += Decimal(str(a['expected_kg'])) * Decimal(str(scenario['yield_factor'])) * recipe.harvest_labour_hours_per_kg * 12
    packing = Decimal(str(row['delivered_kg'])) * Decimal('.30')
    disposal = Decimal(str(row['disposed_kg'])) * Decimal('.15')
    return dict(inputs_sgd=str(inputs), labour_sgd=str(labour), packing_sgd=str(packing), disposal_sgd=str(disposal))


def advance(store, tenant, world, days):
    remaining = len(world['trace']['ledger']) - world['segment_days_executed']
    if days > remaining:
        raise HTTPException(422, f'Only {remaining} unexecuted days remain')
    before_view = public_world(world)
    before = {key: before_view[key] for key in ('beds', 'inventory', 'totals', 'cash_sgd', 'clock_date')}
    farm = Farm.model_validate(world['segment_farm'])
    recipes = {r.id: r for r in farm.recipes}
    for index in range(world['segment_days_executed'], world['segment_days_executed'] + days):
        row = deepcopy(world['trace']['ledger'][index]); day = row['date']
        lot_origins = world.setdefault('harvest_lot_origins', {})
        old_stock = sum(Decimal(str(l['quantity_kg'])) for l in world['inventory'])
        if old_stock != Decimal(str(row['opening_kg'])):
            raise ValueError('Execution opening inventory does not match frozen trace')
        for a in world['segment_allocations']:
            dates = dict(sow=a['sow_date'], transplant=a['transplant_date'], harvest=a['harvest_date'],
                         sanitation_complete=str(date.fromisoformat(a['harvest_date']) + timedelta(days=recipes[a['recipe_id']].sanitation_days)))
            for task, due in dates.items():
                task_id = f"{a['id']}:{task}"
                if due == day and task_id not in world['completed_task_ids']:
                    world['completed_task_ids'].append(task_id)
                    produced_lots = [item['lot_id'] for item in world['trace'].get('harvest_lot_origins', []) if item['source_allocation_id'] == a['id']] if task == 'harvest' else []
                    for lot_id in produced_lots: lot_origins[lot_id] = a['id']
                    append_event(store, tenant, world, 'task_completed', day, task_id=task_id, task=task, allocation_id=a['id'], bed_id=a['bed_id'], crop_id=a['crop_id'], produced_lot_ids=produced_lots)
        day_revenue = Decimal(0)
        for allocation in world['trace']['order_allocations']:
            if allocation['date'] == day:
                if allocation['price_sgd_per_kg'] is not None:
                    day_revenue += Decimal(str(allocation['delivered_kg'])) * Decimal(str(allocation['price_sgd_per_kg']))
                delivery = deepcopy({k: v for k, v in allocation.items() if k != 'date'})
                for lot in delivery.get('lot_allocations', []):
                    if lot['lot_id'] in lot_origins: lot['source_allocation_id'] = lot_origins[lot['lot_id']]
                append_event(store, tenant, world, 'demand_serviced', day, **delivery)
        costs = day_costs(farm, world['segment_allocations'], day, row, world['scenario'])
        # Keep decimal totals, round only the public balances. No cumulative penny drift.
        world['revenue_exact_sgd'] = str(Decimal(world['revenue_exact_sgd']) + day_revenue)
        world['cost_exact_sgd'] = str(Decimal(world['cost_exact_sgd']) + sum(Decimal(v) for v in costs.values()))
        world['cash_sgd'] = (cents(Decimal(world['opening_cash_sgd']) + Decimal(world['revenue_exact_sgd']) - Decimal(world['cost_exact_sgd']))) / 100
        world['revenue_sgd'] = cents(world['revenue_exact_sgd']) / 100
        world['cost_sgd'] = cents(world['cost_exact_sgd']) / 100
        world['inventory'] = deepcopy(world['trace']['inventory_snapshots'][index]['closing_lots'])
        for metric in ('harvest_kg', 'delivered_kg', 'disposed_kg', 'demand_kg'):
            world['totals'][metric] = round(world['totals'][metric] + row[metric], 6)
        row.update(cost_components=costs, cash_sgd=world['cash_sgd'])
        append_event(store, tenant, world, 'day_closed', day, ledger=row, closing_lots=world['inventory'])
        world['clock_date'] = day
        world['days_executed'] += 1
    world['segment_days_executed'] += days
    world['revision'] += 1
    world['status'] = 'COMPLETED' if world['clock_date'] == world['end_date'] else 'ACTIVE'
    world['updated_at'] = now()
    world['state_hash'] = content_hash({k: world[k] for k in ('revision', 'clock_date', 'inventory', 'completed_task_ids', 'totals', 'cash_sgd')})
    after_view = public_world(world)
    after = {key: after_view[key] for key in ('beds', 'inventory', 'totals', 'cash_sgd', 'clock_date')}
    old_beds = {bed['id']: bed for bed in before['beds']}
    world['scene_transition'] = dict(
        event_id=f"simulation:{world['id']}:event:{world['event_sequence']}",
        entity_ids=[bed['id'] for bed in after['beds'] if bed != old_beds.get(bed['id'])],
        effective_date=world['clock_date'], before=before, after=after,
        fact_differences={**{key: round(after['totals'][key] - before['totals'][key], 6)
                            for key in after['totals']},
                          'cash_sgd': round(after['cash_sgd'] - before['cash_sgd'], 2)},
        outcome_basis='recorded_simulation', inference_triggered=False,
    )
    return world


def register(app, tenant):
    def owned(request, id):
        t = tenant(request); world = get_world(app.state.store, t, id)
        if not world: raise HTTPException(404, 'Simulation not found')
        return t, world

    def operation(request, t, body, scope):
        key = request.headers.get('Idempotency-Key', '')
        if not key or len(key) > 128: raise HTTPException(422, 'Idempotency-Key required, maximum 128 characters')
        digest = content_hash(dict(scope=scope, body=body.model_dump(mode='json')))
        with app.state.store.connection() as c:
            old = c.execute(select(RECEIPTS).where(RECEIPTS.c.tenant_id == t, RECEIPTS.c.key == key)).mappings().first()
        if old and old['request_hash'] != digest: raise HTTPException(409, 'Idempotency key reused with changed inputs')
        return key, digest, old['payload'] if old else None

    def finish(t, key, digest, world):
        result = public_world(world)
        with app.state.store.connection(write=True) as c:
            c.execute(update(WORLDS).where(WORLDS.c.id == world['id'], WORLDS.c.tenant_id == t).values(payload=world))
            c.execute(RECEIPTS.insert().values(tenant_id=t, key=key, request_hash=digest, payload=result))
        return result

    @app.get('/api/v1/simulations')
    def worlds(request: Request):
        t = tenant(request)
        with app.state.store.connection() as c:
            rows = c.execute(select(WORLDS.c.payload).where(WORLDS.c.tenant_id == t)).scalars().all()
        return dict(simulations=[dict(id=w['id'], revision=w['revision'], status=w['status'], run_id=w['run_id'], clock_date=w['clock_date'], days_executed=w['days_executed'], created_at=w['created_at']) for w in sorted(rows, key=lambda w: w['created_at'], reverse=True)], limit=8)

    @app.post('/api/v1/simulations', status_code=201)
    def create(body: CreateWorld, request: Request):
        t = tenant(request); store = app.state.store
        with store.transaction(t) as c:
            key, digest, replay = operation(request, t, body, 'create')
            if replay is not None: return replay
            if len(c.execute(select(WORLDS.c.id).where(WORLDS.c.tenant_id == t)).all()) >= 8:
                raise HTTPException(429, 'Eight simulation worlds per session maximum')
            run = store.get_run(t, body.run_id)
            if not run: raise HTTPException(404, 'Mission not found')
            if run['status'] != 'ACCEPTED_FOR_SIMULATION': raise HTTPException(409, 'An accepted planning mission is required')
            if store.latest_farm(t)['version'] != run['input_version']: raise HTTPException(409, 'Accepted mission inputs are stale')
            strategy = next(s for s in run['strategies'] if s['id'] == run['accepted_strategy_id'])
            farm = Farm.model_validate(run['input_snapshot'])
            if any(batch.harvest_date < farm.planning_date for batch in farm.batches):
                raise HTTPException(409, 'Snapshot contains overdue harvests without execution records; resolve them before starting a world')
            scenario = dict(id='execution-central', yield_factor=1.0, demand_factor=1.0, weight=1.0)
            from packages.models import forecast
            demand = run.get('forecast', {}).get('demand') or forecast(farm)['demand']
            trace = simulate(farm, strategy['allocations'], demand, scenario)
            world = dict(id=secrets.token_hex(16), engine_version=VERSION, revision=0, status='ACTIVE', run_id=run['id'],
                created_at=now(), updated_at=now(), clock_date=None, start_date=str(farm.planning_date), end_date=str(farm.planning_date + timedelta(days=farm.horizon_days - 1)),
                days_executed=0, segment_days_executed=0, input_hash=run['input_hash'], input_version=run['input_version'],
                segment_farm=farm.model_dump(mode='json'), segment_allocations=deepcopy(strategy['allocations']), trace=trace, scenario=scenario,
                strategy_id=strategy['id'], strategy_name=strategy['name'], plan_history=[], completed_task_ids=[], harvest_lot_origins={}, event_sequence=0,
                inventory=[l.model_dump(mode='json') for l in farm.inventory if l.harvested_date <= farm.planning_date],
                opening_cash_sgd=str(farm.resources.cash_sgd), cash_sgd=float(farm.resources.cash_sgd), revenue_exact_sgd='0', cost_exact_sgd='0', revenue_sgd=0, cost_sgd=0,
                totals=dict(harvest_kg=0, delivered_kg=0, disposed_kg=0, demand_kg=0),
                outcome_basis='deterministic_synthetic_schedule_and_scenario', real_operations_enabled=False)
            from services.api.provenance import runtime_provenance
            world['runtime_provenance']=runtime_provenance()
            for a in strategy['allocations']:
                for task, field in (('sow', 'sow_date'), ('transplant', 'transplant_date'), ('harvest', 'harvest_date')):
                    if a.get('executed') and a[field] < world['start_date']:
                        world['completed_task_ids'].append(f"{a['id']}:{task}")
            c.execute(WORLDS.insert().values(id=world['id'], tenant_id=t, payload=world))
            append_event(store, t, world, 'world_created', world['start_date'], run_id=run['id'], strategy_hash=content_hash(strategy), inherited_task_ids=world['completed_task_ids'])
            return finish(t, key, digest, world)

    @app.get('/api/v1/simulations/{id}')
    def read(id: str, request: Request):
        return public_world(owned(request, id)[1])

    @app.get('/api/v1/simulations/{id}/events')
    def events(id: str, request: Request, after: int = 0, limit: int = 100):
        t, world = owned(request, id)
        if after < 0 or not 1 <= limit <= 200: raise HTTPException(422, 'Invalid event cursor or limit')
        with app.state.store.connection() as c:
            rows = c.execute(select(EVENTS.c.payload).where(EVENTS.c.world_id == id, EVENTS.c.tenant_id == t, EVENTS.c.sequence > after).order_by(EVENTS.c.sequence).limit(limit + 1)).scalars().all()
        return dict(events=rows[:limit], next_cursor=rows[limit - 1]['sequence'] if len(rows) > limit else None, event_sequence=world['event_sequence'], inference_triggered=False)

    @app.post('/api/v1/simulations/{id}/advance')
    def step(id: str, body: AdvanceWorld, request: Request):
        t = tenant(request); store = app.state.store
        with store.transaction(t):
            key, digest, replay = operation(request, t, body, f'advance:{id}')
            if replay is not None: return replay
            _, world = owned(request, id)
            if str(world.get('run_id','')).startswith('planning-session:'):raise HTTPException(409, 'Advance through the owning guided planning mission')
            if world['revision'] != body.revision: raise HTTPException(409, 'Simulation revision changed; refresh before advancing')
            advance(store, t, world, body.days)
            return finish(t, key, digest, world)

    @app.post('/api/v1/simulations/{id}/replan')
    def replan(id: str, body: ReplanWorld, request: Request):
        t = tenant(request); store = app.state.store
        # Compute outside the tenant lock; commit only if the revision still matches.
        key, digest, replay = operation(request, t, body, f'replan:{id}')
        if replay is not None: return replay
        _, world = owned(request, id)
        if str(world.get('run_id','')).startswith('planning-session:'):raise HTTPException(409, 'Replan through the owning guided planning mission')
        if world['revision'] != body.revision: raise HTTPException(409, 'Simulation revision changed')
        if not world['clock_date']: raise HTTPException(409, 'Advance at least one day before replanning')
        if len(world['plan_history']) >= 12: raise HTTPException(429, 'Twelve replans per world maximum')
        start = date.fromisoformat(world['clock_date']) + timedelta(days=1)
        remaining = (date.fromisoformat(world['end_date']) - start).days + 1
        if remaining < 7: raise HTTPException(409, 'At least seven unexecuted days are required for a new planning horizon')
        farm = Farm.model_validate(world['segment_farm']).model_copy(deep=True)
        recipes = {r.id: r for r in farm.recipes}
        locks = [dict(a, executed=True) for a in world['segment_allocations'] if f"{a['id']}:sow" in world['completed_task_ids'] and date.fromisoformat(a['harvest_date']) + timedelta(days=recipes[a['recipe_id']].sanitation_days) >= start]
        farm.cutoff = datetime.combine(start, time.min, ZoneInfo(farm.timezone)); farm.horizon_days = remaining; farm.batches = []
        farm.inventory = [InventoryLot.model_validate(lot) for lot in world['inventory']]; farm.orders = [o for o in farm.orders if o.due_date >= start]
        farm.resources.cash_sgd = Decimal(str(max(0, world['cash_sgd'])))
        farm = Farm.model_validate(farm.model_dump(mode='json'))
        # Initial imported batch IDs are caller-controlled. Even an ID chosen to
        # mimic a future generated cycle cannot reuse an already recorded task.
        historical_ids = {task.rsplit(':', 1)[0] for task in world['completed_task_ids']}
        result = plan(farm, locked_allocations=locks, candidate_not_before=start,
                      excluded_candidate_ids=historical_ids)
        strategy = next((s for s in result['strategies'] if s['name'] == 'Balanced' and s['status'] == 'FEASIBLE'), None)
        if strategy is None: raise HTTPException(409, 'No feasible continuation; the existing future plan is preserved')
        trace = simulate(farm, strategy['allocations'], result['forecast']['demand'], world['scenario'])
        with store.transaction(t):
            key, digest, replay = operation(request, t, body, f'replan:{id}')
            if replay is not None: return replay
            _, current = owned(request, id)
            if current['revision'] != body.revision: raise HTTPException(409, 'Simulation advanced during calculation; computed plan was not applied')
            world['plan_history'].append(dict(revision=world['revision'], strategy_id=world['strategy_id'], input_hash=content_hash(world['segment_farm']), allocations_hash=content_hash(world['segment_allocations']), through_date=world['clock_date']))
            world.update(segment_farm=farm.model_dump(mode='json'), segment_allocations=strategy['allocations'], trace=trace, segment_days_executed=0, strategy_id=strategy['id'], strategy_name=strategy['name'], revision=world['revision'] + 1, updated_at=now())
            append_event(store, t, world, 'future_replanned', start, locked_allocation_ids=[a['id'] for a in locks], strategy_hash=content_hash(strategy), input_hash=content_hash(farm), inference_triggered=False)
            return finish(t, key, digest, world)
