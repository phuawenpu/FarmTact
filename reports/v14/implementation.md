# V14 implementation and verification

V14 replaces dashboard-first navigation with an animated introduction at `/` and
one card-driven game at `/play`. This supersedes V13's multi-panel shell; V13 source
and image remain immutable. Publication uses private, recoverable historical state,
not destructive cleanup. Release status and deployed source are recorded separately
in the release manifest; this document describes the candidate implementation.

## Beginner loop

Meet a simulated order → calculate two plans → swipe to compare → explicitly choose
→ advance recorded events → record dated B3 maintenance → choose a feasible recovery
→ advance harvest/delivery → read three debrief cards → replay or try two orders.

Swiping previews; only the primary action commits. The server owns dates, quantities,
eligibility, revisions and completion. Returning does not advance time. A separate
four-bed fixture uses the existing synthetic recipes unchanged and leaves the main
farm untouched. First lesson: 25 kg lettuce. Follow-on: 18 kg lettuce and 7 kg pak choi.
These are teaching conditions and simulated deliveries, not real-farm forecasts.

## One interaction model

| Newcomer problem | Implemented response |
| --- | --- |
| Too many screens | One card position and one action area; no public dashboard or edition chooser. |
| No obvious objective | Order quantity/date on the first card and a persistent step/objective header. |
| Unsure what to click | Emphasized center action; farm art has no controls or hotspots. |
| Unclear choices | At least two calculated policies expose delivery, growing area and cost; disabled recovery has a reason. |
| Numbers without consequences | Explicit crop-event advances and saved maintenance/recovery/delivery animate the farm. |
| Council overload | Explain is local; the optional adviser is a More card and never required. |
| Fear of losing progress | Durable revisions, idempotent actions, checkpoint resume, separate replay attempts. |
| No ending or next step | Recorded result, decision comparison and next-challenge closing cards. |
| Hidden settings/details | More remains a swipeable deck in the same position; Back restores the decision. |

## Card → entity → operation → explanation

| Card | Trusted entity | Action | Explanation |
| --- | --- | --- | --- |
| First order | Frozen lesson order | Queue local planning | Local objective and recipe facts |
| Plan choice | Stored strategy/result hash | Revision-bound selection | Server metrics and provenance |
| Crop checkpoint | Saved simulation world/event | Explicit bounded advance | Dated recorded event |
| B3 maintenance | Teaching bed `bed-03`, named B3 | Record constraint and replan | Local constraint facts |
| Recovery | Retained/alternative strategy | Select eligible recovery | Stored deltas and violations |
| Delivery/debrief | Per-order service events | Review; replay/next challenge | Recorded delivered quantities/cost/disposal |
| Adviser | Validated frozen planning focus | Explicit question only | Asha through existing bounded gateway |

B3 in this new isolated four-bed teaching fixture is not the V13 main-farm
`bed-07` reservation. Neither fixture mutates the other's state.

## Motion and accessibility

Introduction scenes are labelled “Illustrated example.” Gameplay uses server scene
projections. Selection changes focus; maintenance adds a bed barrier; crop stages
change only with saved progress; delivery has a one-shot truck arrival. The board
does not offer another interaction system. Pause, reduced-motion and hidden-document
handling stop decorative motion. Previous/Next and keyboard controls replace swipes.
Vertical gestures remain page scrolls. Inactive cards are hidden from accessibility
APIs; native controls do not bubble into the card's primary-action shortcut.

Dialogs are not required for the beginner flow: Explain, adviser and settings remain
in the card area. Visible focus, live calculation status and 44–50 px action targets
are implemented. See `interaction-review.md` for observed versus static checks.

## Abuse protection

Every application API route uses durable shared admission except the fixed read-only
health probe. Limits include per-network/global API rates, per-session writes,
anonymous-session creation and stricter inference attempts (including invalid IDs
and payloads). The existing provider budget is 48 calls/day, with per-run token,
time and concurrency limits. Admission failure is fail-closed; 429 includes
Retry-After. Same-origin writes and tenant isolation remain enforced. No automatic
inference is made by opening, browsing, calculating or completing a season.
Malformed image preflight now happens before credentials or inference reservation.

## Evidence and remaining limits

- `browser-local.json`: 75 passing checks; 360/390/430/1280 introductions and a
  complete real 390px season, resume, actual delivery, three closing cards,
  monotonic lesson progress and a visibly changed checkpoint after each advance.
- `acceptance-local.json`: 71 passing checks across both lessons; recorded events,
  25 kg combined deliveries, and unchanged main farm.
- Backend tests cover both starting policies, stale revisions/receipts, duplicate
  actions, PostgreSQL concurrency/restart, disabled recovery, failures/replay,
  legacy-route bypasses and per-order completion.
- Initial full regression: 773 passed, one failed, one skipped. The failure was
  invalid-image validation after missing credentials; local preflight fixes it,
  with two focused tests passing. The final full regression is recorded separately.
- Build: approximately 240 kB JavaScript (76.4 kB gzip), 145.58 kB CSS. Removing the old shell
  from the entry bundle removes its previous large-JavaScript warning; CSS remains
  a measured optimization opportunity.

Scripted and agent first-use review are not human usability research. The optional
LLM was not quality-certified by these zero-provider-call journeys; earlier semantic
limitations remain. Agronomic calibration, real operations, general card feeds,
  drag-and-drop, automatic inference and game economies remain out of scope.
