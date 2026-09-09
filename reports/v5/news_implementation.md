# V5 News implementation milestone

2026-09-09 UTC; not yet published.

Four RSS feeds collected 346 valid metadata records: SFA Newsroom 154, SFA
Circulars 123, AFSIS 64 and ASEAN Agri-food 5. The source's year 0001 placeholder
was rejected after a test exposed Python email-date parsing coercing it to 2001.
Publication years must now be explicit and valid; the stored date must agree
with the raw source date. No full linked article, image or social profile is fetched.

The API is tenant-authenticated and local-only. It supports bounded crop/region/time
filters and owned frozen scenario/run evidence. A six-hour separate collector
receives no credentials. Each frozen decision carries copied records and a context
hash; scenario conversations/continuation reuse the same context. News timestamps
and synthetic farm calendar dates remain explicitly separate; historical replay
excludes later publication and retrieval. Future-event dates are accepted only
from explicit structured fields; current collected feeds supplied none. CDC's
calendar has future dates but reuse terms block collection, and Reddit access is
unavailable. These absences remain visible rather than fabricated.

Verification at this milestone: 19 focused News tests pass (two existing dependency
deprecation warnings), including XML/byte/URL bounds, date semantics, hash
integrity, cache failure preservation, idempotency, freeze/citation reuse, no
external requests and tenant isolation. Boot regression previously passed 10 tests
alongside the first News test pass; the new scheduled path needs its own focused
review. Real local health/bootstrap and News returned successfully. Independent
review, browser filters/stale responses and release acceptance remain in progress.
