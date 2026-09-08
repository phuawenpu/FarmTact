from __future__ import annotations

import hashlib
import json
import math
from datetime import date, datetime, time, timezone
from typing import Any


POWER_DAILY_URL = "https://power.larc.nasa.gov/api/temporal/daily/point"
POWER_PARAMETERS = ("T2M", "RH2M", "PRECTOTCORR")


def build_query(start: date, end: date, latitude: float, longitude: float) -> dict[str, str]:
    if end < start or (end - start).days > 31:
        raise ValueError("NASA POWER requests must cover 1 to 32 days")
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("invalid point coordinates")
    return {
        "parameters": ",".join(POWER_PARAMETERS), "community": "AG",
        "longitude": str(longitude), "latitude": str(latitude),
        "start": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d"),
        "format": "JSON", "time-standard": "UTC",
    }


def normalize_daily(payload: dict[str, Any], *, snapshot_id: str, retrieved_at: str) -> list[dict[str, Any]]:
    properties = payload.get("properties")
    parameters = properties.get("parameter") if isinstance(properties, dict) else None
    header = payload.get("header")
    parameter_info = payload.get("parameters")
    if not isinstance(parameters, dict) or not isinstance(parameter_info, dict):
        raise ValueError("NASA POWER response lacks parameter data or units")
    rows: list[dict[str, Any]] = []
    variable_map = {"T2M": "air_temperature_daily_mean", "RH2M": "relative_humidity_daily_mean", "PRECTOTCORR": "precipitation_daily_total"}
    for provider_name in POWER_PARAMETERS:
        values = parameters.get(provider_name)
        info = parameter_info.get(provider_name)
        if not isinstance(values, dict) or not isinstance(info, dict) or not info.get("units"):
            raise ValueError(f"NASA POWER missing values or unit for {provider_name}")
        fill_value = header.get("fill_value", -999) if isinstance(header, dict) else -999
        for day_key, value in values.items():
            if value == fill_value or not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                continue
            day = datetime.strptime(day_key, "%Y%m%d").date()
            observed_at = datetime.combine(day, time.min, tzinfo=timezone.utc).isoformat()
            identity = json.dumps([provider_name, day_key, payload.get("geometry")], separators=(",", ":")).encode()
            rows.append({
                "observation_id": f"power-{hashlib.sha256(identity).hexdigest()[:20]}",
                "source_id": "D11", "snapshot_id": snapshot_id, "station_id": None,
                "grid_point": payload.get("geometry", {}).get("coordinates") if isinstance(payload.get("geometry"), dict) else None,
                "variable": variable_map[provider_name], "provider_variable": provider_name,
                "value": value, "unit": info["units"], "interval_minutes": 1440,
                "observed_at": observed_at, "available_at": None,
                "availability_status": "unknown_parameter_release_time_exclude_from_point_in_time_backtests",
                "eligible_for_point_in_time_features": False,
                "retrieved_at": retrieved_at, "time_standard": "UTC",
                "quality_flags": ["gridded_historical_climate", "not_an_on_farm_sensor", "not_a_forecast"],
                "raw_locator": f"properties.parameter.{provider_name}.{day_key}",
            })
    if not rows:
        raise ValueError("NASA POWER response yielded no valid daily observations")
    return rows
