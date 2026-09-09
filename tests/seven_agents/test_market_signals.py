from copy import deepcopy
from datetime import timedelta

import pytest
from pydantic import ValidationError
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from packages.fixtures import synthetic_farm
from services.api.market_signals import MarketObservation, install_routes, summarize_signals


def observation(farm, **changes):
    base = {
        "observation_id": "reaction-1", "crop_id": "caixin", "source_id": "grower-forum",
        "source_url": "https://example.org/posts/1", "observed_at": farm.cutoff - timedelta(hours=2),
        "retrieved_at": farm.cutoff - timedelta(hours=1), "channel": "grower",
        "direction": "mixed", "text": "Reported uneven interest; <script>alert(1)</script>",
        "reuse_permission": "permitted",
    }
    base.update(changes)
    return base


def test_no_records_is_explicitly_not_connected():
    result = summarize_signals(synthetic_farm())
    assert result["status"] == "not_connected"
    assert result["connected_social_feeds"] is False
    assert result["observation_count"] == 0
    assert result["observations"] == result["sources"] == []
    assert all(item["observation_count"] == 0 for item in result["crop_summaries"])


def test_future_records_are_excluded_at_point_in_time_cutoff():
    farm = synthetic_farm()
    result = summarize_signals(farm, [observation(farm, retrieved_at=farm.cutoff + timedelta(seconds=1))])
    assert result["status"] == "not_connected"
    assert result["observation_count"] == 0
    assert any("cutoff" in caveat for caveat in result["limitations"])


def test_crop_filter_and_duplicate_ids_are_deterministic():
    farm = synthetic_farm()
    duplicate = observation(farm, text="second copy", retrieved_at=farm.cutoff)
    pak_choi = observation(farm, observation_id="reaction-2", crop_id="pak_choi")
    a = summarize_signals(farm, [duplicate, pak_choi, observation(farm)], crop_id="caixin")
    b = summarize_signals(farm, [observation(farm), duplicate, pak_choi], crop_id="caixin")
    assert a == b
    assert a["observation_count"] == 1
    assert a["crop_summaries"][0]["crop_id"] == "caixin"
    assert any("duplicate" in caveat for caveat in a["limitations"])


def test_source_provenance_and_counts_do_not_claim_market_demand():
    farm = synthetic_farm()
    result = summarize_signals(farm, [observation(farm)])
    assert result["sources"] == [{
        "source_id": "grower-forum", "source_urls": ["https://example.org/posts/1"],
        "reuse_permissions": ["permitted"], "observation_count": 1,
        "latest_retrieved_at": (farm.cutoff - timedelta(hours=1)).isoformat().replace("+00:00", "Z"),
    }]
    assert result["crop_summaries"][0]["direction_counts"]["mixed"] == 1
    combined = " ".join(result["limitations"] + [result["provenance"]]).lower()
    assert "not measured demand" in combined and "prices" in combined


def test_untrusted_text_is_preserved_for_react_text_rendering_not_interpreted():
    farm = synthetic_farm()
    raw = observation(farm)["text"]
    result = summarize_signals(farm, [observation(farm)])
    assert result["observations"][0]["text"] == raw
    assert result["observations"][0]["text_available"] is True
    assert "untrusted display text" in " ".join(result["limitations"])


@pytest.mark.parametrize("permission", ["restricted", "unknown"])
def test_text_without_explicit_reuse_permission_is_redacted_but_counted(permission):
    farm = synthetic_farm()
    result = summarize_signals(farm, [observation(farm, reuse_permission=permission, text="private reaction")])
    assert result["observation_count"] == 1
    assert result["crop_summaries"][0]["direction_counts"]["mixed"] == 1
    assert result["observations"][0]["text_available"] is False
    assert result["observations"][0]["text"] == f"[redacted: reuse permission {permission}]"


def test_observation_batch_has_hard_bound():
    farm = synthetic_farm()
    with pytest.raises(ValueError, match="cannot exceed 500"):
        summarize_signals(farm, [observation(farm)] * 501)


@pytest.mark.parametrize("changes", [
    {"source_url": "http://example.org/nope"},
    {"observed_at": "2026-01-01T01:00:00+01:00", "retrieved_at": "2026-01-01T02:00:00+01:00"},
    {"text": "x" * 281},
])
def test_observation_schema_rejects_unbounded_or_unsafe_provenance(changes):
    with pytest.raises(ValidationError):
        MarketObservation.model_validate(observation(synthetic_farm(), **changes))


def test_unknown_crop_filter_is_rejected():
    with pytest.raises(ValueError, match="not present"):
        summarize_signals(synthetic_farm(), crop_id="durian")


class _Store:
    def latest_farm(self, tenant):
        assert tenant == "tenant-1"
        return synthetic_farm().model_dump(mode="json")


def test_route_requires_tenant_and_uses_crop_query_alias():
    app = FastAPI()
    app.state.store = _Store()

    def tenant(request):
        if request.headers.get("X-Test-Tenant") != "yes":
            raise HTTPException(401, "Development session required")
        return "tenant-1"

    install_routes(app, tenant)
    with TestClient(app) as client:
        assert client.get("/api/v1/market-signals").status_code == 401
        filtered = client.get("/api/v1/market-signals?crop=caixin", headers={"X-Test-Tenant": "yes"})
        assert filtered.status_code == 200
        assert filtered.json()["crop_id"] == "caixin"
        missing = client.get("/api/v1/market-signals?crop=durian", headers={"X-Test-Tenant": "yes"})
        assert missing.status_code == 404
