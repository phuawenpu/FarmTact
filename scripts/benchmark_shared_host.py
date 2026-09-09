"""Bounded shared-host numerical capacity benchmark for immutable FarmTact editions.

Creates isolated synthetic sessions and frozen scenario branches only. It never
submits conversations, council work, or provider inference. Cookie material is
kept in memory and, when a cookie audit file is requested, only in a mode-0600
file below /tmp; cookie values are never included in the report.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import threading
import time
from typing import Any

import httpx


TERMINAL = {"COMPLETED", "FAILED", "BLOCKED", "INTERRUPTED"}
MEMINFO_FIELDS = {"MemTotal", "MemFree", "MemAvailable", "Buffers", "Cached", "SwapTotal", "SwapFree"}


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(quantile * len(ordered)) - 1)]


def machine_memory(app: str, machine: str) -> dict[str, Any]:
    command = [
        "fly", "ssh", "console", "-a", app, "--machine", machine, "--no-container",
        "-C", "cat /proc/meminfo",
    ]
    started = time.monotonic()
    completed = subprocess.run(command, capture_output=True, text=True, timeout=30, check=False)
    sample: dict[str, Any] = {
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "status": "ok" if completed.returncode == 0 else "error",
    }
    if completed.returncode:
        sample["error"] = f"fly ssh exited {completed.returncode}"
        return sample
    for line in completed.stdout.splitlines():
        if ":" not in line:
            continue
        name, raw = line.split(":", 1)
        if name not in MEMINFO_FIELDS:
            continue
        pieces = raw.split()
        if pieces and pieces[0].isdigit():
            sample[f"{name}_kib"] = int(pieces[0])
    if "MemTotal_kib" not in sample or "MemAvailable_kib" not in sample:
        sample.update(status="error", error="required curated meminfo fields missing")
    else:
        sample["used_excluding_reclaimable_kib"] = sample["MemTotal_kib"] - sample["MemAvailable_kib"]
    return sample


class EditionSession:
    def __init__(self, host: str, edition: str, latency_rows: list[dict[str, Any]], latency_lock: threading.Lock):
        self.host = host.rstrip("/") + "/"
        self.edition = edition
        self.base = f"{self.host}{edition}/api/v1/"
        self.client = httpx.Client(base_url=self.base, timeout=35, follow_redirects=False)
        self.latency_rows = latency_rows
        self.latency_lock = latency_lock

    def close(self) -> None:
        self.client.close()

    def sync_auth_header(self) -> None:
        cookie = next((item for item in self.client.cookies.jar if item.name == f"farmtact_{self.edition}_session"), None)
        if cookie:
            # The private relay uses HTTP while the edition gateway correctly sets
            # production cookies Secure. Supply the same cookie explicitly only to
            # this loopback benchmark client.
            self.client.headers["Cookie"] = f"{cookie.name}={cookie.value}"

    def request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        started = time.monotonic()
        response = self.client.request(method, path, **kwargs)
        self.sync_auth_header()
        elapsed = time.monotonic() - started
        with self.latency_lock:
            self.latency_rows.append({
                "edition": self.edition, "endpoint": path.split("?", 1)[0], "method": method,
                "status_code": response.status_code, "elapsed_seconds": round(elapsed, 4),
            })
        return response

    def get_json(self, path: str) -> dict[str, Any]:
        response = self.request("GET", path)
        response.raise_for_status()
        return response.json()

    def post_json(self, path: str, body: dict[str, Any], key: str) -> dict[str, Any]:
        response = self.request("POST", path, json=body, headers={"Idempotency-Key": key})
        response.raise_for_status()
        return response.json()

    def initialize(self) -> tuple[dict[str, Any], str]:
        bootstrap = self.get_json("bootstrap")
        return bootstrap, digest(bootstrap["farm"])

    def load_cookie_audit(self, directory: Path) -> Path:
        path = directory / f"farmtact-shared-capacity-{self.edition}.cookies.json"
        if path.exists():
            if path.stat().st_mode & 0o077:
                raise PermissionError(f"cookie file for {self.edition} is not mode 0600")
            for name, value in json.loads(path.read_text()).items():
                self.client.cookies.set(name, value)
            self.sync_auth_header()
        return path

    def save_cookie_audit(self, path: Path) -> Path:
        cookies = {cookie.name: cookie.value for cookie in self.client.cookies.jar}
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w") as handle:
            json.dump(cookies, handle)
        os.chmod(path, 0o600)
        return path

    def cross_edition_status(self, other_edition: str) -> int:
        cookie = next((item for item in self.client.cookies.jar if item.name == f"farmtact_{self.edition}_session"), None)
        headers = {"Cookie": f"farmtact_{other_edition}_session={cookie.value}"} if cookie else {}
        response = self.client.get(f"{self.host}{other_edition}/api/v1/scenarios", headers=headers)
        return response.status_code


def create_and_run(session: EditionSession, label: str, controls: dict[str, Any]) -> tuple[str, float]:
    snapshot = session.post_json(
        "data-explorer/snapshots",
        {"name": f"Shared capacity {label}", "generator_settings": {"history_multiplier": 1.05}, "forecast_settings": {"alpha": 0.7}},
        f"shared-capacity-{label}-dataset",
    )
    scenario = session.post_json(
        "scenarios",
        {"name": f"Shared capacity {label}", "explorer_snapshot_id": snapshot["id"], "controls": controls},
        f"shared-capacity-{label}-scenario",
    )
    started = time.monotonic()
    if scenario["status"] == "DRAFT":
        session.post_json(f"scenarios/{scenario['id']}/run", {}, f"shared-capacity-{label}-run")
    return scenario["id"], started


def poll(session: EditionSession, scenario_id: str, started: float, timeout_seconds: int = 180) -> dict[str, Any]:
    deadline = started + timeout_seconds
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        latest = session.get_json(f"scenarios/{scenario_id}")
        if latest.get("status") in TERMINAL:
            elapsed = time.monotonic() - started
            return {
                "scenario_id": scenario_id, "status": latest.get("status"),
                "simulation_status": latest.get("simulation_status"),
                "inference_calls": latest.get("inference_calls"),
                "elapsed_seconds": round(elapsed, 3), "terminal_under_180_seconds": elapsed < timeout_seconds,
                "strategy_statuses": [row.get("status") for row in (latest.get("result") or {}).get("strategies", [])],
            }
        time.sleep(1)
    return {
        "scenario_id": scenario_id, "status": "TIMEOUT", "simulation_status": latest.get("simulation_status"),
        "inference_calls": latest.get("inference_calls"), "elapsed_seconds": round(time.monotonic() - started, 3),
        "terminal_under_180_seconds": False, "strategy_statuses": [],
    }


def sample_browsing(sessions: list[EditionSession]) -> None:
    for session in sessions:
        for endpoint in ("health", "bootstrap", "news"):
            try:
                session.get_json(endpoint)
            except Exception:
                # Status and latency were already recorded. Job polling must continue.
                pass


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8088/")
    parser.add_argument("--report", default="reports/v6/shared_capacity.json")
    parser.add_argument("--cookie-dir", default="/tmp")
    parser.add_argument("--fly-app", default="farmtact")
    parser.add_argument("--machine", default="2871575b4544d8")
    parser.add_argument("--remove-cookies", action="store_true", help="Delete private /tmp cookie files after the run")
    args = parser.parse_args()
    report: dict[str, Any] = {
        "status": "RUNNING", "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "target": "private root-owned local tunnel", "editions": ["v4", "v5"], "provider_calls_requested": 0,
        "policy": "Synthetic frozen scenarios only; council and inference disabled; no farm acceptance or operations.",
        "jobs": [], "browse_samples": [], "memory_samples": {}, "checks": [],
    }
    latency_rows: list[dict[str, Any]] = []
    lock = threading.Lock()
    sessions: list[EditionSession] = []
    cookie_paths: list[Path] = []
    try:
        report["memory_samples"]["before"] = machine_memory(args.fly_app, args.machine)
        sequential = EditionSession(args.url, "v5", latency_rows, lock)
        sessions.append(sequential)
        sequential_cookie_path = sequential.load_cookie_audit(Path(args.cookie_dir))
        before, before_hash = sequential.initialize()
        cookie_paths.append(sequential.save_cookie_audit(sequential_cookie_path))
        report["checks"].append({"name": "v5 cookie rejected by v4", "pass": sequential.cross_edition_status("v4") == 401})
        scenario_id, started = create_and_run(sequential, "sequential-v5", {"demand_crop_id": "pak_choi", "demand_percent": 120})
        sample_browsing([sequential])
        sequential_result = poll(sequential, scenario_id, started)
        sequential_result["edition"] = "v5"
        sequential_result["phase"] = "sequential"
        report["jobs"].append(sequential_result)
        report["checks"].append({"name": "sequential main farm unchanged", "pass": digest(sequential.get_json("bootstrap")["farm"]) == before_hash})

        overlap_sessions = [EditionSession(args.url, "v4", latency_rows, lock), sequential]
        sessions.extend(overlap_sessions)
        initial = []
        for session in overlap_sessions:
            if session is not sequential:
                cookie_path = session.load_cookie_audit(Path(args.cookie_dir))
            else:
                cookie_path = sequential_cookie_path
            bootstrap, farm_hash = session.initialize()
            initial.append((session, farm_hash))
            if session is not sequential:
                cookie_paths.append(session.save_cookie_audit(cookie_path))
            other = "v5" if session.edition == "v4" else "v4"
            report["checks"].append({"name": f"{session.edition} cookie rejected by {other}", "pass": session.cross_edition_status(other) == 401})

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = []
            for session, _ in initial:
                scenario_id, started = create_and_run(
                    session, f"overlap-{session.edition}",
                    {"demand_crop_id": "caixin", "demand_percent": 120},
                )
                futures.append((session, pool.submit(poll, session, scenario_id, started)))
            time.sleep(0.5)
            report["memory_samples"]["during"] = machine_memory(args.fly_app, args.machine)
            sample_browsing(overlap_sessions)
            for session, future in futures:
                result = future.result(timeout=185)
                result.update(edition=session.edition, phase="overlapping")
                report["jobs"].append(result)

        for session, farm_hash in initial:
            unchanged = digest(session.get_json("bootstrap")["farm"]) == farm_hash
            report["checks"].append({"name": f"{session.edition} overlapping main farm unchanged", "pass": unchanged})
        report["memory_samples"]["after"] = machine_memory(args.fly_app, args.machine)

        report["browse_samples"] = latency_rows
        browsing = [row["elapsed_seconds"] for row in latency_rows if row["method"] == "GET" and row["endpoint"] in {"health", "bootstrap", "news"}]
        p95 = percentile(browsing, 0.95)
        report["browsing_p95_seconds"] = round(p95, 4) if p95 is not None else None
        report["checks"].extend([
            {"name": "browsing p95 under 5 seconds", "pass": p95 is not None and p95 < 5},
            {"name": "all jobs terminal under 180 seconds", "pass": all(row["terminal_under_180_seconds"] and row["status"] in TERMINAL for row in report["jobs"])},
            {"name": "zero scenario inference calls", "pass": all(row.get("inference_calls") in (0, None) for row in report["jobs"])},
        ])
        report["status"] = "PASS" if all(row["pass"] for row in report["checks"]) else "FAIL"
    except Exception as error:
        report.update(status="FAIL", error=f"{type(error).__name__}: {error}")
    finally:
        report["browse_samples"] = latency_rows
        if "after" not in report["memory_samples"]:
            report["memory_samples"]["after"] = machine_memory(args.fly_app, args.machine)
        report["finished_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        for session in sessions:
            session.close()
        if args.remove_cookies:
            for path in cookie_paths:
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass
        output = Path(args.report)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, indent=2) + "\n")
        print(f"{report['status']}: {len(report['jobs'])} numerical jobs, {len(latency_rows)} timed requests")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
