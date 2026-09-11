# V8 execution persistence and conservation validation

Date: 11 September 2026  
Scope: synthetic execution worlds, PostgreSQL concurrency, restart persistence,
and a bounded zero-inference HTTP trial

## Result

The execution-world persistence path passed a dedicated PostgreSQL concurrency
test. The test used `farmtact_simulation_test` over the private Unix socket and
started no queue worker. It verified same-key receipt replay, competing writes at
one revision, tenant isolation, and persistence through a newly constructed
`Store` instance.

The actual HTTP trial is implemented in `scripts/v8_execution_trial.py`. It is
intentionally not recorded as executed in this report: the integration owner
will run it after restarting the local service on the completed migration set.
The script cannot request provider work because its planning mission explicitly
sets `council=false` and it fails if any inference reservation or audit record is
observed.

## PostgreSQL concurrency evidence

`tests/gameplay/test_v8_simulation_postgres.py` uses
`postgresql+psycopg://sprite@/farmtact_simulation_test?host=/tmp/farmtact-pg`.
The database was created with `createdb` against that private socket.

One test performs these checks:

1. Six simultaneous `advance` requests use the same tenant, world, request body,
   revision, and idempotency key. All six return the same response, the world
   advances one day, one matching receipt exists, and only one `day_closed`
   event is committed for that date.
2. Two simultaneous requests then use different keys against the same next
   revision. Exactly one returns 200 and exactly one returns 409. The durable
   world advances one additional day.
3. Reusing the first key after the later mutation returns the exact historical
   response while the current world remains unchanged.
4. A second tenant receives 404 for the world, event stream, and advance route.
5. A newly constructed PostgreSQL `Store` returns the same current world and
   ordered event history.
6. Both committed daily ledgers have zero balance error, unique dates, and
   closing-lot mass equal to aggregate closing mass.

Observed focused result:

```text
1 passed in 7.38s
```

The test creates unique tenant and request identifiers and removes its rows at
the end. It does not inspect or claim jobs from the normal `farmtact` database.

## Restart-safe HTTP trial

The HTTP trial supports these phases:

```bash
/tmp/farmtact-docs-venv/bin/python scripts/v8_execution_trial.py \
  --url http://127.0.0.1:8080 \
  --state /tmp/farmtact-v8-execution-state.json \
  --phase start

# Restart the service, then use the same private state.
/tmp/farmtact-docs-venv/bin/python scripts/v8_execution_trial.py \
  --url http://127.0.0.1:8080 \
  --state /tmp/farmtact-v8-execution-state.json \
  --phase finish \
  --report reports/v8/execution-trial.json
```

`--phase all` runs both stages when restart persistence is not being tested.
The state file contains the session cookie, world identity, stable idempotency
keys, and exact request bodies. It is created and rewritten with mode 0600. Each
key is saved before its mutation is submitted. A restart after a server commit
but before the client records success therefore replays the stored receipt.

The start phase creates and waits for an accepted numerical mission, creates a
world, advances seven days, and performs one local numerical replan. The finish
phase reconnects with the stored session and advances the remaining 49 days in
bounded chunks of at most 14 days.

At completion it checks:

- exactly 56 `day_closed` events on 56 contiguous civil dates;
- `opening + harvest - delivered - disposed = closing` for every day;
- closing lot quantities equal aggregate closing inventory and consecutive days
  have continuous opening/closing inventory;
- every order line satisfies `requested = delivered + shortfall` and every lot
  allocation sums to its delivered quantity;
- daily order attribution sums to the aggregate demand and delivery ledger;
- revenue comes only from explicitly priced delivered quantities;
- cumulative input, labour, packing, and disposal costs reconcile to world cost;
- opening cash plus exact revenue minus exact cost reconciles to world cash at
  cent precision;
- every task ID is recorded once and all pre-replan completed actions remain;
- replaying the old seven-day action returns its exact old response without
  changing the current world;
- repeated world, event, bootstrap, and mission GETs add no events and no
  inference reservations.

The script was syntax checked and its command-line entry point was exercised.
No HTTP execution result is claimed until `reports/v8/execution-trial.json` is
written by a successful post-restart run.

## Independent audit findings

The simulation module uses `Store.connection()`, which reuses the current
transaction through a context variable. Event appends, world updates, and
receipt inserts made during a tenant transaction are therefore atomic on
PostgreSQL. Multi-day advances either commit all included civil days or none.
The daily trace uses integer grams for lot allocation, explicit expiry disposal,
order-level attribution, and explicit price status. Public money balances round
only at the cent boundary after accumulating decimal revenue and cost.

The standalone `validate_allocations()` cash violation covers new input cost,
but the main `plan()` acceptance path adds a separate `TOTAL_CASH_BUDGET` hard
violation when any declared scenario's full modeled input, labour, packing, and
disposal cost exceeds available cash. Strategies with that violation are not
`FEASIBLE`, and the mission policy accepts only feasible strategies. The narrower
helper result must therefore not be interpreted alone as the final cash gate.
Modeled rates remain synthetic constants, and the model does not represent
credit, payables, overhead, or revenue-funded purchases within the horizon.

`sanitation_complete` is recorded on the last inclusive sanitation date, while
the public bed remains in sanitation on that date and becomes empty the next
date. The clock is consistent if task completion is interpreted as end of day;
the event name alone does not currently state that convention.

The independent model-evaluation audit found that the original
`leakage_violations` counter was structurally zero: it counted late timestamps
only inside a branch that had already established that all timestamps were on
time. The availability filter itself works, and the adversarial test meaningfully
shows that perturbing a permanently unavailable outcome cannot alter any
forecast. The integration owner is adding an independent counterfactual
behavioral gate and explicit included/excluded dependency counts. Synthetic
benchmarks remain ineligible for production regardless of these checks.

All execution outcomes in this package are deterministic synthetic replay. They
do not constitute observed sowing, harvest, inventory, sales, or biological
validation.
