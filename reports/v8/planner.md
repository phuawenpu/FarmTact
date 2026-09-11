# V8 planner and numerical remediation

Date: 11 September 2026 UTC  
Implementation: `daily-bed-cpsat-v2`  
Scope: NUM-03 through NUM-07 plus additive execution/replanning hooks  
Data status: synthetic demonstration only

## Implemented semantics

### NUM-03 — scenario weights

`plan(..., scenario_set=...)` now accepts a declared scenario set. The planner
rejects empty sets, duplicate IDs, non-finite or negative factors/weights, a
non-positive total weight, and more than 100 scenarios. It normalizes raw weights
and converts them to 1,000 deterministic integer objective units. Every positive
weight receives at least one unit. The returned scenario rows expose the raw
`weight`, `normalized_weight`, and `objective_weight_units`.

The weighted objective consumes those integer units. Scenario-independent new-work
cost is charged once rather than once per scenario. The largest quantization error
is approximately 0.001 of total objective weight; this is disclosed rather than
represented as an exact continuous expectation. The fixed scenarios remain
declared stress cases. No random draw occurs, and planner output now reports
`scenario_seed=null`.

A one-bed constructed case proves behavior rather than checking metadata: changing
weights from 99% quiet / 1% busy to 1% quiet / 99% busy changes the optimal Lean
choice from no planting to planting.

### NUM-04 — objective and Resilient risk behavior

Lean and Balanced maximize weighted policy utility. The output includes, per
scenario, revenue, packing and disposal cost, shortfall mass and coefficient,
disposed mass and coefficient, terminal stock and coefficient, new-work commitment
cost, and the resulting SGD-equivalent policy score. The score is a transparent
engineering preference, not literal expected profit. Input, labour, packing, and
disposal continue to be shown separately as the partial accounting cost.

Resilient uses a lexicographic solve:

1. maximize the minimum aggregate fill rate across every declared scenario to one
   basis-point resolution;
2. only when the primary solve is proven `OPTIMAL`, hold that service floor and
   maximize weighted policy utility.

Solver metadata reports both stage statuses, the achieved fill floor, and whether
the primary optimum was proven. If the primary solve is merely `FEASIBLE`, the
planner does not claim optimal downside protection. If the secondary solve times
out, it retains the proven primary schedule and labels the unfinished tie-break.
The normal explicit fallback still applies when no incumbent exists.

A two-crop, one-bed exhaustive choice shows the distinction: Lean selects the
higher-price 44 kg crop, while Resilient selects the 52 kg crop and proves a 50%
worst-case aggregate fill rate. This is scenario-level aggregate protection. It is
not a per-order service guarantee, chance constraint, CVaR estimate, or calibrated
probability statement.

### NUM-05 — optimizer/replay lot alignment

The optimizer now uses remaining-life buckets keyed to explicit civil expiry dates.
New harvest enters at `recipe.shelf_life_days - 1`; opening lots enter at their
declared `expires_date - planning_date`; bucket zero expires before the next day.
Delivering from a later-expiring bucket forces every earlier-expiring bucket empty.
The replay helper uses the same earliest-expiry rule, then harvest date and lot ID.
For ordinary crop lots with common shelf life this is FIFO; explicit differing
expiry dates make the rule FEFO.

Demand lines are also sequential in both solver and replay: booked commitments,
then inferred residual; known higher price, then stable ID within each kind. A
lower-priority line cannot receive stock until all higher-priority lines on the
same crop/date are complete.

The new tests enumerate all 81 combinations of one-to-three grams in two lots and
one-to-three grams of demand over two days. In every case the allocator matches the
best feasible `(total delivery, -expiry disposal)` outcome. Separate optimal tiny
cases reconcile solver objective units exactly to replay policy utility, including
an opening lot whose explicit shelf life exceeds the recipe default.

This equivalence applies to the supported domain: crop/date demand, one grade,
single-harvest lots, deterministic integer grams, and no lot-specific sale price or
customer restriction. Lots sharing expiry/harvest dates remain interchangeable in
the CP model; the replay's lot-ID tie-break affects attribution only, not mass,
expiry, revenue, or objective value.

### NUM-06 — terminal stock

Closing stock remains live inventory. It is returned as `terminal_stock` with
`physical_status=usable_or_expiring_inventory_at_horizon_close`, zero declared
salvage value, zero current disposal, and exact quantity. It is never added to
`waste_kg` merely because the horizon ends.

The optimization applies a declared closing-stock policy penalty of SGD-equivalent
0.50/kg for Lean, 0.20/kg for Balanced, and 0.05/kg for Resilient. These coefficients
are engineering preferences, not observed storage costs or market salvage values.
A horizon test shows final-day harvest as closing inventory with zero waste; after
extending the horizon beyond expiry, the same mass becomes physical disposal.
Horizon choice can still affect a plan because no empirically estimated salvage or
post-horizon demand model exists.

### NUM-07 — price state and order allocation

Forecast `price_status` is consumed explicitly. `unavailable_no_booked_price`
becomes a null effective price in planner line accounting, while the compatibility
numeric zero remains in the forecast record. The planner reports requested and
delivered unpriced kilograms; it does not turn missing price into observed zero
revenue evidence.

Confirmed demand is expanded to current Farm order IDs and net quantity after
cancellation. Fully cancelled lines receive no allocation. `order_allocations`
reports requested, delivered, and shortfall kg plus every contributing lot ID,
quantity, harvest date, and expiry date. Residual demand gets a stable synthetic
line ID. A scarce-stock test verifies higher-price booked order allocation,
multi-lot delivery, cancellation exclusion, and a delivered residual line with an
explicit missing price.

The Farm schema has no buyer, grade, contractual priority, order status beyond
cancelled mass, or lot/customer eligibility rule. The planner therefore makes no
buyer- or grade-level allocation claim. Adding those constraints requires shared
schema, solver, replay, and UI changes together.

## Execution and replan integration

`demand_lines`, `demand_line_sort_key`, and `allocate_lots` are public planner
helpers. The allocator boundary uses integer grams. `simulate` adds daily
`inventory_snapshots`, order/lot allocation detail, booked-versus-residual daily
mass, and daily revenue/packing/disposal values while preserving the existing
aggregate ledger and metrics.

`plan` also accepts `locked_allocations` and `candidate_not_before`. Locks consume
resources and occupancy, cannot be omitted or modified, and enter future harvest
and replay. A lock marked executed does not re-charge past input/sowing cost;
future harvest labour remains. New candidates cannot sow before the supplied civil
date. Replanning still requires a new frozen Farm input whose cutoff, inventory,
remaining orders, cash, and horizon describe the new planning date; the override
does not reinterpret an old cutoff.

## Verification

Focused commands executed in the locked application environment:

```text
/tmp/farmtact-docs-venv/bin/pytest -q tests/numerical/test_planner_v8.py
9 passed in 1.56s

/tmp/farmtact-docs-venv/bin/pytest -q tests/numerical/test_planner.py tests/planner/test_research_constraints.py tests/numerical/test_planner_v8.py
22 passed in 58.66s (the run preceded the final added explicit-expiry case)

/tmp/farmtact-docs-venv/bin/pytest -q tests/numerical/test_planner.py tests/planner/test_research_constraints.py tests/numerical/test_planner_v8.py tests/review/test_backend_adversarial.py
33 passed in 60.60s (the run preceded the final added explicit-expiry case)

/tmp/farmtact-docs-venv/bin/pytest -q tests/numerical/test_planner.py tests/numerical/test_planner_v8.py tests/planner/test_research_constraints.py tests/review/test_backend_adversarial.py tests/contracts/test_features.py
36 passed in 61.05s
```

The data/model specialist separately reported 73 combined data, model, and planner
tests passing after integrating forecast price status and scenario provenance.

## Remaining scientific and operational limits

- Scenario factors and objective coefficients are declared synthetic policy inputs,
  not learned probabilities, calibrated yield distributions, or observed costs.
- Maximin protects aggregate scenario fill to one basis point. It does not ensure
  minimum service for each crop, buyer, order, or day.
- Time-limited `FEASIBLE` results are incumbents with a bound, not global proofs.
  Only `OPTIMAL` tiny cases are described as proven optima.
- Terminal penalties and zero salvage are explicit provisional assumptions. They
  need observed storage, spoilage, future-order, and disposal economics.
- The model remains whole-bed and integer-gram. It does not hide fractional beds,
  but lacks grade, multi-cut, split-bed, water, energy, packaging, rotation,
  substitution, and partner-supply constraints.
- No output in this work is an observed biological or commercial result, and no
  farm action is executed.
