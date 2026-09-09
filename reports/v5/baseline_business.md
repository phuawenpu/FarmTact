# V5 planning baseline — business, game and judging review

Date: 2026-09-09 UTC  
Reviewed build: live immutable V4, `https://farmtact.fly.dev/v4/`  
Perspective: independent AI review as a first-time younger learner, a practical grower and a hackathon judge  
Scope: planning evidence only. This report proposes V5 work; it does not claim that V5 exists.

## Method and limits

The review used Sumin Lee's full seven-page business thesis and only page 13 of the original hackathon briefing. Page 13 defines seven judging areas: goal and scope; architecture and reasoning; tool integration; autonomy and human checkpoints; safety; observability and evaluation; and platform/tooling usage. No other briefing page informed this assessment.

The automated journey opened the live app in Chromium with touch and reduced-motion settings, inspected the farm and its 56-day calendar, enabled real browser audio, traced a Caixin shortage candidate into its records, changed market demand to 130%, ran one real local numerical experiment, compared Lean, Balanced and Resilient under the same policy, reloaded the session, and checked the main navigation at 360, 390, 430 and 1280 pixels. It did not send an advisor message, invite an agent or convene the council. Network monitoring recorded zero inference submissions and the browser recorded zero page exceptions.

Fresh-session admission was not reset or relaxed. An initial fresh session completed the entry, sound and evidence path; a second fresh session completed the numerical path before a reviewer-locator error. The corrected full-width run used the already-authorized V4 review tenant because the shared IP reached the normal new-session cap. This is a test-harness limitation, and the final JSON discloses it rather than describing that corrected pass as fresh. The test should save its fresh storage state immediately in the next review cycle so one admitted session can survive harness corrections.

The sound test establishes that the bundled files decode and play in Chromium. It cannot establish comfort, appeal, speaker loudness or physical-phone audibility. Those require people listening on representative devices.

Evidence:

- [Browser review JSON](business_browser.json)
- [Review script](../../tests/browser/v5_business_review.mjs)
- [360px first-play view](../../apps/web/screenshots/v5-business/novice-entry-360.png)
- [Evidence journey](../../apps/web/screenshots/v5-business/evidence-390.png) (captured at 360px despite the historical filename)
- [Scenario trade-offs](../../apps/web/screenshots/v5-business/tradeoffs-430.png) (captured at 360px despite the historical filename)
- Responsive farm views: [360](../../apps/web/screenshots/v5-business/responsive-360.png), [390](../../apps/web/screenshots/v5-business/responsive-390.png), [430](../../apps/web/screenshots/v5-business/responsive-430.png), [1280](../../apps/web/screenshots/v5-business/responsive-1280.png)

## Executive assessment

V4 already has a credible numerical planning product beneath the game surface. It keeps synthetic data explicit, bounds the planning horizon, separates a time preview from real observations, freezes scenario inputs, compares the same policy on both sides, exposes six business outcomes, identifies affected beds and deliveries, and leaves the main farm unchanged. Those details answer much of the rubric's safety, tool-use and observability criteria.

The playable story does not yet make Sumin's central business thesis visible. The home screen says, “Tap a bed or visit an advisor to explore the plan.” A learner can wander, but has no single urgent business goal, success condition or recommended first move. Data can reveal a shortage and the Scenario Lab can test a demand shock, yet the chosen shortage disappears between those rooms. After roughly 23 seconds of numerical work, the result goes directly to a before/after table and computed debrief. The six specialists do not visibly contribute distinct constraints, disagree, or hand a reconciled decision to Asha. The architecture exists more clearly in the roster and specifications than in the player's causal experience.

For V5, the main design objective should be one complete, legible decision episode: **notice a dated shortage, inspect why it exists, change one grounded assumption, watch six business roles respond, let the Planner reconcile their conflicts, compare the three policies, then preview when work and harvest occur.** This is a production-planning game loop rather than a crop-growing game loop.

## Prioritized findings

### P0 — Make the architecture the playable argument

**BIZ-04 · High.** Seven named roles are visible on the farm, but the no-inference numerical journey jumps from a slider to policy metrics. It never shows Demand arguing for service, Production rejecting impossible maturity, Supply Chain exposing an input or delivery constraint, Profit showing margin, or Planner resolving the conflict. This weakens Sumin's strongest differentiator and the rubric's architecture/reasoning criterion.

V5 should render a deterministic council reaction after every numerical run from the already-computed evidence. Each role card needs a distinct question, one or two typed facts, and a stance such as `supports`, `warns`, `blocks`, or `unknown`. Asha should cite the exact conflicts she resolves. These cards must not impersonate LLM output: label them “computed role briefs” unless a separately authorized, completed council run exists.

**BIZ-03 · High.** The evidence and action rooms lose the player's subject. The Data Explorer can identify `forecast:caixin:2026-09-21`, expected demand of 31.001 kg and contributing order `order-0-1`; the later Busy Market quest does not carry that selected date, crop or evidence into its briefing. The user changes “market demand” in the abstract.

Add a persistent mission object with crop, delivery date, shortfall, evidence IDs, selected shock and frozen snapshot hash. Keep its compact card visible in Data, the farm, the Scenario Lab and results. “Back to evidence” and “Continue this shortage” should preserve filters and focus.

**BIZ-07 · Medium-high.** The first screen offers exploration rather than a business objective. That is pleasant for returning users but weak for a 12-year-old, a hurried judge, and a farmer asking what needs attention.

Lead with one recommended mission: “Can we cover the Caixin order due 21 Sep?” State why it matters, the target, current expected supply, the next action, and what counts as completion. Preserve free exploration as a secondary choice. A judge should understand the business value within ten seconds.

### P1 — Make time feel agricultural and responsive

**BIZ-05 · Medium.** The 56-day preview is scientifically honest: it explicitly says that previewing does not advance time or create observations. The scenario result, however, arrives as an immediate computation with no in-world sequence connecting the planning date to nursery, transplant, grow-out, harvest and delivery. Younger users may infer that changing a slider “makes crops happen”; growers may not see why a near-term shortage cannot be solved by sowing today.

Use two clearly named clocks:

1. **Calculation time** is real wall-clock waiting while the solver runs. Show truthful stages driven by backend events: freeze inputs, forecast demand, check biological windows, optimize resources, compare policies. Do not use invented agent chatter as a loading animation.
2. **Farm time** is the simulated calendar. After results, let the player scrub or step through dated actions and growth stages. Disable or flag actions that mature after the order date. Show “13 days until order; Caixin needs N days under this declared recipe” beside the decision.

The measured numerical wait was about 22.6 seconds. That is long enough to break a lightweight game loop. Cache identical frozen inputs, stream genuine job stages, and offer a stored demonstration branch for the 90-second pitch. Keep the live calculation path accessible so the demo is not merely prerecorded.

**Persistence discoverability · High usability defect.** The numerical branch persisted server-side, but the automated user could not see it immediately after reload by reopening the Scenario Lab and choosing step 3. The lab opens on its briefing phase and loads saved branches asynchronously; “Compare” did not make the prior branch evident during the check. Whether this is a timing race or presentation problem, the player's expectation is the same: completed work should visibly return.

On reload, show “Last experiment completed” with its date, controls and Resume button. Deep-link the result by scenario ID and retain the selected result in edition-scoped session state. Add an explicit loading state for saved branches.

### P1 — Turn evidence into understandable consequences

The comparison is quantitatively strong: Lean, Balanced and Resilient each retain the same-policy baseline, and the table presents demand filled, contribution margin, waste, unfilled demand, labour and total cost. It also links 15 affected beds and 32 delivery dates in the reviewed Busy Market branch.

For a novice, terms such as “frozen baseline,” “contribution margin,” “EWMA alpha,” “comparison root,” and snapshot hashes need nearby plain-language help. For a grower, totals need operational translation: which beds change, what action moves to what date, which order remains short, and which assumption caused the difference. V5 should always pair one business consequence with one physical farm consequence.

The scenario slider is keyboard-operable to an exact 130%, but this control only exposes a range and output. A numeric input would improve exact touch entry and make the currently selected value more obviously editable on mobile.

### P1 — Build meaningful progression around decisions

The current quest journal awards Experimenter and Trade-off Finder badges. This is age-appropriate and does not trivialize farming, but it rewards completion and inspection rather than decision quality. V5 should use a short progression tied to reasoning:

- **Detective:** identify the dated shortage and open its contributing records.
- **Timekeeper:** reject a planting action that matures after delivery.
- **Trade-off finder:** compare all three policies under one frozen baseline.
- **Evidence keeper:** trace the Planner's conclusion to a source record and numerical constraint.
- **Farm steward:** choose an option and explain the service, waste, labour and margin trade-off.

Badges should unlock explanations, crop art details or replayable challenges, never imply a simulated plan produced real farm impact.

### P2 — Audio works technically; review the experience on real devices

The V4 loop decoded to a 16-second duration, played after a deliberate click, advanced its native playhead, looped at 20% volume, and loaded a navigation cue at 35%. This directly contradicts the earlier symptom that V2 sound was universally inaudible: the current browser pipeline works in the reviewed environment. The interface starts silent and exposes separate music/effects controls, which is appropriate for young users, adults and public demos.

**BIZ-06 · Medium.** Users cannot preview channels or calibrate loudness before enabling the full soundscape. There is no visible acknowledgement of a successfully played effect, and a short repeating loop may fatigue a longer planning session.

Human sound reviewers should test phone speakers, headphones and muted/low-volume OS states. Review at minimum: clarity at 20%, repetition after 5/15/30 minutes, whether completion/error cues differ without being alarming, whether controls remain usable with screen readers, and whether reduced-motion users can also reduce sensory intensity. Add a “Play sample” action per channel and a visible meter only if it reflects real playback state. Do not claim audibility from automated decode alone.

### P2 — Responsive foundations are good; density still needs task testing

All four tested widths had no page-level horizontal overflow, primary navigation targets remained at least 44px, keyboard chart selection worked, the date slider supported keyboard extremes, and no page exception occurred. Those are strong foundations.

The farm map and seven-character roster are visually dense at 360px. The accessible farm list is therefore essential and should become more discoverable during onboarding. Future E2E reviewers should measure whether users can locate a named bed, return from a bottom sheet, read the scenario table without losing row/column context, and reach sound controls while another dialog is open. Automated geometry is necessary but cannot substitute for touch accuracy and comprehension on a physical device.

## Recommended 90-second V5 judge journey

| Time | Player action | Visible business reasoning | Rubric evidence |
|---|---|---|---|
| 0–10s | Open “Caixin due 21 Sep” mission | Required kg, expected harvest, shortfall, synthetic status | Goal and scope |
| 10–22s | Tap the shortage and inspect order/history records | IDs, units, cutoff, observed versus forecast | Tool use; observability |
| 22–35s | Increase demand or apply a dated disruption | One bounded input, frozen snapshot, no inference | State management; safety |
| 35–52s | Run or open a stored numerical result | Real job stages; biological maturity gate | Architecture; platform usage |
| 52–68s | Watch six computed role briefs disagree | Distinct facts and `support/warn/block/unknown` stances | Multi-agent reasoning |
| 68–80s | Planner selects/rejects under declared policy | Constraint resolution with linked evidence | Autonomy and guardrails |
| 80–90s | Compare one policy and scrub the farm calendar | Service, margin, waste, labour and dated actions | Business value; evaluation |

The dramatic moment should be a biologically impossible near-term recovery: demand rises for a delivery before a new sowing can mature. Production blocks the tempting action; Demand shows the shortfall; Supply Chain offers only a partner/substitution path if that evidence exists; Profit states the cost; Planner records the unavoidable shortfall or feasible alternative. That conflict proves why a council is useful without fabricating disagreement.

## Judging-rubric mapping

| Rubric area | V4 evidence | V5 improvement needed | Priority |
|---|---|---|---|
| Goal & scope definition | Synthetic farm, resources and planning language are explicit | Put a dated, quantified business mission and success condition on entry | P0 |
| Architecture & reasoning loop | Frozen inputs, three policies, scenario branches and seven roles exist | Show distinct role stances and Planner conflict resolution inside the playable loop | P0 |
| Tool use & integration | Forecast/history records, numerical optimizer, exact policy comparisons, provenance and hashes | Carry selected record IDs into the mission and show operational bed/order changes | P0 |
| Autonomy & human-in-the-loop | Numerical simulation is local; main farm remains unchanged; advisor inference requires explicit send | Explain what the development policy selected and offer inspect/replay/escalate actions at the decision point | P1 |
| Safety, security & guardrails | No inference while browsing/running the scenario; synthetic and preview states are explicit | Keep deterministic role briefs distinct from model speech; retain maturity and hard-constraint blocks | P0 |
| Observability & evaluation | Six deltas, affected beds/deliveries, snapshot hashes and no-inference traces are visible | Make saved-result recovery obvious; add golden-path timing/comprehension and adversarial impossible-maturity tests | P1 |
| Platform & tooling usage | Responsive React UI, accessible SVG records, real numerical API and edition isolation work together | Demonstrate the orchestration as a coherent event sequence, not seven avatars beside a separate solver | P0 |

## V5 acceptance tests from this review

1. A new user reaches a quantified mission within one action and can state the goal from visible text.
2. Selecting a shortage creates a mission reference that survives Data → Farm → Scenario → Result and reload.
3. A dated impossible-maturity case visibly causes Production to block planting before Planner concludes.
4. Six specialist briefs use distinct typed inputs; Planner cites at least two conflicting briefs and the numerical strategy ID.
5. No computed brief is labelled as live agent speech, and no browsing/numerical action creates a provider request.
6. Solver progress shows only real backend states; a repeated identical snapshot uses a documented cache or stored replay.
7. Farm-time preview shows sowing, nursery/transplant, grow-out, harvest and delivery dates, and never creates observations.
8. Reload returns directly to the last completed branch, with its controls, baseline hash and comparison available.
9. Lean, Balanced and Resilient comparisons retain the same frozen baseline and expose service, waste, labour, cash/margin and constraints.
10. At 360, 390, 430 and 1280px, the mission, role conflict, timeline and comparison remain keyboard/touch operable with no document overflow.
11. Music and every cue decode, start only after opt-in, advance, mute, persist edition-scoped preferences and fail non-blockingly.
12. Human sound reviewers on representative phones can hear and distinguish music, navigation, confirmation, completion and error cues at defaults.
13. A novice, grower and judge can each complete the 90-second journey and explain why the selected plan changed; report task time and wrong turns rather than only pass/fail geometry.

## What should remain unchanged

Keep the immutable edition boundary, explicit synthetic/replay labels, no-provider numerical path, same-policy comparison, source/record traceability, preview-only time semantics, reduced-motion support, 44px navigation targets, separate sound channels, and honest empty states for unconnected community signals. They provide the trust needed for stronger gamification.
