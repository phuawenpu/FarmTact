# V5 decision journey independent review

Reviewed 2026-09-09 as a read-only audit of `DecisionJourney`, `App`,
`DataExplorer`, `GamePanels`, `lib/game`, the explorer API record contract and
scenario/planning terminal semantics. This review did not rebuild, mutate a farm,
submit a provider request or treat browser fixtures as real farm outcomes.

## Decision

The journey has a coherent numerical spine: it starts from a dated booked order,
keeps weekly EWMA context separate, calls its simple supply comparison a screening
gap, and carries the selected owned snapshot into a local scenario. Saved and
scenario datasets remain on their explorer experiment roots; old main-farm
snapshots and the unsaved reference cannot masquerade as the active farm.

Three defects were found during final review and corrected by the implementation
agent before this report was closed:

1. Ravi's stance used the **change** in shortfall rather than the scenario's actual
   shortfall. An unchanged positive shortfall therefore appeared as “supports.”
   The statement still describes the delta, while the corrected stance and
   expanded fact use actual scenario `shortfall_kg`.
2. Asha's expandable violation evidence used `String(object)`, yielding
   `[object Object]`. The corrected formatter shows code/message, entity, required
   and available quantities, and unit.
3. After importing/replacing the active farm, `mainMission` remained visible while
   the asynchronous explorer lookup searched for the matching new farm snapshot.
   During that interval a user could open the old mission against new farm state.
   `loadBootstrap` now clears farm-kind mission state before loading, then publishes
   the newly derived mission only after an exact owned-farm match. A saved-dataset
   mission remains separately preserved.

## Dated-order and biological semantics

`deriveDecisionMission` groups future orders by crop and exact due date, subtracts
cancelled kilograms, and selects the earliest positive provisional gap (largest
gap breaks a same-date tie). It admits a scheduled harvest only when its crop
matches, its harvest is no later than the delivery, and harvest plus declared
shelf-life reaches that delivery. Inventory similarly requires harvest no later
than delivery and expiry no earlier than delivery.

This intentionally does not allocate a harvest or lot across earlier orders and
does not apply storage loss. The card discloses both limits and leaves actual
shortfall to the planner, preventing double-counted screening supply from becoming
a fulfilment claim. It calls EWMA a containing-week statistical forecast and does
not substitute it for booked quantity.

New-sowing timing sums nursery and grow days. It excludes sanitation/turnaround
from biological maturity and labels the result as a declared recipe estimate. The
Pak Choi fixture therefore uses 35 days and reaches 13 October from an 8 September
planning date, after the 21 September delivery. Production's maturity miss now
blocks only that specific new-sowing option; it no longer implies that the whole
solver result is biologically blocked.

## Snapshot routing and cache

- `App` derives the farm mission only from an owned explorer farm detail whose
  farm payload exactly equals the authenticated bootstrap farm.
- The farm view receives only `mainMission`; selecting a saved playground mission
  cannot replace the active farm's card.
- Data Explorer derives its card from the currently loaded detail. An active farm
  can continue to Farm/Scenario Lab; an older farm is inspectable only; the
  reference must be saved; saved and scenario details continue to Experiments.
- Snapshot selection is edition-scoped and a saved selection survives reload.
  Scenario creation then supplies the selected `explorer_snapshot_id` or owned
  `parent_scenario_id`, preserving backend tenant and comparison-root checks.
- The session mission schema is versioned and validates required strings, finite
  nonnegative quantities, ISO-shaped dates, evidence IDs and positive recipe days.
  Old/malformed schemas are discarded and rederived. It is a navigation aid, not
  the numerical input; the backend-owned snapshot remains authoritative.

The import race above was the material cache/state gap. The corrected bootstrap
lifecycle removes the previous card before the lookup, while exact equality still
prevents an old snapshot from becoming the new main mission.

The isolated real-import journey deliberately delayed that lookup. The old card
and action disappeared; the imported farm's Pak Choi booking then appeared as 37
kg with its exact owned version-2 snapshot hash, and reload preserved it. The run
passed **12/12** with no numerical, conversation or provider request and did not
load or mutate the shared browser state.

Final result selection filters displayed columns against one comparison root, so
incompatible farm/playground branches cannot render together. Mission evidence is
attached only when its baseline hash matches and a farm mission has the explicit
`farm:<snapshot hash>` root. A playground with the same raw hash therefore cannot
borrow a main-farm mission. `affected_deliveries` remains honestly labelled as
“deliveries to inspect,” rather than fulfilled, failed or changed orders.

## Numerical perspectives

The seven cards are deterministic templates over frozen controls, policy deltas,
status and violations. They deny inference and agent-message status. Weather
reports no connected weather/yield adjustment; Market calls demand a player
assumption rather than sentiment; Profit preserves increase/decrease direction;
Planner checks solver feasibility and recorded violations. Expandable evidence is
the right interaction pattern once object constraints are formatted legibly.

The interface should treat stance as present-state decision guidance and the
sentence as comparative evidence. A zero delta does not imply no operational
problem. This is why actual scenario shortfall must drive Ravi's warning state,
while the delta text can honestly say it is unchanged.

## Real time, farm time and inference

The waiting state says “Calculation time” and explicitly says farm time is not
advancing. Sliders, previews and scenario polling do not create biological
observations or move the planning date. Results remain frozen and recoverable after
reload. Paid Asha/council interpretation is a separate explicit action after the
numerical cards; the candidate browser trace recorded no inference submissions in
the local journey.

## Outcome sounds

Planning runs prioritize failure/cancellation/stale input as error and
review-withheld/no-feasible-plan as withheld, then use the accepted/Balanced/first
strategy's actual shortfall before completion. Only user-started run IDs are armed,
and polling duplicates are suppressed. Replay and date preview do not emit a
success cue.

Scenarios map every status other than `COMPLETED` to error, then prioritize
NO_FEASIBLE_PLAN as withheld before inspecting selected-policy shortfall. Unknown
or future technical terminal statuses cannot fall through to complete.

## Verification basis and remaining acceptance

The existing focused browser evidence covers the quantified mission, shelf-life
screen, weekly forecast distinction, recipe maturity, exact controls, waiting
language, seven roles, signed deltas, explicit paid advice, reload recovery,
responsive widths and absence of inference calls. Its earlier saved-fixture failure
was a test prerequisite; the revised journey creates a saved reference dataset when
one is absent and then checks owned selection and reload routing.

Human comprehension was not studied. A future play study could ask participants to
identify the dated gap, inspect linked inputs, change one assumption, and explain
why a provisional gap can differ from planned shortfall. This is an explicitly
unperformed study, not evidence for or a new approval gate on this release.
