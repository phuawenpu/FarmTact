# Master implementation brief

Follow CODEX_START_PROMPT.md, build spec v1.2 Section 0, and DeepSeek runtime v1.2. Published v1–v8 remain immutable; v9 is published from source `89d29cc3e071e12373204ff234d0a261ce71b5a1` with image `registry.fly.io/farmtact@sha256:42702ca38566d87c359ae2f92f924b403dbf8fb2ae8166f5377cc829e8d725e4`. Read `docs/technical/v9-ai-followup.md`, `docs/technical/v8-remediation-report.md`, `reports/v9/` and `reports/v8/` before making current-state claims. This brief is reconstructed from the supplied specifications because no original master prompt was present.

Own shared schemas, migration/version decisions, environment dependencies, integration, scope and independent acceptance. Use A01–A12 ownership in build Section 11 and docs/execution-plan.md. Preserve scientific uncertainty and actual source status. Build numerical results before council/UI claims. All actual application inference uses DeepSeek. Automatically advance passing development checks, accept eligible simulation plans through backend policy, and preserve existing work during replanning. No human sign-off is required in this phase. Record authoritative evidence and incomplete items in reports; never treat fixtures as actual inference or actual farm performance.

The current planner is `daily-bed-cpsat-v3`: preserve absolute crop-cycle identity,
collision-checked harvest lots, the world-level lot-origin map, historical executed-ID
exclusion and maximum-declared-yield resource reservations. V9 uses conversation
prompt/context V5, mission prompt/context V6 and validator V4 with exact short alias
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
824 kg booked request against 370/446/518 kg scenario deliveries. The completed
AI-assisted review classified 10 messages as sound, 5 as sound with limits and 3
as materially contradictory: Planning Supply and two Production replies. V10 is
the unpublished remediation candidate.
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

## V10 grounding-remediation candidate — unpublished

V10 advances mission prompt/context to V7, conversation prompt/context to V6 and
validator to V5 while retaining schema V3. Code derives Supply's booked-fulfilment
status and applies a bounded phrase guard without semantic repair. Required-absence
conversation context strips numerical and prior-conversation prose and supplies
explicit empty arrays with `typed_required=false`. The absence-only projection
applies only to Weather/Market in conversational Council mode when their source is
absent; numerical direct/invite and research retain their existing projections. See
`docs/technical/v10-grounding-followup.md`. Candidate checks do not establish a
frozen release or published edition. The V10 full suite passed 611 tests with one
skip in 441.23 seconds. The narrow fix does not establish general prose or crop-mix
entailment; AI quality remains a partial requirement. V8 and V9 stay unchanged.
