# V13 tactical-card prototype recommendations

Review date: 17 September 2026 UTC. The source plan says the prototype should answer fourteen exploration questions but does not enumerate them. This report formulates the fourteen key questions implied by that plan and answers them as technical recommendations.

Evidence codes:

- **V12** — inspected existing implementation/contracts and published V12 evidence.
- **H** — heuristic interface/accessibility review.
- **S** — scripted test design or automated evidence that must be collected from the V13 candidate.
- **Human deferred** — requires representative participants; no current human claim.

## 1. Should tactical cards become the primary entry to the farm mission?

**Recommendation:** Yes, for this bounded prototype, provided the farm board and numerical consequences remain visible in the same continuous page. Cards should prioritize one current decision and should not replace the board, provenance, or strategy comparison.

**Basis:** V12 already has the authoritative board and workflow but presents many peer sections/actions. A single readable active card can reduce initial choice density (**V12, H**). Whether growers find the metaphor clearer or more motivating is **Human deferred**.

**Prototype decision:** Open on Heavy Rainfall, then allow movement to the B3 constraint. Do not build a generalized server-generated feed yet.

## 2. What should the opening Heavy Rainfall card claim?

**Recommendation:** Treat it as a frozen synthetic scenario, never current weather or a live forecast. Display `SIMULATION · SCENARIO ONLY` on the card, in the provenance strip, and in Details. Its primary action is a read-only impact review.

**Basis:** Existing FarmTact contracts distinguish data/execution modes and prohibit contextual weather from silently changing numerical yield (**V12**). Repeated compact provenance mitigates a predictable misreading (**H**). Test whether people actually understand the distinction later (**Human deferred**).

**Prototype decision:** Do not trigger a proposal, planner run, or provider call by selecting or reviewing the rainfall card.

## 3. Is “Reserve space” the right farmer-facing action for the B3 constraint?

**Recommendation:** Use `Reserve space`; keep “constraint” as secondary system language and avoid “Play Constraint” in the primary path. Show the exact grow-space name, dates, and non-mutating draft before apply.

**Basis:** The operation changes a planning reservation, so the verb is concrete and maps directly to the existing reservation field (**V12, H**). Wording comprehension and farmer vocabulary fit are **Human deferred**.

**Prototype decision:** B3 is a display name for `bed-07`, not a new entity. Details exposes the trusted ID.

## 4. Can one card/action model cover evidence, constraints, crops, orders, strategies, tasks, and agents without becoming vague?

**Recommendation:** Use one structural `TacticalCard` view model but preserve type-specific action semantics and server eligibility. Limit visible actions to three; make Details universal; render Ask only for valid focus; keep Compare, Approve, Undo, and Record Result entity-specific.

**Basis:** The shared shell benefits navigation and accessibility, while V12's proposal/strategy/task contracts require different invariants (**V12, H**). The action matrix should be treated as a closed prototype contract rather than a generic command bus.

**Prototype decision:** Derive cards from existing server responses. Do not make cards an independent domain/store or calculate eligibility in the browser.

## 5. How should the B3 reservation connect to a real plan change?

**Recommendation:** Reuse V12's current-revision draft proposal → explicit apply → local recalculation path. Store a single reviewed planning-assumptions change with a dated `bed-07` reservation. Drive progress from the persisted job and update the board/metrics only after the bound result completes.

**Basis:** V12 already supplies tenant-scoped proposals, optimistic revisions, idempotency, numerical jobs, and server-calculated metrics (**V12**). The V13 browser/API journey must prove exact payloads and states (**S**).

**Prototype decision:** Do not create a parallel card mutation endpoint that bypasses proposal history.

## 6. What makes Undo safe and understandable?

**Recommendation:** Implement Undo as a new compensating proposal at the current revision. Bind it to the original proposal/change hash, retain `inverse_of_proposal_id`, run the same planner path, and keep both histories. The server must reject stale or non-exact inverses and return an explicit reason.

**Basis:** V12 preserves applied/result/task history and uses revision checks, but generic client reversal is insufficient when later changes or completed work intervene (**V12, H**). Exact inverse, stale conflict, idempotency, and no-new-job-on-rejection require tests (**S**). Whether users understand compensating history is **Human deferred**.

**Prototype decision:** Never delete or mark the original event as if it did not happen.

## 7. How should card-grounded Ask preserve trust and context?

**Recommendation:** Add an optional validated `focus {card_id, entity_kind, entity_id}` to conversation creation. Resolve it only inside the tenant-owned frozen snapshot and persist server-derived title/source/context. Keep existing `selected_bed_id` compatible and reject contradictory inputs.

**Basis:** V12 already freezes conversation snapshots and validates selected beds; focus is a typed generalization of that proven boundary (**V12**). Focus/entity mismatch, tenant isolation, idempotency, and frozen-result validation need API tests (**S**).

**Prototype decision:** Opening Ask, switching roles, or choosing a populate-only suggested question performs zero inference. Only an explicitly submitted question may invoke DeepSeek.

## 8. How should recalculation consequences be communicated without fabricated precision?

**Recommendation:** Keep old values labelled until completion, then render the new server-derived metrics and signed deltas with names, units, and result binding. Highlight only changed values briefly. Never hard-code a narrative such as 97% → 92%, infer causality from co-occurrence, or let Council prose become the metric source.

**Basis:** The local planner is FarmTact's numerical authority and V12's typed-fact experience shows why valid references do not prove arbitrary causal prose (**V12**). Browser tests must compare displayed values to the actual completed response (**S**).

**Prototype decision:** Production and Planner impact facts are code-rendered. Council explanation remains optional, explicit, and advisory.

## 9. Which responsive layout should be the prototype default?

**Recommendation:** On mobile, use normal-flow stack/provenance/actions followed by board, consequences, Council, and strategies; use a four-item bottom navigation with secondary systems under More. On desktop, use a 25–35% compact card panel, central board, right contextual panel, and strategy tray below.

**Basis:** V12 already supports the target widths and mobile sheet patterns, while the plan calls for card proportions that do not expand into large desktop artwork (**V12, H**). Readability, thumb comfort, and task efficiency remain **Human deferred**.

**Prototype decision:** Normal-flow docking is the product default. `inline`/`sticky` is development-only and sticky must reserve safe-area/layout space.

## 10. What is motion allowed to do?

**Recommendation:** Use motion only to communicate selection, accepted application, persisted job state, completed deltas, and successful inverse completion. Selection uses 180–220 ms; reduced motion removes transforms and animated reordering while retaining immediate structural/status changes.

**Basis:** These transitions map to observable state changes (**H**). Vestibular comfort and subjective benefit require **Human deferred** evidence.

**Prototype decision:** No auto-advance, card flips, count-up metrics, decorative parallax, or animation-based proof of completion.

## 11. How should navigation and selected-card continuity work?

**Recommendation:** Provide swipe, Previous/Next, and Left/Right keyboard equivalence. Use a directional threshold so vertical scrolling wins until horizontal intent is clear. Persist only selected card ID and stack position in edition-scoped storage, validate on restore, and show a compact summary when the main stack scrolls away.

**Basis:** Edition-specific storage already exists and must remain isolated (**V12**). Gesture conflict, restore behavior, and active-card-only interaction require responsive tests (**S**). Natural discoverability is **Human deferred**.

**Prototype decision:** Never persist trusted eligibility, metrics, provenance, or job state in local storage.

## 12. What accessibility criteria are non-negotiable for the stack and panels?

**Recommendation:** Only the active card may be exposed or interactive; adjacent layers are decorative/inert. Require visible focus, 44–48 px targets, persistent disabled reasons, polite live calculation status, textual deltas/provenance, non-color board state, and complete dialog focus containment/restoration. No information is hover-only.

**Basis:** These address concrete risks introduced by stacked cards and contextual panels (**H**). Automated keyboard/accessibility-tree/computed-style checks are required (**S**). Screen-reader comprehension, physical touch, zoom comfort, and software-keyboard behavior remain **Human deferred**.

**Prototype decision:** Gesture and animation are enhancements, never the only way to operate or understand the interface.

## 13. Where should the Council appear, and when should it run?

**Recommendation:** Keep Council/context on the right at desktop and in a bottom sheet on mobile, with the selected card or compact summary retained. Show deterministic suggested questions, role/evidence status, and existing partial/withheld boundaries. Do not run agents automatically for selection, Details, Reserve, recalculation, metric updates, or panel opening.

**Basis:** V12 conversations are explicit and frozen; its qualitative quality limits argue against turning background prose into an invisible automatic layer (**V12**). Network/provider-ledger tests must show zero calls before explicit submission (**S**).

**Prototype decision:** Local planning remains fully usable without Council inference.

## 14. What should determine whether V13 advances beyond a prototype?

**Recommendation:** Keep V13 unpublished until the exact reservation/inverse/focus contracts, full regression, generated contracts, build, isolated PostgreSQL tests, responsive browser journeys, screenshots, and heuristic accessibility review pass while V12 remains unchanged. Even then, treat publication as a separate decision. Defer feed generalization, drag/drop, rewards, collections, automatic inference, and new domain entities until a representative human study validates comprehension and value.

**Basis:** FarmTact's immutable edition policy requires each public iteration to be pinned and isolated; a UI prototype does not justify consuming the edition or making usability claims (**V12**). Technical gates are **S**; farmer comprehension, enjoyment, and operational usefulness are **Human deferred**.

**Prototype decision:** Passing scripted checks establishes a working vertical slice, not product-market, agronomic, accessibility-conformance, or human-usability success.

## Ranked implementation recommendation

1. Preserve the server trust boundaries first: focus validation, exact inverse/stale logic, tenant/idempotency/revision tests.
2. Implement the fixed Heavy Rainfall → B3 → recalculation → Undo path with server-derived cards and consequences.
3. Complete active-card semantics, keyboard/button equivalence, live status, dialog focus, and reduced-motion behavior.
4. Add responsive layout and the selected-card continuity summary; keep the sticky dock experimental.
5. Run scripted evidence at all four widths, capture screenshots, and record bundle size and zero-provider behavior.
6. Conduct representative human/physical-device testing before generalizing the feed or claiming that the tactical metaphor improves understanding or motivation.

## Recommendation boundary

These recommendations are grounded in current contracts and foreseeable interaction risks. They do not establish that cards are superior to V12, that the interface is accessible in use, or that a farmer would make a better decision. Those comparative and human claims remain deliberately deferred.
