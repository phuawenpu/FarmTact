"""Discussion evidence links a reviewed draft without granting mutation authority."""
from copy import deepcopy
import pytest
from tests.gameplay.test_farm_workflow import setup
from services.api import farm_workflow
from services.api.conversation_store import ConversationStore


def discussion(store, tenant, *, snapshot="session-1:result-1", validation="references_verified"):
    persistence = ConversationStore(store)
    persistence.create_conversation(tenant, "discussion", "fixture", {
        "id": "discussion-1", "status": "OPEN",
        "snapshot_ref": {"kind": "planning", "id": snapshot, "hash": "fixture-hash"}})
    return persistence.append_message(tenant, "discussion-1", {
        "id": "message-1", "speaker": "advisor", "content": "Review a labour constraint.",
        "validation_status": validation, "proposed_actions": [
            {"control": "labour_percent", "value": 80, "unit": "percent", "target_id": None}]})


def create(store, tenant, adapter, **extra):
    return farm_workflow.create_proposal(store, tenant, adapter=adapter, session_id="session-1",
        base_revision=2, changes=[{"kind": "planning_assumptions", "assumptions": {
            "capacity": {"labour_hours_per_week": 40}}}], idempotency_key="discussion-proposal",
        source_conversation_id="discussion-1", source_message_id="message-1", **extra)


def test_discussion_draft_preserves_advice_and_user_changes_without_applying(setup):
    store, tenant, _, adapter = setup
    message = discussion(store, tenant)
    before = deepcopy(adapter.session)
    proposal = create(store, tenant, adapter)
    assert proposal["status"] == "draft"
    assert proposal["source_conversation"]["message_hash"] == farm_workflow.content_hash(message)
    assert proposal["source_conversation"]["proposed_actions"][0]["value"] == 80
    assert proposal["changes"][0]["assumptions"]["capacity"]["labour_hours_per_week"] == 40
    assert adapter.session == before
    assert create(store, tenant, adapter) == proposal
    assert farm_workflow.workflow_state(store, tenant)["tasks"] == []


@pytest.mark.parametrize("snapshot,validation", [
    ("session-1:stale-result", "references_verified"),
    ("other-session:result-1", "references_verified"),
    ("session-1:result-1", "unsupported"),
])
def test_stale_or_withheld_discussion_cannot_support_a_draft(setup, snapshot, validation):
    store, tenant, _, adapter = setup
    discussion(store, tenant, snapshot=snapshot, validation=validation)
    with pytest.raises(ValueError): create(store, tenant, adapter)
    assert farm_workflow.workflow_state(store, tenant)["proposals"] == []


def test_cross_tenant_discussion_is_unavailable(setup):
    store, tenant, other, adapter = setup
    discussion(store, other)
    with pytest.raises(ValueError, match="not found"): create(store, tenant, adapter)


def test_partial_discussion_reference_is_rejected(setup):
    store, tenant, _, adapter = setup
    with pytest.raises(ValueError, match="both conversation and message"):
        farm_workflow.create_proposal(store, tenant, adapter=adapter, session_id="session-1",
            base_revision=2, changes=[], idempotency_key="incomplete", source_conversation_id="discussion-1")
