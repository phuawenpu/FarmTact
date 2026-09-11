# V8 UI integration evidence

Generated: 2026-09-11 UTC

## Delivered behavior

- Outcomes now contains a recorded synthetic execution panel for the accepted current mission. A user can create an isolated world, advance its durable civil-date clock by one or seven days, and replan the unexecuted future when at least seven days remain.
- The panel renders the recorded clock, world revision, bed stages, recent task and demand-service events, inventory, harvested/delivered totals, cash, revenue, cost, and replan history. It explicitly states that inference was not triggered and real operations are disabled.
- The farm-map slider is labelled as a static schedule preview. Its maximum is `horizon_days - 1`; 7-, 56-, and 84-day contracts render maxima 6, 55, and 83. Planned harvest and inclusive sanitation dates use `farm.recipe_calendar` metadata from the same canonical schedule-state contract as execution.
- DeepSeek configuration, current verification, historical probe, and last observed execution are shown separately. Configuration does not gate the planning action and does not claim a current execution. Council execution, evidence-reference status, and decision influence are displayed as separate fields; qualitative prose remains explicitly unverified.
- Council planning remains the primary mission action. Numerical-only planning remains visible and was used for all browser verification in this report.
- Scenario branches load in bounded pages, preserve attempt history, and expose cancel/retry controls for active or failed/cancelled numerical attempts. Council research exposes separate local-calculation cancel/retry controls; stopping scripted discussion does not imply cancellation of a calculation.

## Mutation retry contract

`mutationRequest` is the shared mutation transport used by imports, planning/replanning, conversations, council research, scenarios, quest inspection, saved explorer snapshots, and simulation operations.

The session-scoped registry key includes the immutable edition plus request method, API path, and serialized body. A pending idempotency key is written before the request. It survives navigation and reload after a network error, 5xx, 408, 425, or 429; success and definitive 4xx responses clear it. A scenario retry supplies the original run key required by the backend while keeping the retry itself in the same uncertainty-safe registry. Simulation mutations always refresh the current world after a response, because an exact idempotency receipt may intentionally contain an earlier revision.

## Automated evidence

- Production web build: `tsc --noEmit` for app and Node configurations, followed by Vite production build — PASS.
- `tests/browser/v8_simulation_ui.mjs` against a temporary isolated PostgreSQL database with the normal worker enabled — **27/27 PASS**, numerical-only and zero council inference.
  - Verified a 503, then 429, then success reused one key across reloads.
  - Verified success and a definitive 409 cleared their pending operations.
  - Verified mission identity survived reload and room navigation.
  - Verified shared sanitation-calendar rendering and 7/56/84 horizon bounds.
  - Verified create, one-day advance, future replan, seven-day advance, event history, totals, and zero unexpected request failures.
  - Verified no body overflow at 360, 390, 430, and 1280 CSS pixels.
- `tests/gameplay/test_simulation_execution.py` — **3 passed**.
- `tests/gameplay/test_v8_reliability.py tests/council_research/test_v8_history.py` — **7 passed**.
- `tests/models/test_synthetic_evaluation.py tests/models/test_v8_availability_adversarial.py` — **9 passed**.

Machine-readable browser results: [`ui-browser.json`](ui-browser.json).

Screenshots:

- [`360 px mobile`](../../apps/web/screenshots/v8-recorded-simulation-360.png)
- [`390 px mobile`](../../apps/web/screenshots/v8-recorded-simulation-390.png)
- [`430 px mobile`](../../apps/web/screenshots/v8-recorded-simulation-430.png)
- [`1280 px desktop`](../../apps/web/screenshots/v8-recorded-simulation-1280.png)

## Limits

All execution evidence here is deterministic synthetic simulation. It is not a real farm observation, real task completion, purchase, delivery, or buyer communication. The numerical models have not been validated on real-farm outcome data. This browser run did not make a paid or live DeepSeek call, and it provides no claim that current provider inference is verified.

The browser harness uses a local edition-path proxy because the standalone backend is not the public multi-edition gateway; `/api/releases` 404 responses in that harness are expected and excluded from unexpected-request failures. Deliberately injected 503, 429, and 409 responses are recorded in the JSON report as retry-contract evidence.
