"""Bounded, DeepSeek-only Chat Completions gateway for FarmTact.

Provider-private reasoning is retained only in the local stack frame that performs
a tool continuation. It is deliberately absent from every public return type.
"""

from __future__ import annotations

import base64
import hashlib
import io
import json
import math
import os
import re
import threading
import time
import warnings
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Generic, Literal, Mapping, Sequence, TypeVar

import httpx
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, TypeAdapter, ValidationError


T = TypeVar("T")
ThinkingMode = Literal["enabled", "disabled"]
ReasoningEffort = Literal["low", "high", "max"]

REVIEWED_MODELS = frozenset(
    {"deepseek-v4-flash", "deepseek-v4-pro", "deepseek-v4-flash-vision-exp"}
)
REVIEWED_ROUTES: dict[str, tuple[str, str]] = {
    "demand_analyst": ("deepseek-v4-flash", "text"),
    "crop_scientist": ("deepseek-v4-pro", "text"),
    "supply_weather_scout": ("deepseek-v4-flash", "text"),
    "resources_margin_analyst": ("deepseek-v4-flash", "text"),
    "planning_chair": ("deepseek-v4-pro", "text"),
    "independent_critic": ("deepseek-v4-pro", "text"),
    "evidence_extractor": ("deepseek-v4-flash", "text"),
    "crop_alias_resolver": ("deepseek-v4-flash", "text"),
    "runtime_researcher": ("deepseek-v4-pro", "text"),
    "visual_observer": ("deepseek-v4-flash-vision-exp", "vision"),
    "document_vision": ("deepseek-v4-flash-vision-exp", "vision"),
    "satellite_visual_reviewer": ("deepseek-v4-flash-vision-exp", "vision"),
    "test_evaluator": ("deepseek-v4-pro", "text"),
}
INTEGER_LIMIT_CEILINGS = {
    "max_requests": 16,
    "max_reserved_output_tokens": 16_384,
    "max_concurrency": 1,
    "max_images_per_request": 4,
    "max_image_bytes": 4_194_304,
    "max_image_dimension": 4_096,
    "max_request_bytes": 16_777_216,
    "max_response_bytes": 4_194_304,
}
TIME_LIMIT_CEILINGS = {
    "max_wall_seconds": 300.0,
    "connect_timeout_seconds": 10.0,
    "read_timeout_seconds": 90.0,
    "write_timeout_seconds": 30.0,
    "pool_timeout_seconds": 5.0,
}
DEFAULT_PROVIDER_USER_ID = "farmtact_standalone_trial"
PROVIDER_USER_ID_PATTERN = re.compile(r"[A-Za-z0-9_-]{1,512}\Z")


class DeepSeekGatewayError(RuntimeError):
    """Safe gateway error; messages never contain request bodies or credentials."""

    code = "gateway_error"

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class DeepSeekBlockedError(DeepSeekGatewayError):
    code = "blocked"


class DeepSeekPolicyError(DeepSeekGatewayError):
    code = "policy_error"


class DeepSeekResponseError(DeepSeekGatewayError):
    code = "response_error"


@dataclass(frozen=True)
class Route:
    model: str
    capability: Literal["text", "vision"]


@dataclass(frozen=True)
class Limits:
    max_requests: int
    max_reserved_output_tokens: int
    max_wall_seconds: float
    max_concurrency: int
    max_images_per_request: int
    max_image_bytes: int
    max_image_dimension: int
    max_request_bytes: int
    max_response_bytes: int
    connect_timeout_seconds: float
    read_timeout_seconds: float
    write_timeout_seconds: float
    pool_timeout_seconds: float


@dataclass(frozen=True)
class GatewayConfig:
    provider: str
    origin: str
    chat_path: str
    models_path: str
    allowed_models: frozenset[str]
    routes: Mapping[str, Route]
    limits: Limits
    development_phase: str
    decision_policy: str
    default_execution_mode: str
    default_data_mode: str

    @classmethod
    def load(cls, path: str | Path) -> "GatewayConfig":
        try:
            raw = json.loads(
                Path(path).read_text(encoding="utf-8"),
                parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)),
            )
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            raise DeepSeekPolicyError("DeepSeek runtime manifest is not valid JSON") from exc
        expected_keys = {
            "schema_version", "provider", "origin", "chat_path", "models_path",
            "development_phase", "decision_policy", "default_execution_mode",
            "default_data_mode", "allowed_models", "routes", "limits",
        }
        if not isinstance(raw, dict) or set(raw) != expected_keys:
            raise DeepSeekPolicyError("DeepSeek runtime manifest fields differ from reviewed policy")
        if raw.get("schema_version") != "1.0":
            raise DeepSeekPolicyError("Unreviewed DeepSeek runtime manifest version")
        if raw.get("provider") != "deepseek":
            raise DeepSeekPolicyError("Runtime provider must be DeepSeek")
        if raw.get("origin") != "https://api.deepseek.com":
            raise DeepSeekPolicyError("DeepSeek origin is fixed by policy")
        if raw.get("chat_path") != "/chat/completions" or raw.get("models_path") != "/models":
            raise DeepSeekPolicyError("Unreviewed DeepSeek endpoint")
        if not isinstance(raw.get("allowed_models"), list) or any(
            not isinstance(model, str) for model in raw["allowed_models"]
        ):
            raise DeepSeekPolicyError("Model allowlist is not a string list")
        allowed = frozenset(raw["allowed_models"])
        if len(raw["allowed_models"]) != len(allowed) or allowed != REVIEWED_MODELS:
            raise DeepSeekPolicyError("Model allowlist differs from reviewed manifest")
        if not isinstance(raw.get("routes"), dict):
            raise DeepSeekPolicyError("Runtime routes must be an object")
        normalized_routes: dict[str, tuple[str, str]] = {}
        for name, value in raw["routes"].items():
            if not isinstance(name, str) or not isinstance(value, dict) or set(value) != {"model", "capability"}:
                raise DeepSeekPolicyError("Runtime route fields differ from reviewed policy")
            model, capability = value.get("model"), value.get("capability")
            if not isinstance(model, str) or capability not in {"text", "vision"}:
                raise DeepSeekPolicyError("Runtime route is invalid")
            normalized_routes[name] = (model, capability)
        if normalized_routes != REVIEWED_ROUTES:
            raise DeepSeekPolicyError("Role routes differ from reviewed manifest")
        routes = {
            name: Route(model=model, capability=capability)  # type: ignore[arg-type]
            for name, (model, capability) in normalized_routes.items()
        }
        limits_raw = raw.get("limits")
        expected_limit_names = set(INTEGER_LIMIT_CEILINGS) | set(TIME_LIMIT_CEILINGS)
        if not isinstance(limits_raw, dict) or set(limits_raw) != expected_limit_names:
            raise DeepSeekPolicyError("Runtime limit fields differ from reviewed policy")
        for name, ceiling in INTEGER_LIMIT_CEILINGS.items():
            value = limits_raw[name]
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0 or value > ceiling:
                raise DeepSeekPolicyError(f"Runtime limit {name} is outside reviewed bounds")
        for name, ceiling in TIME_LIMIT_CEILINGS.items():
            value = limits_raw[name]
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
                or value <= 0
                or value > ceiling
            ):
                raise DeepSeekPolicyError(f"Runtime limit {name} is outside reviewed bounds")
        if limits_raw["max_image_bytes"] > limits_raw["max_request_bytes"]:
            raise DeepSeekPolicyError("Image byte limit cannot exceed request byte limit")
        try:
            limits = Limits(**limits_raw)
        except TypeError as exc:
            raise DeepSeekPolicyError("Runtime limits are invalid") from exc
        fixed_policy = {
            "development_phase": "autonomous_development",
            "decision_policy": "automatic_development",
            "default_execution_mode": "test",
            "default_data_mode": "synthetic_demo",
        }
        if any(raw.get(name) != value for name, value in fixed_policy.items()):
            raise DeepSeekPolicyError("Runtime mode policy differs from reviewed manifest")
        return cls(
            provider=raw["provider"],
            origin=raw["origin"],
            chat_path=raw["chat_path"],
            models_path=raw["models_path"],
            allowed_models=allowed,
            routes=routes,
            limits=limits,
            development_phase=raw["development_phase"],
            decision_policy=raw["decision_policy"],
            default_execution_mode=raw["default_execution_mode"],
            default_data_mode=raw["default_data_mode"],
        )


@dataclass
class RunBudget:
    max_requests: int = 16
    max_reserved_output_tokens: int = 16_384
    max_wall_seconds: float = 300.0
    started_at: float = field(default_factory=time.monotonic)
    request_count: int = 0
    reserved_output_tokens: int = 0
    _lock: threading.Lock = field(default_factory=threading.Lock, repr=False)

    def __post_init__(self) -> None:
        integer_values = {
            "max_requests": self.max_requests,
            "max_reserved_output_tokens": self.max_reserved_output_tokens,
            "request_count": self.request_count,
            "reserved_output_tokens": self.reserved_output_tokens,
        }
        if any(not isinstance(value, int) or isinstance(value, bool) for value in integer_values.values()):
            raise DeepSeekPolicyError("Run budget integer fields are invalid")
        if not 1 <= self.max_requests <= INTEGER_LIMIT_CEILINGS["max_requests"]:
            raise DeepSeekPolicyError("Run request budget is outside reviewed bounds")
        if not 1 <= self.max_reserved_output_tokens <= INTEGER_LIMIT_CEILINGS["max_reserved_output_tokens"]:
            raise DeepSeekPolicyError("Run output-token budget is outside reviewed bounds")
        if not isinstance(self.max_wall_seconds, (int, float)) or isinstance(self.max_wall_seconds, bool):
            raise DeepSeekPolicyError("Run wall-clock budget is invalid")
        if not math.isfinite(self.max_wall_seconds) or not 0 < self.max_wall_seconds <= TIME_LIMIT_CEILINGS["max_wall_seconds"]:
            raise DeepSeekPolicyError("Run wall-clock budget is outside reviewed bounds")
        if not isinstance(self.started_at, (int, float)) or not math.isfinite(self.started_at):
            raise DeepSeekPolicyError("Run budget start time is invalid")
        if self.started_at > time.monotonic() + 0.01:
            raise DeepSeekPolicyError("Run budget start time cannot be in the future")
        if not 0 <= self.request_count <= self.max_requests:
            raise DeepSeekPolicyError("Run request count is invalid")
        if not 0 <= self.reserved_output_tokens <= self.max_reserved_output_tokens:
            raise DeepSeekPolicyError("Run reserved output-token count is invalid")

    def validate_against(self, limits: Limits) -> None:
        if (
            self.max_requests > limits.max_requests
            or self.max_reserved_output_tokens > limits.max_reserved_output_tokens
            or self.max_wall_seconds > limits.max_wall_seconds
        ):
            raise DeepSeekPolicyError("Run budget exceeds configured limits")

    def remaining_seconds(self) -> float:
        return self.max_wall_seconds - (time.monotonic() - self.started_at)

    def reserve(self, output_tokens: int) -> None:
        if not isinstance(output_tokens, int) or isinstance(output_tokens, bool) or output_tokens < 0:
            raise DeepSeekPolicyError("Output-token reservation must be a non-negative integer")
        with self._lock:
            if time.monotonic() - self.started_at >= self.max_wall_seconds:
                raise DeepSeekBlockedError("DeepSeek run wall-clock budget exhausted")
            if self.request_count + 1 > self.max_requests:
                raise DeepSeekBlockedError("DeepSeek request budget exhausted")
            if self.reserved_output_tokens + output_tokens > self.max_reserved_output_tokens:
                raise DeepSeekBlockedError("DeepSeek output-token budget exhausted")
            self.request_count += 1
            self.reserved_output_tokens += output_tokens


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    prompt_cache_hit_tokens: int | None = None
    prompt_cache_miss_tokens: int | None = None
    reasoning_tokens: int | None = None

    @classmethod
    def from_wire(cls, raw: object) -> "Usage":
        if not isinstance(raw, dict):
            return cls()
        completion_details = raw.get("completion_tokens_details")
        reasoning = completion_details.get("reasoning_tokens") if isinstance(completion_details, dict) else None
        return cls(
            prompt_tokens=_optional_int(raw.get("prompt_tokens")),
            completion_tokens=_optional_int(raw.get("completion_tokens")),
            total_tokens=_optional_int(raw.get("total_tokens")),
            prompt_cache_hit_tokens=_optional_int(raw.get("prompt_cache_hit_tokens")),
            prompt_cache_miss_tokens=_optional_int(raw.get("prompt_cache_miss_tokens")),
            reasoning_tokens=_optional_int(reasoning),
        )


@dataclass(frozen=True)
class SafeAudit:
    provider: str
    requested_model: str
    returned_model: str
    role: str
    capability: str
    execution_mode: str
    data_mode: str
    inference_origin: Literal["deepseek_api"]
    input_sha256: str
    request_id: str | None
    latency_ms: int
    usage: Usage


@dataclass(frozen=True)
class PublicCompletion(Generic[T]):
    content: str
    data: T | None
    model: str
    finish_reason: str
    usage: Usage
    audit: SafeAudit


@dataclass(frozen=True)
class NormalizedImage:
    asset_id: str
    source_sha256: str
    normalized_sha256: str
    width: int
    height: int
    byte_count: int
    _data_url: str = field(repr=False)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    arguments_model: type[BaseModel]

    def wire_schema(self) -> dict[str, Any]:
        schema = self.arguments_model.model_json_schema()
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": schema,
            },
        }


@dataclass(frozen=True)
class _RawCompletion:
    message: dict[str, Any]
    model: str
    finish_reason: str
    usage: Usage
    request_id: str | None
    latency_ms: int
    input_sha256: str


class DeepSeekGateway:
    """Synchronous gateway with a finite per-run budget and no fallback client.

    The remaining run wall time caps every HTTP timeout and is checked after the
    response opens and while each response chunk is consumed. Because httpx's
    synchronous API has no external cancellation primitive, interpreter or OS
    scheduling can add a small amount of cleanup latency after the bound expires.
    """

    def __init__(
        self,
        config: GatewayConfig,
        *,
        api_key: str | None = None,
        user_id: str = DEFAULT_PROVIDER_USER_ID,
        budget: RunBudget | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        key = api_key if api_key is not None else os.environ.get("DEEPSEEK_API_KEY")
        if not key:
            raise DeepSeekBlockedError("DeepSeek credential is unavailable")
        if not isinstance(user_id, str) or not PROVIDER_USER_ID_PATTERN.fullmatch(user_id):
            raise DeepSeekPolicyError("DeepSeek provider user_id is outside reviewed bounds")
        self.config = config
        self._user_id = user_id
        self._concurrency = threading.BoundedSemaphore(config.limits.max_concurrency)
        self.budget = budget or RunBudget(
            max_requests=config.limits.max_requests,
            max_reserved_output_tokens=config.limits.max_reserved_output_tokens,
            max_wall_seconds=config.limits.max_wall_seconds,
        )
        self.budget.validate_against(config.limits)
        timeout = httpx.Timeout(
            connect=config.limits.connect_timeout_seconds,
            read=config.limits.read_timeout_seconds,
            write=config.limits.write_timeout_seconds,
            pool=config.limits.pool_timeout_seconds,
        )
        self._client = httpx.Client(
            base_url=config.origin,
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            timeout=timeout,
            follow_redirects=False,
            trust_env=False,
            transport=transport,
        )

    @classmethod
    def from_config(
        cls,
        path: str | Path,
        *,
        api_key: str | None = None,
        user_id: str = DEFAULT_PROVIDER_USER_ID,
        budget: RunBudget | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> "DeepSeekGateway":
        return cls(
            GatewayConfig.load(path),
            api_key=api_key,
            user_id=user_id,
            budget=budget,
            transport=transport,
        )

    def __enter__(self) -> "DeepSeekGateway":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def list_models(self) -> set[str]:
        wire, _, _, _ = self._request_json("GET", self.config.models_path, None, reserve_tokens=0)
        data = wire.get("data")
        if wire.get("object") != "list" or not isinstance(data, list):
            raise DeepSeekResponseError("DeepSeek model discovery returned an invalid shape")
        ids = {item.get("id") for item in data if isinstance(item, dict) and isinstance(item.get("id"), str)}
        return ids

    def chat_json(
        self,
        role: str,
        messages: Sequence[Mapping[str, Any]],
        output_model: type[T] | Any,
        *,
        max_tokens: int = 512,
        thinking: ThinkingMode = "disabled",
        reasoning_effort: ReasoningEffort | None = None,
        execution_mode: str = "test",
        data_mode: str = "synthetic_demo",
    ) -> PublicCompletion[T]:
        self._validate_modes(execution_mode, data_mode)
        route = self._route(role, "text")
        payload = self._payload(
            route,
            messages,
            max_tokens=max_tokens,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
            response_format={"type": "json_object"},
        )
        raw = self._chat_raw(payload, role=role)
        return self._public_json(raw, route, role, output_model, execution_mode, data_mode)

    def run_tool_json(
        self,
        role: str,
        messages: Sequence[Mapping[str, Any]],
        tools: Sequence[ToolSpec],
        execute_tool: Callable[[str, BaseModel], Mapping[str, Any]],
        output_model: type[T] | Any,
        *,
        max_tokens_each: int = 512,
        thinking: ThinkingMode = "enabled",
        reasoning_effort: ReasoningEffort = "low",
        execution_mode: str = "test",
        data_mode: str = "synthetic_demo",
    ) -> PublicCompletion[T]:
        self._validate_modes(execution_mode, data_mode)
        route = self._route(role, "text")
        if not tools or len({tool.name for tool in tools}) != len(tools):
            raise DeepSeekPolicyError("Tool workflow requires uniquely named allowlisted tools")
        tool_by_name = {tool.name: tool for tool in tools}
        wire_tools = [tool.wire_schema() for tool in tools]
        first_payload = self._payload(
            route,
            messages,
            max_tokens=max_tokens_each,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
            tools=wire_tools,
            # DeepSeek V4 thinking-tool compatibility rejects tool_choice even
            # though the generic Chat Completions schema documents it.
            tool_choice=None if thinking == "enabled" else "required",
        )
        first = self._chat_raw(first_payload, role=role, allowed_finish_reasons={"tool_calls"})

        # Keep the exact assistant message, including reasoning_content, private and
        # alive only until the continuation request finishes.
        private_assistant_message = dict(first.message)
        tool_calls = private_assistant_message.get("tool_calls")
        if not isinstance(tool_calls, list) or len(tool_calls) != 1:
            raise DeepSeekResponseError("DeepSeek must return exactly one tool call for this workflow")
        call = tool_calls[0]
        if not isinstance(call, dict) or call.get("type") != "function" or not isinstance(call.get("id"), str):
            raise DeepSeekResponseError("DeepSeek returned an invalid tool-call envelope")
        function = call.get("function")
        if not isinstance(function, dict) or function.get("name") not in tool_by_name:
            raise DeepSeekPolicyError("DeepSeek requested a tool outside the allowlist")
        tool = tool_by_name[function["name"]]
        try:
            arguments_raw = json.loads(function.get("arguments", ""))
            arguments = tool.arguments_model.model_validate(arguments_raw)
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise DeepSeekResponseError("DeepSeek returned invalid tool arguments") from exc
        result = execute_tool(tool.name, arguments)
        if not isinstance(result, Mapping):
            raise DeepSeekPolicyError("Allowlisted tool result must be a JSON object")

        continuation_messages = [dict(message) for message in messages]
        continuation_messages.extend(
            [
                private_assistant_message,
                {
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(dict(result), separators=(",", ":"), sort_keys=True),
                },
            ]
        )
        second_payload = self._payload(
            route,
            continuation_messages,
            max_tokens=max_tokens_each,
            thinking=thinking,
            reasoning_effort=reasoning_effort,
            tools=wire_tools,
            response_format={"type": "json_object"},
        )
        second = self._chat_raw(second_payload, role=role)
        completion = self._public_json(second, route, role, output_model, execution_mode, data_mode)
        private_assistant_message.clear()
        return completion

    def vision_json(
        self,
        *,
        prompt: str,
        images: Sequence[NormalizedImage],
        output_model: type[T] | Any,
        role: str = "visual_observer",
        max_tokens: int = 512,
        execution_mode: str = "test",
        data_mode: str = "synthetic_demo",
    ) -> PublicCompletion[T]:
        self._validate_modes(execution_mode, data_mode)
        route = self._route(role, "vision")
        if not images or len(images) > self.config.limits.max_images_per_request:
            raise DeepSeekPolicyError("Vision request image count is outside FarmTact limits")
        content: list[dict[str, Any]] = [{"type": "text", "text": prompt}]
        content.extend(
            {"type": "image_url", "image_url": {"url": item._data_url, "detail": "original"}}
            for item in images
        )
        payload = self._payload(
            route,
            [{"role": "user", "content": content}],
            max_tokens=max_tokens,
            thinking="disabled",
            response_format={"type": "json_object"},
        )
        raw = self._chat_raw(payload, role=role)
        return self._public_json(raw, route, role, output_model, execution_mode, data_mode)

    def stream_text(
        self,
        role: str,
        messages: Sequence[Mapping[str, Any]],
        *,
        max_tokens: int = 256,
        thinking: ThinkingMode = "disabled",
        execution_mode: str = "test",
        data_mode: str = "synthetic_demo",
    ) -> PublicCompletion[None]:
        self._validate_modes(execution_mode, data_mode)
        route = self._route(role, "text")
        payload = self._payload(route, messages, max_tokens=max_tokens, thinking=thinking, stream=True)
        encoded = _encode_payload(payload, self.config.limits.max_request_bytes)
        self.budget.reserve(max_tokens)
        started = time.monotonic()
        content_parts: list[str] = []
        private_reasoning_parts: list[str] = []
        finish_reason: str | None = None
        returned_model: str | None = None
        usage = Usage()
        request_id: str | None = None
        saw_done = False
        try:
            if not self._concurrency.acquire(blocking=False):
                raise DeepSeekBlockedError("DeepSeek concurrency budget exhausted")
            try:
                with self._client.stream(
                    "POST",
                    self.config.chat_path,
                    content=encoded,
                    timeout=self._request_timeout(),
                ) as response:
                    self._ensure_wall_available()
                    request_id = _safe_request_id(response.headers)
                    if 300 <= response.status_code < 400:
                        raise DeepSeekPolicyError("DeepSeek redirect rejected", status_code=response.status_code)
                    if response.status_code != 200:
                        raise _status_error(response.status_code, request_id)
                    for line in self._bounded_response_lines(response):
                        stripped = line.strip()
                        if not stripped or stripped.startswith(":"):
                            continue
                        if not stripped.startswith("data:"):
                            raise DeepSeekResponseError("DeepSeek stream contains an invalid SSE field")
                        data = stripped[5:].strip()
                        if data == "[DONE]":
                            saw_done = True
                            break
                        try:
                            chunk = json.loads(data)
                        except json.JSONDecodeError as exc:
                            raise DeepSeekResponseError("DeepSeek stream contains invalid JSON") from exc
                        if not isinstance(chunk, dict):
                            raise DeepSeekResponseError("DeepSeek stream chunk is not an object")
                        if isinstance(chunk.get("model"), str):
                            returned_model = chunk["model"]
                        if chunk.get("usage") is not None:
                            usage = Usage.from_wire(chunk["usage"])
                        choices = chunk.get("choices")
                        if not isinstance(choices, list):
                            raise DeepSeekResponseError("DeepSeek stream choices are invalid")
                        for choice in choices:
                            if not isinstance(choice, dict):
                                raise DeepSeekResponseError("DeepSeek stream choice is invalid")
                            delta = choice.get("delta")
                            if not isinstance(delta, dict):
                                raise DeepSeekResponseError("DeepSeek stream delta is invalid")
                            if delta.get("tool_calls"):
                                raise DeepSeekResponseError("Streamed tool calls are disabled")
                            if isinstance(delta.get("content"), str):
                                content_parts.append(delta["content"])
                            if isinstance(delta.get("reasoning_content"), str):
                                private_reasoning_parts.append(delta["reasoning_content"])
                            if choice.get("finish_reason") is not None:
                                finish_reason = choice["finish_reason"]
            finally:
                self._concurrency.release()
        except httpx.HTTPError as exc:
            raise DeepSeekBlockedError("DeepSeek transport request failed") from exc
        latency_ms = round((time.monotonic() - started) * 1000)
        private_reasoning_parts.clear()
        if not saw_done or finish_reason != "stop" or not "".join(content_parts).strip():
            raise DeepSeekResponseError("DeepSeek stream ended incomplete")
        self._validate_returned_model(route.model, returned_model)
        audit = self._audit(
            route, role, returned_model or "", execution_mode, data_mode,
            hashlib.sha256(encoded).hexdigest(), request_id, latency_ms, usage,
        )
        return PublicCompletion("".join(content_parts), None, returned_model or "", finish_reason, usage, audit)

    def normalize_image(self, source: bytes, *, asset_id: str) -> NormalizedImage:
        if not asset_id or len(asset_id) > 128:
            raise DeepSeekPolicyError("Image asset_id is missing or too long")
        if not source or len(source) > self.config.limits.max_image_bytes:
            raise DeepSeekPolicyError("Source image is outside FarmTact byte limits")
        source_hash = hashlib.sha256(source).hexdigest()
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("error", Image.DecompressionBombWarning)
                with Image.open(io.BytesIO(source)) as opened:
                    if getattr(opened, "n_frames", 1) != 1:
                        raise DeepSeekPolicyError("Animated images are not accepted")
                    if opened.format not in {"PNG", "JPEG", "GIF", "WEBP"}:
                        raise DeepSeekPolicyError("Unsupported image content")
                    if max(opened.size) > self.config.limits.max_image_dimension:
                        raise DeepSeekPolicyError("Image dimensions exceed FarmTact limits")
                    opened.load()
                    normalized = opened.convert("RGBA" if opened.mode in {"RGBA", "LA"} else "RGB")
                    width, height = normalized.size
                    output = io.BytesIO()
                    normalized.save(output, format="PNG", optimize=True)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise DeepSeekPolicyError("Image bytes could not be safely decoded") from exc
        png = output.getvalue()
        if len(png) > self.config.limits.max_image_bytes:
            raise DeepSeekPolicyError("Normalized image exceeds FarmTact byte limits")
        data_url = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
        return NormalizedImage(
            asset_id=asset_id,
            source_sha256=source_hash,
            normalized_sha256=hashlib.sha256(png).hexdigest(),
            width=width,
            height=height,
            byte_count=len(png),
            _data_url=data_url,
        )

    def _route(self, role: str, capability: Literal["text", "vision"]) -> Route:
        route = self.config.routes.get(role)
        if route is None:
            raise DeepSeekPolicyError("Unknown runtime role")
        if route.capability != capability:
            raise DeepSeekPolicyError("Runtime role does not support requested capability")
        return route

    def _validate_modes(self, execution_mode: str, data_mode: str) -> None:
        if execution_mode != "test":
            raise DeepSeekPolicyError("Authenticated development inference requires execution_mode=test")
        if data_mode not in {"synthetic_demo", "historical_replay"}:
            raise DeepSeekPolicyError("Development inference data mode is not permitted")

    def _payload(
        self,
        route: Route,
        messages: Sequence[Mapping[str, Any]],
        *,
        max_tokens: int,
        thinking: ThinkingMode,
        reasoning_effort: ReasoningEffort | None = None,
        response_format: Mapping[str, str] | None = None,
        tools: Sequence[Mapping[str, Any]] | None = None,
        tool_choice: str | None = None,
        stream: bool = False,
    ) -> dict[str, Any]:
        if not isinstance(max_tokens, int) or isinstance(max_tokens, bool) or not 1 <= max_tokens <= 4096:
            raise DeepSeekPolicyError("Per-request max_tokens is outside FarmTact limits")
        clean_messages = [dict(message) for message in messages]
        self._validate_messages(clean_messages, route)
        payload: dict[str, Any] = {
            "model": route.model,
            "messages": clean_messages,
            "max_tokens": max_tokens,
            "thinking": {"type": thinking},
            "user_id": self._user_id,
        }
        if reasoning_effort is not None:
            if thinking != "enabled":
                raise DeepSeekPolicyError("Reasoning effort requires enabled thinking")
            payload["reasoning_effort"] = reasoning_effort
        if response_format is not None:
            payload["response_format"] = dict(response_format)
        if tools is not None:
            if any(tool.get("function", {}).get("strict") for tool in tools):
                raise DeepSeekPolicyError("Strict tools require a separately reviewed beta adapter")
            payload["tools"] = [dict(tool) for tool in tools]
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if stream:
            payload["stream"] = True
            payload["stream_options"] = {"include_usage": True}
        return payload

    def _validate_messages(self, messages: Sequence[Mapping[str, Any]], route: Route) -> None:
        if not messages:
            raise DeepSeekPolicyError("At least one message is required")
        for message in messages:
            role = message.get("role")
            if role not in {"system", "user", "assistant", "tool"}:
                raise DeepSeekPolicyError("Invalid message role")
            content = message.get("content")
            if isinstance(content, list):
                if role != "user" or route.capability != "vision":
                    raise DeepSeekPolicyError("Images require a user message and vision route")
                image_count = 0
                for part in content:
                    if not isinstance(part, dict) or part.get("type") not in {"text", "image_url"}:
                        raise DeepSeekPolicyError("Unsupported vision content part")
                    if part.get("type") == "image_url":
                        image_count += 1
                        image_url = part.get("image_url")
                        url = image_url.get("url") if isinstance(image_url, dict) else None
                        if not isinstance(url, str) or not url.startswith("data:image/png;base64,"):
                            raise DeepSeekPolicyError("Only normalized inline PNG images are accepted")
                if image_count > self.config.limits.max_images_per_request:
                    raise DeepSeekPolicyError("Too many images")
            elif content is not None and not isinstance(content, str):
                raise DeepSeekPolicyError("Message content must be text or reviewed vision parts")

    def _chat_raw(
        self,
        payload: Mapping[str, Any],
        *,
        role: str,
        allowed_finish_reasons: set[str] | None = None,
    ) -> _RawCompletion:
        reserve = payload.get("max_tokens")
        wire, request_id, latency_ms, input_hash = self._request_json(
            "POST", self.config.chat_path, payload, reserve_tokens=int(reserve) if isinstance(reserve, int) else 0
        )
        choices = wire.get("choices")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], dict):
            raise DeepSeekResponseError("DeepSeek returned an invalid choice set")
        choice = choices[0]
        finish = choice.get("finish_reason")
        accepted = allowed_finish_reasons or {"stop"}
        if finish not in accepted:
            raise DeepSeekResponseError("DeepSeek completion did not finish successfully")
        message = choice.get("message")
        if not isinstance(message, dict) or message.get("role") != "assistant":
            raise DeepSeekResponseError("DeepSeek returned an invalid assistant message")
        returned_model = wire.get("model")
        requested_model = payload.get("model")
        if not isinstance(requested_model, str):
            raise DeepSeekPolicyError("Missing server-selected model")
        self._validate_returned_model(requested_model, returned_model)
        return _RawCompletion(
            message=message,
            model=returned_model,
            finish_reason=finish,
            usage=Usage.from_wire(wire.get("usage")),
            request_id=request_id,
            latency_ms=latency_ms,
            input_sha256=input_hash,
        )

    def _request_json(
        self,
        method: str,
        path: str,
        payload: Mapping[str, Any] | None,
        *,
        reserve_tokens: int,
    ) -> tuple[dict[str, Any], str | None, int, str]:
        if path not in {self.config.models_path, self.config.chat_path}:
            raise DeepSeekPolicyError("Unreviewed DeepSeek path")
        encoded = b"" if payload is None else _encode_payload(payload, self.config.limits.max_request_bytes)
        self.budget.reserve(reserve_tokens)
        started = time.monotonic()
        try:
            if not self._concurrency.acquire(blocking=False):
                raise DeepSeekBlockedError("DeepSeek concurrency budget exhausted")
            try:
                with self._client.stream(
                    method,
                    path,
                    content=encoded or None,
                    timeout=self._request_timeout(),
                ) as response:
                    self._ensure_wall_available()
                    request_id = _safe_request_id(response.headers)
                    if 300 <= response.status_code < 400:
                        raise DeepSeekPolicyError(
                            "DeepSeek redirect rejected", status_code=response.status_code
                        )
                    if response.status_code != 200:
                        raise _status_error(response.status_code, request_id)
                    body = self._read_bounded_response(response)
            finally:
                self._concurrency.release()
        except httpx.HTTPError as exc:
            raise DeepSeekBlockedError("DeepSeek transport request failed") from exc
        latency_ms = round((time.monotonic() - started) * 1000)
        try:
            wire = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise DeepSeekResponseError("DeepSeek response is not valid JSON") from exc
        if not isinstance(wire, dict):
            raise DeepSeekResponseError("DeepSeek response is not a JSON object")
        return wire, request_id, latency_ms, hashlib.sha256(encoded).hexdigest()

    def _request_timeout(self) -> httpx.Timeout:
        remaining = self.budget.remaining_seconds()
        if remaining <= 0:
            raise DeepSeekBlockedError("DeepSeek run wall-clock budget exhausted")
        limits = self.config.limits
        return httpx.Timeout(
            connect=min(limits.connect_timeout_seconds, remaining),
            read=min(limits.read_timeout_seconds, remaining),
            write=min(limits.write_timeout_seconds, remaining),
            pool=min(limits.pool_timeout_seconds, remaining),
        )

    def _ensure_wall_available(self) -> None:
        if self.budget.remaining_seconds() <= 0:
            raise DeepSeekBlockedError("DeepSeek run wall-clock budget exhausted")

    def _read_bounded_response(self, response: httpx.Response) -> bytes:
        body = bytearray()
        for chunk in response.iter_bytes(chunk_size=65_536):
            self._ensure_wall_available()
            if len(body) + len(chunk) > self.config.limits.max_response_bytes:
                raise DeepSeekResponseError("DeepSeek response exceeds byte limit")
            body.extend(chunk)
        self._ensure_wall_available()
        return bytes(body)

    def _bounded_response_lines(self, response: httpx.Response):
        """Yield UTF-8 lines while bounding bytes even without a newline."""

        buffer = bytearray()
        total = 0
        for chunk in response.iter_bytes(chunk_size=65_536):
            self._ensure_wall_available()
            total += len(chunk)
            if total > self.config.limits.max_response_bytes:
                raise DeepSeekResponseError("DeepSeek stream exceeds response limit")
            buffer.extend(chunk)
            while True:
                newline = buffer.find(b"\n")
                if newline < 0:
                    break
                raw_line = bytes(buffer[:newline])
                del buffer[: newline + 1]
                try:
                    yield raw_line.rstrip(b"\r").decode("utf-8")
                except UnicodeDecodeError as exc:
                    raise DeepSeekResponseError("DeepSeek stream is not valid UTF-8") from exc
        self._ensure_wall_available()
        if buffer:
            try:
                yield bytes(buffer).rstrip(b"\r").decode("utf-8")
            except UnicodeDecodeError as exc:
                raise DeepSeekResponseError("DeepSeek stream is not valid UTF-8") from exc

    def _public_json(
        self,
        raw: _RawCompletion,
        route: Route,
        role: str,
        output_model: type[T] | Any,
        execution_mode: str,
        data_mode: str,
    ) -> PublicCompletion[T]:
        content = raw.message.get("content")
        if not isinstance(content, str) or not content.strip():
            raise DeepSeekResponseError("DeepSeek returned empty structured content")
        try:
            parsed = json.loads(content)
            validated = TypeAdapter(output_model).validate_python(parsed)
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            raise DeepSeekResponseError("DeepSeek structured output failed local validation") from exc
        audit = self._audit(
            route, role, raw.model, execution_mode, data_mode, raw.input_sha256,
            raw.request_id, raw.latency_ms, raw.usage,
        )
        return PublicCompletion(content, validated, raw.model, raw.finish_reason, raw.usage, audit)

    def _audit(
        self,
        route: Route,
        role: str,
        returned_model: str,
        execution_mode: str,
        data_mode: str,
        input_hash: str,
        request_id: str | None,
        latency_ms: int,
        usage: Usage,
    ) -> SafeAudit:
        self._validate_modes(execution_mode, data_mode)
        return SafeAudit(
            provider="deepseek",
            requested_model=route.model,
            returned_model=returned_model,
            role=role,
            capability=route.capability,
            execution_mode=execution_mode,
            data_mode=data_mode,
            inference_origin="deepseek_api",
            input_sha256=input_hash,
            request_id=request_id,
            latency_ms=latency_ms,
            usage=usage,
        )

    def _validate_returned_model(self, requested: str, returned: object) -> None:
        if not isinstance(returned, str) or returned != requested or returned not in self.config.allowed_models:
            raise DeepSeekResponseError("DeepSeek returned an unexpected model")


def _encode_payload(payload: Mapping[str, Any], max_bytes: int) -> bytes:
    try:
        encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DeepSeekPolicyError("Request payload is not serializable") from exc
    if len(encoded) > max_bytes:
        raise DeepSeekPolicyError("DeepSeek request exceeds FarmTact byte limit")
    return encoded


def provider_user_id_for_tenant(tenant_id: str) -> str:
    """Return a stable provider pseudonym without disclosing the internal tenant ID."""

    if not isinstance(tenant_id, str) or not 1 <= len(tenant_id) <= 200:
        raise DeepSeekPolicyError("Internal tenant identifier is outside reviewed bounds")
    digest = hashlib.sha256(tenant_id.encode("utf-8")).hexdigest()
    return f"farmtact_{digest}"


def _status_error(status_code: int, request_id: str | None) -> DeepSeekGatewayError:
    suffix = f" (request {request_id})" if request_id else ""
    if status_code in {401, 402, 403, 429} or status_code >= 500:
        return DeepSeekBlockedError(f"DeepSeek request blocked with HTTP {status_code}{suffix}", status_code=status_code)
    return DeepSeekResponseError(f"DeepSeek rejected the request with HTTP {status_code}{suffix}", status_code=status_code)


def _safe_request_id(headers: httpx.Headers) -> str | None:
    value = headers.get("x-request-id") or headers.get("request-id")
    if value and 0 < len(value) <= 128 and all(char.isalnum() or char in "-_." for char in value):
        return value
    return None


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) and value >= 0 else None
