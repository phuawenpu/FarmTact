# FarmTact interactive farming world

Release status: **COMPLETE**. The interactive world is deployed at https://farmtact.fly.dev. Automated gameplay, live DeepSeek, final transcript replay, deployment persistence, and development-server shutdown checks passed. Results below describe executed checks, not intended checks.

## Implemented experience

The homepage is an isometric SVG farm with sixteen real selectable beds, eight facilities and six original adult advisors. Pan, zoom, recenter, a schedule-date preview, an accessible farm table, mobile bottom sheets and desktop side panels preserve access to all planning tools. All ten crop identities have original art; the four simulated crops each have seedling, growing and harvest-ready stages. The [art provenance record](../docs/crop-art-provenance.md) records NParks references, visual traits and reuse treatment. No source photographs are distributed.

Typed discussions retain their frozen farm or scenario snapshot. Advisor replies show referenced backend quantities with their own labels and units, evidence findings and applicability limits, linked reply excerpts, stated agreements/disagreements, supported experiment controls, and plot references. An expandable recorded transcript and six-speaker council presentation identify the critic's conclusion only when the final critic actually returns a conclusion. Invitations respond to the selected point's author, including points from earlier invitations or council turns. Saved discussions, partial/interrupted states, replay and SSE reconnection preserve messages without repeating inference.

Late harvest, Busy market, Short-handed week and Tight budget each offer a briefing, bounded assumptions, a local numerical experiment, a same-policy before/after comparison, a computed debrief, and persisted discovery/inspection badges. Sandbox is available without a quest. Infeasible outcomes remain valid learning results. Baseline plus three branches can be compared under Lean, Balanced or Resilient; continued branches apply controls relative to the parent while retaining their original root baseline.

## Invariants and explanation boundaries

- Additive tenant-owned conversation, message, request/event, scenario and quest tables preserve the existing database schema and planning records.
- Branch jobs freeze inputs and never replace the main farm, its latest planning run, acceptance or worklist.
- Numerical runs use the existing local four-crop planner and make no inference requests.
- DeepSeek uses the existing allowlisted gateway and unchanged global daily limits. Direct exchanges permit at most four advisor turns plus one repair; councils permit eight turns plus two repairs.
- Opening/replaying discussions and idle scene animation do not request inference. SSE updates read saved events; a bounded read fallback handles unavailable streams.
- `references_verified` means reference membership and supported controls, not evidence entailment or agronomic correctness. Qualitative interpretations remain explicitly unverified. Quantities/date expressions in advisor prose are conservatively flagged; authoritative figures render from immutable tool references.
- Completed plot highlights derive from allocation differences across policies, including future allocations on currently empty beds. Delivery rows identify changed order inputs or dates with changed aggregate demand/delivery totals. They do not claim per-order fulfilment attribution.
- Illustrations and the date scrubber do not fabricate crop observations or resolve cultivar/agronomic uncertainty. Actual farm operations remain disabled.

## Executed browser verification

| Suite | Evidence | Result |
|---|---|---|
| Real numerical decision journeys | `reports/decision_journeys.json` | 87 checks passed: all four quests at 360/390/430/1280, all three policies, persisted badges, exact snapshot explanations without inference, main-farm/worklist isolation, baseline plus three branches, and sandbox continuation relative to its parent |
| World interaction and accessibility | `reports/gameplay_browser.json` | 42 checks passed: sixteen beds, six advisors, eight facilities, map control hit-testing above mobile navigation, pan/zoom/recenter, date preview, keyboard/focus, reduced motion, empty-bed-to-demand experiment, legible debrief/forms and no page/console errors |
| Conversation UI fixtures | `reports/conversations_browser.json` | 56 checks passed: all advisors, typed followups, selected-point invitations, bounded council/critic, evidence/units, plot highlighting, proposal prefill, unsupported blocking, delayed-response isolation, saved-discussion initialization race and loading locks, nonshrinking mobile shortcuts, errors, interrupted/reconnected history, seven SSE GETs and replay without POSTs; no provider requests |
| Infeasibility UI fixtures | `reports/infeasible_browser.json` | 52 checks passed at 390/1280: explicit constraint requirements/availability, infeasible-result explanation, inspection badges and main-farm isolation; no provider requests |
| Existing application regression | `reports/gameplay_legacy_browser.json` | 44 checks passed through the new navigation |

Conversation and infeasibility fixtures are explicitly labelled intercepted data. They verify UI behavior; they are not evidence of a live provider response. Real decision/world experiments use the actual planner. Screenshots under `apps/web/screenshots/{gameplay,decisions,conversations,infeasible}` were visually inspected.

## Backend and release verification

- TypeScript checks and Vite production build passed.
- Scenario suite: 28 passed, including control bounds, frozen inputs, continuation, comparison limits, relevant quest changes, infeasibility, tenant isolation, idempotency, unchanged worklists, and computed impacts on empty beds.
- Conversation SQLite suite: 24 passed, including all roles, followups/invitations, budget exhaustion, finite repairs, interruption/replay, reference validation, cap enforcement and the resumable eleven-call mocked release trial.
- Combined real PostgreSQL and conversation suite: 24 passed; `reports/gameplay_postgres_conversations.xml`.
- Final backend regression: **257 passed** across complementary selections: 248 non-PostgreSQL cases (`reports/gameplay_pytest.xml`) and all nine PostgreSQL cases (`reports/gameplay_postgres_final.xml`). Two existing dependency deprecation warnings remain; no failures.
- Independent reviews: `reports/agents/scenario_review.md`, `conversation_review.md`, and `completion_audit.md`. The five final cross-layer findings were fixed and rechecked.

## Deployment and hosting

The intended public service is https://farmtact.fly.dev. Its existing Fly machine and persistent PostgreSQL volume are retained. A private release session outside the repository holds a previously completed numerical run for before/after comparison; its authentication material is never logged.

The Sprite URL was the workspace development server, independently exposed by Sprites' HTTP proxy. Per the user's clarified instruction, the `farmtact-web` service is now stopped and its registration removed. Port 8080 is closed; the Sprite URL returns an authentication redirect rather than FarmTact, while the Fly app and health endpoint return 200 (`reports/gameplay_hosting.json`). The workspace and its development database remain intact.

Documentation checked: [Sprites HTTP services](https://docs.sprites.dev/concepts/services/), [Sprites URL authentication](https://docs.sprites.dev/working-with-sprites/), and [Fly app hostnames](https://fly.io/docs/networking/custom-domain/).

Release progress: the deployed real numerical journey passed 87 checks (`reports/decision_journeys_fly.json`). Initial live formatting/action failures remain recorded (`reports/deepseek_initial_failure.json`, `reports/deepseek_partial_attempt.json`): these consumed six calls and preserved a partial discussion. Compact prompt guidance, safe repair diagnostics, and semantic action blocking corrected those failures without raising global limits. A fresh bounded live direct question, two-advisor invitation and eight-turn council **passed with eleven advisor replies and eleven calls, zero repairs** (`reports/deepseek_conversation_live.json`). It retained both reference-checked and unsupported interpretations; a favourable recommendation was not required. Total release-trial use is seventeen calls across both attempts, under the unchanged daily gateway cap. Resuming the completed trial added zero calls (`reports/deepseek_conversation_resume.json`).

The recorded live transcript renders frozen tool quantities, all six council speakers and the critic conclusion, and replay makes no inference POSTs (`reports/live_replay_browser.json`). Its first browser run exposed a saved-record initialization race. The initialization now respects the selected record generation, all inference actions remain disabled during saved-record loading, and all six shortcuts retain usable height. The deterministic conversation fixture passed 56 checks, including the race and 360px layout. Existing main-farm/run records, the completed branch/quest, all fourteen full-discussion messages and all five earlier partial-discussion messages remain intact (`reports/gameplay_pre_final_persistence.json`). Final redeployment preserved all of these records (`reports/gameplay_persistence.json`). The deployed replay browser passed twelve checks at 390/1280, including retained shortcut height, disagreement, blocked suggestions, frozen quantities and zero inference POSTs (`reports/live_replay_browser.json`). The development web service was then stopped and deleted; the development database and workspace remain intact.

## Final release identity

- Fly image: `registry.fly.io/farmtact:deployment-01M21GZT1XS0GN2J7Y2CK93C1Z`.
- Existing machine: `d8d2060c074438`; existing encrypted 3 GB volume: `vol_rnzewn8jd6055ner`, Singapore.
- Final frontend build: `index-mutC_MYy.js`, `index-ixG2-inL.css`.
- Browser coverage: 281 local checks across the five distinct suites, plus 87 deployed numerical-journey checks and 12 final deployed live-replay checks. Intercepted fixtures remain explicitly distinguished from real numerical/provider execution.
- Backend: all 257 tests passed, including the nine real PostgreSQL cases.
- Live trial: eleven final calls, six earlier failed/partial-attempt calls; no favourable recommendation required, no limit increase, and zero new calls on resume or replay.
- Security scan: repository candidates contain no supplied process-credential values (`reports/gameplay_secret_scan.json`).

This remains a synthetic four-crop planning game. Advisor interpretations are labelled unverified, unsupported suggestions are blocked, and actual farm operations are disabled.
