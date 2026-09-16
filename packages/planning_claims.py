"""Server-owned propositions for planning-session comparisons.

The Council may select these records, but it cannot alter their operands,
relationship, scope, or rendered statement.  Every proposition compares two
plans evaluated under the same frozen planning-session snapshot.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from math import isfinite
from typing import Any, Literal, TypedDict

from packages.ai_contracts import canonical_hash


Direction = Literal["increase", "decrease", "unchanged"]


class VerifiedPlanningClaim(TypedDict):
    id: str
    metric: str
    policy: str
    strategy_id: str
    baseline: float | dict[str, float] | list[str]
    scenario: float | dict[str, float] | list[str]
    delta: float | dict[str, float] | None
    direction: Direction | Literal["changed"]
    unit: str
    snapshot_hash: str
    statement: str
    claim_kind: Literal["strategy_metric", "metric_comparison", "crop_mix_comparison", "crop_mix_snapshot"]


_METRICS: dict[str, tuple[str, str]] = {
    "booked_delivered_kg": ("booked demand delivered", "kg"),
    "booked_shortfall_kg": ("booked demand shortfall", "kg"),
    "fill_rate": ("overall demand fill rate", "ratio"),
    "waste_kg": ("expired crop waste", "kg"),
    "closing_stock_kg": ("remaining terminal stock", "kg"),
    "margin_sgd": ("projected margin", "SGD"),
    "cost_sgd": ("projected cost", "SGD"),
    "revenue_sgd": ("projected revenue", "SGD"),
    "labour_hours": ("labour", "hours"),
    "area_m2": ("sown area", "m2"),
}


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return round(parsed, 6) if isfinite(parsed) else None


def _name(plan: dict[str, Any], fallback: str) -> str:
    return str(plan.get("name") or plan.get("policy") or plan.get("id") or fallback)


def _metrics(plan: dict[str, Any]) -> dict[str, Any]:
    value = plan.get("metrics")
    metrics = dict(value) if isinstance(value, dict) else {}
    requested, delivered = _number(metrics.get("booked_requested_kg")), _number(metrics.get("booked_delivered_kg"))
    if requested is not None and delivered is not None and "booked_shortfall_kg" not in metrics:
        metrics["booked_shortfall_kg"] = max(0.0, round(requested - delivered, 6))
    return metrics


def _format(value: float, unit: str) -> str:
    shown = f"{value:,.6f}".rstrip("0").rstrip(".")
    if unit == "SGD":
        return f"SGD {shown}"
    if unit == "ratio":
        return shown
    return f"{shown} {unit}"


def _direction(delta: float) -> Direction:
    if abs(delta) <= 0.000001:
        return "unchanged"
    return "increase" if delta > 0 else "decrease"


def _allocation_mix(plan: dict[str, Any]) -> tuple[dict[str, float], dict[str, float], list[str]]:
    counts: Counter[str] = Counter()
    areas: defaultdict[str, float] = defaultdict(float)
    for allocation in plan.get("allocations") or []:
        if not isinstance(allocation, dict) or not allocation.get("crop_id"):
            continue
        crop = str(allocation["crop_id"])
        counts[crop] += 1
        area = _number(allocation.get("area_m2"))
        if area is not None:
            areas[crop] += area
    return (
        {key: float(counts[key]) for key in sorted(counts)},
        {key: round(areas[key], 6) for key in sorted(areas)},
        sorted(counts),
    )


def _claim_id(payload: dict[str, Any]) -> str:
    return "pc_" + canonical_hash(payload)[:20]


def _snapshot_hash(result: dict[str, Any]) -> str:
    """Bind claims to assumptions and outputs, excluding incidental timings."""
    if result.get("snapshot_hash"):
        return str(result["snapshot_hash"])

    def plan_identity(plan: Any) -> Any:
        if not isinstance(plan, dict):
            return None
        return {key: plan.get(key) for key in (
            "id", "name", "status", "metrics", "allocations", "violations",
            "input_hash", "numerical_input_hash", "calculation_version",
        )}

    return canonical_hash({
        "calculation_contract": result.get("calculation_contract"),
        "numerical_input_hash": result.get("numerical_input_hash"),
        "configuration_hash": result.get("configuration_hash"),
        "assumptions": result.get("assumptions"),
        "retained_strategy": plan_identity(result.get("retained_strategy")),
        "strategies": [plan_identity(row) for row in result.get("strategies", [])],
        "comparisons": result.get("comparisons"),
    })


def _metric_claim(
    *, metric: str, policy: str, strategy_id: str, baseline: float, scenario: float,
    snapshot_hash: str,
) -> VerifiedPlanningClaim:
    label, unit = _METRICS[metric]
    delta = round(scenario - baseline, 6)
    direction = _direction(delta)
    if direction == "unchanged":
        statement = f"{policy}'s {label} remains {_format(scenario, unit)}."
    else:
        statement = (
            f"{policy}'s {label} {direction}s from {_format(baseline, unit)} "
            f"to {_format(scenario, unit)}; the change is {_format(abs(delta), unit)}."
        )
    identity = dict(metric=metric, policy=policy, strategy_id=strategy_id,
                    baseline=baseline, scenario=scenario,
                    snapshot_hash=snapshot_hash, claim_kind="metric_comparison")
    return dict(id=_claim_id(identity), **identity, delta=delta, direction=direction,
                unit=unit, statement=statement)


def _strategy_metric_claim(
    *, metric: str, policy: str, strategy_id: str, value: float, snapshot_hash: str,
) -> VerifiedPlanningClaim:
    label, unit = _METRICS[metric]
    identity = dict(metric=metric, policy=policy, strategy_id=strategy_id,
                    baseline=value, scenario=value, snapshot_hash=snapshot_hash,
                    claim_kind="strategy_metric")
    return dict(
        id=_claim_id(identity), **identity, delta=0.0, direction="unchanged", unit=unit,
        statement=f"{policy}'s {label} is {_format(value, unit)} in this frozen plan.",
    )


def _mix_claims(
    *, policy: str, strategy_id: str, baseline_plan: dict[str, Any],
    scenario_plan: dict[str, Any], snapshot_hash: str,
) -> list[VerifiedPlanningClaim]:
    before_count, before_area, before_ids = _allocation_mix(baseline_plan)
    after_count, after_area, after_ids = _allocation_mix(scenario_plan)
    if not before_count and not after_count:
        return []
    claims: list[VerifiedPlanningClaim] = []
    for metric, before, after, unit, noun in (
        ("crop_allocation_count", before_count, after_count, "allocations", "allocation counts"),
        ("crop_allocation_area_m2", before_area, after_area, "m2", "allocation area by crop"),
    ):
        if metric.endswith("area_m2") and not before and not after:
            continue
        keys = sorted(set(before) | set(after))
        delta = {key: round(after.get(key, 0.0) - before.get(key, 0.0), 6) for key in keys}
        direction: Literal["unchanged", "changed"] = "unchanged" if before == after else "changed"
        statement = f"{policy}'s {noun} are {direction} relative to the retained schedule."
        identity = dict(metric=metric, policy=policy, strategy_id=strategy_id,
                        baseline=before, scenario=after,
                        snapshot_hash=snapshot_hash, claim_kind="crop_mix_comparison")
        claims.append(dict(id=_claim_id(identity), **identity, delta=delta,
                           direction=direction, unit=unit, statement=statement))
    id_direction: Literal["unchanged", "changed"] = "unchanged" if before_ids == after_ids else "changed"
    identity = dict(metric="crop_id_set", policy=policy, strategy_id=strategy_id,
                    baseline=before_ids,
                    scenario=after_ids, snapshot_hash=snapshot_hash,
                    claim_kind="crop_mix_comparison")
    claims.append(dict(
        id=_claim_id(identity), **identity, delta=None, direction=id_direction, unit="crop IDs",
        statement=f"{policy}'s set of crop IDs is {id_direction} relative to the retained schedule.",
    ))
    return claims


def _snapshot_mix_claims(*, policy: str, strategy_id: str, plan: dict[str, Any],
                         snapshot_hash: str) -> list[VerifiedPlanningClaim]:
    """Describe initial composition without inventing a retained-plan comparison."""
    counts, areas, ids = _allocation_mix(plan)
    if not counts:
        return []
    claims = []
    for metric, value, unit, label in (
        ("crop_allocation_count", counts, "allocations", "allocation counts by crop"),
        ("crop_allocation_area_m2", areas, "m2", "allocation area by crop"),
        ("crop_id_set", ids, "crop IDs", "allocated crop IDs"),
    ):
        if not value:
            continue
        identity = dict(metric=metric, policy=policy, strategy_id=strategy_id,
                        baseline=value, scenario=value, snapshot_hash=snapshot_hash,
                        claim_kind="crop_mix_snapshot")
        shown = ", ".join(f"{key}: {amount:g}" for key, amount in value.items()) if isinstance(value, dict) else ", ".join(value)
        claims.append(dict(id=_claim_id(identity), **identity, delta=None,
                           direction="unchanged", unit=unit,
                           statement=f"{policy}'s {label} in this frozen plan: {shown}."))
    return claims


def _pairs(result: dict[str, Any]) -> list[tuple[dict[str, Any], dict[str, Any], str, str]]:
    retained = result.get("retained_strategy") or result.get("retained_plan")
    strategies = [row for row in result.get("strategies", []) if isinstance(row, dict)]
    pairs: list[tuple[dict[str, Any], dict[str, Any], str, str]] = []
    comparisons = result.get("comparisons")
    if isinstance(comparisons, list):
        by_id = {str(row.get("id")): row for row in strategies}
        for row in comparisons:
            if not isinstance(row, dict):
                continue
            before = row.get("baseline") or row.get("retained_strategy")
            after = row.get("scenario") or row.get("strategy") or by_id.get(str(row.get("strategy_id")))
            if isinstance(before, dict) and isinstance(after, dict):
                pairs.append((before, after, _name(after, "Candidate"), str(after.get("id") or row.get("strategy_id"))))
    if not pairs and isinstance(retained, dict):
        for strategy in strategies:
            pairs.append((retained, strategy, _name(strategy, "Candidate"), str(strategy.get("id"))))
    return pairs


def build_claims(result: dict[str, Any]) -> list[VerifiedPlanningClaim]:
    """Build stable, code-rendered propositions from a frozen comparison result."""

    snapshot_hash = _snapshot_hash(result)
    claims: list[VerifiedPlanningClaim] = []
    pairs = _pairs(result)
    for baseline_plan, scenario_plan, policy, strategy_id in pairs:
        baseline_metrics, scenario_metrics = _metrics(baseline_plan), _metrics(scenario_plan)
        for metric in _METRICS:
            baseline = _number(baseline_metrics.get(metric))
            scenario = _number(scenario_metrics.get(metric))
            if baseline is not None and scenario is not None:
                claims.append(_metric_claim(metric=metric, policy=policy, strategy_id=strategy_id,
                                            baseline=baseline,
                                            scenario=scenario, snapshot_hash=snapshot_hash))
        claims.extend(_mix_claims(policy=policy, strategy_id=strategy_id,
                                  baseline_plan=baseline_plan,
                                  scenario_plan=scenario_plan, snapshot_hash=snapshot_hash))
    if not pairs:
        for strategy in (row for row in result.get("strategies", []) if isinstance(row, dict)):
            policy, strategy_id = _name(strategy, "Candidate"), str(strategy.get("id"))
            claims.extend(_snapshot_mix_claims(policy=policy, strategy_id=strategy_id,
                                               plan=strategy, snapshot_hash=snapshot_hash))
            for metric, raw in _metrics(strategy).items():
                value = _number(raw)
                if metric in _METRICS and value is not None:
                    claims.append(_strategy_metric_claim(
                        metric=metric, policy=policy, strategy_id=strategy_id,
                        value=value, snapshot_hash=snapshot_hash,
                    ))
    unique = {claim["id"]: claim for claim in claims}
    return [unique[key] for key in sorted(unique)]
