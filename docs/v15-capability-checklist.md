# V15 capability inventory and acceptance checklist

Status: implementation input, audited 17 September 2026. This inventory describes behavior present in the V12/V13 codebase that V15 must make reachable through the shared card experience. It is not a claim that V15 parity is complete. Checkboxes remain open until the V15 route and end-to-end test exist.

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

- [ ] One shell always exposes current objective, passive farm scene, one active card, and one action area with no more than three actions. Previous/Next, horizontal swipe, and keyboard navigation select the same ordered cards.
- [ ] Default decision actions are **Explain / primary action / More**. Forms and detail cards use **Back** and an explicit review/submit action in the same action area.
- [ ] Forms, charts, source inspection, and transcripts render inside cards; scene objects, portraits, and buildings do not become navigation controls.
- [ ] Every card carries stable card/type and canonical entity IDs, frozen provenance, snapshot/result binding, revision, board targets, eligibility, and a server reason when unavailable. Baseline: V13 focus and inverse contracts in `services/api/conversations.py`, `services/api/farm_workflow.py`; tests `test_v13_conversation_focus.py`, `test_v13_inverse_proposal.py`.
- [ ] Detail/tool return restores origin card ID, card index, scroll position, and focused element after normal return and browser reload.
- [ ] Alternative schedules and strategies say **Preview — not saved**. No board, farm, planning, or task state changes until the server confirms a mutation; an uncertain response is reconciled by GET/idempotency key before retry.
- [ ] Explain presents five explicit sections: what changed, why, tradeoff, evidence, next action. It includes allocation dates, affected beds, and server-derived signed differences, and labels projected, recorded simulation, and farmer-reported facts distinctly.
- [ ] Opening/swiping/comparing/explaining/replaying invokes no provider. Creating a focused conversation is also zero-call; only explicit message, invite, Council, or research submission can enter DeepSeek. Baseline: `services/api/conversations.py`; `test_conversations.py`, `test_v13_conversation_focus.py`, `test_provider_isolation.py`.
- [ ] A semantic scene transition is bound to an event ID and supplies affected entity IDs, effective date, before/after state, and authoritative fact differences. Normal motion plays once from that finite record; reduced motion renders the same final facts immediately.
- [ ] Visible focus, labels, status announcements, vertical scrolling, 200% text zoom, reduced motion, keyboard order, and 360/390/430/desktop layouts pass. Baseline style/interaction evidence: `apps/web/src/components/TacticalMission.tsx`, `reports/v13/accessibility-review.md`, `tests/browser/v13_tactical_cards.mjs`, `tests/browser/v13_real_journey.mjs`.

## Progressive onboarding on the ordinary sandbox farm

- [ ] A new tenant starts from the general synthetic demo farm returned by the ordinary farm/bootstrap workflow, not `packages/beginner_fixture.py` or a separate four-bed journey. All existing demand remains in every calculation; one existing order is merely the initial objective.
- [ ] Persist versioned guidance progress against the tenant's ordinary sandbox/planning context. It records current step, skipped/resumable state, and completed prompts without duplicating farm, order, proposal, or result state.
- [ ] The guided episode reaches: inspect order → compare compatible plans → inspect one tradeoff → review a proposed change → recalculate → approve sandbox actions → inspect recorded result. Every underlying tool remains reachable before guidance completion.
- [ ] Skip and resume preserve the current farm and card context. Completing, skipping, or resetting guidance never unlocks capabilities or changes numerical inputs.
- [ ] Beginner and returning-user tests execute the same APIs and card controls. The legacy isolated state machine in `services/api/beginner_journey.py` and `BeginnerGame.tsx` is historical reference only, not V15's source of farm state.

## Plan

### Objectives, assumptions, calculation, and comparison

- [ ] **Path:** More → Plan → Objectives. Inspect confirmed/tentative demand, full demand totals, planning horizon, and the initial order; review edits before creating a revision-bound proposal.
- [ ] **Path:** More → Plan → Assumptions. Review capacity, labour, cash, seasonal/yield settings, demand adjustments, explicit order changes, and reservations; validation errors remain on the draft card.
- [ ] **Path:** Plan → Calculate. Queue and follow a local numerical job through persisted queued/running/terminal states; cancellation and interruption remain recoverable.
- [ ] **Path:** Plan → Strategies. Compare every supported strategy from the same frozen input, including Lean, Balanced, and Resilient, with allocation dates, bed occupancy, crop mix, delivery, shortfall, inventory/waste, area, labour, cash/cost, and margin facts.
- [ ] **Path:** Strategy → Schedule/details. Show allocations and constraint violations; infeasible outcomes remain inspectable and cannot be approved.
- [ ] **Path:** Strategy → New attempt. Preserve the previous version/history and start from an explicit reviewed base rather than overwriting it.

Baseline implementation: `packages/planner/engine.py`, `packages/planning_numerics.py`, `services/api/planning_sessions.py`, `apps/web/src/components/GuidedPlanning.tsx`. Evidence: `test_v11_planning.py`, `test_planner.py`, `test_planner_v8.py`, `test_v11_planning_sessions.py`, `test_v11_session_adversarial.py`, `test_v11_worker.py`.

### Proposal, reservation, approval, and inverse episode

- [ ] **Path:** Constraint card → Reserve space → review draft. Create a tenant-owned, current-revision dated reservation without changing the farm or plan.
- [ ] **Path:** Draft → Apply & recalculate. Server accepts once, queues calculation, retains old metrics while running, then binds the new result/hash and signed deltas.
- [ ] **Path:** Result → Explain. Explain the affected bed, dates, allocation differences, demand/service and resource tradeoff from structured server facts.
- [ ] **Path:** Result → Approve sandbox work. Require feasible/current proposal, result, revision, and blocking-policy checks; create sandbox tasks only.
- [ ] **Path:** Applied constraint → Undo. Ask the server for exact inverse eligibility, create a new compensating proposal, recalculate, and retain both original and inverse events. Show the exact disabled reason after an intervening revision or dependent work.
- [ ] Concurrent apply/approve/inverse and repeated keys produce one durable outcome; stale revisions fail without mutation.

Baseline: `services/api/farm_workflow.py`; `FarmerWorkflow.tsx`, `TacticalMission.tsx`; `test_v12_integration.py`, `test_v12_acceptance_adversarial.py`, `test_v13_inverse_proposal.py`, `tests/browser/v13_real_journey.mjs`.

## Records & work

### Farm setup and imports

- [ ] **Path:** More → Records & work → Farm. Display the active farm and review a replacement import as an explicit transition showing source, cutoff, counts, warnings, and state that will be replaced. Cancel leaves the current farm untouched.
- [ ] Support the synthetic seed and supported structured farm import through `POST /api/v1/imports`; import replay is idempotent and tenant scoped.
- [ ] **Path:** Imports → accounting/manual/document/photo. Accept supported CSV/XLSX accounting records, manual/correction rows, PDF/image extraction, and store the original private source. Preflight malformed or oversized documents before provider reservation.
- [ ] **Path:** Inbox candidate → Review. Show extracted/raw values, units, date, crop/category, provenance, warnings, correction target and signed delta; explicit accept/reject is required. Photos never authorize yields, inventory, tasks, or operations.
- [ ] Unsupported crops remain visible for accounting with a planning warning. Ambiguous dates/currencies, formulas, unknown schemas, non-finite values, invalid correction targets, and changed replay payloads fail closed.

Baseline: `packages/ingestion/financial.py`, `services/api/document_extraction.py`, `services/api/farm_workflow.py`, `FarmerWorkflow.tsx`. Evidence: `test_financial_ingestion.py`, `test_document_extraction.py`, `test_v12_upload_trial.py`, `test_v12_pdf_trial.py`, `test_farm_workflow.py`, `test_v12_acceptance_adversarial.py`.

### Orders, beds, inventory, work, results, and recovery

- [ ] **Path:** Records & work → Orders/Beds/Inventory. Inspect stable entities, dates, quantity/unit, booked versus tentative semantics, crop/batch/lot origin, expiry, and current reservation/occupancy. A market signal cannot silently become an order.
- [ ] **Path:** Approved plan → Work. Show generated sow/transplant/harvest/delivery tasks with biological dates, checklist, location, quantity/unit, and sandbox status. Historical stages are not regenerated as pending work.
- [ ] **Path:** Task → Record result → Review/submit. Validate current task status, complete checklist, quantity/unit and owned photo reference; append exactly one result event.
- [ ] **Path:** Completed task → Correct result. Require expected event revision, field, corrected value and reason; append a correction rather than rewriting history. Duplicate same-payload keys replay; changed payloads conflict.
- [ ] **Path:** Verify/recovery. Incorporate farmer-reported task events into the reported forecast, preserve completed work and lot identity, expose negative-cash/infeasible recovery honestly, and create a future-only replan.
- [ ] **Path:** Inventory → Waste Rescue. Review dated terminal lots and conservative mixed expiry, compare projected rescue outcome, then enter the ordinary proposal/recalculation path.

Baseline: `packages/workflow_contracts.py`, `services/api/farm_workflow.py`, `services/api/simulation.py`; evidence: `test_farm_workflow.py`, `test_v12_integration.py`, `test_v12_acceptance_adversarial.py`, `test_simulation_execution.py`, `test_v11_session_adversarial.py`.

## Knowledge & evidence

- [ ] **Path:** More → Knowledge & evidence → Crops. Reach all 20 V13 crop SVG assets and the implemented crop catalogue/profile records; show recipe/growth limits, evidence references, freshness and representative-art notice. Explicit stage mapping prevents unsupported/harvested states from appearing harvest-ready. Baseline: `apps/web/src/components/Visuals.tsx`, crop assets, `services/api/app.py` crop/evidence routes, `packages/growth.py`.
- [ ] **Path:** Sources/evidence. Inspect public source registry, observation time, retrieval time, units, coverage, freshness/stale/missing state, licence/export policy, and exact facts admitted to a calculation or answer. Baseline: `packages/ingestion/`, `services/api/provenance.py`, `services/api/explorer_public.py`; `test_ingestion.py`, `test_explorer_public.py`, `test_fixture_reproducibility.py`.
- [ ] **Path:** Any eligible entity → Explain. Use deterministic structured facts without inference and retain explanation references on the card/result/event.
- [ ] **Path:** Card → Ask specialist. Server validates the card/entity/snapshot focus; opening restores the complete saved transcript without inference. Explicit submit can create a bounded DeepSeek request with draft retained across 429/provider failure.
- [ ] **Path:** Conversation → Invite specialist / Council. Preserve reply graph, all seven functional roles, cited typed facts, validation status, partial/withheld/rejected findings, dissent, and planner conclusion. Proposed actions remain non-mutating until converted to a reviewed proposal.
- [ ] **Path:** Plan → Council review. Review the frozen result with role-appropriate evidence and exact strategy facts; budget/missing-source failures remain visible and numerical work stays usable.

Baseline: `services/api/conversations.py`, `conversation_store.py`, `planning_council.py`, `council.py`, `apps/web/src/components/AdvisorEvidence.tsx`. Evidence: `test_conversations.py`, `test_v12_discussion_proposal.py`, `test_v12_demand_grounding.py`, `test_v11_planning_council.py`, `test_research_advisor_trial.py`.

## Experiments

### Scenarios, quests, and simulations

- [ ] **Path:** More → Experiments → Scenarios/quests. List existing quests and create a frozen branch from an explicit root. Review bounded controls before running locally.
- [ ] **Path:** Scenario → Run/compare. Persist the branch, calculate changed forecasts, display infeasible learning results, highlight only changed controls/entities, and compare only compatible frozen roots.
- [ ] **Path:** Scenario → Continue. Continue without replacing the accepted main worklist; retry/cancel/restart are idempotent and recoverable. Conversation-proposed experiments use the exact frozen conversation snapshot.
- [ ] **Path:** Simulations. Create from an accepted sandbox plan, advance the durable clock, show finite recorded task/demand/inventory/cash/crop-stage consequences, and replan while preserving executed tasks and harvest-lot identity.

Baseline: `services/api/scenarios.py`, `services/api/simulation.py`, `apps/web/src/components/SimulationPanel.tsx`; `test_scenarios.py`, `test_scenario_postgres.py`, `test_simulation_execution.py`, `test_v8_reliability_postgres.py`.

### Data Explorer and datasets

- [ ] **Path:** Experiments → Data Explorer. Inspect records/series with filtering, pagination, numeric sort, relationships, source metadata and accessible charts inside cards.
- [ ] **Path:** Dataset generation/forecast settings. Preview bounded EWMA/settings changes locally, review inputs and hashes, freeze an immutable tenant-owned snapshot, and reload it exactly.
- [ ] **Path:** Snapshot → Run strategy. Continue into a compatible numerical run; distinguish unrelated roots even when raw records match. Saved forecast replay never recomputes.
- [ ] **Path:** Export. Download private/public records only when registry reuse policy permits; neutralize spreadsheet formula injection.

Baseline: `services/api/data_explorer.py`, `explorer_public.py`, `apps/web/src/components/DataExplorer.tsx`, `ExplorerChart.tsx`; `test_data_explorer.py`, `test_explorer_postgres.py`, `test_explorer_review.py`, `test_explorer_numerics.py`, `tests/browser/data_explorer.mjs`.

### Council research

- [ ] **Path:** Experiments → Research/reviews. Create and configure the existing research session, run its local calculation, explicitly request bounded specialist review when eligible, challenge/revise through cards, and inspect the report.
- [ ] Current view remains bounded while complete append-only history is reachable. Cancel/retry/restart preserves original actions, partial/withheld findings, and makes no duplicate provider call.

Baseline: `services/api/council_research.py`, `apps/web/src/components/CouncilResearch.tsx`; `test_sessions.py`, `test_v8_history.py`, `test_v8_cancellation.py`, `test_independent_review.py`, `test_postgres.py`.

## History & preferences

- [ ] **Path:** More → History & preferences → Plans/discussions/simulations/events. List saved objects newest first with type, status, revision/snapshot/result identity, effective date and provenance.
- [ ] **Path:** History item → Replay. Render immutable recorded state and event sequence read-only with zero recalculation, mutation, or inference. A separate **New attempt** explicitly creates a new branch/session/version.
- [ ] Conversation replay retains full turns, citations, validation, focus and partial/withheld states. Planning replay retains evidence validation and frozen market/source context. Simulation replay retains recorded consequences.
- [ ] Preferences persist accessibility, reduced motion, and existing optional audio settings per edition/tenant as appropriate. Updated help explains card navigation, device-keyboard voice typing, fact labels, sandbox-only actions, recovery, and provider submission boundaries.

Baseline: replay routes in `services/api/app.py`, `planning_sessions.py`, `conversations.py`, `simulation.py`, `council_research.py`; `AudioControls.tsx`, `lib/audio.ts`; evidence: `test_conversations.py`, `test_v11_planning_sessions.py`, `test_simulation_execution.py`, `test_v8_history.py`, browser audio suites.

## Cross-cutting release gates

- [ ] Generated frontend contracts are current; frontend production build passes and CSS/JS bundle sizes are recorded (V13 baseline JS was 601.77 kB with an over-500 kB warning).
- [ ] Full Python regression passes against isolated PostgreSQL, plus focused concurrent create/apply/save/result tests. SQLite-only evidence is insufficient for release.
- [ ] Tenant isolation covers every restored read/write route. Idempotency, stale revisions, concurrent requests, append-only history, transaction rollback, and restart persistence pass.
- [ ] Global/IP/session limits, stricter write limits, anonymous-session admission, provider concurrency/hour/day budgets, and `Retry-After` behavior pass. Drafts survive admission/provider failures and uncertain writes reconcile before retry.
- [ ] Browse, Explain, compare, preview, replay, local calculation and local simulation produce zero provider requests. Provider requests use only the validated DeepSeek gateway after explicit submission; no fallback exists.
- [ ] Complete browser journeys at 360, 390, 430, and desktop widths cover keyboard, swipe, vertical scrolling, focus return, text zoom and reduced motion. Normal-motion recordings prove finite causal transitions from recorded events.
- [ ] Farm import transition, task reporting/correction, provider outage, 429, interrupted calculation, stale approval, inverse ineligibility and reload each have a recoverable end-to-end test.
- [ ] V15 publishes as a new immutable edition only after these checks pass; `/` and `/play` resolve solely to V15. Earlier sources/images and recoverable data remain private and unchanged, with no automatic cross-edition state merge. Shared abuse/provider counters survive cutover.

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

- [x] **More → Knowledge & evidence → crop/source cards:** `crop card exposes recipe and evidence boundary`, `source card exposes freshness and status`, and `knowledge browse remains provider-free` cover the recipe limitation, freshness/status labels and zero-provider browse boundary at 360 px.
- [x] **Knowledge → Saved discussions → replay → reviewed handoff:** the explicitly labelled recorded-transcript transport fixture proves `recorded adviser handoff preserves exact source IDs` and `linked draft is applied only by the explicit footer action`. It supplies an already-recorded `references_verified` adviser message; it never fabricates or invokes provider inference.
- [x] **Experiments → Research & reviews → calculation/proposal/challenge:** `research calculation records three strategies`, `research edit is previewed before apply`, `research apply creates a new frozen input version`, and `research challenge records corrected evidence status` exercise real service mutations.
- [x] **Research → Revision history:** `research append-only revision history is reachable in cards` and `research history endpoint declares zero inference` exercise `/api/v1/council-research/{id}/history` through the V15 card and verify its replay declaration.
- [x] **Research → Presentation/context/discussion:** `research presentation, context and scripted discussion actions persist` saves checkpoint presentation settings, selects a frozen canonical reference, submits one scripted message, and advances one queued turn.
- [x] **Research → Actual adviser outage:** the explicitly labelled provider-outage transport fixture proves `explicit provider outage is visible and never auto-retried` and `provider outage retains the saved question draft`; exactly one explicit POST is attempted and the fixture returns 503.
- [x] **Knowledge → contextual validated gateway:** `tests/browser/v15_knowledge.mjs` proves direct partial, invited withheld and conversational Council results, a six-turn retained transcript, exact canonical order focus, and the visible card's canonical adviser/session binding. Its post-commit outage assertions prove the same thread and idempotency identity are reused, accepted POSTs leave no resend state, and transcript refresh is read-only. Evidence is persisted at `reports/v15/knowledge-browser.json` (11 passing assertions, 2026-09-17).
- [x] **Research → remaining supported card actions:** `tests/browser/v15_research.mjs` proves queued-turn stop, reservation preview/discard, reviewed order edit into v2, current eligible simulation-only result choice, stale historical result disablement, history beyond 20 revisions, report documents/links, saved-study reopen, and actual-discussion identity across reload. It asserts the visible result card's session, input hash, recorded-simulation basis and server eligibility. Its accepted-POST fixture proves transcript refresh makes no duplicate provider submission; its controlled calculation fixture proves explicit `run → cancel_calculation → retry_calculation`. Evidence is persisted at `reports/v15/research-browser.json` (16 passing assertions, 2026-09-17).
- [x] **Experiments → Dataset/scenario:** `generated preview saves an immutable snapshot`, `saved dataset export returns CSV`, `scenario branch persisted separately`, and `scenario local run reaches a terminal result` use real APIs. `dataset/scenario workflow makes no provider request` covers the local-only boundary.
- [x] **Shared shell:** five `tool reachable:` assertions cover every top-level tools-index destination; `360px shell has no horizontal document overflow`, `mobile tool cards retain vertical scrolling`, and `no browser page errors` cover this suite's mobile baseline.

Actionable V15 browser gaps remain open:

- [ ] Research calculation interrupted-request recovery still needs a DOM assertion against an uncertain calculation action; controlled cancel/retry is covered.
- [ ] Research stale results are disabled in the DOM and current results are chosen through the real service, but a direct stale-version API rejection remains covered only by backend regression rather than this browser suite.
- [ ] The final broad `v15_tools.mjs` rerun was blocked before shell bootstrap by the unchanged anonymous-session admission limit (`429`, `Retry-After: 342`); `reports/v15/tools-browser.json` records that blocked attempt and must be replaced by a passing isolated-service run before release.
- [ ] Successful provider prose remains a transport-fixture validation rather than live inference. No acceptance suite invokes an actual provider.
- [ ] Automated completion remains no evidence of comprehension; representative-user usability is unverified.
