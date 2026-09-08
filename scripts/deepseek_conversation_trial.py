#!/usr/bin/env python3
"""Run the bounded deployed FarmTact dialogue and council acceptance trial.

This script makes no provider request itself.  It exercises the deployed API,
whose server-side DeepSeek gateway and global budget remain authoritative.  One
direct turn, one two-advisor invitation, and one eight-turn council consume 11
normal requests and at most 15 requests if every allowed format repair is used.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import uuid

import httpx


TERMINAL = {"COMPLETED", "PARTIAL", "FAILED", "BLOCKED", "INTERRUPTED"}


def post(client: httpx.Client, path: str, body: dict, key: str) -> dict:
    response = client.post(path, json=body, headers={"Idempotency-Key": key})
    response.raise_for_status()
    return response.json()


def wait_scenario(client: httpx.Client, scenario_id: str, timeout: float) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/scenarios/{scenario_id}")
        response.raise_for_status()
        scenario = response.json()
        if scenario["status"] in {"COMPLETED", "FAILED"}:
            return scenario
        time.sleep(0.75)
    raise TimeoutError("Scenario did not reach a terminal state")


def wait_request(
    client: httpx.Client, conversation_id: str, request_id: str, timeout: float
) -> dict:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        response = client.get(f"/api/v1/conversations/{conversation_id}")
        response.raise_for_status()
        conversation = response.json()
        if (
            conversation.get("last_request_id") == request_id
            and conversation.get("last_request_status") in TERMINAL
        ):
            return conversation
        time.sleep(0.75)
    raise TimeoutError("Conversation request did not reach a terminal state")


def request_messages(conversation: dict, request_id: str) -> list[dict]:
    return [
        message
        for message in conversation.get("messages", [])
        if message.get("request_id") == request_id and message.get("speaker") == "advisor"
    ]


def digest(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def write_private_state(path: Path, state: dict) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as target:
        json.dump(state, target)
    path.chmod(0o600)


def session_cookie(cookies: httpx.Cookies) -> str | None:
    return next(
        (cookie.value for cookie in cookies.jar if cookie.name == "farmtact_session"),
        None,
    )


def run(base_url: str, timeout: float, state_path: Path | None = None, retry_failed: bool = False) -> dict:
    state = json.loads(state_path.read_text()) if state_path and state_path.exists() else {}
    if state.get("url"):
        base_url = state["url"]
    prefix = state.setdefault("conversation_trial_prefix", f"conversation-trial-{uuid.uuid4().hex}")

    def save_state() -> None:
        if state_path:
            write_private_state(state_path, state)

    with httpx.Client(base_url=base_url.rstrip("/"), timeout=30, follow_redirects=False) as client:
        if state.get("cookie") and session_cookie(client.cookies) is None:
            client.cookies.set("farmtact_session", state["cookie"])
        bootstrap = client.get("/api/v1/bootstrap")
        bootstrap.raise_for_status()
        state.update(url=base_url, cookie=session_cookie(client.cookies))
        save_state()
        batch_id = next(
            bed["batch_id"]
            for bed in bootstrap.json()["farm"]["beds"]
            if bed.get("batch_id")
        )

        if state.get("scenario_id"):
            scenario_response = client.get(f"/api/v1/scenarios/{state['scenario_id']}")
            scenario_response.raise_for_status()
            scenario = scenario_response.json()
        else:
            state.setdefault("conversation_trial_scenario_key", f"{prefix}-scenario")
            save_state()
            scenario = post(
                client,
                "/api/v1/scenarios",
                {
                    "name": "Bounded advisor trial",
                    "quest_id": "late_harvest",
                    "controls": {
                        "batch_id": batch_id,
                        "delay_days": 3,
                        "yield_percent": 90,
                    },
                },
                state["conversation_trial_scenario_key"],
            )
            state["scenario_id"] = scenario["id"]
            state.setdefault("conversation_trial_scenario_run_key", f"{prefix}-scenario-run")
            save_state()
        if scenario["status"] == "DRAFT":
            post(
                client,
                f"/api/v1/scenarios/{scenario['id']}/run",
                {},
                state.setdefault("conversation_trial_scenario_run_key", f"{prefix}-scenario-run"),
            )
            save_state()
        if scenario["status"] in {"DRAFT", "QUEUED", "RUNNING"}:
            scenario = wait_scenario(client, scenario["id"], timeout)
        if scenario["status"] != "COMPLETED":
            raise RuntimeError("Numerical scenario failed before conversation trial")
        if state.get("conversation_id"):
            existing_response = client.get(
                f"/api/v1/conversations/{state['conversation_id']}"
            )
            existing_response.raise_for_status()
            existing = existing_response.json()
            if existing["snapshot_ref"]["id"] != scenario["id"]:
                raise RuntimeError("Saved conversation is attached to a different scenario")
            conversation_id = existing["id"]
        else:
            state.setdefault("conversation_trial_conversation_key", f"{prefix}-conversation")
            save_state()
            conversation = post(
                client,
                "/api/v1/conversations",
                {
                    "advisor": "mei",
                    "snapshot_kind": "scenario",
                    "snapshot_id": scenario["id"],
                        "selected_bed_id": next(iter(scenario.get("affected_bed_ids", [])), bootstrap.json()["farm"]["beds"][0]["id"]),
                },
                state["conversation_trial_conversation_key"],
            )
            conversation_id = conversation["id"]
            state["conversation_id"] = conversation_id
            save_state()

        def current_transcript() -> dict:
            response = client.get(f"/api/v1/conversations/{conversation_id}")
            response.raise_for_status()
            return response.json()

        def inference_count() -> int:
            response = client.get(f"/api/v1/conversations/{conversation_id}/events")
            response.raise_for_status()
            return sum(
                event["event_type"] == "inference_request_reserved"
                for event in response.json()["events"]
            )

        def stage(
            name: str,
            path: str,
            body: dict,
            expected_messages: int,
            worst_case_requests: int,
        ) -> tuple[dict, list[dict]]:
            request_field = f"conversation_trial_{name}_request_id"
            key_field = f"conversation_trial_{name}_key"
            request_id = state.get(request_field)
            transcript_before = current_transcript()
            if request_id:
                completed = request_messages(transcript_before, request_id)
                if len(completed) == expected_messages:
                    return transcript_before, completed
                retry_field = f"conversation_trial_{name}_release_retry"
                if retry_failed and transcript_before.get("last_request_status") == "FAILED" and not completed and not state.get(retry_field):
                    # Explicit post-fix retry only. Preserve the failure and all consumed
                    # calls in this conversation's unchanged aggregate allowance.
                    state[retry_field] = request_id
                    state[key_field] = f"{state[key_field]}-release-repair"
                    state.pop(request_field, None)
                    save_state()
            used = inference_count()
            if used + worst_case_requests > 16:
                raise RuntimeError(
                    f"Insufficient aggregate request allowance for {name}: {used} already consumed"
                )
            state.setdefault(key_field, f"{prefix}-{name}")
            save_state()  # Persist the idempotency key before any paid request can start.
            queued = post(client, path, body, state[key_field])
            state[request_field] = queued["id"]
            save_state()
            transcript_after = wait_request(
                client, conversation_id, queued["id"], timeout
            )
            if transcript_after["last_request_status"] != "COMPLETED":
                raise RuntimeError(f"{name} advisor exchange did not complete")
            completed = request_messages(transcript_after, queued["id"])
            if len(completed) != expected_messages:
                raise RuntimeError(
                    f"{name} exchange persisted {len(completed)} of {expected_messages} expected advisor replies"
                )
            return transcript_after, completed

        transcript, direct_messages = stage(
            "direct",
            f"/api/v1/conversations/{conversation_id}/messages",
            {
                "content": "Explain how this experiment changes the same-policy comparison. Cite the frozen assumptions and result, and flag any unsupported conclusion."
            },
            expected_messages=1,
            worst_case_requests=2,
        )

        transcript, invited_messages = stage(
            "invite",
            f"/api/v1/conversations/{conversation_id}/invite",
            {
                "advisor": "ravi",
                "question": "Challenge Mei's delivery interpretation, using this exact scenario snapshot and replying to her point.",
                "reply_to": direct_messages[-1]["id"],
            },
            expected_messages=2,
            worst_case_requests=3,
        )
        if invited_messages[0]["reply_to"] != direct_messages[-1]["id"]:
            raise RuntimeError("Invited advisor did not reply to the selected point")
        if invited_messages[1]["reply_to"] != invited_messages[0]["id"]:
            raise RuntimeError("Original advisor did not challenge the invited reply")

        transcript, council_messages = stage(
            "council",
            f"/api/v1/conversations/{conversation_id}/council",
            {
                "question": "Convene the council on this frozen experiment. Compare Lean, Balanced, and Resilient consequences, retain disagreements, and let Idris conclude.",
                "reply_to": invited_messages[-1]["id"],
            },
            expected_messages=8,
            worst_case_requests=10,
        )
        if len(council_messages) != 8 or not council_messages[-1].get("critic_conclusion"):
            raise RuntimeError("Council transcript is missing bounded turns or critic conclusion")

        events_response = client.get(f"/api/v1/conversations/{conversation_id}/events")
        events_response.raise_for_status()
        events = events_response.json()["events"]
        request_count = sum(
            event["event_type"] == "inference_request_reserved" for event in events
        )
        if request_count > 16:
            raise RuntimeError("Conversation trial exceeded the sixteen-request aggregate ceiling")
        replay_response = client.get(f"/api/v1/conversations/{conversation_id}/replay")
        replay_response.raise_for_status()
        replay = replay_response.json()
        if replay.get("inference_triggered") is not False or replay.get("transcript_mode") != "replay":
            raise RuntimeError("Stored replay is not visibly read-only")

        validation_states = sorted(
            {
                message["validation_status"]
                for message in transcript["messages"]
                if message.get("speaker") == "advisor"
            }
        )
        state.update(
            url=base_url,
            cookie=session_cookie(client.cookies),
            scenario_id=scenario["id"],
            conversation_id=conversation_id,
            conversation_snapshot_hash=transcript["snapshot_ref"]["hash"],
            conversation_messages_hash=digest(transcript["messages"]),
            conversation_message_count=len(transcript["messages"]),
            conversation_trial_completed=True,
        )
        save_state()
        return {
            "status": "PASS",
            "base_url": base_url,
            "scenario_id": scenario["id"],
            "conversation_id": conversation_id,
            "snapshot_hash": transcript["snapshot_ref"]["hash"],
            "actual_inference_requests": request_count,
            "maximum_permitted_requests": 16,
            "advisor_messages": 11,
            "validation_states": validation_states,
            "favourable_recommendation_required": False,
            "replay_inference_triggered": replay["inference_triggered"],
            "private_state_updated": bool(state_path),
            "preserved_failed_requests": sum(key.endswith('_release_retry') for key in state),
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="https://farmtact.fly.dev")
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument(
        "--state",
        type=Path,
        default=Path("/tmp/farmtact-deepseek-conversation-trial.json"),
        help="Private 0600 session-state file to reuse and update for persistence verification.",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="Required acknowledgement that the deployed server may make billable DeepSeek calls.",
    )
    parser.add_argument('--retry-failed', action='store_true', help='After a reviewed fix, retry an empty failed stage once while retaining its failures and the aggregate request ceiling.')
    args = parser.parse_args()
    if not args.live:
        parser.error("Pass --live to run the deployed billable conversation trial")
    print(
        json.dumps(
            run(args.base_url, args.timeout, args.state, args.retry_failed), indent=2, sort_keys=True
        )
    )


if __name__ == "__main__":
    main()
