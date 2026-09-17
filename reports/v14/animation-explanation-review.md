# V14 live UX review: motion, explanation and lost depth

17 September 2026. Review/specification work only; no application code or deployment
changed. Live target: https://farmtact.fly.dev/ (introduction and `/play`).
Recommendation: [V15 integrated card experience](../../docs/v15-integrated-card-experience.md).
Additional user-requested audit: [V13 graphical and functional reuse map](../../docs/v15-v13-reuse-map.md),
including a fresh SVG contact sheet, 27-file manifest and source-verified limitations.

## Method and limits

Walked the live site in real Chromium with normal motion, including a complete
first season: calculate, compare, choose Resilient, advance, record B3 maintenance,
choose eligible recovery, grow, review recorded delivery and open utility cards.
A second isolated synthetic lesson inspected plan selection, settled frames,
pause/reload and reduced motion. These were ordinary UI actions against saved
teaching journeys, not mock API responses or real farm operations. No questions or
Council/provider actions were submitted. Both audit scripts completed without
reported browser/script errors; the first recorded zero provider-bound requests.
This is bounded observation, not a fresh full regression or backend inference audit.

Full journey viewport: 390×844. Additional plan/explanation layout observations:
360×800, 430×844 and 1280×900. Timed screenshots used normal animation, not
Playwright's `animations: disabled`; animation metadata was sampled separately.
Some journey captures intentionally catch entry motion, so settled comparison frames
are supplied too. Source audit compared the retained V12/V13 modules and current
entrypoint; retired editions were not republished or bypassed for this review.
No human participants, screen-reader session or physical-device trial was conducted.

Raw evidence: [journey observations](ux-audit-2026-09-17/observations.json),
[timed/pause observations](ux-audit-2026-09-17/motion-observations.json).
These contain visible synthetic lesson text, DOM/animation state and geometry, not
credentials, cookies, environment variables or real-farm records.

## What works

The single central decision and clear primary action are a useful foundation. The
live numerical lesson completed; option facts changed, B3 gained a barrier, dates
advanced and the final delivery was recorded. The simulation labels, explicit
advances and noninteractive scene reduce accidental actions. Pause stopped the
sampled running animations in-session; OS reduced motion also produced zero running
animations in the sampled state. Keep these strengths.

## Findings

| Finding | Observed evidence | Consequence and proposed fix |
| --- | --- | --- |
| F01: introduction describes a theme, not how to play | “Compare two plans” shows a single document/checkmark above generic beds; settled frames at 300/1200 ms retain that composition | It does not demonstrate compare versus commit. LEARN-01: interactive illustrated rehearsal with the actual action area |
| F02: highlighted beds are not a plan preview | Lean/Resilient cards change quantities and outlines; scene retains the same starting crops, with no visible preview/saved badge | Users cannot inspect what the alternative actually plants. MOT-01/EX-02: server-bound future allocations, dates and explicit preview label |
| F03: Explain is often provenance or repetition | B3: “This comes from beginner-teaching-farm-v1…”; recovery repeats “Moves future work around…” and the summary quantities | It does not explain which work moved or why delivery survives. EX-01–03: cause, changed allocations, tradeoff, evidence and limits |
| F04: idle movement dominates consequence motion | Settled plan scene has 17 running animations: sun plus 16 plant loops; no user advance is occurring | Motion does not establish a causal model and can imply ongoing growth. MOT-02–04: finite event-bound changes and static idle state |
| F05: temporal/state semantics are weak | On 17 Jan, B3 is visually barred and card says Active, while text says unavailable 18–31 Jan. Delivery stage still says “Compare two ways to grow it, then choose your plan” | Upcoming versus effective and delivered versus review must be explicit. LEARN-02 and semantic transition contract |
| F06: scene and action/explanation do not fit together reliably | At settled 390×844, Explain moves primary to y=829–879; at 360×800 y=798–848; at 430×844 y=811–861 | The next action is partly outside the viewport, increasing separation from the scene. UX-02–03: short explanation cards and adaptive layout, not smaller text |
| F07: desktop is an enlarged vertical mobile column | At 1280×900, scene, wide card and dock form one tall stack; full capture is 969px high | Space is available but cause/detail/action remain vertically separated. UX-01: compact card beside scene using the same controls |
| F08: bed/crop labels overlap scene geometry | A1/Lettuce label is partly occluded by the foreground B3 bed in settled desktop/mobile plan captures | Details are difficult to read even when the image is large. MOT-05: separate label plane and accessible bed detail cards |
| F09: pause is not persistent; duplicate utility controls | Pause gives zero running animations; after reload 17 run again. Utility cards show both Pause and Pause motion, plus Back and Back to season | Preferences and action roles are inconsistent. MOT-04/UX-01: one persistent control, no duplicated utility actions |
| F10: journal and records lose explanatory depth | Journal flattens last four events, exposing raw `bed-02`, `bed-04`, `order-first-delivery`; Records contains an order sentence and bed count; Crops contains nursery/grow days only | Existing entities and history cannot be inspected. EX-03/PAR-01: full source-linked event/record/crop decks |
| F11: current public experience is only the tutorial | Current entrypoint imports BeginnerApp rather than App; earlier workspace capabilities have no reachable cards | Functional simplification has become capability loss. Restore sandbox capability through the same shell, not old screens |

Additional source-confirmed risks: truck rendering depends on generic success tone
rather than delivery event; bed entry keys depend on stage/progress rather than an
audited transition identity; opening a new revision resets explanation state; the
scene accessible name uses raw stages and lacks preview/cause information. These
are implementation risks, not claims that every possible bad state was reproduced.
The DOM live text retained “Resilient plan. Card 2 of 2” into later stage captures;
a screen-reader test must verify and repair stale announcements (A08).

Selected visual evidence:

- [Intro comparison, settled](ux-audit-2026-09-17/intro-choice-1200ms.png)
- [Lean saved-world view](ux-audit-2026-09-17/lean-settled.png) and
  [Resilient saved-world view](ux-audit-2026-09-17/resilient-settled.png)
- [B3 explanation](ux-audit-2026-09-17/04-MAINTENANCE_DUE-explain.png)
- [Recovery explanation](ux-audit-2026-09-17/05-CHOOSE_RECOVERY-explain.png)
- [Delivery-stage instructions](ux-audit-2026-09-17/13-DELIVERY_DUE.png)
- [Desktop plan/explanation](ux-audit-2026-09-17/explain-desktop.png)
- [Journal](ux-audit-2026-09-17/utility-2.png) and
  [records](ux-audit-2026-09-17/utility-3.png)

## Earlier capability versus current reachability

The user is right about lost functionality **in the accessible application**. This
is not evidence that the underlying services or historical data were deleted.
`main.tsx` renders BeginnerApp for all served paths; the retained `App.tsx` rooms
are not imported. Many earlier APIs remain installed in `services/api/app.py`.
Retained source/routes establish reuse candidates, not tested V15 integration.

| Capability | Earlier implementation evidence | V14 public UI | Recommended integration |
| --- | --- | --- | --- |
| Main farm setup, import, records | `Rooms.tsx` setup; `api.ts` imports; `GuidedPlanning.tsx` snapshot/farm facts | Separate fixed teaching fixture; summary records only | Explicit sandbox context; real entity/import/review cards |
| Crop profiles, evidence, public context | `Rooms.tsx` crop/source detail; `DataExplorer.tsx` | Teaching recipe prose, no evidence drill-down | Knowledge/source cards with freshness, limitations and IDs |
| General strategies, allocations and bed inspection | `GuidedPlanning.tsx`; `TacticalMission.tsx` | Two lesson choices and noninteractive starting scene | Keep two-choice lesson; general strategy/bed/schedule detail decks in sandbox |
| Reviewed Inbox, proposals, approvals and inverse | `FarmerWorkflow.tsx`; `TacticalMission.tsx` | Lesson action progression, not general workflow | Review → apply/recalculate → inspect → approve cards with original contracts |
| Tasks, reported results and corrections | `FarmerWorkflow.tsx` | Simulated lesson timeline only | Task/result/correction cards; preserve reported versus simulated distinction |
| Council, grounded discussion and replay | `FarmerWorkflow.tsx`; `GamePanels.tsx` | Asha only; each question creates a new conversation; latest reply flattened into utility prose | Full thread/evidence cards first, optional explicit Council role/review cards |
| Frozen branches and quests | `GamePanels.tsx`; scenario APIs | No accessible workflow | Scenario/objective cards with same-root comparisons |
| Explorer/generation/forecast/export | `DataExplorer.tsx`; explorer APIs | No accessible workflow | Dataset and forecast decks, charts within cards, action-area save/export |
| Research and review | Research components and installed research/review APIs | Non-play routes render intro rather than a working workspace | Study/review cards in sandbox; preserve isolated data and execution modes |
| Waste Rescue | `FarmerWorkflow.tsx` | No accessible workflow | Eligible surplus cards with existing local comparison, no operational authority |
| History and attempts | Existing saved entities and lesson replay API | New attempt supported, old saved attempts not browsable; journal last four events | Separate open-history, visual replay and new-attempt actions |

Relevant source links:
[entrypoint](../../apps/web/src/main.tsx),
[prior shell](../../apps/web/src/App.tsx),
[current adapter](../../apps/web/src/lib/beginner.ts),
[current app](../../apps/web/src/components/BeginnerApp.tsx),
[scene/cards](../../apps/web/src/components/BeginnerGame.tsx),
[motion](../../apps/web/src/components/BeginnerGame.css),
[farmer workflow](../../apps/web/src/components/FarmerWorkflow.tsx),
[planning](../../apps/web/src/components/GuidedPlanning.tsx),
[tactical shell](../../apps/web/src/components/TacticalMission.tsx),
[earlier rooms](../../apps/web/src/components/Rooms.tsx),
[discussions/scenarios](../../apps/web/src/components/GamePanels.tsx),
[explorer](../../apps/web/src/components/DataExplorer.tsx),
[server routes](../../services/api/app.py).

## Recommendation and release boundary

Do not solve this by adding more animation or bringing back every old screen. Keep
one farm table and restore the data/workflows as contextual card decks, with a
visible boundary between the fictional lesson and the tenant's sandbox farm.
Make deterministic explanations and source inspection available without asking AI.

The proposed V15 spec and V13 reuse map define actionable capability parity, motion
storyboards, asset reuse, context/identity contracts, accessibility, rate-limit
behavior and A01–A14 acceptance.
All are pending implementation. This review does not claim human comprehension,
completed parity, a new release, or that earlier automated passes covered these gaps.
