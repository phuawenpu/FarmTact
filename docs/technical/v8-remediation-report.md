# FarmTact V8 remediation: methods, implementation evidence, and validation limits

**Audit date:** 11 September 2026 UTC<br>
**System state:** development worktree; full regression passed, release decision pending<br>
**Data status:** synthetic demonstration only<br>
**Operational status:** real farm operations disabled<br>
**Live Council quality status:** **FAILED / remediation in progress**

## Abstract

This report evaluates the V8 remediation of FarmTact as a software and numerical system, rather than as a validated agricultural decision system. The evaluated implementation joins a deterministic demand baseline, a whole-bed planning model, a persistent synthetic execution world, bounded scenario and research workflows, and optional DeepSeek interpretation. The principal engineering change is that planned schedules can now be advanced through a recorded civil-date clock with append-only events, order and lot attribution, inventory conservation, cash accounting, and future replanning. The numerical planner now consumes explicit weighted scenarios, exposes its objective components, applies a lexicographic maximin policy for the Resilient strategy, distinguishes missing prices from observed zero prices, and aligns optimization with first-expiry-first-out (FEFO) replay. The data package preserves the original fixture hash while adding disjoint, versioned synthetic training and evaluation cohorts. Demand evaluation uses rolling origins and one-, two-, and four-week horizons; crop-cycle evaluation uses independent whole-batch outcomes. The current evaluator is `rolling-origin-demand-v4` and includes a behavioral counterfactual availability probe. No fitted candidate is eligible for production. The crop residual candidate is worse than its recipe baseline on both primary held-out errors, and every real-data promotion gate remains blocked. The Council now selects server-owned typed facts and keeps execution, evidence, and decision influence as separate statuses. However, the retained actual-provider experiments do not pass the quality gate. Twenty-four paid requests have been consumed across four experiments: one failed on a retired-model mismatch, nine exercised the canonical model and native vision but included five unsupported claims, seven exercised the V3 contract with six valid outputs and one format rejection caused by the word `three`, and seven exercised the repaired V3 prompt with six valid outputs and one unknown-reference rejection. Provider connectivity and native-vision transport therefore cannot be reported as validated Council quality. Focused deterministic, browser, and PostgreSQL concurrency tests provide strong evidence for the implemented mechanics. The repository-wide regression completed with 556 passed and one skipped test in 398.002 seconds according to its XML artifact. The retained 56-day HTTP execution trial also passed across an actual application restart with zero provider calls. Release and live Council quality decisions remain separate and unresolved.

## 1. Questions and claim boundary

The audit addressed six questions.

1. Can a frozen accepted mission become a persistent, inspectable synthetic world?
2. Do planning, replay, and execution share explicit schedule and inventory rules?
3. Can the model evaluation detect useful implementation differences without representing synthetic scores as farm accuracy?
4. Are model-generated statements traceable to immutable numerical facts while qualitative interpretation remains visibly unverified?
5. Do retries, cancellation, concurrency, and tenant isolation preserve one authoritative state transition?
6. Which report gaps are resolved in code, and which require live or real-world evidence before release or model promotion?

The strongest supported claim is an engineering claim: FarmTact V8 can calculate and persist bounded synthetic planning experiments with explicit provenance and replay controls. The evidence does not support a biological efficacy claim, a forecast-accuracy claim for a real farm, an economic-return claim, or permission to act on a farm. The system itself labels these boundaries in the private data contract, [simulation service](../../services/api/simulation.py), [model evaluation report](../../reports/v8/synthetic_model_evaluation.json), and [Council remediation report](../../reports/v8/council.md).

## 2. Evidence hierarchy and methods

### 2.1 Evidence hierarchy

The audit used the following order of authority.

| Level | Evidence | Interpretation |
| --- | --- | --- |
| 1 | Current executable source and strict schemas | Defines implemented behavior |
| 2 | Machine-readable generated reports with hashes and versions | Defines the recorded result of a bounded run |
| 3 | Focused test logs and retained browser artifacts | Supports a particular tested path and environment |
| 4 | Specialist narrative reports | Explains methods and known limitations |
| 5 | Specifications and earlier technical chapters | Defines intended behavior and historical context |
| 6 | Provider announcements | Defines external model naming and migration facts only |

Conflicts were resolved in favor of current source and newer generated artifacts. Historical reports were retained rather than rewritten. The machine-readable gap register was `in_progress` when inspected and was being updated concurrently, so this report states evidence dispositions without overriding its eventual integration status; see [gap-status.json](../../reports/v8/gap-status.json).

### 2.2 Static inspection

Static inspection covered the strict farm and outcome contracts, synthetic generators, feature construction, evaluation code, planner, accounting replay, simulation routes, SQL-backed stores, scenario and conversation workers, Council orchestration, provider gateway, client mutation transport, and the recorded-world UI. Primary entry points are listed in the reproducibility appendix. The review checked version constants, bounded collection sizes, tenant predicates, state-transition guards, frozen-input hashes, cancellation boundaries, and the absence of an automatic public-data-to-planner edge.

### 2.3 Dynamic evidence

Dynamic evidence came from existing local artifacts and focused test reports. No provider request was made for this document. The synthetic model report was regenerated with versioned seeds and contains its own report ID, manifest hashes, evaluation versions, and timestamp. The browser report was generated against a temporary isolated PostgreSQL database with the normal worker active and Council inference disabled. The concurrency reports used PostgreSQL rather than treating SQLite behavior as production evidence. Exact commands and the limits of each run appear in Section 12.

### 2.4 Status vocabulary

“Implemented” means a code path and contract exist. “Focused pass” means the cited bounded test completed successfully. “Synthetic result” means every target or execution outcome was generated by code. “Blocked” means a required external or operational condition is absent. “Pending” means the integration owner has not yet produced the final result. “Unsupported” means local evidence validation rejected a model statement even if the provider returned a syntactically usable response.

## 3. V8 system architecture

The browser speaks same-origin JSON and event-stream APIs to FastAPI. PostgreSQL holds tenant-owned farm versions, missions, branches, conversations, research sessions, simulation worlds, events, and mutation receipts. An in-process worker claims durable numerical and provider jobs. Local Python owns forecasting, optimization, replay, state transition, and factual rendering. DeepSeek is called only for explicit interpretation paths.

```mermaid
flowchart LR
    UI[React V8 client] -->|GET, mutations, SSE| API[FastAPI]
    API --> Auth[Anonymous tenant session]
    API --> DB[(PostgreSQL state and receipts)]
    API --> Worker[Bounded job worker]
    Worker --> Forecast[recipe-ewma-v1]
    Worker --> Planner[daily-bed-cpsat-v2]
    Planner --> Replay[Daily FEFO simulation]
    API --> World[synthetic-execution-v1]
    World --> DB
    Worker -. explicit Council request .-> Gateway[Reviewed DeepSeek gateway]
    Gateway -. deepseek-flash .-> Provider[DeepSeek API]
    Public[Public context caches] -. qualitative context only .-> API
    Public -. no automatic numerical edge .-> Planner
```

The implementation preserves the design separation described in [system-data-and-evidence.md](system-data-and-evidence.md): tenant farm state and explicit scenario controls can alter numerical inputs; public weather, news, and trade records cannot do so automatically. `public_features_used` is empty in both current numerical evaluation artifacts.

## 4. Persistent synthetic execution

### 4.1 Admission and world creation

A world can be created only from the current tenant's mission whose status is `ACCEPTED_FOR_SIMULATION` and whose input version is still current. The route rejects a stale mission, an unaccepted mission, overdue historical harvests without execution records, or a ninth world in the same session. Creation chooses the accepted strategy and freezes a central execution scenario with yield and demand factors equal to one. It stores the segment farm, allocations, deterministic replay trace, opening lots, opening cash, exact decimal revenue and cost accumulators, a civil-date horizon, and `real_operations_enabled=false`. The implementation is in [simulation.py](../../services/api/simulation.py).

The public world contains its revision, clock, bed states, inventory, task IDs, totals, cash, event sequence, plan history, runtime provenance, and state hash. Its stage representation comes from the shared [schedule-state-v2 helper](../../packages/growth.py), not from a second UI-specific growth rule. The helper explicitly declares that progress is elapsed schedule fraction and is not physiological biomass.

### 4.2 Canonical schedule semantics

The schedule states are `empty`, `nursery`, `growing`, `ready`, `harvested`, and `sanitation`. An executed harvest requires a recorded task; a snapshot does not infer that a past scheduled harvest occurred. Projected views may assume scheduled tasks execute. A bed is reserved through the harvest date plus `sanitation_days`, inclusive, and becomes available on the following civil date. The API exposes the same recipe calendar metadata to the client, including nursery, grow, sanitation, shelf-life, and growth-model version fields. The UI preview range ends at `horizon_days - 1`, so 7-, 56-, and 84-day horizons end at indices 6, 55, and 83.

### 4.3 Daily state transition

For each included day, execution verifies that persisted opening lot mass equals the frozen trace's opening mass. It records due sow, transplant, harvest, and sanitation-complete tasks once. It appends order-service events from exact order allocations. Revenue accumulates only when a delivered line has a non-null effective price. Input, labour, packing, and disposal costs are accumulated with `Decimal`, and public money values round at the cent boundary. The closing lot snapshot becomes the next day's inventory. The following invariant is checked for each day:

\[
M_{open} + M_{harvest} - M_{delivered} - M_{disposed} = M_{close}.
\]

The cumulative cash identity is:

\[
C_t = C_0 + \sum_{d \le t} Revenue_d - \sum_{d \le t} Cost_d.
\]

The daily event and world update share the store's ambient transaction, which is important because a multi-day advance must commit all included days or none. The world revision advances once per mutation, while the event sequence advances once per appended event.

### 4.4 Replanning

Replanning is admitted after at least one executed day and only when seven or more unexecuted days remain. The route allows at most twelve replans per world. It carries forward inventory, future orders, bounded nonnegative cash, and growing allocations whose sanitation occupancy reaches the new segment. Those allocations enter the planner as executed locks and cannot be silently removed or charged again for already completed sowing inputs. New candidate sowing cannot precede the new segment start. The local calculation runs outside the tenant lock; commit reacquires the lock and compares the original revision. If another mutation has advanced the world, the computed continuation is discarded. Only a feasible Balanced continuation replaces the future segment. The prior plan hashes and through-date remain in `plan_history`.

```mermaid
sequenceDiagram
    participant B as Browser
    participant A as Simulation API
    participant P as Local planner
    participant D as PostgreSQL
    B->>A: POST replan(revision, Idempotency-Key)
    A->>D: find receipt and read tenant world
    A->>A: freeze future farm and executed locks
    A->>P: plan(candidate_not_before, locked_allocations)
    P-->>A: feasible strategies and trace
    A->>D: lock tenant and reread revision
    alt revision unchanged
        A->>D: append prior plan, event, world, receipt
        A-->>B: recorded continuation
    else concurrent mutation committed
        A-->>B: Conflict response - calculated result is not applied
    end
    B->>A: GET current world
```

### 4.5 Execution evidence and limits

The dedicated PostgreSQL test issued six simultaneous same-key advances and found one committed civil day and one matching receipt. Two different keys competing at the next revision produced one success and one 409 conflict. Historical receipt replay returned the original response without changing the newer world. A second tenant received 404 for the world, events, and mutation route. A reconstructed store observed the same world and ordered events. This focused test passed once in 7.38 seconds; details are in [execution-validation.md](../../reports/v8/execution-validation.md).

The 56-day restart-safe HTTP trial in [v8_execution_trial.py](../../scripts/v8_execution_trial.py) passed across an actual application restart. Its retained [execution-trial.json](../../reports/v8/execution-trial.json) records 56 contiguous `day_closed` events, 64 demand-service events, 52 task events, one future replan, mass/cash/order-lot conservation passes, historical-action replay, restart persistence, and zero provider calls. The cash constraint nevertheless remains narrower than the execution ledger: planning constrains new input cost, while execution deducts input, labour, packing, and disposal. A conserved ledger can consequently have a negative balance. That semantic gap must be resolved before cash is described as a full liquidity constraint.

## 5. Planner and accounting remediation

### 5.1 Weighted declared scenarios

`daily-bed-cpsat-v2` accepts an optional declared scenario set while preserving the original three-scenario default. The planner rejects empty sets, duplicate IDs, more than 100 rows, invalid factors, negative or non-finite weights, and non-positive total weight. Raw weights are normalized and converted to 1,000 deterministic integer objective units, with at least one unit for every positive weight. Returned scenario records expose raw, normalized, and integer weights. This is an engineering distribution chosen by the caller, not a calibrated probability model.

```mermaid
flowchart TD
    Farm[Frozen Farm] --> Forecast[Demand and harvest forecast]
    Scenarios[Declared scenarios and weights] --> Validate[Validate and normalize]
    Forecast --> Candidates[Whole-bed candidates and locked work]
    Validate --> Objective[Scenario objective terms]
    Candidates --> CP[CP-SAT whole-bed model]
    CP --> Lean[Lean weighted utility]
    CP --> Balanced[Balanced weighted utility]
    CP --> Primary[Resilient primary maximin fill]
    Primary -->|OPTIMAL floor proven| Secondary[Weighted-utility tie-break]
    Primary -->|incumbent only| Label[Report FEASIBLE without optimality claim]
    Lean --> Replay[Independent daily replay]
    Balanced --> Replay
    Secondary --> Replay
    Replay --> Gate[Constraint, mass, and objective reconciliation]
```

A constructed one-bed test changes the chosen action when the quiet/busy weights are reversed from 99/1 to 1/99. This behavioral check supports use of weights in the objective rather than merely their presence in metadata. The objective charges scenario-independent new-work cost once. The reported maximum quantization scale is approximately 0.001 of total objective weight.

### 5.2 Policy objectives and proof language

Lean and Balanced maximize weighted policy utility. Each scenario exposes revenue, packing cost, disposal cost, shortfall mass and coefficient, disposed mass and coefficient, terminal stock and coefficient, and new-work commitment cost. The resulting unit is described as SGD-equivalent policy score because penalty coefficients encode preferences; it is not literal expected profit.

Resilient first maximizes the minimum aggregate fill rate across all declared scenarios to one basis-point resolution. Only an `OPTIMAL` primary result freezes the proven floor for a secondary weighted utility solve. A merely `FEASIBLE` primary result is an incumbent and cannot support a claim of optimal downside protection. If the secondary stage times out, the proven primary schedule can be retained with an unfinished tie-break label. This is aggregate scenario service protection; it is not a per-order guarantee, chance constraint, CVaR estimate, or empirical risk distribution.

### 5.3 FEFO, order priority, and missing price

The CP model uses remaining-life buckets keyed to civil expiry dates. Replay allocates the earliest expiry first, then harvest date, then lot ID. For common shelf life this resembles FIFO; differing explicit expiry dates make the implemented policy FEFO. A later-expiring bucket cannot be consumed while an earlier bucket is available. The test space enumerated 81 small two-lot/two-day combinations and reconciled the allocator with the best feasible delivery/disposal outcome.

Demand service is sequential: booked commitments precede inferred residual demand, known higher prices precede lower prices within kind, and stable IDs break ties. Confirmed lines expand to current order IDs after cancellation. `order_allocations` records requested, delivered, and shortfall mass plus each lot's ID, quantity, harvest date, and expiry date. Residual lines use stable synthetic IDs. The schema lacks buyer priority, grade, and lot/customer eligibility, so the model makes no such allocation claim.

Forecast contract 2.0 retains numeric `price_sgd_per_kg=0` for compatibility when no booked price exists, but adds `price_status=unavailable_no_booked_price`. The planner converts that state to a null effective price and records unpriced requested and delivered mass. Dates with booked prices use `booked_weighted_average`. Missing price therefore does not become evidence of observed zero revenue.

### 5.4 Terminal stock and horizon effects

Closing inventory remains usable or expiring stock at horizon close. It has zero declared salvage value and is not counted as waste merely because the horizon stops. Lean, Balanced, and Resilient apply provisional closing-stock penalties of 0.50, 0.20, and 0.05 SGD-equivalent per kilogram respectively. A later horizon can convert that same mass into actual expiry disposal. These penalties require observed storage, spoilage, future-order, and disposal economics before operational interpretation. Implementation and test evidence are summarized in [planner.md](../../reports/v8/planner.md), with source in [engine.py](../../packages/planner/engine.py) and [accounting.py](../../packages/planner/accounting.py).

## 6. Data lineage and reproducible fixtures

### 6.1 Registry coverage

Coverage is derived from the current crop and evidence registries rather than hard-coded report prose. The validated registry contains 12 crop profiles and 24 evidence documents, plus registry versions and source-file SHA-256 digests. A contradictory manifest fails validation. The older 8 September data-quality artifact remains historical and was not edited to imitate a current rebuild.

The clean-checkout fixture bundle contains six small project-authored CC0-1.0 provider-contract payloads. Its manifest fixes byte counts and SHA-256 values and rejects unsafe paths or changed content before normalization. It produced 24 normalized rows: six weather observations, seventeen forecast rows, and one trade-contract row. Installation and rebuild produced identical dataset IDs, row counts, and normalized hashes in [data_pipeline_verification.json](../../reports/v8/data_pipeline_verification.json). The bundle is labeled `synthetic_contract_fixture`. Archived SingStat and NASA response bodies were not redistributed because lawful reuse had not been established.

```mermaid
flowchart LR
    Registries[Crop and evidence registries] --> Coverage[Derived 12 / 24 coverage]
    Bundle[Six bounded CC0 synthetic payloads] --> Hash[Byte and path validation]
    Hash --> Normalizers[Normal source normalizers]
    Normalizers --> Rows[24 traceable normalized rows]
    Rows --> Dataset[Content-addressed artifacts and manifests]
    TrainGen[Demand/cycle training generators] --> Train[Disjoint training cohorts]
    EvalGen[Demand/cycle evaluation generators] --> Eval[Disjoint held-out cohorts]
    Train --> Evaluator[Versioned evaluation]
    Eval --> Evaluator
    Dataset -. public_features_used is empty .-> Evaluator
```

### 6.2 Compatibility fixture

The original `synthetic-farm-v1` remains byte-for-byte compatible. Its contract hash is `00286779541fa9ed1245ea2aff65d08c1a05241cdc6a399706aa6601fdbc3f76`. It remains useful for UI, numerical, and regression checks. It is not used as the sole evidence for V8 model behavior.

## 7. Synthetic model evaluation

### 7.1 Cohort design

Training and evaluation use different generator names, seeds, entity IDs, farms, buyers, batches, and date ranges.

| Partition | Version | Seed | Rows | Design |
| --- | --- | ---: | ---: | --- |
| Demand training | `synthetic-demand-train-v2` | 731104 | 7,488 | 6 farms, 18 buyers, 104 weeks from 2023-01-02 |
| Demand evaluation | `synthetic-demand-evaluation-v2` | 982451 | 3,072 | 4 unseen farms, 12 unseen buyers, 64 weeks from 2025-01-06 |
| Cycle training | `synthetic-crop-cycle-train-v1` | 445901 | 576 | 6 farms × 24 cycles × 4 crops |
| Cycle evaluation | `synthetic-crop-cycle-evaluation-v1` | 771283 | 256 | 4 unseen farms × 16 cycles × 4 crops |

Demand generation includes stable, growth, and compression regimes; a 13-week pattern; bounded heterogeneity; surge and drop shocks; booking lead times; cancellations; and separate booking, cancellation, and outcome availability. Crop generation uses independent whole-batch observations with planned and actual stage dates, area, recipe baseline, measurement method, operating regime, delay shocks, and quality shocks. It does not use weather inputs or contain a weather-response coefficient.

![Cohort design showing disjoint versioned training and evaluation generators.](figures/v8/cohort-design.svg)

**Figure 1.** Synthetic cohort design generated from the current evaluation artifact. Distinct identifiers and time ranges test pipeline separation, but both partitions remain products of declared code and can share generator-design bias.

### 7.2 Rolling-origin demand method

`rolling-origin-demand-v4` evaluates farm/crop and buyer/crop series independently. For each forecast origin it supplies only dependencies whose availability timestamp does not exceed that origin. It evaluates one-, two-, and four-week horizons against last-week, 13-week seasonal-naive, fixed alpha-0.35 EWMA, and training-tuned EWMA baselines. Metrics are MAE, RMSE, WAPE, and signed bias. MAE uncertainty uses a deterministic series bootstrap with 500 replicates.

Alpha tuning uses only the training partition and freezes a cutoff of `2025-01-06T12:00:00+00:00`. Candidate alphas were 0.10, 0.20, 0.35, 0.50, 0.65, 0.80, and 0.90. The selected alpha was 0.80 based on one-step training MAE. The evaluation partition was not used for selection.

The initial dependency counter design had a structural weakness: it attempted to count late timestamps only after selecting rows already known to be on time. V4 now reports explicit included dependency auditing and adds an independent behavioral counterfactual. The counterfactual perturbs a permanently unavailable historical target and compares every resulting forecast for a held-out farm/crop and its buyers. It compared 492 farm forecasts and 1,476 buyer forecasts and changed zero. The probe status is `passed`. This supports the tested invariance; it does not prove the absence of every future feature-leakage defect.

### 7.3 Demand results

The held-out farm cohort contains 16 series and 656 predictions per model/horizon. The buyer cohort contains 48 series and 1,968 predictions per model/horizon.

| Cohort | Horizon | Best WAPE | Model | Tuned EWMA WAPE |
| --- | ---: | ---: | --- | ---: |
| Farm | 1 week | 0.048919 | tuned EWMA | 0.048919 |
| Farm | 2 weeks | 0.096992 | fixed EWMA | 0.100631 |
| Farm | 4 weeks | 0.121254 | fixed EWMA | 0.139717 |
| Buyer | 1 week | 0.061945 | fixed EWMA | 0.065245 |
| Buyer | 2 weeks | 0.093836 | fixed EWMA | 0.102266 |
| Buyer | 4 weeks | 0.140546 | fixed EWMA | 0.163816 |

The tuned candidate wins only the farm one-week WAPE comparison. The fixed EWMA performs better in the five other cohort/horizon comparisons shown. This is a useful negative result: training selection does not justify a general promotion claim even inside the synthetic benchmark. Complete metrics and bootstrap intervals are preserved in [synthetic_model_evaluation.json](../../reports/v8/synthetic_model_evaluation.json).

![Rolling-origin demand holdout comparison across farm and buyer cohorts.](figures/v8/demand-holdout.svg)

**Figure 2.** Current V4 rolling-origin synthetic demand results. The figure covers the two synthetic cohort levels and declared horizons; it contains no observed customer or farm demand.

### 7.4 Whole-batch crop-cycle method and result

The candidate adds crop-specific mean training residuals to recipe maturity and marketable-mass baselines. Features are crop ID, recipe cycle days, recipe marketable kilograms per square metre, and occupied area. Public weather, news, trade, and causal weather coefficients are excluded. The evaluation unit is an unseen farm's whole batch, not repeated measurements that could leak the same batch across splits.

| Target | Recipe baseline MAE | Residual candidate MAE | Better result |
| --- | ---: | ---: | --- |
| Fresh marketable mass | 3.722184 kg | 3.907328 kg | Recipe baseline |
| Maturity | 0.957031 days | 1.035536 days | Recipe baseline |

Training-residual 10th–90th percentile ranges covered 84.375% of held-out mass outcomes and 87.5% of held-out maturity outcomes. These are descriptive residual ranges and are not calibrated prediction intervals.

![Whole-batch crop-cycle holdout errors and descriptive interval coverage.](figures/v8/crop-cycle-holdout.svg)

**Figure 3.** Independent synthetic crop-cycle evaluation. The fitted residual candidate fails to improve the primary MAE results and is not promoted.

### 7.5 Promotion decision

The policy is `farmtact-model-promotion-v1`. Schema and split integrity passed. The point-in-time gate passed based on zero included dependency violations, split availability assertions, and the counterfactual invariance described above. Three mandatory gates remain blocked:

- no authorized real farm/customer temporal holdout exists;
- no external farm cohort exists;
- no production drift, alert, rollback, or retraining trial exists.

The report therefore records `eligible_for_production=false` and status `blocked`. No fitted demand or crop-cycle candidate has been promoted. The forecast used by the application remains the declared engineering baseline `recipe-ewma-v1`.

## 8. Council evidence architecture and actual-call inventory

### 8.1 Exact roster and workflow

The current Council is `seven-agent-council-v3` with workflow `sequential_specialists_then_chair`. Six specialists independently receive role-projected slices of the same frozen context. Only the planning chair receives the prior claims, their evidence statuses, validation issues, and eligibility flags. The implementation does not claim a free-form debate or challenge round.

| Persona | Role identifier | Bounded responsibility |
| --- | --- | --- |
| Ravi | `demand_analyst` | Booked orders, forecast demand, required crop quantities and delivery dates |
| Hana | `weather_analyst` | Observed context and freshness; no unsupported yield adjustment |
| Idris | `market_analyst` | Prices and sourced reactions; reactions are not measured demand |
| Mei | `production_analyst` | Recipes, lead times, space, and modeled feasibility |
| Lina | `supply_chain_analyst` | Inventory, expiry, inputs, and delivery timing |
| Ben | `profit_analyst` | Computed costs, labour, cash, and margins under declared assumptions |
| Asha | `planning_chair` | Reconcile eligible claims and explain the deterministic selection policy |

```mermaid
flowchart TD
    Frozen[Frozen numerical and source context] --> Project[Role-specific context projection]
    Project --> D[Demand]
    Project --> W[Weather]
    Project --> M[Market]
    Project --> P[Production]
    Project --> S[Supply chain]
    Project --> F[Profit]
    D --> Local[Schema and evidence gate]
    W --> Local
    M --> Local
    P --> Local
    S --> Local
    F --> Local
    Local --> Prior[Bounded prior claims with eligibility]
    Prior --> Chair[Planning chair]
    Chair --> Final[Execution / evidence / influence statuses]
    Final -->|withhold or unsupported| NoAccept[No Council authorization]
    Final -->|eligible advice| Policy[Still subject to server policy]
```

The normal mission budget is seven calls with up to two bounded structural repairs, for a maximum of nine. Direct and invitation workflows reserve their exact maxima separately. `RunBudget.cancel()` prevents subsequent transmission and stops bounded response consumption between transport chunks. It does not promise immediate interruption inside an already active synchronous HTTP call.

### 8.2 Typed facts and qualitative limits

V8 replaces numeric coincidence with selected `fact_refs`. The server builds a typed catalogue from frozen values and renders the value, unit, entity, period, and snapshot hash after model output. Model-authored quantities and dates are rejected even when they happen to match a value elsewhere in the context. `tool_result_refs` are restricted to qualitative context. Wrong entity, wrong unit, wrong meaning, citation laundering, and numeric prose have adversarial tests in [test_ai_injection_boundaries.py](../../tests/review/test_ai_injection_boundaries.py) and [test_ai_quality.py](../../tests/review/test_ai_quality.py).

`RESPONSE_LIMITS` is the shared prompt/schema authority: 400 content characters, one evidence reference, three context references, three typed facts, one highlight, and one proposed action. Contract versions identify prompt, output schema, validator, frozen context, and source context. New records include a public-context SHA-256 value. Earlier stored records remain readable through conservative additive defaults.

Execution status answers whether a provider workflow ran. Evidence status answers whether the returned references and typed facts passed the local checks. Decision influence answers whether policy can consider the result or must withhold. A successful HTTP response can therefore be `completed`, `unsupported_all`, and `advisory_only` at the same time. Qualitative interpretation remains `qualitative_unverified`; selecting a correct fact reference does not verify causal or agronomic prose.

### 8.3 Provider caller inventory

The fail-closed inventory in [deepseek_runtime.json](../../config/deepseek_runtime.json) contains four callers.

| Caller | Integration | Routes | Maximum | Failure semantics |
| --- | --- | --- | ---: | --- |
| Mission Council | active product | seven Council roles | 9 | visible withheld or partial |
| Persistent conversation | active product | direct, invite, Council, research interpretation | 9 | visible unsupported, partial, or failed |
| Synthetic label observer | active API | visual observer | 1 | visible missing visual evidence |
| Authenticated gateway trial | diagnostic only | demand, production, visual observer | 16 | preserved failed trial |

The gateway requires the compiled inventory and configuration to agree, restricts models to the reviewed set, verifies that the returned model ID exactly matches the requested ID, bounds request/response/image sizes and timeouts, limits concurrency to one, and records token categories where the provider supplies them. Helper or evaluator names do not imply an active caller.

### 8.4 Model migration

On 10 September 2026, DeepSeek announced V4.1-Flash, stated that it was live on the API with native multimodal support, instructed API users to select `deepseek-flash`, and retired the previous V4 Flash and Vision Experimental names; see the [official DeepSeek announcement](https://www.deepseek.com/en/news/deepseek-v4-1-flash/). The runtime's canonical model is consequently `deepseek-flash` for every current text and native-vision route. The discovery evidence is retained in [model-discovery.json](../../reports/v8/model-discovery.json). This migration statement establishes naming and routing policy; it does not prove FarmTact output quality.

### 8.5 Retained actual-provider evidence

The immutable experiment ledger records 24 actual paid requests across four runs; see [live-call-ledger.json](../../reports/v8/live-call-ledger.json).

| Experiment | Requests | Observed result | Audit interpretation |
| --- | ---: | --- | --- |
| Initial local planning Council | 1 | retired-model identity mismatch | Failed closed; run retained as incomplete |
| Canonical model with vision | 9 | native-vision path passed; five claims unsupported | Transport/capability evidence only; Council quality failed |
| V3 context/schema run | 7 | six valid outputs; one response rejected for the word `three` | Improved contract adherence, still incomplete |
| V3 format-repair run | 7 | six valid outputs; Supply Chain selected one unknown reference | Reference membership rejected locally; mission withheld |

The four counts sum to the ledger's `actual_requests_consumed=24`. The first failure demonstrates why exact returned-model validation matters. The second run demonstrates that native visual input can traverse the current route, but five unsupported outputs prevent a quality pass. The third run demonstrates six locally valid outputs, but the remaining format violation prevents complete seven-role coverage. The word `three` was rejected because the V3 prompt forbids number words in model prose and requires exact quantities to be selected through typed facts. The fourth run removed that failure mode but remained withheld because the Supply Chain response selected a reference outside its permitted frozen catalogue.

**Current status: FAILED / PENDING FURTHER QUALITY TRIALS.** No deployed-quality claim is made. The retained planning artifacts are [planning-local.json](../../reports/v8/planning-local.json), [planning-local-canonical.json](../../reports/v8/planning-local-canonical.json), [planning-local-v3.json](../../reports/v8/planning-local-v3.json), and [planning-local-v4.json](../../reports/v8/planning-local-v4.json).

## 9. Scenarios, conversations, and research state machines

### 9.1 Scenario attempts

Scenario roots are immutable tenant-owned numerical experiments. Each scenario keeps at most three append-only attempt summaries with queued, started, completed, cancellation, terminal status, and safe exception type. Retries preserve the frozen farm, baseline root, model versions, prior attempts, and original run idempotency key. A changed or stale key receives 409. An unsupported frozen version fails rather than being silently recomputed by the current model.

Cancellation atomically moves DRAFT, QUEUED, or RUNNING to CANCELLED. Queued cancelled jobs cannot be claimed. Because CP-SAT is synchronous, a running solve is observed as cancelled after the current local solve boundary; the compare-and-write guard prevents its stale result from overwriting the terminal cancellation. Scenario calculation makes no provider request.

Lists use SQL ordering and bounded `limit=1..30` with an exclusive `before` cursor. The thirty-first persisted scenario is rejected before numerical work. Idempotency lookup precedes the quota check so receipt replay still works at the limit.

### 9.2 Conversations

Conversations are independently capped at 30 per tenant and 120 messages per conversation. Admission rechecks capacity under the conversation lock, including the user message and every requested advisor turn. Queued and running requests can be cancelled through an atomic store primitive. Council execution checks cancellation before numerical context assembly, budget reservation, each initial or repair provider call, message persistence, and final completion. Cancellation is cooperative at call boundaries.

Replay preserves the original workflow type, model-call status, evidence state, decision influence, contract versions, and calculation provenance. It does not claim a new calculation or provider call. Historical records missing V8 fields receive conservative compatibility values.

### 9.3 Scripted research and challenge

Council Research is explicitly `scripted_research` with `inference_origin=local_rules` until a user requests a distinct advisor interpretation. Its dialogue can propose bounded reservations, unconfirmed-order treatment, and a 50–100% labour ceiling. Weather challenges state that outdoor rainfall is context rather than a numerical yield input for the sheltered synthetic farm. Farm time does not advance while research calculations run.

Each numerical result is tied to the research schema, forecast version, planner version, input version, and content hash. Revision history stores snapshots before mutations and exposes bounded incremental history pages. `cancel_calculation` and `retry_calculation` are separate from `stop`, which stops scripted dialogue only. A failed or cancelled current calculation can be retried up to three attempts; queued and running states cannot be duplicated. Actions require a current revision and an idempotency key.

```mermaid
stateDiagram-v2
    [*] --> Scripted: create research session
    Scripted --> Edited: select, propose, apply, challenge
    Edited --> Queued: run local calculation
    Queued --> Running: worker claim
    Queued --> Cancelled: cancel_calculation
    Running --> CancelRequested: cancel_calculation
    CancelRequested --> Cancelled: next local boundary
    Running --> Completed: version and hash valid
    Running --> Failed: safe failure record
    Failed --> Queued: retry_calculation, attempt below limit
    Cancelled --> Queued: retry_calculation, attempt below limit
    Completed --> Chosen: choose result
    Scripted --> Stopped: stop dialogue
    Stopped --> Stopped: calculation state remains independent
```

The research workflow supports comparison and provenance, but it does not establish that a proposed control is causally effective. Qualitative suggestions remain subject to the same local evidence labels when a provider is explicitly invoked.

## 10. Concurrency, tenancy, and idempotency

### 10.1 Server transaction model

The core store hashes the anonymous session bearer before persistence and scopes farm, mission, event, receipt, scenario, conversation, research, and simulation queries by tenant. PostgreSQL tenant transactions lock the tenant row to serialize state allocation. An ambient connection context lets nested event, world, and receipt writes join the same transaction. SQLite uses a serialization lock only as a test adapter; it is not the production concurrency claim.

Dedicated PostgreSQL tests used six concurrent same-key scenario retries after a forced transient failure and observed exactly one second attempt. Six concurrent scenario cancellations and six conversation-request cancellations each produced exactly one transition. The simulation concurrency result is described in Section 4.5. One pre-existing shared-database test observed a queued job become RUNNING because another live worker claimed it; the isolated V8 PostgreSQL test passed. This is why the final suite should run without unrelated workers polling the same test queue.

A later focused integration group passed 10 tests covering the SQLite background-worker serialization adapter and both queued and running research-calculation cancellation paths. This result supports those regressions in the test adapter; the production concurrency evidence remains the isolated PostgreSQL runs.

### 10.2 Client retry identity

The shared client mutation transport writes an idempotency key before transmission. Its session-storage identity includes immutable edition, HTTP method, API path, and serialized body. The key survives navigation and reload after a network error, 5xx, 408, 425, or 429 because the server may have committed even when the client lacks a response. Definitive success and definitive 4xx responses clear the pending operation. After a mutation or receipt replay the client fetches the current world, because an old exact receipt intentionally contains an older revision. Implementation is in [api.ts](../../apps/web/src/lib/api.ts) and [research.ts](../../apps/web/src/lib/research.ts).

The browser harness injected a 503 followed by a 429 and then success across page reloads. All three requests carried the same key. A later successful operation cleared it, and a deliberate 409 import response also cleared its separate pending key. This test exercises uncertainty semantics rather than merely checking storage keys.

### 10.3 Remaining persistence limits

Anonymous-session expiry blocks later authentication but does not delete persisted tenant rows. No edition-aware retention and deletion job exists. Cancellation cannot preempt a CP-SAT solve or abort an already active synchronous provider call immediately. Concurrent identical replans may compute the same local solution more than once, although revision and receipt serialization allow only one committed state.

## 11. Browser behavior and visual evidence

The Outcomes room distinguishes a static schedule preview from recorded synthetic execution. The recorded panel can create a world from the accepted current mission, advance one or seven days, display clock and revision, show bed stage and progress, list task and demand events, show inventory and delivery/harvest/cash totals, and replan future work when at least seven days remain. It states that inference was not triggered and real operations are disabled.

Capability presentation separates configured routes, historical probe evidence, current verification, and last observed tenant execution. Planning does not treat “credential configured” as “provider verified.” Council cards separately expose execution, evidence, and decision influence, and label qualitative prose unverified. Council planning remains the primary action, while numerical-only planning is an explicit alternative and was used for this browser run.

![Recorded synthetic execution at 390 CSS pixels.](../../apps/web/screenshots/v8-recorded-simulation-390.png)

**Figure 4. Mobile browser evidence at 390 × 844 CSS pixels.** The Playwright run used an isolated local PostgreSQL database, normal background worker, numerical-only mission, one-day advance, future replan, then seven-day advance. It checked the visible execution totals, event rendering, shared sanitation calendar, mission persistence across refresh, and absence of body overflow. It made zero Council inference requests.

![Recorded synthetic execution at 1280 CSS pixels.](../../apps/web/screenshots/v8-recorded-simulation-1280.png)

**Figure 5. Desktop browser evidence at 1280 × 900 CSS pixels.** This screenshot comes from the same numerical-only recorded world and the same 27-check run. The overflow assertion was repeated at 360, 390, 430, and 1280 CSS pixels. The screenshot does not show a live provider result or a real farm event.

The machine-readable [browser report](../../reports/v8/ui-browser.json) records 27 of 27 checks passing. It also records expected local `/api/releases` 404 responses plus deliberately injected 503, 429, and 409 responses. Those responses were excluded from the “unexpected failures” assertion because they are the intended retry-contract stimuli. The visible synthetic totals after the tested interactions were 54 kg inventory, 136.004 kg delivered, 190 kg harvested, $2,805 cash, $1,030 revenue, and $425 cost. These values belong only to that deterministic test world.

## 12. Verification results

### 12.1 Focused test evidence

| Subsystem | Command or artifact | Recorded result | Scope limit |
| --- | --- | --- | --- |
| Data/model/planner | focused pytest group in `reports/v8/data-ml.md` | 74 passed in 33.38 s | Synthetic and unit/integration scope |
| Planner plus adversarial contracts | focused group in `reports/v8/planner.md` | 36 passed in 61.05 s | Includes deterministic fallback paths |
| Council/gateway/offline quality | package group in `reports/v8/council.md` | 227 passed, 1 skipped, 1 PG test deselected | No live-provider quality pass |
| Council frozen subset | package group in `reports/v8/council.md` | 96 passed in 35.54 s | Bounded gate/gateway/cancel subset |
| Scenario reliability | V8 reliability unit suite | 5 passed in 3.30 s | Local service mechanics |
| Scenario/conversation concurrency | isolated PostgreSQL test | 1 passed in 2.81 s | Dedicated database/worker conditions |
| Scenario combined group | gameplay reliability group | 34 passed in 86.55 s | Focused, not whole repository |
| Simulation execution | execution unit suite | 3 passed in 7.76 s | Synthetic world behavior |
| Simulation concurrency | isolated PostgreSQL test | 1 passed in 7.38 s | Same-key, competing-key, tenant, restart-store |
| Worker/research cancellation | latest focused integration group | 10 passed | SQLite worker serialization plus queued/running cancellation |
| Restart HTTP execution | `execution-trial.json` | PASS: 56 days, one restart, zero provider calls | Deterministic synthetic execution only |
| Web build | TypeScript no-emit plus Vite | PASS | Build only |
| Browser | `v8_simulation_ui.mjs` | 27/27 PASS | Local PG, zero inference, exact journey above |
| Full regression | `full-regression.xml` | 556 passed, 1 skipped in 398.002 s | Development worktree at recorded timestamp |

These results are not additive because test sets can overlap. They should not be summed into a repository pass count.

### 12.2 Repository-wide gate

An earlier repository-wide run reported 499 passing tests and 34 failures while multiple packages were still editing generated manifests. The integration review attributed 32 failures to that concurrent manifest churn and identified two actual defects, which were fixed. The subsequent clean run completed with 557 collected tests: 556 passed, one skipped, zero failures, and zero errors in 398.002 seconds according to the XML suite timer. The authoritative machine-readable evidence is [full-regression.xml](../../reports/v8/full-regression.xml).

**Repository-wide regression gate: PASS.**

This result supports the recorded worktree and test environment. Release and deployment status remain separate decisions and should not be inferred from this test pass.

### 12.3 Test interpretation

Unit tests support schema boundaries and small deterministic cases. Exhaustive tiny planner tests support equivalence only inside their integer-gram, single-grade, single-harvest domain. PostgreSQL tests support the exact concurrent schedules they execute, not arbitrary distributed failure histories. The browser test supports the specified sizes, controls, and local topology. Actual-provider runs support observed transport and validation outcomes but do not replace human agronomic quality assessment. Synthetic model metrics compare implementations under generator assumptions and cannot estimate field accuracy.

## 13. Gap dispositions

The authoritative machine-readable register was being revised during report preparation. The following table records evidence disposition for this report without changing or predicting that register's final status.

| Gap family | Implemented evidence | Required residual evidence |
| --- | --- | --- |
| DATA-01 | Dynamic validation derives 12 crops and 24 documents | Maintain registry/source review on future changes |
| DATA-03 | Versioned report 2.0 metadata and archived pre-V8 report | Clean final regeneration after frozen revision |
| DATA-04 | Self-contained hashed CC0 synthetic source fixtures | Authorized archival store for any real source snapshot |
| DATA-05 | Empty public feature set; no weather/news/trade coupling | Pre-registered real-data ablation before adding any edge |
| DATA-06 | Typed whole-batch outcome records and split checks | Authorized real farm batches and measurement protocol |
| NUM-03 | Weights affect objective behavior and are reported | Calibrated scenario probabilities if probability language is desired |
| NUM-04 | Resilient lexicographic maximin with proof status | Stakeholder-approved service definition and risk calibration |
| NUM-05 | FEFO solver/replay alignment and order/lot attribution | Grades, buyer rules, multi-cut and eligibility schema |
| NUM-06 | Terminal stock kept distinct from waste | Observed salvage, spoilage, disposal, and post-horizon economics |
| NUM-07 | Explicit missing-price state and unpriced accounting | Current observed prices and commercial validation |
| NUM-08 | Rolling-origin multi-horizon V4 evaluator | Real temporal and external-farm holdouts |
| NUM-09 | Promotion gates block synthetic candidates | Monitoring, rollback, drift, and approved thresholds |
| GAME-08 | Bounded attempt history, cancellation, retry, and pagination | Retention/deletion policy and wider soak testing |
| GAME-11 | Tenant locks, same-key receipts, revision conflicts | Multi-process fault injection and production monitoring |
| GAME-12 | Exact computed order delivery impacts | Buyer/grade/customer-priority contract expansion |
| Execution world | Durable clock, events, ledgers, replanning | Completed restart HTTP artifact and negative-cash resolution |
| AI-01/02 | Typed facts and independent local quality dimensions | Successful full live quality suite plus expert scoring |
| AI-03/12 | Execution/evidence/influence split | Validate comprehension with planned human study |
| AI-04 | Configured, historical, and observed statuses separated | Fresh successful explicit execution after quality fixes |
| AI-05/06 | Fail-closed caller inventory and bounded budgets | Dated cost controls and deployment reconciliation |
| AI-07 | Canonical harvest references and value status | Real measured outcome provenance |
| AI-08 | Truthful six-specialists-then-chair workflow | Measure incremental utility before adding challenge calls |
| AI-09/10/11 | Shared limits, rejection projection, version/hash provenance | Complete seven-role live conformance result |
| UX-01 | Recorded/static distinction and responsive controls | Planned human usability/accessibility study |
| OPS-01 | Local PG and build evidence | Final suite, immutable edition, deployment and post-deploy checks |

## 14. Scientific and operational limitations

### 14.1 Synthetic data validity

Every demand and crop-cycle target in V8 evaluation is generated. Independent seeds and cohorts prevent direct identity overlap, but they do not remove shared design assumptions. A model structurally similar to the generator can look favorable for the wrong reason. No score in this report estimates performance on an operating farm.

### 14.2 Biological scope

The schedule helper is a civil-date state machine, not a physiological growth model. Marketable mass uses recipes and declared scenario factors rather than measured light, nutrient, temperature, pest, cultivar, or operator effects. Crop intervals are descriptive synthetic residual ranges. No weather causal coefficient exists.

### 14.3 Demand and commercial scope

The private schema lacks buyer identity on orders, substitution, stockout-censoring state, grade, contract priority, and realized loss records. The demand forecast therefore cannot be described as buyer behavior modeling for a real operation. Missing current prices are made visible, but the system has no real pricing feed. Policy utility is not expected profit.

### 14.4 Optimization scope

The planner uses whole beds, integer grams, one grade, single-harvest lots, and declared scenario factors. It lacks split-bed, multi-cut, water, energy, packaging-capacity, rotation, substitution, partner-supply, and lot/customer eligibility constraints. Bounded CP-SAT `FEASIBLE` status does not prove global optimality. Scenario weights are not probabilities.

### 14.5 Execution scope

Execution replays the deterministic plan and central synthetic scenario. Events do not actuate equipment, assign a worker, send a buyer message, purchase an input, or record an observed harvest. The cash hard constraint does not yet cover every execution cost. The passed restart-safe 56-day HTTP protocol strengthens persistence evidence but remains a local synthetic trial.

### 14.6 AI scope

Typed rendering prevents a model from altering selected values, but it cannot make qualitative interpretation true. The current live quality status is failed. Vision transport success is not agronomic visual validation. Two later trials each produced six locally valid responses but still did not achieve complete Council coverage. No additional paid calls were made for this report.

### 14.7 Operations and privacy scope

The session is an anonymous tenant, not an authenticated farm user. Expired records lack a deletion policy. Focused local PostgreSQL concurrency does not prove behavior under every network, process, database failover, or deployment condition. The final repository suite and deployment decision are pending.

## 15. Evidence required before stronger claims

Real demand evaluation requires authorized order-line history containing farm, buyer/SKU, booking, modification, cancellation, due, delivered, stockout, substitution, and availability timestamps. The evaluation protocol must freeze farm and buyer sampling, temporal splits, censoring policy, metrics, acceptance thresholds, and subgroup checks in advance.

Real crop evaluation requires independent batch records containing recipe and cultivar versions, sow/transplant/harvest and sanitation events, occupied area and system, fresh harvested mass, marketable mass by grade, packout, losses, measurement method, and availability timestamp. The current [outcome collection protocol](../research/v8-outcome-collection-protocol.md) is a protocol proposal, not a collected dataset.

Public weather or market context may enter a numerical model only after units, farm exposure, spatial mapping, and point-in-time availability are resolved and a pre-registered ablation improves an authorized real holdout. That analysis must distinguish prediction from causation.

AI promotion requires a complete current-model trial across direct, invitation, Council, vision where applicable, and research interpretation workflows. The retained report must include every request, repair, usage record, local issue, and failed output. Agronomic usefulness and harm must then receive independent human scoring under the [human study protocol](../research/v8-human-study-protocol.md).

Operational release requires the successful build and regression evidence already recorded plus edition immutability checks, database migration checks, deployment health checks, and a documented rollback target. The zero-AI execution HTTP trial now supplies local restart evidence. None of these steps enables real farm operations under the present policy.

## 16. Reproducibility map

| Purpose | Primary source or artifact |
| --- | --- |
| Private contracts and recipe calendar | [contracts.py](../../packages/contracts.py) |
| Canonical civil-date stages | [growth.py](../../packages/growth.py) |
| Compatibility and benchmark generators | [fixtures.py](../../packages/fixtures.py) |
| Public fixture installation and validation | [packages/ingestion](../../packages/ingestion/) |
| Feature/forecast contract build | [build_features.py](../../scripts/build_features.py) |
| Data rebuild entry point | [build_dataset.py](../../scripts/build_dataset.py) |
| Demand and crop evaluation | [evaluation.py](../../packages/models/evaluation.py) |
| Synthetic evaluation command | [evaluate_synthetic_models.py](../../scripts/evaluate_synthetic_models.py) |
| Synthetic evaluation result | [synthetic_model_evaluation.json](../../reports/v8/synthetic_model_evaluation.json) |
| Numerical evaluation result | [numerical_evaluation.json](../../reports/v8/numerical_evaluation.json) |
| Planner | [engine.py](../../packages/planner/engine.py) |
| Replay accounting | [accounting.py](../../packages/planner/accounting.py) |
| Simulation worlds and events | [simulation.py](../../services/api/simulation.py) |
| Scenario state machine | [scenarios.py](../../services/api/scenarios.py) |
| Core transactional store | [store.py](../../services/api/store.py) |
| Conversation persistence | [conversation_store.py](../../services/api/conversation_store.py) |
| Research state machine/history | [council_research.py](../../services/api/council_research.py) |
| Council orchestration | [council.py](../../services/api/council.py) |
| Council roster and gate | [agents.py](../../packages/agents.py) |
| Typed fact contract | [ai_contracts.py](../../packages/ai_contracts.py) |
| Offline quality scorer | [ai_quality.py](../../packages/ai_quality.py) |
| Provider policy and transport | [deepseek_gateway.py](../../runtime/deepseek_gateway.py) |
| Provider caller manifest | [deepseek_runtime.json](../../config/deepseek_runtime.json) |
| Client mutation transport | [api.ts](../../apps/web/src/lib/api.ts) |
| Recorded execution panel | [SimulationPanel.tsx](../../apps/web/src/components/SimulationPanel.tsx) |
| Browser method | [v8_simulation_ui.mjs](../../tests/browser/v8_simulation_ui.mjs) |
| Browser result | [ui-browser.json](../../reports/v8/ui-browser.json) |
| Restart execution result | [execution-trial.json](../../reports/v8/execution-trial.json) |
| Full regression result | [full-regression.xml](../../reports/v8/full-regression.xml) |
| Execution concurrency method | [test_v8_simulation_postgres.py](../../tests/gameplay/test_v8_simulation_postgres.py) |
| Scenario/conversation reliability report | [game-reliability.md](../../reports/v8/game-reliability.md) |
| UI evidence report | [ui.md](../../reports/v8/ui.md) |
| Data/ML evidence report | [data-ml.md](../../reports/v8/data-ml.md) |
| Planner evidence report | [planner.md](../../reports/v8/planner.md) |
| Council evidence report | [council.md](../../reports/v8/council.md) |
| Execution evidence report | [execution-validation.md](../../reports/v8/execution-validation.md) |

The numerical report used a deterministic zero-second fallback and records `daily-bed-cpsat-v2`, `recipe-ewma-v1`, fixture hash, settings, cutoff, source revision, dirty state, report schema, and public feature exclusions. Bounded CP-SAT wall time, objective, and best bound can vary with solver build and runtime when a positive time limit is used. The archived pre-V8 report remains at [numerical_evaluation.pre-v8.json](../../reports/v8/archive/numerical_evaluation.pre-v8.json).

## 17. Conclusions and pending decisions

V8 materially improves the fidelity of FarmTact's synthetic planning experiment. The implementation now connects an accepted plan to a durable, revisioned execution world whose clock, tasks, lots, orders, costs, and replans can be inspected. Weighted objectives, maximin proof labels, FEFO replay, explicit missing-price state, terminal inventory, and exact order attribution remove several important ambiguities from the numerical layer.

The data and model work also improves the honesty of evaluation. Disjoint generators and cohorts, rolling origins, multiple horizons, whole-batch outcomes, fit cutoffs, and a counterfactual availability probe provide useful engineering tests. Their current result supports no fitted-model promotion, and the promotion policy correctly blocks production eligibility.

The Council architecture has stronger provenance and safer local validation. Its current actual-provider evidence nevertheless fails the quality gate. The canonical `deepseek-flash` migration is implemented, but five unsupported outputs in the vision run, one V3 format rejection, and one later unknown-reference rejection leave the complete workflow unvalidated.

The remaining integration decisions are evidence-driven and explicit:

- **PASS:** repository-wide regression, 556 passed and one skipped;
- **PASS:** retained 56-day restart-safe zero-inference HTTP execution trial;
- **FAILED / REMEDIATING:** complete actual DeepSeek Council quality suite;
- **BLOCKED:** any production model promotion without authorized real outcomes;
- **DISABLED:** all real farm operations.

This report is therefore a reproducible V8 engineering assessment and limitation record, not a deployment certificate, agronomic validation, or operational authorization.
