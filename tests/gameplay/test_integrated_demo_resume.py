import json
from pathlib import Path
import stat

import httpx

from scripts import integrated_demo


class DemoServer:
    def __init__(self, failure):
        self.failure = failure
        self.mission_id = "b451-recovered-mission"
        self.receipt_key = None
        self.mission_posts = []
        self.import_posts = []
        self.paid_missions = 0
        self.lost = False

    @property
    def strategies(self):
        return [{"id": "balanced", "name": "Balanced"}]

    def response(self, request):
        path = request.url.path
        if request.method == "GET" and path == "/api/v1/bootstrap":
            return httpx.Response(
                200,
                json={
                    "capabilities": {},
                    "sources": [{"status": "validated"}],
                    "crops": [{} for _ in range(12)],
                },
                headers={"set-cookie": "farmtact_session=private-test-cookie; Path=/"},
            )
        if request.method == "POST" and path == "/api/v1/imports":
            self.import_posts.append(request.headers["Idempotency-Key"])
            return httpx.Response(201, json={"fixture": "synthetic_demo", "version": 2})
        if request.method == "POST" and path == "/api/v1/planning-runs":
            key = request.headers["Idempotency-Key"]
            self.mission_posts.append(key)
            if self.receipt_key is None:
                self.receipt_key = key
                self.paid_missions += 1
                if self.failure == "lost_response" and not self.lost:
                    self.lost = True
                    raise httpx.ReadError("response lost after commit", request=request)
            assert key == self.receipt_key
            if self.failure == "duplicate_429" and len(self.mission_posts) == 2:
                return httpx.Response(429, json={"detail": "request admission limit"})
            return httpx.Response(202, json={"id": self.mission_id, "status": "CREATED"})
        if request.method == "GET" and path == f"/api/v1/planning-runs/{self.mission_id}":
            return httpx.Response(
                200,
                json={
                    "id": self.mission_id,
                    "status": "ACCEPTED_FOR_SIMULATION",
                    "strategies": self.strategies,
                    "events": [{"event_type": "run_completed"}],
                    "council_status": "not_run",
                    "warnings": [],
                },
            )
        if request.method == "GET" and path == f"/api/v1/planning-runs/{self.mission_id}/replay":
            return httpx.Response(
                200,
                json={
                    "execution_mode": "replay",
                    "strategies": self.strategies,
                    "events": [{"event_type": "run_completed"}],
                },
            )
        return httpx.Response(404, json={"detail": f"unhandled {request.method} {path}"})


def arguments(tmp_path):
    return integrated_demo._parse_args(
        [
            "--url",
            "https://farm.example",
            "--report",
            str(tmp_path / "report.json"),
            "--browser-state",
            str(tmp_path / "browser.json"),
            "--state",
            str(tmp_path / "trial.json"),
        ]
    )


def factory(server):
    transport = httpx.MockTransport(server.response)
    return lambda **kwargs: httpx.Client(transport=transport, **kwargs)


def test_lost_mission_post_response_resumes_with_the_same_receipt_key(tmp_path):
    server = DemoServer("lost_response")
    args = arguments(tmp_path)

    assert integrated_demo.run(args, client_factory=factory(server)) == 1
    state = json.loads(args.state.read_text())
    stable_key = state["keys"]["mission"]
    assert "mission_run_id" not in state["ids"]
    assert server.paid_missions == 1

    assert integrated_demo.run(args, client_factory=factory(server)) == 0
    state = json.loads(args.state.read_text())
    assert state["ids"]["mission_run_id"] == server.mission_id
    assert state["mission_receipt_verified"] is True
    assert server.mission_posts == [stable_key, stable_key, stable_key]
    assert server.paid_missions == 1
    assert len(server.import_posts) == 1
    assert stat.S_IMODE(args.state.stat().st_mode) == 0o600
    assert stat.S_IMODE(args.browser_state.stat().st_mode) == 0o600
    assert json.loads(Path(args.report).read_text())["status"] == "PASS"


def test_duplicate_verification_429_preserves_id_and_resumes_by_get(tmp_path):
    server = DemoServer("duplicate_429")
    args = arguments(tmp_path)

    assert integrated_demo.run(args, client_factory=factory(server)) == 1
    first_report = json.loads(Path(args.report).read_text())
    state = json.loads(args.state.read_text())
    assert first_report["run_id"] == server.mission_id
    assert first_report["error"] == {
        "operation": "planning receipt verification",
        "message": "planning receipt verification returned HTTP 429; no new key or automatic retry was generated.",
        "http_status": 429,
    }
    assert state["ids"]["mission_run_id"] == server.mission_id
    posts_before_resume = list(server.mission_posts)
    assert server.paid_missions == 1

    assert integrated_demo.run(args, client_factory=factory(server)) == 0
    state = json.loads(args.state.read_text())
    assert server.mission_posts == posts_before_resume
    assert server.paid_missions == 1
    assert state["mission_recovered_by_get"] is True
    assert json.loads(Path(args.report).read_text())["status"] == "PASS"
