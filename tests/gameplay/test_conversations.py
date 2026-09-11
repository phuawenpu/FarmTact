from __future__ import annotations

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
import secrets
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from packages.contracts import content_hash
from packages.planner.engine import allocations_existing
from runtime.deepseek_gateway import DeepSeekGatewayError, DeepSeekResponseError, SafeAudit, Usage
from services.api.app import create_app
from services.api.conversation_store import ConversationStore
from services.api.conversations import (
    ADVISORS,
    AdvisorReply,
    MAX_PROVIDER_CONTEXT_CHARACTERS,
    _bounded_model_context,
    _provider_messages,
    _tool_results,
    execute_conversation_job,
)
from services.api.store import Store


def minimal_plan(farm):
    return {
        "input_hash": content_hash(farm),
        "strategies": [
            {
                "id": "balanced-fixture",
                "name": "Balanced",
                "status": "FEASIBLE",
                "metrics": {"margin_sgd": 500.0, "fill_rate": 0.9},
                "violations": [],
            }
        ],
        "forecast": {"demand": [], "harvest": []},
        "scenario_set": [],
    }


def minimal_three_policy_plan(farm):
    strategies = []
    allocations = allocations_existing(farm)
    for index, name in enumerate(("Lean", "Balanced", "Resilient")):
        strategies.append(
            {
                "id": f"{name.lower()}-fixture",
                "name": name,
                "status": "FEASIBLE",
                "metrics": {"margin_sgd": 500.0 - index, "fill_rate": 0.9},
                "violations": [],
                "allocations": deepcopy(allocations),
                "ledger": [],
            }
        )
    return {
        "input_hash": content_hash(farm),
        "strategies": strategies,
        "forecast": {"demand": [], "harvest": []},
        "scenario_set": [],
    }


class FakeGateway:
    def __init__(self, budget, calls, responses=None):
        self.budget = budget
        self.calls = calls
        self.responses = responses if responses is not None else []

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def chat_json(self, role, messages, output_model, max_tokens=512, **_):
        self.budget.reserve(max_tokens)
        self.calls.append({"role": role, "messages": deepcopy(messages)})
        if self.responses:
            response = self.responses.pop(0)
            if isinstance(response, Exception):
                raise response
        else:
            relationship = (
                "conclusion"
                if "relationship should normally be conclusion"
                in messages[0]["content"]
                else "answer"
            )
            supplied_facts = json.loads(messages[1]["content"])["typed_facts"]
            response = {
                "content": f"{ADVISORS[next(key for key, row in ADVISORS.items() if row['role'] == role)]['name']} reviewed the frozen comparison.",
                "evidence_refs": [],
                "tool_refs": [],
                "fact_refs": [next(iter(supplied_facts))],
                "highlight_refs": [],
                "relationship": relationship,
                "proposed_actions": [],
            }
        data = output_model.model_validate(response)
        usage = Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
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
            request_id="fixture-request",
            latency_ms=1,
            usage=usage,
        )
        return SimpleNamespace(
            data=data,
            model="deepseek-flash",
            usage=usage,
            audit=audit,
        )


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setenv("DEEPSEEK_API_KEY", "unit-test-placeholder")
    monkeypatch.setattr("packages.planner.plan", minimal_plan)
    store = Store("sqlite://")
    app = create_app(store, start_worker=False)
    with TestClient(app) as client:
        client.get("/api/v1/bootstrap")
        tenant = store.authenticate(client.cookies.get("farmtact_session"))
        yield client, store, tenant


def gateway_factory(monkeypatch, calls, responses=None):
    queue = list(responses or [])

    def factory(*_, budget=None, **__):
        return FakeGateway(budget, calls, queue)

    monkeypatch.setattr(
        "services.api.conversations.DeepSeekGateway.from_config", staticmethod(factory)
    )


def schema_failure(response):
    try:
        AdvisorReply.model_validate(response)
    except ValidationError as cause:
        error = DeepSeekResponseError(
            "DeepSeek structured output failed local validation"
        )
        error.__cause__ = cause
        return error
    raise AssertionError("Fixture response unexpectedly passed schema validation")


def create(client, key="conversation", **body):
    return client.post(
        "/api/v1/conversations",
        json={"advisor": "mei", **body},
        headers={"Idempotency-Key": key},
    )


def send(client, conversation_id, key="message", **body):
    return client.post(
        f"/api/v1/conversations/{conversation_id}/messages",
        json={"content": "Why is this bed delayed?", **body},
        headers={"Idempotency-Key": key},
    )


def execute(store, tenant, request_id):
    execute_conversation_job(store, tenant, request_id)


def test_seven_current_advisors_and_frozen_create_idempotency(env):
    client, store, tenant = env
    roster = client.get("/api/v1/conversations/advisors").json()["advisors"]
    assert [(row["id"], row["name"]) for row in roster] == [
        ("ravi", "Ravi"),
        ("hana", "Hana"),
        ("idris", "Idris"),
        ("mei", "Mei"),
        ("lina", "Lina"),
        ("ben", "Ben"),
        ("asha", "Asha"),
    ]
    first = create(client).json()
    frozen = ConversationStore(store).get_conversation(tenant, first["id"])
    original_hash = frozen["snapshot_ref"]["hash"]
    changed = deepcopy(store.latest_farm(tenant))
    changed["resources"]["cash_sgd"] = "12345"
    store.save_farm(tenant, changed)
    retry = create(client).json()
    assert retry == {"id": first["id"], "status": "OPEN", "reused": True}
    assert ConversationStore(store).get_conversation(tenant, first["id"])[
        "snapshot_ref"
    ]["hash"] == original_hash
    assert create(client, advisor="ravi").status_code == 409
    public = client.get(f"/api/v1/conversations/{first['id']}").json()
    assert public["tool_results"]["batch:batch-01.bed_id"] == "bed-01"
    assert public["tool_results"]["batch:batch-01.crop_id"] == "caixin"
    assert public["tool_results"]["recipe:caixin-demo-v1.biological_lead_days"] == 28
    # Offline source cache availability is independent from conversation creation.
    assert public["source_workflow_type"] == "numerical_snapshot_advisor"
    assert public["tool_results"]["market:signals"]["status"] == "not_connected"
    assert public["tool_results"]["market:signals"]["connected_social_feeds"] is False


def test_direct_message_persists_validated_reply_and_replay_makes_no_call(
    env, monkeypatch
):
    client, store, tenant = env
    calls = []
    gateway_factory(monkeypatch, calls)
    conversation_id = create(client).json()["id"]
    queued = send(client, conversation_id).json()
    execute(store, tenant, queued["id"])
    transcript = client.get(f"/api/v1/conversations/{conversation_id}").json()
    assert [message["speaker_id"] for message in transcript["messages"]] == [
        "farmer",
        "mei",
    ]
    reply = transcript["messages"][-1]
    assert reply["reply_to"] == queued["message_id"]
    assert reply["validation_status"] == "references_verified"
    assert reply["interpretation_status"] == "qualitative_unverified"
    assert reply["evidence_status"] == "grounded_facts_qualitative_unverified"
    assert reply["rendered_facts"][0]["unit"] in {"SGD", "ratio"}
    assert transcript["tool_results"]["farm:resources.cash_sgd"]
    assert transcript["transcript_mode"] == "recorded"
    monkeypatch.setattr(
        store, "reserve_calls", lambda *_: pytest.fail("GET/replay reserved inference")
    )
    assert client.get(f"/api/v1/conversations/{conversation_id}").status_code == 200
    replay = client.get(f"/api/v1/conversations/{conversation_id}/replay").json()
    assert replay["transcript_mode"] == "replay"
    assert replay["inference_origin"] == "stored_actual_replay"
    assert replay["inference_triggered"] is False
    assert len(calls) == 1


def test_historical_idris_header_stays_critic_but_new_reply_uses_market(env, monkeypatch):
    client, store, tenant = env
    calls = []
    gateway_factory(monkeypatch, calls)
    conversation_id = create(
        client, advisor="idris", key="historical-idris-conversation"
    ).json()["id"]
    persistence = ConversationStore(store)
    archived = persistence.get_conversation(tenant, conversation_id)
    archived["advisor_role"] = "independent_critic"
    persistence.save_conversation(tenant, archived)

    for suffix in ("", "/replay"):
        public = client.get(f"/api/v1/conversations/{conversation_id}{suffix}").json()
        assert public["advisor_role"] == "independent_critic"
        assert public["advisor"]["role"] == "independent_critic"
        assert public["advisor"]["title"] == "Independent critic"

    queued = send(
        client,
        conversation_id,
        key="historical-idris-new-reply",
        content="Review the current market context.",
    ).json()
    execute(store, tenant, queued["id"])
    assert calls[0]["role"] == "market_analyst"
    reply = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"][-1]
    assert reply["advisor_role"] == "market_analyst"


def test_invitation_is_two_sided_exchange_with_specific_reply_graph_and_prior_turns(
    env, monkeypatch
):
    client, store, tenant = env
    calls = []
    gateway_factory(monkeypatch, calls)
    conversation_id = create(client).json()["id"]
    first_job = send(client, conversation_id).json()
    execute(store, tenant, first_job["id"])
    first_reply = client.get(f"/api/v1/conversations/{conversation_id}").json()[
        "messages"
    ][-1]
    persistence = ConversationStore(store)
    for index in range(33):
        persistence.append_message(
            tenant,
            conversation_id,
            {
                "id": f"older-context-filler-{index}",
                "speaker": "system",
                "speaker_id": "system",
                "content": f"Recorded event {index}",
                "created_at": "2026-09-08T00:00:00+00:00",
            },
        )
    invited = client.post(
        f"/api/v1/conversations/{conversation_id}/invite",
        json={
            "advisor": "ravi",
            "question": "Challenge Mei's explanation using the same snapshot.",
            "reply_to": first_reply["id"],
        },
        headers={"Idempotency-Key": "invite-ravi"},
    ).json()
    execute(store, tenant, invited["id"])
    messages = client.get(f"/api/v1/conversations/{conversation_id}").json()[
        "messages"
    ]
    invited_reply, return_challenge = messages[-2:]
    assert invited_reply["speaker_id"] == "ravi"
    assert invited_reply["reply_to"] == first_reply["id"]
    assert return_challenge["speaker_id"] == "mei"
    assert return_challenge["reply_to"] == invited_reply["id"]
    second_invitation_call = calls[-1]
    context = json.loads(second_invitation_call["messages"][1]["content"])
    assert any(turn["id"] == invited_reply["id"] for turn in context["prior_turns"])

    return_invitation = client.post(
        f"/api/v1/conversations/{conversation_id}/invite",
        json={
            "advisor": "mei",
            "question": "Answer Ravi's selected point.",
            "reply_to": invited_reply["id"],
        },
        headers={"Idempotency-Key": "invite-mei-to-ravi"},
    )
    assert return_invitation.status_code == 202
    execute(store, tenant, return_invitation.json()["id"])
    messages = client.get(f"/api/v1/conversations/{conversation_id}").json()[
        "messages"
    ]
    mei_reply, ravi_return = messages[-2:]
    assert mei_reply["speaker_id"] == "mei"
    assert mei_reply["reply_to"] == invited_reply["id"]
    assert ravi_return["speaker_id"] == "ravi"
    assert ravi_return["reply_to"] == mei_reply["id"]

    same_author = client.post(
        f"/api/v1/conversations/{conversation_id}/invite",
        json={
            "advisor": "ravi",
            "question": "Reply to your own selected point.",
            "reply_to": invited_reply["id"],
        },
        headers={"Idempotency-Key": "invite-ravi-to-ravi"},
    )
    assert same_author.status_code == 422
    assert same_author.json()["detail"] == "Invite a different advisor into this exchange"


def test_council_has_seven_bounded_turns_all_with_prior_claims_and_planner_conclusion(
    env, monkeypatch
):
    client, store, tenant = env
    calls = []
    gateway_factory(monkeypatch, calls)
    conversation_id = create(client).json()["id"]
    council = client.post(
        f"/api/v1/conversations/{conversation_id}/council",
        json={"question": "Compare the tradeoffs and show disagreements."},
        headers={"Idempotency-Key": "council"},
    ).json()
    execute(store, tenant, council["id"])
    transcript = client.get(f"/api/v1/conversations/{conversation_id}").json()
    advisor_messages = [
        message for message in transcript["messages"] if message["speaker"] == "advisor"
    ]
    assert [message["advisor_role"] for message in advisor_messages] == [
        "demand_analyst",
        "weather_analyst",
        "market_analyst",
        "production_analyst",
        "supply_chain_analyst",
        "profit_analyst",
        "planning_chair",
    ]
    assert len(calls) == 7
    for index, call in enumerate(calls[1:], start=1):
        context = json.loads(call["messages"][1]["content"])
        earlier = [turn for turn in context["prior_turns"] if turn["speaker"] == "advisor"]
        assert len(earlier) == index
    assert advisor_messages[-1]["planner_conclusion"] is True
    assert all(message["request_mode"] == "council" for message in advisor_messages)
    assert advisor_messages[-1]["relationship"] == "conclusion"
    assert advisor_messages[-1]["validation_status"] == "references_verified"
    assert advisor_messages[-1]["reply_to"] == advisor_messages[-2]["id"]


def test_council_final_answer_is_unsupported_and_not_a_planner_conclusion(
    env, monkeypatch
):
    client, store, tenant = env
    calls = []
    malformed_final = {
        "content": "The final review remains attached to the frozen evidence.",
        "evidence_refs": [],
        "tool_refs": ["farm:resources.cash_sgd"],
        "highlight_refs": [],
        "relationship": "answer",
        "proposed_actions": [],
    }
    gateway_factory(monkeypatch, calls, responses=[malformed_final] * 7)
    conversation_id = create(client, key="malformed-council-conversation").json()["id"]
    council = client.post(
        f"/api/v1/conversations/{conversation_id}/council",
        json={"question": "Reach a planner conclusion from the frozen evidence."},
        headers={"Idempotency-Key": "malformed-council"},
    ).json()
    execute(store, tenant, council["id"])
    transcript = client.get(f"/api/v1/conversations/{conversation_id}").json()
    final_message = transcript["messages"][-1]
    assert len(calls) == 7
    assert final_message["advisor_role"] == "planning_chair"
    assert final_message["relationship"] == "answer"
    assert final_message["validation_status"] == "unsupported"
    assert final_message["planner_conclusion"] is False
    assert (
        "Final planning chair turn must use the conclusion relationship"
        in final_message["validation_errors"]
    )


def test_unsupported_numbers_evidence_and_actions_are_visible_but_never_executed(
    env, monkeypatch
):
    client, store, tenant = env
    calls = []
    gateway_factory(
        monkeypatch,
        calls,
        responses=[
            {
                "content": "Margin will improve by 12 percent.",
                "evidence_refs": ["unknown-paper"],
                "tool_refs": [],
                "highlight_refs": ["bed:unknown"],
                "relationship": "answer",
                "proposed_actions": [
                    {
                        "control": "cash_percent",
                        "target_id": None,
                        "value": 80,
                        "unit": "percent",
                    }
                ],
            }
        ],
    )
    conversation_id = create(client).json()["id"]
    queued = send(client, conversation_id).json()
    farm_before = deepcopy(store.latest_farm(tenant))
    execute(store, tenant, queued["id"])
    public = client.get(f"/api/v1/conversations/{conversation_id}").json()
    reply = public["messages"][-1]
    assert reply["validation_status"] == "unsupported"
    assert public["model_call_status"] == "completed"
    assert public["evidence_status"] == "unsupported_all"
    assert public["decision_influence"] == "advisory_only"
    assert "Advisor prose contains a quantitative or temporal claim; exact values render only from fact_refs" in reply[
        "validation_errors"
    ]
    assert reply["proposed_actions"][0]["status"] == "blocked_unsupported"
    assert store.latest_farm(tenant) == farm_before


@pytest.mark.parametrize(
    ("action", "expected_errors"),
    [
        (
            {
                "control": "delay_days",
                "target_id": None,
                "value": 15,
                "unit": "percent",
            },
            {
                "Delay action unit must be days",
                "Delay action value must be between 0 and 14 days",
                "Delay action must target an actual frozen batch",
            },
        ),
        (
            {
                "control": "yield_percent",
                "target_id": "missing-batch",
                "value": 49,
                "unit": "days",
            },
            {
                "Yield action unit must be percent",
                "Yield action value must be between 50 and 100 percent",
                "Yield action must target an actual frozen batch",
            },
        ),
        (
            {
                "control": "demand_percent",
                "target_id": "unsupported-crop",
                "value": 151,
                "unit": "days",
            },
            {
                "Demand action unit must be percent",
                "Demand action value must be between 50 and 150 percent",
                "Demand action must target a supported simulated crop",
            },
        ),
        (
            {
                "control": "cash_percent",
                "target_id": "batch-01",
                "value": 49,
                "unit": "days",
            },
            {
                "Resource action unit must be percent",
                "Resource action value must be between 50 and 150 percent",
                "Resource actions must use a null target_id",
            },
        ),
    ],
    ids=["delay", "yield", "demand", "resource"],
)
def test_cross_field_action_errors_persist_as_blocked_without_schema_repair(
    env, monkeypatch, action, expected_errors
):
    client, store, tenant = env
    calls = []
    gateway_factory(
        monkeypatch,
        calls,
        responses=[
            {
                "content": "The frozen context supports a cautious review. This proposed experiment needs corrected controls.",
                "evidence_refs": [],
                "tool_refs": ["farm:resources.cash_sgd"],
                "highlight_refs": [],
                "relationship": "answer",
                "proposed_actions": [action],
            }
        ],
    )
    conversation_id = create(
        client, key=f"invalid-{action['control']}-conversation"
    ).json()["id"]
    queued = send(
        client, conversation_id, key=f"invalid-{action['control']}-message"
    ).json()
    farm_before = deepcopy(store.latest_farm(tenant))
    execute(store, tenant, queued["id"])
    request = ConversationStore(store).get_request(tenant, queued["id"])
    reply = client.get(f"/api/v1/conversations/{conversation_id}").json()[
        "messages"
    ][-1]
    assert len(calls) == 1
    assert request["status"] == "COMPLETED"
    assert request["repair_attempts"] == 0
    assert reply["validation_status"] == "unsupported"
    assert expected_errors.issubset(reply["validation_errors"])
    assert reply["proposed_actions"] == [{**action, "status": "blocked_unsupported"}]
    assert store.latest_farm(tenant) == farm_before


def test_message_retry_returns_terminal_job_without_repeating_paid_call(env, monkeypatch):
    client, store, tenant = env
    calls = []
    gateway_factory(monkeypatch, calls)
    conversation_id = create(client).json()["id"]
    first = send(client, conversation_id, key="network-retry").json()
    execute(store, tenant, first["id"])
    retry = send(client, conversation_id, key="network-retry").json()
    assert retry["id"] == first["id"] and retry["reused"] is True
    execute(store, tenant, retry["id"])
    assert len(calls) == 1
    persistence = ConversationStore(store)
    for index in range(118):
        persistence.append_message(
            tenant,
            conversation_id,
            {
                "id": f"limit-filler-{index}",
                "speaker": "system",
                "speaker_id": "system",
                "content": "Recorded event",
                "created_at": "2026-09-08T00:00:00+00:00",
            },
        )
    at_limit_retry = send(client, conversation_id, key="network-retry").json()
    assert at_limit_retry["id"] == first["id"] and at_limit_retry["reused"]
    assert send(client, conversation_id, key="new-at-limit").status_code == 409


def test_numeric_coincidence_never_semantically_validates_wrong_quantity(env, monkeypatch):
    client, store, tenant = env
    calls = []
    gateway_factory(
        monkeypatch,
        calls,
        responses=[
            {
                "content": "Balanced margin is 32 SGD.",
                "evidence_refs": [],
                "tool_refs": ["strategy:balanced.metrics.fill_rate"],
                "highlight_refs": [],
                "relationship": "answer",
                "proposed_actions": [],
            }
        ],
    )
    conversation_id = create(client, key="coincidence-conversation").json()["id"]
    queued = send(client, conversation_id, key="coincidence-message").json()
    execute(store, tenant, queued["id"])
    reply = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"][-1]
    assert reply["validation_status"] == "unsupported"
    assert reply["validation_scope"] == "typed_fact_membership_entity_unit_period_and_supported_controls"
    events = client.get(f"/api/v1/conversations/{conversation_id}/events").json()["events"]
    rejected = next(event for event in events if event["event_type"] == "advisor_reply_rejected")
    assert {issue["code"] for issue in rejected["body"]["validation_issues"]} == {
        "typed_fact_in_context_refs", "model_authored_quantity"
    }


@pytest.mark.parametrize(
    "content",
    [
        "The margin may improve by twelve percent.",
        "The harvest is expected on September eighth.",
        "The harvest is expected tomorrow.",
    ],
)
def test_spelled_quantities_and_relative_dates_remain_unsupported(
    env, monkeypatch, content
):
    client, store, tenant = env
    calls = []
    gateway_factory(
        monkeypatch,
        calls,
        responses=[
            {
                "content": content,
                "evidence_refs": [],
                "tool_refs": ["batch:batch-01.harvest_date"],
                "highlight_refs": [],
                "relationship": "answer",
                "proposed_actions": [],
            }
        ],
    )
    conversation_id = create(
        client, key=f"spelled-claim-{content[:10]}"
    ).json()["id"]
    queued = send(client, conversation_id, key=f"spelled-message-{content[:10]}").json()
    execute(store, tenant, queued["id"])
    reply = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"][-1]
    assert reply["validation_status"] == "unsupported"
    events = client.get(f"/api/v1/conversations/{conversation_id}/events").json()["events"]
    rejected = next(event for event in events if event["event_type"] == "advisor_reply_rejected")
    assert rejected["body"]["content"] == content
    assert "model_authored_quantity" in {
        issue["code"] for issue in rejected["body"]["validation_issues"]
    }


def test_format_only_reply_repair_preserves_meaning_fields_and_original_attempt(env, monkeypatch):
    client, store, tenant = env
    calls = []
    original = {
        "content": "The one delayed batch needs review.",
        "evidence_refs": [],
        "tool_refs": ["batch:batch-01.harvest_date"],
        "fact_refs": [],
        "highlight_refs": [],
        "relationship": "answer",
        "proposed_actions": [],
    }
    corrected = {
        **original,
        "content": "The delayed batch needs review.",
        "tool_refs": [],
        "fact_refs": ["batch:batch-01.harvest_date"],
    }
    gateway_factory(monkeypatch, calls, responses=[original, corrected])
    conversation_id = create(client, key="format-repair-conversation").json()["id"]
    queued = send(client, conversation_id, key="format-repair-message").json()
    execute(store, tenant, queued["id"])

    transcript = client.get(f"/api/v1/conversations/{conversation_id}").json()
    reply = transcript["messages"][-1]
    events = client.get(f"/api/v1/conversations/{conversation_id}/events").json()["events"]
    rejected = next(event for event in events if event["event_type"] == "advisor_reply_rejected")
    assert len(calls) == 2
    assert reply["validation_status"] == "references_verified"
    assert reply["relationship"] == original["relationship"]
    assert reply["proposed_actions"] == original["proposed_actions"]
    assert rejected["body"]["content"] == original["content"]
    assert rejected["body"]["usage"]["total_tokens"] == 15


def test_bounded_research_context_keeps_exact_inputs_without_full_catalogue():
    tools = {
        **{f"delivery:order-{index}.quantity_kg": index for index in range(100)},
        "research:inputs": {"large": "aggregate"},
        "research:reservation:bed-04": {"kind": "research_only_bed_reservation"},
        "research:reservation:bed-04.start_date": "2026-09-17",
        "research:unconfirmed_order:research-extra-order": {
            "kind": "research_only_unconfirmed_order"
        },
        "research:labour_percent": 100,
    }
    from packages.ai_contracts import typed_reference_catalog

    conversation = {
        "snapshot_ref": {"kind": "research", "hash": "frozen"},
        "selected_bed_id": "bed-04",
        "_tool_results": tools,
        "_typed_facts": typed_reference_catalog(tools, snapshot_hash="frozen"),
    }
    qualitative, typed = _bounded_model_context(conversation, "planning_chair")
    assert "research:inputs" not in qualitative
    assert "research:reservation:bed-04" in qualitative
    assert "research:unconfirmed_order:research-extra-order" in qualitative
    assert "research:reservation:bed-04.start_date" in typed
    assert "research:labour_percent" in typed
    assert not any(ref.startswith("delivery:") for ref in typed)


@pytest.mark.parametrize("snapshot_kind", ["scenario", "research"])
def test_provider_context_has_a_hard_serialized_bound_at_maximum_history(snapshot_kind):
    from packages.ai_contracts import typed_reference_catalog

    tools = {
        **{
            f"comparison:policy-{index}.scenario_metrics.margin_sgd": index
            for index in range(300)
        },
        **{
            f"strategy:strategy-{index}.metrics.margin_sgd": index
            for index in range(300)
        },
        "research:reservation:bed-04": {
            "kind": "research_only_bed_reservation",
            "untrusted_padding": "x" * 100_000,
        },
        "research:reservation:bed-04.start_date": "2026-09-17",
        "research:unconfirmed_order:research-extra-order": {
            "kind": "research_only_unconfirmed_order"
        },
    }
    history = [
        {
            "id": f"message-{index}",
            "speaker": "advisor",
            "speaker_id": "mei",
            "content": "x" * 400,
            "evidence_refs": [],
            "tool_refs": [],
            "fact_refs": [],
            "validation_status": "references_verified",
            "evidence_status": "qualitative_unverified",
            "validation_issues": [],
            "relationship": "answer",
        }
        for index in range(120)
    ]

    class Persistence:
        def list_messages(self, *_):
            return history

        def get_message(self, *_):
            return None

    conversation = {
        "id": "bounded",
        "snapshot_ref": {"kind": snapshot_kind, "hash": "frozen"},
        "selected_bed_id": "bed-04",
        "_scenario": {"id": "scenario", "controls": {}, "affected_deliveries": []}
        if snapshot_kind == "scenario" else None,
        "_tool_results": tools,
        "_typed_facts": typed_reference_catalog(tools, snapshot_hash="frozen"),
        "_evidence": [{"finding": "e" * 100_000} for _ in range(24)],
    }
    request = {"mode": "direct", "question": "Review frozen inputs.", "reply_to": None}
    messages = _provider_messages(
        Persistence(), "tenant", conversation, request,
        "planning_chair", "message-119", False,
    )
    context = json.loads(messages[1]["content"])
    assert len(messages[1]["content"]) <= MAX_PROVIDER_CONTEXT_CHARACTERS
    assert len(context["prior_turns"]) == 16
    assert len(context["evidence_context"]) == 6
    if snapshot_kind == "research":
        assert "research:reservation:bed-04" in context["tool_results"]
        assert "research:reservation:bed-04.start_date" in context["typed_facts"]


def test_council_preflight_counts_user_and_all_seven_advisor_turns(env):
    client, store, tenant = env
    conversation_id = create(client, key="council-cap-conversation").json()["id"]
    persistence = ConversationStore(store)
    for index in range(119):
        persistence.append_message(
            tenant,
            conversation_id,
            {
                "id": f"council-cap-filler-{index}",
                "speaker": "system",
                "speaker_id": "system",
                "content": "Recorded event",
                "created_at": "2026-09-08T00:00:00+00:00",
            },
        )
    response = client.post(
        f"/api/v1/conversations/{conversation_id}/council",
        json={"question": "Compare tradeoffs."},
        headers={"Idempotency-Key": "council-over-cap"},
    )
    assert response.status_code == 409
    assert len(persistence.list_messages(tenant, conversation_id)) == 119


def test_budget_exhaustion_and_missing_credentials_create_usable_blocked_states(
    env, monkeypatch
):
    client, store, tenant = env
    calls = []
    gateway_factory(monkeypatch, calls)
    first_id = create(client, key="budget-conversation").json()["id"]
    first = send(client, first_id, key="budget-message").json()
    monkeypatch.setattr(store, "reserve_calls", lambda *_: False)
    execute(store, tenant, first["id"])
    blocked = client.get(f"/api/v1/conversations/{first_id}").json()
    assert blocked["last_request_status"] == "BLOCKED"
    assert len(blocked["messages"]) == 1 and calls == []

    second_id = create(client, key="credential-conversation").json()["id"]
    second = send(client, second_id, key="credential-message").json()
    monkeypatch.delenv("DEEPSEEK_API_KEY")
    monkeypatch.setattr(
        store, "reserve_calls", lambda *_: pytest.fail("missing key reserved budget")
    )
    execute(store, tenant, second["id"])
    assert client.get(f"/api/v1/conversations/{second_id}").json()[
        "last_request_status"
    ] == "BLOCKED"


def test_interruption_and_provider_error_preserve_partial_state_without_requeue(
    env, monkeypatch
):
    client, store, tenant = env
    calls = []
    gateway_factory(monkeypatch, calls, responses=[DeepSeekGatewayError("safe failure")])
    persistence = ConversationStore(store)
    interrupted_id = create(client, key="interrupted-conversation").json()["id"]
    interrupted = send(client, interrupted_id, key="interrupted-message").json()
    assert persistence.claim(tenant, interrupted["id"])
    assert persistence.interrupt_abandoned() == 1
    execute(store, tenant, interrupted["id"])
    assert persistence.get_request(tenant, interrupted["id"])["status"] == "INTERRUPTED"
    assert calls == []

    failed_id = create(client, key="failed-conversation").json()["id"]
    failed = send(client, failed_id, key="failed-message").json()
    execute(store, tenant, failed["id"])
    request = persistence.get_request(tenant, failed["id"])
    assert request["status"] == "FAILED"
    assert request["execution_status"] == "failed"
    assert request["evidence_status"] == "not_evaluated"
    assert "safe failure" in request["error"]
    retry = send(client, failed_id, key="failed-message").json()
    execute(store, tenant, retry["id"])
    assert len(calls) == 1


def test_one_direct_format_repair_and_second_invalid_response_stops(env, monkeypatch):
    client, store, tenant = env
    calls = []
    schema_error = schema_failure(
        {
            "content": "x" * 901,
            "evidence_refs": [],
            "tool_refs": [],
            "highlight_refs": [],
            "relationship": "answer",
            "proposed_actions": [],
        }
    )
    gateway_factory(monkeypatch, calls, responses=[schema_error, schema_error])
    conversation_id = create(client).json()["id"]
    queued = send(client, conversation_id).json()
    execute(store, tenant, queued["id"])
    request = ConversationStore(store).get_request(tenant, queued["id"])
    assert request["status"] == "FAILED"
    assert request["repair_attempts"] == 1
    assert len(calls) == 2
    terminal_event = next(
        event
        for event in ConversationStore(store).get_events(tenant, conversation_id)
        if event["event_type"] == "conversation_request_failed"
    )
    assert terminal_event["body"]["validation_issues"] == [
        {"field": "content", "type": "string_too_long"}
    ]


def test_schema_repair_reports_safe_field_type_and_corrects_long_content(
    env, monkeypatch
):
    client, store, tenant = env
    calls = []
    schema_error = schema_failure(
        {
            "content": "x" * 901,
            "evidence_refs": [],
            "tool_refs": ["farm:resources.cash_sgd"],
            "highlight_refs": [],
            "relationship": "answer",
            "proposed_actions": [],
        }
    )
    gateway_factory(
        monkeypatch,
        calls,
        responses=[
            schema_error,
            {
                "content": "The frozen evidence supports caution. Review the cited cash context.",
                "evidence_refs": [],
                "tool_refs": ["farm:resources.cash_sgd"],
                "highlight_refs": [],
                "relationship": "answer",
                "proposed_actions": [],
            },
        ],
    )
    conversation_id = create(client, key="repair-context-conversation").json()["id"]
    queued = send(client, conversation_id, key="repair-context-message").json()
    execute(store, tenant, queued["id"])
    request = ConversationStore(store).get_request(tenant, queued["id"])
    assert request["status"] == "COMPLETED"
    assert request["repair_attempts"] == 1
    assert len(calls) == 2
    system_prompt = calls[0]["messages"][0]["content"]
    assert "one or two short sentences and no more than 400 characters" in system_prompt
    assert "at most 3 tool_refs, 3 fact_refs, 1 evidence_ref" in system_prompt
    assert '"relationship":"answer"' in system_prompt
    assert '"proposed_actions":[]' in system_prompt
    repair_prompt = calls[1]["messages"][-1]["content"]
    assert "Your response did not match the required JSON schema." in repair_prompt
    assert "content:string_too_long" in repair_prompt
    assert "x" * 100 not in repair_prompt
    repair_event = next(
        event
        for event in ConversationStore(store).get_events(tenant, conversation_id)
        if event["event_type"] == "advisor_reply_repair"
    )
    assert repair_event["body"]["validation_issues"] == [
        {"field": "content", "type": "string_too_long"}
    ]


def test_tenant_isolation_and_last_event_id_resume(env, monkeypatch):
    client, store, tenant = env
    calls = []
    gateway_factory(monkeypatch, calls)
    conversation_id = create(client).json()["id"]
    queued = send(client, conversation_id).json()
    execute(store, tenant, queued["id"])
    all_events = client.get(
        f"/api/v1/conversations/{conversation_id}/events"
    ).json()["events"]
    cursor = all_events[1]["sequence"]
    resumed = client.get(
        f"/api/v1/conversations/{conversation_id}/events?after=1",
        headers={"Last-Event-ID": str(cursor)},
    ).json()["events"]
    assert resumed and all(event["sequence"] > cursor for event in resumed)
    assert len({event["sequence"] for event in resumed}) == len(resumed)
    assert client.get(
        f"/api/v1/conversations/{conversation_id}/events",
        headers={"Last-Event-ID": "invalid"},
    ).status_code == 422

    client.cookies.clear()
    client.get("/api/v1/bootstrap")
    assert client.get(f"/api/v1/conversations/{conversation_id}").status_code == 404
    assert client.get(f"/api/v1/conversations/{conversation_id}/replay").status_code == 404


def test_whitespace_is_rejected_and_reply_to_advisor_targets_that_speaker(env, monkeypatch):
    client, store, tenant = env
    calls = []
    gateway_factory(monkeypatch, calls)
    conversation_id = create(client).json()["id"]
    assert send(client, conversation_id, content="   ").status_code == 422
    assert client.post(
        f"/api/v1/conversations/{conversation_id}/council",
        json={"question": " \n "},
        headers={"Idempotency-Key": "blank-council"},
    ).status_code == 422
    critic = ConversationStore(store).append_message(
        tenant,
        conversation_id,
        {
            "id": "idris-specific-point",
            "speaker": "advisor",
            "speaker_id": "idris",
            "speaker_name": "Idris",
            "advisor_role": "independent_critic",
            "content": "The evidence does not support that conclusion.",
            "created_at": "2026-09-08T00:00:00+00:00",
        },
    )
    queued = send(
        client,
        conversation_id,
        key="reply-to-idris",
        content="Which evidence would change your view?",
        reply_to=critic["id"],
    ).json()
    execute(store, tenant, queued["id"])
    assert calls[0]["role"] == "market_analyst"
    reply = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"][-1]
    assert reply["speaker_id"] == "idris" and reply["reply_to"] == queued["message_id"]
    assert reply["relationship"] == "answer"
    assert "planner_conclusion" in reply and reply["planner_conclusion"] is False


def test_real_postgres_conversation_idempotency_sequences_and_restart_persistence():
    from sqlalchemy import delete
    from packages.fixtures import synthetic_farm
    from services.api.conversation_store import (
        conversation_events,
        conversation_messages,
        conversation_requests,
        conversations,
    )
    from services.api.store import farms, now, tenants

    store = Store()
    assert store.engine.dialect.name == "postgresql"
    tenant, _ = store.new_session()
    store.save_farm(tenant, synthetic_farm().model_dump(mode="json"))
    persistence = ConversationStore(store)
    try:
        def create_row(index):
            payload = {
                "id": f"conversation-pg-{secrets.token_hex(12)}",
                "status": "OPEN",
                "advisor_id": "mei",
                "advisor_role": "production_analyst",
                "snapshot_ref": {"hash": "frozen"},
                "created_at": now(),
                "updated_at": now(),
                "execution_mode": "test",
                "caller": index,
            }
            return persistence.create_conversation(
                tenant, "postgres-conversation-key", "same-body", payload
            )

        with ThreadPoolExecutor(max_workers=6) as pool:
            created = list(pool.map(create_row, range(6)))
        ids = {row[0]["id"] for row in created}
        assert len(ids) == 1 and sum(row[1] for row in created) == 1
        conversation_id = ids.pop()

        def create_request(index):
            request_id = f"conversation-request-pg-{secrets.token_hex(10)}"
            message_id = f"conversation-message-pg-{secrets.token_hex(10)}"
            return persistence.create_request(
                tenant,
                conversation_id,
                "postgres-message-key",
                "same-message-body",
                {
                    "id": request_id,
                    "conversation_id": conversation_id,
                    "status": "QUEUED",
                    "question": "same",
                    "created_at": now(),
                },
                {
                    "id": message_id,
                    "speaker": "user",
                    "content": "same",
                    "created_at": now(),
                },
            )

        with ThreadPoolExecutor(max_workers=6) as pool:
            queued = list(pool.map(create_request, range(6)))
        request_ids = {row[0]["id"] for row in queued}
        assert len(request_ids) == 1 and sum(row[2] for row in queued) == 1

        def append(index):
            return persistence.append_message(
                tenant,
                conversation_id,
                {
                    "id": f"concurrent-message-{secrets.token_hex(12)}",
                    "speaker": "system",
                    "content": str(index),
                    "created_at": now(),
                },
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            appended = list(pool.map(append, range(8)))
        assert sorted(row["sequence"] for row in appended) == list(range(2, 10))

        restarted = Store()
        try:
            restored = ConversationStore(restarted)
            assert restored.get_conversation(tenant, conversation_id)["snapshot_ref"] == {
                "hash": "frozen"
            }
            assert len(restored.list_messages(tenant, conversation_id)) == 9
            assert restored.get_request(tenant, request_ids.pop())["status"] == "QUEUED"
        finally:
            restarted.engine.dispose()
    finally:
        with store.engine.begin() as connection:
            connection.execute(
                delete(conversation_events).where(conversation_events.c.tenant_id == tenant)
            )
            connection.execute(
                delete(conversation_requests).where(
                    conversation_requests.c.tenant_id == tenant
                )
            )
            connection.execute(
                delete(conversation_messages).where(
                    conversation_messages.c.tenant_id == tenant
                )
            )
            connection.execute(
                delete(conversations).where(conversations.c.tenant_id == tenant)
            )
            connection.execute(delete(farms).where(farms.c.tenant_id == tenant))
            connection.execute(delete(tenants).where(tenants.c.id == tenant))
        store.engine.dispose()


@pytest.mark.parametrize("fail_initial", [False, True])
def test_deployed_trial_runner_dry_contract_stays_within_aggregate_call_limit(
    env, monkeypatch, tmp_path, fail_initial
):
    import scripts.deepseek_conversation_trial as trial
    from services.api.scenarios import execute_scenario, pending_scenarios

    client, store, tenant = env
    calls = []
    initial_failures = (
        [
            DeepSeekResponseError(
                "DeepSeek structured output failed local validation"
            )
            for _ in range(2)
        ]
        if fail_initial
        else None
    )
    gateway_factory(monkeypatch, calls, responses=initial_failures)
    monkeypatch.setattr("services.api.scenarios.plan", minimal_three_policy_plan)

    class DryClient:
        def __init__(self, *_, **__):
            self.cookies = client.cookies

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def post(self, path, **kwargs):
            return client.post(path, **kwargs)

        def get(self, path, **kwargs):
            if path.startswith("/api/v1/scenarios/"):
                for scenario_tenant, scenario_id in pending_scenarios(store):
                    execute_scenario(store, scenario_tenant, scenario_id)
            if path.startswith("/api/v1/conversations/"):
                persistence = ConversationStore(store)
                for request_tenant, request_id in persistence.pending():
                    execute_conversation_job(store, request_tenant, request_id)
            return client.get(path, **kwargs)

    monkeypatch.setattr(trial.httpx, "Client", DryClient)
    state_path = tmp_path / "private-trial-state.json"
    if fail_initial:
        with pytest.raises(RuntimeError, match="direct advisor exchange did not complete"):
            trial.run("https://dry.invalid", timeout=5, state_path=state_path)
        assert len(calls) == 2
        result = trial.run(
            "https://dry.invalid",
            timeout=5,
            state_path=state_path,
            retry_failed=True,
        )
    else:
        result = trial.run("https://dry.invalid", timeout=5, state_path=state_path)
    expected_calls = 12 if fail_initial else 10
    assert result["status"] == "PASS"
    assert result["actual_inference_requests"] == expected_calls
    assert result["preserved_failed_requests"] == (1 if fail_initial else 0)
    assert result["favourable_recommendation_required"] is False
    assert len(calls) == expected_calls
    assert state_path.stat().st_mode & 0o777 == 0o600
    resumed = trial.run(
        "https://dry.invalid",
        timeout=5,
        state_path=state_path,
        retry_failed=fail_initial,
    )
    assert resumed["status"] == "PASS"
    assert resumed["actual_inference_requests"] == expected_calls
    assert len(calls) == expected_calls


def test_advisor_schema_and_prompt_share_every_response_boundary():
    base = {
        "content": "x" * 400,
        "evidence_refs": ["P01"],
        "tool_refs": ["a", "b", "c"],
        "fact_refs": ["d", "e", "f"],
        "highlight_refs": ["bed:a"],
        "relationship": "answer",
        "proposed_actions": [
            {"control": "cash_percent", "target_id": None, "value": 100, "unit": "percent"}
        ],
    }
    AdvisorReply.model_validate(base)
    for field, extra in (
        ("content", "x"),
        ("evidence_refs", "P02"),
        ("tool_refs", "overflow"),
        ("fact_refs", "overflow"),
        ("highlight_refs", "bed:b"),
        ("proposed_actions", base["proposed_actions"][0]),
    ):
        invalid = deepcopy(base)
        if field == "content":
            invalid[field] += extra
        else:
            invalid[field].append(extra)
        with pytest.raises(ValidationError):
            AdvisorReply.model_validate(invalid)


def test_forecast_harvest_mass_is_an_exact_typed_batch_fact():
    from packages.fixtures import synthetic_farm
    from packages.models import forecast
    from packages.ai_contracts import typed_reference_catalog

    farm = synthetic_farm()
    calculation = {"strategies": [], "forecast": forecast(farm)}
    snapshot = farm.model_dump(mode="json")
    refs = _tool_results(snapshot, planning=calculation)
    first = calculation["forecast"]["harvest"][0]
    key = f"forecast:batch_{first['batch_id']}.marketable_kg"
    assert refs[key] == first["marketable_kg"]
    assert f"forecast:batch_{first['batch_id']}.expected_kg" not in refs
    typed = typed_reference_catalog(refs, snapshot_hash="frozen-hash")
    assert typed[key] == {
        "reference": key,
        "kind": "quantity",
        "value": first["marketable_kg"],
        "unit": "kg",
        "entity": {"type": "batch", "id": first["batch_id"]},
        "period": None,
        "context": "forecast",
        "snapshot_hash": "frozen-hash",
        "verification": "code_rendered_frozen_value",
    }
    date_fact = typed[f"forecast:batch_{first['batch_id']}.harvest_date"]
    assert date_fact["period"] == {"kind": "harvest_date", "value": first["harvest_date"]}


def test_later_advisor_receives_bounded_validation_errors_and_cannot_use_rejected_turn(env):
    client, store, tenant = env
    conversation_id = create(client, key="error-projection-conversation").json()["id"]
    persistence = ConversationStore(store)
    rejected = persistence.append_message(
        tenant,
        conversation_id,
        {
            "id": "rejected-advisor-turn",
            "speaker": "advisor",
            "speaker_id": "ravi",
            "content": "This assertion is unsupported.",
            "evidence_refs": [],
            "tool_refs": ["unknown"],
            "fact_refs": [],
            "validation_status": "unsupported",
            "evidence_status": "unsupported",
            "validation_issues": [
                {"code": "unknown_tool_reference", "message": "Unknown frozen tool reference"}
            ],
            "relationship": "challenge",
            "created_at": "2026-09-11T00:00:00+00:00",
        },
    )
    conversation = persistence.get_conversation(tenant, conversation_id)
    request_payload = {
        "mode": "direct",
        "question": "Review the prior claim.",
        "reply_to": rejected["id"],
    }
    messages = _provider_messages(
        persistence, tenant, conversation, request_payload,
        "production_analyst", rejected["id"], False,
    )
    context = json.loads(messages[1]["content"])
    prior = next(item for item in context["prior_turns"] if item["id"] == rejected["id"])
    assert prior["validation_issues"] == [
        {"code": "unknown_tool_reference", "message": "Unknown frozen tool reference"}
    ]
    assert prior["eligible_as_evidence"] is False


def test_legacy_message_replay_decodes_without_new_contract_fields(env):
    client, store, tenant = env
    conversation_id = create(client, key="legacy-replay-conversation").json()["id"]
    ConversationStore(store).append_message(
        tenant,
        conversation_id,
        {
            "id": "legacy-advisor-message",
            "speaker": "advisor",
            "speaker_id": "mei",
            "content": "Archived qualitative interpretation.",
            "validation_status": "references_verified",
            "tool_refs": ["forecast:lead_times"],
            "created_at": "2026-09-10T00:00:00+00:00",
        },
    )
    replay = client.get(f"/api/v1/conversations/{conversation_id}/replay").json()
    assert replay["messages"][-1]["content"] == "Archived qualitative interpretation."
    assert replay["inference_origin"] == "stored_actual_replay"
    assert replay["inference_triggered"] is False


def test_cancelled_conversation_request_is_terminal_and_never_calls_provider(env, monkeypatch):
    client, store, tenant = env
    calls=[]
    gateway_factory(monkeypatch,calls)
    conversation_id=create(client,key="cancel-conversation").json()["id"]
    queued=send(client,conversation_id,key="cancel-message").json()
    path=f"/api/v1/conversations/{conversation_id}/requests/{queued['id']}/cancel"
    cancelled=client.post(path).json()
    assert cancelled == {"id":queued["id"],"status":"CANCELLED","cancelled":True}
    assert client.post(path).json() == {"id":queued["id"],"status":"CANCELLED","cancelled":False}
    execute(store,tenant,queued["id"])
    assert ConversationStore(store).get_request(tenant,queued["id"])["status"] == "CANCELLED"
    assert calls == []
    public=client.get(f"/api/v1/conversations/{conversation_id}").json()
    assert public["model_call_status"] == "cancelled"
    assert public["decision_influence"] == "none_cancelled"
