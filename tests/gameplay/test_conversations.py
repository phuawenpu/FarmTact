from __future__ import annotations

from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import json
import secrets
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from packages.contracts import content_hash
from runtime.deepseek_gateway import DeepSeekGatewayError, DeepSeekResponseError, SafeAudit, Usage
from services.api.app import create_app
from services.api.conversation_store import ConversationStore
from services.api.conversations import ADVISORS, AdvisorReply, execute_conversation_job
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
    for index, name in enumerate(("Lean", "Balanced", "Resilient")):
        strategies.append(
            {
                "id": f"{name.lower()}-fixture",
                "name": name,
                "status": "FEASIBLE",
                "metrics": {"margin_sgd": 500.0 - index, "fill_rate": 0.9},
                "violations": [],
                "allocations": [],
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
            response = {
                "content": f"{ADVISORS[next(key for key, row in ADVISORS.items() if row['role'] == role)]['name']} reviewed the frozen comparison.",
                "evidence_refs": [],
                "tool_refs": ["farm:resources.cash_sgd"],
                "highlight_refs": ["bed:bed-01"],
                "relationship": "answer",
                "proposed_actions": [],
            }
        data = output_model.model_validate(response)
        usage = Usage(prompt_tokens=10, completion_tokens=5, total_tokens=15)
        audit = SafeAudit(
            provider="deepseek",
            requested_model="deepseek-v4-flash",
            returned_model="deepseek-v4-flash",
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
            model="deepseek-v4-flash",
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


def test_six_original_advisors_and_frozen_create_idempotency(env):
    client, store, tenant = env
    roster = client.get("/api/v1/conversations/advisors").json()["advisors"]
    assert [(row["id"], row["name"]) for row in roster] == [
        ("mei", "Mei"),
        ("ravi", "Ravi"),
        ("hana", "Hana"),
        ("ben", "Ben"),
        ("asha", "Asha"),
        ("idris", "Idris"),
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
    assert public["tool_results"]["source:D04.summary"]


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
    assert reply["interpretation_status"] == "unverified_advisor_interpretation"
    assert transcript["tool_results"]["farm:resources.cash_sgd"]
    assert transcript["transcript_mode"] == "recorded"
    monkeypatch.setattr(
        store, "reserve_calls", lambda *_: pytest.fail("GET/replay reserved inference")
    )
    assert client.get(f"/api/v1/conversations/{conversation_id}").status_code == 200
    replay = client.get(f"/api/v1/conversations/{conversation_id}/replay").json()
    assert replay["transcript_mode"] == "replay"
    assert replay["inference_origin"] == "stored_messages"
    assert replay["inference_triggered"] is False
    assert len(calls) == 1


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


def test_council_has_eight_bounded_turns_all_with_prior_claims_and_critic_conclusion(
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
        "crop_scientist",
        "supply_weather_scout",
        "resources_margin_analyst",
        "planning_chair",
        "independent_critic",
        "planning_chair",
        "independent_critic",
    ]
    assert len(calls) == 8
    for index, call in enumerate(calls[1:], start=1):
        context = json.loads(call["messages"][1]["content"])
        earlier = [turn for turn in context["prior_turns"] if turn["speaker"] == "advisor"]
        assert len(earlier) == index
    assert advisor_messages[-1]["critic_conclusion"] is True
    assert advisor_messages[-1]["reply_to"] == advisor_messages[-2]["id"]


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
    reply = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"][-1]
    assert reply["validation_status"] == "unsupported"
    assert "Advisor prose contains a quantitative or temporal claim; exact values render only from tool references" in reply[
        "validation_errors"
    ]
    assert reply["proposed_actions"][0]["status"] == "blocked_unsupported"
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
                "tool_refs": ["farm:resources.labour_hours_per_week"],
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
    assert reply["validation_scope"] == "reference_membership_and_supported_controls"


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
    assert (
        "Advisor prose contains a quantitative or temporal claim; exact values render only from tool references"
        in reply["validation_errors"]
    )


def test_council_preflight_counts_user_and_all_eight_advisor_turns(env):
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
    assert "safe failure" in request["error"]
    retry = send(client, failed_id, key="failed-message").json()
    execute(store, tenant, retry["id"])
    assert len(calls) == 1


def test_one_direct_format_repair_and_second_invalid_response_stops(env, monkeypatch):
    client, store, tenant = env
    calls = []
    schema_error = DeepSeekResponseError(
        "DeepSeek structured output failed local validation"
    )
    gateway_factory(monkeypatch, calls, responses=[schema_error, schema_error])
    conversation_id = create(client).json()["id"]
    queued = send(client, conversation_id).json()
    execute(store, tenant, queued["id"])
    request = ConversationStore(store).get_request(tenant, queued["id"])
    assert request["status"] == "FAILED"
    assert request["repair_attempts"] == 1
    assert len(calls) == 2


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
    assert calls[0]["role"] == "independent_critic"
    reply = client.get(f"/api/v1/conversations/{conversation_id}").json()["messages"][-1]
    assert reply["speaker_id"] == "idris" and reply["reply_to"] == queued["message_id"]


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
                "advisor_role": "crop_scientist",
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


def test_deployed_trial_runner_dry_contract_uses_eleven_mocked_calls(
    env, monkeypatch, tmp_path
):
    import scripts.deepseek_conversation_trial as trial
    from services.api.scenarios import execute_scenario, pending_scenarios

    client, store, tenant = env
    calls = []
    gateway_factory(monkeypatch, calls)
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
    result = trial.run("https://dry.invalid", timeout=5, state_path=state_path)
    assert result["status"] == "PASS"
    assert result["actual_inference_requests"] == 11
    assert result["favourable_recommendation_required"] is False
    assert len(calls) == 11
    assert state_path.stat().st_mode & 0o777 == 0o600
    resumed = trial.run("https://dry.invalid", timeout=5, state_path=state_path)
    assert resumed["status"] == "PASS"
    assert resumed["actual_inference_requests"] == 11
    assert len(calls) == 11
