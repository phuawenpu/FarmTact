# A10 — Mobile UI implementation report

## Objective

Build the FarmTact web experience as a mobile-first tactical farm board rather than a chat dashboard. Bind the interface to the frozen frontend view contract, keep synthetic/public and test/replay modes explicit, and provide honest loading, empty and failure states without client-side forecast values.

## Delivered

- React 19 + TypeScript + Vite application with an isolated `apps/web/package.json` and npm lockfile.
- Responsive app shell with a desktop rail and five-item mobile thumb navigation.
- Tactical board with code-native SVG crop illustrations, growing stages, actual bed progress, harvest dates, persistent data/execution/simulation labels, and horizontal mobile board controls.
- Mission lifecycle UI using idempotent planning-run creation, SSE updates, polling fallback, automatic Balanced acceptance, replay, and a single clearly labelled synthetic crop-delay replan.
- Three-way strategy comparison using backend metrics only; accepted candidate is first on mobile. Detailed sheet shows service, margin, harvest, shortfall, waste, cost, constraint violations and assumptions.
- Harvest timeline with crop-stage cards and a keyboard-accessible table alternative.
- Resource meters derived from backend strategy usage and declared farm capacities.
- Advisor characters and concise evidence cards. With no claims, the roster explicitly waits rather than presenting invented conversation as activity.
- Data room with public/synthetic origin, observed/retrieved timestamps, freshness, execution mode and source links. Seven current source cards were exercised in-browser.
- Ten-card crop library with alias search, recipe status, warnings, and detail retrieval from `/api/v1/crops/{id}/evidence`; evidence title, finding, limit, year and source link are expandable.
- Outcomes room with backend weekly demand/harvest series, simulation metrics and stored replay mode.
- Setup room with one-click `{fixture:"synthetic_demo"}` import and client-parsed JSON `{farm}` import. The client enforces a 1 MB pre-check and never executes uploaded content.
- Reduced-motion CSS, visible focus treatment, Escape-close dialogs, explicit units, Singapore date formatting, source links with safe external-link attributes, and no drag-only interaction.

## Files changed

- `apps/web/index.html`
- `apps/web/package.json`
- `apps/web/package-lock.json`
- `apps/web/tsconfig.json`
- `apps/web/tsconfig.app.json`
- `apps/web/tsconfig.node.json`
- `apps/web/vite.config.ts`
- `apps/web/src/main.tsx`
- `apps/web/src/App.tsx`
- `apps/web/src/styles.css`
- `apps/web/src/lib/types.ts`
- `apps/web/src/lib/api.ts`
- `apps/web/src/components/Visuals.tsx`
- `apps/web/src/components/Board.tsx`
- `apps/web/src/components/Rooms.tsx`
- `apps/web/dist/` production output
- `apps/web/screenshots/` visual verification artifacts
- `reports/agents/mobile_ui.md`

## Interface and schema notes

The client consumes frontend view contract v1 unchanged. The only integration adapter detail discovered during live verification was that crop detail is returned as `{crop,evidence}` from `/api/v1/crops/{id}/evidence`; the client unwraps the crop and attaches the evidence records for display. The source adapter was exercised with nullable observation times and scalar or list units. Strategy constraint violations accept either a string or the backend structured constraint object.

Planning creation sends `{council:true}` with a unique `Idempotency-Key`. Replanning sends `{disruption:"crop_delay"}` with a unique key. Browser verification created its deterministic mission with `council:false` outside the UI, following master-agent direction, so no duplicate paid inference occurred.

## Verification performed

- `npm install`: 28 packages installed; npm reported 0 vulnerabilities.
- `npm run build`: passed TypeScript checks and Vite production build. Final raw output was 243.42 kB JavaScript and 33.18 kB CSS; gzip output was 74.84 kB and 7.86 kB respectively.
- Installed Playwright Chromium and its Linux runtime packages for actual browser inspection.
- Browser exercised Board, Crops, Data, Outcomes and Setup at 360, 390, 430 and 1280 px widths.
- Browser checked body-level horizontal overflow at every requested width: none found. Deliberate farm/strategy rows remain horizontally scrollable inside their own containers on mobile.
- Browser console and page-error collection across all widths: zero errors.
- Browser exercised crop search, evidence modal, Escape close, strategy sheet, visual timeline, accessible timeline table, five-room navigation and route-backed data states.
- Accepted-run integration returned `ACCEPTED_FOR_SIMULATION`, three strategies, automatic Balanced selection and actual numerical data.
- Stored replay returned and displayed `execution_mode=replay`; browser confirmed scroll reset to the top and no new inference route was used.
- Crop-delay replan returned an actual parent-linked run with `disruption.type=crop_delay`, `origin=synthetic`; the UI displayed the simulation banner while running and after automatic acceptance.
- Current source integration returned seven cards, including five NEA/public current-information entries, with provenance fields rendered.
- Final correctness pass changed fill-rate copy to “demand filled,” recipe progress to “cycle elapsed,” and raw system/execution identifiers to human-readable labels. A read-only Playwright pass against the final integrated browser session confirmed all labels, `DeepSeek text`, `Public refresh`, and zero console/page errors.
- Accepted worklist links are present in the strategy sheet and Outcomes room. The final integrated session requested its latest accepted `/worklist.csv` and received HTTP 200; no mission or paid inference was started during this pass.
- Dependency ranges are pinned to the exact versions resolved in the npm lockfile. Both `npm install --package-lock-only` and a clean `npm ci` completed with zero reported vulnerabilities before the production build.
- Fresh sessions expose three distinct actions: “Plan with DeepSeek council” (`council:true`), “Plan with numerical tools” (`council:false`), and “Replay recorded demo” (`GET /api/v1/demo/replay`). The shared replay is visibly labelled as stored replay activity and keeps worklist/replan controls disabled while leaving both own-mission actions available.
- The shared replay UI was browser-verified against the exact curated `data/fixtures/deepseek_demo_replay.json` artifact while the running service awaited restart for its newly added route: shared/replay labelling visible, three compact advisor cards rendered, zero worklist links, zero disruption controls, both own-mission actions visible, no overflow or page errors. No API planning POST was made.

Key inspected screenshots:

- `apps/web/screenshots/accepted-board-360.png`
- `apps/web/screenshots/accepted-board-390.png`
- `apps/web/screenshots/accepted-board-430.png`
- `apps/web/screenshots/accepted-board-1280.png`
- `apps/web/screenshots/accepted-strategies-390.png`
- `apps/web/screenshots/balanced-sheet-390.png`
- `apps/web/screenshots/timeline-390.png`
- `apps/web/screenshots/timeline-table-390.png`
- `apps/web/screenshots/data-390.png`
- `apps/web/screenshots/crop-evidence-390.png`
- `apps/web/screenshots/disruption-accepted-390.png`
- `apps/web/screenshots/replay-top-390.png`
- `apps/web/screenshots/final-integrated-outcomes-390.png`
- `apps/web/screenshots/fresh-mission-actions-390.png`
- `apps/web/screenshots/shared-recorded-demo-390.png`

## Sources and assumptions

Implementation followed `CODEX_START_PROMPT.md`, Section 0 and Sections 9.4/10/11 of `FarmTact_Build_Specification.md`, the frozen frontend view contract from the master agent, and the runtime mode/provider constraints in `FarmTact_DeepSeek_Runtime_Specification.md`. The frontend does not call a model provider. It treats the same-origin API as the authority for all farm, source, crop and strategy values.

The crop illustration shape and interface colors are presentational; they are not diagnostic evidence. No live value, yield, business result, source status or planning event is invented in the client. Static UI transitions are limited to loading, event toast and user-opened sheet state; reduced-motion preferences suppress them.

## Risks and limitations

- API responses rely on the frozen TypeScript contract rather than a generated runtime decoder. Missing optional fields have safe display paths, while a structurally invalid required payload is expected to fail visibly instead of being silently fabricated.
- Source freshness is displayed exactly as supplied. The client does not recalculate freshness from wall-clock time.
- The development UI deliberately exposes simulation/replay and accepted-for-simulation state. It provides no real-farm execution or operational approval control.

## Proposed next task

Keep the browser assertions under the root-owned test suite and add screenshot-diff baselines after final fonts/rendering are stable in CI. Re-run the same width matrix whenever the shared API view contract changes.

## Final reproducible browser suite

`node tests/browser/run.mjs` now performs the complete same-origin workflow from a fresh authenticated browser session. It loads the real shared replay, starts one `council:false` mission through the visible UI, downloads the accepted worklist, reads terminal SSE history, submits one numerical crop-delay replan, confirms the old worklist becomes stale, exercises keyboard dialogs/table/data/crop evidence, checks 360/390/430/1280 widths, and saves final screenshots plus `reports/browser.json`.

Final result: **PASS, 44/44 checks**, zero console errors and zero uncaught page errors. Numerical run and replan both reached `ACCEPTED_FOR_SIMULATION` with `council_status=not_run` and three strategies. The suite made no paid council request.

The final presentation pass uses compact accepted-run heroes so crop tiles remain visible in the initial 390 px viewport. Acceptance copy now distinguishes numerical-only validation from a run containing a validated independent critic. Automated screenshots disable finite animation and hide the caret; the inspected Balanced sheet is fully opaque with stable geometry and no underlying content bleeding through its surface.

Plan resources now distinguish summed quantities from peak constraints. Area is labelled “New sowing area” with an explicit note that peak occupancy is validated separately. Labour is labelled for the full planning horizon and compared with `labour_hours_per_week × ceil(horizon_days / 7)`. The suite verifies the computed accessibility-meter maximum and confirms the misleading weekly label is absent. See `apps/web/screenshots/final-plan-resources-390.png`.
