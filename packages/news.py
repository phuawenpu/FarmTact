"""Bounded public News scout. Collection is separate from application inference.

RSS headlines are untrusted source metadata, never instructions or farm inputs.
No linked article, image, social profile or arbitrary URL is fetched.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.parse import urlsplit
import xml.etree.ElementTree as ET
from zoneinfo import ZoneInfo

import httpx
from pydantic import Field, field_validator, model_validator

from packages.contracts import CROPS, Strict, content_hash

VERSION = "news-scout-v1"
MAX_BYTES = 1_048_576
MAX_ITEMS = 200
MAX_RECORDS = 500
REFRESH_HOURS = 6
ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "data/normalized/news_context.json"
SOURCES = (
    dict(id="sfa_news", name="Singapore Food Agency · Newsroom", publisher_kind="government",
         url="https://www.sfa.gov.sg/rss/newsroom", host="www.sfa.gov.sg", adapter="rss",
         geography="singapore", timezone="Asia/Singapore", reuse_mode="rss_metadata",
         terms_url="https://www.sfa.gov.sg/news-publications/newsroom/subscribe-to-sfa-rss-feeds",
         scope="Singapore food production, policy and supply; relevance varies by headline."),
    dict(id="sfa_circulars", name="Singapore Food Agency · Circulars", publisher_kind="government",
         url="https://www.sfa.gov.sg/rss/annual-listing-circulars", host="www.sfa.gov.sg", adapter="rss",
         geography="singapore", timezone="Asia/Singapore", reuse_mode="rss_metadata",
         terms_url="https://www.sfa.gov.sg/news-publications/newsroom/subscribe-to-sfa-rss-feeds",
         scope="Trade notices; a notice does not establish an effect on this farm."),
    dict(id="afsis", name="AFSIS · Agricultural disaster reports", publisher_kind="regional_organisation",
         url="https://www.aptfsis.org/rssfeed", host="www.aptfsis.org", adapter="rss",
         geography="regional", timezone=None, reuse_mode="rss_metadata",
         terms_url="https://www.aptfsis.org/publication/disaster",
         scope="ASEAN agricultural hazards; these are not measurements of Singapore leafy crops."),
    dict(id="asean_agrifood", name="ASEAN Agri-food / GIZ programme", publisher_kind="regional_programme",
         url="https://asean-agrifood.org/feed/", host="asean-agrifood.org", adapter="rss",
         geography="regional", timezone=None, reuse_mode="rss_metadata",
         terms_url="https://asean-agrifood.org/feed/",
         scope="Regional agriculture programme updates; coverage includes other crops and languages."),
    dict(id="reddit", name="Reddit · Singapore community discussions", publisher_kind="community",
         url="https://www.reddit.com/dev/api/", adapter="unavailable", geography="singapore",
         reuse_mode="blocked", terms_url="https://redditinc.com/policies/data-api-terms",
         scope="Approved API access and retention/deletion controls required. No discussions collected."),
    dict(id="safef", name="SAFEF · Local-produce community", publisher_kind="industry",
         url="https://www.safef.org.sg/activities", adapter="unavailable", geography="singapore",
         reuse_mode="link_only", terms_url="https://www.safef.org.sg/activities",
         scope="No reusable dated feed verified. Open the organisation's activities page for context."),
    dict(id="cdc_events", name="Central Singapore CDC · Market calendar", publisher_kind="government",
         url=None, adapter="unavailable", geography="singapore", reuse_mode="blocked",
         terms_url=None, scope="Calendar found, but published reuse terms require permission. No events copied."),
)


def instant(value: str | datetime) -> datetime:
    if not isinstance(value,(str,datetime)): raise ValueError("An ISO timestamp or aware datetime is required")
    result = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("An aware timestamp is required")
    return result.astimezone(timezone.utc)


def stamp(value: datetime) -> str:
    return instant(value).isoformat().replace("+00:00", "Z")


def https_url(value: str, host: str | None = None) -> str:
    parsed = urlsplit(value)
    if (len(value) > 1000 or parsed.scheme != "https" or not parsed.hostname or
            parsed.username or parsed.password or parsed.port not in (None, 443) or
            (host and parsed.hostname != host) or any(ord(c) < 33 for c in value)):
        raise ValueError("Invalid source URL")
    return value


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(); self.parts = []; self.skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"): self.skip += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style"): self.skip = max(0, self.skip - 1)

    def handle_data(self, data):
        if not self.skip: self.parts.append(data)


def plain(value: str, limit: int = 240) -> str:
    parser = _Text(); parser.feed(value[:10000])
    return " ".join(" ".join(parser.parts).split())[:limit]


def record_hash(fields: dict) -> str:
    # An absent observation time has no semantic content. Keep hashes compatible
    # with v1 metadata collected before this optional field was exposed.
    return content_hash({k:v for k,v in fields.items() if k not in ('content_hash','retrieved_at') and not (k=='observed_at' and v is None)})


class NewsRecord(Strict):
    id: str = Field(pattern=r"^news_[0-9a-f]{24}$")
    source_id: str = Field(max_length=40)
    external_id: str = Field(max_length=500)
    title: str = Field(min_length=1, max_length=240)
    canonical_url: str = Field(max_length=1000)
    published_at_raw: str = Field(max_length=150)
    published_at: datetime
    retrieved_at: datetime
    observed_at: datetime | None = None
    event_start_at: datetime | None = None
    event_end_at: datetime | None = None
    event_date_basis: str | None = Field(default=None, max_length=80)
    geography: str = Field(pattern=r"^(singapore|regional)$")
    crop_ids: list[str] = Field(default_factory=list, max_length=10)
    topics: list[str] = Field(default_factory=list, max_length=8)
    quality_issues: list[str] = Field(default_factory=list, max_length=12)
    reuse_mode: str = Field(default="rss_metadata", pattern=r"^rss_metadata$")
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("canonical_url")
    @classmethod
    def source_url(cls, value): return https_url(value)

    @field_validator("published_at", "retrieved_at", "observed_at", "event_start_at", "event_end_at")
    @classmethod
    def dates(cls, value): return instant(value) if value is not None else None

    @model_validator(mode="after")
    def integrity(self):
        source = next((s for s in SOURCES if s["id"] == self.source_id and s["adapter"] == "rss"), None)
        if not source: raise ValueError("Unknown collected source")
        https_url(self.canonical_url, source["host"])
        parsed, _ = parse_publication(self.published_at_raw, source)
        if parsed != self.published_at: raise ValueError("Publication date does not match source value")
        if self.id != "news_" + content_hash([self.source_id, self.external_id])[:24]: raise ValueError("News identity mismatch")
        if self.published_at.year < 2000 or self.published_at > self.retrieved_at:
            raise ValueError("Publication time is invalid or after retrieval")
        if any(value and value.year < 2000 for value in (self.observed_at,self.event_start_at,self.event_end_at)): raise ValueError("Invalid observation/event year")
        if self.observed_at and self.observed_at > self.retrieved_at: raise ValueError("Observation cannot follow retrieval")
        if self.event_end_at and (not self.event_start_at or self.event_end_at < self.event_start_at):
            raise ValueError("Invalid event interval")
        if self.event_start_at and not self.event_date_basis: raise ValueError("Event dates need an explicit source basis")
        if any(c not in CROPS for c in self.crop_ids): raise ValueError("Unknown crop tag")
        data = self.model_dump(mode="json", exclude={"content_hash", "retrieved_at"})
        if record_hash(data) != self.content_hash: raise ValueError("News content hash mismatch")
        return self


def parse_publication(raw: str, source: dict) -> tuple[datetime, list[str]]:
    issues = []
    year = re.search(r"\b(\d{4})\b", raw)
    if not year or int(year.group(1)) < 2000: raise ValueError("Invalid explicit publication year")
    try:
        if re.fullmatch(r"\d{1,2} [A-Za-z]{3} \d{4} \d{1,2}:\d{2} (?:AM|PM)", raw, re.I):
            result = datetime.strptime(raw, "%d %b %Y %I:%M %p")
        else: result = parsedate_to_datetime(raw)
    except (ValueError, TypeError):
        try: result = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError: result = datetime.strptime(raw, "%d %b %Y %I:%M %p")
    if result.tzinfo is None:
        if not source.get("timezone"): raise ValueError("Source publication timezone missing")
        result = result.replace(tzinfo=ZoneInfo(source["timezone"]))
        issues.append("publication_timezone_assumed_Asia_Singapore")
    return instant(result), issues


ALIASES = {"caixin": ("caixin", "choy sum"), "pak_choi": ("pak choi", "bok choy", "xiao bai cai"),
           "kailan": ("kailan", "kai lan", "chinese kale"), "bayam": ("bayam", "amaranth"),
           "kangkong": ("kangkong", "water spinach"), "lettuce": ("lettuce",), "kale": ("curly kale",),
           "mustard_greens": ("mustard greens",), "malabar_spinach": ("malabar spinach", "ceylon spinach"),
           "sweet_potato_leaves": ("sweet potato leaves", "sweet-potato leaves")}
TOPICS = {"weather": ("flood", "rainfall", "cyclone", "drought", "earthquake"),
          "production": ("farm", "agricultur", "grow", "vegetable", "crop", "agri-space"),
          "trade": ("trade", "import", "export", "supply", "tender"),
          "community": ("market", "community", "event", "workshop", "training"),
          "policy": ("policy", "regulat", "requirement", "circular", "programme")}


def parse_feed(source: dict, payload: bytes, retrieved_at: datetime) -> tuple[list[dict], int]:
    if len(payload) > MAX_BYTES or re.search(br"<!\s*(DOCTYPE|ENTITY)", payload, re.I):
        raise ValueError("Feed exceeds bounds or contains forbidden XML declarations")
    decoded = payload.decode("utf-8-sig")
    if "\x00" in decoded: raise ValueError("Only UTF-8 feed XML is supported")
    root = ET.fromstring(decoded)
    records = []; rejected = 0; seen = set()
    for item in root.findall("./channel/item")[:MAX_ITEMS]:
        try:
            title = plain(item.findtext("title") or "")
            url = https_url((item.findtext("link") or "").strip(), source["host"])
            raw = (item.findtext("pubDate") or "").strip()[:150]
            published, issues = parse_publication(raw, source)
            if published > retrieved_at or published.year < 2000: raise ValueError("Invalid publication date")
            external = (item.findtext("guid") or url).strip()[:500]
            identity = "news_" + content_hash([source["id"], external])[:24]
            if identity in seen: continue
            fields = dict(id=identity, source_id=source["id"], external_id=external,
                          title=title, canonical_url=url, published_at_raw=raw,
                          published_at=stamp(published), retrieved_at=stamp(retrieved_at),
                          observed_at=None, event_start_at=None, event_end_at=None, event_date_basis=None,
                          geography=source["geography"],
                          crop_ids=[crop for crop, aliases in ALIASES.items() if any(a in title.lower() for a in aliases)],
                          topics=[topic for topic, words in TOPICS.items() if any(w in title.lower() for w in words)],
                          quality_issues=issues, reuse_mode="rss_metadata")
            # Accept only explicitly structured event dates. Never guess from a
            # publication date, year in a headline, or an LLM interpretation.
            event = {child.tag.split("}")[-1]: child.text for child in item
                     if child.tag in ("{https://schema.org/}startDate", "{https://schema.org/}endDate")}
            if event.get("startDate"):
                fields.update(event_start_at=stamp(instant(event["startDate"])),
                              event_end_at=stamp(instant(event["endDate"])) if event.get("endDate") else None,
                              event_date_basis="explicit_schema_org_RSS_event_fields")
            fields["content_hash"] = record_hash(fields)
            records.append(NewsRecord.model_validate(fields).model_dump(mode="json")); seen.add(identity)
        except (ValueError, TypeError, OverflowError): rejected += 1
    return records, rejected


def empty_cache() -> dict:
    return dict(version=VERSION, refreshed_at=None, records=[], sources=[
        dict(source_id=s["id"], status="not_collected" if s["adapter"] == "rss" else "not_connected",
             last_attempt_at=None, last_success_at=None, record_count=0, rejected_count=0) for s in SOURCES])


class SourceState(Strict):
    source_id: str
    status: str = Field(pattern=r"^(available|not_collected|not_connected|refresh_failed|unavailable)$")
    last_attempt_at: datetime | None = None
    last_success_at: datetime | None = None
    record_count: int = Field(default=0,ge=0,le=MAX_ITEMS)
    rejected_count: int = Field(default=0,ge=0,le=MAX_ITEMS)
    error_kind: str | None = Field(default=None,max_length=80,pattern=r"^[A-Za-z]+$")

    @field_validator("last_attempt_at", "last_success_at")
    @classmethod
    def timestamps(cls,value):
        if value is not None and instant(value).year < 2000: raise ValueError("Invalid source timestamp")
        return instant(value) if value is not None else None

    @model_validator(mode="after")
    def source_and_dates(self):
        if self.source_id not in {s["id"] for s in SOURCES}: raise ValueError("Unknown source state")
        if self.last_success_at and (not self.last_attempt_at or self.last_success_at > self.last_attempt_at): raise ValueError("Invalid success time")
        return self


def load_cache(path: Path = CACHE) -> dict:
    if not path.is_file(): return empty_cache()
    try:
        if path.stat().st_size > MAX_BYTES * 2: raise ValueError("Cache exceeds bounds")
        data = json.loads(path.read_text())
        if data["version"] != VERSION or len(data["records"]) > MAX_RECORDS: raise ValueError("Invalid cache version/size")
        data["records"] = [NewsRecord.model_validate(r).model_dump(mode="json") for r in data["records"]]
        refreshed = instant(data["refreshed_at"])
        if refreshed.year < 2000: raise ValueError("Invalid cache timestamp")
        states = [SourceState.model_validate(s) for s in data["sources"]]
        if len(states) != len(SOURCES) or {s.source_id for s in states} != {s["id"] for s in SOURCES}: raise ValueError("Invalid source inventory")
        if any(s.last_attempt_at and s.last_attempt_at > refreshed for s in states): raise ValueError("Source state after cache cutoff")
        if any(instant(r['retrieved_at']) > refreshed for r in data['records']): raise ValueError("Record after cache cutoff")
        data['sources'] = [s.model_dump(mode='json',exclude_none=True) for s in states]
        return data
    except (ValueError, KeyError, TypeError, OSError):
        data = empty_cache(); data["quality_issue"] = "cache_invalid"; return data


def refresh(path: Path = CACHE, *, client=None, at: datetime | None = None) -> dict:
    """CLI-only refresh with strict per-source host, byte and six-hour limits."""
    at = instant(at or datetime.now(timezone.utc)); previous = load_cache(path)
    owned = client is None
    client = client or httpx.Client(timeout=httpx.Timeout(15, connect=5), follow_redirects=False,
                                    trust_env=False, headers={"User-Agent": "FarmTact-NewsScout/1.0 (RSS metadata reader)"})
    records = []; states = []
    try:
        for source in SOURCES:
            state = next((s for s in previous["sources"] if s["source_id"] == source["id"]), {})
            old = [r for r in previous["records"] if r["source_id"] == source["id"]]
            if source["adapter"] != "rss":
                states.append(dict(source_id=source["id"], status="not_connected", record_count=0)); continue
            if state.get("last_attempt_at") and timedelta(0) <= at - instant(state["last_attempt_at"]) < timedelta(hours=REFRESH_HOURS):
                records.extend(old); states.append(state); continue
            row = dict(source_id=source["id"], last_attempt_at=stamp(at), last_success_at=state.get("last_success_at"), rejected_count=0)
            try:
                with client.stream("GET", source["url"], follow_redirects=False, headers={"Accept-Encoding":"identity"}) as response:
                    response.raise_for_status()
                    if response.headers.get("content-encoding", "identity").lower() not in ("", "identity"): raise ValueError("Compressed feeds are not accepted")
                    kind = response.headers.get("content-type", "").split(";")[0]
                    if kind not in ("text/xml", "application/xml", "application/rss+xml"): raise ValueError("Unexpected feed media type")
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_BYTES: raise ValueError("Feed exceeds byte limit")
                fresh, rejected = parse_feed(source, bytes(body), at)
                if not fresh: raise ValueError("No valid dated feed records")
                records.extend(fresh)
                row.update(status="available", last_success_at=stamp(at), record_count=len(fresh), rejected_count=rejected)
            except (httpx.HTTPError, ValueError, ET.ParseError) as exc:
                records.extend(old)
                row.update(status="refresh_failed" if old else "unavailable", record_count=len(old), error_kind=type(exc).__name__)
            states.append(row)
    finally:
        if owned: client.close()
    records.sort(key=lambda r: (r["published_at"], r["id"]), reverse=True)
    result = dict(version=VERSION, refreshed_at=stamp(at), records=records[:MAX_RECORDS], sources=states)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp"); temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n"); temporary.replace(path)
    return result


def context(*, cutoff: datetime, farm_cutoff: datetime | None = None, cache: dict | None = None,
            crop: str | None = None, geography: str = "all", period: str = "all", limit: int = 12) -> dict:
    """Pure point-in-time selection. Both retrieval and publication must be known."""
    cutoff = instant(cutoff); cache = load_cache() if cache is None else cache
    if crop is not None and crop not in CROPS: raise ValueError("Unknown crop")
    if geography not in ("all", "singapore", "regional") or period not in ("all", "recent", "future", "ongoing", "historical"): raise ValueError("Unknown filter")
    if not 1 <= limit <= 50: raise ValueError("Limit outside bounds")
    rows = []; excluded = 0
    for raw in cache["records"]:
        record = NewsRecord.model_validate(raw); row = record.model_dump(mode="json")
        if record.published_at > cutoff or record.retrieved_at > cutoff or (record.observed_at and record.observed_at > cutoff):
            excluded += 1; continue
        if crop and crop not in record.crop_ids: continue
        if geography != "all" and record.geography != geography: continue
        temporal = ("future" if record.event_start_at and record.event_start_at > cutoff else
                    "ongoing" if record.event_start_at and record.event_end_at and record.event_start_at <= cutoff <= record.event_end_at else
                    "recent" if cutoff - record.published_at <= timedelta(days=7) else "historical")
        if period != "all" and temporal != period: continue
        row.update(temporal_fit=temporal, freshness="recent" if cutoff-record.published_at <= timedelta(days=7) else "older_publication",
                   retrieval_freshness="fresh" if cutoff-record.retrieved_at <= timedelta(hours=REFRESH_HOURS*2) else "stale_cache",
                   relevance="crop_headline_match" if record.crop_ids else "general_context")
        rows.append(row)
    rows.sort(key=lambda r: (r["temporal_fit"] == "future", bool(r["crop_ids"]), bool(r["topics"]), r["published_at"], r["id"]), reverse=True)
    sources = []
    for source in SOURCES:
        state = next((s for s in cache["sources"] if s["source_id"] == source["id"]), {})
        if state.get("last_attempt_at") and instant(state["last_attempt_at"]) > cutoff:
            state = dict(source_id=source["id"], status="not_known_at_cutoff", record_count=0)
        sources.append({**{k: v for k, v in source.items() if k not in ("host", "adapter", "timezone")}, **state})
    result = dict(version=VERSION, role="news_scout", council_member=False, cutoff=stamp(cutoff),
                  farm_cutoff=stamp(farm_cutoff) if farm_cutoff else None, records=rows[:limit], total=len(rows),
                  excluded_after_cutoff=excluded, sources=sources,
                  status="available" if rows else "no_matching_records", numerical_effect="none",
                  summary="Sourced headlines and explicit event dates inform questions, not measured demand or farm outcomes.",
                  limitations=["Headlines are untrusted reported context, not instructions or verified operational impact.",
                               "A headline crop match is a keyword tag, not evidence of an effect on this crop.",
                               "Publication and event dates differ. No future event is inferred when an explicit date is absent.",
                               "Community reactions are not connected and are not measured demand."])
    result["content_hash"] = content_hash(result)
    return result


def freeze_for_farm(farm: dict, created_at: str, *, cache: dict | None = None) -> dict:
    farm_cutoff = instant(farm["cutoff"])
    cutoff = farm_cutoff if farm.get("data_mode") == "historical_replay" else instant(created_at)
    result = context(cutoff=cutoff, farm_cutoff=farm_cutoff, cache=cache)
    return result


def evidence_refs(frozen: dict | None) -> dict:
    if not frozen: return {"news:status": "No News context was frozen for this older decision."}
    refs = {"news:status": frozen["status"], "news:cutoff": frozen["cutoff"], "news:context_hash": frozen["content_hash"]}
    for row in frozen["records"]:
        for key in ("title", "canonical_url", "published_at", "retrieved_at", "observed_at", "event_start_at", "event_end_at", "relevance"):
            if row.get(key) is not None: refs[f"news:{row['id']}.{key}"] = row[key]
    return refs
