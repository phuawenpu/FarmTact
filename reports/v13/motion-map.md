# V13 motion and reduced-motion map

Status: prototype motion contract. Motion communicates persisted state changes; it is not decoration, a timer, or evidence that work completed.

| Event | Trigger and authority | Default motion | Duration | Persistent non-motion evidence | Reduced-motion behavior |
|---|---|---|---:|---|---|
| Card selection | Local selected index after swipe/button/key navigation | Active card gains focus/depth; adjacent visual layers shift slightly | 180–220 ms | Card title, position text, active indicator, Previous/Next state | Immediate card replacement; position text and focus update remain |
| Swipe candidate | Pointer movement after horizontal intent wins | Active card tracks a bounded horizontal distance | Direct manipulation; snap within 180–220 ms | Previous/Next controls remain available | No tracking transform; valid completed gesture changes immediately |
| Swipe cancelled | Vertical intent, insufficient horizontal distance, or pointer cancel | Card returns to origin | ≤180 ms | No index/state change | No transform; no state change |
| Reserve accepted | Server accepts explicit proposal apply | Constraint card begins moving toward Active constraints; B3 highlight appears | 200–260 ms | Proposal ID/revision, “Calculation queued,” highlighted B3 label | Immediate reclassification and highlight plus status text |
| Calculation queued | Persisted job status `QUEUED` | Optional low-amplitude progress pulse; no metric transition | Continuous, not progress-percentage | Polite live text “Calculation queued”; mutation controls unavailable | Static status icon/text |
| Calculation running | Persisted job status `RUNNING` | Optional spinner/progress sheen; B3 remains highlighted | Continuous | Polite live text “Recalculating plan”; previous metrics labelled current-until-complete | Static status icon/text |
| Calculation complete | Bound job/result is `COMPLETED` | Revised strategy enters; only changed values receive a brief background highlight | 240–400 ms highlight; no count-up | New values, signed deltas, result binding and completed status persist | Immediate replacement; signed delta and “Calculation complete” persist |
| Calculation failure/cancel | Persisted terminal failure/cancel | No shake, bounce, or success-like movement | None | Alert text, safe recovery action, old metrics retained | Identical |
| Open Ask/Details | User activation | Mobile sheet rises; desktop panel may fade/translate slightly | 180–220 ms | Named dialog/panel, focus placement, close control | Panel appears immediately |
| Close Ask/Details | Close/Escape | Reverse panel transition | 140–180 ms | Focus returns to invoking card action | Panel closes immediately and focus returns |
| Stack leaves viewport | Intersection/visibility state only | Compact selected-card summary fades in near board/conversation | 140–180 ms | Summary contains selected title and “Return to card” | Summary appears immediately |
| Undo accepted | Server accepts inverse proposal apply | Applied card remains in Active constraints while inverse job runs | No relocation yet | “Undo queued/running” and inverse proposal reference | Identical structure, static status |
| Undo complete | Bound inverse job completes | Constraint card returns to its derived stack position; B3 highlight resolves to server state | 200–260 ms | Original event remains in history; inverse result/deltas and completed status persist | Immediate reorder/state replacement |
| Undo becomes stale | Server reports inverse ineligible | No motion | None | Disabled reason remains visible and associated with Undo | Identical |

## Interaction safeguards

- Do not animate a card into Active constraints before the server accepts apply.
- Do not replace metrics, animate deltas, or insert a revised strategy before the bound result completes.
- Never use a looping animation as the only indication of queued/running state.
- Avoid parallax, perspective flips, uncontrolled spring overshoot, auto-advancing cards, animated counters, and motion tied to simulated farm time.
- Focus never follows decorative layers; it moves only after a real selection or panel transition.
- Reduced-motion mode disables `transform`, smooth scrolling, parallax, and animated reordering for these interactions. Opacity should also be immediate where it could create a vestibular or delayed-content concern.
- Animation cancellation must leave the DOM in the authoritative final state. A reload reconstructs state from the server rather than trying to resume an animation.

## Sticky comparison mode

Normal flow is the product default. A development-only `inline`/`sticky` flag may compare action-dock placement. In sticky mode:

- reserve the dock's layout height;
- add the relevant `env(safe-area-inset-bottom)` padding;
- ensure the final board/strategy/dialog control can scroll fully above the dock;
- fall back to normal flow when a software keyboard or constrained viewport would cause overlap;
- do not animate between inline and sticky during ordinary scrolling.

Browser evidence must separately assert no covered content; a screenshot alone cannot prove every focus target remains reachable.
