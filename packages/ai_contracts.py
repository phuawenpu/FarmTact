"""Versioned, provider-neutral contracts for FarmTact AI interpretation.

Models never author authoritative quantities.  They select frozen reference IDs;
this module attaches the value, unit, entity and period that FarmTact already knows
and returns a code-rendered fact for persistence and display.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re
from typing import Any, Literal, Mapping, Sequence


PROMPT_TEMPLATE_VERSION = "farmtact-advisor-prompt-v5"
MISSION_PROMPT_TEMPLATE_VERSION = "farmtact-mission-council-prompt-v6"
OUTPUT_SCHEMA_VERSION = "farmtact-advisor-output-v3"
VALIDATOR_VERSION = "farmtact-ai-evidence-validator-v4"
CONTEXT_VERSION = "farmtact-frozen-ai-context-v3"
CONVERSATION_CONTEXT_VERSION = "farmtact-conversation-context-v5"
MISSION_CONTEXT_VERSION = "farmtact-mission-context-v6"
SOURCE_CONTEXT_VERSION = "farmtact-source-context-v3"
RESPONSE_LIMITS = {
    "content_characters": 400,
    "evidence_refs": 1,
    "tool_refs": 3,
    "fact_refs": 3,
    "highlight_refs": 1,
    "proposed_actions": 1,
}

FactKind = Literal["quantity", "date", "category", "status"]


@dataclass(frozen=True)
class InferenceVersions:
    prompt_template: str
    output_schema: str = OUTPUT_SCHEMA_VERSION
    validator: str = VALIDATOR_VERSION
    context: str = CONTEXT_VERSION
    sources: str = SOURCE_CONTEXT_VERSION

    def public(self) -> dict[str, str]:
        return asdict(self)


CONVERSATION_VERSIONS = InferenceVersions(
    prompt_template=PROMPT_TEMPLATE_VERSION,
    context=CONVERSATION_CONTEXT_VERSION,
)
MISSION_VERSIONS = InferenceVersions(
    prompt_template=MISSION_PROMPT_TEMPLATE_VERSION,
    context=MISSION_CONTEXT_VERSION,
)


def canonical_hash(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode()
    ).hexdigest()


def _unit_for(reference: str) -> str | None:
    terminal = reference.rsplit(".", 1)[-1]
    explicit = {
        "cash_sgd": "SGD",
        "margin_sgd": "SGD",
        "profit_sgd": "SGD",
        "revenue_sgd": "SGD",
        "area_m2": "m2",
        "quantity_kg": "kg",
        "confirmed_kg": "kg",
        "residual_kg": "kg",
        "expected_kg": "kg",
        "marketable_kg": "kg",
        "expected_marketable_kg": "kg",
        "price_sgd_per_kg": "SGD/kg",
        "labour_hours_per_week": "hours/week",
        "nursery_sites": "sites",
        "nursery_days": "days",
        "grow_days": "days",
        "biological_lead_days": "days",
        "delay_days": "days",
        "fill_rate": "ratio",
    }
    if terminal in explicit:
        return explicit[terminal]
    if terminal.endswith("_kg"):
        return "kg"
    if terminal.endswith("_sgd"):
        return "SGD"
    if terminal.endswith("_hours"):
        return "hours"
    if terminal.endswith("_percent"):
        return "percent"
    return None


def _entity_for(reference: str) -> tuple[str, str] | tuple[None, None]:
    head = reference.split(":", 1)
    if len(head) != 2:
        return None, None
    namespace, tail = head
    identifier = tail.split(".", 1)[0]
    if namespace in {"bed", "batch", "delivery", "order", "recipe", "schedule", "source"}:
        return namespace, identifier
    if namespace == "forecast" and identifier.startswith("batch_"):
        return "batch", identifier.removeprefix("batch_")
    if namespace == "forecast" and ".week_" in tail:
        return "crop", identifier
    if namespace == "strategy":
        return "strategy", identifier
    if namespace in {"scenario", "comparison", "research"}:
        return namespace, identifier
    if namespace == "farm":
        return "farm", "frozen_snapshot"
    return None, None


def _period_for(reference: str, value: object) -> dict[str, str] | None:
    terminal = reference.rsplit(".", 1)[-1]
    if terminal in {"harvest_date", "due_date", "sow_date", "transplant_date", "start_date", "end_date", "cutoff"}:
        return {"kind": terminal, "value": str(value)}
    if ".week_" in reference:
        week = reference.split(".week_", 1)[1].split(".", 1)[0]
        return {"kind": "forecast_week", "value": week}
    return None


def _fact_kind(reference: str, value: object) -> FactKind | None:
    if isinstance(value, bool) or value is None:
        return None
    terminal = reference.rsplit(".", 1)[-1]
    if terminal in {"harvest_date", "due_date", "sow_date", "transplant_date", "start_date", "end_date", "cutoff", "observed_at", "retrieved_at"}:
        return "date"
    if isinstance(value, (int, float)):
        return "quantity"
    if isinstance(value, str) and _unit_for(reference) is not None:
        try:
            if Decimal(value).is_finite():
                return "quantity"
        except InvalidOperation:
            pass
    # Date objects should not occur after JSON conversion but remain supported.
    if isinstance(value, (date, datetime)):
        return "date"
    return None


def typed_reference_catalog(
    tool_results: Mapping[str, Any], *, snapshot_hash: str
) -> dict[str, dict[str, Any]]:
    """Build immutable typed facts from server-owned reference keys and values.

    Only scalar quantities and dates enter this catalogue.  Lists, prose and status
    objects remain contextual tool results and can never become numeric cards.
    """

    catalog: dict[str, dict[str, Any]] = {}
    for reference, value in tool_results.items():
        kind = _fact_kind(reference, value)
        if kind is None:
            continue
        unit = _unit_for(reference)
        if kind == "quantity" and unit is None and reference.endswith(".value"):
            candidate = tool_results.get(reference.removesuffix(".value") + ".unit")
            unit = str(candidate) if isinstance(candidate, str) and candidate else None
        # A number without a unit is metadata, an identifier or an underspecified
        # scalar; it cannot be exposed as an authoritative quantitative card.
        if kind == "quantity" and unit is None:
            continue
        entity_type, entity_id = _entity_for(reference)
        catalog[reference] = {
            "reference": reference,
            "kind": kind,
            "value": value,
            "unit": unit,
            "entity": (
                {"type": entity_type, "id": entity_id}
                if entity_type is not None and entity_id is not None
                else None
            ),
            "period": _period_for(reference, value),
            "context": reference.split(":", 1)[0],
            "snapshot_hash": snapshot_hash,
            "verification": "code_rendered_frozen_value",
        }
    return catalog


def render_facts(
    references: Sequence[str], catalog: Mapping[str, Mapping[str, Any]]
) -> list[dict[str, Any]]:
    """Resolve selected IDs without accepting a model-authored value or unit."""

    return [dict(catalog[reference]) for reference in references if reference in catalog]


def evidence_status(*, errors: Sequence[object], fact_refs: Sequence[str]) -> str:
    if errors:
        return "unsupported"
    if fact_refs:
        return "grounded_facts_qualitative_unverified"
    return "qualitative_unverified"


def quantitative_prose_present(statement: str) -> bool:
    """Conservatively detect model-authored quantities, dates and relative time."""

    checked = re.sub(
        r"\b(?:bed|batch|delivery|order|recipe)-[A-Za-z0-9-]+\b",
        " referenced-entity ",
        statement,
        flags=re.IGNORECASE,
    )
    if re.search(r"(?<![A-Za-z0-9_.])[-+]?\d[\d,]*(?:\.\d+)?(?![A-Za-z0-9_.])", checked):
        return True
    words = (
        "zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|"
        "thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|"
        "thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|"
        "billion|dozen|half|quarter|double|triple|twice|first|second|third|fourth|"
        "fifth|sixth|seventh|eighth|ninth|tenth|eleventh|twelfth|last|january|"
        "february|march|april|june|july|august|september|october|november|december|"
        "today|tomorrow|yesterday|tonight"
    )
    if re.search(rf"\b(?:{words})\b", statement, flags=re.IGNORECASE):
        return True
    return bool(
        re.search(
            r"\b(?:this|next|previous|coming|following)\s+(?:morning|afternoon|"
            r"evening|day|week|month|quarter|season|year|monday|tuesday|wednesday|"
            r"thursday|friday|saturday|sunday)\b",
            statement,
            flags=re.IGNORECASE,
        )
        or re.search(r"\bMay\s+(?:\d|first|second|third|fourth|fifth)", statement)
    )


def validated_turn_projection(message: Mapping[str, Any]) -> dict[str, Any]:
    """Bounded shared projection for later speakers, including rejection detail."""

    raw_issues = message.get("validation_issues")
    if not isinstance(raw_issues, list):
        raw_issues = [
            {"code": "legacy_validation_error", "message": str(item)[:160]}
            for item in message.get("validation_errors", [])[:8]
        ]
    issues = []
    for item in raw_issues[:8]:
        if isinstance(item, Mapping):
            issues.append(
                {
                    "code": str(item.get("code", "validation_error"))[:64],
                    "message": str(item.get("message", "Validation failed"))[:160],
                }
            )
    evidence = str(message.get("evidence_status") or "unknown")
    return {
        "id": message.get("id"),
        "speaker": message.get("speaker"),
        "speaker_id": message.get("speaker_id"),
        "content": str(message.get("content", ""))[:RESPONSE_LIMITS["content_characters"]],
        "reply_to": message.get("reply_to"),
        "evidence_refs": list(message.get("evidence_refs", []))[: RESPONSE_LIMITS["evidence_refs"]],
        "tool_refs": list(message.get("tool_refs", []))[: RESPONSE_LIMITS["tool_refs"]],
        "fact_refs": list(message.get("fact_refs", []))[: RESPONSE_LIMITS["fact_refs"]],
        "validation_status": message.get("validation_status"),
        "evidence_status": evidence,
        "validation_issues": issues,
        "eligible_as_evidence": evidence.startswith("grounded_facts") and not issues,
        "relationship": message.get("relationship"),
    }
