from __future__ import annotations

import hashlib
import json
import math
from datetime import datetime, timezone
from typing import Any


NEA_BASE_URL = "https://api-open.data.gov.sg/v2/real-time/api"
NEA_ENDPOINTS = {
    "D01": ("rainfall", "rainfall", "mm", 15),
    "D02": ("air-temperature", "air_temperature", "degC", 15),
    "D03": ("relative-humidity", "relative_humidity", "%", 15),
    "D04": ("twenty-four-hr-forecast", "forecast_24h", None, 12 * 60),
    "D05": ("four-day-outlook", "forecast_4d", None, 24 * 60),
}


def _require_object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    return value


def validate_envelope(payload: dict[str, Any], source_id: str) -> dict[str, Any]:
    if payload.get("code") != 0:
        raise ValueError(f"{source_id} provider error: {payload.get('errorMsg', 'unknown error')}")
    return _require_object(payload.get("data"), f"{source_id}.data")


def _stable_id(prefix: str, *parts: object) -> str:
    body = json.dumps(parts, separators=(",", ":"), ensure_ascii=False).encode()
    return f"{prefix}-{hashlib.sha256(body).hexdigest()[:20]}"


def normalize_station_observations(
    payload: dict[str, Any], *, source_id: str, snapshot_id: str, retrieved_at: str, variable: str, expected_unit: str
) -> list[dict[str, Any]]:
    data = validate_envelope(payload, source_id)
    stations = data.get("stations")
    readings = data.get("readings")
    if not isinstance(stations, list) or not isinstance(readings, list):
        raise ValueError(f"{source_id} station response lacks stations/readings arrays")
    raw_unit = str(data.get("readingUnit", "")).strip()
    unit_aliases = {"°C": "degC", "deg C": "degC", "Percentage": "%", "percentage": "%", "%": "%", "mm": "mm"}
    unit = unit_aliases.get(raw_unit, raw_unit)
    if unit != expected_unit:
        raise ValueError(f"{source_id} unexpected unit {raw_unit!r}; expected {expected_unit!r}")
    station_index = {str(item.get("id")): item for item in stations if isinstance(item, dict) and item.get("id")}
    rows: list[dict[str, Any]] = []
    for reading_index, reading in enumerate(readings):
        reading = _require_object(reading, f"{source_id}.readings[{reading_index}]")
        observed_at = reading.get("timestamp")
        if not isinstance(observed_at, str):
            raise ValueError(f"{source_id} reading timestamp is missing")
        datetime.fromisoformat(observed_at)
        points = reading.get("data")
        if not isinstance(points, list):
            raise ValueError(f"{source_id} reading data must be an array")
        for point_index, point in enumerate(points):
            point = _require_object(point, f"{source_id}.data[{point_index}]")
            station_id = str(point.get("stationId", ""))
            station = station_index.get(station_id)
            value = point.get("value")
            if station is None or not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                continue
            location = _require_object(station.get("location"), f"{source_id}.station.location")
            latitude, longitude = location.get("latitude"), location.get("longitude")
            if (not isinstance(latitude, (int, float)) or isinstance(latitude, bool) or not math.isfinite(latitude)
                    or not isinstance(longitude, (int, float)) or isinstance(longitude, bool) or not math.isfinite(longitude)
                    or not -90 <= latitude <= 90 or not -180 <= longitude <= 180):
                continue
            rows.append({
                "observation_id": _stable_id("wobs", source_id, station_id, observed_at, variable),
                "source_id": source_id,
                "snapshot_id": snapshot_id,
                "station_id": station_id,
                "station_name": station.get("name"),
                "latitude": latitude,
                "longitude": longitude,
                "variable": variable,
                "value": value,
                "unit": unit,
                "interval_minutes": 5,
                "observed_at": observed_at,
                "available_at": observed_at,
                "availability_status": "uncertain_assumed_equal_to_observed_at",
                "eligible_for_point_in_time_features": False,
                "retrieved_at": retrieved_at,
                "quality_flags": ["automated_station", "subject_to_provider_correction"],
                "raw_locator": f"data.readings[{reading_index}].data[{point_index}]",
            })
    if not rows:
        raise ValueError(f"{source_id} yielded no valid station observations")
    return rows


def _forecast_row(*, source_id: str, snapshot_id: str, retrieved_at: str, issued_at: str, available_at: str,
                  valid_from: str, valid_to: str, location_id: str, variable: str, value: Any, unit: str | None,
                  raw_locator: str) -> dict[str, Any]:
    if isinstance(value, (int, float)) and (isinstance(value, bool) or not math.isfinite(value)):
        raise ValueError(f"{source_id} forecast {variable} is non-finite")
    lead_hours = (datetime.fromisoformat(valid_from).astimezone(timezone.utc) - datetime.fromisoformat(issued_at).astimezone(timezone.utc)).total_seconds() / 3600
    return {
        "forecast_id": _stable_id("wfc", source_id, issued_at, valid_from, location_id, variable),
        "source_id": source_id, "snapshot_id": snapshot_id, "model": "NEA operational forecast",
        "issued_at": issued_at, "available_at": available_at, "retrieved_at": retrieved_at,
        "availability_status": "provider_updated_timestamp", "eligible_for_point_in_time_features": True,
        "valid_from": valid_from, "valid_to": valid_to, "lead_hours": lead_hours,
        "location_id": location_id, "variable": variable, "value": value, "unit": unit,
        "raw_locator": raw_locator,
    }


def normalize_24h_forecast(payload: dict[str, Any], *, snapshot_id: str, retrieved_at: str) -> list[dict[str, Any]]:
    data = validate_envelope(payload, "D04")
    records = data.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("D04 lacks forecast records")
    rows: list[dict[str, Any]] = []
    for record_index, record_value in enumerate(records):
        record = _require_object(record_value, "D04 record")
        issued_at = str(record["timestamp"])
        available_at = str(record.get("updatedTimestamp") or issued_at)
        general = _require_object(record.get("general"), "D04 general")
        valid = _require_object(general.get("validPeriod"), "D04 general.validPeriod")
        start, end = str(valid["start"]), str(valid["end"])
        measures = [
            ("temperature_low", general.get("temperature", {}).get("low"), "degC"),
            ("temperature_high", general.get("temperature", {}).get("high"), "degC"),
            ("relative_humidity_low", general.get("relativeHumidity", {}).get("low"), "%"),
            ("relative_humidity_high", general.get("relativeHumidity", {}).get("high"), "%"),
            ("forecast_condition", general.get("forecast", {}).get("text"), None),
        ]
        for variable, value, unit in measures:
            if value is not None:
                rows.append(_forecast_row(source_id="D04", snapshot_id=snapshot_id, retrieved_at=retrieved_at,
                    issued_at=issued_at, available_at=available_at, valid_from=start, valid_to=end,
                    location_id="singapore", variable=variable, value=value, unit=unit,
                    raw_locator=f"data.records[{record_index}].general"))
        periods = record.get("periods", [])
        if isinstance(periods, list):
            for period_index, period_value in enumerate(periods):
                period = _require_object(period_value, "D04 period")
                window = _require_object(period.get("timePeriod"), "D04 timePeriod")
                regions = _require_object(period.get("regions"), "D04 regions")
                for region, condition in regions.items():
                    if isinstance(condition, dict) and condition.get("text"):
                        rows.append(_forecast_row(source_id="D04", snapshot_id=snapshot_id, retrieved_at=retrieved_at,
                            issued_at=issued_at, available_at=available_at, valid_from=str(window["start"]), valid_to=str(window["end"]),
                            location_id=f"region:{region}", variable="forecast_condition", value=condition["text"], unit=None,
                            raw_locator=f"data.records[{record_index}].periods[{period_index}].regions.{region}"))
    return rows


def normalize_4d_forecast(payload: dict[str, Any], *, snapshot_id: str, retrieved_at: str) -> list[dict[str, Any]]:
    data = validate_envelope(payload, "D05")
    records = data.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("D05 lacks forecast records")
    rows: list[dict[str, Any]] = []
    for record_index, record_value in enumerate(records):
        record = _require_object(record_value, "D05 record")
        issued_at = str(record["timestamp"])
        available_at = str(record.get("updatedTimestamp") or issued_at)
        forecasts = record.get("forecasts")
        if not isinstance(forecasts, list):
            raise ValueError("D05 forecasts must be an array")
        for day_index, day_value in enumerate(forecasts):
            day = _require_object(day_value, "D05 day")
            start_dt = datetime.fromisoformat(str(day["timestamp"]))
            end_dt = start_dt.replace(hour=23, minute=59, second=59)
            measures = [
                ("temperature_low", day.get("temperature", {}).get("low"), "degC"),
                ("temperature_high", day.get("temperature", {}).get("high"), "degC"),
                ("relative_humidity_low", day.get("relativeHumidity", {}).get("low"), "%"),
                ("relative_humidity_high", day.get("relativeHumidity", {}).get("high"), "%"),
                ("forecast_condition", day.get("forecast", {}).get("summary") or day.get("forecast", {}).get("text"), None),
            ]
            for variable, value, unit in measures:
                if value is not None:
                    rows.append(_forecast_row(source_id="D05", snapshot_id=snapshot_id, retrieved_at=retrieved_at,
                        issued_at=issued_at, available_at=available_at, valid_from=start_dt.isoformat(), valid_to=end_dt.isoformat(),
                        location_id="singapore", variable=variable, value=value, unit=unit,
                        raw_locator=f"data.records[{record_index}].forecasts[{day_index}]"))
    return rows
