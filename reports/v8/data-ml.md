# V8 data synthesis and model-pipeline remediation

Date: 11 September 2026  
Scope: DATA-01, DATA-03, DATA-04, DATA-05, NUM-08 and NUM-09  
Execution: local deterministic calculations only; no LLM or paid inference

## Result

The data and evaluation pipeline now has a clean-checkout offline path, versioned
report schemas, independent synthetic train/evaluation cohorts, rolling-origin
multi-horizon demand benchmarks, typed whole-batch crop-cycle outcomes and hard
production-promotion gates. The work does **not** claim a validated farm model.

The original `synthetic-farm-v1` output was kept byte-for-byte compatible. Its
contract hash remains
`00286779541fa9ed1245ea2aff65d08c1a05241cdc6a399706aa6601fdbc3f76`.

## Data coverage and reproducibility

`packages/ingestion/validation.py` now reads and validates the crop and evidence
registries. It derives 12 crop profiles and 24 evidence documents together with
the registry versions and source-file SHA-256 digests. A rebuild fails if a
manifest declares contradictory coverage. The old
`data/reports/data_quality.json` remains unchanged as historical evidence of the
8 September build; new manifests contain the current, derived coverage.

The checked-in `data/fixtures/public_context_v1` bundle contains six small,
project-authored synthetic provider-contract payloads under CC0-1.0. Every source
file has a declared byte count and SHA-256 digest. The installer rejects changed
bytes and unsafe paths, runs the normalizers without network access and labels all
sources `synthetic_contract_fixture`. It does not redistribute the archived
SingStat/NASA response bodies whose reuse was not verified.

The offline verification produced 24 traceable normalized rows (six weather
observations, 17 forecast rows and one trade-contract row). Installing the bundle
and rebuilding from its content-addressed snapshots produced identical dataset
IDs, row counts and normalized artifact hashes. Evidence is in
`reports/v8/data_pipeline_verification.json`.

`scripts/build_features.py` emits feature schema 1.1, forecast contract version
2.0.0 and explicit price-status counts. `public_features_used` remains empty.
Weather, News and trade values have no path into demand or harvest quantities.

## Synthetic benchmark design

The original 12-week repeating fixture remains available for UI and compatibility
tests. A separate benchmark now exercises substantially different conditions:

| Partition | Generator | Records | Cohorts and dates |
| --- | --- | ---: | --- |
| Demand training | `synthetic-demand-train-v2` | 7,488 | 6 farms, 18 buyers, 104 weeks beginning 2023-01-02 |
| Demand evaluation | `synthetic-demand-evaluation-v2` | 3,072 | 4 unseen farms, 12 unseen buyers, 64 weeks beginning 2025-01-06 |
| Crop-cycle training | `synthetic-crop-cycle-train-v1` | 576 | 6 farms × 24 cycles × 4 crops |
| Crop-cycle evaluation | `synthetic-crop-cycle-evaluation-v1` | 256 | 4 unseen farms × 16 cycles × 4 crops |

Demand records include stable/growth/compression regimes, a 13-week pattern,
bounded stochastic heterogeneity, declared surge/drop shocks, booking lead times,
cancellations and separate booking/cancellation/outcome availability timestamps.
The partitions use different seeds, generator versions, IDs and date ranges.

Crop-cycle records are independent whole-batch observations with planned and
actual stage dates, input/outcome availability, area, recipe baseline, observed
fresh marketable mass, measurement method, operating regime and explicit
delay/quality shocks. Their generator has no weather inputs or weather-response
coefficient.

## Evaluation behavior

The demand evaluator tunes EWMA alpha using the training partition only, then
freezes it for evaluation. It compares last-week, 13-week seasonal-naive, fixed
alpha-0.35 EWMA and tuned EWMA at 1, 2 and 4 weeks. It runs separate farm/crop and
buyer/crop series, respects as-of booking and cancellation visibility, and reports
MAE, RMSE, WAPE, bias and deterministic series-bootstrap 95% intervals. Both
cohort paths reported zero availability leakage violations.

Selected synthetic results illustrate why a candidate is not automatically
promoted. At the farm cohort level, tuned EWMA had the best one-week WAPE (4.89%),
but fixed EWMA was better at two and four weeks (9.70% and 12.13%). At the buyer
cohort level, fixed EWMA also beat the training-tuned candidate at all three
horizons. The selected alpha was 0.8. These comparisons measure behavior against
generated targets and are not accuracy estimates for a farm.

For crop cycles, the candidate adds crop-specific mean training residuals to the
recipe baseline. It did not consistently improve the held-out synthetic cohort:
marketable-mass MAE was 3.907 kg versus 3.722 kg for the recipe baseline, and
maturity MAE was 1.036 days versus 0.957 days. Descriptive 10th–90th-percentile
residual intervals covered 84.38% of synthetic mass outcomes and 87.50% of
synthetic maturity outcomes. These are descriptive ranges, not calibrated
probabilities.

The promotion policy always requires real-farm temporal validation, an external
farm cohort, and operational monitoring/rollback evidence. All three are blocked;
`eligible_for_production` is false. Full evidence is in
`reports/v8/synthetic_model_evaluation.json`, with compact source manifests in
`data/manifests/synthetic_benchmark_manifest.json`.

## Forecast and report contracts

`forecast()` keeps its existing call signature and `recipe-ewma-v1` algorithm
identifier. Forecast contract 2.0 adds:

- `price_status=booked_weighted_average` for a date with booked lines;
- `price_status=unavailable_no_booked_price` when the compatibility numeric value
  remains zero but zero is not an observed market price;
- typed harvest `value_status`, `observed` and `unit` fields while retaining
  batch ID, crop ID, harvest date, `marketable_kg`, endpoint and origin.

The root numerical evaluation now validates against
`farmtact-numerical-evaluation-2.0.0`. It includes report identity, run time,
source revision/dirty state, complete fixture/generator/model/settings/cutoff
metadata, cohort and target scope, solver reproducibility notes, public-feature
exclusion and a synthetic-only promotion status. The former report is preserved
unchanged at `reports/v8/archive/numerical_evaluation.pre-v8.json`; the new report
is written to both `reports/numerical_evaluation.json` and
`reports/v8/numerical_evaluation.json`.

## Checks run

```bash
.venv/bin/python scripts/evaluate_synthetic_models.py
.venv/bin/python scripts/evaluate_synthetic_models.py --check
.venv/bin/python scripts/evaluate_numerical.py --time-limit 0
.venv/bin/python scripts/evaluate_numerical.py --check
.venv/bin/python scripts/verify_data_pipeline.py
.venv/bin/python -m pytest -q \
  tests/models/test_synthetic_evaluation.py \
  tests/data/test_fixture_reproducibility.py \
  tests/data/test_ingestion.py \
  tests/contracts/test_features.py \
  tests/models/test_explorer_numerics.py \
  tests/contracts/test_private_data.py
```

The combined focused data/model/planner run passed 74 tests in 33.38 seconds.
The numerical report used the deterministic
zero-second fallback path; bounded CP-SAT runs can vary in wall time, objective
and bound with runtime and solver build, and the report says so explicitly.

## Data required before any real model claim

A real evaluation needs authorized order-line history with farm, buyer/SKU,
booking, modification, cancellation, due, delivered, stockout/substitution and
availability timestamps. It also needs independent batch records with recipe and
cultivar versions, stage events, occupied area/system, harvest/grade/packout
measurements, measurement method and availability timestamps. Farm and buyer
sampling, temporal splits, stockout-censoring policy, loss function, acceptance
thresholds and subgroup review must be frozen before evaluation.

Weather or other public context can be considered only after time-of-availability,
farm-exposure and units are resolved and an ablation demonstrates predictive
benefit on those real holdouts. No present artifact supports a causal weather
coefficient, automated public-data coupling or operational crop decision.
