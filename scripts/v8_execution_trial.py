#!/usr/bin/env python3
"""Restart-safe, zero-inference HTTP trial for a 56-day synthetic world.

Run ``--phase start``, restart the service, then run ``--phase finish`` with
the same private state path.  ``--phase all`` performs both stages without a
restart.  The state contains the session cookie and is always written mode 0600.
"""
from __future__ import annotations

import argparse
from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import hashlib
import json
import os
from pathlib import Path
import time
import uuid
from urllib.parse import urlsplit

import httpx


SCHEMA_VERSION = "farmtact-v8-execution-trial-1.0.0"
TERMINAL_RUNS = {
    "ACCEPTED_FOR_SIMULATION",
    "NO_FEASIBLE_PLAN",
    "REVIEW_WITHHELD",
    "FAILED",
    "CANCELLED",
    "STALE_INPUT",
}


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def write_private(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as target:
        json.dump(value, target, sort_keys=True)
    path.chmod(0o600)


def write_report(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def cookie_name(url: str) -> str:
    edition = urlsplit(url).path.strip("/")
    return f"farmtact_{edition}_session" if edition.startswith("v") and edition[1:].isdigit() else "farmtact_session"


def cookie_value(cookies: httpx.Cookies, name: str) -> str | None:
    return next((cookie.value for cookie in cookies.jar if cookie.name == name), None)


def rounded_cents(value: Decimal) -> Decimal:
    return value.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)


def run(args) -> dict:
    state_path = Path(args.state)
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    if not isinstance(state, dict):
        raise ValueError("Private execution state must contain a JSON object")
    saved_url = state.get("url")
    if saved_url and args.url.rstrip("/") != str(saved_url).rstrip("/"):
        raise ValueError("--url does not match the private execution state")
    url = str(saved_url or args.url).rstrip("/")
    state.setdefault("schema_version", SCHEMA_VERSION)
    if state["schema_version"] != SCHEMA_VERSION:
        raise ValueError("Private execution state has an incompatible schema version")
    state.setdefault("url", url)
    state.setdefault("prefix", f"v8-execution-{uuid.uuid4().hex}")
    state.setdefault("keys", {})
    write_private(state_path, state)

    name = cookie_name(url)
    with httpx.Client(base_url=url, timeout=args.timeout, follow_redirects=False) as client:
        if state.get("cookie"):
            client.cookies.set(name, state["cookie"])

        def checked(response: httpx.Response) -> dict:
            response.raise_for_status()
            return response.json()

        def get(path: str, **kwargs) -> dict:
            return checked(client.get("/api/v1" + path, **kwargs))

        def mutation(step: str, path: str, body: dict) -> dict:
            saved = state["keys"].setdefault(
                step,
                {"key": f"{state['prefix']}-{step}", "body": body},
            )
            if saved["body"] != body:
                raise RuntimeError(f"Saved {step} inputs differ from the requested inputs")
            write_private(state_path, state)
            return checked(
                client.post(
                    "/api/v1" + path,
                    json=saved["body"],
                    headers={"Idempotency-Key": saved["key"]},
                )
            )

        bootstrap = get("/bootstrap")
        if urlsplit(url).hostname in {"127.0.0.1", "localhost"}:
            for cookie in client.cookies.jar:
                cookie.secure = False
        state["cookie"] = cookie_value(client.cookies, name)
        if not state["cookie"]:
            raise RuntimeError("Bootstrap did not establish a development session")
        write_private(state_path, state)

        def await_run(run_id: str) -> dict:
            deadline = time.monotonic() + args.run_timeout
            while True:
                current = get(f"/planning-runs/{run_id}")
                if current["status"] in TERMINAL_RUNS:
                    return current
                if time.monotonic() >= deadline:
                    raise TimeoutError("Zero-AI planning mission exceeded the trial deadline")
                time.sleep(0.5)

        def read_all_events(world_id: str) -> list[dict]:
            rows = []
            cursor = 0
            while True:
                page = get(
                    f"/simulations/{world_id}/events",
                    params={"after": cursor, "limit": 200},
                )
                if page.get("inference_triggered") is not False:
                    raise RuntimeError("Execution event read did not declare zero inference")
                rows.extend(page["events"])
                if page["next_cursor"] is None:
                    return rows
                cursor = page["next_cursor"]

        if args.phase in {"start", "all"}:
            mission = mutation("mission", "/planning-runs", {"council": False})
            state["run_id"] = mission["id"]
            write_private(state_path, state)
            planning_run = await_run(state["run_id"])
            if planning_run["status"] != "ACCEPTED_FOR_SIMULATION":
                raise RuntimeError(f"Numerical mission ended as {planning_run['status']}")
            if planning_run.get("council_requested") is not False or planning_run.get("council_status") != "not_run":
                raise RuntimeError("Trial mission was not a zero-council numerical run")
            if planning_run.get("inference_audit") not in (None, []):
                raise RuntimeError("Zero-council mission contains inference audit records")
            if any(event.get("event_type") == "inference_request_reserved" for event in planning_run["events"]):
                raise RuntimeError("Zero-council mission reserved provider inference")
            state["run_read_hash"] = digest(planning_run)

            world = mutation("create-world", "/simulations", {"run_id": state["run_id"]})
            state["world_id"] = world["id"]
            if (date.fromisoformat(world["end_date"]) - date.fromisoformat(world["start_date"])).days + 1 != 56:
                raise RuntimeError("Trial requires the 56-day synthetic fixture horizon")
            first_body = {"revision": world["revision"], "days": 7}
            advanced = mutation(
                "advance-7",
                f"/simulations/{state['world_id']}/advance",
                first_body,
            )
            if advanced["days_executed"] != 7:
                raise RuntimeError("Initial execution segment did not close seven days")
            state["first_advance"] = advanced
            state["completed_before_replan"] = list(advanced["completed_task_ids"])
            write_private(state_path, state)
            replanned = mutation(
                "replan",
                f"/simulations/{state['world_id']}/replan",
                {"revision": advanced["revision"]},
            )
            if replanned["days_executed"] != 7 or replanned["clock_date"] != advanced["clock_date"]:
                raise RuntimeError("Replanning changed the executed clock")
            if replanned["inventory"] != advanced["inventory"] or replanned["cash_sgd"] != advanced["cash_sgd"]:
                raise RuntimeError("Replanning changed realized stock or cash")
            if not set(advanced["completed_task_ids"]).issubset(replanned["completed_task_ids"]):
                raise RuntimeError("Replanning lost completed task history")
            state["phase"] = "STARTED_AND_REPLANNED"
            write_private(state_path, state)
            if args.phase == "start":
                return {
                    "status": "READY_FOR_RESTART",
                    "phase": state["phase"],
                    "run_id": state["run_id"],
                    "world_id": state["world_id"],
                    "days_executed": replanned["days_executed"],
                    "provider_calls": 0,
                }

        if args.phase in {"finish", "all"}:
            if state.get("phase") not in {"STARTED_AND_REPLANNED", "COMPLETED"}:
                raise RuntimeError("Run --phase start successfully before --phase finish")
            world = get(f"/simulations/{state['world_id']}")
            for index, days in enumerate((14, 14, 14, 7), start=1):
                step = f"finish-{index}"
                saved = state["keys"].get(step)
                if saved is not None:
                    receipt = mutation(
                        step,
                        f"/simulations/{state['world_id']}/advance",
                        saved["body"],
                    )
                    world = get(f"/simulations/{state['world_id']}")
                    if world["days_executed"] < receipt["days_executed"]:
                        raise RuntimeError("Stored advance receipt is ahead of the durable world")
                    continue
                if world["days_executed"] >= 56:
                    break
                remaining = 56 - world["days_executed"]
                step_days = min(days, remaining)
                world = mutation(
                    step,
                    f"/simulations/{state['world_id']}/advance",
                    {"revision": world["revision"], "days": step_days},
                )
                write_private(state_path, state)
            if world["status"] != "COMPLETED" or world["days_executed"] != 56:
                raise RuntimeError("Execution world did not complete exactly 56 days")

            events = read_all_events(state["world_id"])
            closed = [event for event in events if event["type"] == "day_closed"]
            serviced = [event for event in events if event["type"] == "demand_serviced"]
            tasks = [event for event in events if event["type"] == "task_completed"]
            replans = [event for event in events if event["type"] == "future_replanned"]
            if len(closed) != 56 or len({event["date"] for event in closed}) != 56:
                raise RuntimeError("Execution did not record one closing event per civil day")
            expected_dates = [str(date.fromordinal(date.fromisoformat(world["start_date"]).toordinal() + offset)) for offset in range(56)]
            if [event["date"] for event in closed] != expected_dates:
                raise RuntimeError("Execution closing dates are not a contiguous 56-day clock")
            if len(replans) != 1:
                raise RuntimeError("Trial expected exactly one stored future replan")
            if len({event["task_id"] for event in tasks}) != len(tasks):
                raise RuntimeError("An executed task was replayed more than once")
            if not set(state["completed_before_replan"]).issubset(world["completed_task_ids"]):
                raise RuntimeError("A completed pre-replan action disappeared")

            service_by_day: dict[str, list[dict]] = {}
            for event in serviced:
                service_by_day.setdefault(event["date"], []).append(event)
                requested = Decimal(str(event["requested_kg"]))
                delivered = Decimal(str(event["delivered_kg"]))
                shortfall = Decimal(str(event["shortfall_kg"]))
                lot_total = sum(
                    (Decimal(str(item["quantity_kg"])) for item in event["lot_allocations"]),
                    Decimal(0),
                )
                if requested != delivered + shortfall or delivered != lot_total:
                    raise RuntimeError("Order or lot allocation mass does not reconcile")

            revenue_exact = Decimal(0)
            cost_exact = Decimal(0)
            previous_closing = None
            for event in closed:
                ledger = event["ledger"]
                opening = Decimal(str(ledger["opening_kg"]))
                harvest = Decimal(str(ledger["harvest_kg"]))
                delivered = Decimal(str(ledger["delivered_kg"]))
                disposed = Decimal(str(ledger["disposed_kg"]))
                closing = Decimal(str(ledger["closing_kg"]))
                if opening + harvest - delivered - disposed != closing:
                    raise RuntimeError(f"Mass conservation failed on {event['date']}")
                if previous_closing is not None and opening != previous_closing:
                    raise RuntimeError(f"Inventory continuity failed on {event['date']}")
                previous_closing = closing
                closing_lots = sum(
                    (Decimal(str(item["quantity_kg"])) for item in event["closing_lots"]),
                    Decimal(0),
                )
                if closing_lots != closing:
                    raise RuntimeError(f"Closing lots do not reconcile on {event['date']}")
                daily_services = service_by_day.get(event["date"], [])
                if sum((Decimal(str(item["requested_kg"])) for item in daily_services), Decimal(0)) != Decimal(str(ledger["demand_kg"])):
                    raise RuntimeError(f"Order demand does not reconcile on {event['date']}")
                if sum((Decimal(str(item["delivered_kg"])) for item in daily_services), Decimal(0)) != delivered:
                    raise RuntimeError(f"Order deliveries do not reconcile on {event['date']}")
                for item in daily_services:
                    if item["price_sgd_per_kg"] is not None:
                        revenue_exact += Decimal(str(item["delivered_kg"])) * Decimal(str(item["price_sgd_per_kg"]))
                cost_exact += sum((Decimal(str(value)) for value in ledger["cost_components"].values()), Decimal(0))

            if rounded_cents(revenue_exact) != Decimal(str(world["revenue_sgd"])):
                raise RuntimeError("Cumulative revenue does not reconcile")
            if rounded_cents(cost_exact) != Decimal(str(world["cost_sgd"])):
                raise RuntimeError("Cumulative cost does not reconcile")
            expected_cash = rounded_cents(
                Decimal(str(world["opening_cash_sgd"])) + revenue_exact - cost_exact
            )
            if expected_cash != Decimal(str(world["cash_sgd"])):
                raise RuntimeError("Cumulative cash does not reconcile")
            if sum((Decimal(str(item["quantity_kg"])) for item in world["inventory"]), Decimal(0)) != previous_closing:
                raise RuntimeError("Terminal world inventory differs from the final closing lots")

            current_before_replay = get(f"/simulations/{state['world_id']}")
            old = state["keys"]["advance-7"]
            replay = checked(
                client.post(
                    f"/api/v1/simulations/{state['world_id']}/advance",
                    json=old["body"],
                    headers={"Idempotency-Key": old["key"]},
                )
            )
            if replay != state["first_advance"]:
                raise RuntimeError("Historical action receipt did not replay exactly")
            if get(f"/simulations/{state['world_id']}") != current_before_replay:
                raise RuntimeError("Historical receipt replay mutated the current world")

            run_before_gets = get(f"/planning-runs/{state['run_id']}")
            event_sequence = world["event_sequence"]
            for _ in range(3):
                read = get(f"/simulations/{state['world_id']}")
                if read.get("inference_triggered") is not False:
                    raise RuntimeError("World GET did not declare zero inference")
                read_all_events(state["world_id"])
                get("/bootstrap")
            run_after_gets = get(f"/planning-runs/{state['run_id']}")
            final_world = get(f"/simulations/{state['world_id']}")
            if digest(run_after_gets) != digest(run_before_gets):
                raise RuntimeError("GET requests changed the numerical mission or inference audit")
            if final_world["event_sequence"] != event_sequence:
                raise RuntimeError("GET requests appended execution events")
            if run_after_gets.get("inference_audit") not in (None, []) or any(
                event.get("event_type") == "inference_request_reserved"
                for event in run_after_gets["events"]
            ):
                raise RuntimeError("Trial observed an inference request")

            state["phase"] = "COMPLETED"
            state["world_hash"] = digest(final_world)
            write_private(state_path, state)
            return {
                "schema_version": SCHEMA_VERSION,
                "status": "PASS",
                "actual_application_http": True,
                "simulation_only": True,
                "provider_calls": 0,
                "run_id": state["run_id"],
                "world_id": state["world_id"],
                "days_executed": 56,
                "day_closed_events": len(closed),
                "task_events": len(tasks),
                "demand_service_events": len(serviced),
                "future_replans": len(replans),
                "mass_conservation": "PASS",
                "cash_conservation": "PASS",
                "order_lot_conservation": "PASS",
                "historical_action_replay": "PASS",
                "restart_persistence": "PASS" if args.phase == "finish" else "NOT_EXERCISED_IN_ALL_PHASE",
                "get_inference_calls": 0,
                "world_hash": state["world_hash"],
            }
    raise AssertionError("unreachable")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--state", default="/tmp/farmtact-v8-execution-state.json")
    parser.add_argument("--phase", choices=("start", "finish", "all"), required=True)
    parser.add_argument("--report", default="reports/v8/execution-trial.json")
    parser.add_argument("--timeout", type=float, default=180)
    parser.add_argument("--run-timeout", type=float, default=240)
    args = parser.parse_args()
    result = run(args)
    if result["status"] == "PASS":
        write_report(Path(args.report), result)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["status"] in {"PASS", "READY_FOR_RESTART"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
