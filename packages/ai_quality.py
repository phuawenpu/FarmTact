"""Deterministic quality checks for bounded, expert-reviewable advisor cases."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from packages.ai_contracts import quantitative_prose_present


QUALITY_SUITE_VERSION = "farmtact-advisor-quality-v2"


@dataclass(frozen=True)
class QualityCase:
    case_id: str
    workflow: str
    expected_roles: tuple[str, ...]
    required_reference_prefixes: tuple[str, ...]
    relevant_terms: tuple[str, ...]
    forbidden_conclusions: tuple[str, ...] = ()
    abstention_permitted: bool = True
    required_reference_groups: tuple[tuple[str, ...], ...] = ()
    required_term_groups: tuple[tuple[str, ...], ...] = ()
    expected_relationships: tuple[str, ...] = ()
    grounded_fact_required: bool = True


def evaluate_message(case: QualityCase, message: Mapping[str, Any]) -> dict[str, Any]:
    content = str(message.get("content", ""))
    lowered = content.casefold()
    fact_refs = list(message.get("fact_refs", []))
    tool_refs = list(message.get("tool_refs", []))
    refs = fact_refs + tool_refs
    abstained = message.get("relationship") == "abstention"
    reference_groups = case.required_reference_groups or (
        (case.required_reference_prefixes,) if case.required_reference_prefixes else ()
    )
    term_groups = case.required_term_groups or (
        (case.relevant_terms,) if case.relevant_terms else ()
    )
    persisted_validation = message.get("validation_status") in {
        "references_verified", "validated"
    }
    execution_completed = message.get("execution_status", "completed") == "completed"
    checks = {
        "role_relevance": message.get("advisor_role") in case.expected_roles
        and all(any(term.casefold() in lowered for term in group) for group in term_groups),
        "expected_reference": (abstained and case.abstention_permitted) or all(
            any(ref.startswith(prefix) for prefix in group for ref in refs)
            for group in reference_groups
        ),
        "reference_integrity": all(isinstance(ref, str) and bool(ref) for ref in refs)
        and len(refs) == len(set(refs))
        and not set(fact_refs).intersection(tool_refs),
        "unsupported_quantity": not quantitative_prose_present(content),
        "contradiction": not any(term.casefold() in lowered for term in case.forbidden_conclusions),
        "abstention": case.abstention_permitted or not abstained,
        "relationship": not case.expected_relationships
        or message.get("relationship") in case.expected_relationships,
        "persisted_validation": persisted_validation and execution_completed
        and not message.get("validation_issues")
        and not message.get("validation_errors"),
        "evidence": (
            str(message.get("evidence_status", "")).startswith("grounded_facts")
            and (bool(fact_refs) or not case.grounded_fact_required)
        ) or (
            abstained
            and case.abstention_permitted
            and message.get("evidence_status") == "qualitative_unverified"
        ),
        "useful_answer": len(content.strip()) >= 40 and (bool(refs) or abstained),
    }
    return {
        "case_id": case.case_id,
        "workflow": case.workflow,
        "message_id": message.get("id"),
        "checks": checks,
        "status": "PASS" if all(checks.values()) else "FAIL",
        "usage": message.get("usage", {}),
        "validation_issues": list(message.get("validation_issues", [])),
    }


def evaluate_suite(
    cases: Sequence[QualityCase], messages_by_case: Mapping[str, Mapping[str, Any]],
    attempts_by_case: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> dict[str, Any]:
    results = []
    for case in cases:
        message = messages_by_case.get(case.case_id)
        if message is None:
            results.append({"case_id":case.case_id,"workflow":case.workflow,"status":"MISSING","checks":{},"usage":{},"validation_issues":[]})
            continue
        result = evaluate_message(case, message)
        result["attempts"] = [dict(item) for item in (attempts_by_case or {}).get(case.case_id, [])]
        results.append(result)
    return {
        "suite_version": QUALITY_SUITE_VERSION,
        "status": "PASS" if results and all(row["status"] == "PASS" for row in results) else "FAIL",
        "case_count": len(results),
        "failed_case_ids": [row["case_id"] for row in results if row["status"] != "PASS"],
        "results": results,
    }
