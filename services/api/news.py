"""Tenant-aware access to cached or frozen News evidence, with no network calls."""
from datetime import datetime, timezone
from typing import Literal

from fastapi import HTTPException, Query, Request

from packages.news import context, instant


def install_routes(app, tenant):
    @app.get("/api/v1/news")
    def news(request: Request, crop: str | None = Query(default=None, max_length=40),
             geography: Literal["all", "singapore", "regional"] = "all",
             period: Literal["all", "recent", "future", "ongoing", "historical"] = "all",
             limit: int = Query(default=12, ge=1, le=50),
             scenario_id: str | None = Query(default=None, max_length=64),
             run_id: str | None = Query(default=None, max_length=64)):
        owner = tenant(request)
        if scenario_id and run_id: raise HTTPException(422, "Select one frozen decision")
        if scenario_id or run_id:
            if scenario_id:
                from services.api.scenarios import get_scenario
                decision = get_scenario(app.state.store, owner, scenario_id)
            else:
                decision = app.state.store.get_run(owner, run_id)
            if not decision: raise HTTPException(404, "Decision not found")
            frozen = decision.get("news_context")
            if not frozen:
                return dict(status="not_recorded", records=[], sources=[], total=0, frozen=True, decision_id=scenario_id or run_id,
                            summary="This older decision did not freeze News context; current stories were not substituted.")
            return dict(frozen, frozen=True, decision_id=scenario_id or run_id)
        farm = app.state.store.latest_farm(owner)
        if not farm: raise HTTPException(404, "Farm not found")
        at = datetime.now(timezone.utc)
        if farm.get("data_mode") == "historical_replay": at = instant(farm["cutoff"])
        try:
            return dict(context(cutoff=at, farm_cutoff=instant(farm["cutoff"]), crop=crop,
                                geography=geography, period=period, limit=limit), frozen=False)
        except ValueError as exc: raise HTTPException(422, "Invalid News filter") from exc
