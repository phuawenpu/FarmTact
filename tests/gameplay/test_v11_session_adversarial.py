"""Adversarial state-boundary tests for the V11 guided planning session."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from packages.planner.engine import apply_seasonal_assumptions
from services.api.app import create_app
from services.api import planning_sessions
from services.api.planning_sessions import JOBS, VERSIONS, execute_job, get_result, get_session
from services.api.retention import prune_expired_tenants
from services.api.simulation import WORLDS, get_world
from services.api.store import Store, tenants


@pytest.fixture
def env():
    store = Store("sqlite://")
    with TestClient(create_app(store, start_worker=False)) as client:
        client.get("/api/v1/bootstrap")
        tenant = store.authenticate(client.cookies.get("farmtact_session"))
        yield client, store, tenant
    store.engine.dispose()


def _post(client, path, body, key=None):
    return client.post(
        "/api/v1/planning-sessions" + path,
        json=body,
        headers={"Idempotency-Key": key or uuid4().hex},
    )


def _create(client):
    response = _post(client, "", {})
    assert response.status_code == 201, response.text
    return response.json()


def _calculate(client, store, tenant):
    session = _create(client)
    queued = _post(client, f"/{session['id']}/calculate", {"revision": session["revision"]})
    assert queued.status_code == 202, queued.text
    execute_job(store, tenant, queued.json()["job"]["id"])
    session = client.get(f"/api/v1/planning-sessions/{session['id']}").json()
    assert session["status"] == "COMPLETED"
    return session


def _advance(client, session, days=1):
    response = _post(
        client, f"/{session['id']}/advance",
        {"revision": session["revision"], "days": days},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_negative_recorded_cash_refuses_replan_instead_of_clamping(env):
    client, store, tenant = env
    session = _advance(client, _calculate(client, store, tenant))
    world = get_world(store, tenant, session["world_id"])
    world["cash_sgd"] = -0.01
    with store.connection(write=True) as connection:
        connection.execute(
            update(WORLDS).where(WORLDS.c.id == world["id"], WORLDS.c.tenant_id == tenant)
            .values(payload=world)
        )

    response = _post(
        client, f"/{session['id']}/disrupt",
        {"revision": session["revision"], "assumptions": {}},
    )
    assert response.status_code == 409
    assert "cash is negative" in response.json()["detail"]
    after = get_session(store, tenant, session["id"])
    assert after["result_id"] == session["result_id"]
    assert after["job"]["status"] == "COMPLETED"


def test_recorded_harvest_marker_survives_replan_input_and_seasonal_projection(env):
    client, store, tenant = env
    session = _calculate(client, store, tenant)
    # Advance to the first scheduled harvest. It remains in its sanitation
    # occupancy window, so it is still part of the next remaining-plan input.
    session = _advance(client, session)
    world = get_world(store, tenant, session["world_id"])
    target = min(
        row["harvest_date"] for row in world["segment_allocations"]
        if row["harvest_date"] >= world["clock_date"]
    )
    while session["simulation"]["clock_date"] < target:
        session = _advance(client, session)
    world = get_world(store, tenant, session["world_id"])
    harvest_task = next(task for task in world["completed_task_ids"] if task.endswith(":harvest"))
    allocation_id = harvest_task.rsplit(":", 1)[0]
    historical = next(row for row in world["segment_allocations"] if row["id"] == allocation_id)

    snapshot, kwargs = planning_sessions._remaining_input(
        store, tenant, get_session(store, tenant, session["id"])
    )
    locked = next(row for row in kwargs["locked_allocations"] if row["id"] == allocation_id)
    assert locked["harvest_recorded"] is True
    assumption = [{
        "crop_id": locked["crop_id"], "system": "sheltered_hydroponic",
        "start_date": locked["harvest_date"], "end_date": locked["harvest_date"],
        "yield_percent": 50, "delay_days": 14, "reason": "adversarial replay",
        "provenance": "synthetic_assumption",
    }]
    projected = apply_seasonal_assumptions(
        planning_sessions.Farm.model_validate(snapshot), [locked], assumption
    )[0]
    assert projected["harvest_date"] == historical["harvest_date"]
    assert projected["expected_kg"] == historical["expected_kg"]
    assert projected["harvest_recorded"] is True


def test_running_cancel_discards_late_numerical_result(env, monkeypatch):
    client, store, tenant = env
    session = _create(client)
    queued = _post(client, f"/{session['id']}/calculate", {"revision": session["revision"]}).json()
    job_id = queued["job"]["id"]

    def late_result(*_args, **_kwargs):
        running = client.get(f"/api/v1/planning-sessions/{session['id']}").json()
        cancelled = _post(
            client, f"/{session['id']}/cancel", {"revision": running["revision"]}, "cancel-running"
        )
        assert cancelled.status_code == 200
        return {"input_snapshot": deepcopy(running["farm"]), "strategies": [{"id": "late"}],
                "selected_strategy_id": "late"}

    monkeypatch.setattr(planning_sessions, "calculate", late_result)
    execute_job(store, tenant, job_id)

    saved = get_session(store, tenant, session["id"])
    assert saved["status"] == "CANCELLED"
    assert saved["result_id"] is None
    assert get_result(store, tenant, job_id) is None
    with store.connection() as connection:
        assert connection.execute(
            select(JOBS.c.status).where(JOBS.c.id == job_id)
        ).scalar_one() == "CANCELLED"
        assert connection.execute(
            select(VERSIONS.c.id).where(VERSIONS.c.id == job_id)
        ).first() is None


def test_stale_revision_and_idempotency_cannot_mutate_newer_state(env):
    client, store, tenant = env
    session = _create(client)
    body = {"revision": session["revision"]}
    first = _post(client, f"/{session['id']}/calculate", body, "stable-calculate")
    assert first.status_code == 202
    replay = _post(client, f"/{session['id']}/calculate", body, "stable-calculate")
    assert replay.status_code == 202 and replay.json() == first.json()
    assert _post(
        client, f"/{session['id']}/calculate", {"revision": 999}, "stable-calculate"
    ).status_code == 409
    assert _post(
        client, f"/{session['id']}/calculate", body, "new-stale-key"
    ).status_code == 409
    saved = get_session(store, tenant, session["id"])
    assert saved["revision"] == first.json()["revision"]
    assert saved["job"]["id"] == first.json()["job"]["id"]


def test_retention_skips_expired_tenant_with_active_guided_job(env):
    client, store, tenant = env
    session = _create(client)
    queued = _post(client, f"/{session['id']}/calculate", {"revision": session["revision"]})
    assert queued.status_code == 202
    as_of = datetime(2026, 12, 31, 12, tzinfo=timezone.utc)
    with store.connection(write=True) as connection:
        connection.execute(
            update(tenants).where(tenants.c.id == tenant)
            .values(created_at=(as_of - timedelta(days=60)).isoformat())
        )

    report = prune_expired_tenants(
        store, retained_days=30, limit=20, apply=True, as_of=as_of
    )
    skipped = next(row for row in report["skipped_active"] if row["tenant_id"] == tenant)
    assert "guided_planning" in skipped["active_job_types"]
    assert get_session(store, tenant, session["id"])["status"] == "QUEUED"


def test_budget_blocked_review_records_zero_calls_and_never_invokes_provider(env, monkeypatch):
    client, store, tenant = env
    session = _calculate(client, store, tenant)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-credential-never-sent")
    monkeypatch.setattr(store, "reserve_calls", lambda *args, **kwargs: False)
    invoked = []
    monkeypatch.setattr(
        "services.api.planning_council.review_plan",
        lambda *args, **kwargs: invoked.append(True),
    )
    queued = _post(client, f"/{session['id']}/review", {"revision": session["revision"]})
    assert queued.status_code == 202
    execute_job(store, tenant, queued.json()["job"]["id"])

    after = client.get(f"/api/v1/planning-sessions/{session['id']}").json()
    assert after["review"]["status"] == "blocked"
    assert after["review"]["request_count"] == 0
    assert invoked == []
    assert after["selected_strategy_id"] == session["selected_strategy_id"]
