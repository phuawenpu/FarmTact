# FarmTact data and model inventory

Updated 11 September 2026. For equations, call paths, backend state machines and
known implementation gaps, read the [scientific report](technical/README.md).

The current game combines a deterministic fictional farm, simple statistical
baselines, constrained optimisation and pretrained DeepSeek models. There is no
model trained or fine-tuned on real FarmTact farm/customer records.

The published v7 and current v8 candidate crop catalogue has twelve evidence-linked knowledge profiles. Garlic chives
and sawtooth coriander add research and original illustrations, not additional
simulation recipes. See [their evidence review](research/v6_crop_evidence.md).
Each published edition retains its own database/cache subtree on the shared host.

## Synthesized data

`packages/fixtures.py` creates the same versioned fictional farm from its cutoff:

| Records | Default fixture |
| --- | --- |
| Growing beds | 16 beds of 20 m² each; 320 m² total |
| Crop recipes | Caixin, pak choi, kailan and lettuce, with assumed timings, densities, yields, labour, costs and shelf life |
| Active crop batches | 8 batches linked to real fixture bed IDs and scheduled sow/transplant/harvest dates |
| Future customer orders | 32 orders: four crops × eight weeks, with fabricated quantities and selling prices |
| Historical demand | 48 weekly observations: four crops × twelve weeks, produced by a simple deterministic formula |
| Available resources | 2,560 nursery sites, 32 labour hours/week and SGD 2,200 cash |
| Opening inventory | A 5 kg caixin lot with declared harvest/expiry dates |

These are engineering assumptions, not observations, commercial recipes or
estimates learned from research papers. Scenario branches make frozen copies and
change delay, yield, demand, labour or cash. Their allocations, delivery quantities,
waste, costs and margins are model-generated simulation outputs.

The feature builder writes 32 default crop/week rows to `features.parquet`, with
cutoffs, input hashes and dependency references. It excludes information not
available at the planning cutoff. Synthetic batch-label images are also generated
for the vision capability test. Advisor dialogue/replay is recorded model output,
not training labels or scientific evidence.

V8 also includes a separate generated benchmark: six training farms and four
unseen evaluation farms for demand, plus independent whole-batch crop-cycle
cohorts. Seeds, IDs, date ranges and generator versions differ between partitions.
This benchmark evaluates candidate behavior only; none of its targets is a real
farm observation.

## Real and curated data

The recorded public-data build has 200 traceable normalized rows from seven
sources: NEA rainfall/temperature/humidity, NEA 24-hour/four-day forecasts, selected
SingStat vegetable trade volumes, and NASA POWER historical climate. These are
captured public observations/forecasts, not synthesized farm records. Freshness
and availability gaps remain visible; the recorded row count is not a claim that
all values remain current. SingStat trade is not individual-buyer demand and NASA
grid values are not on-farm sensor measurements.

The twelve-crop catalogue and twenty-four publication records are curated reference
metadata. The broader source registry includes sources that are merely discovered; the
seven above describe the original recorded public-data build. V5 added a separate
bounded News cache with explicit source dates and missing community feeds. These
registries do not create crop-specific training labels or validate demo yields.

Public context is displayed to users/advisors but is **not currently a numerical
forecast feature**. The feature manifest explicitly records `public_features_used=[]`.

## Systems actually in use

| System | Method and scope |
| --- | --- |
| Demand baseline | Exponentially weighted moving average, alpha 0.35, over available historical weekly orders. Confirmed orders are retained; only remaining expected demand is added, avoiding double counting. |
| Harvest baseline | Recorded schedule dates and assumed fresh marketable batch yields. Future yield is bed area × declared recipe yield. There is no learned growth or weather-response model. |
| Planner | OR-Tools CP-SAT chooses whole-bed crop schedules under lead-time, bed/nursery occupancy, labour, cash and inventory constraints. Lean/Balanced/Resilient use different declared objectives and resource allowances. A deterministic backward-scheduling fallback is available. This is optimisation, not a trained ML model. |
| Risk comparison | Declared stress scenarios carry validated weights consumed by the objective. Resilient uses a lexicographic worst-scenario aggregate fill floor before its utility tie-break. Scenarios and weights remain engineering assumptions, not learned probabilities or per-order guarantees. |
| Advisors | The v8 candidate routes every current role through exact canonical `deepseek-flash`. Product callers are enumerated separately from diagnostic routes. There is no FarmTact fine-tuning or automatic retraining. |
| Vision capability | The reviewed native-vision route uses the same canonical model to read a generated synthetic FT batch label and the server checks it exactly. It does not detect crop disease, estimate biomass, or assess plant health. |

The deployed forecast remains alpha-0.35 `recipe-ewma-v1`. V8 separately compares
last-week, seasonal-naive, fixed EWMA and training-tuned EWMA over independent
generated cohorts at several horizons, and compares a crop-residual candidate with
the recipe harvest baseline. Candidate gains were inconsistent and every production
promotion gate is blocked. See [the data/ML package report](../reports/v8/data-ml.md).
There is no deployed supervised crop model, satellite predictor, trained demand
regressor, disease classifier or production model-retraining pipeline.

Implementation evidence: `packages/fixtures.py`, `packages/models/__init__.py`,
`packages/planner/engine.py`, `scripts/build_features.py`,
`reports/numerical_evaluation.json`, and `reports/agents/data_foundation.md`.

## Interactive Data Explorer

The Data page now has authenticated, tenant-scoped explorer interfaces under
`/api/v1/data-explorer`. The reference fixture, each main-farm version, immutable
saved playgrounds and frozen scenario branches are separate selections. Tables,
features and forecasts are built from the selected snapshot; the explorer never
reads the global private feature build as a tenant's data.

The generation playground uses `synthetic-farm-v1`. For zero-based crop index `c`
and observed week index `w` (0–11), historical kilograms are:

```
(27 + c × 2 + (w mod 4) × 2 × amplitude)
    × history_multiplier × (1 + history_trend × w / 11)
```

At default settings all original records and the original fixture hash are
preserved. The four-week repeating pattern is an engineering assumption, not
measured seasonality. Order quantities and prices have separate multipliers;
recipes, 16 beds, 12 historical weeks and eight future weeks stay fixed.

`recipe-ewma-v1` supports a validated alpha from 0.05 to 0.95, default 0.35.
It initializes from the first available historical value and folds subsequent
values using `alpha × value + (1−alpha) × previous`. Confirmed orders are retained;
only the positive remainder over the weekly booked total is added at week end.
The saved snapshot freezes the actual forecast, inputs, settings, generator and
forecast versions, planning cutoff, hashes and original reference. Persisted
forecasts replay without recomputation. Hash validation rejects corrupted saved
inputs or forecasts. Worker jobs reject unsupported frozen numerical versions.

Saved playgrounds use the original generated dataset at default alpha as their
comparison baseline. Child delay/yield/demand/labour/cash experiments inherit that
baseline and the chosen alpha. Main-farm experiments retain their existing
baseline. Comparisons reject mixing these different roots, even if their raw
farm records happen to be identical. Daily and weekly simulation ledgers cover
the whole farm; crop filtering cannot manufacture a crop-level resource ledger.

The historical numerical evaluation is explicitly labelled with its original
fixture hash and alpha 0.35. It does not establish accuracy for a changed
playground or imported farm. Neither EWMA nor CP-SAT is a model trained on real
farm outcomes. Public context remains separate from private forecasts and is not
a numerical input. Registry-only sources have no observation charts. Public
exports require a verified redistribution licence; all exports escape spreadsheet
formulas and are bounded. Numerical preview admission is capped at 30 requests
per minute per session and 60 per minute per IP, in addition to existing limits.
