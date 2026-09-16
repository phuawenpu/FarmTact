from types import SimpleNamespace

from packages.planning_claims import build_claims
from runtime.deepseek_gateway import RunBudget, SafeAudit, Usage
from services.api import planning_council


def _plan(id, name, margin, delivered, allocations, *, status="FEASIBLE"):
    return {
        "id": id, "name": name, "status": status, "violations": [],
        "metrics": {
            "margin_sgd": margin, "booked_requested_kg": 824,
            "booked_delivered_kg": delivered, "fill_rate": delivered / 824,
            "waste_kg": 12, "closing_stock_kg": 3, "area_m2": 40,
        },
        "allocations": allocations,
    }


def _result():
    retained = _plan("saved", "Saved schedule", 2467.60, 518, [
        {"crop_id": "caixin", "area_m2": 20},
        {"crop_id": "lettuce", "area_m2": 20},
    ])
    lean = _plan("lean", "Lean", 2414.73, 370, [
        {"crop_id": "caixin", "area_m2": 30},
        {"crop_id": "lettuce", "area_m2": 10},
    ])
    return {"snapshot_hash": "frozen-v11", "retained_strategy": retained, "strategies": [lean]}


def test_claims_compute_direction_shortfall_and_crop_composition_independently():
    claims = build_claims(_result())
    by_metric = {claim["metric"]: claim for claim in claims}

    margin = by_metric["margin_sgd"]
    assert margin["baseline"] == 2467.6
    assert margin["scenario"] == 2414.73
    assert margin["delta"] == -52.87
    assert margin["direction"] == "decrease"
    assert "decreases" in margin["statement"]

    shortfall = by_metric["booked_shortfall_kg"]
    assert shortfall["baseline"] == 306
    assert shortfall["scenario"] == 454
    assert "fully delivered" not in shortfall["statement"]

    assert by_metric["crop_id_set"]["direction"] == "unchanged"
    assert by_metric["crop_allocation_area_m2"]["direction"] == "changed"
    assert by_metric["crop_allocation_count"]["direction"] == "unchanged"
    assert all(claim["snapshot_hash"] == "frozen-v11" for claim in claims)


def test_claim_ids_are_stable_and_nan_metrics_are_not_admitted():
    result = _result()
    result["strategies"][0]["metrics"]["revenue_sgd"] = float("nan")
    first = build_claims(result)
    second = build_claims(result)
    assert [row["id"] for row in first] == [row["id"] for row in second]
    assert "revenue_sgd" not in {row["metric"] for row in first}


def test_initial_plan_has_authoritative_strategy_metrics_without_fake_baseline():
    result = _result()
    result.pop("retained_strategy")
    claims = build_claims(result)
    assert claims
    assert {row["claim_kind"] for row in claims} == {"strategy_metric"}
    margin = next(row for row in claims if row["metric"] == "margin_sgd")
    assert margin["strategy_id"] == "lean"
    assert margin["statement"] == "Lean's projected margin is SGD 2,414.73 in this frozen plan."
    assert "relative" not in margin["statement"]


def test_claim_context_hash_binds_assumptions_and_outputs_not_farm_hash_alone():
    first = _result()
    first.pop("snapshot_hash")
    first.update(input_hash="same-farm", numerical_input_hash="demand-v1",
                 configuration_hash="config-v1", assumptions={"future_demand": []})
    changed = __import__("copy").deepcopy(first)
    changed["assumptions"] = {"future_demand": [{"crop_id": "caixin", "percent": 125}]}
    first_hash = {row["snapshot_hash"] for row in build_claims(first)}
    changed_hash = {row["snapshot_hash"] for row in build_claims(changed)}
    assert len(first_hash) == len(changed_hash) == 1
    assert first_hash != changed_hash


def test_semantic_gate_ties_rationale_and_proposal_to_selected_claims():
    claims = build_claims(_result())
    margin = next(row for row in claims if row["metric"] == "margin_sgd")
    assert planning_council._semantic_issues({
        "claim_ids": [margin["id"]], "tradeoff": "service_over_margin",
        "rationale": "protect_booked_service", "proposed_strategy_id": "lean",
    }, selected=[margin]) == ["rationale_not_supported_by_selected_claims"]
    assert planning_council._semantic_issues({
        "claim_ids": [margin["id"]], "tradeoff": "margin_over_service",
        "rationale": "preserve_margin", "proposed_strategy_id": "other",
    }, selected=[margin]) == ["proposed_strategy_not_supported_by_selected_claims"]


def test_functional_roles_require_crop_composition_and_capacity_cost_evidence():
    claims = build_claims(_result())
    area = next(row for row in claims if row["metric"] == "area_m2")
    service = next(row for row in claims if row["metric"] == "booked_delivered_kg")
    crop_set = next(row for row in claims if row["metric"] == "crop_id_set")
    margin = next(row for row in claims if row["metric"] == "margin_sgd")

    crop_finding = {"claim_ids": [area["id"]], "tradeoff": "space_over_variety",
                    "rationale": "preserve_crop_variety", "proposed_strategy_id": area["strategy_id"]}
    assert "crop_mix_requires_crop_identity_or_allocation_evidence" in planning_council._semantic_issues(
        crop_finding, selected=[area], role="production_analyst")
    crop_finding["claim_ids"] = [crop_set["id"]]
    crop_finding["proposed_strategy_id"] = crop_set["strategy_id"]
    assert planning_council._semantic_issues(crop_finding, selected=[crop_set], role="production_analyst") == []

    capacity_finding = {"claim_ids": [service["id"]], "tradeoff": "service_over_margin",
                        "rationale": "protect_booked_service", "proposed_strategy_id": service["strategy_id"]}
    assert "capacity_cost_evidence_required" in planning_council._semantic_issues(
        capacity_finding, selected=[service], role="supply_chain_analyst")
    capacity_finding.update(claim_ids=[margin["id"]], tradeoff="margin_over_service", rationale="preserve_margin",
                            proposed_strategy_id=margin["strategy_id"])
    assert planning_council._semantic_issues(capacity_finding, selected=[margin], role="supply_chain_analyst") == []
    assert "crop-specific allocation or crop-identity" in planning_council._prompt("production_analyst")
    assert "area, labour, cost, or margin" in planning_council._prompt("supply_chain_analyst")


class FakeGateway:
    calls = []
    versions = []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def chat_json(self, role, messages, output_model, **kwargs):
        context = __import__("json").loads(messages[1]["content"])
        self.calls.append((role, context))
        self.versions.append(kwargs["versions"].public())
        claims = context["verified_claims"]
        preferred = ({"crop_id_set", "crop_allocation_count", "crop_allocation_area_m2"}
                     if role == "production_analyst" else
                     {"area_m2", "labour_hours", "cost_sgd", "margin_sgd"}
                     if role == "supply_chain_analyst" else set())
        selected = next((row for row in claims if row["metric"] in preferred), claims[0] if claims else None)
        ids = [selected["id"]] if selected else []
        strategy = context["eligible_strategy_ids"][0] if ids else None
        metric = selected["metric"] if selected else None
        if metric in {"crop_allocation_count", "crop_allocation_area_m2", "crop_id_set", "area_m2"}:
            tradeoff, rationale = "space_over_variety", "preserve_crop_variety"
        elif metric in {"booked_delivered_kg", "booked_shortfall_kg", "fill_rate"}:
            tradeoff, rationale = "service_over_margin", "protect_booked_service"
        elif metric in {"margin_sgd", "cost_sgd", "revenue_sgd"}:
            tradeoff, rationale = "margin_over_service", "preserve_margin"
        elif metric in {"waste_kg", "closing_stock_kg"}:
            tradeoff = "waste_over_inventory"
            rationale = "reduce_expired_waste" if metric == "waste_kg" else "limit_terminal_stock"
        else:
            tradeoff, rationale, strategy = "insufficient_evidence", "insufficient_external_evidence", None
        data = output_model.model_validate({
            "claim_ids": ids,
            "tradeoff": tradeoff,
            "rationale": rationale,
            "proposed_strategy_id": strategy,
        })
        audit = SafeAudit(
            provider="deepseek", requested_model="deepseek-flash", returned_model="deepseek-flash",
            role=role, capability="text", execution_mode="test", data_mode="synthetic_demo",
            inference_origin="deepseek_api", input_sha256="a" * 64, request_id="req",
            latency_ms=1, usage=Usage(), contract_versions={},
        )
        return SimpleNamespace(data=data, audit=audit, model="deepseek-flash")


def test_review_skips_absent_external_roles_and_chair_sees_statuses(monkeypatch):
    fake = FakeGateway()
    FakeGateway.calls = []
    FakeGateway.versions = []
    monkeypatch.setattr(planning_council.DeepSeekGateway, "from_config", lambda *a, **k: fake)
    events = []
    budget = RunBudget(max_requests=9, max_reserved_output_tokens=16384, max_wall_seconds=300)
    # The fake gateway does not reserve; emulate provider accounting per request.
    original = fake.chat_json
    def counted(*args, **kwargs):
        budget.reserve(768)
        return original(*args, **kwargs)
    fake.chat_json = counted

    review = planning_council.review_plan(
        _result(), budget=budget, emit=lambda kind, body: events.append((kind, body)),
        cancelled=lambda: False, provider_user_id="tenant_test", news_context=None,
    )

    assert review["status"] == "completed"
    assert review["request_count"] == 5
    assert all(version == {
        "prompt_template": "farmtact-planning-council-prompt-v3",
        "output_schema": "farmtact-planning-finding-output-v2",
        "validator": "farmtact-planning-claim-validator-v3",
        "context": "farmtact-planning-comparison-context-v3",
        "sources": "farmtact-planning-source-context-v2",
    } for version in FakeGateway.versions)
    assert [role for role, _ in FakeGateway.calls] == [
        "demand_analyst", "production_analyst", "supply_chain_analyst",
        "profit_analyst", "planning_chair",
    ]
    unavailable = {row["role"]: row for row in review["findings"] if row["status"] == "unavailable"}
    assert set(unavailable) == {"weather_analyst", "market_analyst"}
    assert all(row["audit"] is None for row in unavailable.values())
    chair_context = FakeGateway.calls[-1][1]
    assert len(chair_context["prior_statuses"]) == 6
    assert all(set(row) == {"role", "status", "claim_ids", "proposed_strategy_id", "rejection_reasons"}
               for row in chair_context["prior_statuses"])
    assert chair_context["allowed_tradeoff_rationales"]["margin_over_service"] == ["preserve_margin"]
    assert "margin_sgd" in chair_context["rationale_metrics"]["preserve_margin"]
    assert all("raw_provider_output" in row for row in review["findings"])
    assert any(kind == "planning_council_role_unavailable" for kind, _ in events)


def test_review_cancels_without_opening_provider(monkeypatch):
    opened = []
    monkeypatch.setattr(planning_council.DeepSeekGateway, "from_config", lambda *a, **k: opened.append(True))
    budget = RunBudget(max_requests=9, max_reserved_output_tokens=16384, max_wall_seconds=300)
    review = planning_council.review_plan(
        _result(), budget=budget, emit=lambda *_: None, cancelled=lambda: True,
        provider_user_id="tenant_test",
    )
    assert review["status"] == "cancelled"
    assert review["request_count"] == 0
    assert review["missing_roles"] == planning_council.ROLES
    assert opened == []


def test_functional_view_distinguishes_validated_partial_and_withheld_truth():
    review = {"status": "partial", "findings": [
        {"role": "demand_analyst", "status": "validated", "rendered_facts": ["fact"], "rejection_reasons": []},
        {"role": "weather_analyst", "status": "unavailable", "rendered_facts": [], "rejection_reasons": []},
        {"role": "planning_chair", "status": "rejected", "rendered_facts": [], "rejection_reasons": ["bad claim"]},
    ]}
    public = planning_council.functional_council_view(review)
    assert public["contract_version"] == "farmtact-functional-council-v3"
    assert public["truth_status"] == "withheld"
    assert [(row["functional_role"], row["truth_status"], row["tool_status"]) for row in public["findings"]] == [
        ("Demand Planner", "validated", "local_calculation_and_inference_completed"),
        ("Weather & Risk Monitor", "partial", "source_absent"),
        ("Plan Reviewer", "withheld", "validation_failed"),
    ]
