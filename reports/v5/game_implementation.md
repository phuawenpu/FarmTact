# V5 decision journey implementation

## Result

The farm now opens with a dated, quantified planning mission derived from the active owned farm snapshot. The mission groups actual booked orders by crop and due date, checks harvest shelf life and inventory validity, and presents the earliest positive supply screen. Weekly EWMA demand remains separately labelled as context. The screen calls the result provisional because it does not allocate supply across earlier orders; the numerical planner remains the source of actual delivery shortfall.

The mission preserves its crop, date, snapshot ID/hash and linked evidence through World, Scenario Lab, results, and saved playground experiments. A versioned, validated session cache rejects stale schemas and malformed values. An imported farm rederives the mission from the owned snapshot whose farm payload matches the active bootstrap farm. Older farm snapshots are inspectable but cannot be silently run as the current farm; reference data must be saved, while saved/scenario snapshots continue through their owned experiment root.

Saved-result recovery and result rendering require both the frozen baseline hash and comparison root. A farm mission attaches only to `farm:<snapshot hash>`; a playground result with the same raw reference hash remains inspectable but cannot resume under, compare with, or claim evidence from the farm mission.

## Gameplay and evidence changes

- Scenario controls pair sliders with exact bounded number inputs.
- Calculation waiting copy says that the worker is computing and biological farm time is not advancing.
- Terminal saved results have a visible reload recovery action.
- Seven specialist cards are deterministic templates over the frozen numerical result. They identify their evidence and explicitly state that they are neither inference nor agent messages.
- Margin, cost and shortfall changes retain direction with “increases”, “decreases”, or “unchanged”.
- Recipe maturity uses nursery plus grow days; sanitation remains post-harvest turnaround.
- The real cached News panel appears near the World mission and against saved scenario evidence. The existing paid Asha/council action remains deliberate and separate.
- Result sounds are classified from final evidence, with technical failure and withheld/no-feasible states taking precedence over shortfall. Only user-started terminal events are cued once; polling, replay and date previews do not produce completion cues.

## Verification

`tests/browser/v5_gameplay_candidate.mjs` exercises the full decision loop at 360, 390, 430 and 1280 pixels using the shared authenticated review session. It changes an exact demand value, submits a real local numerical job, inspects all seven evidence views, reloads and resumes the saved result, rejects a malformed cached mission, and verifies saved playground snapshot routing. It also records inference requests and page errors.

`tests/browser/v5_decision_semantics.mjs` separately checks the reference fixture semantics: 28 kg of dated Pak Choi bookings, a separately identified 33 kg weekly forecast, zero shelf-life-eligible harvest, a 35-day nursery-plus-grow recipe rather than 37 days including sanitation, signed delta wording, and malformed-cache recovery.

The final gameplay journey passed 30 of 30 checks. It expands the actual contributing records before changing assumptions and verifies that a remembered explorer result cannot resume under the main-farm mission. When a saved playground fixture is absent, the test creates a named reference-based snapshot and exercises its owned-snapshot and reload path. The focused decision semantics passed 6 of 6 checks. The delayed snapshot race check passed 3 of 3: old mission and experiment actions disappear while the selected snapshot loads. `tests/audio/test_sound_semantics.mjs` passed 8 of 8 classification checks, including withheld and no-feasible priority over shortfall and safe handling of unknown statuses. The production TypeScript and Vite build passed; browser evidence is recorded in `reports/v5/game_browser.json`.

Final frozen web assets: `index-fxjcA9To.js` and `index-DlATHyWR.css`.

No council, conversation-message, or other provider request is made by either numerical test.
