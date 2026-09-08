# A11 independent backend review

**Reviewed:** 8 September 2026
**Scope:** `packages/contracts.py`, `packages/fixtures.py`, `packages/models/`, `packages/planner/`, and `services/api/`
**Method:** independent static inspection plus offline adversarial tests; no live inference

## Executive result

The numerical core passed adversarial checks for due-date lead times, whole-bed and nursery capacity, weekly labour, cash, daily inventory mass balance, and immutable executed allocations. API run lookup and strategy lookup were tenant-scoped, queued cancellation avoided inference, idempotent mission creation reused the original run, and replay did not reserve paid calls.

Six defects were reproduced in the initial offline review. Three were high severity because they could omit booked demand, violate tenant ownership at the persistence layer, or commit a disrupted farm version without its corresponding replan. A subsequent real-PostgreSQL review found one medium-severity concurrent replan idempotency race. The implementation owner corrected all seven without weakening the adversarial expectations. The offline suite passed 12/12 and PostgreSQL suite passed 4/4, so this review considers the A11 backend gate passed subject to the stated deployment and synthetic-model limitations.

## Findings

### A11-01 — High — event ownership is not enforced across tenant and run

`services/api/store.py:12` gives `run_events.run_id` and `run_events.tenant_id` separate foreign keys. That permits an event whose tenant exists and whose run exists even when the run belongs to another tenant. `append_event` at lines 64–69 performs an ownership select but does not check its result before inserting.

The adversarial test created a run for tenant A and successfully appended and retrieved an event for that run under tenant B. Besides cross-tenant contamination, the global `(run_id, sequence)` uniqueness can let the injected event block the owning tenant's next event.

Fix by making run identity tenant-bound at the database level, such as a composite unique/foreign key on `(run_id, tenant_id)`, and fail explicitly when the ownership lock/select returns no row. Add a migration for service databases, not only updated SQLAlchemy metadata.

**Resolution verified:** the store now declares the composite identity/foreign key, checks ownership before insert, and applies named constraints to an existing PostgreSQL schema. The cross-tenant append test passes.

### A11-02 — High — failed replan creation leaves a committed farm mutation

`services/api/app.py:224-228` changes the first batch and calls `save_farm` before `enqueue` attempts to create the replan. These operations use separate transactions. An injected idempotency/concurrency conflict returned HTTP 409 while farm version 2 remained committed and no child run existed.

This breaks the decision chain: later missions see a disruption that has no durable replan event, while retrying the same request can apply the delay and yield reduction again. Move the farm version and child planning run into one store transaction, with the idempotency lookup and parent/current-version lock inside that transaction. Derive a stable disruption identity so a repeated request cannot apply the observation twice.

**Resolution verified:** the store now supports a request-scoped transaction reused by nested farm/run operations, and the replan wraps version validation, mutation, and enqueue in that transaction. An injected creation conflict rolls the farm version back.

### A11-03 — High — booked demand disappears when its crop has no recipe

`Farm.integrity` in `packages/contracts.py:101-118` validates batch dependencies but does not reconcile orders with available recipes or create an unresolved-demand state. `forecast` in `packages/models/__init__.py:13-30` iterates recipes, then selects orders for each recipe crop. A valid pak-choi booking in a farm containing only a caixin recipe produced zero pak-choi demand rows.

The system may accept a plan while a booked commitment is absent from its denominator. Either reject the snapshot with a precise missing-recipe error or preserve the order in the forecast as unschedulable/unresolved demand that prevents silent acceptance. The latter better supports the specification's explicit unresolved-field behavior.

**Resolution verified:** `Farm.integrity` now rejects an order whose crop has no approved development recipe. The adversarial test accepts either explicit rejection or preserved unresolved demand and now passes.

### A11-04 — Medium — daily planning uses UTC date instead of Singapore civil date

The farm declares `timezone='Asia/Singapore'`, but `forecast` and planner functions repeatedly use `farm.cutoff.date()` (`packages/models/__init__.py:8`; `packages/planner/engine.py:27,40,85,138`). With a cutoff of 18:00 UTC on 8 September, which is 02:00 on 9 September in Singapore, the simulation ledger began on 8 September.

This can shift due dates, expiry, nursery occupation, and sow/harvest offsets around the UTC day boundary. Convert the cutoff instant to the declared `ZoneInfo` before deriving the civil planning date, and centralize that conversion so every numerical path uses the same value.

**Resolution verified:** `Farm.planning_date` performs the `ZoneInfo` conversion and forecast/planner paths use it. The UTC-boundary ledger test now begins on the correct Singapore date.

### A11-05 — Medium — cached fallback rows lose immutable snapshot lineage

`_restore_cached_source` in `packages/ingestion/context.py:83-93` copies a prior source summary and normalized rows into the refreshed context but does not copy their referenced `SnapshotRecord` objects. The refreshed rows therefore reference a snapshot absent from `context.snapshots`; the manifest and lineage graph omit the raw dependency. `validate_context` only checks that a row has a snapshot ID, not that the ID resolves.

Copy the relevant prior snapshots when cached rows are restored, deduplicate by snapshot ID, verify referenced snapshot hashes/files, and extend validation so every normalized row's `(source_id, snapshot_id)` resolves to a manifest snapshot with the same source.

**Resolution verified:** cached restoration now copies referenced prior snapshot records without duplicate IDs. The normalized-row lineage test passes. A future hardening step can make the full source/snapshot resolution check part of `validate_context`, rather than relying only on restoration behavior.

### A11-06 — Low — nonpositive inference reservations can credit the budget

`Store.reserve_calls` at `services/api/store.py:83-92` accepts zero and negative counts. A negative value decrements `reserved_calls`, increasing later paid-call capacity. Current application calls use a positive constant, so this is defense in depth rather than an exposed request parameter.

Reject non-integer and nonpositive counts and invalid limits before touching the database. Keep the atomic conditional update for valid reservations.

**Resolution verified:** `reserve_calls` rejects booleans, non-integers, zero, and negative counts before its database operation.

### A11-07 — Medium — concurrent identical replans initially returned a conflict to one caller

The first PostgreSQL race test forced two identical replan requests past their pre-transaction idempotency lookup before either acquired the tenant lock. One request returned 202 and created the disrupted farm version plus child run. The other acquired the lock afterward, saw the parent version as stale, and returned 409. PostgreSQL correctly contained only versions 1 and 2 and one child, so this did not duplicate work, but it violated the idempotency contract for simultaneous callers.

The cause was the idempotency lookup occurring before `Store.transaction(tenant)`, while the stale-parent check occurred after the lock. Rechecking the same tenant/key inside the transaction before stale-parent rejection lets the losing request return the already-created child.

**Resolution verified:** under the same forced ordering, both requests return 202 with one child ID, flags `{reused: false, reused: true}`, exactly one child database row, and farm versions `[1, 2]`.

## Passing evidence

The following adversarial checks passed:

- A delivery earlier than the crop cycle retained a shortage and received no new-sowing allocation.
- Independent validation detected bed overlap, nursery-site exhaustion, weekly labour exhaustion, and input cash exhaustion.
- Every simulated day reconciled opening stock plus harvest with delivery, disposal, and closing stock.
- Removing or changing an executed allocation produced `EXECUTED_ACTION_CHANGED`.
- A second tenant received 404 for another tenant's run and strategy identifiers.
- Replay returned stored events without reserving inference or mutating the run.
- Eight concurrent PostgreSQL calls using the same idempotency key created one run and returned one run ID.
- Sixteen concurrent event appends produced contiguous unique sequences; application ownership checks and the PostgreSQL composite foreign key both rejected a mismatched tenant/run pair.

The pre-existing contracts, numerical, and security suite passed 24 tests. The initial adversarial run executed 12 tests: 6 passed and 6 failed, matching A11-01 through A11-06. After implementation fixes, the same 12 tests passed without relaxed assertions.

Final combined verification passed **37 tests** in 36.97 seconds across contracts, numerical, security, and independent review suites. The only output was two upstream TestClient deprecation warnings.

The first PostgreSQL concurrency run passed three checks and reproduced A11-07. After the fix, all **4 PostgreSQL concurrency tests passed** in 2.02 seconds. Tests used opaque temporary tenants in the existing `farmtact` database, requested no council or inference, and deleted only their exact dependent records. A post-run query found zero remaining `a11pg-*` runs.

## Additional limits observed

The PostgreSQL tests exercised concurrent transactions through one local service instance; they do not simulate multi-region latency, failover, connection loss during commit, or every production isolation configuration. The numerical model remains a synthetic whole-bed planning seed with four selectable recipes. Passing feasibility checks means the declared constraints are internally respected; it does not validate agronomic coefficients, demand accuracy, profitability, or real farm suitability.

## Reproduction

```bash
.venv/bin/python -m pytest -q tests/contracts tests/numerical tests/security
.venv/bin/python -m pytest -q tests/review/test_backend_adversarial.py
.venv/bin/python -m pytest -q tests/review/test_postgres_concurrency.py
```

Both commands pass after the verified fixes.
