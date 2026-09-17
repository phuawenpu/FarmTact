Current release, 17 September 2026: V15 is published from source
`a5ab2a8bf86b0a40968eb1b3b6f97dbd34c46f63` and immutable image
`registry.fly.io/farmtact@sha256:7f19f29f1465ca9f678f29e0336a4bbcccd5d2ba03826d8184f52cff693c39b4`.
The public `/` and `/play` routes serve the same V15 integrated card shell for the
one ordinary synthetic farm. Plan, Records & work, Knowledge & evidence,
Experiments, and History & preferences are available through that shell. Public
edition selection and the V14 four-bed teaching season are historical rather than
the current interface. Read `reports/v15/implementation.md` and
`docs/v15-capability-checklist.md` before making current-state claims.

V15 preserves explicit review, revision-bound mutations, read-only replay and the
existing provider/admission boundaries. It does not establish human usability,
new provider quality, calibrated agronomy or real-farm performance. Actual farm
operations remain disabled. Preserve all historical release records. The next
unused publication number is **V16**; never overwrite V15's source/image or reuse
its number.

Fresh-workspace restart: read [docs/workspace-handoff.md](docs/workspace-handoff.md).

Current V11 handoff (11 September 2026): latest published edition is V11 from
source `37802adbc9010bc80a50869ef725285a119af3f3`, image
`sha256:e82ba02912d7a716ec4a4588a6fc83721cb361549d9fbbefc92eae1ce439cf7d`.
Read `reports/v11/implementation.md` and the V11 technical chapter first. Guided
production planning and newest-first chooser are published. V1–V10 remain pinned.
The historical handoff below is retained as evidence of earlier states.

# Master implementation brief

Follow CODEX_START_PROMPT.md, build spec v1.2 Section 0, and DeepSeek runtime v1.2. Published v1–v9 remain immutable; v10 is published from source `ec4e29874b2c7408f2bd93d012912e3c0cb8d2f3` with image `registry.fly.io/farmtact@sha256:874530e73f481b1197e528bb5f124b958a74be64c9934292c14438b4cdd503bf`. Read `docs/technical/v10-grounding-followup.md`, `docs/technical/v9-ai-followup.md`, `reports/v10/` and `reports/v9/` before making current-state claims. This brief is reconstructed from the supplied specifications because no original master prompt was present.

Own shared schemas, migration/version decisions, environment dependencies, integration, scope and independent acceptance. Use A01–A12 ownership in build Section 11 and docs/execution-plan.md. Preserve scientific uncertainty and actual source status. Build numerical results before council/UI claims. All actual application inference uses DeepSeek. Automatically advance passing development checks, accept eligible simulation plans through backend policy, and preserve existing work during replanning. No human sign-off is required in this phase. Record authoritative evidence and incomplete items in reports; never treat fixtures as actual inference or actual farm performance.

The current planner is `daily-bed-cpsat-v3`: preserve absolute crop-cycle identity,
collision-checked harvest lots, the world-level lot-origin map, historical executed-ID
exclusion and maximum-declared-yield resource reservations. V10 uses conversation
prompt/context V6, mission prompt/context V7, validator V5 and schema V3 with exact short alias
resolution. Both paths are bounded and must abstain when admitted context cannot
answer. Tenant retention is an explicit,
dry-run-by-default operator CLI with a 30-day default, seven-day minimum, 500-tenant
cap and active-job exclusions; there is no automatic deletion. V8 publication and
its 589-test regression passed, but its public quality trial failed: 6 of 10
completed quality cases passed, invited return and conversational Council were
incomplete, and its final ledger records 55 actual requests. V9's frozen offline
suite passed 606 tests with one skip, its mobile typed-fact check passed 21 of 21
assertions, all nine edition health/source checks passed, and v1-v8 preservation
passed. Its authenticated public UI replay passed 38 of 38 mobile/desktop checks
without forwarding mutation or inference requests. V9 then used 21 actual requests
(nine mission, eleven conversation and one
research), bringing the cumulative ledger to 76. Its automated quality result is
FAIL: 12 of 18 cases passed while workflow integrity passed. Two Council abstentions
persisted unsupported, and the scorer missed a false full-fulfilment claim for an
824 kg booked request against 370/446/518 kg strategy deliveries. The completed
AI-assisted review classified 10 messages as sound, 5 as sound with limits and 3
as materially contradictory: Planning Supply and two Production replies. V10 is
the published remediation edition. Its Council-only live quality result is FAIL
(5 of 7 cases passed), and its fresh mission was budget-withheld before inference.
V9's public capacity check passed two numerical jobs and 58 browse samples with
zero provider calls. Its 56-day synthetic execution run passed mass, cash and
lot-receipt checks with 60 task events, 64 demand-service events, one future replan
and zero provider calls; it did not exercise an actual application restart.

## V9 AI follow-up — published 11 September 2026

The public V8 quality trial failed despite mission transport/reference success:
6 of 10 completed quality cases passed, and the invited return and conversational
Council were incomplete. See `reports/v8/public-ai-postmortem.md`. V9 uses mission
prompt/context V6, conversation prompt/context V5 and
validator V4. It preserves semantic names alongside exact aliases, passes the
actual required/advisory policy, bounds role-specific facts, balances comparison
segments, requires typed numerical evidence and enforces absent-source abstention
for Council source specialists. Direct/invited numerical questions remain
answerable from their frozen facts. Conversation prose targets 220 characters
under the unchanged 400-character hard limit. The immutable publication, all nine
edition health/source checks and v1-v8 preservation passed. The frozen offline
suite passed 606 tests with one skip, and the mobile typed-fact check passed 21 of
21 assertions. V9 used 21 actual requests and its automated quality result is FAIL:
12 of 18 cases passed while workflow integrity passed. Two Council abstentions
persisted unsupported. The completed AI-assisted review of 18 messages and 62
atomic assertions found 10 sound, 5 sound with limits and 3 materially
contradictory: Planning Supply and two Production replies.

## V10 grounding-remediation edition — published 11 September 2026

V10 advances mission prompt/context to V7, conversation prompt/context to V6 and
validator to V5 while retaining schema V3. Code derives Supply's booked-fulfilment
status and applies a bounded phrase guard without semantic repair. Required-absence
conversation context strips numerical and prior-conversation prose and supplies
explicit empty arrays with `typed_required=false`. The absence-only projection
applies only to Weather/Market in conversational Council mode when their source is
absent; numerical direct/invite and research retain their existing projections. See
`docs/technical/v10-grounding-followup.md`. V10 is published from source
`ec4e29874b2c7408f2bd93d012912e3c0cb8d2f3` with image
`registry.fly.io/farmtact@sha256:874530e73f481b1197e528bb5f124b958a74be64c9934292c14438b4cdd503bf`.
All ten health/source checks and v1-v9 preservation passed. The Council-only live
trial used nine requests for seven messages and passed 5 of 7 targeted cases.
Weather/Market absence handling passed; Supply was withheld for model-authored
`zero`, and Chair missed a topic word. A fresh mission was correctly withheld before
inference: 41 public requests were used and seven remained, below the nine-request
reservation. Its three numerical strategies were retained. No new direct, invite,
research or vision result is claimed. The cumulative ledger is 85 (44 local and 41
public). The V10 full suite passed 611 tests with one
skip in 441.23 seconds. The narrow fix does not establish general prose or crop-mix
entailment; AI quality remains a partial requirement. V8 and V9 stay unchanged.


Final V10 semantic evidence: `reports/v10/ai-assisted-semantic-review.md` audits
seven messages and 26 assertions: two sound, four sound with limits, one
contradiction. Profit incorrectly labels Lean's −SGD 52.87 margin delta as a gain.
This AI-assisted review is not human expert validation. V10 quality remains failed
and its fresh mission-provider path was budget-blocked; publication and numerical
regression do not close this semantic acceptance requirement. The public 56-day
execution passed mass/cash/order-lot reconciliation and historical receipt replay
with zero provider calls (`reports/v10/execution-public.json`).
