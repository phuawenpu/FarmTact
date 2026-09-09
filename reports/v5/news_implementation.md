# V5 News implementation milestone

2026-09-09 UTC; published as immutable v5 at https://farmtact.fly.dev/v5/.

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
valid. This correction preceded publication; older editions were not modified.

Verification: 37 focused News/review/Fly-boot checks passed, including the separate
collector's stripped credential environment; the final complete backend suite
passed 443 tests. Candidate News browser verification passed 24 checks, including
failed-filter disclosure and retry. The Fly collector independently ingested the
same 346 records. Both the local and deployed explicit Market advisor checks used
one actual DeepSeek request each, cited the frozen title and context hash, and
replayed without additional inference (advisor_local.json and live_api.json).
Deployed browser outcomes and transport timing are recorded separately; see the
final implementation report for the complete release acceptance evidence.
