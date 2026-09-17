Current release, 17 September 2026: V14 is published from `c0e585f` on
`feature/v14-first-season`. Read reports/v14/implementation.md before changing it.
One animated introduction and one card-driven game replace public edition navigation.
V1–V13 public routes are retired; immutable history and remaining state are retained.
The next unused publication number is V15. V14's image must not be overwritten.

Historical release, 16 September 2026: V12 is published from source 9fd5789;
V11 is the retained previous edition. V1–V10 workers/storage are retired, while
immutable release history remains. Read reports/v12/implementation.md,
reports/v12/acceptance-status.md and reports/v12/requirements-evidence.md before
the historical handoffs below. The next unused publication number is V13.

Fresh-workspace restart: read [docs/workspace-handoff.md](docs/workspace-handoff.md).

Current V11 handoff (11 September 2026): latest published edition is V11 from
source `37802adbc9010bc80a50869ef725285a119af3f3`, image
`sha256:e82ba02912d7a716ec4a4588a6fc83721cb361549d9fbbefc92eae1ce439cf7d`.
Read `reports/v11/implementation.md` and the V11 technical chapter first. Guided
production planning and newest-first chooser are published. V1–V10 remain pinned.
The historical handoff below is retained as evidence of earlier states.

Current checkout note (11 September 2026): v10 is the latest published immutable
edition, built from source `ec4e29874b2c7408f2bd93d012912e3c0cb8d2f3` with
image `registry.fly.io/farmtact@sha256:874530e73f481b1197e528bb5f124b958a74be64c9934292c14438b4cdd503bf`.
Start from README.md, the V10 grounding follow-up, the V9/V8 reports and package
reports, docs/execution-plan.md and the release manifests; extend the working
application instead of recreating it.
The catalogue now has twelve profiles and the synthetic fixture still has four
recipes. V7 added a guided, isolated playable council at /v7/research, with labelled
scripted dialogue and real numerical comparisons. Prioritize immediate first-time
usability. Hosting uses one shared gateway Machine and volume for ten editions;
follow the editions runbook. The historical kickoff below is already delivered; current
user intent is conversation connected to tangible farm consequences. V8
introduced explicit required/advisory Council policy, typed server-rendered facts,
a durable synthetic simulation clock and future-only replanning. The current
`daily-bed-cpsat-v3` contract binds cycles to absolute dates, collision-checks
harvest-lot IDs, preserves lot origins across replans, excludes historical executed
cycle IDs and reserves resources against the maximum declared yield factor. The
V10 conversation prompts/projection are V6; mission prompts/projection are V7, use
validator V5 and schema V3, and map short `F001`/`C001` aliases exactly to canonical frozen
references. Both use explicit context bounds and abstain when admitted context
cannot answer. All three actual-AI views render typed evidence from server-shaped
responses. The frozen V9 offline evidence is 606 passed and one skipped regression
test plus 21 of 21 mobile typed-fact assertions. The authenticated public V9 UI
replay passed 38 of 38 mobile/desktop checks without forwarding mutation or
inference requests. The V8 public trial remains a
historical failure: 6 of 10 completed quality cases passed, the invited return and
conversational Council were incomplete, and the ledger records 55 actual requests.
The V9 live quality gate failed: 12 of 18 automated cases passed while workflow
integrity passed. V9 used 21 actual requests (nine mission, eleven conversation and
one research), bringing the cumulative ledger to 76. Two Council abstentions
persisted unsupported, and the scorer missed a false full-fulfilment claim for an
824 kg booked request against 370/446/518 kg strategy deliveries. The completed
AI-assisted review classified 10 messages as sound, 5 as sound with limits and 3
as materially contradictory: Planning Supply and two Production replies. V10 is
the published grounding-remediation edition. Its Council-only live quality result
is FAIL (5 of 7 cases passed); its fresh mission was budget-withheld before inference. Expired
anonymous tenant pruning is a bounded explicit dry-run-by-default operator action
with no automatic schedule. V10 is deployed as a simulation; real operations remain
disabled. V10 publication passed all ten edition health/source checks and captured
v1-v9 preservation passed. V9's capacity check passed two numerical jobs
and 58 browse samples; its 56-day synthetic execution run passed mass, cash and
lot-receipt checks with 60 task events, 64 demand-service events and one replan.
Both used zero provider calls, and the execution run did not exercise a restart.

Start implementing FarmTact in this repository.

Read CODEX_START_PROMPT.md as my latest kickoff instructions, together
with AGENTS.md, MASTER_AGENT_PROMPT.md, the build specification, the
DeepSeek runtime specification, and the trial/cutover runbook.

The new kickoff instructions update the older Strategy Room design:
FarmTact must be mobile-first, visual, playful, and tactical—not a
chat application with farming-themed messages. Preserve the existing
scientific, data-provenance, provider, and your recommended safeguards.

You are the master implementation agent. Inspect the actual repository
before making changes. Reuse the existing contracts, DeepSeek gateway,
fixtures, research registries, and tests where appropriate. Do not
assume the handoff describes capabilities that are already implemented.

Use real Codex subagents for independent work, with at most four running
concurrently. Reuse the A01–A12 briefs. Assign explicit file ownership,
dependencies, deliverables, and acceptance checks. Own shared contracts,
integration, and final verification yourself.

Use the requested GPT master/specialist configuration only where the
installed Codex environment supports it. Verify actual configuration
and availability; do not invent model identifiers, silently change
models, or pretend delegation occurred.

IMPLEMENT IN THIS ORDER

1. Data foundation and early DeepSeek verification

Validate the crop catalogue, scientific evidence, private-data schemas,
and synthetic fixtures. Build actual public-data connectors with
provenance, coverage, units, freshness, and explicit failure states.

Cover all twelve crop knowledge profiles, while initially exercising
caixin, pak choi, kailan, and lettuce in the synthetic farm.

Schedule the DeepSeek gateway tests early, alongside dataset work.
DEEPSEEK_API_KEY will be supplied through the server environment.
Never print it or expose it to the frontend.

All actual FarmTact agent, helper, vision, and LLM-evaluation calls in
development, platform test, staging, and live operation must use
DeepSeek only. GPT/Codex is for building and initial research only.

Verify current official DeepSeek documentation and actual text, tool,
and vision capabilities. Run the supplied bounded authenticated trial
when access is available. Missing access is blocked—not passed—and
must not trigger another-provider fallback.

2. Numerical planning

Implement demand and harvest baselines, supply-gap calculations,
resource constraints, and feasible planting schedules.

Calculate Lean, Balanced, and Resilient strategies using the same
inputs and scenarios. LLMs must not invent authoritative quantities,
yields, probabilities, or business results.

Enforce biological lead times, nursery and bed occupancy, labour,
cash, existing commitments, and inventory mass balance. New sowing
cannot solve a delivery shortage that occurs before crop maturity.

3. Visual mobile Strategy Room

Make the primary interface an interactive farm board with crop tiles,
growth stages, harvest timelines, resource meters, planning missions,
advisor characters, strategy cards, and current-information cards.

Use meaningful animations tied to real backend events. Show agent
findings and disagreements as concise visual cards. Keep detailed
discussion and evidence expandable; chat input is secondary.

On mobile, use thumb-friendly navigation and bottom sheets—not a
compressed desktop dashboard. Support reduced motion, accessible
controls, and non-drag alternatives. Test at 360px, 390px, and 430px
widths as well as desktop.

Every weather, market, and farm-status card must distinguish source
time, freshness, execution mode, and real versus synthetic data.
Never use fake activity, simulated events, or replay as live evidence.

4. Integrated demonstration and review

Demonstrate importing synthetic farm records, retrieving a real public
source, initiating a planning mission, running the DeepSeek council,
calculating alternatives, comparing them visually, approving a
version, and replanning after a clearly labelled simulated disruption.

Persist the evidence and plan versions. Go with your recommendations where approval is needed.
Provide replay without new inference or duplicate paid runs.

Run actual numerical, provider-isolation, security, and browser tests.
Inspect mobile screenshots. Do not report the interface complete
merely because it compiles.

START NOW

Inspect the repository, write a bounded execution plan and ownership
map, delegate the first independent tasks, and begin implementation.
Do not stop after writing a plan or generating another specification.

Continue nonblocked work when an external dependency is unavailable.
Report concrete blockers without fabricating successful integrations.

At each milestone, report files changed, tests actually executed,
source coverage, screenshots where relevant, remaining limitations,
and exact commands to reproduce the result. Preserve resumable status
in the repository.

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
under the unchanged 400-character hard limit. V9 is published from source
`89d29cc3e071e12373204ff234d0a261ce71b5a1` with image
`registry.fly.io/farmtact@sha256:42702ca38566d87c359ae2f92f924b403dbf8fb2ae8166f5377cc829e8d725e4`.
The frozen offline suite passed 606 tests with one skip, the mobile typed-fact
check passed 21 of 21 assertions, all nine edition health/source checks passed,
and v1-v8 preservation passed. V9 used 21 actual requests and its automated quality
result is FAIL: 12 of 18 cases passed while workflow integrity passed. Two Council
abstentions persisted unsupported. The completed AI-assisted review of 18 messages
and 62 atomic assertions found 10 sound, 5 sound with limits and 3 materially
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
public). The V10 full suite passed 611 tests with one skip in 441.23 seconds. The
narrow fix does not establish general prose or crop-mix entailment; AI quality
remains a partial requirement.
V8 and V9 stay unchanged.


Final V10 semantic evidence: `reports/v10/ai-assisted-semantic-review.md` audits
seven messages and 26 assertions: two sound, four sound with limits, one
contradiction. Profit incorrectly labels Lean's −SGD 52.87 margin delta as a gain.
This AI-assisted review is not human expert validation. V10 quality remains failed
and its fresh mission-provider path was budget-blocked; publication and numerical
regression do not close this semantic acceptance requirement. The public 56-day
execution passed mass/cash/order-lot reconciliation and historical receipt replay
with zero provider calls (`reports/v10/execution-public.json`).
