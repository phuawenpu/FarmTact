# V13 tactical card interface prototype

Status: implementation plan for an unpublished prototype. V12 remains the latest immutable published edition. V13 must not be added to the public edition manifest, deployed over V12, or described as published until a separate release decision and the edition runbook gates are complete.

## Objective and evidence boundary

Redesign the full application shell around a compact, tactile field-console interface that makes the next consequential farm decision visible without weakening V12's planning, proposal, conversation, task, numerical, provenance, tenant-isolation, or audit contracts.

The prototype uses the existing Singapore Demo Farm and local planner. It does not establish human usability, farmer preference, agronomic validity, or real-farm benefit. The initial evidence is static inspection, automated browser journeys, numerical/API tests, screenshots, and a scripted heuristic review. Real operations remain disabled.

The fixed demonstration vocabulary is:

- `Heavy Rainfall` is a frozen synthetic seasonal scenario and must always display `SIMULATION · SCENARIO ONLY` near its title and again in expanded provenance.
- Farmer-facing `Grow space B3` resolves to the existing frozen entity `bed-07` (`name: B3`, 20 m², sheltered hydroponic) rather than a new rack, bed, or domain model.
- The action label is `Reserve space`, not `Play Constraint`. The card may move into an `Active constraints` region after successful recalculation, but game terminology is not required to understand the operation.
- Production, coverage, stock/waste, resource, and margin consequences come from the completed local planning result. No percentage or delta is hard-coded.
- Council text remains advisory. Opening a card or creating a conversation performs no inference. Only an explicit submitted question can enqueue a validated DeepSeek conversation request.

## Preserved V12 contracts

V13 is a new presentation and bounded workflow extension, not a replacement planner.

- A proposal is tenant-owned, revision-bound, idempotent, and non-mutating while in `draft`.
- Apply queues the existing local recalculation path. Persisted `QUEUED`, `RUNNING`, `COMPLETED`, `FAILED`, and `CANCELLED` states drive the UI.
- The planner remains the numerical authority. Browser code formats server-derived facts but does not calculate farm facts, consequences, or eligibility.
- A strategy can be approved only when its bound recalculation has completed and the proposal/result revisions still agree.
- Tasks and task-result corrections retain V12's append-only event history and `real_operations_enabled: false` boundary.
- Planning, conversation, proposal, task, storage, and idempotency reads remain tenant-scoped. A card ID is not authorization.
- Every API call remains behind durable global/source-IP admission; authenticated calls also consume a tenant/session allowance and mutations consume a stricter tenant/session write allowance before body parsing. LLM-bound calls additionally retain burst, hourly tenant/IP, concurrency, run-budget, and shared provider-call reservations.
- Existing `selected_bed_id` conversation callers remain valid.
- V12 source, image, state, and release metadata remain immutable.

## Bounded scope

Implement now:

1. A responsive tactical shell with a compact mission header, demand/supply summary, card stack, provenance strip, three-action dock, farm board, calculated consequences, Council context, strategy tray, and four-item mobile navigation.
2. A frontend `TacticalCard` view model derived from existing server responses.
3. The exact B3 reservation flow through a revision-bound workflow proposal and the existing local recalculation worker.
4. A separately revision-bound inverse proposal for Undo; the original proposal and events remain in history.
5. Optional validated conversation `focus` for a card/entity pair, with trusted title/source/context derived by the server from the frozen snapshot.
6. Meaningful motion, reduced-motion equivalence, keyboard and button alternatives, and responsive browser coverage.
7. Edition-scoped selected-card/stack-position persistence and a compact selected-card summary when the stack is outside the viewport.

Defer until this prototype is evaluated: a general server-generated card feed, drag-and-drop, points or streaks, collections, automatic background inference, new rack/domain entities, operational automation, and V13 publication.

## Tactical card contract

`TacticalCard` is a frontend view model, never an independent source of farm truth.

```ts
type TacticalCardType =
  | "evidence"
  | "constraint"
  | "applied_constraint"
  | "crop"
  | "order"
  | "strategy"
  | "action"
  | "agent";

type TacticalCardState =
  | "available"
  | "selected"
  | "drafting"
  | "queued"
  | "running"
  | "applied"
  | "completed"
  | "stale"
  | "unavailable";

interface TacticalCard {
  id: string; // stable within the bound edition/snapshot
  type: TacticalCardType;
  entity: { kind: string; id: string; title: string };
  state: TacticalCardState;
  provenance: {
    dataMode: string;
    executionMode: string;
    sourceKind: string;
    sourceTitle: string;
    observedAt?: string | null;
    retrievedAt?: string | null;
    freshness?: string | null;
    label: string;
  };
  boardTargets: string[];
  planning: {
    sessionId: string;
    sessionRevision: number;
    resultId?: string | null;
    resultHash?: string | null;
    snapshotHash: string;
  };
  actions: Array<{
    id: string;
    label: string;
    intent: "primary" | "secondary" | "destructive";
    enabled: boolean;
    disabledReason?: string;
  }>; // zero to three visible actions
}
```

Derivation rules:

- Stable IDs combine the edition-safe card kind and trusted entity ID; revision-specific applied cards also include the proposal ID.
- Entity titles, board targets, provenance, result bindings, action eligibility, and disabled reasons originate in server responses or server-validated mappings.
- The browser may choose presentation order and format values with units. It must not infer that a proposal is current, an inverse is valid, a strategy is approvable, or a conversation focus is admissible.
- `Details` is available for every card through expanded local/server data. `Ask` is rendered only when the server can create a focus-bound conversation for the current frozen snapshot.
- No card exposes more than three visible actions. Further inspectable information belongs in Details, not an overflow of decision buttons.

The complete action matrix is recorded in `reports/v13/card-action-matrix.md`.

## Exact reservation and inverse flow

### Apply

1. The initial selected card is Heavy Rainfall. It is read-only, frozen, and labelled `SIMULATION · SCENARIO ONLY`.
2. Swipe, keyboard navigation, or `Next` selects `Keep grow space B3 free`. The card's entity is `growing_space:bed-07`; board target is `bed-07`.
3. `Reserve space` asks the server for the current operation eligibility. It creates an idempotent draft proposal at the current planning session revision with one `planning_assumptions` change containing a dated reservation for `bed-07`.
4. Explicit apply invokes the existing proposal apply route. The server rejects a stale base revision, duplicate-key mismatch, foreign tenant, invalid dates, unknown bed, or another active numerical job.
5. The UI polls the saved planning session/proposal and announces queued/running/completed state. The action dock is a progress/status region while calculation is active; repeated activation cannot enqueue another job.
6. Only after the bound job completes does the UI replace strategy metrics and render signed deltas supplied by the new server result, highlight B3, and place the revision-specific card under Active constraints.
7. The dock becomes `Undo`, `View new plan`, and `Ask why`. `View new plan` opens the bound result; it does not approve farm actions.

### Undo

Undo is a compensating action, not deletion or rewind.

1. The server returns inverse eligibility for the applied proposal, including the current expected session revision and an explicit disabled reason when stale.
2. `Undo` creates a new idempotent proposal whose change removes exactly the reservation introduced by the original proposal. It includes `inverse_of_proposal_id`, the original reviewed change hash, and the current base revision.
3. The new proposal follows the same draft → apply → queued/running → completed path. The original proposal, result, and events remain immutable.
4. On successful inverse recalculation, B3 returns to its server-derived board state and the original constraint card returns to the stack. Metrics show the inverse result and signed deltas from the immediately preceding result.
5. Undo is disabled if the session revision/result binding changed, another proposal superseded the affected assumption, the reservation changed independently, completed work now relies on it, or any server invariant says the inverse is no longer exact. The UI displays the returned reason and offers Details; it never synthesizes a best-effort inverse.

This design requires a narrow inverse operation/eligibility response in addition to V12's generic proposal route. Reusing a client-cached revision alone is insufficient because staleness and completed-work locks are server facts.

## Contextual conversation focus

Extend conversation creation with an optional object:

```json
{
  "focus": {
    "card_id": "constraint:bed-07",
    "entity_kind": "growing_space",
    "entity_id": "bed-07"
  }
}
```

Server behavior:

- Validate syntax and a closed set of entity kinds.
- Resolve the entity only inside the tenant-owned frozen farm/planning snapshot selected for the conversation.
- Validate that `card_id` is the canonical card/entity binding for that snapshot; do not trust client title, source text, board targets, or contextual facts.
- Derive and persist trusted `title`, `source`, relevant typed facts, board references, and snapshot/result hashes.
- Reject an entity outside the frozen snapshot with 422, a missing tenant-owned snapshot with 404, and a changed/reused idempotency request with 409.
- Preserve `selected_bed_id` behavior. For a growing-space focus, the server may also populate the compatible selected-bed context; callers may not supply contradictory IDs.
- Creating/opening the conversation remains zero-inference. Only sending a question or explicitly convening/inviting can enqueue provider work under existing budgets and validation.

The mobile presentation is a focus-managed bottom sheet; desktop uses the contextual right panel. The selected card or compact selected-card summary remains visible. Suggested questions are deterministic UI copy and must not be presented as generated advisor dialogue.

## Responsive shell

### 360–430 CSS pixels

- Compact mission header and demand/supply summary precede the card stack.
- Three visual layers indicate a stack, but only the active card is readable, focusable, pointer-active, and exposed to accessibility APIs.
- Provenance and up to three actions remain in normal flow. The center primary action receives visual emphasis without changing DOM or keyboard order.
- Horizontal swipe changes cards only after horizontal intent wins over vertical scroll. Previous/Next buttons and Left/Right arrow keys provide equivalent behavior.
- Farm board, calculated changes, Council state, and strategy cards continue below without being covered by the dock.
- Bottom navigation contains Mission, Records, Crops, and More. Data Explorer, research, reviews, edition controls, audio, and settings live under More.

### Desktop

- Card panel uses approximately 25–35% of the workspace and retains the mobile card's readable proportions.
- Farm board occupies the center; contextual Council/conversation occupies the right; strategies run in a tray below.
- When the stack leaves the viewport, a compact selected-card summary appears near the board or conversation and offers a return-to-card control.

Normal-flow docking is the default. A development-only query/config flag may compare `inline` and `sticky`. Sticky mode must account for safe-area insets, reserve layout space, and pass a no-covered-content assertion. The comparison flag is not persisted as a farmer preference or exposed as a product claim.

## State and browser persistence

- Persist only `selected_card_id` and `stack_position` under an `editionStorageKey(...)` namespace.
- Validate restored IDs against the newly derived card list and its snapshot binding; otherwise select Heavy Rainfall or the first eligible card.
- Do not persist proposal eligibility, metrics, provenance, job status, enabled actions, or trusted focus locally.
- A reload during recalculation restores the selected card, then refreshes server state and resumes status polling without submitting a new proposal/job.
- Edition switching cannot carry card selection or proposal state between editions.

## Motion and accessibility acceptance

- Selection depth/focus transition: 180–220 ms.
- Application: move the card only after accepted apply; highlight B3 while the real job state is visible.
- Completion: briefly highlight only metrics whose server-derived values changed; insert the revised strategy card after result binding succeeds.
- Reduced motion removes translation, scaling, parallax, and animated reordering. It preserves immediate structural changes and status text.
- Use visible focus, semantic buttons, 44–48 px pointer targets, accessible names, persistent disabled reasons, and a polite live region for calculation states.
- Bottom sheets/side panels are labelled dialogs with initial focus, Escape/close behavior, background containment, and focus restoration.
- Adjacent stack cards use `inert` where supported plus `aria-hidden`, no tabbable descendants, and disabled pointer events. Visual peeking must never create duplicate announcements.
- No information, action, or explanation is hover-only.

See `reports/v13/motion-map.md` and `reports/v13/accessibility-review.md`.

## Verification gates

The prototype is ready for review only when evidence records the following without provider calls unless a test explicitly submits a question:

1. Generated contracts and frontend TypeScript/build pass.
2. Python regression passes against isolated PostgreSQL, including focus validation, tenant isolation, idempotency replay/mismatch, revision conflicts, exact inverse behavior, intervening-change staleness, and append-only events.
3. Responsive browser journeys pass at 360, 390, 430, and desktop width for swipe, vertical-scroll disambiguation, Previous/Next, keyboard navigation, active-card-only interactivity, contextual Ask, reservation, job states, B3 highlight, metric deltas, inverse recalculation, and stale Undo.
4. Browser/network evidence proves opening cards/details/conversation creates no provider request and no numerical mutation; only the explicit reservation/inverse calls local planning endpoints.
5. Provenance assertions distinguish synthetic scenario, synthetic farm, projected calculation, advisory interpretation, and farmer-reported result.
6. Screenshots capture the mobile and desktop shell after server-backed state settles. They are prototype evidence, not human-preference evidence.
7. Existing bundle-size warnings remain measured and recorded; they are not silently treated as a new pass or release blocker unless the current threshold is exceeded.
8. V12 release manifests, source/image identity, and state are unchanged. No V13 publication/deployment command is run.
9. Abuse tests prove generic API, authenticated tenant, mutation, and stricter LLM/provider admission limits fail closed with `429`, including the new inverse endpoint.

## Deliverables

- Mobile and desktop prototype screenshots from the responsive browser journey.
- `reports/v13/card-action-matrix.md`.
- `reports/v13/card-entity-tool-agent-map.md`.
- `reports/v13/motion-map.md`.
- `reports/v13/accessibility-review.md`.
- `reports/v13/scripted-usability.md`.
- `reports/v13/recommendations.md`, containing fourteen explicit prototype exploration questions and bounded answers.

## Known risks and stop conditions

- A generic reservation removal can erase later user intent. Ship Undo only with exact server-side inverse/stale validation.
- Card-derived focus can become an injection or data-leak path if client titles/context are trusted. Persist only server-derived focus.
- Swipe can capture vertical reading/scrolling. Require directional intent, cancellation, and controls.
- A sticky dock can conceal content or the software keyboard. Keep normal flow as default and test safe-area/layout reservation.
- Metric animations can make old values appear authoritative during a job. Keep previous values visibly labelled until the new bound result completes.
- “Heavy rainfall” can be mistaken for current weather. Repeat `SIMULATION · SCENARIO ONLY` and never display current/live wording.
- Council affordances can imply automatic intelligence. Never auto-submit suggested questions or invoke DeepSeek during selection, reservation, calculation, details, or panel opening.
- Publishing the prototype would consume the next immutable edition and require the full edition workflow. Publication is deliberately outside this plan.
