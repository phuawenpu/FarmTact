# V5 News-agent source research

Reviewed and probed: 2026-09-09 UTC  
Status: connector plan; no collector, provider call or application behavior implemented

## Role boundary

The News agent should be a **collector and support role**, outside FarmTact's seven-role decision council. It retrieves, normalises, filters and presents time-bounded source records. It does not vote for a strategy, estimate demand, change yield, infer price movement or convert public reaction into farm facts.

For a planning mission, the backend should freeze a news-context pack at the mission cutoff. Demand, Market, Weather, Supply Chain or Planner may cite a relevant record, but any claimed operational consequence must still be supported by farm records or a declared scenario assumption. The seven decision roles remain Demand, Weather, Market, Production, Supply Chain, Profit and Planner.

This keeps “today's news” reproducible. A replay uses the frozen record IDs, retrieved timestamps and content hashes; it does not silently refresh. Browsing the feed should be local/numerical and make no inference call. If a future implementation offers a generated digest, it must be a separate explicit action with citations, bounded input and the existing approved provider policy.

## Recommended first connectors

### 1. SFA Newsroom RSS — implement first

- Feed: [https://www.sfa.gov.sg/rss/newsroom](https://www.sfa.gov.sg/rss/newsroom)
- Official discovery page: [Subscribe to SFA RSS Feeds](https://www.sfa.gov.sg/news-publications/newsroom/subscribe-to-sfa-rss-feeds)
- Probe result: HTTP 200, `text/xml`, 155 items observed, no credential. The feed supplies GUID, title, short description, canonical link and `pubDate`.
- Fit: Singapore food resilience, farm land, local production, food trade, regulatory actions and supply disruptions. An observed item was “Closing of Land Tender for Singapore Agri-space Sales (SAS) Programme 2026”, published 28 July 2026. This is an example of feed coverage, not a claim about current farm conditions.
- Timestamp caution: one old item carried year `0001`; reject impossible dates and keep a quality warning. RSS publication time has no explicit timezone in the observed value, so preserve the source string and parse only under a documented SFA timezone rule.
- Reuse: SFA expressly publishes the endpoint for RSS reading. Store/display feed metadata and canonical links. Do not copy full linked articles unless the applicable SFA terms have been reviewed for that use.

The companion [Circulars RSS](https://www.sfa.gov.sg/rss/annual-listing-circulars) (HTTP 200, 123 observed items) and [Food Alerts/Recalls RSS](https://www.sfa.gov.sg/rss/annual-listing-food-alerts) (HTTP 200, 40 observed items) can use the same adapter. Circulars suit future-effective regulatory notices; alerts suit immediate food-safety context but should normally rank below crop-production and supply records.

### 2. AFSIS disaster RSS — implement second

- Feed: [https://www.aptfsis.org/rssfeed](https://www.aptfsis.org/rssfeed)
- Official discovery page: [AFSIS Disaster Report](https://www.aptfsis.org/publication/disaster)
- Probe result: HTTP 200, `application/rss+xml`, 64 items with 64 `pubDate` elements, no credential. `robots.txt` returned `Disallow:` with no excluded path.
- Fit: ASEAN agricultural disaster and food-security context. The official page describes emergency information on agricultural damage; the feed is regional rather than Singapore/crop-specific.
- Scope caution: AFSIS's wider statistics focus on rice, maize, soybean, sugarcane and cassava. Do not label those records as evidence about FarmTact's leafy crops without an explicit geographic or supply-chain link.
- Reuse: RSS is explicitly offered via an official guide. Retain source attribution and links; ingest metadata/summary only pending a fuller content-reuse review.

### 3. ASEAN Agri-food news RSS — useful regional supplement

- Feed: [https://asean-agrifood.org/feed/](https://asean-agrifood.org/feed/)
- Listing: [https://asean-agrifood.org/news-and-event/](https://asean-agrifood.org/news-and-event/)
- Probe result: HTTP 200, `application/rss+xml`, five items with publication dates observed, no credential.
- Fit: regional projects, training, policy and agricultural events. Coverage can be broader than Singapore and broader than the ten crops.
- Governance caution: the site describes an ASEAN/GIZ agriculture and food programme, while it is not the ASEAN Secretariat's main portal. Display the publisher identity exactly and use the [ASEAN Food, Agriculture and Forestry portal](https://asean.org/our-communities/economic-community/enhanced-connectivity-and-sectoral-development/asean-food-agriculture-and-forestry/) for institutional policy documents.

These three connectors provide real dated records without a new API key. Start with RSS metadata only: title, canonical URL, source GUID, source publication time, retrieval time and the feed-provided description. Filter after ingestion; do not construct keyword-specific feed URLs or scrape search pages.

## Useful sources that need a more cautious adapter

| Source | Observed access | Current-news fit | Future-event fit | Recommendation |
|---|---|---|---|---|
| [MSE latest news](https://www.mse.gov.sg/latest-news/) | Search/browser retrieval exposed dated, categorised records; the direct command-line probe returned HTTP 403. `robots.txt` allowed `/` and disallowed `/search`. | Strong for Singapore sustainability, food policy, energy and trade context. | Some releases announce future programmes and missions. | Registry metadata now; do not work around the 403. Seek a documented feed/API or written reuse guidance before automation. |
| [NEA news index](https://www.nea.gov.sg/media/news/news/index) | HTTP 200 HTML; `robots.txt` allowed `/` and disallowed `/search`; no official RSS was found in this probe. | Useful for food waste, environmental regulation and resource context, usually indirect to crop decisions. | Announced campaigns and regulatory effective dates appear in releases. | Add only after a conservative low-rate HTML adapter and terms review; ingest link metadata rather than bodies. |
| [SFA From SG to SG events](https://www.sfa.gov.sg/fromSGtoSG/getinvolved) | HTTP 200 HTML. The page advertises farmers' markets, cooking classes and supermarket fairs, but the observed page text did not expose reliable event start/end fields. | Strong local-produce/community fit. | Strong if event dates can be extracted from stable structured data. | Use as a user-facing source link or metadata-only registry until dated structured records are available. Never turn an undated promotion into a current event. |
| [SAFEF activities](https://www.safef.org.sg/activities) | HTTP 200 Squarespace HTML; `/feed/` returned 404. | Direct industry/community fit, especially SG Farmers' Market. | Potentially strong, but the activity page observed here was largely retrospective and lacked a stable dated feed. | Registry/link-out first. Ask SAFEF for a calendar/feed or reuse permission before automated reuse. Social-network posts are not a substitute feed. |
| [Central Singapore Market](https://centralsingapore.cdc.gov.sg/central-singapore-market/) | HTTP 200 HTML from a Singapore CDC page. | Direct local farmer/producer/community context. | Good for officially dated market editions. | Candidate for a small events adapter after confirming stable date fields and reuse terms; no daily crawl is needed. |
| [FAO Asia-Pacific news](https://www.fao.org/asiapacific/news/en/) | HTTP 200 HTML; the FAO newsroom advertises RSS, but a regional RSS endpoint was not verified during this probe. | High-authority regional agrifood context but often too broad for a farm mission. | Media advisories can announce future conferences and programmes. | Registry/listing adapter later, or locate an explicitly documented regional RSS feed. Apply strict geography/topic scoring. |
| [Thailand MOAC agricultural-news RSS](https://www.moac.go.th/all_rss/news-type-382791791792-382791791792.xml) | HTTP 200 `application/xml`, no credential; response was about 3.6 MB in the probe. | Potentially useful for a major regional supply market. | Government notices may include future meetings/policies. | Gated pilot: cap bytes/items, support Thai text faithfully, and require Singapore/import relevance. Do not machine-translate silently. |
| [ASEAN main FAF portal](https://asean.org/our-communities/economic-community/enhanced-connectivity-and-sectoral-development/asean-food-agriculture-and-forestry/) | Redirected HTML listing with policy documents; no dedicated news feed found. | Authoritative institutional context, not a timely news stream. | Strong for published plans and future policy horizons. | Treat as a curated document registry, not a live-news connector. |
| [ARASFF](https://www.arasff.net/index.php) | Public landing page exposes some notification metadata, but the system describes exchanges for ASEAN competent authorities and includes login-only areas. | Relevant to regional food/feed safety. | Limited. | Metadata-only link. Do not enter protected areas or imply access to competent-authority notifications. |

## Reddit and community reaction

Relevant public discussions were observed in broad Singapore communities, including `r/singapore` and `r/askSingapore`, around local farms, fresh produce, retail availability and food security. These examples establish topical availability only. They do not establish representativeness, truth, buyer intent or permission to ingest.

Reddit is **not a no-key first connector**:

- The official [Data API documentation](https://www.reddit.com/dev/api/) documents listing/search mechanics.
- The current [Data API Terms](https://redditinc.com/policies/data-api-terms) require registration/access information and permitted API access (including OAuth), impose limits and attribution, limit retention/use, and state that user content remains owned by users.
- The current [User Agreement](https://redditinc.com/policies/user-agreement) prohibits scraping without prior written consent and limits automated collection to permitted means.
- Reddit's [robots/public-content notice](https://redditinc.com/news/robot-txt-update) says unknown bots may be rate-limited or blocked.
- The planning probe of an unauthenticated `r/singapore` search JSON URL returned HTTP 403. No bypass was attempted.

If approved access is later obtained, collect the minimum necessary metadata: post ID, subreddit, title or short permitted excerpt, canonical permalink, created time, retrieval time, score/comment-count snapshots, deletion status and source terms version. Do not store usernames for FarmTact's purpose, build user profiles, ingest private/deleted content, infer demographics, quote comments wholesale, or submit Reddit content to an LLM without a separately reviewed lawful basis and rightsholder permission. Provide deletion refresh and short retention. Label the result “community discussion”, never “market demand” or “consumer sentiment”.

Other social platforms (LinkedIn, Facebook, Instagram, Telegram) may contain timely SAFEF/farm announcements, but no official reusable API/feed was verified here. Link to the organisation's official page; do not scrape embeds or search results.

## Record and time model

Every record should carry:

| Field | Meaning |
|---|---|
| `source_id`, `source_name`, `publisher_kind` | Stable provenance and whether the publisher is government, intergovernmental, industry or community. |
| `canonical_url`, `external_id` | Public link and source GUID/ID; reject non-HTTPS links except documented legacy redirects. |
| `published_at_raw`, `published_at` | Exact source value plus parsed UTC instant and timezone assumption. Invalid/ambiguous values stay null with a quality issue. |
| `event_start_at`, `event_end_at` | Separately extracted announced event interval. Never substitute publication time. |
| `retrieved_at`, `content_hash` | Point-in-time replay and deduplication. |
| `geographies`, `crop_ids`, `topics` | Deterministic, reviewable tags. Unresolved crop aliases remain unmatched. |
| `summary`, `summary_kind` | Feed-provided description or clearly marked deterministic excerpt; no invented digest. |
| `reuse_mode`, `terms_url`, `robots_checked_at` | `rss_metadata`, `link_only`, `approved_api`, or `blocked`. |
| `quality_issues` | Missing timezone, impossible date, missing event date, stale item, language support, or uncertain crop match. |

Classify temporal fit from explicit fields:

- **Current release:** publication is within the configured freshness window; the record may describe past, present or future events.
- **Announced future event:** `event_start_at` is after the mission cutoff, even if the release itself is old.
- **Ongoing event:** cutoff falls within explicit start/end bounds.
- **Historical context:** old publication without an active/future interval.

Do not call something “today's news” merely because it was retrieved today. Display “published”, “event”, and “retrieved” times independently, with timezone and freshness.

## Relevance and safety gate

1. Fetch only allowlisted URLs at a scheduled, source-appropriate cadence with byte, item, redirect and timeout limits.
2. Parse RSS/structured metadata first. Deduplicate by source ID then canonical URL/content hash.
3. Apply deterministic geography/topic/crop aliases. A title match creates a candidate tag, not evidence of operational impact.
4. Retain the source description only when the feed explicitly syndicates it; otherwise retain title/link/time metadata.
5. Freeze the bounded top records at the mission cutoff. Never include a record published or retrieved after that cutoff in a replayed mission.
6. Show empty, stale, blocked and malformed-source states. Never backfill a failed live connector with fictional stories.
7. Keep news evidence visually separate from farm inputs, forecasts, public observations and community discussion.

## V5 recommendation

Implement SFA Newsroom RSS and AFSIS disaster RSS as the first production connectors, with the ASEAN Agri-food RSS as a lower-priority regional stream. These provide enough real, attributable records to demonstrate current releases and regional risk context without new keys. Add SFA circulars/alerts through the same adapter once topic ranking is tested.

Keep MSE, NEA, SFA events, SAFEF, Central Singapore CDC, FAO, Thailand MOAC and ASEAN documents as visible source-registry candidates with their actual access state. Gate Reddit entirely until approved OAuth access, terms review, privacy/retention design and deletion handling are complete.

