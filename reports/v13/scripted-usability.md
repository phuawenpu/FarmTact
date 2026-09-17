# V13 scripted usability protocol and heuristic report

Review date: 17 September 2026 UTC. Evidence type: scripted/heuristic, based on the V13 task definition and static inspection of V12. No representative human session was conducted. No enjoyment, comprehension, preference, task-time, or farm-usefulness claim is made.

## Research question

Can a first-time participant navigate from a clearly simulated risk card to an exact B3 reservation, recognize that local recalculation changed the plan, ask a question in the correct frozen context, and safely undo the change without confusing the prototype with live weather or real operations?

## Fixed test fixture

- Edition: unpublished V13 candidate with edition-scoped storage.
- Farm: Singapore Demo Farm, `data_mode=synthetic_demo`.
- Opening card: Heavy Rainfall, labelled `SIMULATION · SCENARIO ONLY`.
- Target grow space: visible name `B3`, canonical ID `bed-07`.
- Change: a dated reservation encoded as an existing planning assumption.
- Numerical authority: existing local planner and persisted job state.
- Conversation: focus-bound to the selected card/entity/frozen planning snapshot; no inference until a tester explicitly submits a question.
- Operations: disabled throughout.

## Script A — mobile first-use journey

Run independently at 360, 390, and 430 CSS pixels with a fresh edition-scoped browser profile.

| Step | Participant instruction | Observable success evidence | Failure indicators |
|---|---|---|---|
| 1 | “Tell us what this first card represents.” | Participant can find `SIMULATION · SCENARIO ONLY`, source/provenance, and does not need Details to distinguish it from live weather. | “Current/live rain” interpretation; provenance clipped or absent. |
| 2 | “Find the option that keeps B3 available.” | Horizontal swipe or Next reaches `Keep grow space B3 free`; Previous returns correctly; page vertical scroll still works. | Swipe captures vertical scroll, skips cards, or no equivalent button exists. |
| 3 | “Inspect what would change before committing it.” | Details exposes `bed-07`, B3, dates, snapshot/revision, and a non-mutating proposal boundary. | New entity invented; unclear dates; action appears already applied. |
| 4 | “Reserve the space and follow what the system is doing.” | Explicit Reserve/Apply creates one proposal/job; queued → running → completed comes from persisted state and is announced; duplicate activation is blocked. | Optimistic fake completion, duplicate job, provider call, or unexplained wait. |
| 5 | “Show which part of the farm changed.” | Board identifies B3 textually and visually; card is in Active constraints; old/new result identity is inspectable. | Color-only highlight, wrong bed, card relocates before apply accepted. |
| 6 | “Explain the production and plan consequence.” | Server-derived metrics replace prior values only on completion; signed deltas include labels/units; no fixed 97%→92% story. | Client-computed/fabricated number, unlabeled percent, animated value without persistent delta. |
| 7 | “Ask why this plan changed.” | Ask Why opens a named bottom sheet, card/summary remains visible, focus is contained, and suggested questions are clearly deterministic prompts. Opening creates no provider request. | Context disappears, wrong entity, background focusable, or auto-submitted inference. |
| 8 | “Close the question view without sending.” | No provider request exists; focus returns to Ask Why. | Request enqueued or focus lost. |
| 9 | “Undo the reservation.” | A new inverse proposal/job is shown; original event remains; after completion B3/card/metrics reflect the new result. | History deleted, immediate client-only reversal, or old result reused as current. |
| 10 | “Reload and continue.” | Selected card/index restores within V13 only; trusted state/job/provenance refreshes from server. | Cross-edition leakage, stale enabled action, duplicate submission. |

## Script B — input-equivalence and accessibility journey

Run at 390 CSS pixels with reduced motion, then at desktop width using keyboard only.

1. Tab to the stack and use Left/Right to navigate every card.
2. Confirm only the active card and its actions occur in the tab/accessibility order.
3. Activate Previous/Next, Reserve, Details, Ask, close, and Undo without pointer input.
4. Confirm all targets meet the intended 44–48 px geometry and visible focus is not clipped.
5. Confirm reduced motion performs immediate state changes with complete textual status and deltas.
6. Open and close the mobile sheet/desktop side panel with Enter and Escape; confirm initial focus, containment, accessible name, and restoration.
7. Inspect every unavailable entity-specific action and read its persistent disabled reason without hover.
8. Traverse the final board/strategy controls in both inline and development-only sticky dock modes; no focused content may sit beneath the dock.

## Script C — stale inverse and conflict recovery

This script requires a controlled second mutation or fixture endpoint that advances the planning revision after the B3 reservation completes.

1. Complete the B3 reservation flow.
2. Apply an intervening planning change that changes the revision/result binding or affected reservation assumptions.
3. Return to the applied B3 card.
4. Confirm Undo is unavailable and its reason names the intervening/stale condition.
5. Attempt the stale inverse request directly and require a conflict; no new calculation job is created.
6. Refresh and confirm the same state/reason persists.
7. Verify the original proposal/application events remain in history.

## Script D — server and network boundary

Record API requests and persisted counts for each action.

| Interaction | Allowed state/network effect |
|---|---|
| Select/swipe/Previous/Next | Local selection persistence only |
| Details | Read only |
| Open Ask / close Ask / choose a populate-only suggestion | Conversation create/read allowed; zero provider submission |
| Reserve draft | One idempotent draft proposal; no planning job |
| Apply & recalculate | One idempotent apply receipt and one local numerical job |
| Polling/reload | Read only; no duplicate job |
| View new plan / Compare | Read only |
| Undo draft | One new inverse draft; original remains |
| Apply Undo | One new local numerical job |
| Submit Ask question | Existing bounded conversation request; this is the only step in these scripts allowed to invoke DeepSeek |

Repeat proposal, apply, inverse, and conversation creation with the same idempotency key and identical payload; require replay. Reuse each key with changed input; require conflict. Repeat cross-tenant entity/proposal/conversation IDs; require denial without existence leakage.

## Script E — provenance comprehension prompts

These are prompts for a future moderated human session, not current findings:

- “Is the rain happening now, forecast, historical, or simulated? Show what told you.”
- “What is B3 called in the underlying farm record?”
- “Which values were calculated, which were interpreted by the Council, and which were reported by a farmer?”
- “Did opening Ask contact an advisor? What action would do that?”
- “What did Undo do to the original record?”
- “Can this screen cause a real planting or purchase?”

## Automated evidence ledger

The ledger below records completed automated evidence from 17 September 2026. It
is scripted prototype evidence, not a human usability or accessibility result.

| Evidence | Required artifact/result | Current documentation-stage status |
|---|---|---|
| Responsive browser journeys | 360/390/430/desktop assertions and screenshots | PASS — deterministic Playwright journey at all four widths plus screenshots |
| Swipe vs vertical scroll | Pointer/touch outcome assertions | PASS — vertical drag retained selection; horizontal swipe advanced it |
| Keyboard and active-card isolation | Tab/accessibility assertions | PASS — arrows/buttons equivalent; one readable active card and two `aria-hidden` depth layers |
| Proposal/recalculation/inverse | Isolated PostgreSQL API/browser evidence | PASS — real PostgreSQL/CP-SAT browser journey and deterministic edge-state journey; original plus inverse history retained |
| Stale Undo | Conflict plus zero-job assertion | PASS — intervening revision exposed a disabled reason and sent no further inverse mutation |
| Focus-bound Ask | Validation/tenant/idempotency and dialog evidence | PASS — strict server focus tests and dialog focus restoration |
| Zero automatic provider calls | Network and provider-ledger delta of zero before explicit send | PASS — open/navigation/reserve/recalculate/open Ask caused no provider mutation; explicit send was separately observed |
| Provenance distinctions | Visible text assertions | PASS — exact `SIMULATION · SCENARIO ONLY` assertion plus code-derived planner labels |
| Reduced motion | Computed-style and functional equivalence assertions | PASS — transformations/animations reduced to effectively immediate state while text persisted |
| Abuse protection | Durable global/IP/tenant/write and stricter inference admission | PASS — 42 shared-control/admission checks plus repository regression; inverse route fails closed at tenant write limit |
| Blind judging | Three first-use personas with problem statement/rubric only | PASS as scripted evidence — findings, repairs, and limitations recorded in `judging-personas.md` |
| V12 immutability / V13 release | Git/release-manifest checks | V12 remains pinned; V13 uses the numbered edition workflow and isolated state |

Supporting technical results: generated web contracts passed; production frontend
build passed with the retained 601.77 kB bundle warning; the final isolated
PostgreSQL result is preserved in `full-regression.xml`. See
`reports/v13/implementation.md` for command-level scope.

## Measures for later human evaluation

Use task outcomes rather than visual preference alone:

- correct identification of simulated versus live/current evidence;
- correct selection of B3 and recognition of `bed-07` in Details;
- wrong mutations and recovery attempts;
- recognition that the proposal is non-mutating until apply;
- recognition of queued/running/completed states;
- correct explanation of one signed plan delta using its label/unit;
- recognition that Ask does not automatically send;
- understanding that Undo creates a compensating event instead of erasing history;
- time to first meaningful decision and total completion time;
- participant-rated confidence, workload, and enjoyment, reported separately.

Rotate gesture/button-first instructions and mobile/desktop order. Do not train participants on the intended answers before measurement. Physical phones, native software keyboards/dictation, screen readers, variable network conditions, and representative farmer participants remain required before making usability or accessibility claims.

## Heuristic recommendation

Proceed with scripted automated verification because every consequential action has a non-gesture route and a server-verifiable outcome. Do not interpret a passing script as evidence that the card metaphor is intuitive, that farmers prefer it, or that the system improves decisions. Those claims remain deferred to human testing.
