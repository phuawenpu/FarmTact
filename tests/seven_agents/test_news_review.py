"""Independent, offline boundary tests for the News scout.

Every feed and cache in this module is a local fixture.  A network request or an
inference/provider call is therefore a test failure rather than test setup.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from packages import news
from packages.fixtures import synthetic_farm
from services.api.app import MissionRequest, create_mission
from services.api.store import Store


AT = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)


def rss(*, event_start="2026-10-01T09:00:00+08:00", event_end="2026-10-01T17:00:00+08:00"):
    event = ""
    if event_start:
        event = f"<s:startDate>{event_start}</s:startDate><s:endDate>{event_end}</s:endDate>"
    return (f'<rss xmlns:s="https://schema.org/"><channel><item>'
            f'<title>Caixin grower workshop</title><link>https://www.sfa.gov.sg/news/review</link>'
            f'<guid>review</guid><pubDate>Wed, 09 Sep 2026 09:00:00 +0000</pubDate>{event}'
            f'</item></channel></rss>').encode()


def local_cache(payload=None, retrieved=AT):
    result = news.empty_cache()
    result["refreshed_at"] = news.stamp(retrieved)
    result["records"], rejected = news.parse_feed(news.SOURCES[0], payload or rss(), retrieved)
    assert rejected == 0
    result["sources"][0].update(status="available", last_attempt_at=news.stamp(retrieved),
                                last_success_at=news.stamp(retrieved), record_count=len(result["records"]))
    return result


def test_all_semantic_dates_reject_year_one_and_ongoing_is_filterable():
    rows, rejected = news.parse_feed(news.SOURCES[0], rss(event_start="0001-01-01T00:00:00+00:00",
                                                          event_end="0001-01-02T00:00:00+00:00"), AT)
    assert rows == [] and rejected == 1

    selected = news.context(cutoff=datetime(2026, 10, 1, 2, tzinfo=timezone.utc),
                            cache=local_cache(), period="ongoing")
    assert selected["total"] == 1
    assert selected["records"][0]["temporal_fit"] == "ongoing"


def test_cache_rejects_unvalidated_source_timestamps(tmp_path):
    payload = local_cache()
    payload["sources"][0]["last_attempt_at"] = "0001-01-01T00:00:00Z"
    path = tmp_path / "news.json"
    import json
    path.write_text(json.dumps(payload))
    loaded = news.load_cache(path)
    assert loaded["records"] == []
    assert loaded["quality_issue"] == "cache_invalid"


def test_refresh_never_follows_redirects_even_if_injected_client_would(tmp_path):
    seen = []

    def transport(request):
        seen.append(str(request.url))
        if request.url.host == "collector.invalid":
            pytest.fail("News refresh followed a source redirect to an unallowlisted host")
        return httpx.Response(302, headers={"location": "https://collector.invalid/private"})

    with httpx.Client(transport=httpx.MockTransport(transport), follow_redirects=True) as client:
        result = news.refresh(tmp_path / "news.json", client=client, at=AT)
    assert len(seen) == 4
    assert result["records"] == []
    assert all(state["status"] == "unavailable" for state in result["sources"][:4])


def test_cutoff_excludes_records_if_either_observation_time_is_later():
    payload = local_cache(retrieved=AT)
    before = AT - timedelta(minutes=1)
    selected = news.context(cutoff=before, cache=payload)
    assert selected["records"] == []
    assert selected["excluded_after_cutoff"] == 1
    assert selected["sources"][0]["status"] == "not_known_at_cutoff"


def test_mission_continuation_reuses_parent_news_evidence(monkeypatch):
    first_cache = local_cache(retrieved=AT)
    current = {"value": first_cache}
    monkeypatch.setattr(news, "load_cache", lambda: deepcopy(current["value"]))
    store = Store("sqlite://")
    tenant, _ = store.new_session()
    store.save_farm(tenant, synthetic_farm().model_dump(mode="json"))
    parent = create_mission(store, tenant, MissionRequest(council=False), "review-parent")
    parent_run = store.get_run(tenant, parent["id"])
    frozen = deepcopy(parent_run["news_context"])
    parent_run["status"] = "COMPLETED"
    store.save_run(tenant, parent_run)

    current["value"] = news.empty_cache()
    child = create_mission(store, tenant, MissionRequest(council=False), "review-child", parent=parent["id"])
    child_run = store.get_run(tenant, child["id"])
    assert child_run["news_context"] == frozen
    assert child_run["news_context"]["content_hash"] == frozen["content_hash"]


def test_real_cache_contract_is_metadata_only_and_has_no_implicit_effect():
    if not news.CACHE.is_file():
        pytest.skip("Generated News cache is absent in this clean checkout")
    cached = news.load_cache()
    assert cached.get("quality_issue") is None
    assert cached["refreshed_at"] and cached["records"]
    forbidden = {"article_body", "description", "user_profile", "comments", "demand_effect", "price_effect"}
    for record in cached["records"]:
        assert forbidden.isdisjoint(record)
        assert record["reuse_mode"] == "rss_metadata"
    cutoff = news.instant(cached["refreshed_at"]) if cached["refreshed_at"] else AT
    frozen = news.context(cutoff=cutoff, cache=cached)
    assert frozen["numerical_effect"] == "none"
    assert frozen["council_member"] is False
    assert next(s for s in frozen["sources"] if s["id"] == "reddit")["status"] == "not_connected"
    assert next(s for s in frozen["sources"] if s["id"] == "cdc_events")["reuse_mode"] == "blocked"
