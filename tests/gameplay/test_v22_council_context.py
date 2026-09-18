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


def create(client, session_id, key, *, result_id=None, advisor="mei"):
    body = {"advisor": advisor, "snapshot_kind": "planning", "snapshot_id": session_id}
    if result_id is not None:
        body["council_review_result_id"] = result_id
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
