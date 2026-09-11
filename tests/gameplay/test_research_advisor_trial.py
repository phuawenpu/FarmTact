import json

import httpx
import pytest

from scripts import research_advisor_trial as trial


class Response:
    def __init__(self, payload):
        self.payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self.payload


@pytest.mark.parametrize(
    ("validation_status", "expected_status"),
    [("references_verified", "PASS"), ("unsupported", "FAIL")],
)
def test_research_trial_reuses_private_session_and_is_restart_safe(
    tmp_path, monkeypatch, validation_status, expected_status
):
    farm = {"id": "unchanged-main-farm"}
    study = {"id": "research-private", "revision": 0, "input_version": 1, "results": []}
    conversation = None
    posts = []
    receipts = {}

    class Client:
        def __init__(self, **_):
            self.cookies = httpx.Cookies()

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return None

        def get(self, path):
            if path == "/api/v1/bootstrap":
                self.cookies.set("farmtact_session", "same-private-session")
                return Response({"farm": farm})
            if path == "/api/v1/council-research/research-private":
                return Response(study)
            if path == "/api/v1/conversations/conversation-private":
                return Response(conversation)
            if path == "/api/v1/conversations/conversation-private/events":
                return Response(
                    {
                        "events": [
                            {
                                "event_type": "inference_request_reserved",
                                "request_id": "request-private",
                            }
                        ]
                    }
                )
            if path == "/api/v1/conversations/conversation-private/replay":
                return Response({"inference_triggered": False})
            raise AssertionError(path)

        def post(self, path, json, headers):
            nonlocal conversation
            key = headers["Idempotency-Key"]
            posts.append((path, key))
            if key in receipts:
                return Response(receipts[key])
            if path == "/api/v1/council-research":
                payload = dict(study)
            elif path.endswith("/actions"):
                study["revision"] += 1
                if json["action"] == "apply":
                    study["input_version"] += 1
                if json["action"] == "run":
                    study["results"] = [
                        {
                            "version": study["input_version"],
                            "status": "COMPLETED",
                            "input_hash": "frozen-hash",
                        }
                    ]
                payload = dict(study)
            elif path == "/api/v1/conversations":
                payload = {"id": "conversation-private", "status": "OPEN"}
                conversation = {
                    "id": "conversation-private",
                    "last_request_id": None,
                    "last_request_status": None,
                    "snapshot_ref": {
                        "id": "research-private",
                        "hash": "frozen-hash",
                        "version": study["input_version"],
                    },
                    "tool_results": {"research:version": study["input_version"]},
                    "messages": [],
                }
            elif path.endswith("/messages"):
                payload = {"id": "request-private", "status": "QUEUED"}
                conversation.update(
                    last_request_id="request-private",
                    last_request_status="COMPLETED",
                    messages=[
                        {
                            "speaker": "advisor",
                            "request_id": "request-private",
                            "validation_status": validation_status,
                        }
                    ],
                )
            else:
                raise AssertionError(path)
            receipts[key] = payload
            return Response(payload)

    monkeypatch.setattr(trial.httpx, "Client", Client)
    state_path = tmp_path / "shared-private-state.json"
    state_path.write_text(
        json.dumps(
            {
                "url": "http://127.0.0.1:8080",
                "cookie": "same-private-session",
                "conversation_id": "main-conversation-private",
            }
        )
    )
    report_path = tmp_path / "report.json"
    ledger_path = tmp_path / "ledger.json"

    first = trial.run(None, report_path, ledger_path, state_path, timeout=1)
    first_posts = list(posts)
    resumed = trial.run(None, report_path, ledger_path, state_path, timeout=1)

    assert first["status"] == resumed["status"] == expected_status
    assert first["actual_provider_calls"] == 1
    assert posts == first_posts
    state = json.loads(state_path.read_text())
    assert state["conversation_id"] == "main-conversation-private"
    assert state["research_session_id"] == "research-private"
    assert state["research_conversation_id"] == "conversation-private"
    assert state["research_request_id"] == "request-private"
    assert state_path.stat().st_mode & 0o777 == 0o600
    public_report = json.loads(report_path.read_text())
    assert "research_session_id" not in public_report
    assert "research_conversation_id" not in public_report
    ledger = json.loads(ledger_path.read_text())
    assert ledger["maximum_provider_calls_per_run"] == 2
    assert ledger["runs"][0]["actual_provider_calls"] == 1
