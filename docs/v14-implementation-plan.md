# V14: one farm, one decision, one action area

Follow-up: the [live UX review](../reports/v14/animation-explanation-review.md) found
explanation, motion and capability-access gaps despite the completed technical
journey. The [proposed V15 integration spec](v15-integrated-card-experience.md)
addresses them and is being implemented privately; acceptance and publication remain pending. This document remains the historical V14 plan.

Approved scope: replace the edition chooser with an illustrated, animated introduction
at `/`; serve the latest game at `/play`. Retire old public editions while retaining
immutable source/image history and recoverable state. No public version navigation.

The first season uses an isolated four-bed teaching fixture and existing numerical
crop recipe. One order, two meaningful calculated options, explicit event advances,
a dated B3 maintenance constraint, recalculated recovery and recorded delivery lead
to an honest debrief. All gameplay is card swiping and the consistent action area;
the 2.5D farm is noninteractive and automatically frames the consequence. Explanation,
journal, settings, replay and contextual adviser questions stay in card decks.

## Ownership

- Root: shared contracts, application integration, specifications, end-to-end tests,
  numerical/security verification, commits, publication and evidence.
- `v13_focus` (existing GPT-5.6-Sol specialist): beginner journey service, isolated
  teaching fixture, focused backend tests and necessary planning hooks.
- `v13_ui` (existing GPT-5.6-Sol specialist): beginner intro/game/scene components,
  isolated styles and frontend journey adapter.
- `v13_evidence` (existing GPT-5.6-Sol specialist): public routing, latest-only
  publication/retirement compatibility and focused deployment tests.

No recursive delegation; at most three specialists plus root. Work on
`feature/v14-first-season`. Existing V13 source/image remain immutable.

## Required boundaries

Authoritative facts, eligibility, next checkpoint and progress are server-owned.
Use current-revision idempotent actions and existing local planner/simulation ledger;
never derive yields or completion in the browser. Preserve executed work. Replay
creates another attempt. Optional AI requires explicit submission through existing
validated snapshot focus and all durable abuse/provider gates. Opening, browsing,
calculating and progressing require no inference. Actual farm operations remain off.

Landing animations say “Illustrated example”; actual gameplay animations follow
saved simulation events. Reduced motion, pause, 44px controls, keyboard/button
equivalents and no page-scroll interception are required. Only the active card is
interactive. Forms may accept input within cards but submit from the action area.

## Acceptance

Fresh visitor intro → order → calculate → choose → progress → maintenance → recovery
→ delivery → debrief → replay/next/explore. Resume at each checkpoint. Numerical
fixtures must prove distinct feasible choices and recoverable maintenance. Verify
duplicate actions, interruption, stale revision, rate limits, tenant isolation,
zero automatic inference and preserved main-farm state. Test 360/390/430/desktop,
inspect screenshots, run contracts/build and Python/PostgreSQL regression. Blind
scripted reviews test comprehension without an external manual; no human claims.

Publish a new immutable numbered release only after checks; current unnumbered
paths route to it. Verify the new public journey before stopping previous workers.
Archive prior state instead of invoking destructive retired-state cleanup.
