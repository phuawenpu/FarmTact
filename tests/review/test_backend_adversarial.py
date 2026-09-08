"""Independent A11 adversarial tests for backend safety and numerical invariants."""

from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from packages.contracts import Farm
from packages.fixtures import synthetic_farm
from packages.ingestion.context import _restore_cached_source
from packages.ingestion.models import PublicContext, SnapshotRecord
from packages.models import forecast, scenarios
from packages.planner import plan, simulate, validate_allocations
from packages.planner.engine import allocations_existing, candidates
from services.api.app import create_app
from services.api.store import Store


def test_actual_due_date_before_lead_time_cannot_be_covered_by_new_sowing() -> None:
    farm = synthetic_farm()
    due = farm.cutoff.date() + timedelta(days=20)
    farm.orders = [
        farm.orders[0].model_copy(update={"due_date": due, "quantity_kg": Decimal("1000")})
    ]
    result = plan(farm, time_limit=0.3)
    for strategy in result["strategies"]:
        assert strategy["weekly"][2]["shortfall_kg"] > 0
        assert not any(
            not action["executed"] and action["harvest_date"] <= due.isoformat()
            for action in strategy["allocations"]
        )


def test_validator_independently_rejects_capacity_cash_and_labour_overruns() -> None:
    farm = synthetic_farm()
    candidate = candidates(farm)[0]
    duplicate = dict(candidate, id="same-bed-second-action")
    allocations = allocations_existing(farm) + [candidate, duplicate]
    farm.resources.nursery_sites = 0
    farm.resources.labour_hours_per_week = Decimal("0")
    farm.resources.cash_sgd = Decimal("0")
    codes = {violation["constraint_code"] for violation in validate_allocations(farm, allocations)}
    assert {"BED_OCCUPANCY", "NURSERY_CAPACITY", "LABOUR_CAPACITY", "CASH_BUDGET"} <= codes


def test_daily_inventory_ledger_preserves_mass_balance() -> None:
    farm = synthetic_farm()
    demand = forecast(farm)["demand"]
    result = simulate(farm, allocations_existing(farm), demand, scenarios()[0])
    for row in result["ledger"]:
        assert row["opening_kg"] + row["harvest_kg"] == pytest.approx(
            row["delivered_kg"] + row["disposed_kg"] + row["closing_kg"], abs=1e-6
        )


def test_locked_executed_work_cannot_be_removed_or_rewritten() -> None:
    farm = synthetic_farm()
    original = allocations_existing(farm)
    removed = original[1:]
    changed = copy.deepcopy(original)
    changed[0]["transplant_date"] = (farm.cutoff.date() + timedelta(days=1)).isoformat()
    assert "EXECUTED_ACTION_CHANGED" in {
        item["constraint_code"] for item in validate_allocations(farm, removed)
    }
    assert "EXECUTED_ACTION_CHANGED" in {
        item["constraint_code"] for item in validate_allocations(farm, changed)
    }


def test_booked_crop_without_recipe_is_rejected_or_preserved_as_unresolved_demand() -> None:
    """A booked crop without a recipe must be unresolved, never absent from demand."""
    payload = synthetic_farm().model_dump(mode="json")
    payload["recipes"] = [recipe for recipe in payload["recipes"] if recipe["crop_id"] == "caixin"]
    payload["batches"] = [batch for batch in payload["batches"] if batch["recipe_id"] == "caixin-demo-v1"]
    payload["orders"] = [next(order for order in payload["orders"] if order["crop_id"] == "pak_choi")]
    try:
        farm = Farm.model_validate(payload)
    except ValidationError:
        return
    booked = sum(float(order.quantity_kg - order.cancelled_kg) for order in farm.orders)
    represented = sum(
        row["confirmed_kg"] for row in forecast(farm)["demand"] if row["crop_id"] == "pak_choi"
    )
    assert represented == pytest.approx(booked)


def test_singapore_cutoff_date_drives_daily_planning_calendar() -> None:
    cutoff = datetime(2026, 9, 8, 18, 0, tzinfo=timezone.utc)  # 02:00 on 9 Sep in Singapore
    farm = synthetic_farm(cutoff=cutoff)
    result = simulate(farm, allocations_existing(farm), forecast(farm)["demand"], scenarios()[1])
    assert result["ledger"][0]["date"] == "2026-09-09"


def _new_api() -> tuple[TestClient, Store]:
    store = Store("sqlite://")
    client = TestClient(create_app(store, start_worker=False))
    client.__enter__()
    client.get("/api/v1/bootstrap")
    return client, store


def test_run_and_strategy_idor_is_tenant_scoped() -> None:
    first, store = _new_api()
    try:
        response = first.post(
            "/api/v1/planning-runs",
            json={"council": False},
            headers={"Idempotency-Key": "tenant-a-run"},
        )
        run_id = response.json()["id"]
        second = TestClient(create_app(store, start_worker=False))
        with second:
            second.get("/api/v1/bootstrap")
            assert second.get(f"/api/v1/planning-runs/{run_id}").status_code == 404
            assert second.get("/api/v1/strategies/not-owned").status_code == 404
    finally:
        first.__exit__(None, None, None)


def test_event_tenant_must_match_owning_run() -> None:
    store = Store("sqlite://")
    tenant_a, _ = store.new_session()
    tenant_b, _ = store.new_session()
    payload = {
        "id": "run-a",
        "status": "CREATED",
        "created_at": "2026-09-08T00:00:00+00:00",
        "warnings": [],
    }
    store.create_run(tenant_a, "key-a", "hash-a", payload)
    with pytest.raises((KeyError, ValueError, LookupError)):
        store.append_event(tenant_b, "run-a", "attacker_event", {"value": "cross-tenant"})
    assert store.get_events(tenant_b, "run-a") == []


def test_replan_creation_failure_rolls_back_farm_mutation(monkeypatch: pytest.MonkeyPatch) -> None:
    client, store = _new_api()
    try:
        tenant = store.authenticate(client.cookies.get("farmtact_session"))
        created = client.post(
            "/api/v1/planning-runs",
            json={"council": False},
            headers={"Idempotency-Key": "parent"},
        ).json()
        parent = store.get_run(tenant, created["id"])
        parent["status"] = "ACCEPTED_FOR_SIMULATION"
        parent["council_requested"] = False
        store.save_run(tenant, parent)
        version_before = store.latest_farm(tenant)["version"]

        def fail_create(*_args, **_kwargs):
            raise ValueError("injected run creation conflict")

        monkeypatch.setattr(store, "create_run", fail_create)
        response = client.post(
            f"/api/v1/planning-runs/{created['id']}/replan",
            json={"disruption": "crop_delay"},
            headers={"Idempotency-Key": "failed-replan"},
        )
        assert response.status_code == 409
        assert store.latest_farm(tenant)["version"] == version_before
    finally:
        client.__exit__(None, None, None)


def test_replay_is_read_only_and_does_not_reserve_inference(monkeypatch: pytest.MonkeyPatch) -> None:
    client, store = _new_api()
    try:
        tenant = store.authenticate(client.cookies.get("farmtact_session"))
        created = client.post(
            "/api/v1/planning-runs",
            json={"council": False},
            headers={"Idempotency-Key": "replay-parent"},
        ).json()
        run = store.get_run(tenant, created["id"])
        run.update(status="FAILED", execution_mode="test", strategies=[], events=[])
        store.save_run(tenant, run)
        before = copy.deepcopy(store.get_run(tenant, created["id"]))
        monkeypatch.setattr(store, "reserve_calls", lambda *_: pytest.fail("replay reserved paid inference"))
        response = client.get(f"/api/v1/planning-runs/{created['id']}/replay")
        assert response.status_code == 200
        assert response.json()["inference_origin"] == "stored_events"
        assert store.get_run(tenant, created["id"]) == before
    finally:
        client.__exit__(None, None, None)


def test_cached_rows_keep_their_immutable_snapshot_in_refreshed_context() -> None:
    snapshot = SnapshotRecord(
        snapshot_id="d01-snapshot",
        source_id="D01",
        request_url="https://api-open.data.gov.sg/v2/real-time/api/rainfall",
        query={},
        retrieved_at="2026-09-08T00:00:00+00:00",
        http_status=200,
        sha256="a" * 64,
        byte_count=10,
        media_type="application/json",
        relative_path="raw/d01/a.json",
        response_headers={},
        licence_state="verified_singapore_open_data_licence",
    )
    source = {
        "source_id": "D01",
        "status": "validated",
        "freshness": "fresh",
        "snapshot_id": snapshot.snapshot_id,
    }
    row = {
        "observation_id": "obs-1",
        "source_id": "D01",
        "snapshot_id": snapshot.snapshot_id,
        "raw_locator": "data.readings[0]",
    }
    previous = PublicContext(
        schema_version="1.0.0",
        built_at="2026-09-08T00:00:00+00:00",
        execution_mode="live_public_refresh",
        sources=[source],
        snapshots=[snapshot],
        weather_observations=[row],
    )
    refreshed = PublicContext(
        schema_version="1.0.0",
        built_at="2026-09-08T01:00:00+00:00",
        execution_mode="live_public_refresh",
    )
    assert _restore_cached_source(
        refreshed, previous, "D01", "provider unavailable", "2026-09-08T01:00:00+00:00"
    )
    referenced = {item["snapshot_id"] for item in refreshed.weather_observations}
    retained = {item.snapshot_id for item in refreshed.snapshots}
    assert referenced <= retained


def test_budget_reservation_rejects_nonpositive_counts() -> None:
    store = Store("sqlite://")
    with pytest.raises(ValueError):
        store.reserve_calls(0)
    with pytest.raises(ValueError):
        store.reserve_calls(-1)
