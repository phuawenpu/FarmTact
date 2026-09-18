from copy import deepcopy
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update

from packages.agents import ADVISORS
from services.api.app import create_app
from services.api.conversation_store import ConversationStore, conversations
from services.api.conversations import _provider_messages
from services.api.planning_sessions import SESSIONS, VERSIONS, public_session
from services.api.store import Store


@pytest.fixture
def env(monkeypatch):
    store = Store("sqlite://")
    app = create_app(store, start_worker=False)
    with TestClient(app) as client:
        assert client.get("/api/v1/bootstrap").status_code == 200
        tenant = store.authenticate(client.cookies.get("farmtact_session"))
        monkeypatch.setattr(store, "reserve_calls", lambda *_a, **_k: pytest.fail("read or create reserved provider calls"))
        monkeypatch.setattr(
            "services.api.conversations.DeepSeekGateway.from_config",
            staticmethod(lambda *_a, **_k: pytest.fail("read or create instantiated provider")),
        )
        yield client, store, tenant


def install_session(store, tenant, session_id="v22-session", result_id="v22-result", *, reviews=None):
    farm = deepcopy(store.latest_farm(tenant))
    result = {
        "id": result_id,
        "input_snapshot": farm,
        "strategies": [{
            "id": "balanced-v22", "name": "Balanced", "status": "FEASIBLE",
            "metrics": {"fill_rate": .8, "margin_sgd": 120}, "allocations": [], "violations": [],
        }],
        "forecast": {"demand": [], "harvest": []},
        "assumptions": {},
    }
    session = {
        "id": session_id, "status": "COMPLETED", "result_id": result_id,
        "farm": farm, "review": {"status": "ready", "findings": []},
        "review_history": deepcopy(reviews or []), "history": [], "revision": 3,
    }
    with store.connection(write=True) as connection:
        connection.execute(SESSIONS.insert().values(id=session_id, tenant_id=tenant, status="COMPLETED", payload=session))
        connection.execute(VERSIONS.insert().values(id=result_id, tenant_id=tenant, session_id=session_id, payload=result))
    return session, result


def create(client, session_id, key, *, result_id=None, expected_result_id=None, advisor="mei"):
    body = {"advisor": advisor, "snapshot_kind": "planning", "snapshot_id": session_id}
    if result_id is not None:
        body["council_review_result_id"] = result_id
    if expected_result_id is not None:
        body["expected_result_id"] = expected_result_id
    return client.post("/api/v1/conversations", json=body, headers={"Idempotency-Key": key})


def test_filtered_listing_is_tenant_scoped_result_exact_and_paginated(env):
    client, store, tenant = env
    session, _ = install_session(store, tenant)
    first = create(client, session["id"], "v22-list-one")
    second = create(client, session["id"], "v22-list-two", advisor="ravi")
    assert first.status_code == second.status_code == 201

    listed = client.get("/api/v1/conversations", params={"planning_session_id": session["id"], "result_id": session["result_id"]}).json()["conversations"]
    assert {row["id"] for row in listed} == {first.json()["id"], second.json()["id"]}
    assert client.get("/api/v1/conversations", params={"result_id": session["result_id"]}).status_code == 422

    with store.connection(write=True) as connection:
        saved = ConversationStore(store).get_conversation(tenant, first.json()["id"])
        saved["updated_at"] = "2026-01-01T00:00:00+00:00"
        connection.execute(update(conversations).where(conversations.c.id == saved["id"]).values(payload=saved))
    page = client.get("/api/v1/conversations", params={"planning_session_id": session["id"], "limit": 1}).json()["conversations"]
    assert [row["id"] for row in page] == [second.json()["id"]]
    older = client.get("/api/v1/conversations", params={"planning_session_id": session["id"], "before": page[0]["updated_at"]}).json()["conversations"]
    assert [row["id"] for row in older] == [first.json()["id"]]

    other_app = create_app(store, start_worker=False)
    with TestClient(other_app) as other:
        assert other.get("/api/v1/bootstrap").status_code == 200
        hidden = other.get("/api/v1/conversations", params={"planning_session_id": session["id"]})
        assert hidden.status_code == 404


def test_review_context_freezes_current_result_and_latest_matching_history(env):
    client, store, tenant = env
    reviews = [
        {"job_id": "review-old", "result_id": "v22-result", "review": {"status": "partial", "findings": [{"role": "production_analyst", "rationale": "old"}]}},
        {"job_id": "review-latest", "result_id": "v22-result", "review": {"status": "ready", "findings": [{"role": "production_analyst", "status": "supported", "tradeoff": "More labour", "rationale": "latest", "proposed_strategy_id": "balanced-v22", "rendered_facts": ["80%"]}]}},
    ]
    session, _ = install_session(store, tenant, reviews=reviews)
    response = create(client, session["id"], "v22-review", result_id=session["result_id"])
    assert response.status_code == 201, response.text
    saved = ConversationStore(store).get_conversation(tenant, response.json()["id"])
    assert saved["snapshot_ref"]["id"] == f"{session['id']}:{session['result_id']}"
    assert saved["council_review_result_id"] == session["result_id"]
    assert saved["_council_review"] == {
        "result_id": session["result_id"], "job_id": "review-latest", "status": "ready",
        "findings": [{
            "role": "production_analyst", "status": "supported", "tradeoff": "More labour",
            "rationale": "latest", "proposed_strategy_id": "balanced-v22",
            "rendered_interpretation": None, "rendered_facts": ["80%"], "rejection_reasons": None,
        }],
    }
    messages = _provider_messages(ConversationStore(store), tenant, saved, {"mode": "direct", "question": "Explain", "reply_to": None}, "production_analyst", "queued", False)
    provider_review = json.loads(messages[1]["content"])["recorded_council_review"]
    assert provider_review["result_id"] == saved["_council_review"]["result_id"]
    assert provider_review["job_id"] == "review-latest"
    assert provider_review["findings"][0]["rationale"] == "latest"
    assert provider_review["findings"][0]["rendered_facts"] == ["[bounded]"]

    public = public_session(store, tenant, session)
    assert public["review"]["result_id"] == session["result_id"]
    assert public["review"]["job_id"] == "review-latest"


def test_review_context_rejects_stale_absent_and_foreign_results(env):
    client, store, tenant = env
    session, _ = install_session(store, tenant)
    stale = create(client, session["id"], "v22-stale", result_id="older-result")
    assert stale.status_code == 409
    assert stale.json()["detail"] == "Council review belongs to a different result"
    absent = create(client, session["id"], "v22-absent", result_id=session["result_id"])
    assert absent.status_code == 409
    assert absent.json()["detail"] == "Complete a Council review for this result first"

    other_app = create_app(store, start_worker=False)
    with TestClient(other_app) as other:
        assert other.get("/api/v1/bootstrap").status_code == 200
        foreign = create(other, session["id"], "v22-foreign", result_id=session["result_id"])
        assert foreign.status_code == 404


def test_public_role_names_keep_internal_ids_and_roles(env):
    client, store, tenant = env
    expected = {
        "ravi": ("Demand Planner", "demand_analyst"), "mei": ("Crop Planner", "production_analyst"),
        "hana": ("Weather & Risk", "weather_analyst"), "idris": ("Market Analyst", "market_analyst"),
        "ben": ("Resource Planner", "profit_analyst"), "lina": ("Supply Planner", "supply_chain_analyst"),
        "asha": ("Chair", "planning_chair"),
    }
    roster = client.get("/api/v1/conversations/advisors").json()["advisors"]
    assert {row["id"]: (row["name"], row["role"]) for row in roster} == expected
    assert {key: (row["name"], row["role"]) for key, row in ADVISORS.items()} == expected

    session, _ = install_session(store, tenant, session_id="role-session", result_id="role-result")
    created = create(client, session["id"], "v22-role", advisor="ravi")
    saved = ConversationStore(store).get_conversation(tenant, created.json()["id"])
    assert saved["advisor_id"] == "ravi"
    assert saved["advisor_role"] == "demand_analyst"
    public = client.get(f"/api/v1/conversations/{saved['id']}").json()
    assert public["advisor"] == ADVISORS["ravi"]


def test_expected_result_id_accepts_current_and_rejects_changed_result(env):
    client, store, tenant = env
    session, _ = install_session(store, tenant, session_id="expected-session", result_id="expected-current")
    accepted = create(
        client, session["id"], "expected-current-key",
        expected_result_id=session["result_id"],
    )
    assert accepted.status_code == 201, accepted.text
    saved = ConversationStore(store).get_conversation(tenant, accepted.json()["id"])
    assert saved["snapshot_ref"]["id"] == "expected-session:expected-current"

    changed = create(
        client, session["id"], "expected-stale-key",
        expected_result_id="result-visible-before-recalculation",
    )
    assert changed.status_code == 409
    assert changed.json()["detail"] == "The planning result changed; reload before starting this discussion"
    assert ConversationStore(store).get_conversation_by_key(tenant, "expected-stale-key") is None


def test_composite_cursor_covers_equal_updated_timestamps_without_skips(env):
    client, store, tenant = env
    session, _ = install_session(store, tenant, session_id="cursor-session", result_id="cursor-result")
    created = [create(client, session["id"], f"cursor-{index}") for index in range(3)]
    assert all(response.status_code == 201 for response in created)
    ids = {response.json()["id"] for response in created}
    same_time = "2026-09-18T08:00:00+00:00"
    persistence = ConversationStore(store)
    payloads = [persistence.get_conversation(tenant, conversation_id) for conversation_id in ids]
    with store.connection(write=True) as connection:
        for payload in payloads:
            payload["updated_at"] = same_time
            connection.execute(update(conversations).where(conversations.c.id == payload["id"]).values(payload=payload))

    seen = []
    cursor = None
    for _ in range(3):
        params = {"planning_session_id": session["id"], "limit": 1}
        if cursor is not None:
            params["before"] = cursor
        response = client.get("/api/v1/conversations", params=params)
        assert response.status_code == 200
        page = response.json()
        assert len(page["conversations"]) == 1
        seen.append(page["conversations"][0]["id"])
        cursor = page["next_before"]
        assert cursor == f"{same_time}|{seen[-1]}"
    assert set(seen) == ids
    assert len(seen) == len(set(seen))
    final = client.get("/api/v1/conversations", params={
        "planning_session_id": session["id"], "limit": 1, "before": cursor,
    }).json()
    assert final["conversations"] == []
    assert final["next_before"] is None


def test_snapshot_freeze_runs_inside_tenant_transaction(env, monkeypatch):
    client, store, tenant = env
    session, _ = install_session(store, tenant, session_id="locked-session", result_id="locked-result")
    import services.api.conversations as conversation_api

    original = conversation_api._freeze_snapshot
    observed = []

    def asserting_freeze(current_store, current_tenant, body):
        connection = current_store._transaction.get()
        observed.append((connection is not None, current_tenant))
        return original(current_store, current_tenant, body)

    monkeypatch.setattr(conversation_api, "_freeze_snapshot", asserting_freeze)
    response = create(
        client, session["id"], "transaction-guard",
        expected_result_id=session["result_id"],
    )
    assert response.status_code == 201, response.text
    assert observed == [(True, tenant)]
