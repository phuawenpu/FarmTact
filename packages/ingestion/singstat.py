from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any


SINGSTAT_TABLE_URL = "https://tablebuilder.singstat.gov.sg/api/table/tabledata/T010002"
SELECTED_HS8_CODES = {"07049020", "07049030", "07051100", "07051900", "07097000", "07099990"}
PRODUCT_PATTERN = re.compile(r"^(?P<code>\d{8})\s+-\s+(?P<description>.+?)\s+\((?P<unit>[A-Z0-9]+)\)$")
UNIT_MAP = {"TNE": "tonne", "KGM": "kg", "NMB": "count", "MTK": "m2"}


def latest_period_from_payload(payload: dict[str, Any]) -> str:
    data = payload.get("Data")
    if payload.get("StatusCode") != 200 or not isinstance(data, dict):
        raise ValueError(f"SingStat response error: {payload.get('Message', 'unknown error')}")
    period = data.get("endPeriod")
    if not isinstance(period, str) or not re.fullmatch(r"\d{4} [A-Z][a-z]{2}", period):
        raise ValueError("SingStat response lacks a valid endPeriod")
    return period


def _stable_id(*parts: object) -> str:
    body = json.dumps(parts, separators=(",", ":"), ensure_ascii=False).encode()
    return f"trade-{hashlib.sha256(body).hexdigest()[:20]}"


def normalize_trade_volume(
    payload: dict[str, Any], *, snapshot_id: str, retrieved_at: str
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    data = payload.get("Data")
    if payload.get("StatusCode") != 200 or not isinstance(data, dict):
        raise ValueError(f"SingStat response error: {payload.get('Message', 'unknown error')}")
    rows = data.get("rows")
    if not isinstance(rows, list):
        raise ValueError("SingStat Data.rows must be an array")
    normalized: list[dict[str, Any]] = []
    invalid_quantities = 0
    for index, row_value in enumerate(rows):
        if not isinstance(row_value, dict):
            continue
        product = str(row_value.get("hs8Products", ""))
        match = PRODUCT_PATTERN.match(product)
        if not match or match.group("code") not in SELECTED_HS8_CODES:
            continue
        raw_quantity = row_value.get("quantity")
        try:
            quantity = Decimal(str(raw_quantity).replace(",", ""))
        except (InvalidOperation, AttributeError):
            invalid_quantities += 1
            continue
        if not quantity.is_finite():
            invalid_quantities += 1
            continue
        period = str(row_value.get("period", ""))
        try:
            period_date = datetime.strptime(period, "%Y %b").date().replace(day=1)
        except ValueError as error:
            raise ValueError(f"unexpected SingStat period {period!r}") from error
        code = match.group("code")
        raw_unit = match.group("unit")
        normalized.append({
            "trade_observation_id": _stable_id(code, row_value.get("market"), row_value.get("tradeType"), period),
            "source_id": "D06", "snapshot_id": snapshot_id, "table_id": "T010002",
            "reporter": "Singapore", "partner": row_value.get("market"), "commodity_code": code,
            "commodity_description": match.group("description"), "nomenclature_version": None,
            "mapping_status": "see_research/crop_hs_mappings.json", "trade_flow": row_value.get("tradeType"),
            "period": period, "period_start": period_date.isoformat(), "measure": "trade_volume",
            "value": str(quantity), "unit": UNIT_MAP.get(raw_unit, raw_unit), "raw_unit": raw_unit,
            "observed_at": datetime.combine(period_date, datetime.min.time(), tzinfo=timezone(timedelta(hours=8))).isoformat(),
            "available_at": None,
            "availability_status": "unknown_exact_release_time_exclude_from_point_in_time_backtests",
            "eligible_for_point_in_time_features": False,
            "retrieved_at": retrieved_at, "provider_data_last_updated": data.get("dataLastUpdated"),
            "flags": [], "raw_locator": f"Data.rows[{index}]",
        })
    coverage = {
        "table_id": "T010002", "title": data.get("title"), "frequency": data.get("frequency"),
        "requested_period_start": data.get("startPeriod"), "requested_period_end": data.get("endPeriod"),
        "provider_rows": len(rows), "selected_rows": len(normalized), "row_count": len(normalized),
        "invalid_selected_quantities": invalid_quantities,
        "is_more": bool(data.get("isMore")), "next_cursor": data.get("nextCursor"),
    }
    return normalized, coverage
