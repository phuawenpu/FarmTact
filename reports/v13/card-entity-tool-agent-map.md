# V13 card → entity → tool → explanation map

Status: prototype traceability map based on the V13 design and inspected V12 contracts. “Tool” names the existing or narrowly extended application operation; it does not imply an LLM tool call.

| Card / fixed example | Canonical entity binding | Application operation or state change | Numerical / evidence authority | Explanation role | Provider behavior |
|---|---|---|---|---|---|
| Heavy Rainfall | Frozen synthetic seasonal scenario record bound to the planning snapshot | Read-only impact comparison; no assumption changes | Frozen scenario inputs and local comparison output | Weather & Risk Monitor | None on select/open/review; explicit submitted Ask only |
| Keep grow space B3 free | `growing_space:bed-07`; fixture display name `B3` | Create a revision-bound draft containing a dated reservation; explicit apply queues the existing local planner | Farm snapshot, proposal validation, CP-SAT result | Crop Planner for crop/timing; Capacity & Cost for area/labour/cash; Farm Planner for plan trade-off | Zero calls throughout proposal/recalculation |
| Applied B3 reservation | Current proposal ID + proposal revision + completed result ID/hash | View bound result; create an exact compensating proposal when Undo is eligible | Proposal/event store and current planning revision | Farm Planner; Ask Why may route to a selected specialist | Opening is zero-call; only submitted question may call DeepSeek |
| Balanced strategy | Strategy ID plus result hash | Preview/compare; approve only when feasible/current and policy eligible | Local planner metrics, violations, and V12 approval contract | Farm Planner / Plan Reviewer | None for preview/compare/approve |
| Crop batch | Frozen batch ID | Inspect; compare only against an available calculated version | Farm snapshot, schedule dates, task events | Crop Planner | Explicit Ask only |
| Confirmed order | Frozen order ID | Inspect commitment; no implicit status change | Immutable order events and booked-demand metrics | Demand Planner | Explicit Ask only |
| Tentative order | Frozen tentative record ID | Inspect context; cannot become booked implicitly | Frozen tentative-demand data | Demand Planner / Market & Price Analyst within role scope | Explicit Ask only |
| Farm action | Task ID + event revision | Existing task-result or correction API | Task contract, checklist/quantity validation, append-only event | Relevant functional role selected by context | Explicit Ask only |
| Council specialist | Canonical role/advisor ID | Open role details/evidence or create focused conversation | Role contract, admitted evidence, validation status | The selected role | Creating/opening conversation is zero-call; sending question is explicit inference |

## Reservation lifecycle trace

```text
constraint:bed-07
  → tenant-owned planning session + current revision
  → draft proposal (no numerical or farm-state mutation)
  → explicit apply
  → existing local recalculation job (QUEUED → RUNNING → COMPLETED)
  → new result ID/hash + session revision
  → server-derived board state, metrics, deltas and applied-card eligibility
  → optional explicit sandbox approval under the preserved V12 contract
```

The card transition is a projection of persisted state. It is never the source of the proposal, reservation, calculation, or board highlight.

## Inverse lifecycle trace

```text
applied proposal + current result/revision
  → server inverse-eligibility check
  → new draft proposal with inverse_of_proposal_id
  → explicit apply
  → local recalculation job
  → new result/revision
  → constraint returns to stack
```

The original proposal and `proposal_applied_recalculation_queued` event remain auditable. If an intervening revision, changed reservation, dependent completed work, or superseding proposal prevents an exact inverse, the lifecycle stops at eligibility and returns a disabled reason.

## Contextual Ask trace

```text
card_id + entity_kind + entity_id
  → server resolves tenant-owned frozen snapshot
  → server validates canonical entity/card binding
  → server derives trusted title/source/context and persists focus
  → conversation opens with zero inference
  → user submits a question
  → existing bounded DeepSeek conversation workflow and validation
```

Client-authored titles, source descriptions, numerical facts, and arbitrary context are never admitted as trusted conversation focus. Existing `selected_bed_id` callers remain compatible; a B3 focus may map to the same trusted bed context.

## Provenance vocabulary

| Evidence class | Required wording | May affect numerics automatically? |
|---|---|---|
| Heavy Rainfall prototype record | `SIMULATION · SCENARIO ONLY` | No; only an explicit reviewed assumption/proposal can change planning input |
| Singapore Demo Farm | `Synthetic demo farm` | It is the declared fixture input, not a real observation |
| Planner result | `Projected · local calculation` | It is the numerical result of explicit inputs, not observed performance |
| Council explanation | `Advisory interpretation` plus validation status | No |
| Task result | `Farmer-reported · unverified` until separately reviewed | It enters the existing recorded-result/recovery contract, not retrospective fact rewriting |
