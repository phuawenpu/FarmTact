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

Independent review repaired redirect-policy bypass, null/malformed cache states,
parent-mission context inheritance, and missing observation/ongoing-event fields.
The collector explicitly requests uncompressed feeds and rejects compressed
responses. An additional source-date test exposed ignored AM/PM markers; the
parser now handles SFA's exact format before generic email dates. Revalidation of
the existing development cache corrected 69 timestamps/hashes from preserved raw
publication strings without inventing a new retrieval time. All 346 records remain
valid. No production records were changed.

Verification: 37 focused News/review/Fly-boot checks pass, including the separate
collector's stripped credential environment. A wider backend regression passed
113 checks before the final date-parser additions; the 37-check run covers those
changed paths. The initial News browser run passed 22 checks; a final failed-filter/retry disclosure
check is being added. A real local explicit Market advisor request completed in one
DeepSeek call, cited the frozen title and context hash, and replayed without
inference (reports/v5/advisor_local.json). These remain local candidate results;
publication and deployed verification are pending.
