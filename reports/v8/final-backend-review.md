# V8 final backend review

Date: 11 September 2026
Scope: synthetic execution invariants, planner identity and scenario reserves,
worker/runtime initialization, and immutable-edition publication readiness
External actions: none; no provider request or deployment was made

## Disposition

No additional backend release blocker was found after the fixes below. The
focused planner, numerical, and execution suite passed, and the repository's
post-restart 56-day HTTP execution artifact reports PASS. The full regression
artifact predates the last planner identity/reserve edit, so the integration
owner must still rerun the full suite and HTTP trial against the final frozen
tree before publication.

## Findings fixed during review

Two deterministic identity defects were reproduced in the planner/execution
boundary.

First, generated allocation IDs encoded a horizon-relative sow offset. A later
replan could therefore assign the same ID to a different absolute crop cycle.
Execution de-duplicates task events by `<allocation-id>:<stage>`, so a repeated
ID could suppress a real later harvest event while the frozen numerical trace
still created its inventory. Candidate identity is now
`daily-bed-cpsat-v3`: a fixed-length content identity over bed, crop, recipe,
absolute sow date, transplant date, and harvest date. A caller-controlled batch
ID that imitates a future generated ID is handled separately: `plan()` accepts
at most 10,000 historical `excluded_candidate_ids`, filters only new candidates,
and retains matching active locks. The execution replan path supplies IDs from
all completed task history.

Second, a harvested lot inherited its allocation ID. An arbitrary opening
inventory lot could have that same ID, leaving duplicate closing-lot identities
and ambiguous delivery provenance. Harvest lots now use a bounded deterministic
hash with a deterministic collision ordinal checked against every opening and
previously generated lot ID. Order-level lot allocations expose their source
allocation, and execution persists that relation after harvest so carried stock
retains provenance through later replans.

A third finding affected custom scenarios. The solver and validator accepted
arbitrary finite nonnegative yield factors but reserved harvest labour and cash
at a hard-coded factor of 1.1. A declared factor above 1.1 could therefore pass
the optimization capacity checks and consume more weekly labour in replay.
Planner V3 now uses the maximum yield factor in the declared scenario set for
weekly harvest labour, conservative cash, and scenario-independent commitment
terms. Standalone resource and validation helpers retain the documented 1.1
default when no scenario set is supplied. A constructed one-bed case proves
that factor 1.1 fits while factor 2 is rejected independently by a weekly labour
ceiling and a cash ceiling.

## Execution and persistence invariants

The reviewed execution path freezes planner `ledger`, `inventory_snapshots`,
and order-level lot allocations. Each committed civil day verifies its opening
inventory against the prior durable closing state, applies the frozen closing
lots, records due tasks once, accumulates Decimal revenue and cost, and rounds
only public balances to cents. Replanning begins on the next unexecuted Singapore
civil date. It imports current closing inventory and cash, removes completed
orders, and locks every already-sown allocation whose harvest-plus-sanitation
occupancy reaches the new horizon. Past sow input costs are not charged again;
future harvest labour and produced stock remain in the continuation trace.

`crop_state()` describes elapsed schedule state and explicitly sets
`physiological_biomass_model=false`. A harvest is treated as executed only when
its task ID is recorded. Before the first advance, sow/transplant stages can be
shown from the frozen schedule with `state_basis=snapshot_schedule`; this is a
declared schedule display and must not be described as an observed field state.
The `sanitation_complete` event occurs on the last inclusive sanitation date,
with the bed available on the next civil date. That event name relies on an
end-of-day convention, which remains a presentation clarification rather than a
resource-conservation defect.

PostgreSQL tests exercise same-key concurrent replay, changed-key races at one
revision, tenant isolation, and reopening the store. World mutations use tenant
serialization, revision checks, and durable receipts. The successful HTTP trial
contains 56 unique day-close events, restart persistence, a local replan, mass,
cash, order-lot and task conservation, exact replay of an old idempotency key,
and zero provider calls from GET requests.

## Worker and runtime compatibility

The application starts separate numerical and provider worker lanes. Local
planning, scenarios, and research calculations run in the numerical lane;
provider missions and advisor conversations run in the provider lane. Startup
imports scenarios, conversations, security, data exploration, research, and
simulation before `metadata.create_all`, so a fresh edition database receives
the V8 tables before workers poll them. Abandoned provider-bearing work follows
explicit interruption/retry rules rather than silent inference replay.

Runtime provenance reads the source commit written into
`config/build-source.txt` at image build time and marks an edition immutable only
when both a sealed commit and `FARMTACT_EDITION` are present. Simulation worlds
also freeze this provenance. Development checkouts remain visibly unsealed.

## Actual publication image and immutable storage

`scripts/publish_edition.py` builds with
`config/releases/fly-gateway.toml`, whose build section selects
`Dockerfile.fly`. The generic development Dockerfile is not the Fly publication
image. `Dockerfile.fly` copies `packages`, `services`, `runtime`, `config`,
`research`, `scripts`, required frozen reports and fixtures, installs PostgreSQL
18 plus the locked Python runtime, and writes the exact source commit. The V8
capability registry is under `config/` and is therefore present. V8 review
reports are not copied wholesale, but no application path reads them as runtime
state; the model-discovery report path is provenance/configuration metadata and
does not trigger a file read. Their omission is not a current runtime blocker.

The publisher requires a contiguous immutable registry and exact image digest,
updates the shared Machine with the complete registry, and probes the new
edition's source and edition identity before publishing it as current. The
shared entrypoint creates `/persist/v8`, rejects symlinks and unsafe ownership,
bind-mounts only that subtree at `/data`, unmounts the shared parent, and starts
the exact image's original entrypoint. On a fresh empty V8 subtree, Fly boot
initializes PostgreSQL 18, creates the edition database, and invokes the additive
schema initializer. Existing V1-V7 image digests, registry prefixes, source
identities, and `/persist/v1` through `/persist/v7` databases remain unchanged.
No game table is shared across editions.

This establishes source and state compatibility for a fresh V8 namespace. It
does not establish independent availability: all editions still share one Fly
Machine, one volume, and one gateway. The process-level Python egress hook is not
an operating-system firewall. Those operational limits remain documented in
the V8 operations review.

## Evidence

Focused command run after the planner changes:

```text
/tmp/farmtact-docs-venv/bin/pytest -q \
  tests/planner/test_v8_identity.py \
  tests/numerical/test_planner_v8.py \
  tests/gameplay/test_simulation_execution.py

19 passed, 2 warnings in 20.20s
```

The integration owner's later focused artifact records 23 tests, zero failures,
zero errors, and zero skips. `reports/v8/execution-trial.json` records PASS for
the real local HTTP 56-day/restart/replan trial. The most recent full-suite
artifact records 557 tests, zero failures, zero errors, and one skip, but its
timestamp is earlier than the final planner patch and is retained as prior
evidence only.

All execution and model results reviewed here are synthetic. They do not prove
farm-specific biology, commercial yield, actual operator behavior, participant
usability, production recovery, or multi-host availability.
