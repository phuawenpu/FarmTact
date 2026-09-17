"""V13 tactile constraints use the existing planner and append an inverse event."""
from copy import deepcopy

import pytest
from sqlalchemy import update

from services.api import farm_workflow, planning_sessions
from packages.fixtures import synthetic_farm
from tests.gameplay.test_farm_workflow import setup


def reservation():
    return [{"kind": "planning_assumptions", "assumptions": {
        "reservations": [{"bed_id": "bed-07", "start_date": "2026-09-17", "end_date": "2026-11-11"}],
    }}]


def complete(adapter):
    adapter.session.update(result_id="job-1", status="COMPLETED",
                           revision=adapter.session["revision"] + 1, input_hash="farm-reserved")
    adapter.result["id"] = "job-1"


def test_inverse_is_new_revision_bound_proposal_and_original_history_remains(setup):
    store, tenant, _, adapter = setup
    proposal = farm_workflow.create_proposal(store, tenant, adapter=adapter,
        session_id="session-1", base_revision=2, changes=reservation(),
        idempotency_key="reserve-bed-07")
    assert proposal["inverse_changes"] == [{"kind": "planning_assumptions", "assumptions": {}}]
    applied = farm_workflow.apply_proposal(store, tenant, proposal["id"], adapter=adapter,
        expected_base_revision=2, idempotency_key="apply-bed-07")
    complete(adapter)

    inverse = farm_workflow.apply_inverse_proposal(store, tenant, proposal["id"], adapter=adapter,
        proposal_revision=applied["proposal_revision"], expected_session_revision=4,
        idempotency_key="undo-bed-07")
    assert inverse["status"] == "applied"
    assert inverse["inverse_of_proposal_id"] == proposal["id"]
    assert inverse["changes"] == [{"kind": "planning_assumptions", "assumptions": {}}]
    assert inverse["recalculation_job"]["status"] == "QUEUED"
    assert farm_workflow.apply_inverse_proposal(store, tenant, proposal["id"], adapter=adapter,
        proposal_revision=applied["proposal_revision"], expected_session_revision=4,
        idempotency_key="undo-bed-07") == inverse
    with store.connection() as connection:
        records = list(connection.execute(farm_workflow.PROPOSALS.select().where(
            farm_workflow.PROPOSALS.c.tenant_id == tenant)).mappings())
    assert len(records) == 2
    original = next(row["payload"] for row in records if row["id"] == proposal["id"])
    assert original["status"] == "applied" and original["inverse_proposal_id"] == inverse["id"]


def test_inverse_fails_closed_after_intervening_revision_or_for_other_tenant(setup):
    store, tenant, other, adapter = setup
    proposal = farm_workflow.create_proposal(store, tenant, adapter=adapter,
        session_id="session-1", base_revision=2, changes=reservation(), idempotency_key="reserve")
    applied = farm_workflow.apply_proposal(store, tenant, proposal["id"], adapter=adapter,
        expected_base_revision=2, idempotency_key="apply")
    complete(adapter)
    adapter.session["revision"] += 1
    with pytest.raises(ValueError, match="stale"):
        farm_workflow.apply_inverse_proposal(store, tenant, proposal["id"], adapter=adapter,
            proposal_revision=applied["proposal_revision"], expected_session_revision=5,
            idempotency_key="stale-undo")
    with pytest.raises(ValueError, match="not found"):
        farm_workflow.apply_inverse_proposal(store, other, proposal["id"], adapter=adapter,
            proposal_revision=applied["proposal_revision"], expected_session_revision=4,
            idempotency_key="foreign-undo")


def test_workflow_state_exposes_available_then_submitted_undo_reason(setup):
    store, tenant, _, adapter = setup
    proposal = farm_workflow.create_proposal(store, tenant, adapter=adapter,
        session_id="session-1", base_revision=2, changes=reservation(), idempotency_key="state-reserve")
    applied = farm_workflow.apply_proposal(store, tenant, proposal["id"], adapter=adapter,
        expected_base_revision=2, idempotency_key="state-apply")
    complete(adapter)
    with store.connection(write=True) as connection:
        connection.execute(update(planning_sessions.SESSIONS).where(
            planning_sessions.SESSIONS.c.id == adapter.session["id"],
            planning_sessions.SESSIONS.c.tenant_id == tenant).values(
                status="COMPLETED", payload=deepcopy(adapter.session)))
    current = next(item for item in farm_workflow.workflow_state(store, tenant)["proposals"]
                   if item["id"] == proposal["id"])
    assert current["undo"] == {"available": True, "reason": None, "expected_session_revision": 4}

    farm_workflow.apply_inverse_proposal(store, tenant, proposal["id"], adapter=adapter,
        proposal_revision=applied["proposal_revision"], expected_session_revision=4,
        idempotency_key="state-undo")
    after = next(item for item in farm_workflow.workflow_state(store, tenant)["proposals"]
                 if item["id"] == proposal["id"])
    assert after["undo"] == {"available": False, "reason": "Undo has already been submitted."}


def test_recalculated_consequences_follow_the_result_selected_strategy(setup):
    store, tenant, _, adapter = setup
    proposal = farm_workflow.create_proposal(
        store, tenant, adapter=adapter, session_id="session-1", base_revision=2,
        changes=reservation(), selected_strategy_id="balanced",
        idempotency_key="metric-binding-reserve",
    )
    farm_workflow.apply_proposal(
        store, tenant, proposal["id"], adapter=adapter,
        expected_base_revision=2, idempotency_key="metric-binding-apply",
    )
    result = {
        "id": "job-1",
        "strategies": [
            {"id": "lean-recalculated", "name": "Lean", "metrics": {
                "booked_requested_kg": 10, "booked_delivered_kg": 4,
                "closing_stock_kg": 1, "waste_kg": 1, "margin_sgd": 11,
            }},
            {"id": "balanced-recalculated", "name": "Balanced", "metrics": {
                "booked_requested_kg": 10, "booked_delivered_kg": 7,
                "closing_stock_kg": 2, "waste_kg": 2, "margin_sgd": 22,
            }},
        ],
    }
    adapter.session.update(
        result_id="job-1", selected_strategy_id="balanced-recalculated",
        status="COMPLETED", revision=4,
    )
    with store.connection(write=True) as connection:
        connection.execute(planning_sessions.VERSIONS.insert().values(
            id="job-1", tenant_id=tenant, session_id="session-1", payload=result,
        ))
        connection.execute(update(planning_sessions.SESSIONS).where(
            planning_sessions.SESSIONS.c.id == "session-1",
            planning_sessions.SESSIONS.c.tenant_id == tenant,
        ).values(status="COMPLETED", payload=deepcopy(adapter.session)))

    visible = next(item for item in farm_workflow.workflow_state(store, tenant)["proposals"]
                   if item["id"] == proposal["id"])
    assert visible["recalculated_strategy_id"] == "balanced-recalculated"
    assert visible["recalculated_metrics"]["coverage_kg"] == 7
    assert visible["recalculated_metrics"]["margin_sgd"] == 22


def test_planning_session_exposes_server_bound_scenario_and_b3_context(setup):
    store, tenant, _, _ = setup
    farm = synthetic_farm().model_dump(mode="json")
    session = {"id": "tactical-session", "revision": 7, "result_id": None,
               "input_hash": "snapshot-hash", "farm": farm, "world_id": None}
    context = planning_sessions.public_session(store, tenant, session)["tactical_context"]
    assert context["scenario"] == {
        "id": "synthetic-heavy-rainfall-v1", "entity_kind": "scenario",
        "title": "Heavy rainfall", "label": "SIMULATION · SCENARIO ONLY",
        "source": "Frozen synthetic seasonal record", "execution_mode": "simulation",
        "inference_triggered": False, "ask_eligible": False,
        "ask_disabled_reason": "Complete the local baseline calculation first.",
    }
    assert context["grow_space"] == {
        "id": "bed-07", "entity_kind": "grow_space", "title": "Keep grow space B3 free",
        "name": "B3", "area_m2": 20.0, "system": "sheltered_hydroponic",
        "source": "Frozen planning snapshot",
        "reservation_window": {"start_date": "2026-10-01", "end_date": "2026-11-02"},
        "reservation_active": False, "reserve_eligible": False,
        "reserve_disabled_reason": "Complete the local baseline calculation first.",
        "ask_eligible": False,
        "ask_disabled_reason": "Complete the local baseline calculation first.",
    }
