from types import SimpleNamespace

from packages.agents import ROLES
from runtime.deepseek_gateway import SafeAudit, Usage
from services.api import council as council_module


class FakeGateway:
    def __init__(self, calls):
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def chat_json(self, role, messages, output_model, **kwargs):
        self.calls.append((role, messages, kwargs))
        context = __import__("json").loads(messages[1]["content"])
        context_ref = next(iter(context["qualitative_context"]))
        if role == "planning_chair":
            context_ref = next(
                alias for alias, value in context["qualitative_context"].items()
                if "balanced-service-margin-id-v1" in str(value)
            )
        fact_ref = next(iter(context["typed_facts"]), None)
        data = output_model.model_validate(
            {
                "claim_type": "observation",
                "statement": "The frozen comparison supports this role-specific finding.",
                "evidence_ids": [],
                "tool_result_refs": [context_ref],
                "fact_refs": [fact_ref] if fact_ref else [],
                "recommendation": "proceed_simulation",
            }
        )
        usage = Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2)
        audit = SafeAudit(
            provider="deepseek",
            requested_model="deepseek-flash",
            returned_model="deepseek-flash",
            role=role,
            capability="text",
            execution_mode="test",
            data_mode="synthetic_demo",
            inference_origin="deepseek_api",
            input_sha256="a" * 64,
            request_id="fixture",
            latency_ms=1,
            usage=usage,
        )
        return SimpleNamespace(data=data, audit=audit, model="deepseek-flash", usage=usage)


def repair_computed():
    return {
        "input_hash": "frozen-repair-input",
        "forecast": {"cutoff": "2026-09-09T00:00:00Z", "uncertainty": {}, "demand": [], "harvest": []},
        "strategies": [{
            "id": "balanced", "name": "Balanced", "status": "FEASIBLE",
            "metrics": {
                "margin_sgd": 10.0, "booked_requested_kg": 4.0,
                "fill_rate": 0.8, "harvest_kg": 5.0, "shortfall_kg": 1.0,
                "waste_kg": 0.0, "closing_stock_kg": 0.0,
                "revenue_sgd": 11.0, "cost_sgd": 1.0, "labour_hours": 1.0,
            },
            "violations": [], "allocations": [], "order_allocations": [],
        }],
    }


def test_council_runs_six_specialists_then_planner_with_frozen_market_context(monkeypatch):
    calls = []
    monkeypatch.setattr(
        council_module.DeepSeekGateway,
        "from_config",
        lambda *_, **__: FakeGateway(calls),
    )
    market = {
        "status": "not_connected",
        "connected_social_feeds": False,
        "summary": "No community evidence source is connected.",
        "observations": [],
    }
    computed = {
        "input_hash": "frozen-input",
        "forecast": {
            "cutoff": "2026-09-09T00:00:00Z",
            "uncertainty": {},
            "demand": [{
                "crop_id": "caixin", "week": 0, "date": "2026-09-14",
                "confirmed_kg": 4.0, "residual_kg": 1.0, "expected_kg": 5.0,
                "price_sgd_per_kg": 6.0, "price_status": "booked_weighted_average",
            }],
        },
        "strategies": [
            {
                "id": "balanced",
                "name": "Balanced",
                "metrics": {
                    "margin_sgd": 10.0,
                    "booked_requested_kg": 4.0,
                    "fill_rate": 0.8,
                    "harvest_kg": 5.0,
                    "shortfall_kg": 1.0,
                },
                "violations": [],
                "risk": "bounded",
                "status": "FEASIBLE",
                "assumptions": [],
                "allocations": [{
                    "id": "allocation-a", "recipe_id": "caixin-demo-v1",
                    "crop_id": "caixin", "sow_date": "2026-09-01",
                    "transplant_date": "2026-09-08", "harvest_date": "2026-09-29",
                    "expected_kg": 5.0,
                }],
                "order_allocations": [{
                    "demand_line_id": "order-a", "demand_kind": "booked",
                    "crop_id": "caixin", "date": "2026-09-14", "requested_kg": 4.0,
                    "delivered_kg": 4.0, "shortfall_kg": 0.0, "price_sgd_per_kg": 6.0,
                }],
            }
        ],
    }

    claims, audits = council_module.council(
        computed,
        "run-seven",
        lambda *_: None,
        market_signals=market,
    )

    assert [role for role, _, _ in calls] == ROLES
    assert len(claims) == len(audits) == 7
    assert all(claim["evidence_status"] == "grounded_facts_qualitative_unverified" for claim in claims)
    assert all(claim["rendered_facts"][0]["verification"] == "code_rendered_frozen_value" for claim in claims)
    assert all(call[2]["max_tokens"] == 1_536 for call in calls)
    assert all("reference_alias_mapping" in audit for audit in audits)
    assert all("provider_returned_aliases" in audit for audit in audits)
    assert all(
        all(not ref.startswith("F") for ref in claim["fact_refs"])
        and all(not ref.startswith("C") for ref in claim["tool_result_refs"])
        for claim in claims
    )
    for role, messages, _ in calls[:-1]:
        assert role != "planning_chair"
        assert '"prior_claims": []' in messages[1]["content"]
    planner_context = calls[-1][1][1]["content"]
    assert '"prior_claims": [' in planner_context
    assert '"status": "not_connected"' in planner_context
    parsed = __import__("json").loads(planner_context)
    assert set(parsed["qualitative_context"]).isdisjoint(parsed["typed_facts"])
    assert all(ref.startswith("C") for ref in parsed["qualitative_context"])
    assert any("balanced-service-margin-id-v1" in str(value) for value in parsed["qualitative_context"].values())
    demand_context = __import__("json").loads(calls[0][1][1]["content"])
    assert all(ref.startswith("F") for ref in demand_context["typed_facts"])
    assert any(value["context"] == "forecast" for value in demand_context["typed_facts"].values())


def test_short_aliases_resolve_exactly_to_the_same_canonical_frozen_fact():
    qualitative = {"policy:automatic_selection": "server-owned policy"}
    typed = {
        "order:strategy_order:order-0-0.shortfall_kg": {
            "reference": "order:strategy_order:order-0-0.shortfall_kg",
            "kind": "quantity", "value": 4.0, "unit": "kg",
        }
    }
    aliased_qualitative, aliased_typed, mapping = council_module._alias_context(
        qualitative, typed
    )
    assert aliased_qualitative == {"C001": "server-owned policy"}
    assert aliased_typed["F001"]["reference"] == "F001"
    claim, returned, alias_issues = council_module._resolve_claim_aliases(
        {"tool_result_refs": ["C001"], "fact_refs": ["F001"]}, mapping
    )
    assert alias_issues == []
    assert returned == {"tool_result_refs": ["C001"], "fact_refs": ["F001"]}
    assert claim["tool_result_refs"] == ["policy:automatic_selection"]
    assert claim["fact_refs"] == ["order:strategy_order:order-0-0.shortfall_kg"]
    assert council_module.render_facts(claim["fact_refs"], typed)[0]["value"] == 4.0


def test_unknown_and_cross_kind_aliases_still_fail_closed():
    qualitative = {"context:lead_time": "server-owned"}
    typed = {"strategy:balanced.metrics.margin_sgd": {"reference": "strategy:balanced.metrics.margin_sgd"}}
    _, _, mapping = council_module._alias_context(qualitative, typed)
    unknown, _, alias_issues = council_module._resolve_claim_aliases(
        {"tool_result_refs": [], "fact_refs": ["F999"]}, mapping
    )
    assert alias_issues[0]["code"] == "unknown_fact_alias"
    assert unknown["fact_refs"] == ["F999"]

    crossed, _, alias_issues = council_module._resolve_claim_aliases(
        {
            "statement": "The frozen comparison needs review.",
            "evidence_ids": [],
            "tool_result_refs": ["F001"],
            "fact_refs": ["C001"],
        }, mapping
    )
    assert alias_issues == []
    issues = council_module._claim_issues(crossed, qualitative, typed, set())
    assert {issue["code"] for issue in issues} == {
        "unknown_tool_reference", "typed_fact_in_context_refs", "unknown_typed_fact"
    }


def test_typed_claim_gate_rejects_wrong_meaning_and_model_authored_values():
    refs = {
        "forecast:batch_batch-01.marketable_kg": 12.5,
        "forecast:batch_batch-01.harvest_date": "2026-09-20",
        "source:weather_scope": "Context only",
    }
    from packages.ai_contracts import typed_reference_catalog

    typed = typed_reference_catalog(refs, snapshot_hash="frozen")
    laundering = {
        "statement": "The margin is 12.5 SGD.",
        "evidence_ids": [],
        "tool_result_refs": [],
        "fact_refs": ["forecast:batch_batch-01.marketable_kg"],
    }
    issues = council_module._claim_issues(laundering, refs, typed, set())
    assert {issue["code"] for issue in issues} == {"model_authored_quantity"}
    rendered = council_module.render_facts(laundering["fact_refs"], typed)[0]
    assert rendered["entity"] == {"type": "batch", "id": "batch-01"}
    assert rendered["unit"] == "kg"
    assert rendered["value"] == 12.5

    wrong_ref = dict(laundering, statement="The frozen comparison needs review.", fact_refs=["forecast:batch_batch-02.marketable_kg"])
    issues = council_module._claim_issues(wrong_ref, refs, typed, set())
    assert [issue["code"] for issue in issues] == ["unknown_typed_fact"]


def test_chair_context_carries_specialist_rejection_categories(monkeypatch):
    calls = []

    class RejectingGateway(FakeGateway):
        def chat_json(self, role, messages, output_model, **kwargs):
            result = super().chat_json(role, messages, output_model, **kwargs)
            if role == "demand_analyst":
                result.data.fact_refs = ["strategy:missing.metrics.margin_sgd"]
            return result

    monkeypatch.setattr(
        council_module.DeepSeekGateway,
        "from_config",
        lambda *_, **__: RejectingGateway(calls),
    )
    computed = {
        "input_hash": "frozen-input",
        "forecast": {"cutoff": "2026-09-09T00:00:00Z", "uncertainty": {}, "harvest": []},
        "strategies": [{"id":"balanced","name":"Balanced","metrics":{"margin_sgd":10.0},"violations":[],"risk":"bounded","status":"FEASIBLE","assumptions":[]}],
    }
    claims, _ = council_module.council(computed, "run-errors", lambda *_: None)
    assert {issue["code"] for issue in claims[0]["validation_issues"]} == {
        "unknown_fact_alias", "unknown_typed_fact"
    }
    chair = __import__("json").loads(calls[-1][1][1]["content"])["prior_claims"][0]
    assert chair["eligible_as_evidence"] is False
    assert chair["validation_issues"][0]["code"] == "unknown_fact_alias"


def test_actual_failure_patterns_remain_rejected_and_prompt_explains_repairs():
    qualitative = {
        "strategy:balanced.violations": {"status": "none"},
        "policy:automatic_selection": "Prefer Balanced before service and margin tie-breaks.",
    }
    typed = {
        "strategy:balanced.metrics.margin_sgd": {"reference": "strategy:balanced.metrics.margin_sgd"}
    }
    misplaced = {
        "role": "profit_analyst",
        "statement": "The margin needs review.",
        "evidence_ids": [],
        "tool_result_refs": ["strategy:balanced.metrics.margin_sgd"],
        "fact_refs": ["strategy:balanced.metrics.margin_sgd"],
    }
    spelled_count = dict(misplaced, tool_result_refs=[], statement="All three strategies need review.")
    assert {i["code"] for i in council_module._claim_issues(misplaced, qualitative, typed, set())} == {
        "unknown_tool_reference", "typed_fact_in_context_refs"
    }
    assert {i["code"] for i in council_module._claim_issues(spelled_count, qualitative, typed, set())} == {
        "model_authored_quantity"
    }
    prompt = council_module._prompt("weather_analyst")
    assert "number words" in prompt and "claim_type abstention" in prompt
    assert "recommendation proceed_simulation" in prompt


def test_chair_must_cite_server_selection_policy():
    issues = council_module._claim_issues(
        {
            "role": "planning_chair",
            "statement": "The server policy selects the eligible plan.",
            "evidence_ids": [],
            "tool_result_refs": [],
            "fact_refs": [],
        },
        {"policy:automatic_selection": "server-owned"},
        {},
        set(),
    )
    assert [issue["code"] for issue in issues] == ["selection_policy_reference_required"]


def test_format_only_failure_repairs_once_and_preserves_rejected_attempt(monkeypatch):
    calls = []
    per_role = {}

    class RepairingGateway(FakeGateway):
        def chat_json(self, role, messages, output_model, **kwargs):
            result = super().chat_json(role, messages, output_model, **kwargs)
            per_role[role] = per_role.get(role, 0) + 1
            if role == "production_analyst" and per_role[role] == 1:
                result.data.statement = "All three strategies need production review."
            return result

    monkeypatch.setattr(council_module.DeepSeekGateway, "from_config", lambda *_, **__: RepairingGateway(calls))
    events = []
    progress = {}
    claims, audits = council_module.council(
        repair_computed(), "repair-run", lambda kind, body: events.append((kind, body)),
        progress=progress,
    )

    production = next(claim for claim in claims if claim["role"] == "production_analyst")
    assert production["status"] == "validated"
    assert len(calls) == len(ROLES) + 1
    assert len(audits) == len(ROLES) + 1
    assert len(progress["audits"]) == len(ROLES) + 1
    rejected = [body for kind, body in events if kind == "claim_rejected" and body.get("role") == "production_analyst"]
    assert rejected[0]["statement"] == "All three strategies need production review."
    assert rejected[0]["validation_issues"][0]["code"] == "model_authored_quantity"
    repair_prompt = calls[4][1][-1]["content"]
    assert "format_correction_only" in repair_prompt and "Preserve the original claim_type" in repair_prompt


def test_format_repair_budget_exhaustion_keeps_next_bad_claim_rejected(monkeypatch):
    calls = []
    per_role = {}

    class ExhaustingGateway(FakeGateway):
        def chat_json(self, role, messages, output_model, **kwargs):
            result = super().chat_json(role, messages, output_model, **kwargs)
            per_role[role] = per_role.get(role, 0) + 1
            if role in ROLES[:3] and per_role[role] == 1:
                result.data.statement = "Three options need review."
            return result

    monkeypatch.setattr(council_module.DeepSeekGateway, "from_config", lambda *_, **__: ExhaustingGateway(calls))
    claims, audits = council_module.council(repair_computed(), "exhausted-run", lambda *_: None)

    assert len(calls) == len(ROLES) + 2
    assert len(audits) == len(ROLES) + 2
    assert claims[0]["status"] == claims[1]["status"] == "validated"
    assert claims[2]["status"] == "rejected"
    assert claims[2]["validation_issues"][0]["code"] == "model_authored_quantity"
