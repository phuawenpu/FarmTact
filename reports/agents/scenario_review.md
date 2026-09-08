# Independent scenario and quest review

Reviewed 2026-09-08. Scope: `services/api/scenarios.py`, `tests/gameplay/test_scenarios.py`, and `tests/gameplay/test_scenario_postgres.py`, with read-only inspection of conversation snapshot integration and store transaction semantics. No provider or inference call was made.

## Resolution verification

Both findings below were fixed and independently rechecked on 2026-09-08:

- `ScenarioRequest.quest_assumption` now requires a non-default control relevant to the declared quest, and creation additionally rejects a quest whose frozen input hash did not change. The new four-case wrong-control test covers every quest.
- Root branch creation now returns HTTP 409 when the tenant has no farm snapshot. The new authenticated missing-farm test covers this path.

`.venv/bin/pytest -q tests/gameplay/test_scenarios.py tests/gameplay/test_scenario_postgres.py` now reports **26 passed**, including the real PostgreSQL concurrency/persistence case. The findings remain below as the audit trail; neither remains open.

## Findings

### 1. Resolved: named quests accepted unrelated and no-op experiments, then awarded discovery badges

`ScenarioRequest.quest_id` and `controls` are independently valid (`services/api/scenarios.py:39-44`). Creation does not check that the chosen controls exercise the named quest, and `_progress` awards `Experiment explorer` after any completed branch plus `Tradeoff discovered` after any call to inspect (`services/api/scenarios.py:128-139`).

An adversarial in-memory probe confirmed all of these requests reached `completed` with both badges:

- `late_harvest` with all controls at their defaults;
- `busy_market` with only `cash_percent=50`;
- `short_handed_week` with only a caixin demand increase;
- `tight_budget` with only `labour_percent=50`.

The first case has identical baseline and scenario inputs, so there is no experiment or tradeoff to discover. The other cases complete a different quest from the one declared. This breaks each quest's required learning objective and makes badge state unreliable.

Recommended fix: validate quest/control compatibility before persistence. Require `late_harvest` to name a batch and change `delay_days` or `yield_percent`; require `busy_market` to name a crop and change `demand_percent`; require `short_handed_week` to change `labour_percent`; require `tight_budget` to change `cash_percent`. Additional sandbox controls can remain allowed if the named quest's required control is also changed. Add negative request tests for all four no-op and cross-quest combinations, plus assertions that unchanged `policy_comparisons` cannot earn `Tradeoff discovered`.

### 2. Resolved: authenticated scenario creation without a farm returned HTTP 500

For a root branch, creation passes `store.latest_farm(t)` directly to `apply_controls` (`services/api/scenarios.py:176-177`). If an authenticated tenant has no farm snapshot, `Farm.model_validate(None)` raises an uncaught validation error. A `TestClient` probe with a valid new tenant and no bootstrap/import returned `500 Internal Server Error`.

The conversation API already handles this state explicitly with HTTP 409. Scenario creation should do the same before calling `apply_controls`, with a stable message such as “Import a farm before creating an experiment.” Add a route test that creates an authenticated session without calling bootstrap and expects 409.

## Verified behavior

- Control ranges and strict integer handling cover delay `0–14`, yield `50–100`, and demand/labour/cash `50–150`; changed harvest controls require a batch and changed demand requires a crop.
- `apply_controls` deep-copies and revalidates the frozen farm. The tested branch leaves the main farm and accepted main worklist unchanged.
- Child branches continue from the parent's frozen input and preserve the root baseline hash. Comparison accepts one to three distinct, completed branches and rejects different frozen baselines.
- Tenant filters cover listing, read, run, parent lookup, comparison, quest inspection, and conversation-derived snapshots.
- Scenario jobs make no inference reservations, persist numerical results for replay, requeue interrupted numerical work, and allow an infeasible numerical result to reach the debrief state.
- Tenant row locking serializes duplicate create/run requests in PostgreSQL; the persistence/concurrency test passed.

## Checks executed

- `.venv/bin/pytest -q tests/gameplay/test_scenarios.py` — 20 passed.
- `.venv/bin/pytest -q tests/gameplay/test_scenario_postgres.py` — 1 passed against PostgreSQL.
- Adversarial quest/control probe — reproduced four incorrect quest completions.
- Authenticated missing-farm probe — reproduced HTTP 500.

The passing suite establishes branch isolation, bounds, continuation, comparison, persistence, infeasibility, tenant isolation, and idempotency for its asserted paths. It does not cover the two failure modes above.
