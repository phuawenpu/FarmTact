from types import SimpleNamespace

from packages.agents import ROLES
from runtime.deepseek_gateway import SafeAudit, Usage
from services.api import council as council_module


class FakeGateway:
    def __init__(self, calls):
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return None

    def chat_json(self, role, messages, output_model, **kwargs):
        self.calls.append((role, messages, kwargs))
        data = output_model.model_validate(
            {
                "claim_type": "observation",
                "statement": "The frozen comparison supports this role-specific finding.",
                "evidence_ids": [],
                "tool_result_refs": ["forecast:cutoff"],
                "recommendation": "proceed_simulation",
            }
        )
        usage = Usage(prompt_tokens=1, completion_tokens=1, total_tokens=2)
        audit = SafeAudit(
            provider="deepseek",
            requested_model="deepseek-v4-flash",
            returned_model="deepseek-v4-flash",
            role=role,
            capability="text",
            execution_mode="test",
            data_mode="synthetic_demo",
            inference_origin="deepseek_api",
            input_sha256="a" * 64,
            request_id="fixture",
            latency_ms=1,
            usage=usage,
        )
        return SimpleNamespace(data=data, audit=audit, model="deepseek-v4-flash", usage=usage)


def test_council_runs_six_specialists_then_planner_with_frozen_market_context(monkeypatch):
    calls = []
    monkeypatch.setattr(
        council_module.DeepSeekGateway,
        "from_config",
        lambda *_, **__: FakeGateway(calls),
    )
    market = {
        "status": "not_connected",
        "connected_social_feeds": False,
        "summary": "No community evidence source is connected.",
        "observations": [],
    }
    computed = {
        "input_hash": "frozen-input",
        "forecast": {"cutoff": "2026-09-09T00:00:00Z", "uncertainty": {}},
        "strategies": [
            {
                "id": "balanced",
                "name": "Balanced",
                "metrics": {"margin_sgd": 10.0},
                "violations": [],
                "risk": "bounded",
                "status": "FEASIBLE",
                "assumptions": [],
            }
        ],
    }

    claims, audits = council_module.council(
        computed,
        "run-seven",
        lambda *_: None,
        market_signals=market,
    )

    assert [role for role, _, _ in calls] == ROLES
    assert len(claims) == len(audits) == 7
    assert all(call[2]["max_tokens"] == 1_536 for call in calls)
    for role, messages, _ in calls[:-1]:
        assert role != "planning_chair"
        assert '"prior_claims": []' in messages[1]["content"]
    planner_context = calls[-1][1][1]["content"]
    assert '"prior_claims": [' in planner_context
    assert '"market:signals": {"status": "not_connected"' in planner_context

