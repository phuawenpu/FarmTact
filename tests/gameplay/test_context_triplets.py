import pytest

from packages.ai_contracts import typed_reference_catalog
from services.api.conversations import _bounded_model_context


CONTROLS = {
    "scenario:controls.delay_days": 3,
    "scenario:controls.yield_percent": 90,
    "scenario:controls.demand_percent": 110,
    "scenario:controls.labour_percent": 95,
    "scenario:controls.cash_percent": 85,
}
SEGMENTS = ("baseline_metrics", "scenario_metrics", "deltas")
POLICIES = ("lean", "balanced", "resilient")


def conversation(tools):
    return {
        "snapshot_ref": {"kind": "scenario", "hash": "frozen"},
        "_tool_results": tools,
        "_typed_facts": typed_reference_catalog(tools, snapshot_hash="frozen"),
    }


@pytest.mark.parametrize(
    ("role", "metrics"),
    [
        (
            "demand_analyst",
            (
                "booked_delivered_kg",
                "booked_requested_kg",
                "fill_rate",
                "residual_delivered_kg",
                "residual_requested_kg",
                "shortfall_kg",
            ),
        ),
        (
            "profit_analyst",
            (
                "cash_sgd",
                "closing_stock_kg",
                "cost_sgd",
                "labour_hours",
                "margin_sgd",
                "revenue_sgd",
                "waste_kg",
            ),
        ),
    ],
)
def test_crowded_comparison_projection_never_splits_available_triplets(role, metrics):
    tools = dict(CONTROLS)
    tools.update(
        {
            f"comparison:{policy}.{segment}.{metric}": index + 1
            for index, metric in enumerate(metrics)
            for policy in POLICIES
            for segment in SEGMENTS
        }
    )

    _, projected = _bounded_model_context(conversation(tools), role)

    assert set(CONTROLS) <= set(projected)
    assert len(projected) <= 48
    assert len(projected) < len(typed_reference_catalog(tools, snapshot_hash="frozen"))
    for policy in POLICIES:
        for metric in metrics:
            available = {
                f"comparison:{policy}.{segment}.{metric}" for segment in SEGMENTS
            }
            selected = available.intersection(projected)
            assert selected in (set(), available)


def test_comparison_group_uses_every_member_that_is_actually_available():
    tools = dict(CONTROLS)
    tools.update(
        {
            "comparison:balanced.deltas.booked_delivered_kg": -4,
            "comparison:balanced.scenario_metrics.booked_delivered_kg": 20,
        }
    )
    tools.update(
        {
            f"comparison:{policy}.{segment}.{metric}": 1
            for metric in ("booked_requested_kg", "fill_rate", "residual_delivered_kg", "residual_requested_kg", "shortfall_kg")
            for policy in POLICIES
            for segment in SEGMENTS
        }
    )

    _, projected = _bounded_model_context(conversation(tools), "demand_analyst")

    assert "comparison:balanced.deltas.booked_delivered_kg" in projected
    assert "comparison:balanced.scenario_metrics.booked_delivered_kg" in projected
    assert "comparison:balanced.baseline_metrics.booked_delivered_kg" not in projected
    for policy in POLICIES:
        for metric in ("booked_requested_kg", "fill_rate", "residual_delivered_kg", "residual_requested_kg", "shortfall_kg"):
            available = {
                f"comparison:{policy}.{segment}.{metric}" for segment in SEGMENTS
            }
            selected = available.intersection(projected)
            assert selected in (set(), available)


def test_absent_source_context_is_prioritized_and_metric_names_cannot_bypass_role_filter():
    absent = {
        "status": "unavailable",
        "scope": "No frozen weather observation is attached.",
    }
    source_tools = {"weather:source_context": absent}
    source_tools.update({f"source:D{index:02}.summary": "context" for index in range(30)})
    qualitative, _ = _bounded_model_context(conversation(source_tools), "weather_analyst")
    assert qualitative["weather:source_context"] == absent
    assert len(qualitative) <= 24

    metric_tools = {}
    for prefix in (
        "strategy:balanced.metrics",
        "scenario:baseline.balanced.metrics",
        "scenario:result.balanced.metrics",
        "comparison:balanced.baseline_metrics",
        "comparison:balanced.scenario_metrics",
        "comparison:balanced.deltas",
    ):
        metric_tools[f"{prefix}.fill_rate"] = 0.8
        metric_tools[f"{prefix}.revenue_sgd"] = 100
    _, projected = _bounded_model_context(conversation(metric_tools), "planning_chair")
    assert any(reference.endswith("fill_rate") for reference in projected)
    assert not any(reference.endswith("revenue_sgd") for reference in projected)
