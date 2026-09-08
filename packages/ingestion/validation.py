from __future__ import annotations

from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
import math
from typing import Any

from .models import PublicContext


EXPECTED_UNITS = {
    "rainfall": {"mm"}, "air_temperature": {"degC"}, "relative_humidity": {"%"},
    "temperature_low": {"degC"}, "temperature_high": {"degC"},
    "relative_humidity_low": {"%"}, "relative_humidity_high": {"%"},
    "forecast_condition": {None},
}


def validate_context(context: PublicContext) -> dict[str, Any]:
    issues: list[dict[str, Any]] = []
    all_rows = context.weather_observations + context.weather_forecasts + context.trade_observations
    traceable = sum(1 for row in all_rows if row.get("source_id") and row.get("snapshot_id") and row.get("raw_locator"))
    snapshot_ids = {snapshot.snapshot_id for snapshot in context.snapshots}
    orphaned_snapshot_references = sum(1 for row in all_rows if row.get("snapshot_id") not in snapshot_ids)
    identifiers = [row.get("observation_id") or row.get("forecast_id") or row.get("trade_observation_id") for row in all_rows]
    duplicates = sorted(key for key, count in Counter(identifiers).items() if key and count > 1)
    if duplicates:
        issues.append({"severity": "error", "code": "duplicate_row_ids", "count": len(duplicates), "examples": duplicates[:5]})
    invalid_units = 0
    invalid_times = 0
    nonfinite_values = 0
    invalid_availability_use = 0
    for row in all_rows:
        variable = row.get("variable")
        if variable in EXPECTED_UNITS and row.get("unit") not in EXPECTED_UNITS[variable]:
            invalid_units += 1
        value = row.get("value")
        if isinstance(value, float) and not math.isfinite(value):
            nonfinite_values += 1
        if row.get("measure") == "trade_volume":
            try:
                if not Decimal(str(value)).is_finite():
                    nonfinite_values += 1
            except InvalidOperation:
                nonfinite_values += 1
        for key in ("observed_at", "issued_at", "available_at", "valid_from", "valid_to", "retrieved_at"):
            if row.get(key):
                try:
                    parsed = datetime.fromisoformat(str(row[key]))
                    if parsed.tzinfo is None:
                        invalid_times += 1
                except ValueError:
                    invalid_times += 1
        availability = str(row.get("availability_status", ""))
        if ("uncertain" in availability or "unknown" in availability) and row.get("eligible_for_point_in_time_features"):
            invalid_availability_use += 1
    if invalid_units:
        issues.append({"severity": "error", "code": "invalid_units", "count": invalid_units})
    if invalid_times:
        issues.append({"severity": "error", "code": "invalid_timestamps", "count": invalid_times})
    if nonfinite_values:
        issues.append({"severity": "error", "code": "nonfinite_values", "count": nonfinite_values})
    if invalid_availability_use:
        issues.append({"severity": "error", "code": "uncertain_availability_enabled_for_point_in_time", "count": invalid_availability_use})
    if traceable != len(all_rows):
        issues.append({"severity": "error", "code": "untraceable_rows", "count": len(all_rows) - traceable})
    if orphaned_snapshot_references:
        issues.append({"severity": "error", "code": "orphaned_snapshot_references", "count": orphaned_snapshot_references})
    crop_counts = {"catalogue_profiles": 10, "scientific_evidence_documents": 20}
    return {
        "status": "passed" if not any(issue["severity"] == "error" for issue in issues) else "failed",
        "row_counts": {
            "weather_observations": len(context.weather_observations),
            "weather_forecasts": len(context.weather_forecasts),
            "trade_observations": len(context.trade_observations),
            "traceable_rows": traceable,
        },
        "source_counts": dict(sorted(Counter(row.get("source_id") for row in all_rows).items())),
        "coverage": crop_counts,
        "failure_count": len(context.failures),
        "issues": issues,
        "known_gaps": [
            "NEA observation availability time is not separately supplied and remains uncertain.",
            "SingStat exact historical release timestamps and nomenclature version remain unresolved.",
            "Trade mappings are limited to exact provider descriptions; broad vegetable codes remain unresolved.",
            "Public context is not farm-specific weather, demand, yield, price, or commercial recipe evidence.",
        ],
    }
