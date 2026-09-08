"""Independent A11 provider-isolation tests.

Every network interaction uses httpx.MockTransport. No test can reach a provider.
"""

from __future__ import annotations

import inspect
import io
import json
import os
import stat
import subprocess
import sys
import time
from dataclasses import asdict, replace
from pathlib import Path

import httpx
import pytest
from PIL import Image
from pydantic import BaseModel, ConfigDict
from fastapi.testclient import TestClient

import runtime.deepseek_gateway as gateway_module
from runtime.deepseek_gateway import (
    DeepSeekBlockedError,
    DeepSeekGateway,
    DeepSeekPolicyError,
    DeepSeekResponseError,
    GatewayConfig,
    NormalizedImage,
    RunBudget,
)
from services.api import council as council_module
from services.api import vision as vision_module
from services.api.app import create_app
from services.api.store import Store


ROOT = Path(__file__).parents[2]
CONFIG = ROOT / "config" / "deepseek_runtime.json"
SERVE = ROOT / "scripts" / "serve.py"
PLACEHOLDER_KEY = "provider-isolation-test-placeholder"


class Result(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: str


def completion(
    content: str = '{"status":"ok"}', *, model: str = "deepseek-v4-flash",
    reasoning_content: str | None = None,
) -> dict:
    message = {"role": "assistant", "content": content}
    if reasoning_content is not None:
        message["reasoning_content"] = reasoning_content
    return {
        "id": "mock-completion",
        "model": model,
        "choices": [{"index": 0, "finish_reason": "stop", "message": message}],
        "usage": {
            "prompt_tokens": 5,
            "completion_tokens": 3,
            "total_tokens": 8,
            "completion_tokens_details": {"reasoning_tokens": 2},
        },
    }


def mocked_gateway(handler, *, budget: RunBudget | None = None, config: GatewayConfig | None = None) -> DeepSeekGateway:
    return DeepSeekGateway(
        config or GatewayConfig.load(CONFIG),
        api_key=PLACEHOLDER_KEY,
        budget=budget,
        transport=httpx.MockTransport(handler),
    )


def write_changed_config(tmp_path: Path, mutate) -> Path:
    raw = json.loads(CONFIG.read_text(encoding="utf-8"))
    mutate(raw)
    target = tmp_path / "changed-runtime.json"
    target.write_text(json.dumps(raw), encoding="utf-8")
    return target


@pytest.mark.parametrize(
    "mutation",
    [
        lambda raw: raw.update(provider="openai"),
        lambda raw: raw.update(origin="https://api.deepseek.com.attacker.invalid"),
        lambda raw: raw.update(origin="http://api.deepseek.com"),
        lambda raw: raw.update(chat_path="https://attacker.invalid/chat/completions"),
        lambda raw: raw.update(models_path="/../models"),
        lambda raw: raw["allowed_models"].append("gpt-6-astra"),
        lambda raw: raw["routes"]["demand_analyst"].update(model="gpt-6-astra"),
        lambda raw: raw["routes"]["demand_analyst"].update(model="deepseek-v4-pro"),
        lambda raw: raw["routes"]["visual_observer"].update(model="deepseek-v4-flash"),
        lambda raw: raw["routes"]["demand_analyst"].update(capability="vision"),
        lambda raw: raw["routes"].update(attacker_role={"model": "deepseek-v4-flash", "capability": "text"}),
        lambda raw: raw["routes"].pop("test_evaluator"),
    ],
)
def test_alternate_provider_origin_path_and_model_configs_fail_closed(tmp_path: Path, mutation) -> None:
    path = write_changed_config(tmp_path, mutation)
    with pytest.raises(DeepSeekPolicyError):
        DeepSeekGateway.from_config(path, api_key=PLACEHOLDER_KEY, transport=httpx.MockTransport(lambda _: pytest.fail("no transmission")))


def test_reviewed_roles_are_complete_and_council_has_no_provider_or_model_override() -> None:
    config = GatewayConfig.load(CONFIG)
    expected_roles = {
        "demand_analyst", "crop_scientist", "supply_weather_scout", "resources_margin_analyst",
        "planning_chair", "independent_critic", "evidence_extractor", "crop_alias_resolver",
        "runtime_researcher", "visual_observer", "document_vision",
        "satellite_visual_reviewer", "test_evaluator",
    }
    assert set(config.routes) == expected_roles
    assert all(config.routes[role].capability == "text" for role in council_module.ROLES)
    assert set(inspect.signature(council_module.council).parameters).isdisjoint({"provider", "model", "origin", "execution_mode"})


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("max_requests", 17),
        ("max_reserved_output_tokens", 16_385),
        ("max_concurrency", 2),
        ("max_images_per_request", 5),
        ("max_image_bytes", 4_194_305),
        ("max_image_dimension", 4_097),
        ("max_request_bytes", 16_777_217),
        ("max_response_bytes", 4_194_305),
        ("max_wall_seconds", 300.1),
        ("connect_timeout_seconds", 10.1),
        ("read_timeout_seconds", 90.1),
        ("write_timeout_seconds", 30.1),
        ("pool_timeout_seconds", 5.1),
        ("max_wall_seconds", float("inf")),
    ],
)
def test_manifest_cannot_raise_reviewed_resource_or_timeout_ceiling(tmp_path: Path, name: str, value: object) -> None:
    path = write_changed_config(tmp_path, lambda raw: raw["limits"].update({name: value}))
    with pytest.raises(DeepSeekPolicyError):
        GatewayConfig.load(path)


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("development_phase", "operational"),
        ("decision_policy", "prompt_selected"),
        ("default_execution_mode", "live"),
        ("default_data_mode", "real_private"),
    ],
)
def test_manifest_cannot_change_fixed_development_mode_policy(tmp_path: Path, name: str, value: str) -> None:
    path = write_changed_config(tmp_path, lambda raw: raw.update({name: value}))
    with pytest.raises(DeepSeekPolicyError):
        GatewayConfig.load(path)


def test_run_budget_cannot_exceed_a_more_restrictive_loaded_config() -> None:
    config = GatewayConfig.load(CONFIG)
    restricted = replace(config, limits=replace(config.limits, max_requests=2, max_reserved_output_tokens=100, max_wall_seconds=10))
    budget = RunBudget(max_requests=3, max_reserved_output_tokens=100, max_wall_seconds=10)
    with pytest.raises(DeepSeekPolicyError, match="exceeds configured limits"):
        mocked_gateway(lambda _: pytest.fail("invalid budget must not create a request"), budget=budget, config=restricted)


@pytest.mark.parametrize("role", ["openai", "gpt_evaluator", "../visual_observer", "VISUAL_OBSERVER"])
def test_alternate_or_malformed_roles_fail_before_transmission(role: str) -> None:
    transmitted = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal transmitted
        transmitted += 1
        return httpx.Response(500)

    with mocked_gateway(handler) as client, pytest.raises(DeepSeekPolicyError, match="Unknown runtime role"):
        client.chat_json(role, [{"role": "user", "content": "fixture"}], Result)
    assert transmitted == 0


@pytest.mark.parametrize(
    ("execution_mode", "data_mode"),
    [("live", "synthetic_demo"), ("replay", "historical_replay"), ("test", "live_advisory"), ("test", "real_private")],
)
def test_modes_fail_before_any_text_transmission(execution_mode: str, data_mode: str) -> None:
    with mocked_gateway(lambda _: pytest.fail("mode rejection must precede transmission")) as client, pytest.raises(DeepSeekPolicyError):
        client.chat_json(
            "demand_analyst", [{"role": "user", "content": "fixture"}], Result,
            execution_mode=execution_mode, data_mode=data_mode,
        )


def test_vision_mode_role_and_forged_remote_image_fail_before_transmission() -> None:
    forged = NormalizedImage(
        asset_id="forged", source_sha256="a" * 64, normalized_sha256="b" * 64,
        width=1, height=1, byte_count=1, _data_url="https://attacker.invalid/private.png",
    )
    with mocked_gateway(lambda _: pytest.fail("vision policy rejection must precede transmission")) as client:
        with pytest.raises(DeepSeekPolicyError, match="execution_mode=test"):
            client.vision_json(prompt="fixture", images=[forged], output_model=Result, execution_mode="live")
        with pytest.raises(DeepSeekPolicyError, match="does not support"):
            client.vision_json(prompt="fixture", images=[forged], output_model=Result, role="demand_analyst")
        with pytest.raises(DeepSeekPolicyError, match="normalized inline PNG"):
            client.vision_json(prompt="fixture", images=[forged], output_model=Result)


def test_client_disables_redirects_and_inherited_proxy_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict = {}

    class CapturingClient:
        def __init__(self, **kwargs):
            captured.update(kwargs)

        def close(self) -> None:
            pass

    monkeypatch.setattr(gateway_module.httpx, "Client", CapturingClient)
    client = DeepSeekGateway.from_config(CONFIG, api_key=PLACEHOLDER_KEY)
    client.close()
    assert captured["base_url"] == "https://api.deepseek.com"
    assert captured["follow_redirects"] is False
    assert captured["trust_env"] is False
    assert "proxies" not in captured and "proxy" not in captured


@pytest.mark.parametrize("stream", [False, True])
def test_redirect_to_alternate_origin_is_rejected_without_second_request(stream: bool) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(308, headers={"location": "https://attacker.invalid/collect"})

    with mocked_gateway(handler) as client, pytest.raises(DeepSeekPolicyError, match="redirect rejected"):
        if stream:
            client.stream_text("demand_analyst", [{"role": "user", "content": "fixture"}])
        else:
            client.chat_json("demand_analyst", [{"role": "user", "content": "fixture"}], Result)
    assert seen == ["https://api.deepseek.com/chat/completions"]


@pytest.mark.parametrize("status", [400, 401, 403, 429, 500, 503])
def test_provider_errors_are_safe_and_never_trigger_fallback(status: int) -> None:
    seen: list[str] = []
    private_body = "mock-private-prompt-and-provider-detail"

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(str(request.url))
        return httpx.Response(status, text=private_body, headers={"x-request-id": "safe.fixture-id"})

    with mocked_gateway(handler) as client, pytest.raises((DeepSeekBlockedError, DeepSeekResponseError)) as caught:
        client.chat_json("demand_analyst", [{"role": "user", "content": "fixture-private-input"}], Result)
    assert seen == ["https://api.deepseek.com/chat/completions"]
    assert private_body not in str(caught.value)
    assert "fixture-private-input" not in str(caught.value)
    assert "attacker.invalid" not in str(caught.value)


def test_transport_timeout_is_safe_bounded_and_has_no_fallback() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        raise httpx.ReadTimeout("mock-private-timeout-detail", request=request)

    with mocked_gateway(handler) as client, pytest.raises(DeepSeekBlockedError, match="transport request failed") as caught:
        client.chat_json("demand_analyst", [{"role": "user", "content": "fixture-private-input"}], Result)
    assert calls == 1
    assert "mock-private" not in str(caught.value)
    assert "fixture-private-input" not in str(caught.value)


def test_expired_wall_budget_blocks_before_transmission() -> None:
    budget = RunBudget(max_requests=2, max_reserved_output_tokens=100, max_wall_seconds=0.01, started_at=time.monotonic() - 1)
    with mocked_gateway(lambda _: pytest.fail("expired run must not transmit"), budget=budget) as client, pytest.raises(
        DeepSeekBlockedError, match="wall-clock budget exhausted"
    ):
        client.chat_json("demand_analyst", [{"role": "user", "content": "fixture"}], Result, max_tokens=10)
    assert budget.request_count == 0
    assert budget.reserved_output_tokens == 0


def test_oversized_response_is_rejected_before_json_or_private_body_exposure() -> None:
    config = GatewayConfig.load(CONFIG)
    constrained = replace(config, limits=replace(config.limits, max_response_bytes=32))
    private_body = b'{"private":"' + b"x" * 64 + b'"}'
    with mocked_gateway(lambda _: httpx.Response(200, content=private_body), config=constrained) as client, pytest.raises(
        DeepSeekResponseError, match="response exceeds byte limit"
    ) as caught:
        client.chat_json("demand_analyst", [{"role": "user", "content": "fixture"}], Result)
    assert "private" not in str(caught.value)


def test_provider_reasoning_is_not_exposed_in_completion_audit_or_repr() -> None:
    private_reasoning = "mock-private-chain-of-thought-sentinel"
    wire = completion(reasoning_content=private_reasoning)
    with mocked_gateway(lambda _: httpx.Response(200, json=wire)) as client:
        result = client.chat_json("demand_analyst", [{"role": "user", "content": "fixture"}], Result)
    public = asdict(result)
    public["data"] = result.data.model_dump()
    assert private_reasoning not in json.dumps(public)
    assert private_reasoning not in repr(result)
    assert result.audit.input_sha256 and len(result.audit.input_sha256) == 64
    assert result.audit.usage.reasoning_tokens == 2
    assert not hasattr(result, "reasoning_content")
    assert not hasattr(result.audit, "reasoning_content")


def test_provider_failure_body_and_secret_never_enter_public_run(monkeypatch: pytest.MonkeyPatch) -> None:
    private_provider_body = "mock-private-provider-body-and-reasoning-sentinel"
    calls = 0

    def handler(_: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(503, text=private_provider_body)

    def factory(*_args, budget=None, **_kwargs):
        return mocked_gateway(handler, budget=budget)

    monkeypatch.setenv("DEEPSEEK_API_KEY", PLACEHOLDER_KEY)
    monkeypatch.setattr(council_module.DeepSeekGateway, "from_config", staticmethod(factory))
    store = Store("sqlite://")
    app = create_app(store, start_worker=False)
    with TestClient(app) as client:
        client.get("/api/v1/bootstrap")
        created = client.post(
            "/api/v1/planning-runs", json={"council": True, "with_vision": False},
            headers={"Idempotency-Key": "provider-failure-sanitization"},
        ).json()
        tenant = store.authenticate(client.cookies.get("farmtact_session"))
        assert store.claim(tenant, created["id"])
        app.state.worker.execute(tenant, created["id"])
        response = client.get(f"/api/v1/planning-runs/{created['id']}")
        assert response.status_code == 200
        public_body = response.text
        public_run = response.json()
    assert calls == 1
    assert public_run["council_status"] == "failed"
    assert private_provider_body not in public_body
    assert PLACEHOLDER_KEY not in public_body
    assert "mock-private" not in json.dumps(public_run.get("events", []))
    assert public_run.get("inference_audit") == []


def png_bytes() -> bytes:
    image = Image.new("RGB", (16, 8), "#eef2d4")
    output = io.BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def test_synthetic_visual_workflow_preserves_provenance_and_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    requests: list[dict] = []
    run_id = "abcdef123456"
    expected_label = "FT-ABCDEF"

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        requests.append(body)
        assert str(request.url) == "https://api.deepseek.com/chat/completions"
        assert body["model"] == "deepseek-v4-flash-vision-exp"
        content = body["messages"][0]["content"]
        assert "synthetic label" in content[0]["text"].lower()
        assert content[1]["image_url"]["url"].startswith("data:image/png;base64,")
        return httpx.Response(200, json=completion(
            json.dumps({"batch_id": expected_label, "visible_condition": "Synthetic fixture label only", "uncertain": False}),
            model="deepseek-v4-flash-vision-exp",
        ))

    def factory(*_args, budget=None, **_kwargs):
        return mocked_gateway(handler, budget=budget)

    monkeypatch.setattr(vision_module.DeepSeekGateway, "from_config", staticmethod(factory))
    result = vision_module.observe_fixture(run_id, budget=RunBudget(max_requests=1, max_reserved_output_tokens=1024, max_wall_seconds=30))
    assert len(requests) == 1
    assert result["origin"] == "synthetic"
    assert result["agronomic_measurement"] is False
    assert result["review_status"] == "label_verified_against_fixture"
    assert result["asset_id"].startswith("synthetic-label-")
    assert result["observation"]["batch_id"] == expected_label
    assert len(result["source_sha256"]) == 64 and len(result["normalized_sha256"]) == 64
    assert result["audit"]["provider"] == "deepseek"
    assert result["audit"]["inference_origin"] == "deepseek_api"


def _minimal_subprocess_env(home: Path, stub_dir: Path, marker: Path) -> dict[str, str]:
    return {
        "PATH": os.environ.get("PATH", ""),
        "HOME": str(home),
        "PYTHONPATH": str(stub_dir),
        "FARMTACT_TEST_MARKER": str(marker),
        "PYTHONIOENCODING": "utf-8",
    }


def _write_uvicorn_stub(stub_dir: Path) -> None:
    (stub_dir / "uvicorn.py").write_text(
        "import json,os\n"
        "from pathlib import Path\n"
        "def run(app,**kwargs):\n"
        " Path(os.environ['FARMTACT_TEST_MARKER']).write_text(json.dumps({"
        "'secret_present':bool(os.environ.get('DEEPSEEK_API_KEY')),'execution_mode':os.environ.get('FARMTACT_EXECUTION_MODE'),"
        "'app':app,'host':kwargs.get('host'),'port':kwargs.get('port'),'access_log':kwargs.get('access_log')}))\n",
        encoding="utf-8",
    )


def test_server_secret_file_delivery_checks_permissions_and_exposes_no_value(tmp_path: Path) -> None:
    home, stub_dir = tmp_path / "home", tmp_path / "stub"
    secret_dir = home / ".config" / "farmtact"
    secret_dir.mkdir(parents=True)
    stub_dir.mkdir()
    marker = tmp_path / "marker.json"
    secret_file = secret_dir / "server-secrets.json"
    secret_file.write_text(json.dumps({"DEEPSEEK_API_KEY": PLACEHOLDER_KEY}), encoding="utf-8")
    secret_file.chmod(stat.S_IRUSR | stat.S_IWUSR)
    _write_uvicorn_stub(stub_dir)
    completed = subprocess.run(
        [sys.executable, str(SERVE)], cwd=ROOT, env=_minimal_subprocess_env(home, stub_dir, marker),
        text=True, capture_output=True, timeout=10, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    observed = json.loads(marker.read_text(encoding="utf-8"))
    assert observed == {
        "secret_present": True, "execution_mode": "test", "app": "services.api.app:app",
        "host": "0.0.0.0", "port": 8080, "access_log": False,
    }
    assert PLACEHOLDER_KEY not in completed.stdout + completed.stderr + marker.read_text(encoding="utf-8")


def test_server_rejects_overpermissive_secret_file_without_starting(tmp_path: Path) -> None:
    home, stub_dir = tmp_path / "home", tmp_path / "stub"
    secret_dir = home / ".config" / "farmtact"
    secret_dir.mkdir(parents=True)
    stub_dir.mkdir()
    marker = tmp_path / "marker.json"
    secret_file = secret_dir / "server-secrets.json"
    secret_file.write_text(json.dumps({"DEEPSEEK_API_KEY": PLACEHOLDER_KEY}), encoding="utf-8")
    secret_file.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP)
    _write_uvicorn_stub(stub_dir)
    completed = subprocess.run(
        [sys.executable, str(SERVE)], cwd=ROOT, env=_minimal_subprocess_env(home, stub_dir, marker),
        text=True, capture_output=True, timeout=10, check=False,
    )
    assert completed.returncode != 0
    assert not marker.exists()
    assert "unsafe ownership or permissions" in completed.stderr
    assert PLACEHOLDER_KEY not in completed.stdout + completed.stderr


def test_process_egress_hook_blocks_alternate_hosts_ips_and_ports_in_isolated_process(tmp_path: Path) -> None:
    marker = tmp_path / "egress-marker"
    program = """
import socket,sys
class FakeSocket: family=socket.AF_INET
socket.getaddrinfo=lambda host,port,*a,**k:[(socket.AF_INET,socket.SOCK_STREAM,6,'',(\"203.0.113.10\",port))]
from services.api.egress import install
install()
socket.getaddrinfo('api.deepseek.com',443)
sys.audit('socket.connect',FakeSocket(),('203.0.113.10',443))
blocked=0
for operation in (
 lambda: socket.getaddrinfo('attacker.invalid',443),
 lambda: sys.audit('socket.connect',FakeSocket(),('198.51.100.2',443)),
 lambda: sys.audit('socket.connect',FakeSocket(),('203.0.113.10',80)),
):
 try: operation()
 except PermissionError: blocked+=1
assert blocked==3
from pathlib import Path
Path(sys.argv[1]).write_text('pass')
"""
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": str(ROOT), "PYTHONIOENCODING": "utf-8"}
    completed = subprocess.run(
        [sys.executable, "-c", program, str(marker)], cwd=ROOT, env=env,
        text=True, capture_output=True, timeout=10, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert marker.read_text(encoding="utf-8") == "pass"
