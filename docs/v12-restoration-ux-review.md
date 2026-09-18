# V12 restoration: source review and comparative walkthrough brief

V12 is the product baseline. This review inspects immutable V12 `9fd57898`,
V15 `a5ab2a8` and V19 `ef4cba0`, plus their retained test evidence. The first
sections identify source findings; the final section records a fresh, bounded
interactive walkthrough of those original sources. Neither is a human usability
study.
Restore and publish the V12 interface first; improvements belong in a subsequent
candidate so that restoration is independently verifiable.

## What to preserve

V12 names the destinations: Plan, Farm, Council research, Farm tools, Crops, Data,
Outcomes and Setup. Its Plan page makes the farm board, seven Council roles,
comparison cards and reviewed actions visible in one continuous workflow:
observe → discuss → decide → approve → act → verify → replan. Keep these named
destinations, direct actions, information depth and board. Council research is a
distinct experiment; Planning Council reviews the current frozen plan.

V12 final source already includes inspected Inbox fields/warnings/provenance,
manual review candidates, specialist conversation history and an explicit
“Review a proposal from this discussion” handoff. Earlier pre-release audits
describe gaps that were subsequently fixed. Do not mistake those old findings
for missing capabilities in the published source.

## Comparison supported by the inspected source

| Version | Useful behavior | Cost or limitation | Application to V12 |
| --- | --- | --- | --- |
| V12 | Named sections, visible specialist roster, explicit Apply/recalculate and separate approval, rich records and data | Long planning page; workflow rail looks actionable but only changes local phase styling; dialog keyboard behavior is incomplete | Keep structure; make existing controls truthful and easy to reach |
| V15 | Preview labels, deterministic explanations, explicit reviewed mutations, returning to origin card/focus/scroll | Sequential cards and the generic More index replace visible destinations; users must discover tools in a deck | Borrow preview/explanation/return behavior without the card shell |
| V19 | Compact allocation count, affected beds, dates and optional Council status beside a plan | Council occupies the primary strategy action; other decisions require navigating onward, and tools remain behind More | Put a small brief beside V12 comparison cards and keep Council a separate optional action |

These are concrete interface properties. Claims about actual confusion or task
completion require the fresh walkthrough below.

## Small improvement packages after restoration

1. **Truthful workflow navigation.** In `FarmerWorkflow.tsx`, the rail currently
   calls only `setPhase(id)`. It neither navigates to the corresponding section
   nor performs work. It marks all earlier positions complete using
   `index < phaseIndex`, so clicking Replan can visually complete prior stages.
   Separate the focused section from server-evidenced progress. Each rail
   control should scroll/focus its corresponding existing section; unavailable
   sections should explain the required preceding result. Completion must use
   saved calculation/proposal/task/report evidence. Optional Council review must
   not block numerical planning or appear completed merely by navigation.
2. **Make comparison and board agree.** `MetricStrip` receives the locally chosen
   strategy, while `FarmBoard` independently chooses the saved strategy or first
   result. Selecting an Alternative can therefore change metrics without
   changing the board. Pass the selected preview strategy explicitly to the
   board and label the projection “Preview—not saved.” Add the selected strategy
   name, affected beds and dated allocations beneath the existing cards. Render
   the complete schedule in a disclosure, including multiple cycles on a bed;
   do not imply the board's one-tile-per-bed representation is the full schedule.
   Keep Apply & Recalculate and approval as the existing explicit boundaries.
3. **Accessible dialog return.** The shared V12 `Dialog` declares modal semantics
   but has no initial focus, focus containment, Escape handler or opener return.
   Add those behaviors for Inbox, specialist, proposal, approval and explainers.
   Preserve the page's scroll position. Keep unsent field state when a dialog is
   temporarily left; use explicit discard where closing would lose edits.
4. **Make the next action understandable.** Beside the existing decision actions,
   show the selected strategy and why approval is available or unavailable.
   Readiness comes from the existing revision-bound server proposal, not a new
   client policy. Label local selection as a preview and distinguish stored
   Council findings from a new submitted review. Provide a contextual jump to
   the already visible Council table, keeping Calculate/Apply/Approve prominent.

Packages 1–3 have direct code evidence. Package 4's final wording and placement
should be informed by the walkthrough. Do not introduce another tutorial mode,
three-button ceiling, universal deck, numerical model or provider requirement.

## Fresh comparative walkthrough to perform

Run original V12, V15 and V19 privately with separate ordinary demo sessions.
Capture desktop and 390px journeys, then check 360/430px, keyboard and reduced
motion. For each task, record visible entry point, actions taken, scroll/context
loss, state label and outcome. Do not equate an endpoint response with usable UI.

- First visit: identify the farm, demand, next numerical action and demo boundary.
- Calculate and compare: find the plan's metrics, dates, affected beds and tradeoff;
  verify selection changes only a preview until explicit application.
- Council: locate seven roles, read recorded evidence/history and find the reviewed
  proposal handoff. Avoid live inference during inspection; use captured fixtures
  for unavailable/partial/withheld states and clearly label them.
- Find Crops, Council research, Data, Setup and Outcomes from the current task;
  inspect relevant detail and return without losing context.
- Complete reviewed import → proposal → recalculate → approve sandbox tasks →
  report → correction/recovery; test interrupted and stale requests.
- Leave and return, reload, and operate dialogs by keyboard; inspect draft and
  focus retention. Record causal transitions in normal motion, not just stills.

Acceptance for the later candidate: unchanged V12 destinations and capabilities;
no completion caused by browsing; selected metrics/board/schedule share one frozen
strategy; keyboard dialogs restore their opener; previews/reading cause neither
provider calls nor farm writes; saved-state feedback follows server confirmation.
Public release evidence must separately identify the restored baseline and any
subsequent improvement edition. Representative-user comprehension remains untested.

## Interactive inspection, 18 September 2026

Original source copies were served privately at localhost ports 4212, 4215 and
4219 against isolated APIs. Screenshots and browser observations are retained in
[curated evidence](../reports/v12-v15-v19-walkthrough/README.md); application sources were unmodified. The Vite
proxy adapter and isolated test services differ from historical deployment. A
Playwright route guard blocked review/conversation/invite/Council POST endpoints;
no provider was invoked. Screenshots listed below were opened for visual inspection.

- **V12 first visit, 390px and desktop:** named navigation is visible. The hero,
  guidance, metrics and all 16 bed tiles precede Calculate options, placing the
  first numerical action several mobile screens down. Desktop initial content is
  2115px tall at a 1280×900 viewport. In V15 and V19 the initial desktop task fits
  a 900px page. Keep V12's board, but place its Calculate action above the board
  as well as below and reduce the hero's mobile footprint.
- **V12 calculate and compare:** real local calculation completed and displayed
  Lean/Balanced/Resilient alternatives, seven specialist entries and separate
  Apply/Approve controls. Choosing Lean changed the metric strip but left the
  board text unchanged ([v12-specific.json](../reports/v12-v15-v19-walkthrough/v12-specific.json)), confirming the source mismatch.
- **V12 rail:** after calculation, clicking Replan left scroll at zero and changed
  completed tick count from one to six ([walkthrough.json](../reports/v12-v15-v19-walkthrough/walkthrough.json)). This is observed
  false progress, not a hypothetical usability concern.
- **V12 Inbox:** opening the dialog left keyboard focus on the underlying Inbox
  opener; pressing Escape did not close it ([v12-specific.json](../reports/v12-v15-v19-walkthrough/v12-specific.json)). This supports
  the proposed shared dialog accessibility fix.
- **V12 sections:** Crops, Data and Council were each reachable by one named
  bottom-nav action; Plan returned to the calculated workflow. Crops displayed
  the searchable catalogue; Data exposed Overview/Generator/Records/Public
  context/Experiments; Council showed a focused experimental farm and explicit
  challenge controls. The private historical V12 crop image URLs initially failed under the prefixed
  Vite route. Correcting only the route adapter restored all twelve images; the
  recaptured screenshot confirms intact original assets.
- **V15 knowledge:** from the plan, More → Next → Next → Open tool reached Caixin
  as card 1 of 22. It showed crop stages, limitations and cited references, but
  no immediately visible category index. The persistent farm scene occupies the
  top of the page even while reading crop evidence. Rich content exists; finding
  another type of information requires navigating the sequence.
- **V19 knowledge:** More displays a named tools index and Knowledge opens a
  second library index with Crops/Sources/Specialists and saved Council links.
  This improves V15 discoverability, but adds hierarchy compared with V12's
  direct section labels. The initial three-step demo further delays access until
  completed or skipped. Keep the explicit category naming, not the extra shells.

Observed screenshots: [v12-initial-390.png](../reports/v12-v15-v19-walkthrough/v12-initial-390.png), [v12-desktop.png](../reports/v12-v15-v19-walkthrough/v12-desktop.png),
[v12-crops-390.png](../reports/v12-v15-v19-walkthrough/v12-crops-390.png), [v15-initial-390.png](../reports/v12-v15-v19-walkthrough/v15-initial-390.png), [v15-knowledge-390.png](../reports/v12-v15-v19-walkthrough/v15-knowledge-390.png),
[v19-desktop.png](../reports/v12-v15-v19-walkthrough/v19-desktop.png), [v19-knowledge-390.png](../reports/v12-v15-v19-walkthrough/v19-knowledge-390.png). Actual observations do not establish
new-user comprehension. V15/V19 numerical calculations were temporarily deferred during CPU contention
and then completed sequentially. The later sections complete bounded V15/V19 mutation/recovery and normal-motion
recordings; representative-user testing remains outstanding.

The V19 numerical calculation also completed locally. Its strategy card showed
14 allocations across 11 beds with a useful compact decision brief. At 390px,
the board overlay labels are very small, and the full strategy page is about
1400px tall; Council is the primary action while applying a decision requires
continuing to another card. Borrow the brief and explicit preview label, keeping
V12’s direct decision controls and readable board labels. V15/V19 Experiments
were also opened: V15 initially reveals only Scenarios & quests (1 of 5), whereas
V19 exposes an index containing scenarios, Data Explorer, generation, Council
research and Waste Rescue. These are discoverability differences, not lost
backend capabilities.

V15’s local calculation completed too ([v15-calculation.json](../reports/v12-v15-v19-walkthrough/v15-calculation.json)). Its Lean card
showed 44.5% Delivery covered, 604kg Shortfall and SGD1,166.7 Cost; its primary
action was the nonspecific Continue. V19 improves this by naming all-demand
coverage/shortfall and explaining the selected order is not separately reported.
Use similarly precise metric labels in V12 while preserving booked-demand labels
where those are the actual metric basis. Do not silently relabel values.

## Original V15 mutation and recovery follow-through

After the restoration regression completed, the historical V15 services were
restarted alone. The existing full card journey was adapted only for temporary
paths and the private server, with provider routes blocked. Its real workflow
passed 26 assertions: comparison, explicit reservation review, apply/recalculate,
five-part explanation, reviewed inverse, approval producing 52 sandbox tasks,
and an explicit seven-day History advance with server-recorded scene state.
The normal-motion transition terminated; reduced motion retained the same facts.

A second real UI journey reported a failed harvest task, observed
`recovery_required`, replanned future work, read the retained-schedule comparison,
and verified that report data was preserved and focus/scroll returned exactly to
Replan future work. All seven assertions passed. The workflows are functional;
the main comparative weakness is discoverability and context, not absent backend
capability.

Evidence: [mutation assertions](../reports/v12-v15-v19-walkthrough/v15-mutation.json),
[recovery assertions](../reports/v12-v15-v19-walkthrough/v15-recovery.json), and
[normal-motion recording](../reports/v12-v15-v19-walkthrough/v15-normal-motion.webm).
The mutation recording is 43.72 seconds. Inspected frames show saved signed deltas,
the B3 reservation label and 52 created sandbox tasks. This is an automated causal
sequence, not a representative-user comprehension claim.


## Original V19 mutation and recovery follow-through

The same private sequential walkthrough passed 26 mutation/scene assertions and
seven failed-task recovery assertions on original V19. Reservation review,
apply/recalculate, inverse, sandbox approval, seven-day recorded advance, finite
motion and reduced-motion facts all passed. Recovery retained the original report
and returned to the action at the same 522px scroll position. No provider requests
were made. The services were stopped after verification to free local CPU.

Evidence: [mutation assertions](../reports/v12-v15-v19-walkthrough/v19-mutation.json),
[recovery assertions](../reports/v12-v15-v19-walkthrough/v19-recovery.json), and
[normal-motion recording](../reports/v12-v15-v19-walkthrough/v19-normal-motion.webm). The mutation video
is 43.04 seconds. Visually inspected extracted frames show the recorded server
consequence and saved reservation state. Together with V15 this establishes the
bounded workflows and factual transitions work; it does not prove discoverability
or comprehension. The interface lesson is to retain clear consequences and reliable
returns while exposing those same operations directly within V12’s named workflow.

### Final recommendation

Make the V12 baseline public independently. Apply only the observed correctness
and navigation fixes in its follow-up: genuine phase jumps/evidenced progress,
consistent selected-plan preview and dated schedule, modal keyboard/return behavior,
and a visible early Calculate control. Keep Council optional and visible beside
V12’s explicit actions. Restore rich sections as ordinary named destinations;
never infer that a passing 26-step automation justifies replacing them with a deck.
