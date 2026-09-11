from __future__ import annotations

import base64
import io
import json
import time
from pathlib import Path

import httpx
import pytest
from PIL import Image
from pydantic import BaseModel, ConfigDict

from runtime.deepseek_gateway import (
    DeepSeekBlockedError,
    DeepSeekGateway,
    DeepSeekPolicyError,
    DeepSeekResponseError,
    INTEGER_LIMIT_CEILINGS,
    RunBudget,
    TIME_LIMIT_CEILINGS,
    ToolSpec,
)
from packages.ai_contracts import CONVERSATION_VERSIONS


ROOT = Path(__file__).parents[2]
CONFIG = ROOT / "config/deepseek_runtime.json"


class Probe(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str
    count: int


class Args(BaseModel):
    model_config = ConfigDict(extra="forbid")
    crop_id: str


def completion(
    content: str | None,
    *,
    model: str = "deepseek-flash",
    finish: str = "stop",
    message_extra: dict | None = None,
) -> dict:
    message = {"role": "assistant", "content": content}
    message.update(message_extra or {})
    return {
        "id": "safe-id",
        "model": model,
        "choices": [{"index": 0, "finish_reason": finish, "message": message}],
        "usage": {"prompt_tokens": 8, "completion_tokens": 4, "total_tokens": 12},
    }


def gateway(handler, *, budget: RunBudget | None = None) -> DeepSeekGateway:
    return DeepSeekGateway.from_config(
        CONFIG,
        api_key="unit-test-placeholder",
        budget=budget,
        transport=httpx.MockTransport(handler),
    )


def changed_config(tmp_path: Path, mutate) -> Path:
    raw = json.loads(CONFIG.read_text())
    mutate(raw)
    changed = tmp_path / "runtime.json"
    changed.write_text(json.dumps(raw), encoding="utf-8")
    return changed


def test_chat_json_uses_exact_origin_and_server_route() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == "https://api.deepseek.com/chat/completions"
        assert request.headers["authorization"].startswith("Bearer ")
        body = json.loads(request.content)
        assert body["model"] == "deepseek-flash"
        assert body["thinking"] == {"type": "disabled"}
        assert body["response_format"] == {"type": "json_object"}
        return httpx.Response(200, json=completion('{"status":"ok","count":2}'), headers={"x-request-id": "req-safe"})

    with gateway(handler) as client:
        result = client.chat_json("demand_analyst", [{"role": "user", "content": "Return JSON"}], Probe)
    assert result.data == Probe(status="ok", count=2)
    assert result.audit.provider == "deepseek"
    assert result.audit.request_id == "req-safe"
    assert not hasattr(result, "reasoning_content")
    assert result.audit.contract_versions["validator"]
    assert result.audit.public_context_sha256


def test_caller_supplied_contract_versions_are_preserved() -> None:
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=completion('{"status":"ok","count":2}'))

    with gateway(handler) as client:
        result = client.chat_json(
            "demand_analyst",
            [{"role": "user", "content": "Return JSON"}],
            Probe,
            versions=CONVERSATION_VERSIONS,
            public_context_sha256="b" * 64,
        )
    assert result.audit.contract_versions == CONVERSATION_VERSIONS.public()
    assert result.audit.public_context_sha256 == "b" * 64


def test_cancelled_budget_blocks_before_transport() -> None:
    budget = RunBudget(max_requests=1, max_reserved_output_tokens=512, max_wall_seconds=30)
    budget.cancel()
    with gateway(lambda _: pytest.fail("cancelled work must not transmit"), budget=budget) as client:
        with pytest.raises(DeepSeekBlockedError, match="cancelled"):
            client.chat_json(
                "demand_analyst",
                [{"role": "user", "content": "Return JSON"}],
                Probe,
            )


def test_cancellation_during_response_stops_consumption_without_retry() -> None:
    budget = RunBudget(max_requests=1, max_reserved_output_tokens=512, max_wall_seconds=30)
    calls = 0

    class CancellingStream(httpx.SyncByteStream):
        def __iter__(self):
            yield b'{"id":"partial"'
            budget.cancel()
            yield b'}'

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, stream=CancellingStream())

    with gateway(handler, budget=budget) as client:
        with pytest.raises(DeepSeekBlockedError, match="cancelled"):
            client.chat_json(
                "demand_analyst",
                [{"role": "user", "content": "Return JSON"}],
                Probe,
            )
    assert calls == 1
    assert budget.request_count == 1


def test_manifest_distinguishes_active_product_and_diagnostic_callers() -> None:
    with gateway(lambda _: pytest.fail("manifest inspection makes no request")) as client:
        callers = client.config.callers
    assert callers["mission_council"]["max_requests"] == 9
    assert callers["persistent_conversation"]["integration"] == "active_product"
    assert callers["authenticated_gateway_trial"]["integration"] == "diagnostic_only"
    active_routes = {
        route
        for caller in callers.values()
        if caller["integration"].startswith("active")
        for route in caller["routes"]
    }
    assert "evidence_extractor" not in active_routes


def test_missing_key_is_blocked(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    with pytest.raises(DeepSeekBlockedError, match="credential is unavailable"):
        DeepSeekGateway.from_config(CONFIG)


@pytest.mark.parametrize("role", ["", "prompt_selected_provider", "gpt_evaluator"])
def test_unknown_role_fails_before_transmission(role: str) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    with gateway(handler) as client, pytest.raises(DeepSeekPolicyError, match="Unknown runtime role"):
        client.chat_json(role, [{"role": "user", "content": "x"}], Probe)
    assert calls == 0


def test_config_rejects_endpoint_override(tmp_path: Path) -> None:
    raw = json.loads(CONFIG.read_text())
    raw["origin"] = "https://example.invalid"
    changed = tmp_path / "runtime.json"
    changed.write_text(json.dumps(raw))
    with pytest.raises(DeepSeekPolicyError, match="origin is fixed"):
        DeepSeekGateway.from_config(changed, api_key="unit-test-placeholder")


@pytest.mark.parametrize(
    "mutate",
    [
        lambda raw: raw["routes"]["demand_analyst"].update(model="deepseek-v4-pro"),
        lambda raw: raw["routes"]["demand_analyst"].update(capability="vision"),
        lambda raw: raw["routes"].update(
            extra_reviewer={"model": "deepseek-flash", "capability": "text"}
        ),
        lambda raw: raw["routes"].pop("test_evaluator"),
        lambda raw: raw["routes"]["demand_analyst"].update(note="unreviewed"),
    ],
)
def test_config_rejects_role_manifest_mutation(tmp_path: Path, mutate) -> None:
    changed = changed_config(tmp_path, mutate)
    with pytest.raises(DeepSeekPolicyError, match="route|Role"):
        DeepSeekGateway.from_config(changed, api_key="unit-test-placeholder")


def test_config_rejects_caller_inventory_mutation(tmp_path: Path) -> None:
    changed = changed_config(
        tmp_path,
        lambda raw: raw["callers"]["persistent_conversation"].update(max_requests=10),
    )
    with pytest.raises(DeepSeekPolicyError, match="caller inventory"):
        DeepSeekGateway.from_config(changed, api_key="unit-test-placeholder")


def test_model_migration_is_dated_and_all_routes_use_canonical_model() -> None:
    with gateway(lambda _: pytest.fail("manifest inspection makes no request")) as client:
        assert client.config.allowed_models == {"deepseek-flash"}
        assert {route.model for route in client.config.routes.values()} == {"deepseek-flash"}
        assert client.config.model_migration["reviewed_at"] == "2026-09-11"
        assert client.config.model_migration["discovery_artifact"] == "reports/v8/model-discovery.json"


def test_config_rejects_model_migration_mutation(tmp_path: Path) -> None:
    changed = changed_config(
        tmp_path,
        lambda raw: raw["model_migration"].update(canonical_model="deepseek-v4-pro"),
    )
    with pytest.raises(DeepSeekPolicyError, match="model migration"):
        DeepSeekGateway.from_config(changed, api_key="unit-test-placeholder")


@pytest.mark.parametrize("name,ceiling", sorted(INTEGER_LIMIT_CEILINGS.items()))
def test_config_rejects_integer_limits_above_reviewed_ceiling(
    tmp_path: Path, name: str, ceiling: int
) -> None:
    changed = changed_config(tmp_path, lambda raw: raw["limits"].update({name: ceiling + 1}))
    with pytest.raises(DeepSeekPolicyError, match=name):
        DeepSeekGateway.from_config(changed, api_key="unit-test-placeholder")


@pytest.mark.parametrize("name,ceiling", sorted(TIME_LIMIT_CEILINGS.items()))
def test_config_rejects_time_limits_above_reviewed_ceiling(
    tmp_path: Path, name: str, ceiling: float
) -> None:
    changed = changed_config(tmp_path, lambda raw: raw["limits"].update({name: ceiling + 0.01}))
    with pytest.raises(DeepSeekPolicyError, match=name):
        DeepSeekGateway.from_config(changed, api_key="unit-test-placeholder")


@pytest.mark.parametrize("bad", [0, -1, True, "1"])
def test_config_rejects_nonpositive_or_wrong_type_limit(tmp_path: Path, bad: object) -> None:
    changed = changed_config(tmp_path, lambda raw: raw["limits"].update(max_requests=bad))
    with pytest.raises(DeepSeekPolicyError, match="max_requests"):
        DeepSeekGateway.from_config(changed, api_key="unit-test-placeholder")


@pytest.mark.parametrize(
    "name,value",
    [
        ("development_phase", "production"),
        ("decision_policy", "manual"),
        ("default_execution_mode", "live"),
        ("default_data_mode", "live_advisory"),
    ],
)
def test_config_rejects_mode_policy_mutation(tmp_path: Path, name: str, value: str) -> None:
    changed = changed_config(tmp_path, lambda raw: raw.update({name: value}))
    with pytest.raises(DeepSeekPolicyError, match="mode policy"):
        DeepSeekGateway.from_config(changed, api_key="unit-test-placeholder")


def test_config_allows_only_tighter_limits(tmp_path: Path) -> None:
    def tighten(raw: dict) -> None:
        for name, ceiling in INTEGER_LIMIT_CEILINGS.items():
            raw["limits"][name] = max(1, ceiling // 2)
        for name, ceiling in TIME_LIMIT_CEILINGS.items():
            raw["limits"][name] = ceiling / 2

    changed = changed_config(tmp_path, tighten)
    with DeepSeekGateway.from_config(changed, api_key="unit-test-placeholder") as client:
        assert client.config.limits.max_requests == 8
        assert client.config.limits.max_response_bytes == 2_097_152


def test_run_budget_cannot_exceed_tighter_config(tmp_path: Path) -> None:
    changed = changed_config(tmp_path, lambda raw: raw["limits"].update(max_requests=2))
    with pytest.raises(DeepSeekPolicyError, match="exceeds configured"):
        DeepSeekGateway.from_config(
            changed,
            api_key="unit-test-placeholder",
            budget=RunBudget(max_requests=3),
        )


@pytest.mark.parametrize("max_tokens", [True, 1.5, "2", 0, 4097])
def test_invalid_max_tokens_fails_before_transmission(max_tokens: object) -> None:
    with gateway(lambda _: pytest.fail("must not transmit")) as client:
        with pytest.raises(DeepSeekPolicyError, match="max_tokens"):
            client.chat_json(
                "demand_analyst",
                [{"role": "user", "content": "x"}],
                Probe,
                max_tokens=max_tokens,  # type: ignore[arg-type]
            )


def test_redirect_rejected_without_following() -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(307, headers={"location": "https://example.invalid/steal"})

    with gateway(handler) as client, pytest.raises(DeepSeekPolicyError, match="redirect rejected"):
        client.list_models()
    assert seen == ["https://api.deepseek.com/models"]


@pytest.mark.parametrize("status", [401, 402, 403, 429, 500, 503])
def test_blocking_statuses_are_safe_and_never_fallback(status: int) -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(status, text="sensitive provider body deliberately ignored")

    with gateway(handler) as client, pytest.raises(DeepSeekBlockedError) as caught:
        client.list_models()
    assert calls == 1
    assert "sensitive provider body" not in str(caught.value)


def test_request_and_output_budget_are_reserved_even_on_failure() -> None:
    budget = RunBudget(max_requests=1, max_reserved_output_tokens=4, max_wall_seconds=30)

    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(503)

    with gateway(handler, budget=budget) as client:
        with pytest.raises(DeepSeekBlockedError):
            client.list_models()
        with pytest.raises(DeepSeekBlockedError, match="request budget exhausted"):
            client.list_models()
    assert budget.request_count == 1


def test_output_token_budget_fails_before_transmission() -> None:
    calls = 0
    budget = RunBudget(max_requests=2, max_reserved_output_tokens=8, max_wall_seconds=30)

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(200, json=completion('{"status":"ok","count":1}'))

    with gateway(handler, budget=budget) as client, pytest.raises(DeepSeekBlockedError, match="output-token"):
        client.chat_json("demand_analyst", [{"role": "user", "content": "x"}], Probe, max_tokens=9)
    assert calls == 0


@pytest.mark.parametrize(
    ("execution_mode", "data_mode"),
    [("live", "synthetic_demo"), ("test", "live_advisory"), ("replay", "synthetic_demo")],
)
def test_disallowed_modes_fail_before_transmission(execution_mode: str, data_mode: str) -> None:
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(500)

    with gateway(handler) as client, pytest.raises(DeepSeekPolicyError):
        client.chat_json(
            "demand_analyst",
            [{"role": "user", "content": "x"}],
            Probe,
            execution_mode=execution_mode,
            data_mode=data_mode,
        )
    assert calls == 0


@pytest.mark.parametrize(
    "wire",
    [
        completion(""),
        completion("not-json"),
        completion('{"status":"ok"}'),
        completion('{"status":"ok","count":1}', finish="length"),
        completion('{"status":"ok","count":1}', model="unreviewed-model"),
    ],
)
def test_invalid_or_incomplete_output_is_rejected(wire: dict) -> None:
    with gateway(lambda _: httpx.Response(200, json=wire)) as client, pytest.raises(DeepSeekResponseError):
        client.chat_json("demand_analyst", [{"role": "user", "content": "x"}], Probe)


def test_unexpected_returned_model_is_safe_but_diagnostic() -> None:
    wire = completion('{"status":"ok","count":1}', model="deepseek-v4-flash")
    with gateway(lambda _: httpx.Response(200, json=wire)) as client, pytest.raises(
        DeepSeekResponseError, match=r"returned_model=deepseek-v4-flash"
    ):
        client.chat_json("demand_analyst", [{"role": "user", "content": "x"}], Probe)


def test_malformed_returned_model_is_not_exposed() -> None:
    marker = "provider-private-marker"
    wire = completion('{"status":"ok","count":1}', model=marker + "!")
    with gateway(lambda _: httpx.Response(200, json=wire)) as client, pytest.raises(
        DeepSeekResponseError, match="returned_model=invalid_identifier"
    ) as caught:
        client.chat_json("demand_analyst", [{"role": "user", "content": "x"}], Probe)
    assert marker not in str(caught.value)


def test_tool_round_trip_preserves_private_reasoning_on_wire_only() -> None:
    requests: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        if len(requests) == 1:
            return httpx.Response(
                200,
                json=completion(
                    None,
                    finish="tool_calls",
                    message_extra={
                        "reasoning_content": "private chain must only continue in memory",
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {"name": "get_snapshot", "arguments": '{"crop_id":"caixin"}'},
                            }
                        ],
                    },
                ),
            )
        return httpx.Response(200, json=completion('{"status":"ok","count":7}'))

    tool = ToolSpec("get_snapshot", "Return the validated snapshot", Args)
    with gateway(handler) as client:
        result = client.run_tool_json(
            "demand_analyst",
            [{"role": "user", "content": "Use the tool and return JSON"}],
            [tool],
            lambda name, args: {"count": 7, "crop_id": args.crop_id},
            Probe,
            max_tokens_each=32,
        )
    assistant = requests[1]["messages"][-2]
    assert assistant["reasoning_content"].startswith("private")
    assert requests[1]["messages"][-1]["tool_call_id"] == "call_1"
    assert result.data.count == 7
    assert "private" not in result.content
    assert not hasattr(result.audit, "reasoning_content")


def test_unknown_tool_never_executes() -> None:
    executed = False
    wire = completion(
        None,
        finish="tool_calls",
        message_extra={
            "tool_calls": [{"id": "x", "type": "function", "function": {"name": "shell", "arguments": "{}"}}]
        },
    )

    def execute(_: str, __: BaseModel) -> dict:
        nonlocal executed
        executed = True
        return {}

    with gateway(lambda _: httpx.Response(200, json=wire)) as client, pytest.raises(DeepSeekPolicyError, match="outside the allowlist"):
        client.run_tool_json(
            "demand_analyst", [{"role": "user", "content": "x"}],
            [ToolSpec("get_snapshot", "safe", Args)], execute, Probe,
        )
    assert not executed


def test_invalid_tool_arguments_never_execute() -> None:
    executed = False
    wire = completion(
        None,
        finish="tool_calls",
        message_extra={
            "tool_calls": [{"id": "x", "type": "function", "function": {"name": "get_snapshot", "arguments": "{}"}}]
        },
    )

    def execute(_: str, __: BaseModel) -> dict:
        nonlocal executed
        executed = True
        return {}

    with gateway(lambda _: httpx.Response(200, json=wire)) as client, pytest.raises(DeepSeekResponseError, match="invalid tool arguments"):
        client.run_tool_json(
            "demand_analyst", [{"role": "user", "content": "x"}],
            [ToolSpec("get_snapshot", "safe", Args)], execute, Probe,
        )
    assert not executed


def test_strict_tool_is_rejected() -> None:
    spec = ToolSpec("get_snapshot", "safe", Args)
    wire = spec.wire_schema()
    wire["function"]["strict"] = True
    with gateway(lambda _: pytest.fail("must not transmit")) as client, pytest.raises(DeepSeekPolicyError, match="Strict tools"):
        client._payload(
            client.config.routes["demand_analyst"],
            [{"role": "user", "content": "x"}],
            max_tokens=10,
            thinking="disabled",
            tools=[wire],
        )


def png_bytes(*, size: tuple[int, int] = (40, 20), metadata: bool = False) -> bytes:
    image = Image.new("RGB", size, "white")
    output = io.BytesIO()
    kwargs = {"exif": Image.Exif()} if metadata else {}
    if metadata:
        kwargs["exif"][0x010E] = "private description"
    image.save(output, "PNG", **kwargs)
    return output.getvalue()


def test_image_normalization_strips_metadata_and_uses_inline_png() -> None:
    request_body: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        request_body.update(json.loads(request.content))
        return httpx.Response(
            200,
            json=completion(
                '{"status":"ok","count":1}', model="deepseek-flash"
            ),
        )

    with gateway(handler) as client:
        normalized = client.normalize_image(png_bytes(metadata=True), asset_id="asset-1")
        result = client.vision_json(prompt="Return JSON", images=[normalized], output_model=Probe)
    assert result.data.status == "ok"
    url = request_body["messages"][0]["content"][1]["image_url"]["url"]
    assert url.startswith("data:image/png;base64,")
    decoded = base64.b64decode(url.split(",", 1)[1])
    with Image.open(io.BytesIO(decoded)) as image:
        assert not image.getexif()
        assert "private description" not in json.dumps(image.info)


def test_non_image_and_oversized_dimension_rejected_before_transmission() -> None:
    with gateway(lambda _: pytest.fail("must not transmit")) as client:
        with pytest.raises(DeepSeekPolicyError, match="safely decoded"):
            client.normalize_image(b"not really a png", asset_id="bad")
        with pytest.raises(DeepSeekPolicyError, match="dimensions exceed"):
            client.normalize_image(png_bytes(size=(4097, 1)), asset_id="wide")


def test_text_model_image_request_rejected_before_transmission() -> None:
    data_url = "data:image/png;base64," + base64.b64encode(png_bytes()).decode()
    with gateway(lambda _: pytest.fail("must not transmit")) as client, pytest.raises(DeepSeekPolicyError, match="Images require"):
        client.chat_json(
            "demand_analyst",
            [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": data_url}}]}],
            Probe,
        )


def test_remote_vision_url_rejected_before_transmission() -> None:
    with gateway(lambda _: pytest.fail("must not transmit")) as client, pytest.raises(DeepSeekPolicyError, match="normalized inline PNG"):
        route = client.config.routes["visual_observer"]
        client._payload(
            route,
            [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "https://example.invalid/x.png"}}]}],
            max_tokens=10,
            thinking="disabled",
        )


def test_stream_parses_keepalive_usage_and_done() -> None:
    events = "\n".join(
        [
            ": keep-alive",
            'data: {"model":"deepseek-flash","choices":[{"delta":{"role":"assistant","content":"Farm"},"finish_reason":null}],"usage":null}',
            'data: {"model":"deepseek-flash","choices":[{"delta":{"content":"Tact"},"finish_reason":"stop"}],"usage":{"prompt_tokens":3,"completion_tokens":2,"total_tokens":5}}',
            "data: [DONE]",
            "",
        ]
    )
    with gateway(lambda _: httpx.Response(200, text=events, headers={"content-type": "text/event-stream"})) as client:
        result = client.stream_text("demand_analyst", [{"role": "user", "content": "x"}])
    assert result.content == "FarmTact"
    assert result.usage.total_tokens == 5


@pytest.mark.parametrize(
    "events",
    [
        'data: {"model":"deepseek-flash","choices":[{"delta":{"content":"x"},"finish_reason":"stop"}],"usage":null}\n',
        "data: not-json\n\ndata: [DONE]\n",
        'event: message\ndata: [DONE]\n',
        'data: {"model":"deepseek-flash","choices":[{"delta":{"content":"x"},"finish_reason":"length"}],"usage":null}\n\ndata: [DONE]\n',
    ],
)
def test_incomplete_or_invalid_stream_fails(events: str) -> None:
    with gateway(lambda _: httpx.Response(200, text=events)) as client, pytest.raises(DeepSeekResponseError):
        client.stream_text("demand_analyst", [{"role": "user", "content": "x"}])


def test_model_listing_shape() -> None:
    wire = {
        "object": "list",
        "data": [{"id": "deepseek-flash", "object": "model", "owned_by": "deepseek"}],
    }
    with gateway(lambda _: httpx.Response(200, json=wire)) as client:
        assert client.list_models() == {"deepseek-flash"}


def test_json_response_is_bounded_while_reading(tmp_path: Path) -> None:
    changed = changed_config(tmp_path, lambda raw: raw["limits"].update(max_response_bytes=64))
    with DeepSeekGateway.from_config(
        changed,
        api_key="unit-test-placeholder",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"x" * 65)),
    ) as client, pytest.raises(DeepSeekResponseError, match="byte limit"):
        client.list_models()


def test_unterminated_sse_line_is_bounded_while_reading(tmp_path: Path) -> None:
    changed = changed_config(tmp_path, lambda raw: raw["limits"].update(max_response_bytes=64))
    with DeepSeekGateway.from_config(
        changed,
        api_key="unit-test-placeholder",
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=b"data: " + b"x" * 64)),
    ) as client, pytest.raises(DeepSeekResponseError, match="stream exceeds"):
        client.stream_text("demand_analyst", [{"role": "user", "content": "x"}])


def test_wall_budget_is_checked_after_transport_returns(tmp_path: Path) -> None:
    changed = changed_config(tmp_path, lambda raw: raw["limits"].update(max_wall_seconds=0.02))
    calls = 0

    def slow_handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        time.sleep(0.03)
        return httpx.Response(200, json={"object": "list", "data": []})

    with DeepSeekGateway.from_config(
        changed,
        api_key="unit-test-placeholder",
        transport=httpx.MockTransport(slow_handler),
    ) as client, pytest.raises(DeepSeekBlockedError, match="wall-clock"):
        client.list_models()
    assert calls == 1
