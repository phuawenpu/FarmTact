# V15 capability inventory and acceptance checklist

Status: implemented and published as V15 on 17 September 2026. The inventory was
built before development from V12/V13. Checked items below identify reachable card
workflows and their scoped verification; they do not establish human comprehension.
Publication evidence is in `reports/v15/release/`. Earlier dated follow-ups remain
as history; their pending statements are superseded by the final release record.

## Audit basis and parity rule

The primary implementation sources are `services/api/`, `packages/`, and `apps/web/src/`. The strongest historical acceptance evidence is `reports/v12/requirements-evidence.md`, `reports/v12/acceptance-status.md`, `reports/v13/implementation.md`, and the executable tests cited below. V13's `card-action-matrix.md` and `card-entity-tool-agent-map.md` define the trusted card/action boundary for the reservation episode.

A capability counts as restored only when a user can enter it from `/` or `/play`, complete it inside cards, return to the originating card with focus and position restored, and observe the authoritative saved result after server confirmation. A link, generic detail sheet, or button that only scrolls is not parity. Read-only paths must make zero provider calls. Mutation tests must assert revision, idempotency, tenant, history, and recovery behavior as applicable.

The five-card More index is the stable top-level map:

1. **Plan** — objective, assumptions, strategies, proposals, approval, reservations and recovery.
2. **Records & work** — farm setup/import, Inbox, orders, beds, inventory, tasks, results and corrections.
3. **Knowledge & evidence** — crops, sources, explanations, adviser conversations and Council.
4. **Experiments** — scenarios/quests, Data Explorer, dataset generation, simulations, research and Waste Rescue.
5. **History & preferences** — plans, discussions, simulations, events, replay, new attempts, accessibility, motion, audio and help.

## Shared card and navigation contract

- [x] One shell always exposes current objective, passive farm scene, one active card, and one action area with no more than three actions. Previous/Next, horizontal swipe, and keyboard navigation select the same ordered cards. Named browser evidence: `360/390/430/1280: one card and one three-action area` in `responsive-guide-contract.json`; `ArrowRight changes the active card` and `keyboard and swipe do not mutate farm/planner state` in `browser-cards-fresh.json`.
- [x] Default decision actions are **Explain / primary action / More**. Forms and detail cards use **Back** and an explicit review/submit action in the same action area. Named browser evidence: `review retains one card and one three-key action area` in `browser-cards-fresh.json`, action-label/footer parity checks in `bound-card-contract.json`, and the Records review/action checks in `records-browser.json`.
- [x] Forms, charts, source inspection, and transcripts render inside cards; scene objects, portraits, and buildings do not become navigation controls.
- [x] Every card carries stable card/type and canonical entity IDs, honest nullable frozen provenance/snapshot/result/revision bindings, board targets where applicable, and action eligibility/source/reason metadata. Named browser evidence: all 46 mission, Plan strategy/proposal, Records task/result-form, Knowledge crop/source/conversation, Experiments scenario/dataset/record, and History frozen-replay checks in `bound-card-contract.json`; in particular the disabled Records submit metadata follows live form validity, unrelated Knowledge bindings remain absent, and History replay retains the exact frozen result with unknown revision. Baseline: V13 focus and inverse contracts in `services/api/conversations.py`, `services/api/farm_workflow.py`; tests `test_v13_conversation_focus.py`, `test_v13_inverse_proposal.py`.
- [x] Detail/tool return restores origin card ID, card index, scroll position, and focused element after normal return and browser reload. Named browser evidence: `shell-reload-return.json` restores strategy card `strategy-1dee4a9ec3e906c66cab`, `Farm plan · 2 of 7`, the **More** action focus, and scroll position 316 after More → Plan → reload → Back, with zero writes/provider submissions; `card-return-browser.json` separately covers normal Plan and History focus/scroll return.
- [x] Alternative schedules and strategies say **Preview — not saved**. No board, farm, planning, or task state changes until the server confirms a mutation; an uncertain response is reconciled by GET/idempotency key before retry.
- [ ] Explain presents five explicit sections: what changed, why, tradeoff, evidence, next action. It includes allocation dates, affected beds, and server-derived signed differences, and labels projected, recorded simulation, and farmer-reported facts distinctly. Named browser evidence: `saved recalculation explanation contains five structured facts and allocation evidence` in `browser-cards-fresh.json`.
- [x] Opening/swiping/comparing/explaining/replaying invokes no provider. Creating a focused conversation is also zero-call; only explicit message, invite, Council, or research submission can enter DeepSeek. Named browser evidence: `read/explain triggered no provider request` and `full card journey made no automatic provider request` in `browser-cards-fresh.json`; `Reading and returning performs zero writes` in `card-return-browser.json`; focused-conversation and explicit-submit boundaries in `knowledge-browser.json` and `research-browser.json`. Baseline: `services/api/conversations.py`; `test_conversations.py`, `test_v13_conversation_focus.py`, `test_provider_isolation.py`.
- [x] A semantic scene transition is bound to an event ID and supplies affected entity IDs, effective date, before/after state, and authoritative fact differences. Normal motion plays once from that finite record; reduced motion renders the same final facts immediately. Named browser evidence: `recorded consequence transition remains factual and provider-free`, `normal-motion transition is finite`, and `reduced motion retains the same recorded consequence facts` in `browser-cards-fresh.json`. The recorded normal-motion artifact `reports/v15/video/page@db32f03de7d50f8d20f52138b7f1640c.webm` was sampled at frame 57, which visibly retained the recorded date, bed-stage changes, reservation, changed-bed outlines, delivery/disposal facts, and sandbox tasks.
- [x] Visible focus, labels, status announcements, vertical scrolling, 200% text zoom, reduced motion, keyboard order, and 360/390/430/desktop layouts pass. Named browser evidence: 26 responsive/overflow/guide checks and screenshots in `responsive-guide-contract.json`; `200% zoom uses document scrolling` plus finite/reduced-motion checks in `browser-cards-fresh.json`; six exact focus/scroll/read-only return checks in `card-return-browser.json`. Baseline style/interaction evidence: `apps/web/src/components/TacticalMission.tsx`, `reports/v13/accessibility-review.md`, `tests/browser/v13_tactical_cards.mjs`, `tests/browser/v13_real_journey.mjs`.

## Progressive onboarding on the ordinary sandbox farm

- [x] A new tenant starts from the general synthetic demo farm returned by the ordinary farm/bootstrap workflow, not `packages/beginner_fixture.py` or a separate four-bed journey. All existing demand remains in every calculation; one existing order is merely the initial objective. Named browser evidence: `360/390/430/1280: passive scene is not four-bed fixture` in `responsive-guide-contract.json`, `Lean Balanced and Resilient are all available` in `browser-cards-fresh.json`, and the canonical ordinary-order assertion in `bound-card-contract.json`.
- [x] Persist versioned guidance progress against the tenant's ordinary sandbox/planning context. It records current step, skipped/resumable state, and completed prompts without duplicating farm, order, proposal, or result state. Named browser evidence: `guide resume then skip preserves exact session and planner revision` and `guide skip and resume use only guidance mutations` in `responsive-guide-contract.json`, plus `previously skipped guide remains skipped` in `browser-cards-fresh.json`.
- [x] The guided episode reaches: inspect order → compare compatible plans → inspect one tradeoff → review a proposed change → recalculate → approve sandbox actions → inspect recorded result. Every underlying tool remains reachable before guidance completion. Named browser evidence: the full reservation/review/recalculation/inverse/approval/recorded-result chain in `browser-cards-fresh.json`, and all five top-level tools in `tools-browser.json`.
- [x] Skip and resume preserve the current farm and card context. Completing, skipping, or resetting guidance never unlocks capabilities or changes numerical inputs. Named browser evidence: `guide resume then skip preserves exact session and planner revision`, `guide skip and resume use only guidance mutations`, and the read-only-open checks at all four widths in `responsive-guide-contract.json`.
- [x] Beginner and returning-user tests execute the same APIs and card controls. The legacy isolated state machine in `services/api/beginner_journey.py` and `BeginnerGame.tsx` is historical reference only, not V15's source of farm state. Named browser evidence: `browser-cards-fresh.json` exercises the ordinary `/play` bootstrap/planning/farm-workflow APIs through the shared controls; `responsive-guide-contract.json` resumes that same ordinary session through those controls and records no beginner-journey request.

## Plan

### Objectives, assumptions, calculation, and comparison

- [x] **Path:** More → Plan → Objectives. Inspect confirmed/tentative demand, full demand totals, planning horizon, and the initial order; review edits before creating a revision-bound proposal.
- [x] **Path:** More → Plan → Assumptions. Review capacity, labour, cash, seasonal/yield settings, demand adjustments, explicit order changes, and reservations; validation errors remain on the draft card.
- [x] **Path:** Plan → Calculate. Queue and follow a local numerical job through persisted queued/running/terminal states; cancellation and interruption remain recoverable.
- [x] **Path:** Plan → Strategies. Compare every supported strategy from the same frozen input, including Lean, Balanced, and Resilient, with allocation dates, bed occupancy, crop mix, delivery, shortfall, inventory/waste, area, labour, cash/cost, and margin facts.
- [x] **Path:** Strategy → Schedule/details. Show allocations and constraint violations; infeasible outcomes remain inspectable and cannot be approved.
- [x] **Path:** Strategy → New attempt. Preserve the previous version/history and start from an explicit reviewed base rather than overwriting it.

Baseline implementation: `packages/planner/engine.py`, `packages/planning_numerics.py`, `services/api/planning_sessions.py`, `apps/web/src/components/GuidedPlanning.tsx`. Evidence: `test_v11_planning.py`, `test_planner.py`, `test_planner_v8.py`, `test_v11_planning_sessions.py`, `test_v11_session_adversarial.py`, `test_v11_worker.py`.

### Proposal, reservation, approval, and inverse episode

- [x] **Path:** Constraint card → Reserve space → review draft. Create a tenant-owned, current-revision dated reservation without changing the farm or plan.
- [x] **Path:** Draft → Apply & recalculate. Server accepts once, queues calculation, retains old metrics while running, then binds the new result/hash and signed deltas.
- [x] **Path:** Result → Explain. Explain the affected bed, dates, allocation differences, demand/service and resource tradeoff from structured server facts.
- [x] **Path:** Result → Approve sandbox work. Require feasible/current proposal, result, revision, and blocking-policy checks; create sandbox tasks only.
- [x] **Path:** Applied constraint → Undo. Ask the server for exact inverse eligibility, create a new compensating proposal, recalculate, and retain both original and inverse events. Show the exact disabled reason after an intervening revision or dependent work.
- [x] Concurrent apply/approve/inverse and repeated keys produce one durable outcome; stale revisions fail without mutation. `test_v15_concurrent_proposal_apply_inverse_and_approval_are_exactly_once` passes through real HTTP/PostgreSQL with four concurrent retries for each mutation, one original apply event, one inverse and one set of tasks; stale/conflicting-payload tests remain in the full regression.

Baseline: `services/api/farm_workflow.py`; `FarmerWorkflow.tsx`, `TacticalMission.tsx`; `test_v12_integration.py`, `test_v12_acceptance_adversarial.py`, `test_v13_inverse_proposal.py`, `tests/browser/v13_real_journey.mjs`.

V15 evidence: `reports/v15/plan-history-browser.json` (26 checks) covers local
calculation, reviewed assumptions/proposal, frozen schedules, saved replay and
new-attempt preservation. `browser-cards-fresh.json` (19 checks) covers real
reservation review/apply/recalculation, five-part explanation, compensating inverse,
approval and recorded consequences with zero provider requests.
`plan-recovery-browser.json` (five checks) adds a labelled post-response interruption
fixture for cancellation and stable-key retry. Server inverse staleness/tenant
rejection and append-only history are exercised by
`test_v13_inverse_proposal.py` in the 792-pass PostgreSQL regression. The remaining unchecked
rows still require their full listed field/validation coverage to be audited.
`plan-history-gaps-browser.json` adds seven passing real-service assertions: full
confirmed totals and tentative/horizon labels, demand-edit review, rejection of
invalid capacity without a revision change, a draft containing all supported
assumption groups, newest-first historical identity/facts, and a reviewed separate
new attempt that preserves the saved replay. The new attempt explicitly uses
current imported records; it does not silently import a historical snapshot.

`strategy-facts-browser.json` verifies all three strategies retain the same frozen result, expose every server metric and dated bed/crop allocations, and cause zero writes while comparing. Its infeasible display case is explicitly a transport fixture, not a claimed real numerical result.

## Records & work

### Farm setup and imports

- [x] **Path:** More → Records & work → Farm. Display the active farm and review a replacement import as an explicit transition showing source, cutoff, counts, warnings, and state that will be replaced. Cancel leaves the current farm untouched.
- [x] Support the synthetic seed and supported structured farm import as an atomic, tenant-scoped farm/workflow transition. Named browser evidence: explicit parsed JSON review, new remembered session and retained prior sessions in `plan-history-browser.json`; atomic demo transition and new-session DOM isolation in `records-extended-browser.json`.
- [x] **Path:** Imports → accounting/manual/document/photo. Accept supported CSV/XLSX accounting records, manual/correction rows, PDF/image extraction, and store the original private source. Named browser evidence: real CSV/source inspection in `records-extended-browser.json`, real XLSX parsing and labelled retained-file image outage in `records-gaps-browser.json`; provider extraction remains deliberately uninvoked.
- [x] **Path:** Inbox candidate → Review. Show extracted/raw values, units, date, crop/category, provenance, warnings, correction target and signed delta; explicit accept/reject is required. Photos never authorize yields, inventory, tasks, or operations. Named evidence: manual/CSV confirmation and XLSX rejection in the three Records reports; controlled extracted fields remain explicitly inactive in `records-extended-browser.json`.
- [x] Unsupported crops remain visible for accounting with a planning warning. Ambiguous dates/currencies, formulas, unknown schemas, non-finite values, invalid correction targets, and changed replay payloads fail closed. Backend evidence remains `test_financial_ingestion.py`, `test_document_extraction.py`, `test_v12_acceptance_adversarial.py`, and request/idempotency tests; browser transport replay evidence is in `records-browser.json`.

Baseline: `packages/ingestion/financial.py`, `services/api/document_extraction.py`, `services/api/farm_workflow.py`, `FarmerWorkflow.tsx`. Evidence: `test_financial_ingestion.py`, `test_document_extraction.py`, `test_v12_upload_trial.py`, `test_v12_pdf_trial.py`, `test_farm_workflow.py`, `test_v12_acceptance_adversarial.py`.

### Orders, beds, inventory, work, results, and recovery

- [x] **Path:** Records & work → Orders/Beds/Inventory. Inspect stable entities, dates, quantity/unit, booked versus tentative semantics, crop/batch/lot origin, expiry, and current reservation/occupancy. A market signal cannot silently become an order. Named browser evidence: ordinary record facts or an explicit empty inventory state in `records-gaps-browser.json`.
- [x] **Path:** Approved plan → Work. Show generated sow/transplant/harvest/delivery tasks with biological dates, checklist, location, quantity/unit, and sandbox status. Historical stages are not regenerated as pending work. Named browser evidence: exact proposal approval/task identity in `records-extended-browser.json` and exact task binding in `records-gaps-browser.json`.
- [x] **Path:** Task → Record result → Review/submit. Validate current task status, complete checklist, quantity/unit and owned photo reference; append exactly one result event. Named browser evidence: failed/recovery result in `records-extended-browser.json` and completed checklist/quantity/note result in `records-gaps-browser.json`.
- [x] **Path:** Completed task → Correct result. Require expected event revision, field, corrected value and reason; append a correction rather than rewriting history. Duplicate same-payload keys replay; changed payloads conflict. Named browser evidence: quantity correction in `records-browser.json`, result-note correction and incremented event revision in `records-gaps-browser.json`.
- [x] **Path:** Verify/recovery. Incorporate farmer-reported task events into the reported forecast, preserve completed work and lot identity, expose negative-cash/infeasible recovery honestly, and create a future-only replan. Named browser evidence: reported-forecast/source boundary in `records-gaps-browser.json`; real future-only recalculation, retained schedule comparison, preserved task event, and focus/scroll return in `records-extended-browser.json`.
- [x] **Path:** Inventory → Waste Rescue. Review dated terminal lots and conservative mixed expiry, then compare the existing three read-only rescue options. The supported V12/V13 boundary ends at this frozen-lot comparison (`WasteRescueDialog` in `apps/web/src/components/FarmerWorkflow.tsx`, `POST /api/v1/farm-workflow/waste-rescue`); it has no rescue execution or proposal schema. Resource or demand changes use the separate ordinary Plan proposal/recalculation workflow and must not apply hypothetical rescue prices automatically.

Baseline: `packages/workflow_contracts.py`, `services/api/farm_workflow.py`, `services/api/simulation.py`; evidence: `test_farm_workflow.py`, `test_v12_integration.py`, `test_v12_acceptance_adversarial.py`, `test_simulation_execution.py`, `test_v11_session_adversarial.py`.

V15 contextual transition evidence: `context-import-browser.json` passes six checks for Inventory → Waste Rescue → exact inventory/focus/scroll return, current-versus-incoming farm cutoff/count/source review, explicit validation/retention warnings, cancellation preserving the exact original farm, and zero writes/inference while reviewing. Existing `scenarios-browser.json` proves the real frozen-lot three-option comparison.

## Knowledge & evidence

- [x] **Path:** More → Knowledge & evidence → Crops. Reach all 20 V13 crop SVG assets and the 12 implemented crop catalogue/profile records; show recipe/growth limits, evidence references, freshness and representative-art notice. Explicit stage labels and the non-state notice prevent ready-stage reference art from claiming a current crop is harvest-ready. Named browser evidence: all 12 `crop profile … exposes supported recipe boundary` assertions and `all 20 representative crop-stage assets are explicitly mapped and reachable` in `knowledge-browser.json`. Baseline: `apps/web/src/components/Visuals.tsx`, crop assets, `services/api/app.py` crop/evidence routes, `packages/growth.py`.
- [x] **Path:** Sources/evidence. Inspect public source registry, observation time, retrieval time, units, coverage, freshness/stale/missing state, licence/export policy, and exact facts admitted to a calculation or answer. `labelled source transport fixture exposes complete registry metadata and exact admitted facts` verifies every field and an exact typed fact; the ordinary empty registry continues to render an honest missing-source record. Answer-specific typed references remain visible in the recorded transcript. Baseline: `packages/ingestion/`, `services/api/provenance.py`, `services/api/explorer_public.py`; `test_ingestion.py`, `test_explorer_public.py`, `test_fixture_reproducibility.py`.
- [x] **Path:** Any eligible entity → Explain. Use deterministic structured facts without inference and retain explanation references on the card/result/event.
- [x] **Path:** Card → Ask specialist. Server validates the card/entity/snapshot focus; opening restores the complete saved transcript without inference. Explicit submit can create a bounded DeepSeek request with draft retained across provider/transport failure. Named browser evidence: `V15 adviser submission uses exact canonical selected focus`, `historical Knowledge transcript decodes real planning snapshot binding`, `explicit retry uses the same thread and idempotency identity`, and `read-only refresh does not resubmit accepted provider work` in `v15_knowledge.mjs`.
- [x] **Path:** Conversation → Invite specialist / Council. Preserve reply graph, all seven functional roles, cited typed facts, validation status, partial/withheld/rejected findings, dissent, and planner conclusion. Proposed actions remain non-mutating until converted to a reviewed proposal. Named browser evidence: direct partial, invited withheld, conversational Council, full six-turn transcript assertions in `v15_knowledge.mjs`, plus the recorded validated handoff/apply assertions in `v15_tools.mjs`.
- [x] **Path:** Plan → Council review. Review the frozen result with role-appropriate evidence and exact strategy facts; budget/missing-source failures remain visible and numerical work stays usable. The labelled budget-503 assertion `planning Council budget outage keeps numerical result usable without automatic retry` verifies one explicit request, a visible error, unchanged session revision and strategy count, and no automatic retry; conversational partial/withheld/success fixtures separately verify retained finding presentation.

Baseline: `services/api/conversations.py`, `conversation_store.py`, `planning_council.py`, `council.py`, `apps/web/src/components/AdvisorEvidence.tsx`. Evidence: `test_conversations.py`, `test_v12_discussion_proposal.py`, `test_v12_demand_grounding.py`, `test_v11_planning_council.py`, `test_research_advisor_trial.py`.

## Experiments

### Scenarios, quests, and simulations

- [x] **Path:** More → Experiments → Scenarios/quests. List existing quests and create a frozen branch from an explicit root. Review bounded controls before running locally. Evidence: real branch creation/run in `v15_tools.mjs` and explicit parent, dataset and conversation roots in `v15_scenarios.mjs` and `v15_experiment_gaps.mjs`.
- [x] **Path:** Scenario → Run/compare. Persist the branch, calculate changed forecasts, display infeasible learning results, highlight only changed controls/entities, and compare only compatible frozen roots. Evidence: real same-policy calculations plus changed-control/entity cards; the labelled result-transport fixture verifies infeasible status and violations remain visible; `scenario-controls-browser.json` verifies incompatible roots retain the server reason.
- [x] **Path:** Scenario → Continue. Continue without replacing the accepted main worklist; retry/cancel/restart are idempotent and recoverable. Conversation-proposed experiments use the exact frozen conversation snapshot. Evidence: `scenarios-browser.json`, `scenario-controls-browser.json`, and the exact conversation ID/baseline-hash assertions in `experiment-gaps-browser.json`.
- [x] **Path:** Simulations. Create from an accepted sandbox plan, advance the durable clock, show finite recorded task/demand/inventory/cash/crop-stage consequences, and replan while preserving executed tasks and harvest-lot identity.

Baseline: `services/api/scenarios.py`, `services/api/simulation.py`, `apps/web/src/components/SimulationPanel.tsx`; `test_scenarios.py`, `test_scenario_postgres.py`, `test_simulation_execution.py`, `test_v8_reliability_postgres.py`.

### Data Explorer and datasets

- [x] **Path:** Experiments → Data Explorer. Inspect records/series with filtering, pagination, numeric sort, relationships, source metadata and accessible charts inside cards. Evidence: `explorer-browser.json` covers date/crop filters, numeric descending sort, relationships, responsive text zoom and read-only behavior; `v15_tools.mjs` covers saved snapshot browse.
- [x] **Path:** Dataset generation/forecast settings. Preview bounded EWMA/settings changes locally, review inputs and hashes, freeze an immutable tenant-owned snapshot, and reload it exactly. Named browser evidence: `generated dataset reopens with exact immutable ID hash and facts without regeneration` performs Preview → review → Save, reloads the document, reopens the saved record through Data Explorer, and proves the ID, content hash and complete record payload are unchanged while preview/save POST counts remain exactly one.
- [x] **Path:** Snapshot → Run strategy. Continue into a compatible numerical run; distinguish unrelated roots even when raw records match. Saved forecast replay never recomputes. The supported scenario API calculates all Lean/Balanced/Resilient policies; dataset policy selection applies to projection/export and is not invented as a scenario input. `experiment-gaps-browser.json` proves the exact snapshot ID is submitted and the real branch completes all three policy comparisons.
- [x] **Path:** Export. Download private/public records only when registry reuse policy permits; neutralize spreadsheet formula injection. Browser evidence covers filtered CSV/JSON export and ordering (`tools-browser.json`, `explorer-browser.json`); server regression `test_explorer_public.py` remains the authority for reuse denial and formula neutralization.

Baseline: `services/api/data_explorer.py`, `explorer_public.py`, `apps/web/src/components/DataExplorer.tsx`, `ExplorerChart.tsx`; `test_data_explorer.py`, `test_explorer_postgres.py`, `test_explorer_review.py`, `test_explorer_numerics.py`, `tests/browser/data_explorer.mjs`.

### Council research

- [x] **Path:** Experiments → Research/reviews. Create and configure the existing research session, run its local calculation, explicitly request bounded specialist review when eligible, challenge/revise through cards, and inspect the report. The real-service broad suite covers presentation, frozen context, scripted discussion, calculation, proposal/apply, challenge and report; `v15_research.mjs` covers explicit actual-adviser submission/replay boundaries.
- [x] Current view remains bounded while complete append-only history is reachable. Cancel/retry/restart preserves original actions, partial/withheld findings, and makes no duplicate provider call. Named assertions cover history beyond 20 revisions, exact displayed revision/busy action parity, accepted-provider refresh without resubmit, interrupted calculation GET reconciliation, and explicit run/cancel/retry.

Baseline: `services/api/council_research.py`, `apps/web/src/components/CouncilResearch.tsx`; `test_sessions.py`, `test_v8_history.py`, `test_v8_cancellation.py`, `test_independent_review.py`, `test_postgres.py`.

## History & preferences

- [x] **Path:** More → History & preferences → Plans/discussions/simulations/events. List saved objects newest first with type, status, revision/snapshot/result identity, effective date and provenance.
- [x] **Path:** History item → Replay. Render immutable recorded state and event sequence read-only with zero recalculation, mutation, or inference. A separate **New attempt** explicitly creates a new branch/session/version.
- [x] Conversation replay retains full turns, citations, validation, focus and partial/withheld states. Planning replay retains evidence validation and frozen market/source context. Simulation replay retains recorded consequences.
- [x] Preferences persist accessibility, reduced motion, and existing optional audio settings per edition/tenant as appropriate. Updated help explains card navigation, device-keyboard voice typing, fact labels, sandbox-only actions, recovery, and provider submission boundaries.

Baseline: replay routes in `services/api/app.py`, `planning_sessions.py`, `conversations.py`, `simulation.py`, `council_research.py`; `AudioControls.tsx`, `lib/audio.ts`; evidence: `test_conversations.py`, `test_v11_planning_sessions.py`, `test_simulation_execution.py`, `test_v8_history.py`, browser audio suites.

## Cross-cutting release gates

- [x] Generated frontend contracts are current; frontend production build passes and CSS/JS bundle sizes are recorded (V13 baseline JS was 601.77 kB with an over-500 kB warning).
- [x] Full Python regression passes against isolated PostgreSQL, plus focused concurrent create/apply/save/result tests. SQLite-only evidence is insufficient for release.
- [x] Tenant isolation covers every restored read/write route. Idempotency, stale revisions, concurrent requests, append-only history, transaction rollback, and restart persistence pass.
- [x] Global/IP/session limits, stricter write limits, anonymous-session admission, provider concurrency/hour/day budgets, and `Retry-After` behavior pass. Drafts survive admission/provider failures and uncertain writes reconcile before retry.
- [x] Browse, Explain, compare, preview, replay, local calculation and local simulation produce zero provider requests. Provider requests use only the validated DeepSeek gateway after explicit submission; no fallback exists.
- [x] Complete browser journeys at 360, 390, 430, and desktop widths cover keyboard, swipe, vertical scrolling, focus return, text zoom and reduced motion. Normal-motion recordings prove finite causal transitions from recorded events.
- [x] Farm import transition, task reporting/correction, provider outage, 429, interrupted calculation, stale approval, inverse ineligibility and reload each have a recoverable end-to-end test.
- [x] V15 publishes as a new immutable edition only after these checks pass; `/` and `/play` resolve solely to V15. Earlier sources/images and recoverable data remain private and unchanged, with no automatic cross-edition state merge. Shared abuse/provider counters survive cutover.

## Known limits that V15 must state truthfully

- Actual farm operations are disabled. Approval creates sandbox work; no card may claim to sow, harvest, deliver, contact a buyer, or control equipment.
- The numerical outputs are projections from declared inputs. Simulation results are recorded synthetic execution. Farmer-entered task results are reported and unverified unless separately reviewed.
- The implemented catalogue and recipe/planner models define supported crops. Unsupported crops may be retained for accounting but cannot be silently assigned agronomic recipes. V15 does not add new agricultural models.
- Crop art is representative. Stage art must follow explicit supported mappings; visual appearance is not crop health or harvest-readiness evidence.
- Public sources may be stale, absent, registry-only, or not reusable for export. Weather and Market advisers can remain partial when required source context is absent.
- Council/adviser prose is advisory and can be partial, withheld, rejected, or unsupported. Typed server facts and deterministic calculations remain authoritative; prior V12/V13 evidence is not a general semantic-quality proof.
- Document extraction was exercised on bounded native PDFs/images and synthetic examples, not every scanner/layout or field diagnosis. A photograph cannot authorize a yield, task, or state change.
- There is no live ERP/webhook/buyer outreach, autonomous inference, community feed, custom recording/transcription, reward system, or drag-and-drop requirement in V15.
- Automated/browser completion does not establish farmer comprehension, agronomic efficacy, physical-device behavior, screen-reader coverage, or representative-user usability. Human usability remains unverified until tested with representative new users.

## Integration advice

Keep the existing state machines and put a card projection layer over them. The shared card should refer to canonical IDs and result/event hashes; it should not become another persistence model for farms, plans, conversations, or experiments. Add onboarding progress separately and bind it to the ordinary planning context.

Implement the reservation episode first against `farm_workflow` and `planning_sessions`, because it exercises the hardest shared contracts: draft versus saved state, revision conflicts, async reconciliation, signed numerical differences, scene transitions, approval and exact inverse. Once that card/result/event vocabulary is stable, adapt imports/tasks, conversations, scenarios, explorer and research through dedicated card adapters.

Extend responses additively for explanation references and semantic transitions. Derive explanations from saved result/event facts and store references, so opening Explain or replay stays zero-call. Preserve the old endpoints during integration; route replacement should happen only after each capability has a reachable V15 card journey and end-to-end test.

## V15 integrated-card browser evidence

The named assertions below are in `tests/browser/v15_tools.mjs` and run through `/` on the real isolated service unless explicitly marked as a transport fixture.

- [x] **More → Knowledge & evidence → crop/source cards:** `knowledge-browser.json` records 27 passing assertions, including every one of the 12 supported crop profiles, all 20 reachable stage-labelled SVG assets, the labelled full source-metadata/admitted-fact fixture, and the Council budget-outage boundary. `crop card exposes recipe and evidence boundary`, `source card exposes freshness and status`, and `knowledge browse remains provider-free` in the broad suite retain the 360 px and zero-provider browse checks.
- [x] **Knowledge → Saved discussions → replay → reviewed handoff:** the explicitly labelled recorded-transcript transport fixture proves `recorded adviser handoff preserves exact source IDs` and `linked draft is applied only by the explicit footer action`. It supplies an already-recorded `references_verified` adviser message; it never fabricates or invokes provider inference.
- [x] **Experiments → Research & reviews → calculation/proposal/challenge:** `research calculation records three strategies`, `research edit is previewed before apply`, `research apply creates a new frozen input version`, and `research challenge records corrected evidence status` exercise real service mutations.
- [x] **Research → Revision history:** `research append-only revision history is reachable in cards` and `research history endpoint declares zero inference` exercise `/api/v1/council-research/{id}/history` through the V15 card and verify its replay declaration.
- [x] **Research → Presentation/context/discussion:** `research presentation, context and scripted discussion actions persist` saves checkpoint presentation settings, selects a frozen canonical reference, submits one scripted message, and advances one queued turn.
- [x] **Research → Actual adviser outage:** the explicitly labelled provider-outage transport fixture proves `explicit provider outage is visible and never auto-retried` and `provider outage retains the saved question draft`; exactly one explicit POST is attempted and the fixture returns 503.
- [x] **Knowledge → contextual validated gateway:** `tests/browser/v15_knowledge.mjs` proves direct partial, invited withheld and conversational Council results, a six-turn retained transcript, exact canonical order focus, footer/card-action parity, and the real `session_id:result_id` frozen planning snapshot binding without treating the farm-schema version as a planning revision. Its post-commit outage assertions prove the same thread and idempotency identity are reused, accepted POSTs leave no resend state, and transcript refresh is read-only. Evidence is persisted at `reports/v15/knowledge-browser.json` (27 passing assertions, 2026-09-17).
- [x] **Research → remaining supported card actions:** `tests/browser/v15_research.mjs` proves queued-turn stop, reservation preview/discard, reviewed order edit into v2, current eligible simulation-only result choice, stale historical result disablement, history beyond 20 revisions, report documents/links, saved-study reopen, and actual-discussion identity across reload. It asserts the visible result card's session, input hash, projected-outcome basis and server eligibility, and exact history revision/busy footer parity. Its accepted-POST fixture proves transcript refresh makes no duplicate provider submission; its controlled fixture proves interrupted-run GET reconciliation without automatic retry followed by explicit `run → cancel_calculation → retry_calculation`. Evidence is persisted at `reports/v15/research-browser.json` (18 passing assertions, 2026-09-17).
- [x] **Experiments → Dataset/scenario:** `generated preview saves an immutable snapshot`, `saved dataset export returns CSV`, `scenario branch persisted separately`, and `scenario local run reaches a terminal result` use real APIs. `dataset/scenario workflow makes no provider request` covers the local-only boundary.
- [x] **Experiments → frozen roots and comparison facts:** `experiment-gaps-browser.json` records 12 passing assertions. It verifies an exact conversation ID and frozen baseline hash, explicit changed controls and affected entities, a labelled infeasible-result presentation fixture alongside real comparisons, exact dataset persistence across document reload without regeneration, and an exact saved-dataset branch request with no invented policy field; the real branch completes Lean, Balanced and Resilient calculations.
- [x] **Shared shell:** five `tool reachable:` assertions cover every top-level tools-index destination; `360px shell has no horizontal document overflow`, `mobile tool cards retain vertical scrolling`, and `no browser page errors` cover this suite's mobile baseline.
- [x] **Broad tools journey:** `reports/v15/tools-browser.json` records 30 passing assertions on the isolated real service, including all five tools, crop/source browse, immutable dataset/export, scenario run, the local research cycle, reviewed adviser handoff and explicit provider-outage recovery.

Verification limits (not claims of live provider quality or human usability):

- Research stale results are disabled in the DOM and current results are chosen through the real service, but a direct stale-version API rejection remains covered only by backend regression rather than this browser suite.
- Successful provider prose remains a transport-fixture validation rather than live inference. No acceptance suite invokes an actual provider.
- Automated completion remains no evidence of comprehension; representative-user usability is unverified.

## Final local acceptance evidence — 17 September 2026

- The current isolated PostgreSQL suite passes **792 tests, one skipped, four warnings
  in 857.27 seconds** (`reports/v15/regression-final.xml`). The skip is the optional
  generated News-cache contract. The added concurrent HTTP test covers proposal
  creation/application, inverse and approval; existing focused PostgreSQL tests
  cover guidance/import races, restart, stale revisions and rollback.
- `simulation-replan-browser.json` passes nine checks through real UI mutations:
  an accepted/executed plan is recalculated and approved, while simulation identity,
  clock, completed task IDs, inventory, harvest-lot origins and recorded totals
  remain unchanged. Its old result still replays and no provider request occurs.
- `history-replay-browser.json` passes 12 checks for full labelled recorded
  discussion fields, real simulation/event replay, motion and audio persistence,
  and zero POST/provider calls. `plan-history-gaps-browser.json` separately proves
  historical list metadata and a reviewed new attempt preserving the saved plan.
- `records-approval-guard-browser.json` proves the infeasible server reason is
  visible, submit disabled, metadata server-sourced, and no POST attempted.
  `strategy-facts-browser.json` proves infeasible schedules remain inspectable.
- `records-extended-browser.json` passes 20 checks, including retained source bytes
  inspected inside the card. Binary PDF/workbook originals remain downloadable;
  extracted rows and metadata stay inside cards, without a custom document parser.
- Explanations are the eligible mission/proposal-result card projections already
  covered by the five-part explanation and canonical binding tests; static tools
  or unsupported crop states do not invent numerical explanations. Read-only
  navigation, comparisons and preview never imply saved farm state.

Private staging, exact-image acceptance, public cutover and counter preservation
are still pending. These local results do not establish representative-user
comprehension, field performance or new provider prose quality.

Security/recovery evidence for the restored routes is the current full regression,
including `tests/security/test_api.py`, `test_request_admission.py`,
`test_budget_day.py`, `tests/review/test_abuse_postgres.py`,
`test_provider_isolation.py`, `test_postgres_concurrency.py`,
`tests/gameplay/test_v12_acceptance_adversarial.py`,
`test_v13_inverse_proposal.py`, both V15 guidance/transition files, and the
Explorer/Research PostgreSQL suites. These exercise tenant ownership/FKs,
concurrent receipt replay, changed-payload conflicts, stale revisions, append-only
events, rollback, restarted stores and fixed limits without provider fallback.
Frontend recovery is covered separately by Records' labelled 429/post-commit-503
fixtures, `plan-recovery-browser.json`, `knowledge-browser.json`,
`research-browser.json`, `records-extended-browser.json`, and the real inverse
journey. None of these claims proves preservation of production counters across
cutover; that remains in the open publication gate.

Final native form follow-up: `native-assumptions-browser.json` passes 36 checks
for capacity and every supported demand/seasonal/order/reservation row group.
It covers add/edit/remove, persistence, exact review payloads and allowed enums.
The suite found and verified a fix for Add → Amend inheriting an empty crop and
unintended due date. Native row editing, reload and review make zero writes; the
explicit Create request is intercepted for payload inspection. Real proposal
creation and apply/recalculation remain covered by the integrated Plan and
reservation journeys. Cross-width interaction checks pass 25 assertions for
keyboard, equivalent swipe targets, 200% zoom and reduced motion. Full mutation
journeys at the remaining widths and exact staged-image acceptance remain gates.

The clean production build and generated-contract drift check pass
(`frontend-build.json`, `frontend-build.txt`). The main JS is 232.72 kB / 72.99 kB
gzip; lazy tool chunks are measured separately in the artifact. Complete real-service
reservation → inverse → approval → recorded simulation journeys now pass 20 checks
each at 360, 430 and 1280 px (`browser-cards-360.json`, `browser-cards-430.json`,
`browser-cards-1280.json`), complementing the 390 px fresh/returning evidence.
The initial 430 px harness timeout was traced to reload/guidance reconciliation: no
calculation POST had been sent and the session stayed DRAFT. The harness now waits
for the intended bound session and pending requests before acting. No backend job
was restarted or API limit relaxed. Exact staged-image/browser and public cutover
verification remain outstanding.

Staging reopened the final frontend gates: the actual candidate exposed a mobile
review-ID overflow and delayed status-poll/readiness race. These are implementation
defects, not waived test limits. The first image will not be published. Overflow
assertions now apply to every complete-journey screenshot; delayed-response
coherence and repeated full-width journeys precede a corrected clean build.

Final local follow-up (17 September, 14:53 UTC): corrected source `f50b9e7`
passes all four complete widths (26 checks each) plus 20 read-only return/reload
checks. The final clean build matches the tested main-chunk hash. The controlled
response regression passes 11 narrowly stated coherence/busy/context/admission
checks; it does not claim a separate running-job polling rearm. The original
staged candidate remains rejected until a newly pinned image passes actual
private latency/visual acceptance.

Final control delta: `reservation-eligibility-browser.json` passes 34 checks on
`index-C89Jrp2Y.js`, covering unavailable reservation windows, denied approval,
keyboard submission prevention, matching action metadata and visible server
reasons, plus real persisted work navigation. No records are created by this
suite. `terminal-reconciliation-browser.json` contains the 11 controlled real
response checks; `final-motion-review.json` records timed finite transitions and
identical reduced-motion facts. Full four-width evidence is
`browser-cards-widths.json`, including `browser-cards-390.json`. Publication is
still unchecked until the corrected exact image passes private acceptance and
public preservation/route verification.


## Final publication evidence — 17 September 2026

Source `a5ab2a8`, immutable image `sha256:7f19f29f1465ca9f678f29e0336a4bbcccd5d2ba03826d8184f52cff693c39b4`:
`release/operator-acceptance.json` passes 20 real API checks;
`release/staged-browser.json` passes 26 exact-image journey checks;
`release/public-browser.json` passes 67 read-only checks at all four widths;
`release/public-isolation.json` passes 13 route/session/dataset checks;
`release/public-preservation.json` passes all nine history, storage and shared
admission-budget checks. Paths are relative to `reports/v15`.
`release/retention.json` records archive-only retention, a recovery snapshot,
V14's stopped worker and no deleted storage. The earlier staging/publication
pending paragraphs are historical. The rejected candidate was never published.

The staged operator journey includes one identity-bound proposal → recalculation
→ inverse → approval → task report → correction → historical replay chain, so the
A05 end-to-end evidence is not limited to composition across separate browser runs.
`release/polling-rearm.json` supplements real delayed-response acceptance with an
explicitly labelled read-only RUNNING-status overlay: return from tools rearms
polling for the same job without a POST or provider request.


Postpublication semantic audit reopened explanation acceptance: saved general
proposals can expose raw assumption JSON across core stages. See
`reports/v15/final-semantics-published-failure.json`. Five headings are insufficient
without stage-specific causal facts. The full rewrite goal remains active, with a
V16 correction required by immutable edition policy; earlier numerical, workflow,
security and release checks retain their stated scope.
