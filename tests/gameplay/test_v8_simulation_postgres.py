"""PostgreSQL serialization, tenant isolation, and restart checks for execution worlds.

This module deliberately uses a dedicated database.  It never starts a queue
worker and therefore cannot claim jobs from the regular test database.
"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import secrets

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import delete, func, select

from packages.fixtures import synthetic_farm
from packages.planner import plan
from services.api.app import MissionRequest, create_app, create_mission
from services.api.simulation import EVENTS, RECEIPTS, WORLDS
from services.api.store import Store, events as run_events, farms, runs, tenants


DATABASE_URL = "postgresql+psycopg://sprite@/farmtact_simulation_test?host=/tmp/farmtact-pg"


def _client(store, token):
    client = TestClient(create_app(store, start_worker=False))
    client.cookies.set("farmtact_session", token)
    return client


@pytest.fixture(scope="module")
def accepted_plan():
    farm = synthetic_farm()
    result = plan(farm, time_limit=1)
    strategy = next(row for row in result["strategies"] if row["name"] == "Balanced")
    assert strategy["status"] == "FEASIBLE"
    return farm, result, strategy


def test_postgres_world_advance_is_serialized_isolated_and_durable(accepted_plan):
    farm, result, strategy = accepted_plan
    store = Store(DATABASE_URL)
    assert store.engine.dialect.name == "postgresql"
    tenant, token = store.new_session()
    other_tenant = None
    world_id = None
    try:
        store.save_farm(tenant, farm.model_dump(mode="json"))
        run = create_mission(
            store,
            tenant,
            MissionRequest(council=False),
            f"simulation-pg-mission-{secrets.token_hex(8)}",
        )
        run = store.get_run(tenant, run["id"])
        run.update(deepcopy(result))
        run.update(status="ACCEPTED_FOR_SIMULATION", accepted_strategy_id=strategy["id"])
        store.save_run(tenant, run)

        with _client(store, token) as client:
            response = client.post(
                "/api/v1/simulations",
                json={"run_id": run["id"]},
                headers={"Idempotency-Key": f"create-{secrets.token_hex(8)}"},
            )
            assert response.status_code == 201, response.text
            created = response.json()
            world_id = created["id"]

        same_key = f"same-advance-{secrets.token_hex(8)}"
        same_body = {"revision": 0, "days": 1}

        def same_advance(_):
            local_store = Store(DATABASE_URL)
            try:
                with _client(local_store, token) as client:
                    response = client.post(
                        f"/api/v1/simulations/{world_id}/advance",
                        json=same_body,
                        headers={"Idempotency-Key": same_key},
                    )
                    return response.status_code, response.json()
            finally:
                local_store.engine.dispose()

        with ThreadPoolExecutor(max_workers=6) as pool:
            same_results = list(pool.map(same_advance, range(6)))
        assert {status for status, _ in same_results} == {200}
        assert all(payload == same_results[0][1] for _, payload in same_results)
        first_advance = same_results[0][1]
        assert first_advance["revision"] == 1
        assert first_advance["days_executed"] == 1

        race_body = {"revision": 1, "days": 1}

        def changed_key_advance(index):
            local_store = Store(DATABASE_URL)
            try:
                with _client(local_store, token) as client:
                    response = client.post(
                        f"/api/v1/simulations/{world_id}/advance",
                        json=race_body,
                        headers={"Idempotency-Key": f"changed-{index}-{secrets.token_hex(6)}"},
                    )
                    return response.status_code, response.json()
            finally:
                local_store.engine.dispose()

        with ThreadPoolExecutor(max_workers=2) as pool:
            race_results = list(pool.map(changed_key_advance, range(2)))
        assert sorted(status for status, _ in race_results) == [200, 409]
        race_winner = next(payload for status, payload in race_results if status == 200)
        assert race_winner["revision"] == 2
        assert race_winner["days_executed"] == 2

        # A receipt remains an immutable historical response after later changes.
        with _client(store, token) as client:
            replay = client.post(
                f"/api/v1/simulations/{world_id}/advance",
                json=same_body,
                headers={"Idempotency-Key": same_key},
            )
            assert replay.status_code == 200
            assert replay.json() == first_advance
            current = client.get(f"/api/v1/simulations/{world_id}").json()
        assert current == race_winner

        with store.connection() as connection:
            assert connection.execute(
                select(func.count()).select_from(RECEIPTS).where(
                    RECEIPTS.c.tenant_id == tenant, RECEIPTS.c.key == same_key
                )
            ).scalar_one() == 1
            event_rows = connection.execute(
                select(EVENTS.c.payload).where(
                    EVENTS.c.tenant_id == tenant, EVENTS.c.world_id == world_id
                ).order_by(EVENTS.c.sequence)
            ).scalars().all()
        closed = [event for event in event_rows if event["type"] == "day_closed"]
        assert len(closed) == 2
        assert len({event["date"] for event in closed}) == 2
        assert all(event["ledger"]["balance_error"] == 0 for event in closed)
        assert sum(float(lot["quantity_kg"]) for lot in current["inventory"]) == pytest.approx(
            closed[-1]["ledger"]["closing_kg"]
        )

        other_tenant, other_token = store.new_session()
        store.save_farm(other_tenant, farm.model_dump(mode="json"))
        with _client(store, other_token) as other:
            assert other.get(f"/api/v1/simulations/{world_id}").status_code == 404
            assert other.get(f"/api/v1/simulations/{world_id}/events").status_code == 404
            assert other.post(
                f"/api/v1/simulations/{world_id}/advance",
                json={"revision": 2, "days": 1},
                headers={"Idempotency-Key": "other-tenant"},
            ).status_code == 404

        reopened = Store(DATABASE_URL)
        try:
            with _client(reopened, token) as client:
                durable = client.get(f"/api/v1/simulations/{world_id}")
                assert durable.status_code == 200
                assert durable.json() == current
                durable_events = client.get(
                    f"/api/v1/simulations/{world_id}/events", params={"limit": 200}
                ).json()
                assert durable_events["event_sequence"] == len(event_rows)
                assert durable_events["events"] == event_rows
        finally:
            reopened.engine.dispose()
    finally:
        with store.engine.begin() as connection:
            if world_id is not None:
                connection.execute(delete(EVENTS).where(EVENTS.c.world_id == world_id))
                connection.execute(delete(WORLDS).where(WORLDS.c.id == world_id))
            connection.execute(delete(RECEIPTS).where(RECEIPTS.c.tenant_id == tenant))
            connection.execute(delete(run_events).where(run_events.c.tenant_id == tenant))
            connection.execute(delete(runs).where(runs.c.tenant_id == tenant))
            connection.execute(delete(farms).where(farms.c.tenant_id == tenant))
            if other_tenant is not None:
                connection.execute(delete(RECEIPTS).where(RECEIPTS.c.tenant_id == other_tenant))
                connection.execute(delete(farms).where(farms.c.tenant_id == other_tenant))
                connection.execute(delete(tenants).where(tenants.c.id == other_tenant))
            connection.execute(delete(tenants).where(tenants.c.id == tenant))
        store.engine.dispose()
