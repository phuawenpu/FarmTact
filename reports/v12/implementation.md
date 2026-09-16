# V12 farmer workflow and two-edition retention

V12 is published at https://farmtact.fly.dev/v12/ from immutable source
`9fd57898b8a4e3b69a40c3abf03895f0fcb05daf` and image
`registry.fly.io/farmtact@sha256:d41111021de2b40df9bad75f1ee3c8ccaa910ee5e84584f8887dbefcf40fea56`.
The publication manifest commit is `26dde74`; tag `farmtact-v12` pins the source.
Public history contains V1–V12, while active previous/latest are V11/V12 only.
Post-publication cleanup/preservation evidence is being finalized.
V11 is preserved at source `37802adbc9010bc80a50869ef725285a119af3f3` with its frozen
image and independent database. V1–V10 running applications and exact storage
subtrees have been retired after a completed recovery snapshot. Immutable release
history, Git commits/tags and manifests remain.

## Delivered workflow

Singapore Demo Farm connects observe → discuss → decide → approve → act → verify
→ replan. Synthetic examples are the default. CSV/XLSX and standardized accounting
records pass through FinancialDataConnector; manual records and document extraction
enter a tenant-scoped Inbox. Source bytes/hash, extracted fields and warnings remain
reviewable. Explicit confirmation is required before a candidate can support a
planning proposal. Photo observations have separate observation-only authority and
cannot independently change yield or authorize farm actions.

Seven functional Council roles expose their contracts, evidence and tool status.
Missing Weather/Market sources produce partial findings. Read-only specialist
questions freeze the numerical result. Changes require an explicit reviewed
proposal, Apply & Recalculate, and Approve & Create Actions. Approvals bind the
completed result and revision; idempotency prevents duplicate tasks. Tasks retain
crop/batch, location, due date, checklist, quantity/unit, optional photo and status.
User reports and corrections append events, update forecast feedback and preserve
completed work during recovery planning. No physical operation is enabled.

Confirmed-order coverage, unallocated surplus, expiry/rejection exposure and
contribution margin come from local calculations. Tentative demand and market
prices do not become booked commitments. Waste Rescue presents dated, hypothetical
scenario comparisons. Four numerical crop recipes are supported; unsupported crop
inputs are explicitly flagged. Outcomes distinguish projected, simulated and
farmer-reported evidence.

Three 48-second captioned H.264 guides have in-app controls, exact transcripts,
static alternatives and downloadable MP4s. Responsive and keyboard checks cover
360/390/430-pixel and desktop views. The visual farm board remains central.

## Provider evidence and limits

All actual inference used the existing DeepSeek gateway under the unchanged shared
48-call daily limit. The recorded total after bounded V12 trials is 32 requests,
including failed/repair attempts; replay and capacity probes added none. Five actual
Council numerical roles validated; two external-source roles were truthfully partial.
An initial specialist reply confused broader forecast shortfall with confirmed
orders. Conversation prompt/context V7 now supplies explicit booked metrics and
names broader metrics all_demand, with validator V6 withholding mismatched claims.
The corrected live reply cited booked shortfalls of 306/378/454 kg and explained
that modeled residual demand was excluded.

A synthetic invoice image and native-text PDF returned authored date, reference,
quantity/unit and SGD amount accurately. The provider omitted request-id headers;
audits retain actual model, input hash, token usage and latency without invented IDs.
A synthetic labeled graphic was correctly described as synthetic and did not produce
crop/yield claims. This is bounded extraction/abstention evidence, not real-field
agronomic vision validation. Original failed helper and quality reports remain.
The extracted null crop normalization defect is fixed and the later PDF returned
crop_id null correctly. Human expert and commercial-farm validation remain outside
these software acceptance results.

## Retention and resource evidence

The active manifest controls chooser, switchers, routing and inference admission.
Retired GET and mutation routes return 410 Gone, with available-edition links.
Historical numbering never resets. Candidate failure leaves the public pair intact;
successful publication atomically advances the pair. Cleanup is restartable,
snapshot-backed, and excludes active/staged editions and shared gateway controls.

Retirement reclaimed 694,558,720 bytes (about 662.38 MiB). Sampled active VM memory
fell from roughly 982 MB to 247 MB and available memory rose from 1.96 GB to 3.33 GB;
one-minute load averaged 6.419 before versus 0.575 after in the recorded windows.
These are VM gauges, not per-process RSS or a controlled causal benchmark. Baseline
host process/RSS readings were unavailable. Fly-managed image layers were not pruned
without verified ownership. The 4-shared-CPU/4096-MB Machine and 3-GB volume remain;
freeing resources does not by itself establish a lower hosting bill.

## Verification

The final backend suite passed 728 tests with one skip in 695.90 seconds. Its
Python tree matches the final application; only host-side publication command
compatibility changed during/after the run and passed its focused release suite
(56 tests after the final CLI correction). The skip is the existing absent generated
News-cache fixture; three library warnings remain. See regression-final-scope.json.
The final browser suites passed 25 mocked and 30 real-backend assertions, and the
published navigation check passed 28 assertions at all four widths with no errors
or inference requests. The public edition verifier passed 18 checks.
Three paired numerical capacity trials passed the unchanged 180-second completion
and 5-second browse-p95 gates, completing in 12–13 seconds with browse p95 below
0.18 seconds on the final image. This combines two private/private uncached pairs
and one authenticated private-V12/public-V11 uncached pair, proven by persisted
worker timings. Original session-rate-limit failures remain recorded; no limit was
reset or relaxed. Two later cached pairs are excluded from the capacity claim.
These are bounded shared-host trials, not a general concurrency SLA.
The live state-changing discussion proposed labour at 80%; its reviewed draft
remained non-mutating, and explicit Apply recalculated 32 hours to 25.6 hours while
preserving orders, yield assumptions and the main farm. Its prose also proposed an
unsupported causal margin explanation. That limitation is retained explicitly;
backend and UI label interpretation unverified and show checked facts separately.

Final records separately capture browser review, Inbox/manual confirmation,
restart/replay without inference, source/image identity and preserved V11 hashes.

Live accounting integrations, public webhooks, buyer outreach, full ERP and real
operational automation remain deferred.

## Publication recovery

Atomic publication succeeded before host-side cleanup encountered unsupported
`fly machine status --json`. No deletion was attempted by that failed query. The
release tool now uses supported `fly machine list --json`, selects exactly one
configured Machine and retains all active/staged/runtime exclusions. Cleanup is
resumed without republishing or changing V12's source/image. The original failure
and subsequent result are separate evidence.
