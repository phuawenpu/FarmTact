from __future__ import annotations

from collections import Counter
from datetime import datetime
from decimal import Decimal, InvalidOperation
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .models import PublicContext


EXPECTED_UNITS = {
    "rainfall": {"mm"}, "air_temperature": {"degC"}, "relative_humidity": {"%"},
    "temperature_low": {"degC"}, "temperature_high": {"degC"},
    "relative_humidity_low": {"%"}, "relative_humidity_high": {"%"},
    "forecast_condition": {None},
}

REGISTRY_COVERAGE_SCHEMA_VERSION='farmtact-registry-coverage-1.0.0'


def registry_coverage(registry_dir:Path|str|None=None,declared:dict[str,Any]|None=None)->dict[str,Any]:
    """Validate the two scientific registries and derive versioned coverage.

    Counts are never accepted as configuration.  A manifest may provide a prior
    declaration, but a contradiction with the checked-in registry is an error.
    """

    root=Path(registry_dir) if registry_dir is not None else Path(__file__).resolve().parents[2]/'research'
    catalogue_path=root/'crop_catalogue.json';evidence_path=root/'evidence_register.json'
    catalogue=json.loads(catalogue_path.read_text(encoding='utf-8'))
    evidence=json.loads(evidence_path.read_text(encoding='utf-8'))
    if catalogue.get('schema_version')!='1.0.0' or evidence.get('schema_version')!='1.0.0':
        raise ValueError('unsupported crop/evidence registry schema version')
    profiles=catalogue.get('profiles');documents=evidence.get('documents')
    if not isinstance(profiles,list) or not profiles or not isinstance(documents,list) or not documents:
        raise ValueError('crop/evidence registries require non-empty record arrays')
    crop_ids=[row.get('crop_id') for row in profiles];evidence_ids=[row.get('evidence_id') for row in documents]
    if None in crop_ids or len(crop_ids)!=len(set(crop_ids)):
        raise ValueError('crop registry has missing or duplicate crop IDs')
    if None in evidence_ids or len(evidence_ids)!=len(set(evidence_ids)):
        raise ValueError('evidence registry has missing or duplicate evidence IDs')
    evidence_id_set=set(evidence_ids)
    missing=sorted({identifier for row in profiles for identifier in row.get('evidence_ids',[]) if identifier not in evidence_id_set})
    if missing:
        raise ValueError(f'crop profiles reference missing evidence IDs: {missing}')
    output={
        'schema_version':REGISTRY_COVERAGE_SCHEMA_VERSION,
        'catalogue_profiles':len(profiles),'scientific_evidence_documents':len(documents),
        'catalogue_version':catalogue.get('catalogue_version'),'evidence_register_version':evidence.get('register_version'),
        'catalogue_sha256':hashlib.sha256(catalogue_path.read_bytes()).hexdigest(),
        'evidence_register_sha256':hashlib.sha256(evidence_path.read_bytes()).hexdigest(),
    }
    if not output['catalogue_version'] or not output['evidence_register_version']:
        raise ValueError('registry versions are required for coverage evidence')
    if declared is not None:
        compared=('schema_version','catalogue_profiles','scientific_evidence_documents','catalogue_version',
            'evidence_register_version','catalogue_sha256','evidence_register_sha256')
        contradictions={key:{'declared':declared.get(key),'derived':output[key]} for key in compared if declared.get(key)!=output[key]}
        if contradictions:
            raise ValueError(f'declared registry coverage contradicts validated registries: {contradictions}')
    return output


def validate_context(context: PublicContext, *, registry_dir:Path|str|None=None,
                     declared_registry_coverage:dict[str,Any]|None=None) -> dict[str, Any]:
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
    crop_counts = registry_coverage(registry_dir,declared_registry_coverage)
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
