# V5 engagement release acceptance

Status: implemented, independently reviewed, published and verified as immutable v5.

The release follows Sumin Lee's business proposal and the original briefing's
page-13 rubric. Its playable loop starts from a dated delivery gap, exposes the
actual input records, freezes one changed assumption, calculates Lean/Balanced/
Resilient, and shows the same-policy numerical consequences before a deliberate
paid advisor action. Seven deterministic perspective cards explain evidence;
they are explicitly not autonomous council messages. The actual council remains
Demand, Weather, Market, Production, Supply Chain, Profit and Planner.

## Implemented behavior

- A provisional gap groups actual net booked orders by crop/date. It checks
  harvest shelf life and inventory expiry; weekly EWMA remains separate context.
  The planner handles allocation across earlier deliveries and authoritative
  shortfall. Maturity includes nursery plus grow days, excluding sanitation.
- Main-farm, saved playground and scenario evidence retain their owned snapshots
  and comparison roots. Reload recovers an eligible saved result. Incompatible
  roots cannot share a displayed baseline, including before a comparison request.
  Changing a snapshot hides old interactive data while the new snapshot loads.
- Exact numeric controls accompany sliders. Waiting is calculation time, never
  simulated crop growth. Expandable records and constraints retain units and
  readable evidence. Infeasible results remain inspectable and earn learning
  badges; advisor actions stay explicit.
- Eighteen original SVGs distinguish ten crops and four growth sequences, using
  research on leaf, stem and growth forms. Independent small-size/color/grayscale
  review prompted revisions to mustard, kale and pak choi.
- Optional sound starts silent, with separate channels, an immediate test when
  effects are enabled, retry and 44px controls. Nine deterministic PCM assets have
  a stronger mix and no clipping. The 64-second loop has a zero-sample boundary
  and 0.16 dB first/last 100 ms RMS difference. Result cues distinguish shortfall,
  withheld acceptance and failure; polling and replay do not create extra cues.
- The News scout supports the seven roles without adding an eighth council call.
  Four allowlisted RSS feeds yielded 346 real public metadata records locally and in the deployed edition.
  Collection is bounded and separate from credential-bearing processes; browsing
  reads only cached data. Publication, retrieval, observation and explicit event
  dates remain distinct from the synthetic farm clock. Decisions freeze the exact
  News context; continuation, advisor interpretation and replay reuse it.

No structured future-event dates were present in these feeds. Reddit has no
approved connected API; the CDC calendar's reuse terms exclude automated reuse.
Both absences are visible. No social reaction or news headline automatically
changes demand, price or yield. Physical-device listening and human crop-recognition
studies were not performed; AI, signal and browser evidence is labelled accordingly.

## Verification evidence

- Full backend run: **443 passed**, zero failures, two existing dependency
  deprecation warnings (243.77 seconds). The earlier stale two-edition fixture was
  isolated before this final run. Generated contracts pass.
- PostgreSQL test confirms saved snapshot/restart persistence, interrupted numerical
  continuation, unchanged main farm, and frozen News inheritance without refreshing.
- Game journey: 30 checks at 360/390/430/1280; snapshot race 3; decision semantics 6;
  sound semantics 8. The same-hash/different-root edge is covered; farm mission
  association requires an explicit matching farm root.
- Broad explorer regression: 73 checks, five real numerical jobs, linked graph/table
  selection, controls, preview/freeze agreement, exports, continuation and mobile
  widths. One continuation produced a real inspectable NO_FEASIBLE_PLAN.
- Explicitly mocked infeasible UI: 60 checks, including readable constraint facts,
  touch targets, no overflow and preserved real bootstrap state.
- News browser: 24 checks, including all filters, unavailable future records,
  delayed obsolete responses, failed-filter disclosure and retry, keyboard and
  four responsive widths. No provider submissions.
- Isolated real import: 12 checks change a dated booking 28→37 kg through Setup,
  hide stale mission actions during delayed rematching, verify the new owned
  snapshot, and preserve it on reload. No numerical or provider request.
- Audio browser 22 and PCM 4 checks; source/asset/independent measurements recorded.
- One real local explicit Market advisor request completed using
  `deepseek-v4-flash`, cited the frozen title and context hash, and replayed with
  zero additional calls. It used one request within a two-request repair ceiling.
  This is reference-membership evidence, not validated agronomic interpretation.
- TypeScript/Vite and generated-contract checks pass. Final frontend assets are index-fxjcA9To.js and index-DlATHyWR.css.
  All candidate acceptance checks passed before source freeze.

The transient local 500 investigation traced failures to GET /v5 while an in-place
Vite build temporarily removed dist/index.html. No numerical API handler failed.
Builds and browser checks are serialized for final acceptance; deployed images
contain the complete frontend and do not run Vite builds at runtime.

## Hosting and preservation

The Fly cost assessment retains separate edition Machines. Equivalent capacity
has essentially no packing discount; cheaper shared sizes reduce CPU/memory and
have not passed concurrent-workload/isolation migration tests. No topology change
was made. The read-only post-publication comparison confirms that v1-v4 manifests and owned
farm/run/scenario/conversation records are unchanged. V5 has its own database,
Machine and encrypted volume. It pins source 0f54565d23f5387fc751eeac4f329372e0460018
and image sha256:65164c323cb733f02434730cd31c2a32d5b478150f7041f12034ef65d539c103.

See the package reports in this directory, the
[rubric mapping](../../docs/v5-engagement-plan.md), and the
[hosting assessment](../../docs/deployment/consolidation-assessment.md).

## Deployed verification

Published at https://farmtact.fly.dev/v5/; manifest commit 255f1b1.
The deployed API smoke passes 17 checks: exact source, edition-cookie isolation,
200 retained public numerical observations, 346 collected News metadata records,
a real saved-dataset numerical run at alpha 0.7, continuation/root preservation,
unchanged main farm, one explicit DeepSeek advisor request citing the exact frozen
News title/context, and replay with no extra inference. Local and deployed actual
advisor checks used one request each; browsing/numerical browser checks use none.

Sprite HTTP registrations were removed and ports 8080/8085 are closed. PostgreSQL
and the existing keepalive remain. Deployed browser verification passes the complete game journey (30 checks),
explorer (73 checks, five completed numerical jobs), audio (22 checks), News (24
checks) and release chooser (6 checks). The deployed snapshot race passes 3 checks and isolated decision semantics passes 6.
All these browser journeys made zero provider calls and recorded no page errors.

Parallel deployed test traffic exposed slower responses and two 30-second
navigation/network-idle timeouts before those suites reached assertions. The
complete explorer still finished all five jobs in about 6.5 minutes. During that
load a read-only probe returned HTTP 200 for registry, health, HTML and News, with
News taking 8.564 seconds. Recent Fly status/log inspection showed a healthy
Machine and no restart, OOM or application exception. News subsequently passed the same 24 assertions in an isolated live harness
using DOM readiness, 60-second action bounds, a 3-second stale-response fixture
window and awaited route cleanup. This is not a claim that the original
30-second network-idle harness passed. The final semantic check passed 6/6 in
3.85 seconds. A subsequent sequential read-only probe returned registry/health/
HTML/News in 0.027/0.023/0.070/0.187 seconds, all HTTP 200. These observations establish eventual
functional correctness, not a concurrent latency target or a proved cause.
Retained parallel-attempt evidence must not be hidden by the later passing run.
See live_http_timing.json, live_http_timing_isolated.json,
news_live_parallel_attempt.json and game_live_addendum.md.
The capacity limitations reinforce the hosting decision; no smaller shared-host
performance claim or migration is made.
