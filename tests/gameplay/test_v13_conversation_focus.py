from copy import deepcopy
import json

import pytest
from fastapi.testclient import TestClient

from packages.contracts import content_hash
from services.api.app import create_app
from services.api.conversation_store import ConversationStore
from services.api.conversations import _provider_messages
from services.api.planning_sessions import SESSIONS, VERSIONS
from services.api.store import Store


@pytest.fixture
def env(monkeypatch):
    store = Store("sqlite://")
    app = create_app(store, start_worker=False)
    with TestClient(app) as client:
        assert client.get("/api/v1/bootstrap").status_code == 200
        tenant = store.authenticate(client.cookies.get("farmtact_session"))
        monkeypatch.setattr(
            store,
            "reserve_calls",
            lambda *_args, **_kwargs: pytest.fail(
                "conversation creation attempted a provider reservation"
            ),
        )
        monkeypatch.setattr(
            "services.api.conversations.DeepSeekGateway.from_config",
            staticmethod(
                lambda *_args, **_kwargs: pytest.fail(
                    "conversation creation attempted to instantiate a provider"
                )
            ),
        )
        yield client, store, tenant


def _install_planning_snapshot(store, tenant, *, session_id="planning-focus"):
    farm = deepcopy(store.latest_farm(tenant))
    result_id = f"{session_id}-result"
    strategy = {
        "id": "strategy-balanced-focus",
        "name": "Balanced",
        "status": "FEASIBLE",
        "description": "Balance coverage, cost and surplus.",
        "metrics": {"fill_rate": 0.92, "margin_sgd": 123.45},
        "violations": [],
        "allocations": [],
    }
    result = {
        "id": result_id,
        "input_snapshot": farm,
        "strategies": [strategy],
        "forecast": {"demand": [], "harvest": []},
        "assumptions": {},
    }
    session = {
        "id": session_id,
        "status": "COMPLETED",
        "result_id": result_id,
        "farm": farm,
    }
    with store.connection(write=True) as connection:
        connection.execute(
            SESSIONS.insert().values(
                id=session_id,
                tenant_id=tenant,
                status="COMPLETED",
                payload=session,
            )
        )
        connection.execute(
            VERSIONS.insert().values(
                id=result_id,
                tenant_id=tenant,
                session_id=session_id,
                payload=result,
            )
        )
    return session, result


def _create(client, body, key):
    return client.post(
        "/api/v1/conversations",
        json={"advisor": "mei", **body},
        headers={"Idempotency-Key": key},
    )


def _read(client, created):
    return client.get(f"/api/v1/conversations/{created.json()['id']}").json()


def test_b3_focus_is_frozen_trusted_and_selected_bed_compatible(env):
    client, store, tenant = env
    session, _ = _install_planning_snapshot(store, tenant)
    body = {
        "snapshot_kind": "planning",
        "snapshot_id": session["id"],
        "focus": {
            "card_id": "constraint-bed-07",
            "entity_kind": "grow_space",
            "entity_id": "bed-07",
        },
    }

    created = _create(client, body, "focus-b3")
    assert created.status_code == 201, created.text
    public = _read(client, created)

    assert public["selected_bed_id"] == "bed-07"
    assert public["focus"] == {
        "card_id": "constraint-bed-07",
        "entity_kind": "grow_space",
        "entity_id": "bed-07",
        "title": "Grow space B3",
        "source": "Frozen farm snapshot",
        "context": {
            "snapshot_kind": "planning",
            "snapshot_id": f"{session['id']}:{session['result_id']}",
            "snapshot_hash": public["snapshot_ref"]["hash"],
            "name": "B3",
            "area_m2": "20",
            "system": "sheltered_hydroponic",
            "batch_ids": ["batch-07"],
        },
    }
    saved = ConversationStore(store).get_conversation(tenant, public["id"])
    assert saved["focus"] == public["focus"]
    provider_messages = _provider_messages(
        ConversationStore(store),
        tenant,
        saved,
        {"mode": "direct", "question": "Why keep B3 free?", "reply_to": None},
        "production_analyst",
        "queued-user-message",
        False,
    )
    supplied_context = json.loads(provider_messages[1]["content"])
    assert supplied_context["focus"] == public["focus"]
    assert supplied_context["selected_bed_id"] == "bed-07"
    assert "bed:bed-07.area_m2" in supplied_context["typed_facts"]


def test_heavy_rainfall_focus_is_planning_bound_scenario_only(env):
    client, store, tenant = env
    session, _ = _install_planning_snapshot(store, tenant, session_id="rain-planning")
    body = {
        "snapshot_kind": "planning",
        "snapshot_id": session["id"],
        "focus": {
            "card_id": "scenario-heavy-rainfall",
            "entity_kind": "scenario",
            "entity_id": "synthetic-heavy-rainfall-v1",
        },
    }

    created = _create(client, body, "focus-rain")
    assert created.status_code == 201, created.text
    focus = _read(client, created)["focus"]
    assert focus["title"] == "Heavy rainfall"
    assert focus["source"] == "Frozen synthetic seasonal record"
    assert focus["context"]["provenance_label"] == "SIMULATION · SCENARIO ONLY"
    assert focus["context"]["simulation_only"] is True
    assert focus["context"]["observed_weather"] is False
    assert focus["context"]["snapshot_kind"] == "planning"

    outside_planning = _create(
        client,
        {"focus": body["focus"]},
        "focus-rain-without-planning",
    )
    assert outside_planning.status_code == 422
    assert outside_planning.json()["detail"] == "Focused entity is outside the frozen snapshot"


def test_focus_rejects_missing_unknown_mismatched_and_client_claimed_entities(env):
    client, store, tenant = env
    session, _ = _install_planning_snapshot(store, tenant, session_id="focus-rejection")

    mismatched_card = _create(
        client,
        {
            "snapshot_kind": "planning",
            "snapshot_id": session["id"],
            "focus": {
                "card_id": "constraint-bed-08",
                "entity_kind": "grow_space",
                "entity_id": "bed-07",
            },
        },
        "focus-card-coordinate-mismatch",
    )
    assert mismatched_card.status_code == 422
    assert mismatched_card.json()["detail"] == "Focused card does not match the frozen entity"

    assert _create(
        client,
        {
            "focus": {
                "card_id": "missing-bed",
                "entity_kind": "grow_space",
                "entity_id": "bed-99",
            }
        },
        "focus-missing",
    ).status_code == 422
    assert _create(
        client,
        {
            "focus": {
                "card_id": "unknown-kind",
                "entity_kind": "warehouse",
                "entity_id": "one",
            }
        },
        "focus-unknown",
    ).status_code == 422
    assert _create(
        client,
        {
            "selected_bed_id": "bed-08",
            "focus": {
                "card_id": "mismatched-bed",
                "entity_kind": "grow_space",
                "entity_id": "bed-07",
            },
        },
        "focus-mismatch",
    ).status_code == 422
    claimed = _create(
        client,
        {
            "focus": {
                "card_id": "claimed-title",
                "entity_kind": "grow_space",
                "entity_id": "bed-07",
                "title": "Attacker-controlled title",
                "source": "Attacker-controlled source",
            }
        },
        "focus-client-claims",
    )
    assert claimed.status_code == 422
    assert claimed.json()["detail"] == "Invalid request schema"


def test_focus_idempotency_includes_card_and_entity_coordinates(env):
    client, _, _ = env
    body = {
        "focus": {
            "card_id": "crop-batch-batch-01",
            "entity_kind": "batch",
            "entity_id": "batch-01",
        }
    }
    first = _create(client, body, "focus-idempotency")
    assert first.status_code == 201, first.text
    replay = _create(client, body, "focus-idempotency")
    assert replay.json() == {
        "id": first.json()["id"],
        "status": "OPEN",
        "reused": True,
    }
    changed = deepcopy(body)
    changed["focus"]["entity_id"] = "batch-02"
    conflict = _create(client, changed, "focus-idempotency")
    assert conflict.status_code == 409


def test_selected_bed_only_callers_remain_compatible(env):
    client, _, _ = env
    created = _create(
        client,
        {"selected_bed_id": "bed-07"},
        "legacy-selected-bed",
    )
    assert created.status_code == 201, created.text
    public = _read(client, created)
    assert public["selected_bed_id"] == "bed-07"
    assert public["focus"] is None


def test_focus_entity_is_tenant_scoped_before_resolution(env):
    first_client, store, first_tenant = env
    session, _ = _install_planning_snapshot(
        store, first_tenant, session_id="private-planning-focus"
    )

    app = create_app(store, start_worker=False)
    with TestClient(app) as second_client:
        assert second_client.get("/api/v1/bootstrap").status_code == 200
        response = _create(
            second_client,
            {
                "snapshot_kind": "planning",
                "snapshot_id": session["id"],
                "focus": {
                    "card_id": "foreign-b3",
                    "entity_kind": "grow_space",
                    "entity_id": "bed-07",
                },
            },
            "foreign-focus",
        )
    assert response.status_code == 404
    assert response.json()["detail"] == "Planning session not found"
    assert first_client.get("/api/v1/conversations").json()["conversations"] == []


@pytest.mark.parametrize(
    ("entity_kind", "entity_id", "expected_source"),
    [
        ("order", "order-0-0", "Frozen farm snapshot"),
        ("crop", "caixin", "Frozen farm snapshot"),
        ("batch", "batch-01", "Frozen farm snapshot"),
        ("agent", "mei", "FarmTact council roster"),
        ("role", "production_analyst", "FarmTact council roster"),
        ("evidence", "P01", "Frozen evidence register record"),
    ],
)
def test_available_snapshot_entity_kinds_resolve_from_server_data(
    env, entity_kind, entity_id, expected_source
):
    client, _, _ = env
    created = _create(
        client,
        {
            "focus": {
                "card_id": ({
                    "order": "order-order-0-0",
                    "crop": "crop-caixin",
                    "batch": "crop-batch-batch-01",
                    "agent": "agent-mei",
                    "role": "agent-mei",
                    "evidence": "evidence-P01",
                })[entity_kind],
                "entity_kind": entity_kind,
                "entity_id": entity_id,
            }
        },
        f"focus-kind-{entity_kind}",
    )
    assert created.status_code == 201, created.text
    focus = _read(client, created)["focus"]
    assert focus["entity_id"] == entity_id
    assert focus["source"] == expected_source
    assert focus["title"]
    assert focus["context"]["snapshot_hash"]


def test_strategy_requires_and_uses_the_frozen_planning_result(env):
    client, store, tenant = env
    session, result = _install_planning_snapshot(
        store, tenant, session_id="strategy-planning"
    )
    strategy = result["strategies"][0]
    created = _create(
        client,
        {
            "snapshot_kind": "planning",
            "snapshot_id": session["id"],
            "focus": {
                "card_id": f"strategy-{strategy['id']}",
                "entity_kind": "strategy",
                "entity_id": strategy["id"],
            },
        },
        "focus-strategy",
    )
    assert created.status_code == 201, created.text
    focus = _read(client, created)["focus"]
    assert focus["title"] == "Balanced strategy"
    assert focus["context"]["metrics"] == strategy["metrics"]
    assert focus["context"]["result_hash"] == content_hash(result)

    unavailable = _create(
        client,
        {
            "focus": {
                "card_id": f"strategy-{strategy['id']}",
                "entity_kind": "strategy",
                "entity_id": strategy["id"],
            }
        },
        "focus-strategy-unavailable",
    )
    assert unavailable.status_code == 422


def test_task_focus_fails_closed_when_tasks_are_not_in_frozen_result(env):
    client, _, _ = env
    response = _create(
        client,
        {
            "focus": {
                "card_id": "action-task-not-frozen",
                "entity_kind": "task",
                "entity_id": "task-not-frozen",
            }
        },
        "focus-task-unavailable",
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "Focused entity is outside the frozen snapshot"
