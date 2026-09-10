"""Independent adversarial checks for the scripted council interpreter.

These focus on mixed-initiative safety: a bounded interpreter must clarify
negation and multiple targets rather than turn them into a plausible edit.
"""
import uuid

import pytest
from fastapi.testclient import TestClient

from services.api.app import create_app
from services.api.store import Store


@pytest.fixture
def client():
    store = Store("sqlite://")
    with TestClient(create_app(store, start_worker=False)) as api:
        api.get("/api/v1/bootstrap")
        yield api


def create(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/council-research",
        json={},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 201
    return response.json()


def say(client: TestClient, session: dict, text: str) -> dict:
    response = client.post(
        f"/api/v1/council-research/{session['id']}/actions",
        json={"action": "say", "revision": session["revision"], "text": text},
        headers={"Idempotency-Key": str(uuid.uuid4())},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize(
    "utterance",
    [
        "Do not reserve Bed 4.",
        "Don't keep Bed 4 free.",
    ],
)
def test_negated_reservation_never_becomes_a_proposal(client, utterance):
    session = say(client, create(client), utterance)
    assert session["proposal"] is None
    assert session["events"][-1]["type"] == "clarification"


def test_two_explicit_beds_require_clarification(client):
    session = say(client, create(client), "Keep Bed 4 and Bed 5 free.")
    assert session["proposal"] is None
    assert session["events"][-1]["type"] == "clarification"


@pytest.mark.parametrize(
    "utterance",
    [
        "The additional order is not confirmed.",
        "The customer hasn't confirmed the additional order.",
    ],
)
def test_negative_confirmation_is_not_interpreted_as_confirmed(client, utterance):
    session = say(client, create(client), utterance)
    assert session["proposal"]["operation"] == "order_status"
    assert session["proposal"]["confirmed"] is False


def test_opening_a_challenge_invalidates_a_prior_simulated_choice(client):
    """Unit-level invariant independent of solver runtime."""
    from services.api.council_research import Action, challenge, new_session, NewSession

    session = new_session(NewSession())
    session["chosen"] = {
        "version": 1,
        "actor": "research-participant",
        "simulation_only": True,
    }
    challenge(
        session,
        Action(action="challenge", revision=session["revision"], text="Show why this is safe"),
    )
    assert session["chosen"] is None
    assert session["challenge"]["status"] == "unresolved"
