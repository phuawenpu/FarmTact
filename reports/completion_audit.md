# FarmTact development completion audit

Scope: the latest kickoff in `CODEX_START_PROMPT.md`, with the v1.2 autonomous-development policy. This audit distinguishes implemented development behavior from production or research claims. **Development verification passed on 8 September 2026.** Machine reports are authoritative for their recorded runs.

| Requirement | Implementation and evidence |
| --- | --- |
| No human sign-off during this phase | Build/runtime/research specifications use technical gates, independent agent review and server-only `ACCEPTED_FOR_SIMULATION`. The backend selects Balanced after validation. Operational routes are disabled. |
| Actual repository inventory and real delegation | Initial tree had four Markdown files. `docs/execution-plan.md` records real data/gateway/mobile specialists, their disjoint ownership and the verified model configuration. Missing seed artifacts were built, not assumed present. |
| Ten crop knowledge profiles and evidence | `research/crop_catalogue.json` and the evidence/source registries record ten profiles and twenty publications. Four explicitly synthetic recipes power the demo; inaccessible articles and uncertain taxonomies remain labelled. |
| Public data foundation | `data/manifests/dataset_manifest.json`, `data/manifests/lineage.json` and `data/reports/data_quality.json`: seven real sources, eight snapshots, 200 traceable rows. Raw/normalized layers are rebuildable; unresolved releases/licences are explicit. |
| Private contracts and point-in-time features | Pydantic contracts reject invalid units, temporal relationships and missing recipe dependencies. `scripts/build_features.py` writes 32 synthetic features with input/dependency hashes; uncertain public availability excludes those sources from private predictive features. |
| Numerical planning and independent validation | Recipe/EWMA baselines, daily CP-SAT scheduling, Lean/Balanced/Resilient policies, common declared scenarios, nursery/bed/labour/cash constraints, executed-action locks, actual order dates and expiring inventory mass balance. `reports/numerical_evaluation.json` separates synthetic forecast errors and decision metrics. Solver time limits and bounds are reported honestly. |
| DeepSeek-only runtime and actual verification | Exact official origin and thirteen role routes; bounded JSON/tools/vision/SSE gateway; no alternative provider. Final DS-G1/DS-G2 aggregate passed in 15/16 requests and 7,232/8,192 output reservations. `reports/deepseek/latest.json` preserves provenance and prior failed attempts. `reports/final_gateway_probe.json` verifies the hardened gateway through actual process egress. |
| Integrated council, acceptance and replan | `reports/integrated_demo.json` records actual HTTP import, public context, synthetic image observation, six real DeepSeek roles, computed alternatives, automatic acceptance, stored replay and a numerical disruption replan. One unsupported claim is visibly rejected; that does not become a validated assertion. |
| Durable versions and duplicate prevention | PostgreSQL tenant ownership/FKs, immutable farm versions, frozen evidence/input hashes, durable jobs, event cursors, run idempotency and request-budget reservations. Imports and acceptance serialize on a tenant lock. Changed inputs invalidate worklists and trigger automatic numerical refresh. |
| Mobile tactical interface | React crop board, stages/timeline, resource meters, strategy cards, concise advisors, evidence/source details, reduced motion and keyboard alternatives. Numerical-only planning and curated recorded replay are explicit separate actions. `tests/browser/run.mjs` exercises real HTTP behavior at 360/390/430/1280 px. |
| Security and independent review | Independent backend and provider review reports record adversarial tests and resolved findings. Public callers cannot select provider/model/phase, access another tenant's jobs or accept operational plans. Uploads and inference are bounded; credentials stay outside served assets and reports. |
| Reproduction | Locked Python/npm dependencies, documented Sprite services, isolated PostgreSQL verification and `scripts/verify_clean_checkout.py`. The optional Docker definition is not claimed tested. |

## Final verification

- Full Python suite: **191 passed**, zero failures, two upstream TestClient deprecation warnings. Command: `.venv/bin/python -m pytest -q --junitxml=reports/pytest.xml`.
- Real Chromium/HTTP browser suite: **44/44 passed**, zero console/page errors, at 360/390/430/1280 px. Command: `node tests/browser/run.mjs`. Final mobile board, opaque strategy sheet, source/evidence and corrected horizon-resource screenshots were inspected by the master.
- Shared response contracts: generated TypeScript matches Pydantic; bootstrap and recorded replay retain all provenance. Command: `.venv/bin/python scripts/generate_web_contracts.py --check`.
- Clean staged-tree reproduction: **PASS** in a new directory, fresh virtual environment/npm install and separate PostgreSQL database. It fetched 200 public rows, built features/frontend, imported a synthetic farm, accepted three-strategy planning, replayed it and accepted a disruption replan with zero inference calls. Final application source digest matches the tested tree. See `reports/clean_checkout.json`; rerun after staging intended files with `.venv/bin/python scripts/verify_clean_checkout.py`.
- Authenticated final provider trial and separate application integration: **PASS**. Final hardened gateway/egress JSON probe also passed with one bounded real request. No alternate provider was used.
- Repository credential scan: no supplied credential values in staged/tracked candidates; ignored local delivery/runtime files are excluded. Whitespace checks passed.

The served app is `https://farm001-bqddl.sprites.app/`, managed by `farmtact-web` and its PostgreSQL dependency `farmtact-db`. Fresh sessions can use the recorded DeepSeek demo without inference cost or run a new numerical mission. Real council runs remain metered and subject to the finite global daily budget.

## Interpretation and limits

The implemented release is an isolated synthetic planning demonstration. It is not validated for real farm operations, autonomous physical work, buyer communications or commercial decision making. The other six crops remain knowledge profiles; multi-cut, satellite agronomy, energy-system design and regional supply-chain causal forecasting are roadmap items, not demonstrated capabilities.

Public coverage is deliberately bounded: one SingStat page/period, seven historical NASA grid days and NEA observations/forecasts. None is a fictional on-farm sensor. SingStat/NASA redistribution terms and historical availability remain unresolved; public context is not used to fabricate farm labels or causal price/demand effects. Research titles and metadata do not establish agronomic coefficients.

Predictions, margins, resource costs, scenario weights and outcomes come from a labelled synthetic fixture. Downside metrics are minima across the declared scenarios, not calibrated probability bounds. A feasible strategy may leave demand unmet, and solver timeout may use an explicitly recorded deterministic fallback. No savings are measured farm impact.

Recorded integration/council reports preserve their original times, quantities and rejected claims. Later gateway/label/validation corrections are verified separately; replay does not pretend to be a fresh inference call. A numerical-only run has `council_status=not_run` and cannot pass authenticated provider gates.

The demo's Python socket policy permits DeepSeek HTTPS and the configured PostgreSQL destination. It is defense in depth, not an OS/container network security boundary. Production needs infrastructure egress enforcement, a separate credential boundary, real tenant authorization/retention controls, farm recipe validation and operational approval. In-flight HTTP cancellation is bounded by timeouts rather than instantaneous interruption.
