# V11 planning Council grounding

V11 changes the Council from prose that cites facts into a review that selects
server-owned propositions. `packages/planning_claims.py` computes each comparison
from the frozen retained schedule and candidate strategy. Every proposition stores
both operands, delta, direction, unit, policy, snapshot hash and the sentence the
application may display as authoritative.

Before a disruption exists, the same catalogue exposes direct frozen strategy
metrics rather than manufacturing a baseline comparison. After disruption it
switches to retained-schedule comparisons. Every record also carries the exact
strategy ID, so a provider recommendation is rejected unless at least one of its
selected propositions concerns that strategy.

Crop composition is deliberately split into three statements: crop-ID set,
allocation count by crop and allocated area by crop. An unchanged crop-ID set can
therefore never establish that the mix or area composition is unchanged. Scenario
differences are labelled comparisons; no proposition claims that an input caused
the result.

`services/api/planning_council.py` runs the existing DeepSeek-only sequential
specialists-then-Chair workflow with the configured exact model. Specialists select
up to three role-scoped proposition IDs, a bounded tradeoff and a rationale code.
The server renders the rationale. Provider output and safe transport audits remain
available for review, while displayed quantities and relationships come only from
the proposition catalogue. The Chair receives verified facts and prior role
statuses, not specialist prose.

The workflow has its own inference identity: planning Council prompt, output,
validator, context and source contracts are all versioned independently from the
legacy mission Council. Validation also binds each rationale to compatible selected
metrics and each tradeoff to its rationale, so a margin rationale cannot be attached
to an unrelated demand or crop-composition proposition.

Weather and Market receive deterministic `unavailable` findings when no admitted
external evidence is frozen. Those findings do not create provider transcripts or
consume requests. A normal no-external-evidence review therefore uses five calls;
the contract remains bounded by nine calls to allow all seven roles and two schema
repairs. Cancellation stops further admission and returns an explicit partial
record.

The offline tests reproduce the V10 reversed-margin counterexample, partial booked
fulfillment and the distinction between stable crop IDs and changed crop area.
They also verify stable claim identities, non-finite-value rejection, absent-role
call skipping, Chair input isolation and cancellation. No authenticated provider
call was made for this package; end-to-end provider behavior remains a release
acceptance item subject to the shared inference budget.
