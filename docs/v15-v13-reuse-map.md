# V13 → V15 reuse map: preserve depth, replace navigation

Status: specification only, 17 September 2026. Companion to the
[integrated card experience](v15-integrated-card-experience.md). Reuse the intellectual
structure and graphical vocabulary of V13 inside V14's minimal flow; do not mount
both applications, resurrect edition navigation or copy old state into a new context.

## What was inspected

Reference: tag `farmtact-v13`, commit
`30f4e974cda4e5624d85f66627e7667be91d9a15`. Compared that tag with current retained
`TacticalMission`, `TacticalConsole`, `World`, `Visuals`, `public/art` and
`public/explainers`: no differences in those paths. Thus these are genuine V13
reuse candidates, not an inferred reconstruction from the new tutorial.

Inspected V13 mobile screenshot, its implementation report and action/entity maps;
read source rather than treating those intended-behavior matrices as proof. Viewed
historical art sheets and rendered a fresh contact sheet from all 27 current SVGs.
The original contact sheet is incomplete/outdated: it has six portraits and older
crop art. Use the fresh inventory, not that sheet's old role labels.

- [Current 27-asset contact sheet](../reports/v14/ux-audit-2026-09-17/v13-current-assets.png)
- [Asset paths, byte counts and SHA-256 inventory](../reports/v14/ux-audit-2026-09-17/v13-asset-manifest.json)
- [V13 actual-API mobile screenshot](../apps/web/screenshots/v13-real-mobile-390.png)
- [V13 controlled tactical screenshot](../apps/web/screenshots/v13-tactical-390.png)
- [Original provenance and limits](crop-art-provenance.md)

The 20 crop SVGs plus seven portrait SVGs total **38,007 uncompressed bytes**.
This is only the art payload, not the application bundle or network transfer size.
The current files are original repository-native vectors. No new image generation
or downloaded artwork is needed to recover this visual vocabulary.

## Asset decisions

| Retained asset | Use in the new minimal interface | Do not carry forward |
| --- | --- | --- |
| `art/crops/{lettuce,pak_choi,caixin,kailan}-{seedling,growing,ready}.svg` (12) | Replace generic sprouts with crop-specific stage art in the passive scene and batch/recipe cards; seedling → canopy → ready only on matching server state | Client-estimated maturity, endlessly scaling “growth,” or assuming a harvested bed is still ready |
| Eight other mature crop SVGs: bayam, kangkong, kale, mustard greens, malabar spinach, sweet-potato leaves, garlic chives, sawtooth coriander | Almanac/profile illustration with name and support/recipe limitations | Invented seedling stages, implied numerical recipe support, or treating the representative cultivar as verified |
| Seven adviser portraits: Asha, Ben, Hana, Idris, Lina, Mei, Ravi | Small named avatar on the relevant role/question/recorded-message card; relevant specialist introduced only when helpful | All advisers standing around as additional buttons, decorative “thinking,” fabricated speech or portrait-implied evidence status |
| `World.FarmLandscape` inline SVG paths, nursery/greenhouse/packing shapes, earth/grass palette and shadows | Extract only useful, noninteractive scenery. Nursery → growing bed → packing location can explain a server-recorded crop/inventory event | Full busy village, clickable facilities, camera controls, pan/zoom/move mode and decorative facilities implying real capacity |
| `CropArt` soil fallback and presentational treatment | Neutral unknown/empty-bed depiction, with an explicit textual status | A believable crop substituted for an unknown ID or undocumented default ready state |
| Tactical card paper/depth, provenance strip, state and disabled-reason treatment | One readable active card, unobtrusive depth, source/mode label and actionable disabled reason; full provenance in detail deck | Simultaneous strategy tray, Council panel, active-constraint panel and permanent bottom room navigation |
| Lucide action/status vectors | One consistent icon beside visible action text | Icon-only mysteries, hover-only meaning or status inferred by generic string matching |
| Three captioned explainer packages (`observe-decide`, `council-evidence`, `act-replan`) | Reuse teaching outline and transcripts as source material; offer optional re-authored help cards/video after copy audit | Old V12-labelled text posters as the landing animation, auto-playing video, or video screenshots presented as current farm facts |
| Historical review/research screenshots | Reference and regression evidence only | Runtime backgrounds, fake live charts, current-state labels or new educational content |

The useful new look is **the simple V14 composition with the crop identity and
tactile detail retained in V13**, not a miniature copy of V13's entire page.
Keep upper-left lighting, paper/forest/earth palette and clear stage silhouettes.
Labels occupy a separate foreground layer so crop sprites and beds cannot cover
them. Portraits are secondary to decision text. At 54–64px, keep crop names: visual
recognition alone has not been validated with humans, and some silhouettes are close.

### Rendering safeguards

**REUSE-01** Build an explicit allowed asset registry keyed by canonical crop ID
and server-provided stage. `CropArt` is a useful presentational seam, but its current
regex normalizer is not authoritative: `/harvest/` can classify a harvested state as
ready, and unstaged crops deliberately fall back to mature catalogue art. The new
scene must explicitly distinguish nursery, growing, ready, harvested, sanitation,
empty and maintenance. Missing stage assets get a labelled fallback, not guessed art.
The lesson currently teaches lettuce and then pak choi; the registry also supports
the existing caixin/kailan model. Art does not broaden numerical model support.

**REUSE-02** Use external local SVG images or namespace IDs when extracting/inlining
vectors; repeated gradients/masks must not collide. Audit assets for scripts,
external fetches and unsafe user-supplied paths. Use current-release asset routing,
never `/v13/art/...` links that require retired public routes. No source-photo reuse.
Preserve the repository's provenance record and representative-art limitations.

**REUSE-03** Portrait ID/name/role comes from the validated current role registry,
not baked text in historical contact sheets. For example, the oldest sheet labels
Idris a critic; the retained application registry maps him to Market. Keep advisor
identity separate from the functional Council role contract. A portrait's presence
never signals that a provider ran or a finding was verified. Authored teaching copy
must be labelled guide text rather than passed off as an AI adviser utterance.

## Functional reuse: contracts first, not whole components

V13's strongest loop is: **scenario → concrete constraint → explicit reservation
proposal → local recalculation → stored deltas → current-revision inverse/history**.
Carry that into sandbox play after the tutorial; the original B3 entity remains
`bed-07` in that fixture. It is not the tutorial's `bed-03`.

| Source seam | Preserve | Adaptation in the one-card shell |
| --- | --- | --- |
| `TacticalCard` / `TacticalPlanningBinding` / provenance types | Stable card/entity IDs, target IDs, frozen snapshot/hash/session/revision/result, proposal/task binding, facts and explicit actions | One shared presentation contract with an explicit lesson/sandbox context; adapters from existing server responses, not a new generic server feed |
| `TacticalMission` reservation/inverse/job integration | Exact dated reservations, executed-crop/sanitation boundary, persisted jobs, server metric deltas, stale inverse rejection | Review card then action-area apply; active-constraint state becomes a card rather than an extra panel |
| `ProvenanceStrip` | Real/synthetic/scenario/projected/reported distinction, observed/retrieved time and freshness | Short always-visible label; source-detail cards preserve full fields; Heavy Rainfall keeps exact `SIMULATION · SCENARIO ONLY` |
| `ActionDock` and swipe intent handling | Active-card-only actions, emphasized primary, disabled reason, job progress, keyboard equivalents | One action area, no independent navigation bar; align with V15 Back/Explain/More grammar |
| `ConversationSummary`, Ask focus and suggestion plumbing | Frozen focus, explicit submit, ordered stored messages, pending/failure states and no invented fallback | In-place adviser/thread/evidence deck with portrait and source cards, not a simultaneous sidebar/modal shell |
| `TacticalFarmBoard` bindings | Frozen bed records, crop/batch lookup, exact target highlights and reservation state | Feed passive 2.5D scene and entity-detail cards; the tactical board itself uses generic Sprout icons, not the richer crop sprite set |
| `World` crop/landscape composition | Crop SVG placement, stage vocabulary, recognizable facilities, affected/reference IDs | Extract a pure renderer driven by server scene projection; do not transplant `previewBed`'s client-side date/progress calculation as farm authority |
| `StrategyTray` and earlier detailed planners | Stored feasibility, violations, metrics and allocations | One strategy at a time, explicit comparison cards, allocation/constraint drill-down; no scroll-to-another-panel action |
| `FarmerWorkflow` task/approval/correction APIs and forms | Complete existing validation and append-only event contracts | Review/report/correct cards with forms inside, submissions solely in the action area; no “go to Records screen” escape |
| `AdvisorEvidence`, prior discussion/research/explorer adapters | Fact/evidence/tool refs, withheld states, frozen context and compatible comparisons | Small evidence/result cards; preserve optional deeper paths in the tool index |

Do not run the old `App` and new `BeginnerApp` in parallel as separate navigable
products. Extract presentational pieces and adapt domain workflows under a single
context-aware shell. Keep edition/context/journey/deck selection storage scoped;
clear stale async responses on context switch. Lazy-load optional workflow decks
and evidence/media, retaining the bundle warning as a measured item.

## V13 limitations that must not be mistaken for finished features

The source dispatch in `TacticalMission` is more limited than its aspirational card
matrix. Preserve this distinction when estimating or implementing parity:

- `review_impact` selects `constraint-bed-07`; it does **not** itself render a
  calculated rainfall comparison. V15 needs a real compatible comparison or an
  honest unavailable reason. Rain artwork must not imply weather changed yield.
- `view_plan`, `preview` and `compare` scroll to the strategy tray. V15 needs explicit
  preview identity, schedules and same-baseline comparison, not just renamed buttons.
- Tactical `record_result` is disabled and directs users to the older full Records
  workflow. Reuse that workflow's implementation behind cards; don't reproduce the
  disabled handoff in the replacement product.
- `CardDetails` is a title/summary/entity/snapshot view, not a complete causal
  explanation. Enrich it using V15 EX-01–04; don't merely relabel Details as Explain.
- Some V13 documentation describes a draft/review step, while the Reserve handler
  creates and applies in one action. V15's explicit review/commit grammar is a new
  integration requirement, not a claim about the previous UI.

## A concrete integrated sandbox episode

1. Open sandbox through its labelled context-switch card; show current farm/version
   and pending objective. It is not the saved tutorial farm.
2. Swipe to a supported scenario card. Its illustration is secondary to provenance;
   reviewing it cannot mutate assumptions or trigger AI.
3. Select the B3 constraint. The passive scene frames the exact bed. Details show
   its occupancy and proposed reservation dates; center key opens review.
4. Confirm the revision-bound reservation. Keep saved state during queued/running
   calculation. On completion show the new result, affected allocation animation and
   signed server deltas, then settle on “What changed.”
5. Explain opens binding constraints, before/after schedule and source cards. A named
   specialist can answer an explicitly submitted question; deterministic explanation
   is already available without AI.
6. Browse new strategy cards. Approval and sandbox task reporting use the same keys.
   Undo is a reviewed inverse proposal if still eligible, not browser Back.

This episode restores V13's depth without adding a second navigation grammar.

## Added acceptance checks

**A12 asset truthfulness:** manifest/file existence, canonical crop/stage lookup,
unknown/unsupported/harvested fallbacks, portrait registry identity, current-release
asset paths, no external requests from SVGs, duplicate-ID safety, 54/64px and
360/390/430/desktop screenshots. Verify source labels and human-readable stage text;
art must not certify crop health, yield or cultivar identity.

**A13 V13 episode parity:** actual local planner path through scenario inspection,
reservation review/apply, jobs/deltas, explanation, compatible comparison, approval,
task result/correction and eligible/stale inverse. Assert unchanged identities,
zero provider calls until explicit Ask, admission on every route and no automatic
movement between teaching and sandbox data. Buttons that only scroll or show generic
details do not pass their corresponding workflow check.

**A14 minimalist containment:** all commands stay in the action area; scene/portraits
have no hotspots; no old room navigation, simultaneous strategy/Council panels,
edition selector or endless decorative loops. Detailed tools preserve parent card,
focus and context on Back. The same task is possible with swipe, buttons and keyboard.
