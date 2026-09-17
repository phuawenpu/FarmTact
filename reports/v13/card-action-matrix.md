# V13 tactical card action matrix

Status: prototype contract. This matrix defines visible actions and server-authoritative eligibility; it is not evidence that every row has completed browser verification.

## Global rules

- Every card has a stable ID, one trusted entity reference, frozen provenance, zero or more board targets, and a planning snapshot/result binding.
- At most three actions are visible. A Details surface is universal (through the dock where space permits, otherwise by opening the card itself). `Ask` is visible only when a focus-bound conversation can be validated against the frozen snapshot.
- The center action is the primary action visually. Visual order must match reading and keyboard order.
- Disabled controls remain discoverable and expose a persistent reason in text and through `aria-describedby`; a disabled state is not communicated by color alone.
- Eligibility is returned or validated by the server. Browser state never makes a proposal current, an inverse safe, a task reportable, or a strategy approvable.
- Opening, selecting, comparing, or viewing Details never invokes an inference provider.

## Matrix

| Card type | Trusted entity | State | Left action | Center / primary action | Right action | Server-authoritative eligibility and disabled reason |
|---|---|---|---|---|---|---|
| Evidence | Frozen evidence, forecast, or scenario record | available/selected | Ask | Review impact | Details | Ask requires valid focus and snapshot; Review impact requires a compatible frozen comparison. Heavy Rainfall is always labelled `SIMULATION · SCENARIO ONLY`. |
| Constraint | Planning constraint or grow space | available/selected | Ask | Reserve space | Details | Requires current planning revision, valid dated reservation, eligible grow space, and no active planning job. For this prototype, B3 resolves to `bed-07`. Typical reason: “Planning revision changed; refresh before reserving.” |
| Constraint | Planning constraint or grow space | drafting | Discard | Apply & recalculate | Details | Apply requires the unchanged proposal base revision and a draft owned by the tenant. Typical reason: “Review the reservation dates before applying.” |
| Constraint | Planning constraint or grow space | queued/running | Details | Calculating… | — | Progress replaces mutation controls. The disabled primary describes persisted job state; repeated activation cannot enqueue a duplicate. |
| Applied constraint | Current revision-bound proposal | applied/completed | Undo | View new plan | Ask why | View requires the result bound to the completed recalculation. Undo requires an exact inverse at the current revision. Ask why requires a validated applied-proposal or grow-space focus. |
| Applied constraint | Current revision-bound proposal | stale | Details | View current plan | Ask why | Undo is disabled/omitted with the exact server reason, for example “Another planning change now depends on this reservation.” No best-effort inverse is offered. |
| Crop | Crop batch | available/selected | Compare | Inspect batch | Ask | Inspect uses the frozen batch. Compare requires a compatible comparison result. Ask requires the batch to exist in the frozen conversation snapshot. |
| Order | Confirmed or tentative order | available/selected | Ask | Inspect commitment | Details | The card preserves confirmed/tentative semantics. Actions cannot convert a tentative record or market signal into a confirmed order. |
| Strategy | Strategy version and result hash | available/selected | Compare | Preview plan | Details | Preview and Compare require the frozen completed result. Values and deltas are server-derived. |
| Strategy | Strategy version and result hash | eligible | Compare | Preview plan | Approve | Approve requires a feasible completed result, matching proposal/result/revision, no blocking violations, and existing V12 approval policy. Approval creates sandbox actions only; Details remains available through Preview. |
| Strategy | Strategy version and result hash | unavailable/stale | Compare | Preview plan | Approve (disabled) | Show exact reason, such as “Recalculation is still running,” “Strategy is infeasible,” or “Planning result changed.” Details remains available through Preview. |
| Action | Sandbox farm task | pending/in progress/recovery required | Ask | Record result | Details | Record Result requires a current task status and complete task-specific fields/checklist. Real operations remain disabled. |
| Action | Sandbox farm task | completed/reported | Ask | Inspect result | Details | Corrections continue through the existing append-only correction API; the visible action can move into Details if three-action capacity is reached. |
| Agent | Council role | available/partial/withheld | Evidence | Ask specialist | Role details | Ask creates/opens validated context but does not submit a question automatically. Partial/withheld roles retain reasons and cannot masquerade as fresh advice. |

## Fixed B3 flow states

| State | Card location | Visible actions | Required visible evidence |
|---|---|---|---|
| Initial | Main stack | Ask / Reserve space / Details | `Grow space B3`, trusted ID `bed-07` in Details, snapshot provenance |
| Draft created | Main stack | Discard / Apply & recalculate / Details | Base revision, reservation dates, non-mutating draft statement |
| Queued | Main stack transitioning only after accepted apply | Details / Calculating… | Job `QUEUED`, live status announcement, old metrics retained |
| Running | Active constraints target/board linked | Details / Calculating… | Job `RUNNING`, B3 highlight, no duplicate submission |
| Completed | Active constraints | Undo / View new plan / Ask why | Bound result ID/hash, current revision, calculated metrics and signed deltas |
| Inverse queued/running | Active constraints | Details / Undoing… | New inverse proposal ID, `inverse_of` reference, persisted job status |
| Inverse completed | Main stack | Ask / Reserve space / Details | Original event still in history; board/metrics reflect the inverse result |
| Inverse stale | Active constraints | Undo (disabled) / View current plan / Details or Ask why | Explicit stale reason and intervening revision/result identity |

## Explicit non-actions

- A Heavy Rainfall card cannot apply weather to yield by itself; it opens a read-only impact comparison.
- An Ask action cannot mutate assumptions, apply a proposal, approve a plan, create tasks, or record a result.
- Viewing a strategy cannot approve it.
- Undo cannot delete the original proposal, job, result, or event.
- A card cannot authorize a physical farm operation.
