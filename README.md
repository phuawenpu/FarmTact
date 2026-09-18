# FarmTact · One farm, one card experience

FarmTact V19 is the current unpublished candidate for the ordinary synthetic farm through one integrated card
shell. The same application is served at
[the public root](https://farmtact.fly.dev/) and
[/play](https://farmtact.fly.dev/play): review the current farm, calculate and
compare plans, inspect records and evidence, explore saved experiments, replay
history, and manage preferences without switching to a separate dashboard or
edition chooser. Previous/Next buttons, arrow keys and horizontal swipe provide
equivalent card navigation; forms and decisions remain inside the active card
with a bounded action area below it.

V18 remains the published public experience while V19 is verified. V19 brings an
optional Planning Council checkpoint and layered decision brief onto every calculated
strategy card, while preserving the ordinary sandbox, complete tool decks,
revision-bound actions and disabled physical operations. Publication requires a new
immutable V19 source/image record; V18 data and source remain preserved. Read the
[V19 decision-brief contract](docs/v19-council-decision-brief.md),
[V15 capability checklist](docs/v15-capability-checklist.md), and
[publication policy](docs/deployment/editions.md).

The integrated tools cover **Plan**, **Records & work**, **Knowledge & evidence**,
**Experiments**, and **History & preferences**. Planning uses the complete ordinary
farm snapshot and local numerical strategies. Reviewed proposals, imports, task
results, corrections, recovery plans and simulation advances remain explicit,
revision-bound actions. Reading saved explanations, evidence and replays makes no
provider call. Optional adviser and extraction submissions retain the existing
bounded DeepSeek controls; V16 adds no new provider-quality claim.

All farm records and outcomes in the public application remain synthetic or
simulated and are labelled by evidence type. Actual planting, purchasing,
delivery, communication and other physical farm operations are disabled. Automated
V16 verification currently includes 49 semantic, 97 layout, 108 complete-journey,
20 operator, and 28 exact staged-image checks with zero provider requests. Human
farmer comprehension and usability have not been verified.

**Read:** [documentation index](docs/README.md) ·
[scientific implementation report](docs/technical/README.md) ·
[V16 implementation evidence](reports/v16/implementation.md) ·
[V15 capability checklist](docs/v15-capability-checklist.md)

## Historical V13 tactical field console

V13 reorganizes the full shell around one current decision without replacing the
farm board or numerical evidence. Mobile uses a compact card stack, normal-flow
three-action dock, board, Council context, horizontally comparable strategies and
Mission/Records/Crops/More navigation. Desktop keeps the card panel at roughly
25–35% of the workspace, with the board centered and contextual Council alongside it.

The opening **Heavy rainfall** card is a frozen synthetic scenario labelled
`SIMULATION · SCENARIO ONLY`; it is not current weather and does not silently change
the plan. **Keep grow space B3 free** maps to the real fixture entity `bed-07`.
Reserve Space creates and applies an existing revision-bound proposal, waits for the
persisted local CP-SAT job, highlights B3, and replaces the strategy values with the
selected recalculated result plus signed server-derived deltas. The reservation starts
only after the recorded crop's harvest and sanitation period.

Undo is not deletion: it appends a compensating proposal and runs another calculation.
The original event remains auditable, and intervening revisions disable a stale inverse
with a reason. Ask Why carries a server-validated card/entity/snapshot focus. Merely
opening the panel makes no provider call; only an explicitly submitted question may
enter the bounded DeepSeek path. If that optional path is unavailable, the local plan
remains usable and the interface invents no fallback dialogue.

Three scripted first-use judging personas—farm manager, agent architect, and
security/evaluation reviewer—tested fresh tenants with only the original problem
statement and hackathon rubric. Their findings drove fixes to occupancy dates,
feasibility, inverse recovery, duplicate activation, booked gap, strategy eligibility,
focus validation, blocked-provider explanation and selected-strategy metric binding.
This is AI-persona and automated evidence, not human usability research or a claim
about real-farm outcomes.


## V11 guided production planning

V11 follows the [organizer’s original brief](docs/v11-implementation-plan.md):
review farm records, calculate schedules, explicitly request Council review, simulate
a selected plan, then change demand or seasonal assumptions and compare keeping
the saved schedule against replanning. Both comparison arms face the same changed
conditions. Future demand adjustments preserve history and confirmed bookings;
booking edits are explicit. Seasonal yield/delay assumptions are dated synthetic
sensitivities, not fitted weather predictions.

The guided Council selects server-verified facts and tradeoffs. Four specialists
and the Chair make actual DeepSeek calls; Weather and Market receive labelled
absence notices when observations are not admitted. The numerical plan remains
available if optional review is blocked. See the [V11 technical chapter](docs/technical/v11-guided-production-planning.md)
and [acceptance evidence](reports/v11/implementation.md). The full suite passed 643 tests
with one skip; the subsequent staging fix passed 63 tests. The staged live journey
passed all 20 checks using five DeepSeek calls, with no repairs.

The starting screen and V11 switcher list numbered editions newest first.
Planning remains synthetic: the accepted example still leaves 440 kg of booked
demand unserved. Empirical model calibration and farmer validation remain open.

## Earlier planning capabilities and technical background

The capabilities below document the retained planning engine and previous UI
iterations. Historical V14 presented its beginner workflow through cards and did not
expose the earlier room-based navigation or public release chooser. V15 supersedes
that four-bed teaching interface with the ordinary-farm integrated shell.

- Navigate the V13 field deck by swipe, Previous/Next or arrow keys; inspect the
  frozen scenario, reserve B3 through the real planner, compare calculated
  consequences, ask in validated context and undo through an inverse revision.
- Follow the guided production mission from records to schedules, Council review,
  simulated progress and comparison under changed conditions.
- Start the guided council study, calculate a plan, reserve a bed, test an
  unconfirmed order, challenge an assumption and compare frozen versions.
- Explore the main farm board, active batches, deliveries, constraints and worklists.
- Compare **Lean**, **Balanced** and **Resilient** schedules under the same declared
  scenarios. Inspect uncovered demand, costs, resource use, waste and closing stock.
- Use the Data Explorer to inspect records, vary synthetic-generation assumptions,
  adjust the demand baseline and save independent numerical experiments.
- Browse twelve evidence-linked crop profiles and original illustrations. Four
  profiles—caixin, pak choi, kailan and lettuce—have numerical demo recipes.
- Ask Demand, Weather, Market, Production, Supply Chain, Profit and Planner
  advisers for optional interpretations. Reopen saved responses without new inference.
- Inspect weather, trade, climate and News context with dates and provenance.
  Community feeds remain unconnected.
- Enable optional locally bundled music/effects. Text fields support device-keyboard
  dictation where the device offers it; custom recording/transcription is not integrated.

Acceptance saves projected outcomes and worklists. In v8, an accepted
current mission can create a tenant-owned synthetic execution world. Explicit
advance actions move its civil-date clock by one or seven days and record synthetic
sowing, transplanting, harvesting, delivery, inventory, cost and revenue events.
Replanning freezes the next unexecuted day, locks work already started and preserves
past events. The farm-map date slider remains a static preview and records nothing.
Neither path performs a real farm operation.
The [game backend audit](docs/technical/game-backend-and-state-machines.md) traces
these boundaries and the Council gaps in detail.

FarmTact has three distinct Council workflows:

1. A **planning mission Council** runs six specialist DeepSeek calls followed by
   the Planner on one frozen numerical result. Specialists do not debate each other;
   only the Planner receives their validated, bounded findings. There are no two
   challenge rounds. A mission declares `required` or `advisory` Council policy.
   Required policy withholds automatic selection on incomplete or unsupported
   findings; advisory policy keeps the numerical decision available while showing
   Council issues.
2. A **persistent adviser conversation** supports one direct reply, a two-turn
   invited exchange, or a seven-turn sequential Council on a frozen farm, scenario
   or research snapshot. Stored replay makes no inference call.
3. The **guided research study** uses scripted dialogue and local numerical jobs.
   It stores private versioned inputs and never changes the main farm. An explicit
   separate direct-adviser action may interpret a completed frozen research result.

## API and LLM abuse protection

Request admission runs before request-body parsing, job creation or provider
reservation. Counters are atomic PostgreSQL records and are shared across processes,
restarts and active editions through the private control service. If admission
storage is unavailable, protected requests fail closed with HTTP 503; over-limit
requests return HTTP 429 with `Retry-After`.

| Boundary | Current limit |
| --- | --- |
| Every API, per source network | 600/minute |
| Every admitted API/application request, global | 3,000/minute |
| Authenticated API calls, per edition/session | 900/minute |
| Mutations, per source network | 60/minute |
| Mutations, per edition/session | 45/minute |
| Provider-triggering POSTs, per source network | 6/minute and 20/hour |
| Provider-triggering POSTs, per edition/session | 12/hour |
| New anonymous sessions | 30/hour per source network; 100/hour global |
| Shared DeepSeek reservation | 48 calls/day; at most 16 in one reservation |

Provider-triggering admission covers planning Council/review, replanning,
conversation message/invite/Council routes, vision-backed document extraction and
all failed or malformed attempts. The DeepSeek runtime also applies caller-specific
request/output/wall-time budgets, a concurrency ceiling, an allowlisted origin/model,
and no alternate-provider fallback. Numerical planning routes are local but still
receive the ordinary API/mutation quotas. Health and fixed static assets are the only
documented low-cost exemptions. See [security controls](docs/security.md) and the
[provider/council boundary](docs/technical/ai-provider-and-council.md).

## How the intelligence works

![FarmTact separates inputs, numerical authority and optional AI interpretation](docs/technical/figures/system-overview.svg)

| Component | Implemented method | Interpretation boundary |
| --- | --- | --- |
| Farm records | Deterministic versioned fixture; validated imports and saved snapshots | Orders, recipes and farm outcomes in the demonstration are synthetic |
| Demand | Deployed alpha-0.35 EWMA over available weekly order history; confirmed bookings plus positive residual demand | Statistical baseline; the separate synthetic benchmark does not replace it or establish real-farm accuracy |
| Plant development | Recipe nursery/grow dates, fixed marketable yield per area, calendar-based visual progress | Scheduling simulation; no physiological growth, disease or biomass model |
| Strategies | `daily-bed-cpsat-v3` OR-Tools CP-SAT whole-bed selection plus FEFO local simulation and validation | Absolute crop-cycle IDs, collision-checked harvest-lot IDs and a persistent lot-origin map preserve identity across replans; feasibility within declared constraints does not imply full delivery coverage, and only an `OPTIMAL` solver result proves the stated optimum |
| Risk | Declared weighted stress scenarios; Resilient first maximizes the worst scenario aggregate fill floor, then applies its utility tie-break when that floor is proven | Engineering scenarios and weights, not calibrated probabilities, per-order guarantees or confidence intervals |
| Council | Separate planning, conversation and scripted research workflows | Seven roles do not establish seven independent sources of truth |
| DeepSeek | Server-only allowlisted text/native-vision routes use the exact canonical `deepseek-flash` model, bounded calls and local validation | The active caller manifest distinguishes product callers from diagnostic routes; configuration is not a current capability or correctness result |
| Public sources / News | Cached, provenance-aware context | No automatic numerical effect on demand, yield or maturity |
| Vision | Synthetic batch-label reading probe | No deployed crop-health, disease, satellite or biomass inference |

No model is trained or fine-tuned on real FarmTact farm/customer records. V8
introduced, and later editions retain,
independent generated train/evaluation cohorts and benchmarks fixed/tuned EWMA,
seasonal-naive and crop-residual candidates. Promotion is blocked because real-farm,
external-cohort and operational evidence is absent; deployed forecasts remain
`recipe-ewma-v1`. There is no embedding/vector-search or automatic retraining
pipeline. GPT/Codex builds and reviews the software; application inference uses
the DeepSeek gateway.
The [technical report](docs/technical/README.md) documents equations, prompts,
call triggers, budgets, persistence, evidence and limitations with source links.

## Reference farm and evidence

The default fixture represents 16 beds of 20 m², eight existing batches, 32 future
orders and 48 weekly historical observations across four crops. The planning
horizon is 56 days from the fixture's September 2026 cutoff; waiting for a job
does not advance the farm calendar. Nursery, labour, cash and inventory are explicit
constraints. Twelve crop knowledge profiles do not imply twelve validated recipes.

The original public ingestion report contains 200 normalized rows across seven
weather/trade/climate sources. These are recorded snapshots with bounded coverage,
not a promise of current availability or a complete historical warehouse. News is
a separate bounded RSS metadata cache. Research citations do not validate fixture
yields, financial assumptions or achieved farm benefits.

See [data inventory](docs/data-and-models.md),
[data lineage](docs/technical/system-data-and-evidence.md) and
[growth mathematics](docs/technical/numerical-models-and-growth.md).

## Repository map

| Path | Responsibility |
| --- | --- |
| `apps/web/` | React/TypeScript/Vite interface, farm artwork, council study, explorer and audio |
| `services/api/app.py` | FastAPI application, planning worker, simulation acceptance and routes |
| `services/api/` | Tenant persistence, scenarios, conversations, research, security and edition gateway |
| `runtime/deepseek_gateway.py` | Provider policy, transport, JSON/tool/vision/stream handling and safe audit |
| `config/deepseek_runtime.json` | Active caller inventory, exact canonical model routes, migration provenance and transport/budget limits |
| `packages/contracts.py` | Validated farm inputs, recipes and hashes |
| `packages/fixtures.py`, `packages/models/` | Synthetic generation and EWMA/harvest baselines |
| `packages/planner/` | Whole-bed scheduling, scenario simulation and research constraints |
| `packages/ingestion/`, `packages/news.py` | Public-source normalization and bounded News collection |
| `research/`, `data/manifests/` | Curated knowledge and source/feature provenance |
| `tests/`, `reports/` | Executable checks and dated evidence with scoped claims |
| `config/releases/`, `config/hosting/` | Immutable release registry and shared Fly topology |
| `docs/` | Technical report, requirements gaps, research and operational runbooks |

## Local setup

The locked application targets Python 3.13+, Node 24 and PostgreSQL 18.
Use the committed dependency files; the optional Docker Compose path remains
historically unverified. The separate Fly image was built and deployed.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
npm ci --prefix apps/web
npm run build --prefix apps/web
```

Provide an empty development PostgreSQL database through `FARMTACT_DATABASE_URL`.
The Sprite default is `postgresql+psycopg://sprite@/farmtact?host=/tmp/farmtact-pg`;
it works only when that local server/database has been provisioned. The checkout
does not contain a virtual environment, running database or generated frontend build.
`.env.example` documents names; it is not automatically loaded by `serve.py`.

```bash
.venv/bin/python scripts/initialize_database.py
.venv/bin/python -m packages.fixtures
.venv/bin/python scripts/build_dataset.py --fixture-bundle data/fixtures/public_context_v1
.venv/bin/python scripts/build_features.py
.venv/bin/python scripts/generate_web_contracts.py
```

The fixture-bundle command is a clean-checkout, network-free path. It verifies the
committed project-authored synthetic provider-contract bundle before running the
normalizers. `--offline` instead rebuilds previously captured immutable snapshots;
a live build makes bounded public-source requests and writes explicit failure/cache
states. See the [reproduction guide](docs/technical/reproducibility.md)
for offline checks, generated artifacts and service prerequisites.

Outside Sprite, run `.venv/bin/python scripts/serve.py` to serve the application
on port 8080, then open `/v13/` for the tactical shell. **Inside Sprite**, register
that command using `sprite-env services create`; follow the Sprite skill for service management. Numerical-only exploration
does not require a DeepSeek key. Actual adviser calls require `DEEPSEEK_API_KEY`
in the server environment (or the protected local delivery file supported by
`serve.py`). Keep credentials out of source, frontend variables, command arguments
and logs. Key presence does not establish current model availability.

## Verification and current limits

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/generate_web_contracts.py --check
npm run build --prefix apps/web
```

V13's release gate includes generated contracts, a production TypeScript/Vite
build, the full suite against an isolated PostgreSQL 18 database, and two browser
layers. The deterministic responsive journey covers 360, 390, 430 and 1280 px,
swipe versus vertical scroll, buttons, keyboard, active-card isolation, reduced
motion, focus restoration, stale Undo, and zero inference before explicit Ask.
The separate real-backend journey exercises PostgreSQL, the worker and local CP-SAT
through baseline → post-sanitation B3 reservation → feasible selected-strategy
deltas → inverse recalculation. Final evidence is preserved in
[the V13 implementation report](reports/v13/implementation.md) and
[`full-regression.xml`](reports/v13/full-regression.xml). The production bundle is
601.77 kB JavaScript (172.60 kB gzip); the retained over-500 kB warning is a measured
code-splitting item, not hidden as a pass.

The final isolated PostgreSQL run passed **757 tests with one skip** in 758.42
seconds. It emitted two test-client deprecations and one Pydantic schema warning;
there were no failures or errors. Generated web contracts, the frontend build,
53 focused focus/inverse/admission tests, 42 shared-control/admission tests, the
real browser journey and the responsive browser journey all passed.

The final real 390 px journey displayed 824 kg booked demand, 446 kg baseline supply
and a 378 kg booked gap. Reserving B3 from 1 October produced three feasible options;
the selected Balanced consequences were 442 kg coverage, 41 kg closing surplus,
193 kg expiry exposure and SGD 2,731.1 margin. Undo restored the baseline. Those are
synthetic fixture results, not yield forecasts or evidence of agronomic benefit.

`apps/web/src/lib/types.ts` is generated from the authoritative Pydantic view
models; edit the models and regenerate rather than hand-editing that file. Fixture
import, planning, conversation, research and simulation mutations require an
`Idempotency-Key` of at most 128 characters. Reusing a key with identical input
returns the stored result; changed input is rejected.

V9 passed the final whole-repository regression with **606 tests passed and one
skipped** in 446.38 seconds. Its mobile typed-fact check passed **21 assertions**
at 390 × 844 with no JavaScript errors, using intercepted server-shaped fixtures
and zero provider calls. All nine public health/source checks and captured v1–v8
state preservation passed. These software and display checks do not establish
provider answer quality.

The [authenticated public V9 UI replay](reports/v9/ui-live-replay.json) passed **38 of 38** checks at mobile and
desktop widths. It read the saved mission, conversation and research state; all
mutation attempts and direct provider traffic were intercepted before network
dispatch, so no mutation or inference request was forwarded.

V9's public capacity check passed two overlapping numerical jobs and 58 browse
samples with zero provider calls. Its 56-day synthetic execution run passed mass,
cash and lot-receipt checks with 60 task events, 64 demand-service events, one
future replan and zero provider calls. That run did not exercise an actual
application restart.

**V8 public AI quality failed.** The planning Council completed seven validly
referenced replies, but some explanations confused metric meaning or role scope.
The invited conversation stopped at the existing response-length limit. The
combined scorer passed 6 of 10 completed cases and failed workflow completeness.
The [postmortem](reports/v8/public-ai-postmortem.md) preserves all evidence. V9
publishes the separate semantic-context, typed-evidence and display corrections,
but its live quality gate also failed: **12 of 18** automated cases passed while
workflow integrity passed. V9 consumed 21 actual requests (nine mission, eleven
conversation and one research), bringing the cumulative ledger to 76. Two Council
abstentions persisted as unsupported, and a Supply reply falsely said an 824 kg
booked request was fully delivered despite strategy deliveries of 370, 446 and
518 kg. The completed [AI-assisted semantic review](reports/v9/ai-assisted-semantic-review.md)
classified the 18 messages as 10 sound, 5 sound with limits and 3 materially
contradictory: Planning Supply and two Production replies. It found that four
automated failures were conservative keyword/prefix misses and two were real
abstention-contract failures. V10 is the published
[grounding-remediation edition](docs/technical/v10-grounding-followup.md).
Its full suite passed 611 tests with one skip in 441.23 seconds. The live
Council-only trial used nine requests for seven messages and passed 5 of 7 targeted
cases: Weather/Market absence handling passed, while Supply was withheld for the
model-authored word “zero” and Chair missed a topic word. A fresh mission was
correctly withheld before inference because seven daily requests remained but nine
were required; all three numerical strategies remained available. No new direct,
invite, research or vision result is claimed. That narrow fix
does not establish general prose or crop-mix entailment; AI quality remains partial.
The final task total is **85 actual requests** (44 local and 41 public), including
failed and repaired attempts. **V10 AI quality remains failed/incomplete.** Its
[seven-case semantic audit](reports/v10/ai-assisted-semantic-review.md) found two
sound messages, four with limits and one contradiction: Profit called a negative
Lean margin delta a gain. These gaps are retained as explicit next-iteration
requirements. The public 56-day V10 execution passed numerical reconciliation
and receipt replay with zero provider calls. **Shared-host capacity also failed**
the final two-job test: both scenarios exceeded 180 seconds and browse p95 was
15.04 seconds. [Capacity evidence](reports/v10/capacity-protocol-note.md) preserves
both runs; healthy endpoints do not establish acceptable loaded performance.

Expired anonymous workspaces can be reviewed and removed only through the explicit
[retention CLI](docs/runbooks/retention.md). It defaults to dry-run, retains 30
days, enforces a minimum of seven days and a maximum of 500 candidate tenants per
invocation, skips active jobs, and has no automatic deletion schedule.

The full suite includes PostgreSQL integration tests; use the dedicated test
databases documented in the [reproduction guide](docs/technical/reproducibility.md).
Browser checks require a running development service and Playwright Chromium.
`node tests/browser/run.mjs` covers the original journey; release-specific scripts
cover later features. The numerical evaluator rewrites its report and may produce
different feasible schedules under time-limited solving.

Archived v7 evidence records 33 final contracts/research tests, 111 planning/UI
checks and 48 novice checks. The broad candidate run had 492 passes and one contract
drift failure; that failure was fixed and checked in the focused group. Public
browser review passed 111 checks. These are historical scopes, not newly rerun
full-suite results. See [v7 evidence](reports/v7/implementation.md) and the
[documentation audit record](reports/documentation/2026-09-11.md).

Both recorded v7 actual adviser probes were flagged **unsupported**. They verified
transport/context/replay boundaries, not farming-answer quality. Earlier successful
provider trials do not erase those results. Future work includes grounded adviser
quality, capability freshness, clearer model semantics, stronger numerical validation
and human usability studies; acceptance criteria are in the
[v8 remediation report](docs/technical/v8-remediation-report.md). V8 package
evidence is in [Council](reports/v8/council.md), [planner](reports/v8/planner.md)
and [data/ML](reports/v8/data-ml.md); the V9 follow-up and its evidence are linked
above. Actual trial failures remain evidence rather than being overwritten by
later attempts.

## Hosting and releases

The `farmtact` app runs in Singapore. V15 is the single current public application;
its `/` and `/play` entry points share the same shell and ordinary-farm state.
Historical application sources and images remain immutable, and prior public state
was preserved according to the cutover records. Abuse and inference spending limits
remain shared infrastructure boundaries. Healthy endpoints alone do not establish
loaded capacity.

Every newly published application iteration receives a new immutable edition.
Use [the edition publisher](docs/deployment/editions.md); a generic `fly deploy`
does not describe the preserved release workflow. After V15, the next contiguous
edition is V16; existing numbered source, image and retained state are never
overwritten. See [Fly operations](docs/deployment/fly.md).

Development scope and provider policy are controlled by the
[build specification](FarmTact_Build_Specification.md),
[runtime specification](FarmTact_DeepSeek_Runtime_Specification.md) and
[repository instructions](AGENTS.md). Their requirements include future work;
source and dated reports establish what has been implemented and tested.
