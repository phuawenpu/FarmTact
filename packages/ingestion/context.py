from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from .http import Transport, UrlLibTransport
from .models import PublicContext, SnapshotRecord, SourceFailure
from .nea import (
    NEA_BASE_URL,
    NEA_ENDPOINTS,
    normalize_24h_forecast,
    normalize_4d_forecast,
    normalize_station_observations,
)
from .power import POWER_DAILY_URL, build_query as build_power_query, normalize_daily
from .singstat import SINGSTAT_TABLE_URL, latest_period_from_payload, normalize_trade_volume
from .storage import SnapshotStore, write_json_atomic, write_jsonl_atomic
from .validation import validate_context


SCHEMA_VERSION = "1.0.0"
TRANSFORM_VERSION = "farmtact-public-context-1.0.0"
FRESHNESS_THRESHOLDS = {"D01": 15, "D02": 15, "D03": 15, "D04": 12 * 60, "D05": 24 * 60}
LICENCES = {
    "D01": "verified_singapore_open_data_licence", "D02": "verified_singapore_open_data_licence",
    "D03": "verified_singapore_open_data_licence", "D04": "verified_singapore_open_data_licence",
    "D05": "verified_singapore_open_data_licence", "D06": "not_verified_for_redistribution",
    "D11": "terms_not_reviewed_for_redistribution",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    if moment.tzinfo is None:
        raise ValueError("now must be timezone-aware")
    return moment.astimezone(timezone.utc).isoformat()


def _age_minutes(now: datetime, source_time: str | None) -> float | None:
    if not source_time:
        return None
    parsed = datetime.fromisoformat(source_time)
    if parsed.tzinfo is None:
        return None
    return max(0.0, (now - parsed.astimezone(timezone.utc)).total_seconds() / 60)


def _source_summary(
    *, source_id: str, provider: str, kind: str, source_time: str | None, retrieved_at: str,
    threshold_minutes: int | None, unit: str | list[str] | None, coverage: dict[str, Any],
    snapshot_id: str, status: str = "validated", failure_reason: str | None = None,
) -> dict[str, Any]:
    now = datetime.fromisoformat(retrieved_at)
    age = _age_minutes(now, source_time)
    freshness = "unknown" if age is None or threshold_minutes is None else ("fresh" if age <= threshold_minutes else "stale")
    return {
        "source_id": source_id, "provider": provider, "kind": kind, "status": status,
        "data_mode": "real_public", "source_time": source_time, "retrieved_at": retrieved_at,
        "freshness": freshness, "freshness_age_minutes": round(age, 2) if age is not None else None,
        "unit": unit, "coverage": coverage, "snapshot_id": snapshot_id,
        "licence_state": LICENCES[source_id], "failure_reason": failure_reason,
    }


def _snapshot_fetch(
    *, transport: Transport, store: SnapshotStore, source_id: str, url: str, query: dict[str, str],
    retrieved_at: str, timeout: float,
) -> tuple[dict[str, Any], SnapshotRecord]:
    response = transport.get(url, query, timeout)
    snapshot = store.save(source_id=source_id, request_url=url, query=query, retrieved_at=retrieved_at,
                          response=response, licence_state=LICENCES[source_id])
    if response.status != 200:
        raise RuntimeError(f"HTTP {response.status}; snapshot={snapshot.snapshot_id}")
    return response.json(), snapshot


def _restore_cached_source(context: PublicContext, previous: PublicContext, source_id: str, reason: str, occurred_at: str) -> bool:
    old_source = next((row for row in previous.sources if row.get("source_id") == source_id), None)
    if old_source is None or old_source.get("status") not in {"validated", "cached_stale"}:
        return False
    restored = dict(old_source)
    restored.update({"status": "cached_stale", "freshness": "stale", "failure_reason": reason})
    context.sources.append(restored)
    context.weather_observations.extend(row for row in previous.weather_observations if row.get("source_id") == source_id)
    context.weather_forecasts.extend(row for row in previous.weather_forecasts if row.get("source_id") == source_id)
    context.trade_observations.extend(row for row in previous.trade_observations if row.get("source_id") == source_id)
    referenced_snapshot_ids = {
        row["snapshot_id"]
        for row in context.weather_observations + context.weather_forecasts + context.trade_observations
        if row.get("source_id") == source_id and row.get("snapshot_id")
    }
    if restored.get("snapshot_id"):
        referenced_snapshot_ids.add(restored["snapshot_id"])
    existing_snapshot_ids = {snapshot.snapshot_id for snapshot in context.snapshots}
    context.snapshots.extend(
        snapshot for snapshot in previous.snapshots
        if snapshot.snapshot_id in referenced_snapshot_ids and snapshot.snapshot_id not in existing_snapshot_ids
    )
    return True


def _record_failure(context: PublicContext, previous: PublicContext, source_id: str, reason: str, occurred_at: str) -> None:
    cached = _restore_cached_source(context, previous, source_id, reason, occurred_at)
    context.failures.append(SourceFailure(source_id=source_id, state="blocked", occurred_at=occurred_at,
                                          reason=reason, retryable=True, cached_context_available=cached))
    if not cached:
        context.sources.append({
            "source_id": source_id, "provider": "NEA / data.gov.sg" if source_id.startswith("D0") and source_id != "D06" else "public provider",
            "kind": "public_context", "status": "blocked", "data_mode": "real_public",
            "source_time": None, "retrieved_at": occurred_at, "freshness": "unknown",
            "freshness_age_minutes": None, "unit": None, "coverage": {"row_count": 0},
            "snapshot_id": None, "licence_state": LICENCES.get(source_id, "unknown"), "failure_reason": reason,
        })


def refresh(
    data_dir: Path | str = Path("data"), *, include_singstat: bool = True, include_power: bool = False,
    now: datetime | None = None, transport: Transport | None = None,
) -> PublicContext:
    """Fetch bounded public context, preserve raw snapshots, normalize, validate and persist it.

    Each connector fails independently. When a prior context exists, failed sources are
    restored as `cached_stale` with the current failure recorded.
    """
    destination = Path(data_dir)
    current = now or _utc_now()
    built_at = _iso(current)
    client = transport or UrlLibTransport()
    store = SnapshotStore(destination)
    previous = get_public_context(destination)
    context = PublicContext(schema_version=SCHEMA_VERSION, built_at=built_at, execution_mode="live_public_refresh")

    for source_id, (endpoint, variable, expected_unit, threshold) in NEA_ENDPOINTS.items():
        url = f"{NEA_BASE_URL}/{endpoint}"
        try:
            payload, snapshot = _snapshot_fetch(transport=client, store=store, source_id=source_id, url=url,
                                                query={}, retrieved_at=built_at, timeout=20)
            context.snapshots.append(snapshot)
            if source_id in {"D01", "D02", "D03"}:
                rows = normalize_station_observations(payload, source_id=source_id, snapshot_id=snapshot.snapshot_id,
                    retrieved_at=built_at, variable=variable, expected_unit=expected_unit or "")
                context.weather_observations.extend(rows)
                source_time = max(row["observed_at"] for row in rows)
                stations = {row["station_id"] for row in rows}
                units: str | list[str] = sorted({row["unit"] for row in rows})
                units = units[0] if len(units) == 1 else units
                coverage = {"row_count": len(rows), "station_count": len(stations), "interval_minutes": 5, "geography": "Singapore stations"}
            elif source_id == "D04":
                rows = normalize_24h_forecast(payload, snapshot_id=snapshot.snapshot_id, retrieved_at=built_at)
                context.weather_forecasts.extend(rows)
                source_time = max(row["available_at"] for row in rows)
                units = sorted({row["unit"] for row in rows if row["unit"]})
                coverage = {"row_count": len(rows), "location_count": len({row["location_id"] for row in rows}),
                            "valid_from": min(row["valid_from"] for row in rows), "valid_to": max(row["valid_to"] for row in rows)}
            else:
                rows = normalize_4d_forecast(payload, snapshot_id=snapshot.snapshot_id, retrieved_at=built_at)
                context.weather_forecasts.extend(rows)
                source_time = max(row["available_at"] for row in rows)
                units = sorted({row["unit"] for row in rows if row["unit"]})
                coverage = {"row_count": len(rows), "day_count": len({row["valid_from"][:10] for row in rows}),
                            "valid_from": min(row["valid_from"] for row in rows), "valid_to": max(row["valid_to"] for row in rows)}
            context.sources.append(_source_summary(source_id=source_id, provider="NEA / data.gov.sg",
                kind="weather_observation" if source_id in {"D01", "D02", "D03"} else "weather_forecast",
                source_time=source_time, retrieved_at=built_at, threshold_minutes=threshold, unit=units,
                coverage=coverage, snapshot_id=snapshot.snapshot_id))
        except Exception as error:  # connector isolation is intentional
            _record_failure(context, previous, source_id, f"{type(error).__name__}: {error}", built_at)

    if include_singstat:
        try:
            discovery_query = {"timeFilter": current.strftime("%Y %b")}
            discovery, discovery_snapshot = _snapshot_fetch(transport=client, store=store, source_id="D06",
                url=SINGSTAT_TABLE_URL, query=discovery_query, retrieved_at=built_at, timeout=30)
            context.snapshots.append(discovery_snapshot)
            latest_period = latest_period_from_payload(discovery)
            if latest_period == discovery_query["timeFilter"] and discovery.get("Data", {}).get("rows"):
                payload, snapshot = discovery, discovery_snapshot
            else:
                payload, snapshot = _snapshot_fetch(transport=client, store=store, source_id="D06",
                    url=SINGSTAT_TABLE_URL, query={"timeFilter": latest_period}, retrieved_at=built_at, timeout=30)
                context.snapshots.append(snapshot)
            rows, coverage = normalize_trade_volume(payload, snapshot_id=snapshot.snapshot_id, retrieved_at=built_at)
            if not rows:
                raise ValueError("no selected fresh/chilled vegetable volume rows in latest SingStat period")
            context.trade_observations.extend(rows)
            context.sources.append(_source_summary(source_id="D06", provider="Singapore Department of Statistics",
                kind="trade_observation", source_time=None, retrieved_at=built_at, threshold_minutes=None,
                unit=sorted({row["unit"] for row in rows}), coverage=coverage, snapshot_id=snapshot.snapshot_id))
        except Exception as error:
            _record_failure(context, previous, "D06", f"{type(error).__name__}: {error}", built_at)

    if include_power:
        try:
            rows = []
            snapshot = None
            attempted_periods = []
            last_error: Exception | None = None
            for lag_days in (30, 365, 730):
                end = current.date() - timedelta(days=lag_days)
                start = end - timedelta(days=6)
                attempted_periods.append({"start": start.isoformat(), "end": end.isoformat()})
                query = build_power_query(start, end, 1.3521, 103.8198)
                payload, candidate_snapshot = _snapshot_fetch(transport=client, store=store, source_id="D11", url=POWER_DAILY_URL,
                                                               query=query, retrieved_at=built_at, timeout=30)
                context.snapshots.append(candidate_snapshot)
                try:
                    rows = normalize_daily(payload, snapshot_id=candidate_snapshot.snapshot_id, retrieved_at=built_at)
                    snapshot = candidate_snapshot
                    break
                except ValueError as error:
                    last_error = error
            if not rows or snapshot is None:
                raise last_error or ValueError("NASA POWER yielded no available historical period")
            context.weather_observations.extend(rows)
            context.sources.append(_source_summary(source_id="D11", provider="NASA POWER", kind="historical_climate",
                source_time=max(row["observed_at"] for row in rows), retrieved_at=built_at, threshold_minutes=None,
                unit=sorted({row["unit"] for row in rows}),
                coverage={"row_count": len(rows), "day_count": len({row["observed_at"][:10] for row in rows}),
                          "point": {"latitude": 1.3521, "longitude": 103.8198}, "time_standard": "UTC",
                          "attempted_periods": attempted_periods, "selected_period": {"start": start.isoformat(), "end": end.isoformat()}},
                snapshot_id=snapshot.snapshot_id))
        except Exception as error:
            _record_failure(context, previous, "D11", f"{type(error).__name__}: {error}", built_at)

    context.sources.sort(key=lambda row: row["source_id"])
    context.freshness = [{key: source.get(key) for key in ("source_id", "source_time", "retrieved_at", "freshness", "freshness_age_minutes")}
                         for source in context.sources]
    context.quality = validate_context(context)
    _persist_context(destination, context)
    return context


def _load_dataclass_context(value: dict[str, Any]) -> PublicContext:
    return PublicContext(
        schema_version=value["schema_version"], built_at=value["built_at"], execution_mode=value["execution_mode"],
        sources=value.get("sources", []),
        snapshots=[SnapshotRecord(**row) for row in value.get("snapshots", [])],
        weather_observations=value.get("weather_observations", []), weather_forecasts=value.get("weather_forecasts", []),
        trade_observations=value.get("trade_observations", []),
        failures=[SourceFailure(**row) for row in value.get("failures", [])],
        freshness=value.get("freshness", []), quality=value.get("quality", {}),
    )


def get_public_context(data_dir: Path | str = Path("data")) -> PublicContext:
    path = Path(data_dir) / "runtime" / "public_context.json"
    if path.exists():
        context = _load_dataclass_context(json.loads(path.read_text(encoding="utf-8")))
        read_at = _utc_now()
        for source in context.sources:
            threshold = FRESHNESS_THRESHOLDS.get(source.get("source_id"))
            age = _age_minutes(read_at, source.get("source_time"))
            source["freshness_age_minutes"] = round(age, 2) if age is not None else None
            if source.get("status") == "cached_stale":
                source["freshness"] = "stale"
            else:
                source["freshness"] = "unknown" if age is None or threshold is None else ("fresh" if age <= threshold else "stale")
        context.freshness = [{key: source.get(key) for key in ("source_id", "source_time", "retrieved_at", "freshness", "freshness_age_minutes")}
                             for source in context.sources]
        return context
    return PublicContext(
        schema_version=SCHEMA_VERSION, built_at=_iso(_utc_now()), execution_mode="unavailable",
        failures=[SourceFailure(source_id="public_context", state="blocked", occurred_at=_iso(_utc_now()),
                                reason="No built public context; run refresh() or scripts/build_dataset.py", retryable=True)],
        quality={"status": "blocked", "row_counts": {}, "issues": [{"severity": "error", "code": "context_not_built"}]},
    )


def rebuild(data_dir: Path | str = Path("data")) -> PublicContext:
    """Rebuild normalized artifacts from the immutable snapshots in the manifest."""
    destination = Path(data_dir)
    manifest_path = destination / "manifests" / "dataset_manifest.json"
    if not manifest_path.exists():
        raise FileNotFoundError(f"missing manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    context = PublicContext(
        schema_version=manifest["schema_version"], built_at=manifest["built_at"],
        execution_mode="offline_snapshot_rebuild", sources=manifest.get("sources", []),
        snapshots=[SnapshotRecord(**row) for row in manifest.get("source_snapshots", [])],
        failures=[SourceFailure(**row) for row in manifest.get("failures", [])],
    )
    trade_rows: list[dict[str, Any]] = []
    for snapshot in context.snapshots:
        payload = json.loads((destination / snapshot.relative_path).read_text(encoding="utf-8"))
        if snapshot.source_id in {"D01", "D02", "D03"}:
            _, variable, unit, _ = NEA_ENDPOINTS[snapshot.source_id]
            context.weather_observations.extend(normalize_station_observations(
                payload, source_id=snapshot.source_id, snapshot_id=snapshot.snapshot_id,
                retrieved_at=snapshot.retrieved_at, variable=variable, expected_unit=unit or ""))
        elif snapshot.source_id == "D04":
            context.weather_forecasts.extend(normalize_24h_forecast(payload, snapshot_id=snapshot.snapshot_id,
                                                                    retrieved_at=snapshot.retrieved_at))
        elif snapshot.source_id == "D05":
            context.weather_forecasts.extend(normalize_4d_forecast(payload, snapshot_id=snapshot.snapshot_id,
                                                                   retrieved_at=snapshot.retrieved_at))
        elif snapshot.source_id == "D06":
            candidate, _ = normalize_trade_volume(payload, snapshot_id=snapshot.snapshot_id, retrieved_at=snapshot.retrieved_at)
            if candidate:
                trade_rows = candidate
        elif snapshot.source_id == "D11":
            try:
                context.weather_observations.extend(normalize_daily(payload, snapshot_id=snapshot.snapshot_id,
                                                                    retrieved_at=snapshot.retrieved_at))
            except ValueError:
                # A bounded availability probe may contain only provider fill values.
                continue
    context.trade_observations = trade_rows
    context.freshness = [{key: source.get(key) for key in ("source_id", "source_time", "retrieved_at", "freshness", "freshness_age_minutes")}
                         for source in context.sources]
    context.quality = validate_context(context)
    _persist_context(destination, context)
    return context


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _persist_context(data_dir: Path, context: PublicContext) -> None:
    normalized_dir = data_dir / "normalized"
    paths = {
        "weather_observations": normalized_dir / "weather_observations.jsonl",
        "weather_forecasts": normalized_dir / "weather_forecasts.jsonl",
        "trade_observations": normalized_dir / "trade_observations.jsonl",
    }
    write_jsonl_atomic(paths["weather_observations"], context.weather_observations)
    write_jsonl_atomic(paths["weather_forecasts"], context.weather_forecasts)
    write_jsonl_atomic(paths["trade_observations"], context.trade_observations)
    write_json_atomic(data_dir / "runtime" / "public_context.json", context.as_dict())
    dependency_hashes = sorted(snapshot.sha256 for snapshot in context.snapshots)
    dataset_id = hashlib.sha256(json.dumps({"transform": TRANSFORM_VERSION, "snapshots": dependency_hashes}, sort_keys=True).encode()).hexdigest()
    artifacts = {name: {"path": str(path.relative_to(data_dir)), "sha256": _file_sha256(path),
                        "row_count": len(getattr(context, name))} for name, path in paths.items()}
    manifest = {
        "schema_version": SCHEMA_VERSION, "dataset_id": dataset_id, "built_at": context.built_at,
        "transform_version": TRANSFORM_VERSION, "execution_mode": context.execution_mode,
        "source_snapshots": [snapshot.__dict__ for snapshot in context.snapshots],
        "sources": context.sources,
        "artifacts": artifacts, "quality_status": context.quality.get("status"),
        "failures": [failure.__dict__ for failure in context.failures],
        "rebuild_command": "python scripts/build_dataset.py --data-dir data",
    }
    contributing_ids = {
        "weather_observations": {row["snapshot_id"] for row in context.weather_observations},
        "weather_forecasts": {row["snapshot_id"] for row in context.weather_forecasts},
        "trade_observations": {row["snapshot_id"] for row in context.trade_observations},
    }
    lineage = {
        "schema_version": SCHEMA_VERSION, "dataset_id": dataset_id,
        "nodes": ([{"id": snapshot.snapshot_id, "kind": "immutable_raw_snapshot", "sha256": snapshot.sha256}
                   for snapshot in context.snapshots] +
                  [{"id": name, "kind": "normalized_artifact", **metadata} for name, metadata in artifacts.items()]),
        "edges": [{"from": snapshot.snapshot_id, "to": name, "transform": TRANSFORM_VERSION}
                  for snapshot in context.snapshots for name in artifacts if snapshot.snapshot_id in contributing_ids[name]],
    }
    write_json_atomic(data_dir / "manifests" / "dataset_manifest.json", manifest)
    write_json_atomic(data_dir / "manifests" / "lineage.json", lineage)
    write_json_atomic(data_dir / "reports" / "data_quality.json", context.quality)
