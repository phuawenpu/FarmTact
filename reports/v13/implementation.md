# V13 tactical-card prototype implementation evidence

Evidence date: 17 September 2026 UTC. Status: implemented on unpublished branch
`feature/v13-tactical-cards`. V12 remains the immutable latest published edition;
release and hosting configuration are unchanged from `main`.

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

## Abuse admission

Every API retains durable global and source-IP admission. Authenticated calls also
consume a 900-per-minute tenant/session allowance. Mutations additionally consume
60-per-minute source-IP and 45-per-minute tenant/session write allowances before
body parsing. Provider-bound routes remain narrower: 6 requests per source IP per
minute, 20 per IP per hour, and 12 per tenant/session per hour, plus the existing
concurrency/run budget and shared 48-call provider reservation. These gates are
cumulative and the inverse endpoint is covered by the generic mutation gate.

## Verification

| Check | Result |
|---|---|
| Generated web contracts | PASS — `scripts/generate_web_contracts.py --check` |
| Focused V13/security suites | PASS — 52 tests |
| Full isolated PostgreSQL regression | PASS — 756 passed, 1 skipped, 2 dependency deprecation warnings in 755.97 s |
| Frontend production build | PASS — CSS 172.01 kB; JS 599.11 kB; existing over-500 kB warning retained as an optimization item |
| Responsive browser journey | PASS — 46 checks, zero failures at 360, 390, 430, and 1280 px, including development-only inline/sticky dock checks |
| Screenshots | PASS — `apps/web/screenshots/v13-tactical-{360,390,430,1280}.png` |
| Provider boundary | PASS — no provider mutation before explicit Ask submit; no actual provider credential used in regression/browser evidence |
| V12 preservation / V13 publication | PASS — release/hosting config unchanged; no publication or deployment performed |

The browser journey uses controlled API responses so it can deterministically assert
queued/running/completed transitions and exact server values. The Python suite covers
the real persistence, tenant isolation, idempotency, revision conflict, inverse, focus,
and abuse-admission contracts against PostgreSQL. Neither is evidence of real-farm
efficacy or human comprehension.

## Deferred and measured limits

General server-generated feeds, drag-and-drop, rewards/streaks, card collections,
background inference, new rack/domain entities, human usability claims, and V13
publication remain deferred. Physical phones, native keyboards/dictation, screen
readers, zoom/reflow, and representative farmer sessions remain required before an
accessibility or usability claim. The current JavaScript bundle warning is recorded,
not hidden, and should be addressed through a later code-splitting pass.
