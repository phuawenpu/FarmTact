from packages.ai_quality import QualityCase, evaluate_message, evaluate_suite
from scripts.deepseek_quality_e2e import _apply_human_review, _workflow_integrity, collect_cases
from scripts.deepseek_conversation_trial import responses_verified


CASE = QualityCase(
    case_id="harvest-mass",
    workflow="direct",
    expected_roles=("production_analyst",),
    required_reference_prefixes=("forecast:batch_batch-01.",),
    relevant_terms=("harvest", "batch"),
    forbidden_conclusions=("guaranteed", "observed yield"),
)


def message(**overrides):
    value = {
        "id": "reply-1",
        "speaker": "advisor",
        "advisor_role": "production_analyst",
        "content": "The harvest baseline for this batch needs cautious review.",
        "fact_refs": ["forecast:batch_batch-01.marketable_kg"],
        "tool_refs": [],
        "relationship": "answer",
        "validation_status": "references_verified",
        "execution_status": "completed",
        "evidence_status": "grounded_facts_qualitative_unverified",
        "validation_issues": [],
        "usage": {"prompt_tokens": 10, "completion_tokens": 8},
    }
    value.update(overrides)
    return value


def test_quality_case_scores_dimensions_separately_and_preserves_usage():
    result = evaluate_message(CASE, message())
    assert result["status"] == "PASS"
    assert set(result["checks"]) == {
        "role_relevance", "expected_reference", "reference_integrity",
        "unsupported_quantity", "contradiction", "abstention", "relationship",
        "persisted_validation", "evidence", "useful_answer",
    }
    assert result["usage"]["completion_tokens"] == 8


def test_quality_case_exposes_citation_laundering_contradiction_and_wrong_entity():
    result = evaluate_message(
        CASE,
        message(
            content="Observed yield is guaranteed at 12 kg.",
            fact_refs=["forecast:batch_batch-02.marketable_kg"],
            evidence_status="unsupported",
            validation_issues=[{"code":"model_authored_quantity"}],
        ),
    )
    assert result["status"] == "FAIL"
    assert result["checks"]["expected_reference"] is False
    assert result["checks"]["unsupported_quantity"] is False
    assert result["checks"]["contradiction"] is False
    assert result["checks"]["evidence"] is False


def test_useful_explicit_abstention_passes_without_laundered_reference():
    result = evaluate_message(
        CASE,
        message(
            content="I abstain because the frozen context cannot establish harvest quality.",
            fact_refs=[], relationship="abstention",
            evidence_status="qualitative_unverified",
        ),
    )
    assert result["status"] == "PASS"


def test_suite_keeps_failed_attempts_and_missing_cases_visible():
    missing = QualityCase(
        case_id="research-abstention", workflow="research", expected_roles=("planning_chair",),
        required_reference_prefixes=("research:",), relevant_terms=("research",),
    )
    report = evaluate_suite(
        [CASE, missing],
        {CASE.case_id: message()},
        {CASE.case_id: [{"status":"schema_failed","usage":{"total_tokens":12}}]},
    )
    assert report["status"] == "FAIL"
    assert report["failed_case_ids"] == ["research-abstention"]
    assert report["results"][0]["attempts"][0]["status"] == "schema_failed"


def test_e2e_harness_labels_direct_invite_council_and_research_without_calling_provider():
    messages=[]
    for index,(mode,role) in enumerate((
        ("direct","production_analyst"),
        ("invite","demand_analyst"),
        ("council","planning_chair"),
    )):
        messages.append(message(
            id=f"message-{index}", request_mode=mode, advisor_role=role,
            content={
                "production_analyst":"The harvest batch needs cautious review.",
                "demand_analyst":"The demand delivery needs cautious review.",
                "planning_chair":"The strategy comparison needs cautious review.",
            }[role],
            fact_refs={
                "production_analyst":["forecast:batch_batch-01.marketable_kg"],
                "demand_analyst":["forecast:caixin.week_0.expected_kg"],
                "planning_chair":["strategy:balanced.metrics.margin_sgd"],
            }[role],
        ))
    cases,_,_=collect_cases({"snapshot_ref":{"kind":"scenario"},"messages":messages},"main")
    assert {case.workflow for case in cases} == {"direct","invite","council"}
    research_cases,_,_=collect_cases(
        {"snapshot_ref":{"kind":"research"},"messages":[messages[0]]},"research"
    )
    assert research_cases[0].workflow == "research"


def test_keyword_and_reference_shape_cannot_certify_bad_persisted_validation():
    result = evaluate_message(
        CASE,
        message(
            content="Harvest harvest harvest remains a batch review.",
            validation_status="unsupported",
            validation_errors=["Known validation failure"],
        ),
    )
    assert result["status"] == "FAIL"
    assert result["checks"]["persisted_validation"] is False


def test_reference_must_not_be_laundered_between_typed_and_qualitative_lists():
    ref = "forecast:batch_batch-01.marketable_kg"
    result = evaluate_message(CASE, message(fact_refs=[ref], tool_refs=[ref]))
    assert result["checks"]["reference_integrity"] is False
    assert result["status"] == "FAIL"


def test_transport_complete_trial_does_not_pass_an_unsupported_reply():
    assert responses_verified([message()]) is True
    assert responses_verified([message(validation_status="unsupported")]) is False
    assert responses_verified([]) is False


def test_automated_pass_does_not_claim_unreviewed_semantic_assurance():
    report = evaluate_suite([CASE], {CASE.case_id: message()})
    _apply_human_review(report, None)
    assert report["status"] == "PASS_AUTOMATED"
    assert report["automated_status"] == "PASS"
    assert report["semantic_review_status"] == "PENDING"
    assert "does not establish" in report["pass_scope"]


def test_workflow_integrity_rejects_role_shaped_but_incomplete_council():
    messages = [
        message(id="chair", advisor_role="planning_chair", request_id="request", request_mode="council")
    ]
    cases, by_case, _ = collect_cases(
        {"snapshot_ref": {"kind": "scenario"}, "messages": messages}, "main"
    )
    integrity = _workflow_integrity(cases, by_case, {"council"})
    assert integrity["status"] == "FAIL"
    assert integrity["workflows"][0]["checks"]["exact_message_count"] is False
