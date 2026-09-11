#!/usr/bin/env python3
"""Evaluate stored actual AI outputs without triggering inference.

Deterministic checks reject malformed provenance, incomplete workflows, and
known failure patterns. They can return PASS_AUTOMATED without human review;
the separate semantic-review dimension stays pending because keywords and
citations cannot prove free-form meaning.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any, Mapping
from urllib.parse import urlsplit

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.agents import ROLES
from packages.ai_quality import QualityCase, evaluate_suite


KNOWN_FALSE_CONCLUSIONS = (
    "guaranteed", "observed yield", "real farm approved", "will definitely",
    "rental-input", "rental input", "marginal return", "per added",
)
ROLE_EXPECTATIONS = {
    "demand_analyst": (
        ("forecast:", "delivery:", "order:", "comparison:", "scenario:"),
        (("demand", "delivery", "order", "shortfall", "coverage"),),
    ),
    "weather_analyst": (
        ("source:", "weather:", "farm:", "strategy:", "scenario:"),
        (("weather", "condition", "uncertainty", "context", "yield adjustment"),),
    ),
    "market_analyst": (
        ("market:", "news:", "delivery:", "farm:", "strategy:", "scenario:"),
        (("market", "price", "buyer", "signal", "commercial", "demand"),),
    ),
    "production_analyst": (
        ("forecast:batch_", "batch:", "recipe:", "bed:", "schedule:", "scenario:", "comparison:"),
        (("harvest", "batch", "crop", "bed", "production", "allocation", "scenario", "comparison"),),
    ),
    "supply_chain_analyst": (
        ("forecast:batch_", "batch:", "delivery:", "farm:", "schedule:", "order:", "strategy:"),
        (("supply", "inventory", "delivery", "expiry", "batch", "order", "shortfall"),),
    ),
    "profit_analyst": (
        ("strategy:", "scenario:", "comparison:", "farm:resources."),
        (("margin", "cash", "labour", "cost", "strategy", "profit"),),
    ),
    "planning_chair": (
        ("strategy:", "scenario:", "comparison:", "forecast:", "research:"),
        (("plan", "strategy", "comparison", "evidence", "conclusion", "research"),),
    ),
}
EXPECTED_WORKFLOW_ROLES = {
    "direct": ("production_analyst",),
    "invite": ("demand_analyst", "production_analyst"),
    "council": tuple(ROLES),
    "research": ("planning_chair",),
    "planning": tuple(ROLES),
}


def get_json(client: httpx.Client, path: str) -> dict[str, Any]:
    response = client.get(path)
    response.raise_for_status()
    return response.json()


def _case_for(case_id: str, workflow: str, role: str) -> QualityCase:
    reference_prefixes, term_groups = ROLE_EXPECTATIONS[role]
    if workflow == "direct":
        term_groups = (
            ("experiment", "scenario", "comparison"),
            ("frozen", "synthetic", "assumption", "unsupported"),
        )
    elif workflow == "research":
        term_groups = (("reserved", "reservation"), ("unconfirmed",), ("order",))
        reference_prefixes = ("research:",)
    expected_relationships = (
        ("conclusion",)
        if workflow in {"council", "planning"} and role == "planning_chair"
        else ("answer",)
        if workflow in {"direct", "research"}
        else ()
    )
    abstention_permitted = role in {"weather_analyst", "market_analyst"} and workflow in {
        "council", "planning"
    }
    return QualityCase(
        case_id=case_id,
        workflow=workflow,
        expected_roles=(role,),
        required_reference_prefixes=reference_prefixes,
        relevant_terms=tuple(term for group in term_groups for term in group),
        required_term_groups=term_groups,
        forbidden_conclusions=KNOWN_FALSE_CONCLUSIONS,
        abstention_permitted=abstention_permitted,
        expected_relationships=expected_relationships,
        grounded_fact_required=not abstention_permitted,
    )


def collect_cases(
    transcript: Mapping[str, Any], label: str,
    request_ids: Mapping[str, str] | None = None,
) -> tuple[list[QualityCase], dict[str, Mapping[str, Any]], dict[str, list[dict]]]:
    cases: list[QualityCase] = []
    messages: dict[str, Mapping[str, Any]] = {}
    positions: dict[str, int] = {}
    for message in transcript.get("messages", []):
        if message.get("speaker") != "advisor":
            continue
        role = message.get("advisor_role")
        if role not in ROLE_EXPECTATIONS:
            continue
        workflow = (
            "research" if transcript.get("snapshot_ref", {}).get("kind") == "research"
            else str(message.get("request_mode", "unknown"))
        )
        if request_ids and request_ids.get(workflow) != message.get("request_id"):
            continue
        position = positions.get(workflow, 0)
        positions[workflow] = position + 1
        case_id = f"{label}:{workflow}:{position}:{role}"
        cases.append(_case_for(case_id, workflow, role))
        messages[case_id] = message
    return cases, messages, {}


def collect_planning_cases(report: Mapping[str, Any]) -> tuple[list[QualityCase], dict[str, dict]]:
    run = report.get("run", report)
    claims = run.get("claims", run.get("council_claims", []))
    cases: list[QualityCase] = []
    messages: dict[str, dict] = {}
    for position, claim in enumerate(claims):
        role = claim.get("role")
        if role not in ROLE_EXPECTATIONS:
            continue
        case_id = f"planning:planning:{position}:{role}"
        normalized = {
            **claim,
            "id": f"{run.get('id', 'planning')}:{position}",
            "advisor_role": role,
            "content": claim.get("statement", ""),
            "tool_refs": claim.get("tool_result_refs", []),
            "relationship": (
                "conclusion" if role == "planning_chair" and claim.get("claim_type") == "decision"
                else "abstention" if claim.get("claim_type") == "abstention"
                else claim.get("claim_type")
            ),
            "validation_status": "validated" if claim.get("status") == "validated" else "unsupported",
        }
        cases.append(_case_for(case_id, "planning", role))
        messages[case_id] = normalized
    return cases, messages


def _workflow_integrity(
    cases: list[QualityCase], messages: Mapping[str, Mapping[str, Any]], required: set[str]
) -> dict[str, Any]:
    rows = []
    for workflow in sorted(required):
        ordered = [messages[case.case_id] for case in cases if case.workflow == workflow]
        roles = tuple(str(message.get("advisor_role")) for message in ordered)
        request_ids = {message.get("request_id") for message in ordered if message.get("request_id")}
        expected_roles = EXPECTED_WORKFLOW_ROLES[workflow]
        checks = {
            "exact_role_sequence": roles == expected_roles,
            "single_request": workflow == "planning" or len(request_ids) == 1,
            "exact_message_count": len(ordered) == len(expected_roles),
        }
        rows.append({
            "workflow": workflow,
            "expected_roles": list(expected_roles),
            "observed_roles": list(roles),
            "checks": checks,
            "status": "PASS" if all(checks.values()) else "FAIL",
        })
    return {
        "status": "PASS" if rows and all(row["status"] == "PASS" for row in rows) else "FAIL",
        "workflows": rows,
    }


def _apply_human_review(report: dict[str, Any], review: Mapping[str, Any] | None) -> None:
    report["automated_status"] = report["status"]
    expected_ids = {row["case_id"] for row in report["results"]}
    supplied = review.get("reviews", {}) if isinstance(review, Mapping) else {}
    valid = {
        case_id: dict(item)
        for case_id, item in supplied.items()
        if case_id in expected_ids
        and isinstance(item, Mapping)
        and item.get("status") in {"PASS", "FAIL"}
        and bool(str(item.get("rationale", "")).strip())
    }
    if set(valid) != expected_ids:
        report["semantic_review_status"] = "PENDING"
        if report["automated_status"] == "PASS":
            report["status"] = "PASS_AUTOMATED"
    else:
        report["semantic_review_status"] = (
            "PASS" if all(item["status"] == "PASS" for item in valid.values()) else "FAIL"
        )
        if report["semantic_review_status"] == "FAIL":
            report["status"] = "FAIL"
    report["human_reviews"] = valid
    report["semantic_assurance"] = (
        "Human review checks whether each conclusion follows from its rendered frozen facts; "
        "keyword and reference checks alone do not establish meaning."
    )
    report["pass_scope"] = (
        "Automated status covers exact workflow roles and counts, persisted validation, "
        "reference shape, required topic groups, quantitative-prose blocking, and known "
        "contradiction phrases. It does not establish that arbitrary prose follows from facts."
    )


def run(
    base_url: str, conversation_id: str,
    research_conversation_id: str | None = None, cookie: str | None = None, *,
    request_ids: Mapping[str, str] | None = None,
    planning_report: Mapping[str, Any] | None = None,
    research_replay: Mapping[str, Any] | None = None,
    human_review: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    edition = urlsplit(base_url).path.strip("/")
    cookie_name = f"farmtact_{edition}_session" if edition.startswith("v") and edition[1:].isdigit() else "farmtact_session"
    with httpx.Client(base_url=base_url.rstrip("/"), timeout=30, follow_redirects=False) as client:
        if cookie:
            client.cookies.set(cookie_name, cookie)
        transcripts = [("conversation", get_json(client, f"/api/v1/conversations/{conversation_id}"), True)]
        if research_conversation_id:
            transcripts.append(("research", get_json(client, f"/api/v1/conversations/{research_conversation_id}"), True))
        elif research_replay is not None:
            transcripts.append(("research", dict(research_replay), False))
        all_cases: list[QualityCase] = []
        all_messages: dict[str, Mapping[str, Any]] = {}
        all_attempts: dict[str, list[dict]] = {}
        for label, transcript, fetch_events in transcripts:
            selected_request_ids = dict(request_ids or {})
            if label == "research" and not fetch_events and transcript.get("last_request_id"):
                selected_request_ids["research"] = transcript["last_request_id"]
            cases, messages, _ = collect_cases(
                transcript, label, selected_request_ids or None
            )
            all_cases.extend(cases)
            all_messages.update(messages)
            events = (
                get_json(client, f"/api/v1/conversations/{transcript['id']}/events").get("events", [])
                if fetch_events else transcript.get("events", [])
            )
            by_request: dict[str, list[dict]] = {}
            for event in events:
                if event.get("event_type") in {
                    "advisor_reply_repair", "conversation_request_failed",
                    "advisor_message_unsupported", "conversation_request_cancelled",
                }:
                    by_request.setdefault(str(event.get("request_id")), []).append({
                        "event_type": event["event_type"], "body": event.get("body", {}),
                    })
            for case_id, message in messages.items():
                all_attempts[case_id] = by_request.get(str(message.get("request_id")), [])
        if planning_report is not None:
            cases, messages = collect_planning_cases(planning_report)
            all_cases.extend(cases)
            all_messages.update(messages)

        report = evaluate_suite(all_cases, all_messages, all_attempts)
        required = {"direct", "invite", "council"}
        if research_conversation_id or research_replay is not None:
            required.add("research")
        if planning_report is not None:
            required.add("planning")
        integrity = _workflow_integrity(all_cases, all_messages, required)
        report.update(
            execution_scope="stored_actual_outputs_no_new_inference",
            required_workflows=sorted(required),
            observed_workflows=sorted({case.workflow for case in all_cases}),
            workflow_integrity=integrity,
            source_provenance={
                "conversation": "base_url_stored_transcript",
                "research": (
                    "base_url_stored_transcript" if research_conversation_id
                    else "provided_read_only_replay" if research_replay is not None
                    else "not_included"
                ),
                "planning": "provided_report" if planning_report is not None else "not_included",
            },
        )
        if research_replay is not None and (
            research_replay.get("inference_triggered") is not False
            or research_replay.get("transcript_mode") != "replay"
        ):
            report["workflow_integrity"]["status"] = "FAIL"
            report["workflow_integrity"]["research_replay_read_only"] = False
            report["status"] = "FAIL"
        if integrity["status"] != "PASS":
            report["status"] = "FAIL"
        _apply_human_review(report, human_review)
        return report


def _same_value(name: str, argument: str | None, saved: Any) -> str:
    if argument and saved and str(argument).rstrip("/") != str(saved).rstrip("/"):
        raise ValueError(f"{name} does not match the private trial state")
    value = argument or saved
    if not value:
        raise ValueError(f"Provide {name} or a private state containing it")
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url")
    parser.add_argument("--conversation-id")
    parser.add_argument("--research-conversation-id")
    parser.add_argument("--planning-report", type=Path)
    parser.add_argument("--research-replay", type=Path)
    parser.add_argument("--human-review", type=Path)
    parser.add_argument("--state", type=Path, help="Private 0600 state containing URL, IDs, and session cookie")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    state = json.loads(args.state.read_text(encoding="utf-8")) if args.state else {}
    if not isinstance(state, dict):
        parser.error("Private trial state must contain a JSON object")
    try:
        base_url = _same_value("--base-url", args.base_url, state.get("url"))
        conversation_id = _same_value("--conversation-id", args.conversation_id, state.get("conversation_id"))
        if args.research_replay and args.research_conversation_id:
            raise ValueError("Use either --research-replay or --research-conversation-id")
        research_id = None if args.research_replay else args.research_conversation_id or state.get("research_conversation_id")
        if args.research_conversation_id and state.get("research_conversation_id") and args.research_conversation_id != state["research_conversation_id"]:
            raise ValueError("--research-conversation-id does not match the private trial state")
    except ValueError as exc:
        parser.error(str(exc))
    request_ids = {
        workflow: state[key]
        for workflow, key in {
            "direct": "conversation_trial_direct_request_id",
            "invite": "conversation_trial_invite_request_id",
            "council": "conversation_trial_council_request_id",
            "research": "research_request_id",
        }.items()
        if state.get(key)
    }
    planning = json.loads(args.planning_report.read_text(encoding="utf-8")) if args.planning_report else None
    research_replay = json.loads(args.research_replay.read_text(encoding="utf-8")) if args.research_replay else None
    review = json.loads(args.human_review.read_text(encoding="utf-8")) if args.human_review else None
    report = run(
        base_url, conversation_id, research_id, state.get("cookie"),
        request_ids=request_ids or None, planning_report=planning,
        research_replay=research_replay, human_review=review,
    )
    report["source_artifacts"] = {
        "planning_report": str(args.planning_report) if args.planning_report else None,
        "research_replay": str(args.research_replay) if args.research_replay else None,
    }
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    raise SystemExit(0 if report["status"] in {"PASS", "PASS_AUTOMATED"} else 1)


if __name__ == "__main__":
    main()
