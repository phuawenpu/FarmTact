# V5 News scout independent review

Reviewed 2026-09-09 against `packages/news.py`, `services/api/news.py`,
`scripts/refresh_news.py`, `scripts/fly_boot.py`, mission/scenario/conversation
freezing and evidence references, and the primary News tests. This was a static
and offline-fixture review: it made no feed, article, provider, or inference
requests.

## Verdict

The News scout is correctly separated from the seven-role decision council. It
collects public headline metadata into a bounded cache and gives it no numerical
effect. The council can cite frozen fields, but the headline text is expressly
treated as untrusted context. The public API authenticates the tenant and uses
owned scenario/run lookups, so one tenant cannot request another tenant's frozen
News evidence.

Four correctness gaps and one defence-in-depth gap were found. All five were
corrected during review and the regression suite in
`tests/seven_agents/test_news_review.py` now captures the required behavior.

| Priority | Finding | Consequence | Required correction |
|---|---|---|---|
| High | Mission continuations created with `parent_run_id` freeze the current cache again. Scenario continuations correctly copy their parent/conversation context. | A replan can cite stories that were unavailable to its parent, breaking replay and evidence-chain consistency. | For an owned parent, deep-copy its frozen `news_context`. If an older parent has no field, preserve that absence rather than substituting current stories. |
| Medium | Explicit event timestamps accept year 0001. Publication timestamps have a 2000 lower bound, while event timestamps only receive timezone and interval validation. | Sentinel dates can be presented as real event evidence. | Require event start/end years to be at least 2000, while retaining the explicit-source-basis and ordered-interval checks. |
| Medium | Records can be classified `ongoing`, but `period="ongoing"` is rejected by the package and API enum. | The UI/API cannot directly retrieve a state the model exposes. | Add `ongoing` to the package filter and API literal (and corresponding UI control). |
| Medium | `load_cache` validates record models but trusts the outer source-state objects and their timestamps. `context` and `refresh` later parse those values outside a safe normalization boundary. | A malformed persisted cache can turn a recoverable cache problem into a browse or refresh exception. | Validate exact known source IDs, bounded status/count/error fields, and aware years >=2000 for refreshed/attempt/success times. Reject duplicate/unknown/missing states or rebuild an empty cache with `cache_invalid`. |
| Low | `refresh` relies on an injected client's redirect policy. The production-owned client sets `follow_redirects=False`, but an injected client configured to follow redirects leaves the allowlisted source host. | Tests or a future caller can weaken the collector's host boundary accidentally. | Pass `follow_redirects=False` on each streamed request, or reject any redirect response before following regardless of client defaults. |

## Controls that held

- Collection starts only from four declared HTTPS URLs and validates record links
  against each exact source host. Ports, credentials, control characters, and
  non-HTTPS links are rejected.
- The production collector disables environment proxy inheritance and redirects,
  uses explicit connect/read/write/pool timeouts, streams at most 1 MiB, parses at
  most 200 items per source, and persists at most 500 records.
- `DOCTYPE`, entity declarations, NUL bytes, unexpected media types, invalid UTF-8,
  missing/undated publications, and publication-after-retrieval records are
  rejected. Failed refreshes preserve the prior valid records for that source.
- Publication times require an explicit four-digit year at or after 2000. Naive
  SFA dates use the declared Asia/Singapore assumption and carry a quality flag;
  naive timestamps from sources without a declared timezone are rejected.
- Point-in-time selection requires both `published_at <= cutoff` and
  `retrieved_at <= cutoff`. Source attempt state later than the cutoff is hidden.
  Historical-replay farms use the farm cutoff; current farms use decision time.
- Record identity derives from source plus external ID. The content hash covers
  stable metadata and intentionally excludes retrieval time. Frozen context has
  its own hash and is separate from the farm input hash.
- Scenario branches reuse parent or source-conversation News context. Conversations
  freeze the scenario context, or freeze once on creation, and expose only
  allowlisted evidence references. Headline/title fields cannot become tool
  instructions, and ordinary browsing/numerical setup invokes no provider.
- The generated cache contains 346 records from four RSS sources at review time.
  Records contain headline metadata rather than article bodies, comments, or user
  profiles. Reddit remains `not_connected`; CDC remains blocked by reuse terms;
  SAFEF remains link-only/uncollected.

## Future-event honesty

The parser supports explicit schema.org `startDate` and `endDate` elements and
keeps event time distinct from publication time. A year mentioned only in a
headline does not create a future event. The local regression fixture exercises
future and ongoing classification.

The generated cache had **zero records with structured event dates** at review
time. Therefore the implementation capability is real, but the present public
feeds do not yet supply an observed announced-future-event record. The product
must show an empty future-event state rather than imply that headlines are a
calendar or forecast.

## Regression coverage

`tests/seven_agents/test_news_review.py` adds offline checks for:

1. year-0001 event rejection and direct ongoing filtering;
2. invalid persisted source timestamp rejection at `load_cache`;
3. redirect refusal even with a permissive injected HTTP client;
4. publication/retrieval and source-state cutoff behavior;
5. mission parent/child frozen-context equality;
6. metadata-only fields, zero numerical effect, non-council status, and the
   explicit Reddit/CDC restrictions in the real normalized cache.

Before correction, the combined News run exposed failures in event-year bounds,
source-state validation, per-request redirect policy, and mission continuation.
The added optional observation timestamp also initially invalidated existing
record hashes; compatibility was restored by omitting an absent observation from
the semantic hash while hashing one when it is present. `instant(None)` now fails
as a handled validation error. The existing generated cache then validated all
346 real metadata records without a network refresh.

Final verification:

```text
.venv/bin/pytest -q tests/seven_agents/test_news.py tests/seven_agents/test_news_review.py
```

Result: **25 passed** in 2.54 seconds. The two emitted messages were dependency
deprecation warnings from FastAPI/Starlette test infrastructure, not News test
failures. `git diff --check` passed for this report and the independent test file.
