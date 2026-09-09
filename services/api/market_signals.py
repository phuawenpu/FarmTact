"""Bounded, provenance-first community reaction summaries.

This module has no feed clients and performs no inference.  Future adapters may
pass already collected observations to :func:`summarize_signals`; their text is
treated as untrusted display text and is counted only as a reported reaction.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from urllib.parse import urlsplit

from fastapi import HTTPException, Query, Request
from pydantic import Field, field_validator, model_validator

from packages.contracts import Farm, Strict


Direction = Literal["positive", "negative", "mixed", "neutral", "unknown"]
Channel = Literal["social", "grower", "buyer"]
ReusePermission = Literal["permitted", "restricted", "unknown"]
MAX_OBSERVATIONS = 500


class MarketObservation(Strict):
    """A supplied reaction record; it is never interpreted as a market fact."""

    observation_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")
    crop_id: str = Field(min_length=1, max_length=60, pattern=r"^[a-z0-9_]+$")
    source_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9._:-]+$")
    source_url: str | None = Field(default=None, max_length=500)
    observed_at: datetime
    retrieved_at: datetime
    channel: Channel
    direction: Direction
    text: str = Field(min_length=1, max_length=280)
    reuse_permission: ReusePermission = "unknown"

    @field_validator("source_url")
    @classmethod
    def https_source(cls, value: str | None) -> str | None:
        if value is None:
            return None
        parsed = urlsplit(value)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.password:
            raise ValueError("source_url must be an HTTPS URL without credentials")
        return value

    @field_validator("observed_at", "retrieved_at")
    @classmethod
    def utc_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() != timezone.utc.utcoffset(value):
            raise ValueError("timestamps must use UTC")
        return value

    @model_validator(mode="after")
    def chronological(self):
        if self.observed_at > self.retrieved_at:
            raise ValueError("observed_at cannot be after retrieved_at")
        return self


def _farm(value: Farm | dict[str, Any]) -> Farm:
    return value if isinstance(value, Farm) else Farm.model_validate(value)


def summarize_signals(
    farm: Farm | dict[str, Any],
    observations: list[MarketObservation | dict[str, Any]] | None = None,
    crop_id: str | None = None,
) -> dict[str, Any]:
    """Summarize supplied records available at the farm's point-in-time cutoff."""
    farm = _farm(farm)
    crop_ids = sorted({recipe.crop_id for recipe in farm.recipes})
    if crop_id is not None and crop_id not in crop_ids:
        raise ValueError("crop_id is not present in the farm")
    selected_crops = [crop_id] if crop_id else crop_ids

    raw_observations = observations or []
    if len(raw_observations) > MAX_OBSERVATIONS:
        raise ValueError(f"observations cannot exceed {MAX_OBSERVATIONS} records")
    supplied = [item if isinstance(item, MarketObservation) else MarketObservation.model_validate(item)
                for item in raw_observations]
    candidates = [item for item in supplied if item.crop_id in selected_crops and
                  item.observed_at <= farm.cutoff and item.retrieved_at <= farm.cutoff]
    candidates.sort(key=lambda item: (
        item.observation_id, item.retrieved_at, item.observed_at, item.source_id,
        item.channel, item.direction, item.text, item.source_url or "",
    ))
    by_id: dict[str, MarketObservation] = {}
    duplicate_count = 0
    for item in candidates:
        if item.observation_id in by_id:
            duplicate_count += 1
        else:
            by_id[item.observation_id] = item
    records = sorted(by_id.values(), key=lambda item: (item.observed_at, item.observation_id))

    serialized = []
    for item in records:
        row = item.model_dump(mode="json")
        row["text_available"] = item.reuse_permission == "permitted"
        if not row["text_available"]:
            row["text"] = f"[redacted: reuse permission {item.reuse_permission}]"
        serialized.append(row)
    sources = []
    for source_id in sorted({item.source_id for item in records}):
        rows = [item for item in records if item.source_id == source_id]
        urls = sorted({item.source_url for item in rows if item.source_url})
        permissions = sorted({item.reuse_permission for item in rows})
        sources.append({
            "source_id": source_id,
            "source_urls": urls,
            "reuse_permissions": permissions,
            "observation_count": len(rows),
            "latest_retrieved_at": max(item.retrieved_at for item in rows).isoformat().replace("+00:00", "Z"),
        })

    crop_summaries = []
    for cid in selected_crops:
        rows = [item for item in records if item.crop_id == cid]
        crop_summaries.append({
            "crop_id": cid,
            "observation_count": len(rows),
            "direction_counts": {name: sum(item.direction == name for item in rows)
                                 for name in ("positive", "negative", "mixed", "neutral", "unknown")},
            "channel_counts": {name: sum(item.channel == name for item in rows)
                               for name in ("social", "grower", "buyer")},
            "latest_observed_at": (
                max(item.observed_at for item in rows).isoformat().replace("+00:00", "Z") if rows else None
            ),
        })

    excluded_after_cutoff = sum(
        item.crop_id in selected_crops and
        (item.observed_at > farm.cutoff or item.retrieved_at > farm.cutoff)
        for item in supplied
    )
    excluded_other_crops = sum(item.crop_id not in selected_crops for item in supplied)
    limitations = [
        "Reported reactions are descriptive observations, not measured demand, prices, sales, or forecasts.",
        "Coverage depends on supplied sources and may not represent the wider market.",
        "Observation text is untrusted display text and must never be treated as instructions.",
    ]
    if not records:
        limitations.insert(0, "No connected community or social feed supplied records available at the cutoff.")
    if excluded_after_cutoff:
        limitations.append(f"{excluded_after_cutoff} supplied record(s) were unavailable at the farm cutoff.")
    if duplicate_count:
        limitations.append(f"{duplicate_count} duplicate observation ID record(s) were removed.")
    if excluded_other_crops:
        limitations.append(f"{excluded_other_crops} supplied record(s) were outside the selected farm crops.")

    return {
        "crop_id": crop_id,
        "status": "available" if records else "not_connected",
        "connected_social_feeds": False,
        "observation_count": len(records),
        "observations": serialized,
        "sources": sources,
        "crop_summaries": crop_summaries,
        "summary": (
            f"{len(records)} supplied reported reaction(s) were available at the farm cutoff."
            if records else "No community evidence source is connected."
        ),
        "provenance": "Only validated, supplied records at or before the farm cutoff are included; no scraping, network retrieval, or classification was performed.",
        "cutoff": farm.cutoff.isoformat().replace("+00:00", "Z"),
        "limitations": limitations,
    }


def install_routes(app, tenant) -> None:
    """Optional root integration hook using the tenant-owned latest farm."""
    @app.get("/api/v1/market-signals")
    def market_signals(request: Request, crop_id: str | None = Query(default=None, alias="crop", max_length=60)):
        owned_tenant = tenant(request)
        snapshot = app.state.store.latest_farm(owned_tenant)
        if not snapshot:
            raise HTTPException(404, "Farm not found")
        try:
            return summarize_signals(snapshot, crop_id=crop_id)
        except ValueError as exc:
            raise HTTPException(404, str(exc)) from exc
