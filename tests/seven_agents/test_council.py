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
        requirement = context["role_context"]["output_requirement"]
        required_ref = requirement.get("required_qualitative_reference")
        if required_ref:
            context_ref = next(
                alias for alias, value in context["qualitative_context"].items()
                if value["canonical_reference"] == required_ref
            )
            claim_type = "abstention"
            statement = "The role-specific source is unavailable, so this advisor abstains."
            fact_refs = []
        else:
            context_ref = next(iter(context["qualitative_context"]))
            if role == "planning_chair":
                context_ref = next(
                    alias for alias, value in context["qualitative_context"].items()
                    if value["canonical_reference"] == "policy:automatic_selection"
                )
            claim_type = "observation"
            statement = "The frozen comparison supports this role-specific finding."
            fact_ref = next(iter(context["typed_facts"]), None)
            fact_refs = [fact_ref] if fact_ref else []
        data = output_model.model_validate(
            {
                "claim_type": claim_type,
                "statement": statement,
                "evidence_ids": [],
                "tool_result_refs": [context_ref],
                "fact_refs": fact_refs,
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
                "booked_delivered_kg": 3.0,
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
    assert all(claim["status"] == "validated" for claim in claims)
    factual = [claim for claim in claims if claim["fact_refs"]]
    assert len(factual) == 5
    assert all(claim["evidence_status"] == "grounded_facts_qualitative_unverified" for claim in factual)
    assert all(claim["rendered_facts"][0]["verification"] == "code_rendered_frozen_value" for claim in factual)
    assert {
        claim["role"] for claim in claims if claim["claim_type"] == "abstention"
    } == {"weather_analyst", "market_analyst"}
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
    parsed = __import__("json").loads(planner_context)
    assert set(parsed["qualitative_context"]).isdisjoint(parsed["typed_facts"])
    assert all(ref.startswith("C") for ref in parsed["qualitative_context"])
    policy = next(
        value for value in parsed["qualitative_context"].values()
        if value["canonical_reference"] == "policy:automatic_selection"
    )
    assert policy["value"]["numerical_candidate"] == {
        "strategy_id": "balanced",
        "strategy_name": "Balanced",
        "status": "candidate_before_council_gate",
    }
    assert policy["value"]["council_policy"] == "required"
    assert policy["value"]["council_gate"]["review_completion_alone_requires_withholding"] is False
    demand_context = __import__("json").loads(calls[0][1][1]["content"])
    assert all(ref.startswith("F") for ref in demand_context["typed_facts"])
    assert any(value["context"] == "forecast" for value in demand_context["typed_facts"].values())
    margin = next(
        value for value in parsed["typed_facts"].values()
        if value["canonical_reference"].endswith("metrics.margin_sgd")
    )
    assert "calculated synthetic margin" in margin["semantic_label"]
    assert margin["reference"] == margin["canonical_reference"]


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
    assert aliased_qualitative["C001"]["value"] == "server-owned policy"
    assert aliased_qualitative["C001"]["canonical_reference"] == "policy:automatic_selection"
    assert aliased_typed["F001"]["alias"] == "F001"
    assert aliased_typed["F001"]["reference"] == "order:strategy_order:order-0-0.shortfall_kg"
    assert aliased_typed["F001"]["semantic_label"].endswith("unfilled demand quantity")
    claim, returned, alias_issues = council_module._resolve_claim_aliases(
        {"tool_result_refs": ["C001"], "fact_refs": ["F001"]}, mapping
    )
    assert alias_issues == []
    assert returned == {"tool_result_refs": ["C001"], "fact_refs": ["F001"]}
    assert claim["tool_result_refs"] == ["policy:automatic_selection"]
    assert claim["fact_refs"] == ["order:strategy_order:order-0-0.shortfall_kg"]
    assert council_module.render_facts(claim["fact_refs"], typed)[0]["value"] == 4.0


def test_absent_external_sources_project_abstention_instead_of_plan_metrics():
    computed = repair_computed()
    qualitative, typed = council_module._mission_context(
        computed,
        {"status": "not_connected", "observations": [], "summary": "No feed."},
        None,
        None,
    )

    weather_qualitative, weather_typed = council_module._role_context(
        "weather_analyst", qualitative, typed
    )
    market_qualitative, market_typed = council_module._role_context(
        "market_analyst", qualitative, typed
    )
    weather_requirement = council_module._role_context_descriptor(
        "weather_analyst", weather_qualitative, weather_typed
    )["output_requirement"]
    market_requirement = council_module._role_context_descriptor(
        "market_analyst", market_qualitative, market_typed
    )["output_requirement"]

    assert weather_typed == market_typed == {}
    assert set(weather_qualitative) == {"source:site_weather_availability"}
    assert set(market_qualitative) == {"market:availability", "market:signals.summary"}
    assert weather_requirement["claim_type"] == market_requirement["claim_type"] == "abstention"
    assert weather_requirement["fact_refs"] == market_requirement["fact_refs"] == []

    advisory_qualitative, _ = council_module._mission_context(
        computed, None, None, None, "advisory"
    )
    policy = advisory_qualitative["policy:automatic_selection"]
    assert policy["council_policy"] == "advisory"
    assert policy["council_gate"]["rejected_or_withholding_finding"] == (
        "records advisory issues without blocking numerical acceptance"
    )


def test_role_gates_reject_generic_or_semantically_wrong_supported_shapes():
    weather_refs = {
        "source:site_weather_availability": {"status": "absent"},
    }
    generic_weather = {
        "role": "weather_analyst",
        "claim_type": "observation",
        "statement": "The internal plan appears feasible.",
        "evidence_ids": [],
        "tool_result_refs": ["source:site_weather_availability"],
        "fact_refs": [],
        "recommendation": "proceed_simulation",
    }
    assert [
        issue["code"] for issue in council_module._claim_issues(
            generic_weather, weather_refs, {}, set()
        )
    ] == ["optional_context_abstention_required"]

    market_fact = "strategy:balanced.metrics.margin_sgd"
    absent_market_with_internal_margin = {
        **generic_weather,
        "role": "market_analyst",
        "claim_type": "observation",
        "tool_result_refs": ["market:availability"],
        "fact_refs": [market_fact],
    }
    issues = council_module._claim_issues(
        absent_market_with_internal_margin,
        {"market:availability": {"status": "absent"}},
        {market_fact: {"reference": market_fact}},
        set(),
    )
    assert {issue["code"] for issue in issues} == {
        "optional_context_abstention_required", "absent_context_fact_reference",
    }

    supply_without_fact = {
        **generic_weather,
        "role": "supply_chain_analyst",
        "tool_result_refs": ["strategy:balanced.violations"],
    }
    issues = council_module._claim_issues(
        supply_without_fact,
        {"strategy:balanced.violations": {"status": "none"}},
        {"strategy:balanced.metrics.shortfall_kg": {"reference": "strategy:balanced.metrics.shortfall_kg"}},
        set(),
    )
    assert [issue["code"] for issue in issues] == ["role_relevant_fact_required"]


def test_supply_context_exposes_code_derived_booked_fulfillment_per_strategy():
    computed = repair_computed()
    computed["strategies"].append({
        **computed["strategies"][0],
        "id": "resilient",
        "name": "Resilient",
        "metrics": {
            **computed["strategies"][0]["metrics"],
            "booked_requested_kg": 5.0,
            "booked_delivered_kg": 5.0,
        },
    })
    qualitative, typed = council_module._mission_context(
        computed, None, None, None
    )
    supply_qualitative, supply_typed = council_module._role_context(
        "supply_chain_analyst", qualitative, typed
    )

    assert supply_qualitative["strategy:balanced.booked_fulfillment"] == {
        "strategy_name": "Balanced",
        "status": "partial_delivery",
        "all_booked_demand_fully_delivered": False,
        "meaning": (
            "This frozen plan has a positive booked-demand shortfall; "
            "booked demand is not fully delivered."
        ),
    }
    assert supply_qualitative["strategy:resilient.booked_fulfillment"][
        "all_booked_demand_fully_delivered"
    ] is True
    values = {
        reference: record["value"] for reference, record in supply_typed.items()
    }
    assert values["strategy:balanced.metrics.booked_requested_kg"] == 4.0
    assert values["strategy:balanced.metrics.booked_delivered_kg"] == 3.0
    assert values["strategy:balanced.metrics.booked_shortfall_kg"] == 1.0
    assert values["strategy:resilient.metrics.booked_shortfall_kg"] == 0.0


def test_supply_booked_fulfillment_guard_rejects_false_totals_but_accepts_negatives():
    refs = {
        "strategy:balanced.booked_fulfillment": {
            "strategy_name": "Balanced",
            "status": "partial_delivery",
            "all_booked_demand_fully_delivered": False,
        },
        "strategy:resilient.booked_fulfillment": {
            "strategy_name": "Resilient",
            "status": "fully_delivered",
            "all_booked_demand_fully_delivered": True,
        },
    }
    typed_ref = "strategy:balanced.metrics.booked_shortfall_kg"
    typed = {typed_ref: {"reference": typed_ref}}

    def issue_codes(statement):
        return {
            issue["code"] for issue in council_module._claim_issues(
                {
                    "role": "supply_chain_analyst",
                    "claim_type": "observation",
                    "statement": statement,
                    "evidence_ids": [],
                    "tool_result_refs": [
                        "strategy:balanced.booked_fulfillment"
                    ],
                    "fact_refs": [typed_ref],
                    "recommendation": "proceed_simulation",
                },
                refs,
                typed,
                set(),
            )
        }

    assert issue_codes("Booked order routing is fully delivered.") == {
        "booked_fulfillment_contradiction"
    }
    assert issue_codes("Each booked order is delivered.") == {
        "booked_fulfillment_contradiction"
    }
    assert issue_codes("Balanced booked demand is completely covered.") == {
        "booked_fulfillment_contradiction"
    }
    assert issue_codes("Booked order routing is not fully delivered.") == set()
    assert issue_codes("Not all booked orders are delivered.") == set()
    assert issue_codes("Resilient booked demand is fully delivered.") == set()
    assert issue_codes(
        "Some booked quantities are delivered, while total demand remains unfilled."
    ) == set()


def test_supply_semantic_failure_does_not_spend_format_repair(monkeypatch):
    calls = []

    class ContradictingGateway(FakeGateway):
        def chat_json(self, role, messages, output_model, **kwargs):
            result = super().chat_json(role, messages, output_model, **kwargs)
            if role == "supply_chain_analyst":
                result.data.statement = "Booked order routing is fully delivered."
            return result

    monkeypatch.setattr(
        council_module.DeepSeekGateway,
        "from_config",
        lambda *_, **__: ContradictingGateway(calls),
    )
    events = []
    claims, audits = council_module.council(
        repair_computed(),
        "semantic-rejection-run",
        lambda kind, body: events.append((kind, body)),
    )

    supply = next(
        claim for claim in claims if claim["role"] == "supply_chain_analyst"
    )
    assert len(calls) == len(ROLES)
    assert len(audits) == len(ROLES)
    assert supply["status"] == "rejected"
    assert [issue["code"] for issue in supply["validation_issues"]] == [
        "booked_fulfillment_contradiction"
    ]
    assert all(
        "format_correction_only" not in message["content"]
        for _, messages, _ in calls for message in messages
    )
    assert any(
        kind == "claim_rejected"
        and body.get("role") == "supply_chain_analyst"
        for kind, body in events
    )


def test_role_relevance_failures_reject_without_spending_format_repairs(monkeypatch):
    calls = []

    class IrrelevantGateway(FakeGateway):
        def chat_json(self, role, messages, output_model, **kwargs):
            result = super().chat_json(role, messages, output_model, **kwargs)
            if role == "weather_analyst":
                result.data.claim_type = "observation"
            if role == "supply_chain_analyst":
                result.data.fact_refs = []
            return result

    monkeypatch.setattr(
        council_module.DeepSeekGateway,
        "from_config",
        lambda *_, **__: IrrelevantGateway(calls),
    )
    claims, audits = council_module.council(
        repair_computed(), "relevance-run", lambda *_: None
    )

    assert len(calls) == len(ROLES)
    assert len(audits) == len(ROLES)
    weather = next(claim for claim in claims if claim["role"] == "weather_analyst")
    supply = next(claim for claim in claims if claim["role"] == "supply_chain_analyst")
    assert [issue["code"] for issue in weather["validation_issues"]] == [
        "optional_context_abstention_required"
    ]
    assert [issue["code"] for issue in supply["validation_issues"]] == [
        "role_relevant_fact_required"
    ]


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
    assert "number words" in prompt and "role_context.output_requirement" in prompt
    assert "booked_fulfillment records are code-derived totals" in prompt
    assert '"recommendation":"proceed_simulation"' in prompt


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
