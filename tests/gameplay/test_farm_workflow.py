from datetime import datetime, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from packages.ingestion.financial import FinancialDataConnector
from services.api import farm_workflow, planning_sessions
from services.api.store import Store


class Adapter:
    def __init__(self, session, result): self.session, self.result = session, result
    def get_session(self, store, tenant_id, session_id):
        return self.session if session_id == self.session["id"] else None
    def get_result(self, store, tenant_id, result_id):
        return self.result if result_id == self.result["id"] else None
    def queue_recalculation(self, store, tenant_id, session, changes):
        session.update(revision=session["revision"] + 1, status="QUEUED")
        return {"id": "job-1", "status": "QUEUED", "changes": changes}
    def approve_result(self, store, tenant_id, session, proposal, result, strategy_id):
        session["approved_result_id"] = result["id"]
        session["selected_strategy_id"] = strategy_id
        return session


@pytest.fixture
def setup():
    store = Store("sqlite://")
    tenant, _ = store.new_session()
    other, _ = store.new_session()
    session = {"id": "session-1", "revision": 2, "result_id": "result-1", "input_hash": "farm-1", "selected_strategy_id": "balanced"}
    with store.connection(write=True) as c:
        c.execute(planning_sessions.SESSIONS.insert().values(id=session["id"], tenant_id=tenant, status="COMPLETE", payload=session))
    result = {"id": "result-1", "input_snapshot": {"recipes": [{"id": "recipe-caixin", "density_per_m2": 20}]},
        "strategies": [{"id": "balanced", "status": "FEASIBLE", "violations": [],
        "metrics": {"booked_requested_kg": 10, "booked_delivered_kg": 8, "closing_stock_kg": 3, "waste_kg": 1, "margin_sgd": 25},
        "order_allocations": [{"order_id": "order-1", "demand_kind": "booked", "crop_id": "caixin", "date": "2026-10-10",
            "delivered_kg": 8, "lot_allocations": [{"lot_id": "lot-1", "quantity_kg": 5, "harvested_date": "2026-10-09", "expires_date": "2026-10-12"},
                                                        {"lot_id": "lot-2", "quantity_kg": 3, "harvested_date": "2026-10-10", "expires_date": "2026-10-13"}]}],
        "allocations": [{"id": "batch-1", "recipe_id": "recipe-caixin", "area_m2": 2, "crop_id": "caixin", "bed_id": "bed-1", "sow_date": "2026-09-20",
                         "transplant_date": "2026-09-25", "harvest_date": "2026-10-10", "expected_kg": 8}]}]}
    return store, tenant, other, Adapter(session, result)


def test_review_is_explicit_tenant_isolated_and_photos_never_gain_yield_authority(setup):
    store, tenant, other, _ = setup
    candidate = FinancialDataConnector().from_rows(tenant_id=tenant, source_name="manual", rows=[
        {"date": "2026-09-01", "kind": "inventory", "amount": "0", "quantity": "4", "unit": "kg"}
    ])
    saved = farm_workflow.save_import(store, tenant, candidate, source_kind="photo_observation")
    assert saved["yield_authority"] is False
    reviewed = farm_workflow.review_import(store, tenant, saved["candidate_id"], decision="confirm", reviewer="farmer")
    assert reviewed["status"] == "confirmed" and reviewed["planning_eligible"] is False
    with pytest.raises(ValueError, match="not found"):
        farm_workflow.review_import(store, other, saved["candidate_id"], decision="confirm", reviewer="other")


def test_financial_corrections_resolve_reviewed_target_category_and_signed_delta(setup):
    store, tenant, _, _ = setup
    connector = FinancialDataConnector()
    ledger = connector.from_rows(tenant_id=tenant, source_name="reviewed-ledger", rows=[
        {"date": "2026-09-01", "kind": "sale", "reference": "SALE-1", "amount": "100"},
        {"date": "2026-09-01", "kind": "expense", "reference": "EXP-1", "amount": "100"},
    ])
    saved = farm_workflow.save_import(store, tenant, ledger)
    farm_workflow.review_import(store, tenant, saved["candidate_id"], decision="confirm", reviewer="farmer")

    corrections = connector.from_rows(tenant_id=tenant, source_name="signed-corrections", import_kind="correction", rows=[
        {"date": "2026-09-02", "kind": "correction", "reference": "CORR-SALE-UP",
         "target_reference": "SALE-1", "amount": "10"},
        {"date": "2026-09-02", "kind": "correction", "reference": "CORR-SALE-DOWN",
         "target_reference": "SALE-1", "amount": "-3"},
        {"date": "2026-09-02", "kind": "correction", "reference": "CORR-EXP-UP",
         "target_reference": "EXP-1", "amount": "10"},
        {"date": "2026-09-02", "kind": "correction", "reference": "CORR-EXP-DOWN",
         "target_reference": "EXP-1", "amount": "-3"},
    ])
    candidate = farm_workflow.save_import(store, tenant, corrections, source_kind="correction")
    summary = candidate["reconciliation"]
    assert {key: summary[key] for key in (
        "source_row_count", "counted_row_count", "duplicate_references", "correction_row_count",
        "correction_semantics", "revenue_sgd", "expense_sgd", "net_sgd", "quantity_by_unit",
    )} == {
        "source_row_count": 4, "counted_row_count": 4, "duplicate_references": [],
        "correction_row_count": 4, "correction_semantics": "target_category_signed_delta",
        "revenue_sgd": "7", "expense_sgd": "7", "net_sgd": "0", "quantity_by_unit": {},
    }
    assert [(row["corrects_reference"], row["target_kind"], row["signed_delta_sgd"])
            for row in summary["resolved_corrections"]] == [
        ("SALE-1", "sale", "10"), ("SALE-1", "sale", "-3"),
        ("EXP-1", "expense", "10"), ("EXP-1", "expense", "-3"),
    ]
    assert all(row["target_source_sha256"] == ledger.source_sha256
               and row["target_row_number"] in {2, 3} for row in summary["resolved_corrections"])
    reviewed = farm_workflow.review_import(store, tenant, candidate["candidate_id"],
                                           decision="confirm", reviewer="farmer")
    assert reviewed["reconciliation"] == candidate["reconciliation"]
    assert len(reviewed["rows"]) == 4 and all(row["corrects_reference"] for row in reviewed["rows"])


def test_financial_correction_rejects_unknown_and_ambiguous_reviewed_targets(setup):
    store, tenant, _, _ = setup
    connector = FinancialDataConnector()
    unknown = connector.from_rows(tenant_id=tenant, source_name="unknown", import_kind="correction", rows=[
        {"date": "2026-09-02", "kind": "correction", "reference": "CORR-UNKNOWN",
         "target_reference": "MISSING", "amount": "1"},
    ])
    with pytest.raises(ValueError, match="Unknown correction target"):
        farm_workflow.save_import(store, tenant, unknown, source_kind="correction")

    inventory = connector.from_rows(tenant_id=tenant, source_name="inventory-ledger", rows=[
        {"date": "2026-09-01", "kind": "inventory", "reference": "STOCK-1",
         "quantity": "5", "unit": "kg", "amount": "0"},
    ])
    saved_inventory = farm_workflow.save_import(store, tenant, inventory)
    farm_workflow.review_import(store, tenant, saved_inventory["candidate_id"],
                                decision="confirm", reviewer="farmer")
    category_mismatch = connector.from_rows(tenant_id=tenant, source_name="inventory-correction",
                                             import_kind="correction", rows=[
        {"date": "2026-09-02", "kind": "correction", "reference": "CORR-STOCK",
         "target_reference": "STOCK-1", "amount": "1"},
    ])
    with pytest.raises(ValueError, match="not a sale or expense"):
        farm_workflow.save_import(store, tenant, category_mismatch, source_kind="correction")

    for source, amount in (("ledger-a", "10"), ("ledger-b", "20")):
        item = connector.from_rows(tenant_id=tenant, source_name=source, rows=[
            {"date": "2026-09-01", "kind": "sale", "reference": "DUP-1",
             "description": source, "amount": amount},
        ])
        saved = farm_workflow.save_import(store, tenant, item)
        farm_workflow.review_import(store, tenant, saved["candidate_id"], decision="confirm", reviewer="farmer")
    ambiguous = connector.from_rows(tenant_id=tenant, source_name="ambiguous", import_kind="correction", rows=[
        {"date": "2026-09-02", "kind": "correction", "reference": "CORR-AMBIG",
         "target_reference": "DUP-1", "amount": "1"},
    ])
    with pytest.raises(ValueError, match="Ambiguous correction target"):
        farm_workflow.save_import(store, tenant, ambiguous, source_kind="correction")


def test_correction_reference_reuse_rejects_changed_delta_but_same_candidate_replays(setup):
    store, tenant, _, _ = setup
    connector = FinancialDataConnector()
    ledger = connector.from_rows(tenant_id=tenant, source_name="ledger", rows=[
        {"date": "2026-09-01", "kind": "expense", "reference": "EXP-REUSE", "amount": "100"},
    ])
    saved = farm_workflow.save_import(store, tenant, ledger)
    farm_workflow.review_import(store, tenant, saved["candidate_id"], decision="confirm", reviewer="farmer")
    first = connector.from_rows(tenant_id=tenant, source_name="correction", import_kind="correction", rows=[
        {"date": "2026-09-02", "kind": "correction", "reference": "CORR-REUSE",
         "target_reference": "EXP-REUSE", "amount": "10"},
    ])
    saved_first = farm_workflow.save_import(store, tenant, first, source_kind="correction")
    assert farm_workflow.save_import(store, tenant, first, source_kind="correction") == saved_first
    farm_workflow.review_import(store, tenant, saved_first["candidate_id"], decision="confirm", reviewer="farmer")
    changed = connector.from_rows(tenant_id=tenant, source_name="correction-changed", import_kind="correction", rows=[
        {"date": "2026-09-02", "kind": "correction", "reference": "CORR-REUSE",
         "target_reference": "EXP-REUSE", "amount": "11"},
    ])
    with pytest.raises(ValueError, match="Correction reference is already used"):
        farm_workflow.save_import(store, tenant, changed, source_kind="correction")


def test_reject_remains_available_if_correction_target_later_becomes_ambiguous(setup):
    store, tenant, _, _ = setup
    connector = FinancialDataConnector()
    original = connector.from_rows(tenant_id=tenant, source_name="original", rows=[
        {"date": "2026-09-01", "kind": "sale", "reference": "SALE-LATE-DUP", "amount": "10"},
    ])
    saved_original = farm_workflow.save_import(store, tenant, original)
    farm_workflow.review_import(store, tenant, saved_original["candidate_id"], decision="confirm", reviewer="farmer")
    correction = connector.from_rows(tenant_id=tenant, source_name="pending-correction", import_kind="correction", rows=[
        {"date": "2026-09-02", "kind": "correction", "reference": "CORR-LATE-DUP",
         "target_reference": "SALE-LATE-DUP", "amount": "1"},
    ])
    pending = farm_workflow.save_import(store, tenant, correction, source_kind="correction")
    duplicate = connector.from_rows(tenant_id=tenant, source_name="duplicate", rows=[
        {"date": "2026-09-01", "kind": "sale", "reference": "SALE-LATE-DUP",
         "description": "separate transaction using same external reference", "amount": "12"},
    ])
    saved_duplicate = farm_workflow.save_import(store, tenant, duplicate)
    farm_workflow.review_import(store, tenant, saved_duplicate["candidate_id"], decision="confirm", reviewer="farmer")
    with pytest.raises(ValueError, match="Ambiguous correction target"):
        farm_workflow.review_import(store, tenant, pending["candidate_id"], decision="confirm", reviewer="farmer")
    rejected = farm_workflow.review_import(store, tenant, pending["candidate_id"],
                                           decision="reject", reviewer="farmer")
    assert rejected["status"] == "rejected" and rejected["planning_eligible"] is False


def test_unsupported_crop_review_is_truthfully_accounting_only(setup):
    store, tenant, _, _ = setup
    candidate = FinancialDataConnector().from_rows(tenant_id=tenant, source_name="unknown-crop", rows=[
        {"date": "2026-09-01", "kind": "sale", "reference": "SALE-U1",
         "crop_id": "garlic_chives", "quantity": "2", "unit": "kg", "amount": "10"},
    ])
    saved = farm_workflow.save_import(store, tenant, candidate)
    reviewed = farm_workflow.review_import(store, tenant, saved["candidate_id"],
                                           decision="confirm", reviewer="farmer")
    assert reviewed["status"] == "confirmed"
    assert reviewed["planning_eligible"] is False
    assert reviewed["planning_eligibility"] == "accounting_only_unsupported_crop"
    assert reviewed["row_eligibility"] == [{
        "row_number": 2, "accounting_eligible": True, "planning_eligible": False,
    }]


def test_stale_proposal_duplicate_approval_and_auditable_correction(setup):
    store, tenant, _, adapter = setup
    with pytest.raises(ValueError, match="revision changed"):
        farm_workflow.create_proposal(store, tenant, adapter=adapter, session_id="session-1", base_revision=1,
                                      changes=[], idempotency_key="stale")
    proposal = farm_workflow.create_proposal(store, tenant, adapter=adapter, session_id="session-1", base_revision=2,
                                             changes=[{"kind": "demand", "crop_id": "caixin", "percent": 110}], idempotency_key="p1")
    assert proposal["calculated_metrics"] == {"coverage_kg": 8.0, "surplus_kg": 3.0, "expiry_kg": 1.0,
                                               "rejection_kg": None, "margin_sgd": 25.0, "waste_rescue_kg": 0.0}
    applied = farm_workflow.apply_proposal(store, tenant, proposal["id"], adapter=adapter,
                                           expected_base_revision=2, idempotency_key="apply")
    adapter.session.update(result_id="job-1", status="COMPLETED", revision=adapter.session["revision"] + 1,
                           input_hash="farm-2")
    adapter.result["id"] = "job-1"
    first = farm_workflow.approve_and_create_actions(store, tenant, proposal["id"], adapter=adapter,
                                                      proposal_revision=applied["proposal_revision"], idempotency_key="approve")
    duplicate = farm_workflow.approve_and_create_actions(store, tenant, proposal["id"], adapter=adapter,
                                                          proposal_revision=applied["proposal_revision"], idempotency_key="approve")
    assert [x["id"] for x in first["tasks"]] == [x["id"] for x in duplicate["tasks"]]
    sow = next(x for x in first["tasks"] if x["action"] == "sow")
    assert (sow["planned_quantity"], sow["unit"]) == (40.0, "plants")
    short = farm_workflow.record_task_result(store, tenant, sow["id"], expected_status="pending", result_status="completed",
                                             actual_quantity=30, unit="plants", checklist_completed=sow["checklist"])
    assert short["status"] == "recovery_required"
    assert short["forecast_feedback"]["delta_quantity"] == "-10.0"
    delivery = next(x for x in first["tasks"] if x["action"] == "delivery")
    assert [lot["lot_id"] for lot in delivery["lot_allocations"]] == ["lot-1", "lot-2"]
    with pytest.raises(ValueError, match="exceeds its allocated lots"):
        farm_workflow.record_task_result(store, tenant, delivery["id"], expected_status="pending", result_status="completed",
            actual_quantity=7, rejected_quantity=2, unit="kg", checklist_completed=delivery["checklist"])
    delivery_result = farm_workflow.record_task_result(store, tenant, delivery["id"], expected_status="pending", result_status="completed",
        actual_quantity=7, rejected_quantity=1, unit="kg", checklist_completed=delivery["checklist"])
    assert delivery_result["status"] == "recovery_required"
    harvest = next(x for x in first["tasks"] if x["action"] == "harvest")
    completed = farm_workflow.record_task_result(store, tenant, harvest["id"], expected_status="pending", result_status="completed",
                                                 actual_quantity=7, unit="kg",
                                                 checklist_completed=harvest["checklist"])
    corrected = farm_workflow.correct_task_result(store, tenant, harvest["id"], expected_event_revision=completed["event_revision"],
                                                  field="actual_quantity", corrected_value="6.5", reason="scale transcription",
                                                  idempotency_key="correction")
    assert corrected["actual_quantity"] == "6.5" and corrected["status"] == "recovery_required"
    assert "quantity_below_plan" in corrected["recovery"]["reasons"]
    assert farm_workflow.correct_task_result(store, tenant, harvest["id"], expected_event_revision=completed["event_revision"],
                                             field="actual_quantity", corrected_value="6.5", reason="scale transcription",
                                             idempotency_key="correction") == corrected
    with pytest.raises(ValueError, match="revision changed"):
        farm_workflow.correct_task_result(store, tenant, harvest["id"], expected_event_revision=completed["event_revision"],
                                          field="actual_quantity", corrected_value="6", reason="again", idempotency_key="other")


def test_correction_revalidates_complete_task_and_owned_photo_invariants(setup):
    store, tenant, _, adapter = setup
    proposal = farm_workflow.create_proposal(store, tenant, adapter=adapter, session_id="session-1", base_revision=2,
        changes=[{"kind": "planning_assumptions", "assumptions": {}}], idempotency_key="correct-whole-proposal")
    applied = farm_workflow.apply_proposal(store, tenant, proposal["id"], adapter=adapter,
        expected_base_revision=2, idempotency_key="correct-whole-apply")
    adapter.session.update(result_id="job-1", status="COMPLETED", revision=adapter.session["revision"] + 1,
                           input_hash="farm-2")
    adapter.result["id"] = "job-1"
    tasks = farm_workflow.approve_and_create_actions(store, tenant, proposal["id"], adapter=adapter,
        proposal_revision=applied["proposal_revision"], idempotency_key="correct-whole-approve")["tasks"]

    harvest = next(task for task in tasks if task["action"] == "harvest")
    with pytest.raises(ValueError, match="previously reported"):
        farm_workflow.correct_task_result(store, tenant, harvest["id"], expected_event_revision=0,
            field="note", corrected_value="premature", reason="no prior result", idempotency_key="pending-correction")
    failed_harvest = farm_workflow.record_task_result(store, tenant, harvest["id"], expected_status="pending",
        result_status="failed", actual_quantity=None, unit=None, checklist_completed=[])
    with pytest.raises(ValueError, match="Completed harvest requires an actual quantity"):
        farm_workflow.correct_task_result(store, tenant, harvest["id"],
            expected_event_revision=failed_harvest["event_revision"], field="result_status", corrected_value="completed",
            reason="incorrect completion", idempotency_key="invalid-harvest-completion")

    delivery = next(task for task in tasks if task["action"] == "delivery")
    failed_delivery = farm_workflow.record_task_result(store, tenant, delivery["id"], expected_status="pending",
        result_status="failed", actual_quantity=None, unit=None, rejected_quantity=None, checklist_completed=[])
    with pytest.raises(ValueError, match="Completed delivery requires accepted and rejected quantities"):
        farm_workflow.correct_task_result(store, tenant, delivery["id"],
            expected_event_revision=failed_delivery["event_revision"], field="result_status", corrected_value="completed",
            reason="incorrect completion", idempotency_key="invalid-delivery-completion")
    with pytest.raises(ValueError, match="owned reviewed photo"):
        farm_workflow.correct_task_result(store, tenant, delivery["id"],
            expected_event_revision=failed_delivery["event_revision"], field="photo_reference", corrected_value="other-tenant-photo",
            reason="attach evidence", idempotency_key="invalid-correction-photo")


def test_http_import_review_is_tenant_scoped_and_waste_rescue_is_dated(setup):
    store, tenant, other, _ = setup
    def client_for(owner):
        app = FastAPI(); app.state.store = store
        farm_workflow.register(app, lambda request: owner)
        return TestClient(app)
    with client_for(tenant) as client:
        created = client.post("/api/v1/farm-workflow/imports", json={"source_name": "manual", "rows": [
            {"date": "2026-09-01", "kind": "expense", "amount": "12.50"}
        ]})
        assert created.status_code == 201, created.text
        candidate_id = created.json()["candidate_id"]
        source = b"date,kind,amount,currency\n2026-09-01,expense,12.50,SGD\n"
        uploaded = client.post("/api/v1/farm-workflow/imports/upload?filename=ledger.csv&source_kind=accounting_export",
                               content=source, headers={"content-type": "text/csv"})
        assert uploaded.status_code == 201, uploaded.text
        source_id = uploaded.json()["candidate_id"]
        preview = client.get(f"/api/v1/farm-workflow/imports/{source_id}/source")
        assert preview.content == source and preview.headers["content-disposition"].startswith("inline")
        assert client.get(f"/api/v1/farm-workflow/imports/{source_id}/source/download").headers["content-disposition"].startswith("attachment")
        assert client.get("/api/v1/farm-workflow/imports/../source").status_code == 404
        from datetime import date
        rescued = farm_workflow.waste_rescue_scenarios(quantity_kg=5, expires_on=date(2026, 9, 18), today=date(2026, 9, 16),
            sale_price_sgd_per_kg=4, rescue_price_sgd_per_kg=2, rescue_cost_sgd_per_kg=.5)
        assert rescued["scenarios"][1]["margin_delta_sgd"] == -12.5
    with client_for(other) as client:
        assert client.get(f"/api/v1/farm-workflow/imports/{source_id}/source").status_code == 404
        response = client.post(f"/api/v1/farm-workflow/imports/{candidate_id}/review", json={
            "decision": "confirm", "reviewer": "other"
        })
        assert response.status_code == 404, response.text


def test_action_pack_omits_historical_stages_but_keeps_biological_dates():
    from datetime import timedelta
    from packages.fixtures import synthetic_farm
    farm = synthetic_farm()
    day = farm.planning_date
    result = {"input_snapshot": farm.model_dump(mode="json"), "strategies": [{"id": "balanced", "status": "FEASIBLE", "violations": [],
        "allocations": [{"id": "existing-cycle", "recipe_id": farm.recipes[0].id, "crop_id": farm.recipes[0].crop_id,
            "bed_id": farm.beds[0].id, "area_m2": float(farm.beds[0].area_m2), "expected_kg": 5,
            "sow_date": str(day - timedelta(days=10)), "transplant_date": str(day - timedelta(days=4)),
            "harvest_date": str(day + timedelta(days=5)), "executed": True}], "order_allocations": []}]}
    proposal = {"id": "p", "session_id": "s", "proposal_revision": 2}
    tasks = farm_workflow._tasks_from_result("tenant", proposal, result, "balanced")
    assert [task["action"] for task in tasks] == ["harvest"]
    assert tasks[0]["biological_dates"] == {"sow_date": str(day - timedelta(days=10)),
        "transplant_date": str(day - timedelta(days=4)), "harvest_date": str(day + timedelta(days=5))}


def test_waste_rescue_uses_terminal_lot_dates_and_conservative_mixed_expiry(setup, monkeypatch):
    store, tenant, _, _ = setup
    from packages.fixtures import synthetic_farm
    farm = synthetic_farm().model_dump(mode="json")
    session = {"id": "s", "result_id": "r", "approved_result_id": "r", "farm": farm}
    result = {"id": "r", "input_snapshot": farm, "strategies": [{"id": "balanced",
        "inventory_snapshots": [{"date": "2026-10-31", "closing_lots": [
            {"id": "lot-later", "crop_id": "caixin", "quantity_kg": 3, "harvested_date": "2026-10-30", "expires_date": "2026-11-03", "origin": "synthetic"},
            {"id": "lot-first", "crop_id": "lettuce", "quantity_kg": 2, "harvested_date": "2026-10-29", "expires_date": "2026-11-01", "origin": "synthetic"},
        ]}]}]}
    monkeypatch.setattr(planning_sessions, "get_session", lambda *_: session)
    monkeypatch.setattr(planning_sessions, "get_result", lambda *_: result)
    app = FastAPI(); app.state.store = store; farm_workflow.register(app, lambda request: tenant)
    with TestClient(app) as client:
        response = client.post("/api/v1/farm-workflow/waste-rescue", json={"session_id": "s", "result_id": "r",
            "strategy_id": "balanced", "sale_price_sgd_per_kg": 4, "rescue_price_sgd_per_kg": 2, "rescue_cost_sgd_per_kg": .5})
        assert response.status_code == 200, response.text
        aggregate = response.json()
        assert aggregate["as_of"] == "2026-10-31" and aggregate["expires_on"] == "2026-11-01"
        assert aggregate["quantity_kg"] == 5 and len(aggregate["surplus_lots"]) == 2
        assert aggregate["selection_basis"] == "all_terminal_lots_aggregated_using_earliest_actual_expiry"
        selected = client.post("/api/v1/farm-workflow/waste-rescue", json={"session_id": "s", "result_id": "r",
            "strategy_id": "balanced", "lot_id": "lot-later", "sale_price_sgd_per_kg": 4})
        assert selected.json()["expires_on"] == "2026-11-03" and selected.json()["quantity_kg"] == 3
