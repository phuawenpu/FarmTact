#!/usr/bin/env python3
"""Run one restart-safe DeepSeek interpretation of a frozen research result.

Point ``--state`` at the private state written by
``deepseek_conversation_trial.py`` to reuse its URL and session. Every mutation
gets a stable key which is written before submission, so a restart recovers the
stored receipt instead of creating another study or billable request. The only
inference request is a direct advisor turn: one initial call plus at most one
schema repair.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
import uuid
from urllib.parse import urlsplit

import httpx


TERMINAL = {"COMPLETED", "PARTIAL", "FAILED", "BLOCKED", "INTERRUPTED", "CANCELLED"}
MAX_PROVIDER_CALLS = 2


def write_private_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as target:
        json.dump(state, target)
    path.chmod(0o600)


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cookie_value(cookies: httpx.Cookies, name: str) -> str | None:
    return next((cookie.value for cookie in cookies.jar if cookie.name == name), None)


def run(
    url: str | None,
    report_path: Path,
    ledger_path: Path,
    state_path: Path | None = None,
    timeout: float = 330,
    retry_unsupported: bool = False,
) -> dict:
    state = (
        json.loads(state_path.read_text(encoding="utf-8"))
        if state_path and state_path.exists()
        else {}
    )
    if not isinstance(state, dict):
        raise ValueError("Private trial state must contain a JSON object")
    saved_url = state.get("url")
    if url and saved_url and url.rstrip("/") != str(saved_url).rstrip("/"):
        raise ValueError("--url does not match the URL in the private trial state")
    url = str(saved_url or url or "")
    if not url:
        raise ValueError("Provide --url or a --state file containing url")

    prefix = state.setdefault("research_trial_prefix", f"research-trial-{uuid.uuid4().hex}")

    def save_state() -> None:
        if state_path:
            write_private_state(state_path, state)

    save_state()
    ledger = (
        json.loads(ledger_path.read_text(encoding="utf-8"))
        if ledger_path.exists()
        else {
            "schema_version": "research-advisor-budget-v2",
            "maximum_provider_calls_per_run": MAX_PROVIDER_CALLS,
            "runs": [],
        }
    )
    if ledger.get("maximum_provider_calls_per_run") != MAX_PROVIDER_CALLS:
        raise RuntimeError("Research experiment ledger has an incompatible request ceiling")
    active_run_key = state.setdefault("research_active_run_key", prefix)
    run_record = next(
        (item for item in ledger["runs"] if item.get("run_key") == active_run_key), None
    )
    if run_record is None:
        run_record = {
            "run_key": active_run_key,
            "status": "PREPARING",
            "maximum_provider_calls": MAX_PROVIDER_CALLS,
            "actual_provider_calls": 0,
            "started_at": datetime.now(timezone.utc).isoformat(),
        }
        ledger["runs"].append(run_record)
        write_json(ledger_path, ledger)

    report = {
        "status": "RUNNING",
        "url": url,
        "maximum_provider_calls_this_run": MAX_PROVIDER_CALLS,
        "purpose": "Explicit interpretation of a frozen numerical research result; no farm mutation.",
        "private_state_updated": bool(state_path),
    }
    paid_submission_started = False
    edition = urlsplit(url).path.strip("/")
    cookie_name = (
        f"farmtact_{edition}_session"
        if edition.startswith("v") and edition[1:].isdigit()
        else "farmtact_session"
    )

    with httpx.Client(base_url=url.rstrip("/"), timeout=30, follow_redirects=False) as client:
        if state.get("cookie"):
            client.cookies.set(cookie_name, state["cookie"])

        def get(path: str) -> dict:
            response = client.get("/api/v1" + path)
            response.raise_for_status()
            return response.json()

        def post(path: str, body: dict, key: str) -> dict:
            response = client.post(
                "/api/v1" + path,
                json=body,
                headers={"Idempotency-Key": key},
            )
            response.raise_for_status()
            return response.json()

        try:
            bootstrap = get("/bootstrap")
            if urlsplit(url).hostname in {"127.0.0.1", "localhost"}:
                for cookie in client.cookies.jar:
                    cookie.secure = False
            state.update(url=url, cookie=cookie_value(client.cookies, cookie_name))
            save_state()
            farm_before = bootstrap["farm"]

            create_key = state.setdefault("research_trial_create_key", f"{prefix}-create")
            save_state()
            if state.get("research_session_id"):
                study = get(f"/council-research/{state['research_session_id']}")
            else:
                study = post("/council-research", {}, create_key)
                state["research_session_id"] = study["id"]
                save_state()

            action_steps = state.setdefault("research_trial_actions", {})

            def action(step: str, kind: str, **fields: object) -> dict:
                current = get(f"/council-research/{state['research_session_id']}")
                saved = action_steps.get(step)
                if saved and saved.get("completed"):
                    return current
                if saved is None:
                    saved = {
                        "key": f"{prefix}-{step}",
                        "body": {
                            "action": kind,
                            "revision": current["revision"],
                            **fields,
                        },
                        "completed": False,
                    }
                    action_steps[step] = saved
                    save_state()
                receipt = post(
                    f"/council-research/{state['research_session_id']}/actions",
                    saved["body"],
                    saved["key"],
                )
                saved.update(completed=True, resulting_revision=receipt["revision"])
                save_state()
                return get(f"/council-research/{state['research_session_id']}")

            action(
                "reserve-proposal",
                "propose",
                operation="reserve_bed",
                bed_id="bed-04",
                start_date="2026-09-17",
                end_date="2026-11-02",
            )
            action("reserve-apply", "apply")
            action(
                "order-proposal",
                "propose",
                operation="order_status",
                order_id="research-extra-order",
                confirmed=False,
            )
            action("order-apply", "apply")
            action("calculate", "run")

            deadline = time.monotonic() + timeout
            while True:
                study = get(f"/council-research/{state['research_session_id']}")
                result = next(
                    (
                        item
                        for item in study["results"]
                        if item["version"] == study["input_version"]
                        and item["status"] in {"COMPLETED", "FAILED"}
                    ),
                    None,
                )
                if result:
                    break
                if time.monotonic() > deadline:
                    raise TimeoutError("Numerical worker did not complete")
                time.sleep(1)
            if result["status"] != "COMPLETED":
                raise RuntimeError("Research numerical calculation failed")

            prior_request_id = state.get("research_request_id")
            if (
                retry_unsupported
                and prior_request_id
                and state.get("research_conversation_id")
                and not state.get("research_context_v4_retry_used")
            ):
                prior = get(f"/conversations/{state['research_conversation_id']}")
                prior_replies = [
                    message for message in prior.get("messages", [])
                    if message.get("speaker") == "advisor"
                    and message.get("request_id") == prior_request_id
                ]
                if (
                    prior.get("last_request_id") == prior_request_id
                    and prior.get("last_request_status") == "COMPLETED"
                    and prior_replies
                    and any(message.get("validation_status") != "references_verified" for message in prior_replies)
                ):
                    state.update(
                        research_context_v4_retry_used=True,
                        research_prior_conversation_id=state["research_conversation_id"],
                        research_prior_unsupported_request_id=prior_request_id,
                        research_active_run_key=f"{prefix}:context-v4-retry",
                        research_trial_conversation_key=f"{prefix}-conversation-context-v4-retry",
                        research_trial_message_key=f"{prefix}-direct-context-v4-retry",
                        research_trial_completed=False,
                    )
                    state.pop("research_conversation_id", None)
                    state.pop("research_request_id", None)
                    active_run_key = state["research_active_run_key"]
                    run_record = next(
                        (item for item in ledger["runs"] if item.get("run_key") == active_run_key),
                        None,
                    )
                    if run_record is None:
                        run_record = {
                            "run_key": active_run_key,
                            "status": "PREPARING",
                            "maximum_provider_calls": MAX_PROVIDER_CALLS,
                            "actual_provider_calls": 0,
                            "started_at": datetime.now(timezone.utc).isoformat(),
                            "reason": "Reviewed retry with newly frozen v4 context",
                        }
                        ledger["runs"].append(run_record)
                    save_state()
                    write_json(ledger_path, ledger)

            conversation_key = state.setdefault(
                "research_trial_conversation_key", f"{prefix}-conversation"
            )
            save_state()
            if state.get("research_conversation_id"):
                conversation = get(f"/conversations/{state['research_conversation_id']}")
                expected_snapshot_id = f"{state['research_session_id']}:v{study['input_version']}"
                if conversation["snapshot_ref"].get("kind") != "research" or conversation["snapshot_ref"]["id"] != expected_snapshot_id or conversation["snapshot_ref"].get("version") != study["input_version"]:
                    raise RuntimeError("Saved research conversation uses another study")
            else:
                created = post(
                    "/conversations",
                    {
                        "advisor": "asha",
                        "snapshot_kind": "research",
                        "snapshot_id": state["research_session_id"],
                        "research_version": study["input_version"],
                        "selected_bed_id": "bed-04",
                    },
                    conversation_key,
                )
                state["research_conversation_id"] = created["id"]
                save_state()
                conversation = get(f"/conversations/{state['research_conversation_id']}")

            message_body = {
                "content": (
                    "Explain the reserved bed and unconfirmed order in this frozen research result. "
                    "Cite the exact research:reservation and research:unconfirmed_order references, "
                    "plus relevant typed numerical or date references. Do not claim to "
                    "have changed any inputs or real farm operations."
                )
            }
            request_id = state.get("research_request_id")
            message_key = state.setdefault("research_trial_message_key", f"{prefix}-direct")
            save_state()
            if not request_id:
                run_record["status"] = "RESERVED"
                write_json(ledger_path, ledger)
                paid_submission_started = True
                queued = post(
                    f"/conversations/{state['research_conversation_id']}/messages",
                    message_body,
                    message_key,
                )
                request_id = queued["id"]
                state["research_request_id"] = request_id
                save_state()

            deadline = time.monotonic() + timeout
            while True:
                conversation = get(f"/conversations/{state['research_conversation_id']}")
                if (
                    conversation.get("last_request_id") == request_id
                    and conversation.get("last_request_status") in TERMINAL
                ):
                    break
                if time.monotonic() > deadline:
                    raise TimeoutError("Advisor request did not terminate")
                time.sleep(1)

            events = get(f"/conversations/{state['research_conversation_id']}/events")["events"]
            calls = sum(
                event.get("event_type") == "inference_request_reserved"
                and event.get("request_id") == request_id
                for event in events
            )
            run_record["actual_provider_calls"] = calls
            if calls > MAX_PROVIDER_CALLS:
                raise RuntimeError("Research advisor request exceeded its two-call ceiling")
            run_record.update(
                status=conversation["last_request_status"],
                completed_at=datetime.now(timezone.utc).isoformat(),
            )
            replay = get(f"/conversations/{state['research_conversation_id']}/replay")
            if replay.get("inference_triggered") is not False:
                raise RuntimeError("Stored research conversation replay triggered inference")
            if farm_before != get("/bootstrap")["farm"]:
                raise RuntimeError("Research trial changed the main farm")
            if conversation["snapshot_ref"]["hash"] != result["input_hash"]:
                raise RuntimeError("Research conversation snapshot hash changed")
            if conversation["snapshot_ref"]["version"] != study["input_version"]:
                raise RuntimeError("Research conversation snapshot version changed")
            if conversation["tool_results"]["research:version"] != study["input_version"]:
                raise RuntimeError("Research tool results use another input version")

            replies = [
                message
                for message in conversation["messages"]
                if message.get("speaker") == "advisor"
                and message.get("request_id") == request_id
            ]
            references_verified = bool(replies) and all(
                message.get("validation_status") == "references_verified"
                for message in replies
            )
            final_status = (
                "PASS"
                if conversation["last_request_status"] == "COMPLETED"
                and replies
                and references_verified
                else "FAIL"
                if conversation["last_request_status"] == "COMPLETED"
                else conversation["last_request_status"]
            )
            state.update(
                research_version=study["input_version"],
                research_input_hash=result["input_hash"],
                research_trial_completed=final_status == "PASS",
            )
            save_state()
            report.update(
                status=final_status,
                actual_provider_calls=calls,
                references_verified=references_verified,
                frozen_context_match=True,
                main_farm_unchanged=True,
                replay_inference_triggered=False,
                advisor_messages=replies,
                events=[
                    event for event in events if event.get("request_id") == request_id
                ],
                pass_scope=(
                    "Provider boundary, frozen context, main-farm preservation and replay; "
                    "interpretation quality is reported separately."
                ),
            )
            return report
        except Exception as error:
            if not paid_submission_started and not state.get("research_request_id"):
                run_record.update(
                    status="FAILED_BEFORE_PROVIDER_SUBMISSION", actual_provider_calls=0
                )
            else:
                run_record["status"] = "FAILED"
            report.update(status="FAILED", error=type(error).__name__)
            raise
        finally:
            write_json(ledger_path, ledger)
            write_json(report_path, report)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", help="Application base URL; optional when --state contains url")
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("reports/v8/research_advisor_experiment_budget.json"),
    )
    parser.add_argument(
        "--state",
        type=Path,
        help="Private 0600 state file from deepseek_conversation_trial.py to reuse and update.",
    )
    parser.add_argument("--timeout", type=float, default=330)
    parser.add_argument("--live", action="store_true")
    parser.add_argument(
        "--retry-unsupported",
        action="store_true",
        help="Retry one preserved unsupported pre-v4 response with a new stable key.",
    )
    args = parser.parse_args()
    if not args.live:
        parser.error("Explicit --live required: the application may invoke DeepSeek")
    result = run(
        args.url, args.report, args.ledger, args.state, args.timeout,
        retry_unsupported=args.retry_unsupported,
    )
    print(
        result["status"],
        "provider requests:",
        result.get("actual_provider_calls", "unknown"),
    )


if __name__ == "__main__":
    main()
