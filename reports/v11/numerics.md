# V11 guided-planning numerical package

Date: 11 September 2026

## Result

`packages.planning_numerics.calculate_session` is a pure orchestration boundary over the existing `daily-bed-cpsat-v3` planner. It validates a frozen Farm snapshot and V11 planning assumptions, creates a new input version only for explicit order changes, calculates Lean/Balanced/Resilient alternatives, and optionally evaluates a supplied saved schedule without optimizing or repairing it.

Future-demand adjustments scale residual forecast demand only. They do not rewrite historical records, confirmed quantities, or Farm orders. An explicit add, amend, or cancel operation is required to change a booked order.

Seasonal inputs are labelled synthetic sensitivities. One inclusive crop/system/date window can scale marketable yield from 50–100% and delay harvest by 0–14 days. Applicability is based on the nominal harvest date. Allocation identity and nominal endpoints are retained while an `effective_projection` records the changed harvest and yield. The effective date drives bed occupancy, harvest labour, inventory creation, shelf life, and order allocation. Reapplying the same assumptions is idempotent.

The retained schedule uses the same changed Farm, forecast and scenario set as optimized strategies. Its violations and outcomes are returned even when infeasible; it is never silently repaired. Comparisons expose baseline and scenario metrics, arithmetic deltas, and added, removed or changed allocations for each policy.

The retained result includes its weekly trace, daily mass ledger, order-level lot allocations, terminal inventory and cost breakdown. Its status incorporates both structural/resource validation and the maximum replayed total cost across the declared scenarios. This supports Council claims about the saved schedule from the exact pre-replan records rather than reconstructed metrics.

The response records calculation timings for input validation, forecast normalization, candidate generation, each policy solve, each policy replay, retained-schedule evaluation, and total assembly. It performs no persistence, provider call, or operational farm action.

## Verification

Executed in the repository `.venv`:

```text
python -m py_compile packages/planning_numerics.py packages/planner/engine.py
pytest -q tests/numerical/test_v11_planning.py tests/numerical/test_planner_v8.py
16 passed in 32.66s
```

A separate bounded smoke calculation applied a 90% yield and three-day delay sensitivity to caixin over the 56-day horizon. Lean, Balanced and Resilient all returned feasible; each contained two allocations with explicit effective projections. No inference call was made.

The edge-case suite also covers exact no-op retained-plan parity, daily mass conservation, an advanced simulation segment with an empty Farm batch list and an executed active lock, future-only candidate admission, historical allocation exclusion, and removal/replacement of a previous seasonal projection from its nominal values.

An allocation marked `harvest_recorded` is immutable historical evidence. Later seasonal assumptions leave its dates, yield and prior effective projection exactly unchanged, and planner replay does not create its harvest or harvest labour a second time. Its remaining sanitation occupancy can still constrain the start of the replanning horizon.

## Limits

The seasonal fields are declared sensitivities, not a weather-to-growth model or measured causal estimate. Delay changes the projected harvest and subsequent bed release; it does not independently model growth stage, disease, nutrients, or energy. Existing financial and synthetic-data limitations of `daily-bed-cpsat-v3` remain unchanged.
