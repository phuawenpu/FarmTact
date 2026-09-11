# Implementation gaps and next-iteration acceptance criteria

**Audit:** 11 September 2026, source baseline `a96025e`; deployed v7 remains frozen.
This register records observed implementation gaps and scientific limitations. The
proposed changes are **requirements for future work**, not fixes implemented by
this documentation update. P0 means address before making the affected correctness
claim or using the feature as reliable evidence; it does not mean real farm
operations are enabled. P1 improves the next demonstration; P2 requires a separately
validated data/research expansion.

Source detail: [Council/provider audit](ai-provider-and-council.md),
[numerical audit](numerical-models-and-growth.md),
[game backend audit](game-backend-and-state-machines.md), and
[data architecture audit](system-data-and-evidence.md).

## 1. Council, evidence and provider behavior

| ID / priority | Observed gap and source | Required next behavior / acceptance evidence |
| --- | --- | --- |
| AI-01 / P0 | Both v7 actual adviser probes remain unsupported; transport/replay success is not answer-quality success. [Local](../../reports/v7/advisor_local.json), [public](../../reports/v7/advisor_public.json). | Build frozen, expert-reviewable cases with expected references and permissible conclusions. Evaluate role relevance, unsupported quantities, contradictions, abstention and useful answers separately from HTTP/schema success. Preserve all failed attempts and per-case usage. Do not hide unsupported replies or use them to accept a plan. |
| AI-02 / P0 | Reference membership and numeric-value matching do not prove that cited evidence entails a sentence. [Claims](../../services/api/council.py), [conversation validation](../../services/api/conversations.py). | Represent quantitative assertions as typed reference/value/unit/entity/period relations and render those values from code. Test wrong crop/date/unit/sign, a correct number attached to the wrong meaning, fabricated causal claims and citation laundering. Qualitative statements retain an explicit unverified status unless independently supported. |
| AI-03 / P1 | Three mechanisms share “council” language: precomputed planning findings, bounded conversation turns and scripted research dialogue. | Expose workflow type, inference origin, model/call status and whether a new calculation occurred. Tests must distinguish a script, fixture, actual completion, stored actual replay, failed provider call and numerical-only result. No invented tool or agent activity. |
| AI-04 / P0 | Capability `verified` is derived from archived trial JSON plus key presence for text; vision uses archived success. [views.capabilities](../../services/api/views.py). | Return historical probe date/model/source, configured/not-configured state and last observed execution separately. Missing/aged/account-mismatched evidence must not claim current verified access. Test old reports, no key, missing model and failed last execution without triggering paid background probes. |
| AI-05 / P1 | Registered helper, evaluator and vision role names exceed actual integrated call sites. [Runtime manifest](../../config/deepseek_runtime.json). | Maintain a machine-readable route-to-caller/feature inventory. Distinguish available server capability from active product integration. A new helper/evaluator requires caller, prompt/schema version, finite budget, test, egress review and visible failure semantics. |
| AI-06 / P1 | Per-run request and reserved-output limits plus shared call counts do not establish a hard USD spending cap or strict end-to-end cancellation. [Gateway](../../runtime/deepseek_gateway.py). | Add conservative total-cost reservation with dated price metadata if a monetary guarantee is required; report input/output/cache/reasoning accounting. Test timeout/cancellation during transport and between turns, midnight reconciliation and multi-edition concurrency. Do not automatically retry potentially billed interrupted generations. |
| AI-07 / P1 | Crop-harvest forecast emits `marketable_kg`; the conversation reference builder expects `expected_kg`, omitting that forecast mass reference. [Forecast](../../packages/models/__init__.py), [context builder](../../services/api/conversations.py). | Adopt one shared typed harvest record and reference generator. Assert that every forecast batch/date/marketable-mass field is available with the same value, unit and frozen snapshot hash in adviser context. Preserve existing batch-level references during migration. |


| AI-08 / P1 | Mission specialists see the same frozen tools but not one another's findings; only the chair sees previous validated/rejected findings. No two-round challenge protocol exists. | Preserve this truthful sequential contract or implement explicit challenge targets, turn/round budgets, stop states and evidence updates. Test which prior findings and rejection reasons each role receives; measure usefulness against the simpler existing chain. |
| AI-09 / P1 | Conversation prompts request tighter response limits than `AdvisorReply` enforces (400 versus 900 characters and lower reference/action counts). | Put one bounded response contract in the schema and generate prompt instructions from it. Test limits at and just beyond every boundary; distinguish structural repair from unsupported-claim handling. |
| AI-10 / P1 | Conversational chair sees prior `validation_status` but its context projection omits detailed `validation_errors`; mission chair receives rejection reasons. | Define a bounded shared validated-message projection with explicit error categories and test that later roles cannot treat rejected/unsupported statements as evidence. |
| AI-11 / P1 | Per-call records lack a complete explicit prompt/schema/validator version set; roster version alone cannot identify prompt behavior. | Persist prompt-template, output-schema, validator, numerical/context and source versions with every completion and replay export. Demonstrate reconstruction of the sent public context without persisting private reasoning. |
| AI-12 / P1 | A persistent conversation request may be `COMPLETED` while every reply is unsupported; a valid mission claim can withhold selection through its `recommendation` field. | Expose execution status, evidence status and decision influence separately. Test all-successful transport with unsupported answers, partial failures and a single veto; compare with a numerical-only run on identical inputs. |

Council-specific chain, validation and budget gaps are analyzed in the
[AI chapter](ai-provider-and-council.md). The game's challenge/proposal/acceptance
state gaps are separately identified as `GAME-*` in the
[backend chapter](game-backend-and-state-machines.md); those are part of this
register's next-iteration scope and must not be lost in a provider-only assessment.

## 2. Crop development, optimization and simulation

| ID / priority | Observed gap and source | Required next behavior / acceptance evidence |
| --- | --- | --- |
| NUM-01 / P0 | Backend marks batches ready at/after harvest; standalone frontend preview makes beds empty at/after harvest. Neither exposes sanitation occupancy. [views](../../services/api/views.py), [World](../../apps/web/src/components/World.tsx). | Define one versioned crop-cycle state contract for nursery, growing, ready, harvested, sanitation and available, distinguishing planned versus recorded events. Test every day around transplant, harvest and sanitation end, with/without accepted overlays and delayed batches. UI availability must agree with planner occupancy. |
| NUM-02 / P1 | Preview slider includes `planning_date + horizon_days`, one day beyond the final planner index. | Use the same inclusive horizon contract everywhere. Test a 7-, 56- and 84-day horizon, date labels, exports and final-day inventory. |
| NUM-03 / P1 | Three scenario weights are stored but not consumed by the solver; seed produces no random draws. [models](../../packages/models/__init__.py), [engine](../../packages/planner/engine.py). | Either enforce equal-weight-only configuration explicitly or consume validated normalized weights. Demonstrate changed weights affect a constructed optimum; report scenario provenance. Rename/remove unused random-seed semantics until stochastic sampling exists. |
| NUM-04 / P1 | “Resilient” increases shortage penalties; it is not maximin, CVaR or a low-yield service guarantee. The objective is policy-weighted utility, not literal expected net profit. | Publish objective terms and units. If downside protection is the desired product contract, implement an explicit risk/service constraint with infeasibility reporting. Test trade-offs on small enumerated cases and compare all policies on the same baseline. |
| NUM-05 / P0 | CP-SAT inventory age buckets do not explicitly require FIFO; the reporting simulator uses FIFO. This is an unproven equivalence, not a demonstrated failing numerical case. | Prove equivalence for the supported domain or align both allocation rules. Enumerate small perishability cases and reconcile delivered mass, expiry, revenue and selected objective against replay. Keep this classified as a validation gap until a counterexample or proof exists. |
| NUM-06 / P1 | General terminal stock value/penalty is absent; horizon truncation can affect the preference for unconsumed stock. | Declare terminal treatment and test horizon extension, late harvest, salvage assumptions and expiry beyond the horizon. Never classify all closing stock as physical waste. |
| NUM-07 / P1 | Residual demand with no booked line in its week is assigned zero price. Fulfilment is by crop/date, not individual buyer/order/grade. | Make missing prices explicit and distinguish requested, booked and delivered quantities. Add buyer-level allocation only with corresponding schema/priority rules; test scarce stock with multiple prices and cancellation states. |
| NUM-08 / P2 | No fitted maturity/yield/growth/quality/weather-response model; delay/yield shocks are direct inputs without biological coupling. | Collect independent crop-cycle outcomes and availability timestamps. Compare recipe baselines with candidate models on whole-batch temporal holdouts; report timing/yield errors and interval coverage. No model promotion from synthetic accuracy alone. |
| NUM-09 / P2 | EWMA is constant-level and tested only on patterned fictional history; no calibrated demand distribution. | Rolling-origin multi-horizon real-order evaluation with last-week and seasonal baselines, leakage checks and stockout/cancellation handling. Separate farm/buyer cohorts and report uncertainty in validation estimates. |
| NUM-10 / P2 | Whole-bed, single-harvest assumptions omit water, energy, HVAC, seed, packaging, grade, rotation, multi-cut, partner supply and buyer-level contracts. | Maintain a supported-constraint registry. Extend schema, validator, solver, replay and UI together for each capability. In particular, multi-cut crops require persistent occupied capacity and regrowth states, not another single-cut recipe. |

## 3. Evidence, provenance and engineering reproduction

| ID / priority | Observed gap and source | Required next behavior / acceptance evidence |
| --- | --- | --- |
| DATA-01 / P0 | Quality builder hard-codes 10 profiles/20 publications; current registries contain 12/24. [validation.py](../../packages/ingestion/validation.py). | Derive coverage counts from validated input registries, version manifests and fail on contradictory totals. Preserve old release reports as dated artifacts rather than rewriting them as current evidence. |
| DATA-02 / P1 | `integrated_demo.py` still expects 10 crops, while the catalogue contains 12. | Derive expected coverage from a versioned manifest and distinguish recipe count from knowledge count. An integrated run must pass without weakening tests to accept arbitrary missing crops. |
| DATA-03 / P1 | The checked-in numerical report has `evaluation_scope` metadata that its current generator does not emit. | Add a versioned report schema and generator check. Regeneration must preserve cohort, settings, fixture hash, cutoff, model versions and explicit synthetic-only conclusions. Archive before replacing evidence; report solver nondeterminism where applicable. |
| DATA-04 / P1 | Ignored raw/public cache files prevent an exact historical rebuild from Git alone. | Produce a licensed, integrity-checked snapshot bundle or clearly offer transform-only reproduction. Compare source byte hashes and availability cutoffs; a new live fetch is a new dataset version. |
| DATA-06 / P1 | Fresh offline game checks fail because `test_seven_current_advisors_and_frozen_create_idempotency` assumes an ignored NEA D04 cache is present (`source:D04.summary`). | Give offline tests explicit bounded source fixtures or assert the documented missing-source state; keep real-source integration checks separate. A clean checkout must pass its declared offline group without fetching current data to satisfy a fixture assertion. |
| DATA-05 / P1 | Citation/source presence does not validate numerical crop coefficients; public sources are contextual only. | Preserve `public_features_used=[]` until an explicit feature path and point-in-time validation exist. Any new weather/News/market numerical effect needs units, availability, exposure mapping, ablation and evidence of predictive benefit. |
| OPS-01 / P1 | Python egress policy is not an OS/network enforcement boundary; a single host shares availability across editions. | Before operational promotion, validate infrastructure egress controls and recovery on an isolated environment. Exercise provider denial and database restore, not only static string scans or volume existence. |
| UX-01 / P1 | AI/headless walkthroughs do not establish human usability or agronomic decision benefit. | Pre-register a small task-based human study with novice and relevant practitioner groups, clear synthetic framing, task success, time, error and comprehension outcomes. Do not infer benefits from animated dialogue or agent agreement. |

## 4. Proposed bounded implementation sequence

1. **Restore semantic consistency:** AI-04, AI-07, NUM-01/02, DATA-01/02/03 and the
   concrete game-state inconsistencies in `GAME-*`. These improve truthful status,
   synchronized state and reproducible evidence without pretending to improve biology.
2. **Make the council useful and inspectable:** AI-01/02/03 and the Council backend
   gaps. Test interpretations against fixed quantities and explicit unresolved
   assumptions; make proposal → apply → calculation → compare → selection observable.
3. **Strengthen numerical acceptance:** NUM-03/04/05/06/07 with enumerated small
   examples, explicit policy semantics and objective/replay reconciliation.
4. **Evaluate people and data:** UX-01 and NUM-08/09/10 only with appropriate
   observed data and research design. Keep operational integrations disabled.

This is a recommended scope order, not authorization to publish a release as part
of the documentation task. An implementation release must use the next unused
immutable edition and retain previous editions' source/image and state.
