#!/usr/bin/env python3
"""Score persisted actual advisor outputs against frozen FarmTact cases.

This reader never triggers inference. Run ``deepseek_conversation_trial.py`` (and
one explicit research-snapshot direct question) first, then point this script at
their conversation IDs. Failed/repair events and per-message usage stay visible.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.ai_quality import QualityCase, evaluate_suite


ROLE_EXPECTATIONS = {
    "demand_analyst": (("forecast:", "delivery:"), ("demand", "delivery", "order", "shortfall")),
    "weather_analyst": (("source:", "weather:", "farm:"), ("weather", "condition", "uncertainty", "context")),
    "market_analyst": (("market:", "news:", "delivery:", "farm:"), ("market", "price", "buyer", "signal", "context")),
    "production_analyst": (("forecast:batch_", "batch:", "recipe:", "bed:"), ("harvest", "batch", "crop", "bed", "production", "allocation")),
    "supply_chain_analyst": (("forecast:batch_", "batch:", "delivery:", "farm:"), ("supply", "inventory", "delivery", "expiry", "batch")),
    "profit_analyst": (("strategy:", "scenario:", "comparison:", "farm:resources."), ("margin", "cash", "labour", "cost", "strategy")),
    "planning_chair": (("strategy:", "scenario:", "comparison:", "forecast:"), ("plan", "strategy", "comparison", "evidence", "conclusion")),
}


def get_json(client: httpx.Client, path: str) -> dict:
    response = client.get(path)
    response.raise_for_status()
    return response.json()


def collect_cases(transcript: dict, label: str) -> tuple[list[QualityCase], dict, dict]:
    cases=[]; messages={}; attempts={}
    for index,message in enumerate(transcript.get("messages", [])):
        if message.get("speaker") != "advisor":
            continue
        role = message.get("advisor_role")
        expected = ROLE_EXPECTATIONS.get(role)
        if not expected:
            continue
        mode = "research" if transcript.get("snapshot_ref", {}).get("kind") == "research" else message.get("request_mode", "unknown")
        case_id = f"{label}:{mode}:{index}:{role}"
        cases.append(QualityCase(
            case_id=case_id, workflow=mode, expected_roles=(role,),
            required_reference_prefixes=expected[0], relevant_terms=expected[1],
            forbidden_conclusions=("guaranteed", "observed yield", "real farm approved", "will definitely"),
        ))
        messages[case_id] = message
    return cases,messages,attempts


def run(base_url: str, conversation_id: str, research_conversation_id: str | None = None, cookie: str | None = None) -> dict:
    edition=urlsplit(base_url).path.strip("/")
    cookie_name=f"farmtact_{edition}_session" if edition.startswith("v") and edition[1:].isdigit() else "farmtact_session"
    with httpx.Client(base_url=base_url.rstrip("/"),timeout=30,follow_redirects=False) as client:
        if cookie:
            client.cookies.set(cookie_name,cookie)
        transcripts=[("conversation",get_json(client,f"/api/v1/conversations/{conversation_id}"))]
        if research_conversation_id:
            transcripts.append(("research",get_json(client,f"/api/v1/conversations/{research_conversation_id}")))
        all_cases=[]; all_messages={}; all_attempts={}
        for label,transcript in transcripts:
            cases,messages,attempts=collect_cases(transcript,label)
            all_cases.extend(cases); all_messages.update(messages); all_attempts.update(attempts)
            events=get_json(client,f"/api/v1/conversations/{transcript['id']}/events").get("events",[])
            by_request={}
            for event in events:
                if event.get("event_type") in {"advisor_reply_repair","conversation_request_failed"}:
                    by_request.setdefault(event.get("request_id"),[]).append({
                        "event_type":event["event_type"],"body":event.get("body",{}),
                    })
            for case_id,message in messages.items():
                all_attempts[case_id]=by_request.get(message.get("request_id"),[])
        report=evaluate_suite(all_cases,all_messages,all_attempts)
        workflows={case.workflow for case in all_cases}
        required={"direct","invite","council"} | ({"research"} if research_conversation_id else set())
        report.update(
            execution_scope="stored_actual_outputs_no_new_inference",
            required_workflows=sorted(required), observed_workflows=sorted(workflows),
            workflow_coverage_status="PASS" if required <= workflows else "FAIL",
        )
        if report["workflow_coverage_status"] != "PASS":
            report["status"]="FAIL"
        return report


def main() -> None:
    parser=argparse.ArgumentParser()
    parser.add_argument("--base-url",required=True)
    parser.add_argument("--conversation-id",required=True)
    parser.add_argument("--research-conversation-id")
    parser.add_argument("--state",type=Path,help="Private 0600 trial state containing the session cookie")
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    cookie=None
    if args.state:
        state=json.loads(args.state.read_text(encoding="utf-8"))
        cookie=state.get("cookie")
    report=run(args.base_url,args.conversation_id,args.research_conversation_id,cookie)
    rendered=json.dumps(report,indent=2,sort_keys=True)
    if args.output:
        args.output.write_text(rendered+"\n",encoding="utf-8")
    else:
        print(rendered)
    raise SystemExit(0 if report["status"] == "PASS" else 1)


if __name__ == "__main__":
    main()
