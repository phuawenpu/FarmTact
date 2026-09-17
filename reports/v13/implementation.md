# V13 tactical-card prototype implementation evidence

Evidence date: 17 September 2026 UTC. Status: release candidate on
`feature/v13-tactical-cards`. V12 remains immutable while the V13 candidate is
verified and staged as a separately pinned image/state boundary.

## Implemented scope

- Responsive tactile mission shell with compact card proportions, board, Council
  context, strategy tray, selected-card summary, mobile navigation, and More sheet.
- Server-derived Heavy Rainfall scenario with exact `SIMULATION · SCENARIO ONLY`
  provenance and grow-space B3 mapped to existing `bed-07`.
- Revision-bound Reserve Space proposal using the local planner, persisted job states,
  B3 highlighting, stored result metrics, and signed server deltas.
- Append-only inverse proposal with exact current-revision eligibility and stale Undo
  rejection; original and compensating history are retained.
- Strict optional conversation focus validated against the frozen planning snapshot;
  opening Ask makes zero provider calls and only explicit question submission enters
  the existing DeepSeek path.
- Edition-scoped card selection, horizontal-intent swipe, button and keyboard
  alternatives, normal-flow docking with a safe development comparison flag,
  focus-managed responsive dialog, meaningful motion, and reduced-motion behavior.
- Planner-aligned B3 occupancy: the reservation begins only after the executed
  crop's harvest and sanitation period. Consequences bind to the recalculated
  result's selected strategy even though content-derived strategy IDs change.
- Synchronous client mutation locks plus authoritative server idempotency,
  revision conflicts, tenant checks, and durable admission counters.

## Abuse admission

Every API retains durable global and source-IP admission. Authenticated calls also
consume a 900-per-minute tenant/session allowance. Mutations additionally consume
60-per-minute source-IP and 45-per-minute tenant/session write allowances before
body parsing. Provider-bound routes remain narrower: 6 requests per source IP per
minute, 20 per IP per hour, and 12 per tenant/session per hour, plus the existing
concurrency/run budget and shared 48-call provider reservation. These gates are
cumulative and the inverse endpoint is covered by the generic mutation gate.
New anonymous sessions are limited to 30 per source network and 100 globally per
hour. The production shared-control allowlist includes generic API/session and
write/session rules, edition-scoped to prevent cross-edition tenant collisions.

## Verification

| Check | Result |
|---|---|
| Generated web contracts | PASS — `scripts/generate_web_contracts.py --check` |
| Focused V13/security suites | PASS — 53 focus/inverse/admission tests plus 42 shared-control/admission tests |
| Full isolated PostgreSQL regression | PASS — 757 passed, 1 skipped, 3 dependency/model-schema warnings in 758.42 s |
| Frontend production build | PASS — CSS 172.83 kB; JS 601.77 kB; existing over-500 kB warning retained as an optimization item |
| Responsive browser journey | PASS — deterministic journey at 360, 390, 430, and 1280 px; swipe, buttons, keyboard, stale Undo, focus, reduced motion, and overflow |
| Real backend browser journey | PASS — local PostgreSQL/CP-SAT baseline → Reserve → feasible result/deltas → inverse, with zero automatic provider requests |
| Screenshots | PASS — `apps/web/screenshots/v13-tactical-{360,390,430,1280}.png` and `v13-real-mobile-390.png` |
| Provider boundary | PASS — no provider mutation before explicit Ask submit; no actual provider credential used in regression/browser evidence |
| Blind scripted judging | PASS as evidence collection — three personas, defects/rechecks, and scoped limitations in `judging-personas.md` |
| V12 preservation / V13 publication | V12 source/image remain immutable; publication is a separate pinned-edition operation |

The responsive browser journey uses controlled API responses so it can deterministically assert
queued/running/completed transitions and exact server values. The Python suite covers
the real persistence, tenant isolation, idempotency, revision conflict, inverse, focus,
and abuse-admission contracts against PostgreSQL. A second journey uses the actual
API, database, worker, and local planner. Neither is evidence of real-farm
efficacy or human comprehension.

## Deferred and measured limits

General server-generated feeds, drag-and-drop, rewards/streaks, card collections,
background inference, new rack/domain entities, and human usability claims remain
deferred. Physical phones, native keyboards/dictation, screen
readers, zoom/reflow, and representative farmer sessions remain required before an
accessibility or usability claim. The current JavaScript bundle warning is recorded,
not hidden, and should be addressed through a later code-splitting pass.
