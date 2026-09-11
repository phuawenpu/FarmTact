# V8 scenario and conversation reliability

Date: 11 September 2026 UTC  
Scope: GAME-08, GAME-11, GAME-12 and exact scenario delivery impacts  
Execution mode: synthetic/test; no provider requests made

## Scenario attempts and retry safety

Each new scenario now stores an append-only bounded attempt summary with attempt
number, queued/started/completed timestamps, terminal status and safe exception
type. At most three local numerical attempts are admitted per immutable scenario.

The original run idempotency key remains bound to the scenario. A repeated request
while queued, running or completed returns the existing response with `reused=true`.
A failed or cancelled attempt can be queued again with that same key through either
the existing `/run` endpoint or the additive `/retry` endpoint. A different or stale
key receives 409 and cannot create another attempt. A repeated retry after the new
attempt is queued returns the same state and does not increment accounting.

Retries preserve the frozen input, baseline root, model versions and prior attempt
history. They clear stale result/acceptance fields before calculation. Unsupported
frozen numerical versions still fail explicitly; the worker does not substitute a
new model.

## Scenario cancellation

`POST /api/v1/scenarios/{id}/cancel` atomically changes DRAFT, QUEUED or RUNNING to
CANCELLED. Repeated cancellation is idempotent. The current attempt records its
cancellation time. A queued cancelled job cannot be claimed.

Numerical optimization is synchronous and does not accept a cancellation token.
The worker therefore checks persisted cancellation immediately after each local
plan calculation and again under the tenant lock before writing acceptance or quest
progress. Cancellation during a solve has bounded latency equal to the current
solver call; it cannot interrupt CP-SAT mid-call. The final compare-and-write guard
prevents a stale local result from overwriting a concurrently committed CANCELLED
state. Scenario computation makes no paid inference call and no inference budget
reservation.

Worker restart keeps a running numerical attempt as the same queued attempt and
records interruption metadata. It does not append a retry attempt merely because
the process restarted.

## Tenant bounds and listing

Scenario creation locks the tenant row and rejects the thirty-first persisted branch
with 429 before numerical work. Existing idempotency keys are resolved before the
quota check. Listing performs SQL ordering and limit rather than loading every JSON
branch, accepts `limit=1..30`, and accepts an exclusive ISO `before` cursor while
preserving the response shape `{scenarios: [...]}`.

Conversation persistence independently enforces 30 conversations per tenant under
the tenant lock. Conversation listing is SQL ordered and bounded to 30, with
optional limit/before values. Atomic request admission rechecks the 120-message
capacity while holding the conversation lock, including one user message plus all
requested advisor turns.

No retention deletion job was added. Anonymous-session expiry still prevents later
authentication, but persistent expired tenant rows require a separately authorized,
edition-aware retention policy.

## Conversation cancellation primitive

`ConversationStore.cancel_request(tenant, conversation_id, request_id)` atomically
changes QUEUED/RUNNING to CANCELLED and returns the stored request plus a transition
flag. It also returns the conversation to OPEN and records the cancelled request as
its latest terminal state. `is_cancelled` is a bounded status query.

The Council package wires this primitive into an additive cancel route and checks it
before numerical context, budget reservation, each initial or repair provider call,
message persistence and final completion. CANCELLED is terminal. This package made
no live or paid provider request. Cancellation during an already-active synchronous
HTTP transport remains cooperative at the next gateway/turn boundary; it is not a
database-driven transport abort.

## Exact computed delivery impacts

Scenario `computed_impacts` now compares the planner's `order_allocations` for the
same policy and stable demand-line ID. Each affected booked order includes baseline
and branch requested/delivered kilograms, branch shortfall, price state and policy.
The former aggregate-date disclaimer was removed. Multiple policy changes for one
order are grouped into one delivery row, preserving the existing UI's unique
order-key shape.

Old frozen strategy payloads without `order_allocations` remain readable. They use
the prior changed-date screening and say explicitly that this is a legacy fallback.
Residual forecast lines are not presented as buyer orders because they have no
order ID.

## PostgreSQL concurrency evidence

The dedicated PostgreSQL test runs six concurrent same-key scenario retries after a
forced transient failure. Exactly one second attempt is appended. Six concurrent
cancellations produce exactly one state transition. A separate six-way conversation
request cancellation also produces exactly one transition. All callers observe the
same terminal payload.

## Synthetic execution review

The new execution engine was inspected without editing it. Its segment clock,
transaction reuse, daily mass check, task dates, Decimal cash accumulation, remaining
order cutoff, locked growing work and receipt compare-and-set are internally
consistent with the planner trace.

One integration defect was found: replan validates persisted closing lots through
`InventoryLot`, which requires `origin`, while the first planner snapshot shape
omitted it. Planner snapshots now include `origin=synthetic`. The execution replan
suite passes with this correction. Concurrent identical replans can perform the same
local solver computation more than once before receipt serialization, but one state,
event sequence and receipt commits; no provider call occurs.

## Verification

```text
/tmp/farmtact-docs-venv/bin/pytest -q tests/gameplay/test_v8_reliability.py
5 passed in 3.30s

/tmp/farmtact-docs-venv/bin/pytest -q tests/gameplay/test_v8_reliability_postgres.py
1 passed in 2.81s

/tmp/farmtact-docs-venv/bin/pytest -q tests/gameplay/test_v8_reliability.py tests/gameplay/test_v8_reliability_postgres.py tests/gameplay/test_scenarios.py
34 passed in 86.55s

/tmp/farmtact-docs-venv/bin/pytest -q tests/gameplay/test_simulation_execution.py
3 passed in 7.76s
```

One independently rerun pre-existing PostgreSQL conversation persistence test saw
its globally visible queued request claimed by another concurrently active test
worker and observed RUNNING instead of QUEUED. Its concurrent sequence/idempotency
checks had passed before that assertion. The dedicated isolated V8 PostgreSQL test
passed; a final root suite should run without other processes polling the shared
`farmtact_test` queue.

## Remaining limits

- Scenario cancellation cannot preempt a CP-SAT call already executing.
- Provider transport cancellation remains cooperative between bounded calls.
- Scenario retry history records safe exception classes, not full tracebacks or
  sensitive internal messages.
- Tenant data retention and deletion is still an explicit policy gap.
- Exact order impacts cover the current order schema: order ID, crop, date, net
  quantity and price. Buyer, grade, customer priority and lot eligibility do not
  exist in the shared contract.
- All calculations and executions remain synthetic. No farm operation is enabled.
