"""Read-only presentation adapter for the cached public-data context."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from packages.ingestion import get_public_context


ROOT = Path(__file__).resolve().parents[2]
DATASET_NAMES = ("weather_observations", "weather_forecasts", "trade_observations")
REDISTRIBUTABLE_LICENCES = {"verified_singapore_open_data_licence"}


def _reuse_policy(licence_state: str | None) -> tuple[bool, list[str]]:
    if licence_state in REDISTRIBUTABLE_LICENCES:
        return True, []
    return False, ["Public export is disabled until redistribution terms are verified."]


def _record(
    dataset: str,
    row: dict[str, Any],
    export_allowed: bool,
    licence_state: str | None,
    reuse_restrictions: list[str],
) -> dict[str, Any]:
    common = {
        "source_id": row["source_id"],
        "value": row.get("value"),
        "unit": row.get("unit"),
        "retrieved_at": row.get("retrieved_at"),
        "available_at": row.get("available_at"),
        "availability_status": row.get("availability_status"),
        "eligible_for_point_in_time_features": row.get("eligible_for_point_in_time_features"),
        "snapshot_id": row.get("snapshot_id"),
        "export_allowed": export_allowed,
        "licence_state": licence_state,
        "reuse_restrictions": list(reuse_restrictions),
    }
    if dataset == "weather_observations":
        common.update(
            id=row["observation_id"], date=row["observed_at"][:10], metric=row["variable"],
            observed_at=row.get("observed_at"), station_id=row.get("station_id"),
            station_name=row.get("station_name"), latitude=row.get("latitude"),
            longitude=row.get("longitude"), grid_point=row.get("grid_point"),
            interval_minutes=row.get("interval_minutes"), provider_variable=row.get("provider_variable"),
            time_standard=row.get("time_standard"), quality_flags=list(row.get("quality_flags", [])),
        )
    elif dataset == "weather_forecasts":
        common.update(
            id=row["forecast_id"], date=row["valid_from"][:10], metric=row["variable"],
            observed_at=None, issued_at=row.get("issued_at"), valid_from=row.get("valid_from"),
            valid_to=row.get("valid_to"), location_id=row.get("location_id"),
            model=row.get("model"), lead_hours=row.get("lead_hours"), quality_flags=[],
        )
    else:
        common.update(
            id=row["trade_observation_id"], date=row["period_start"], metric=row.get("measure"),
            observed_at=row.get("observed_at"), period=row.get("period"),
            period_start=row.get("period_start"), reporter=row.get("reporter"), partner=row.get("partner"),
            trade_flow=row.get("trade_flow"), commodity_code=row.get("commodity_code"),
            commodity_description=row.get("commodity_description"), table_id=row.get("table_id"),
            raw_unit=row.get("raw_unit"), provider_data_last_updated=row.get("provider_data_last_updated"),
            mapping_status=row.get("mapping_status"), quality_flags=list(row.get("flags", [])),
        )
    return common


def public_explorer() -> dict[str, Any]:
    """Return registry metadata and normalized records from the local public cache only."""
    registry = json.loads((ROOT / "research" / "dataset_registry.json").read_text(encoding="utf-8"))["datasets"]
    context = get_public_context(ROOT / "data").as_dict()
    context_sources = {row["source_id"]: row for row in context.get("sources", [])}
    snapshots = {row["snapshot_id"]: row for row in context.get("snapshots", [])}
    row_counts = {
        source["source_id"]: sum(
            1 for dataset in DATASET_NAMES for row in context.get(dataset, [])
            if row.get("source_id") == source["source_id"]
        )
        for source in registry
    }

    sources = []
    export_policy: dict[str, tuple[bool, str | None, list[str]]] = {}
    for registered in registry:
        source_id = registered["source_id"]
        cached = context_sources.get(source_id)
        count = row_counts[source_id]
        allowed, restrictions = _reuse_policy(registered.get("licence_state"))
        export_policy[source_id] = (allowed, registered.get("licence_state"), restrictions)
        source_status = cached.get("status") if cached else None
        quality_flags: list[str] = []
        if source_status == "cached_stale":
            quality_flags.append("cached_stale")
        if cached and cached.get("failure_reason"):
            quality_flags.append("source_failure")
        if count == 0:
            quality_flags.append("no_ingested_rows")
        sources.append({
            "id": source_id,
            "name": registered["name"],
            "provider": registered.get("provider"),
            "kind": registered.get("kind"),
            "url": registered.get("url"),
            "api_url": registered.get("api_url"),
            "status": source_status if count else "metadata_only",
            "upstream_status": source_status or registered.get("integration_state"),
            "coverage": cached.get("coverage", {"row_count": 0}) if cached else {"row_count": 0},
            "observed_at": cached.get("source_time") if cached else None,
            "retrieved_at": cached.get("retrieved_at") if cached else None,
            "freshness": cached.get("freshness", "unknown") if cached else "unknown",
            "freshness_age_minutes": cached.get("freshness_age_minutes") if cached else None,
            "quality": (
                "metadata_only" if not count else
                "stale" if source_status == "cached_stale" else
                context.get("quality", {}).get("status", "unknown")
            ),
            "quality_flags": quality_flags,
            "licence_state": registered.get("licence_state"),
            "reuse_restrictions": restrictions,
            "export_allowed": allowed,
            "record_count": count,
            "unit_scope": registered.get("unit_scope"),
            "freshness_expectation": registered.get("freshness_expectation"),
            "snapshot_id": cached.get("snapshot_id") if cached else None,
            "snapshot_url": snapshots.get(cached.get("snapshot_id"), {}).get("request_url") if cached else None,
            "failure_reason": cached.get("failure_reason") if cached else None,
        })

    datasets = {}
    for name in DATASET_NAMES:
        datasets[name] = []
        for row in context.get(name, []):
            allowed, licence, restrictions = export_policy.get(
                row.get("source_id"), (False, None, ["Source is absent from the public dataset registry."])
            )
            datasets[name].append(_record(name, row, allowed, licence, restrictions))
    return {"sources": sources, "datasets": datasets}
