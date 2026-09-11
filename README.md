# FarmTact · Command & Cultivate

FarmTact is a mobile farm-planning game and research demonstration for a fictional
Singapore vegetable farm. Explore a visual farm, inspect orders and evidence,
compare planting strategies, and discuss the consequences with a council of advisers.
Local Python calculations produce quantities and schedules; optional DeepSeek calls
interpret frozen results. Actual planting, purchases and farm communications are disabled.

**Play:** [guided v7 council](https://farmtact.fly.dev/v7/research) ·
[main v7 farm](https://farmtact.fly.dev/v7/) ·
[edition chooser, v1–v7](https://farmtact.fly.dev/)

**Read:** [documentation index](docs/README.md) ·
[scientific implementation report](docs/technical/README.md) ·
[known gaps and next iteration](docs/technical/gaps-and-next-iteration.md)

## What you can do

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

Acceptance saves projected outcomes and worklists. The backend does not yet advance
a simulation clock or mark sowing, harvesting and delivery tasks as executed.
The [game backend audit](docs/technical/game-backend-and-state-machines.md) traces
these boundaries and the Council gaps in detail.

The v7 research study stores its own inputs, jobs, proposals and selected simulation.
It does not change the main farm. Its default dialogue is **scripted**; calculation
jobs run the real numerical planner. Actual adviser interpretation is a separate action.

## How the intelligence works

![FarmTact separates inputs, numerical authority and optional AI interpretation](docs/technical/figures/system-overview.svg)

| Component | Implemented method | Interpretation boundary |
| --- | --- | --- |
| Farm records | Deterministic versioned fixture; validated imports and saved snapshots | Orders, recipes and farm outcomes in the demonstration are synthetic |
| Demand | EWMA over available weekly order history; confirmed bookings plus positive residual demand | Statistical baseline; no trained demand regressor or real-farm accuracy claim |
| Plant development | Recipe nursery/grow dates, fixed marketable yield per area, calendar-based visual progress | Scheduling simulation; no physiological growth, disease or biomass model |
| Strategies | OR-Tools CP-SAT whole-bed selection plus local simulation and validation | Feasibility within declared constraints does not imply full delivery coverage or proven optimality |
| Risk | Three fixed yield/demand stress cases with equal declared weights | Scenario comparisons, not calibrated probabilities or confidence intervals |
| Council | Separate planning, conversation and scripted research workflows | Seven roles do not establish seven independent sources of truth |
| DeepSeek | Server-only allowlisted text/vision routes with bounded calls and local validation | An allowed route is not proof that a feature uses it or that a response is correct |
| Public sources / News | Cached, provenance-aware context | No automatic numerical effect on demand, yield or maturity |
| Vision | Synthetic batch-label reading probe | No deployed crop-health, disease, satellite or biomass inference |

No model is trained or fine-tuned on FarmTact farm/customer records. There is no
embedding/vector-search or model-retraining pipeline. GPT/Codex builds and reviews
the software; application LLM inference uses the DeepSeek gateway.
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
| `config/deepseek_runtime.json` | Registered roles, model aliases and transport/budget limits |
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
.venv/bin/python scripts/build_dataset.py --with-power
.venv/bin/python scripts/build_features.py
```

Dataset building makes bounded public-source requests and writes explicit
failure/cache states. `--offline` requires previously fetched raw files, which
are not committed. See the [reproduction guide](docs/technical/reproducibility.md)
for offline checks, generated artifacts and service prerequisites.

Outside Sprite, run `.venv/bin/python scripts/serve.py` to serve the application
on port 8080. **Inside Sprite**, register that command using `sprite-env services
create`; follow the Sprite skill for service management. Numerical-only exploration
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
[gap register](docs/technical/gaps-and-next-iteration.md).

## Hosting and releases

The `farmtact` app runs in Singapore on one shared 4-vCPU/4-GB Fly Machine and one
3-GB persistent volume. The gateway and v1–v7 occupy eight isolated containers with
separate application databases/caches/progress; abuse and inference spending limits
are shared. One host is a shared failure boundary. Read-only checks on 11 September
2026 found the Machine started with 1/1 health checks passing.

Every newly published application iteration receives a new immutable edition.
Use [the edition publisher](docs/deployment/editions.md); a generic `fly deploy`
does not describe the active container topology. The next unallocated edition in
the inspected registry is v8. This documentation update does not modify v7 or
publish v8. See [Fly operations](docs/deployment/fly.md).

Development scope and provider policy are controlled by the
[build specification](FarmTact_Build_Specification.md),
[runtime specification](FarmTact_DeepSeek_Runtime_Specification.md) and
[repository instructions](AGENTS.md). Their requirements include future work;
source and dated reports establish what has been implemented and tested.
