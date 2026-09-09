from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import httpx
import pytest
from fastapi.testclient import TestClient

from packages import news
from packages.contracts import content_hash
from packages.fixtures import synthetic_farm
from services.api.app import create_app
from services.api.store import Store

AT = datetime(2026, 9, 9, 12, tzinfo=timezone.utc)


def feed(*, title="Caixin growers announce a workshop", date="Wed, 09 Sep 2026 09:00:00 +0000", event="", link="https://www.sfa.gov.sg/news/example", guid="example"):
    return f'''<rss xmlns:s="https://schema.org/"><channel><item><title>{title}</title><link>{link}</link><guid>{guid}</guid><pubDate>{date}</pubDate>{event}</item></channel></rss>'''.encode()


def cache(payload=None, at=AT):
    data = news.empty_cache()
    data["records"], rejected = news.parse_feed(news.SOURCES[0], payload or feed(), at)
    assert not rejected
    data["sources"][0].update(status="available", last_attempt_at=news.stamp(at), last_success_at=news.stamp(at), record_count=len(data["records"]))
    return data


def test_reproducible_metadata_hash_and_plain_text_only():
    data = cache(feed(title="&lt;b&gt;Caixin&lt;/b&gt; &lt;script&gt;steal()&lt;/script&gt; workshop"))
    row = data["records"][0]
    assert row["title"] == "Caixin workshop"
    assert row["crop_ids"] == ["caixin"]
    assert row["event_start_at"] is None
    later = cache(feed(title="&lt;b&gt;Caixin&lt;/b&gt; &lt;script&gt;steal()&lt;/script&gt; workshop"), AT+timedelta(hours=1))
    assert later["records"][0]["content_hash"] == row["content_hash"]
    tampered = deepcopy(row); tampered["title"] = "Changed headline"
    with pytest.raises(ValueError, match="hash mismatch"): news.NewsRecord.model_validate(tampered)


@pytest.mark.parametrize("date", ["01 Jan 0001 01:00 AM", "bad date", "Thu, 10 Sep 2026 01:00:00 +0000"])
def test_impossible_missing_and_future_publications_are_rejected(date):
    rows, rejected = news.parse_feed(news.SOURCES[0], feed(date=date), AT)
    assert rows == [] and rejected == 1


def test_timezone_assumption_is_disclosed():
    rows, rejected = news.parse_feed(news.SOURCES[0], feed(date="09 Sep 2026 09:00 AM"), AT)
    assert not rejected
    assert news.instant(rows[0]["published_at"]).hour == 1
    assert "publication_timezone_assumed_Asia_Singapore" in rows[0]["quality_issues"]
    with pytest.raises(ValueError): news.parse_publication("09 Sep 2026 09:00 AM", news.SOURCES[2])


def test_future_event_uses_explicit_event_date_not_publication_or_headline_year():
    data = cache(feed(event="<s:startDate>2026-10-01T09:00:00+08:00</s:startDate><s:endDate>2026-10-01T17:00:00+08:00</s:endDate>"))
    selected = news.context(cutoff=AT, cache=data, period="future")
    assert selected["total"] == 1
    assert selected["records"][0]["temporal_fit"] == "future"
    assert selected["records"][0]["published_at"] != selected["records"][0]["event_start_at"]
    assert news.context(cutoff=AT, cache=cache(feed(title="Caixin workshop in 2027")), period="future")["total"] == 0
    ongoing = news.context(cutoff=datetime(2026,10,1,2,tzinfo=timezone.utc), cache=data)
    assert ongoing["records"][0]["temporal_fit"] == "ongoing"


def test_cutoff_checks_both_publication_and_retrieval_and_hides_later_source_state():
    data = cache()
    result = news.context(cutoff=AT-timedelta(hours=1), cache=data)
    assert result["total"] == 0 and result["excluded_after_cutoff"] == 1
    assert result["sources"][0]["status"] == "not_known_at_cutoff"
    assert "last_attempt_at" not in result["sources"][0]


def test_current_context_and_historical_replay_use_distinct_cutoffs():
    farm = synthetic_farm().model_dump(mode="json")
    current = news.freeze_for_farm(farm, news.stamp(AT), cache=cache())
    assert current["total"] == 1 and current["farm_cutoff"] != current["cutoff"]
    farm["data_mode"] = "historical_replay"
    historical = news.freeze_for_farm(farm, news.stamp(AT), cache=cache())
    assert historical["total"] == 0 and historical["farm_cutoff"] == historical["cutoff"]


def test_filters_staleness_empty_sources_and_no_automatic_effects():
    data = cache()
    assert news.context(cutoff=AT, cache=data, crop="lettuce")["total"] == 0
    assert news.context(cutoff=AT, cache=data, geography="regional")["total"] == 0
    result = news.context(cutoff=AT+timedelta(days=30), cache=data, period="historical")
    assert result["records"][0]["retrieval_freshness"] == "stale_cache"
    assert result["numerical_effect"] == "none" and not result["council_member"]
    assert next(s for s in result["sources"] if s["id"] == "reddit")["status"] == "not_connected"
    for kw in ({"crop":"unknown"},{"geography":"other"},{"period":"today"},{"limit":51}):
        with pytest.raises(ValueError): news.context(cutoff=AT, cache=data, **kw)


@pytest.mark.parametrize("payload", [b'<!DOCTYPE rss [<!ENTITY x "abc">]><rss/>', b'x'*(news.MAX_BYTES+1)])
def test_xml_and_byte_bounds(payload):
    with pytest.raises(ValueError): news.parse_feed(news.SOURCES[0], payload, AT)


@pytest.mark.parametrize("url", ["http://www.sfa.gov.sg/a", "https://evil.example/a", "https://www.sfa.gov.sg:8443/a", "https://secret@www.sfa.gov.sg/a", "javascript:alert(1)"])
def test_feed_cannot_supply_arbitrary_destinations(url):
    assert news.parse_feed(news.SOURCES[0],feed(link=url),AT) == ([],1)


def test_collection_is_allowlisted_bounded_and_preserves_old_cache_on_failure(tmp_path):
    seen=[]
    def transport(request):
        seen.append(str(request.url))
        if request.url.host == 'www.sfa.gov.sg': return httpx.Response(200,content=feed(),headers={'content-type':'text/xml'})
        return httpx.Response(403)
    path=tmp_path/'news.json'
    with httpx.Client(transport=httpx.MockTransport(transport)) as client:
        first=news.refresh(path,client=client,at=AT)
        assert len(seen)==4 and all(url in [s['url'] for s in news.SOURCES if s['adapter']=='rss'] for url in seen)
        second=news.refresh(path,client=client,at=AT+timedelta(minutes=1))
        assert len(seen)==4 and first['records']==second['records']
    with httpx.Client(transport=httpx.MockTransport(lambda r:httpx.Response(503))) as client:
        failed=news.refresh(path,client=client,at=AT+timedelta(hours=7))
    assert failed['records']==first['records']
    assert failed['sources'][0]['status']=='refresh_failed'
    assert failed['sources'][0]['last_success_at']==news.stamp(AT)
    assert news.load_cache(path)['records']==first['records']
    path.write_text('{bad cache')
    assert news.load_cache(path)['quality_issue']=='cache_invalid'


def test_scenario_freezes_news_and_advisor_uses_the_same_records(monkeypatch):
    from services.api.conversation_store import ConversationStore
    original = cache(at=AT-timedelta(days=2), payload=feed(date="Mon, 07 Sep 2026 09:00:00 +0000"))
    monkeypatch.setattr(news, 'load_cache', lambda: deepcopy(original))
    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', lambda *a, **k: pytest.fail('No external HTTP during browse or numerical setup'))
    store=Store('sqlite://')
    with TestClient(create_app(store,start_worker=False)) as client:
        client.get('/api/v1/bootstrap')
        tenant=store.authenticate(client.cookies.get('farmtact_session'))
        body={'name':'News experiment','controls':{'demand_crop_id':'caixin','demand_percent':130}}
        response=client.post('/api/v1/scenarios',json=body,headers={'Idempotency-Key':'news-test'})
        assert response.status_code==201,response.text[:500]
        scenario=response.json(); frozen=deepcopy(scenario['news_context'])
        assert frozen['records'] and frozen['numerical_effect']=='none'
        original['records']=[]
        repeated=client.post('/api/v1/scenarios',json=body,headers={'Idempotency-Key':'news-test'}).json()
        assert repeated['news_context']==frozen
        saved=client.get('/api/v1/news',params={'scenario_id':scenario['id']}).json()
        assert saved['content_hash']==frozen['content_hash'] and saved['frozen']
        assert client.get('/api/v1/news').json()['total']==0
        # Mark numerical work terminal without inventing a computation; this test
        # is for the frozen conversation contract, not numerical acceptance.
        from services.api.scenarios import save_scenario
        scenario['status']='COMPLETED';scenario['result']={'strategies':[]};save_scenario(store,tenant,scenario)
        response=client.post('/api/v1/conversations',json={'advisor':'idris','snapshot_kind':'scenario','snapshot_id':scenario['id']},headers={'Idempotency-Key':'news-conversation'})
        assert response.status_code in (200,201),response.text
        conversation=ConversationStore(store).get_conversation(tenant,response.json()['id'])
        assert conversation['_news_context']==frozen
        assert conversation['_tool_results']['news:context_hash']==frozen['content_hash']
        assert any(k.endswith('.title') and k.startswith('news:news_') for k in conversation['_tool_results'])
        for query in ({'limit':51},{'period':'tomorrow'},{'crop':'not_a_crop'},{'scenario_id':scenario['id'],'run_id':'other'}):
            assert client.get('/api/v1/news',params=query).status_code==422
        with TestClient(create_app(store,start_worker=False)) as other:
            other.get('/api/v1/bootstrap')
            assert other.get('/api/v1/news',params={'scenario_id':scenario['id']}).status_code==404


def test_mission_freeze_and_replay_keep_news_separate_from_farm_hash(monkeypatch):
    from services.api.app import MissionRequest,create_mission
    original=cache(at=AT-timedelta(days=2),payload=feed(date="Mon, 07 Sep 2026 09:00:00 +0000"))
    monkeypatch.setattr(news,'load_cache',lambda:deepcopy(original))
    store=Store('sqlite://')
    with TestClient(create_app(store,start_worker=False)) as client:
        client.get('/api/v1/bootstrap');tenant=store.authenticate(client.cookies.get('farmtact_session'))
        created=create_mission(store,tenant,MissionRequest(council=False),'news-mission')
        run=store.get_run(tenant,created['id'])
        assert run['input_hash']==content_hash(run['input_snapshot'])
        frozen=deepcopy(run['news_context']);original['records']=[]
        assert create_mission(store,tenant,MissionRequest(council=False),'news-mission')['id']==created['id']
        assert store.get_run(tenant,created['id'])['news_context']==frozen
        assert client.get('/api/v1/news',params={'run_id':created['id']}).json()['content_hash']==frozen['content_hash']
