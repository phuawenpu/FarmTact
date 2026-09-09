#!/usr/bin/env python3
"""Run the bounded authenticated DeepSeek capability and council trial."""

from __future__ import annotations

import argparse
import io
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, ConfigDict, Field


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from runtime.deepseek_gateway import (  # noqa: E402
    DeepSeekGateway,
    DeepSeekGatewayError,
    RunBudget,
    ToolSpec,
)


from packages.agents import ROLES, ROLE_EXPERTISE

CONFIG = ROOT / "config/deepseek_runtime.json"
REPORT_DIR = ROOT / "reports/deepseek"


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FlashProbe(StrictModel):
    status: Literal["ok"]
    capability: Literal["json"]
    marker: Literal[17]


class ProProbe(StrictModel):
    crop_id: Literal["caixin"]
    delivery_window_days: Literal[7]
    new_crop_lead_time_days: Literal[35]
    new_sowing_can_meet_delivery: Literal[False]


class SupplyToolArgs(StrictModel):
    crop_id: Literal["caixin"]
    horizon_days: Literal[7]


class ToolProbe(StrictModel):
    crop_id: Literal["caixin"]
    near_term_supply_kg: float
    order_kg: float
    shortfall_kg: float
    new_sowing_can_close_shortfall: Literal[False]
    source_tool: Literal["get_supply_snapshot"]


class VisionProbe(StrictModel):
    # Vision models may add useful uncertainty fields. Required FarmTact fields
    # remain validated and their exact provenance values are checked below.
    model_config = ConfigDict(extra="ignore")
    asset_id: str
    source_sha256: str
    batch_id: str
    visible_findings: list[str] = Field(min_length=1, max_length=5)
    unknowns: list[str] = Field(min_length=1, max_length=5)
    ambiguity: str
    review_status: Literal["proposed_observation"]


class CouncilOutput(StrictModel):
    role: str
    recommendation: str = Field(min_length=1, max_length=800)
    new_sowing_can_meet_seven_day_delivery: Literal[False]
    evidence_refs: list[str] = Field(min_length=1, max_length=8)
    risks: list[str] = Field(min_length=1, max_length=5)


def _image_fixture() -> bytes:
    batch_id = "SG-CX-4827"
    image = Image.new("RGB", (1100, 520), "white")
    draw = ImageDraw.Draw(image)
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
    ]
    font = None
    for font_path in font_paths:
        try:
            font = ImageFont.truetype(font_path, 92)
            break
        except OSError:
            continue
    if font is None:
        font = ImageFont.load_default(size=72)
    draw.rectangle((25, 25, 1075, 495), outline="darkgreen", width=12)
    draw.text((80, 85), "SYNTHETIC CAIXIN", fill="darkgreen", font=font)
    draw.text((80, 250), f"BATCH {batch_id}", fill="black", font=font)
    output = io.BytesIO()
    image.save(output, "PNG")
    return output.getvalue()


def _frozen_snapshot_and_plans() -> tuple[dict, list[dict]]:
    snapshot = {
        "snapshot_id": "synthetic-caixin-2026-09-08",
        "data_mode": "synthetic_demo",
        "crop_id": "caixin",
        "order_kg": 20.0,
        "delivery_window_days": 7,
        "inventory_kg": 9.0,
        "validated_mature_harvest_kg": 6.0,
        "new_crop_lead_time_days": 35,
        "evidence_refs": [
            "synthetic-order-001",
            "inventory-lot-001",
            "mature-batch-001",
            "recipe-caixin-demo-v1",
            "solver-run-toy-v1",
        ],
    }
    available = snapshot["inventory_kg"] + snapshot["validated_mature_harvest_kg"]
    gap = max(0.0, snapshot["order_kg"] - available)
    plans = [
        {
            "strategy_id": "lean-v1",
            "policy": "Lean",
            "farm_supply_kg": available,
            "partner_supply_kg": 0.0,
            "planned_delivery_kg": available,
            "shortfall_kg": gap,
            "feasible": False,
            "new_sowing_for_this_delivery_kg": 0.0,
        },
        {
            "strategy_id": "balanced-v1",
            "policy": "Balanced",
            "farm_supply_kg": available,
            "partner_supply_kg": gap,
            "planned_delivery_kg": snapshot["order_kg"],
            "shortfall_kg": 0.0,
            "feasible": True,
            "new_sowing_for_this_delivery_kg": 0.0,
        },
        {
            "strategy_id": "resilient-v1",
            "policy": "Resilient",
            "farm_supply_kg": available,
            "partner_supply_kg": gap + 1.0,
            "planned_delivery_kg": snapshot["order_kg"],
            "buffer_kg": 1.0,
            "shortfall_kg": 0.0,
            "feasible": True,
            "new_sowing_for_this_delivery_kg": 0.0,
        },
    ]
    return snapshot, plans


def _record_completion(result) -> dict:
    return {
        "status": "PASS",
        "model": result.model,
        "finish_reason": result.finish_reason,
        "validated_content": result.data.model_dump(mode="json") if result.data is not None else result.content,
        "audit": asdict(result.audit),
    }


def _write_report(report: dict) -> Path:
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = REPORT_DIR / f"deepseek_authenticated_trial_{stamp}.json"
    text = json.dumps(report, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    (REPORT_DIR / "latest.json").write_text(text, encoding="utf-8")
    return path


def _load_resume(path: Path | None) -> tuple[dict | None, int, int]:
    if path is None:
        return None, 0, 0
    prior = json.loads(path.read_text(encoding="utf-8"))
    expected_passes = {"model_discovery", "flash_json", "pro_json"}
    capabilities = prior.get("capabilities", {})
    tool_already_passed = capabilities.get("thinking_tool_continuation", {}).get("status") == "PASS"
    core_already_passed = (
        tool_already_passed
        and capabilities.get("vision_json", {}).get("status") == "PASS"
        and capabilities.get("streaming", {}).get("status") == "PASS"
    )
    if prior.get("trial_version") == "3-explicit-vision-schema" and prior.get("actual_request_count") == 9 and core_already_passed:
        expected_count = 9
        expected_failure = "DeepSeek structured output failed local validation"
    elif prior.get("trial_version") == "2-short-json-council" and prior.get("actual_request_count") == 6:
        expected_count = 6
        expected_failure = "DeepSeek structured output failed local validation"
    elif core_already_passed:
        expected_count = 10
        expected_failure = "DeepSeek completion did not finish successfully"
    elif tool_already_passed:
        expected_count = 7
        expected_failure = "DeepSeek structured output failed local validation"
    else:
        expected_count = 4
        expected_failure = "DeepSeek rejected the request with HTTP 400"
    if (
        prior.get("provider") != "deepseek"
        or prior.get("origin") != "https://api.deepseek.com"
        or prior.get("overall_status") != "BLOCKED"
        or not expected_passes.issubset(capabilities)
        or any(capabilities[key].get("status") != "PASS" for key in expected_passes)
        or prior.get("actual_request_count") != expected_count
        or prior.get("failure", {}).get("safe_message") != expected_failure
    ):
        raise ValueError("Resume report is not the expected stopped tool-compatibility trial")
    return prior, int(prior["actual_request_count"]), int(prior["reserved_output_tokens"])


def run_trial(with_council: bool, resume_path: Path | None = None) -> tuple[dict, int]:
    prior, prior_requests, prior_tokens = _load_resume(resume_path)
    report: dict = {
        "schema_version": "1.0",
        "trial_version": "5-seven-agent-council",
        "trial": "DS-G1+DS-G2" if with_council else "DS-G1",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "development_phase": "autonomous_development",
        "decision_policy": "automatic_development",
        "execution_mode": "test",
        "data_mode": "synthetic_demo",
        "provider": "deepseek",
        "origin": "https://api.deepseek.com",
        "retry_policy": "none",
        "request_ceiling": 16,
        "planned_request_count": 7 + len(ROLES) if with_council else 7,
        "reserved_output_token_ceiling": 8192,
        "wall_clock_ceiling_seconds": 300,
        "capabilities": {},
        "council": {"status": "NOT_RUN"},
        "overall_status": "RUNNING",
    }
    if prior is not None:
        report["resume"] = {
            "prior_report": str(resume_path),
            "reason": "Corrected probe prompt/schema or documented compatibility; passing probes reused with prior requests and token reservations counted.",
            "prior_request_count_included": prior_requests,
        }
        reusable_names = (
            "model_discovery",
            "flash_json",
            "pro_json",
            "thinking_tool_continuation",
            "vision_json",
            "streaming",
        )
        reused = [
            name for name in reusable_names
            if prior["capabilities"].get(name, {}).get("status") == "PASS"
        ]
        report["capabilities"].update({key: prior["capabilities"][key] for key in reused})
        remaining = len(ROLES) if with_council else 0
        if "thinking_tool_continuation" not in reused:
            remaining += 2
        if "vision_json" not in reused:
            remaining += 1
        if "streaming" not in reused:
            remaining += 1
        report["planned_request_count"] = prior_requests + remaining
    budget = RunBudget(
        max_requests=16,
        max_reserved_output_tokens=8192,
        max_wall_seconds=300,
        request_count=prior_requests,
        reserved_output_tokens=prior_tokens,
    )
    try:
        if report["planned_request_count"] > report["request_ceiling"]:
            raise RuntimeError("The requested trial does not fit the existing request ceiling; no calls started")
        with DeepSeekGateway.from_config(CONFIG, budget=budget) as gateway:
            if prior is None:
                models = gateway.list_models()
                required_models = {
                    "deepseek-v4-flash",
                    "deepseek-v4-pro",
                    "deepseek-v4-flash-vision-exp",
                }
                missing = sorted(required_models - models)
                if missing:
                    raise RuntimeError("Required reviewed model aliases are not all available to this account")
                report["capabilities"]["model_discovery"] = {
                    "status": "PASS",
                    "required_models_available": True,
                    "reviewed_models_discovered": sorted(models & required_models),
                }

                flash = gateway.chat_json(
                    "demand_analyst",
                    [{"role": "user", "content": "Return only a JSON object with status 'ok', capability 'json', and integer marker 17."}],
                    FlashProbe,
                    max_tokens=128,
                    thinking="disabled",
                )
                report["capabilities"]["flash_json"] = _record_completion(flash)

                pro = gateway.chat_json(
                    "production_analyst",
                    [{
                        "role": "user",
                        "content": (
                            "Return only JSON with crop_id 'caixin', delivery_window_days 7, "
                            "new_crop_lead_time_days 35, and new_sowing_can_meet_delivery false. "
                            "The durations are supplied test facts; do not calculate or alter them."
                        ),
                    }],
                    ProProbe,
                    max_tokens=128,
                    thinking="disabled",
                )
                report["capabilities"]["pro_json"] = _record_completion(pro)

            if "thinking_tool_continuation" not in report["capabilities"]:
                tool = ToolSpec(
                    "get_supply_snapshot",
                    "Return validated synthetic caixin supply and order quantities for a bounded horizon.",
                    SupplyToolArgs,
                )

                def execute_tool(name: str, args: BaseModel) -> dict:
                    if name != "get_supply_snapshot" or args.crop_id != "caixin" or args.horizon_days != 7:
                        raise RuntimeError("Tool authorization scope mismatch")
                    return {
                        "crop_id": "caixin",
                        "horizon_days": 7,
                        "near_term_supply_kg": 12.4,
                        "order_kg": 20.0,
                        "shortfall_kg": 7.6,
                        "new_crop_lead_time_days": 35,
                        "source_ref": "synthetic-tool-snapshot-001",
                    }

                tool_result = gateway.run_tool_json(
                    "demand_analyst",
                    [{
                        "role": "user",
                        "content": (
                            "Call get_supply_snapshot for caixin and a 7-day horizon. Then return only a JSON object "
                            "with crop_id, near_term_supply_kg, order_kg, shortfall_kg, "
                            "new_sowing_can_close_shortfall, and source_tool='get_supply_snapshot'. "
                            "Use the tool quantities exactly and recognize that a 35-day new crop cannot close a 7-day gap."
                        ),
                    }],
                    [tool],
                    execute_tool,
                    ToolProbe,
                    max_tokens_each=256,
                    thinking="enabled",
                    reasoning_effort="low",
                )
                if abs(tool_result.data.shortfall_kg - 7.6) > 1e-6 or abs(tool_result.data.near_term_supply_kg - 12.4) > 1e-6:
                    raise RuntimeError("Tool continuation changed validated numerical tool output")
                report["capabilities"]["thinking_tool_continuation"] = _record_completion(tool_result)
                report["capabilities"]["thinking_tool_continuation"]["private_reasoning_retention"] = (
                    "preserved in-memory for continuation and excluded from report"
                )

            if "vision_json" not in report["capabilities"]:
                source_image = _image_fixture()
                normalized = gateway.normalize_image(source_image, asset_id="synthetic-vision-probe")
                vision = gateway.vision_json(
                    prompt=(
                        "Read the batch identifier visible in this synthetic image. Return only JSON containing "
                        "asset_id='synthetic-vision-probe', source_sha256='"
                        + normalized.source_sha256
                        + "', batch_id copied from the image, one or more visible_findings, one or more unknowns "
                        "including that yield cannot be inferred, a concise ambiguity string, and "
                        "review_status='proposed_observation'. The batch identifier is intentionally absent from this text. All visible_findings and unknowns entries must be plain strings; ambiguity must be a string. Exact JSON schema: " + json.dumps(VisionProbe.model_json_schema())
                    ),
                    images=[normalized],
                    output_model=VisionProbe,
                    max_tokens=512,
                )
                if (
                    vision.data.asset_id != normalized.asset_id
                    or vision.data.source_sha256 != normalized.source_sha256
                    or vision.data.batch_id.strip().upper() != "SG-CX-4827"
                ):
                    raise RuntimeError("Vision response did not read the image-only batch identifier")
                report["capabilities"]["vision_json"] = _record_completion(vision)
                report["capabilities"]["vision_json"]["image_transport"] = {
                    "asset_id": normalized.asset_id,
                    "source_sha256": normalized.source_sha256,
                    "normalized_sha256": normalized.normalized_sha256,
                    "width": normalized.width,
                    "height": normalized.height,
                    "normalized_bytes": normalized.byte_count,
                    "raw_or_base64_persisted": False,
                }

            if "streaming" not in report["capabilities"]:
                stream = gateway.stream_text(
                    "demand_analyst",
                    [{"role": "user", "content": "Reply with exactly FARMTACT_STREAM_OK and no other text."}],
                    max_tokens=64,
                    thinking="disabled",
                )
                if stream.content.strip() != "FARMTACT_STREAM_OK":
                    raise RuntimeError("Streaming content marker did not match")
                report["capabilities"]["streaming"] = _record_completion(stream)

            if with_council:
                snapshot, plans = _frozen_snapshot_and_plans()
                role_prompts = [(role, ROLE_EXPERTISE[role]) for role in ROLES]
                known_refs = set(snapshot["evidence_refs"])
                council_results: list[dict] = []
                report["council"] = {"status": "RUNNING", "role_results": council_results}
                for role, instruction in role_prompts:
                    prompt = {
                        "instruction": instruction + " Return every required field. evidence_refs and risks must be arrays of plain strings. recommendation must be one string, not an object.",
                        "json_schema": CouncilOutput.model_json_schema(),
                        "role": role,
                        "frozen_snapshot": snapshot,
                        "computed_plans": plans,
                        "output_contract": {
                            "role": role,
                            "recommendation": "one sentence under forty words; quantities must come from computed_plans",
                            "new_sowing_can_meet_seven_day_delivery": False,
                            "evidence_refs": "one or more IDs from frozen_snapshot.evidence_refs",
                            "risks": "one or more concise uncertainties",
                        },
                    }
                    result = gateway.chat_json(
                        role,
                        [{"role": "user", "content": "Return only JSON. " + json.dumps(prompt, separators=(",", ":"))}],
                        CouncilOutput,
                        max_tokens=768,
                        thinking="disabled",
                    )
                    if result.data.role != role:
                        raise RuntimeError("Council response role mismatch")
                    if not set(result.data.evidence_refs).issubset(known_refs):
                        raise RuntimeError("Council response cited evidence outside the frozen snapshot")
                    council_results.append(_record_completion(result))

                balanced = next(plan for plan in plans if plan["strategy_id"] == "balanced-v1")
                all_roles_present = {item["validated_content"]["role"] for item in council_results} == {
                    role for role, _ in role_prompts
                }
                lead_time_preserved = all(
                    item["validated_content"]["new_sowing_can_meet_seven_day_delivery"] is False
                    for item in council_results
                )
                eligible = bool(
                    all_roles_present
                    and lead_time_preserved
                    and balanced["feasible"]
                    and balanced["shortfall_kg"] == 0.0
                    and snapshot["data_mode"] == "synthetic_demo"
                )
                if not eligible:
                    raise RuntimeError("Independent backend simulation-acceptance checks failed")
                report["council"] = {
                    "status": "PASS",
                    "snapshot": snapshot,
                    "computed_plans": plans,
                    "role_results": council_results,
                    "backend_validation": {
                        "all_seven_roles_present": all_roles_present,
                        "lead_time_preserved": lead_time_preserved,
                        "selected_strategy_feasible": True,
                        "planner_completed": True,
                    },
                    "decision_event": {
                        "event_type": "ACCEPTED_FOR_SIMULATION",
                        "strategy_id": "balanced-v1",
                        "actor": "service:farmtact-development-policy",
                        "policy_version": "automatic-development-v1",
                        "execution_mode": "test",
                        "data_mode": "synthetic_demo",
                        "operational_live_promotion": "disabled",
                        "human_approval_event": False,
                    },
                    "scope_note": "Transport/workflow seed; not a finished optimizer or evidence of production benefit.",
                }

            expected = report["planned_request_count"]
            if budget.request_count != expected:
                raise RuntimeError(f"Trial request count was {budget.request_count}; expected {expected}")
            report["overall_status"] = "PASS"
    except (DeepSeekGatewayError, RuntimeError, ValueError) as exc:
        report["overall_status"] = "BLOCKED" if isinstance(exc, DeepSeekGatewayError) else "FAIL"
        report["failure"] = {
            "error_type": type(exc).__name__,
            "error_code": getattr(exc, "code", "trial_validation_error"),
            "safe_message": str(exc),
        }
    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["actual_request_count"] = budget.request_count
    report["reserved_output_tokens"] = budget.reserved_output_tokens
    return report, 0 if report["overall_status"] == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true", help="Perform real authenticated DeepSeek HTTP calls")
    parser.add_argument("--with-council", action="store_true", help="Add the seven-role synthetic council trial")
    parser.add_argument("--resume", type=Path, help="Resume the recorded stopped compatibility trial within its original budget")
    args = parser.parse_args()
    if not args.live:
        parser.error("--live is required; offline contracts use pytest")
    if os.environ.get("FARMTACT_EXECUTION_MODE") != "test":
        parser.error("FARMTACT_EXECUTION_MODE=test is required for authenticated development calls")
    report, exit_code = run_trial(args.with_council, args.resume)
    path = _write_report(report)
    print(f"DeepSeek trial {report['overall_status']}; requests={report['actual_request_count']}; report={path}")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
