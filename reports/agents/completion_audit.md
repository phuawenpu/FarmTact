# Interactive-world completion audit

Reviewed 2026-09-08. Scope: the current FarmTact tree and recorded evidence for the 16-plot interactive world, six persistent advisors, four numerical quests, isolated scenario comparisons, crop artwork, additive persistence, DeepSeek limits, and Fly state preservation. This was a read-only implementation audit except for this report. No inference, service, deployment, or application mutation was triggered.

## Resolution verification

Five material findings were identified during the audit and corrected before release verification. The descriptions below retain the failure mode and the reviewed resolution.

### CA-01 — Resolved: empty plots created an invalid batch target and blocked non-harvest quests

`sandboxControls` and `questControls` derive `batch_id` from every selected bed (`apps/web/src/components/GamePanels.tsx:353-362`). For empty fixture beds 09–16 this fabricates identifiers such as `batch-09`; only batches 01–08 exist. The batch selector renders only occupied beds, but its controlled state can retain the nonexistent value. `apply_controls` rejects any supplied unknown batch before considering whether delay or yield changed (`services/api/scenarios.py:74-80`). Consequently, selecting an empty plot and then running Busy market, Short-handed week, Tight budget, or a resource-only sandbox experiment can return HTTP 422 even though that experiment does not use a harvest control.

`scenarioTargetBed` now uses the selected bed only when it has a real `batch_id`, otherwise choosing the first actual occupied batch. The batch selector uses those same real IDs. The world browser journey now opens empty bed C1 through the accessible list, starts Busy market, verifies the fallback is not fabricated `batch-09`, and requires the completed persisted branch to contain one of the selector's real batch IDs.

### CA-02 — Resolved: the conversation client did not use the event stream

The backend persists conversation events and exposes cursor-resumable SSE at `/api/v1/conversations/{id}/events` (`services/api/conversations.py:772-811`). The web client defines no conversation event URL and `ConversationPanel` polls the full conversation every 900 ms for up to 330 attempts (`apps/web/src/components/GamePanels.tsx:78,107-115`). The browser fixture accepts an `events` request but does not require that one occurs; source search finds `EventSource` only for planning-run events in `App.tsx`.

`ConversationPanel` now opens that SSE route for an active request, refreshes on stored events, closes on a terminal status or context change, and retains a five-second GET fallback that cannot initiate inference. Generation guards prevent an old stream from overwriting a newly selected advisor. The final browser fixture explicitly requires an SSE GET for both a typed response and a reconnect; its recorded network trace contains seven event-stream requests.

### CA-03 — Resolved: invitations ceased to be exchanges with the referenced advisor

The invite route validates that `reply_to` is an advisor message but rejects only `body.advisor == conversation.advisor_id`, then schedules roles `[invited advisor, conversation's initial advisor]` (`services/api/conversations.py:730-753`). After a council or earlier invitation, a user can therefore invite the advisor who authored the selected point, and the return turn always comes from the initial advisor rather than the referenced speaker. The focused test covers only the special case where the referenced speaker is the initial advisor (Mei) and the invitee is Ravi.

The route now resolves the referenced message's supported advisor author, rejects inviting that same author, and schedules `[invitee role, referenced-author role]`. The focused test covers Mei→Ravi, then Mei invited to Ravi's point with Ravi returning, plus self-invitation rejection.

### CA-04 — Resolved: the UI could label an ordinary final reply as the critic's conclusion

The final council message receives `critic_conclusion=true` solely from its turn position and role (`services/api/conversations.py:1245-1246`). The typed `relationship` is not required to equal `conclusion`; the system prompt says it “should normally” do so. The backend council test returns `relationship="answer"` for every fake response yet asserts that the final message is a critic conclusion (`tests/gameplay/test_conversations.py:58-85,262-295`). The UI now replaces the displayed relationship with “Critic’s conclusion” whenever that positional flag is true.

`critic_conclusion` is now true only when the final independent-critic reply declares `relationship="conclusion"`. A different relationship is retained, visibly marked unsupported, and cannot receive the conclusion label. Positive and negative eight-turn tests cover both cases; the structural order remains fixed and bounded.

### CA-05 — Resolved: scenario “affected” entities were input-scope heuristics rather than computed effects

`affected_bed_ids` and `affected_deliveries` are selected from input crop IDs rather than differences between the baseline and scenario plan (`services/api/scenarios.py:191-199,113-114`). Labour or cash changes mark only beds containing current batches even when future allocations on empty beds change. Delay/yield changes label every order for the crop as affected even when an order's fulfilled quantity does not change. The UI presents these values as affected beds and deliveries.

Completed scenarios now replace the preliminary scope hints with `computed_impacts`: bed IDs come from per-policy allocation differences, including newly allocated empty beds, while delivery rows are explicitly limited to dates with changed aggregate demand/delivery totals or changed order inputs. Persistence and UI text state that this is not per-order fulfilment attribution. A focused regression requires a changed allocation on `bed-09`, excludes an unchanged delivery date, and preserves the scope label.

## Verified scope

- The fixture and farm view contain 16 real tenant-owned beds; the interactive world exposes six advisors, pan, wheel/button zoom, a date scrubber, an accessible list, 44 px targets, responsive layouts at 360/390/430/1280 px, and reduced-motion CSS. Recorded world checks report 42 passes, including an empty-bed quest completed with a real persisted batch target.
- Conversations freeze farm or completed-scenario snapshots, persist typed messages/reply graphs/events, prevent idle/replay inference, enforce one active request, retain partial output without automatic paid retry, and share the durable global daily DeepSeek reservation table. Direct, two-role invite, and eight-turn council call counts are bounded. Tenant, idempotency, interruption, provider isolation, and PostgreSQL persistence tests exist.
- Scenario controls enforce integer ranges for delay, yield, demand, labour, and cash. Branches deep-copy frozen inputs, keep the main farm/worklist unchanged, inherit the root baseline on continuation, compare the same Lean/Balanced/Resilient policy across a baseline plus up to three branches, persist numerical results without inference, and allow infeasible results to count after inspection. All four quest-specific control gates are covered.
- Ten crop IDs have distinct original SVG artwork. Caixin, pak choi, kailan, and lettuce each have seedling/growing/ready assets; the other six have mature almanac art. Hashes are distinct, the UI selects fixed local paths, and `docs/crop-art-provenance.md` records NParks/GardeningSG reference treatment and scientific limitations.
- Gameplay tables are additive to the existing metadata. Composite tenant foreign keys, tenant-scoped reads/writes, idempotent request keys, PostgreSQL concurrency tests, conservative interruption handling, and the shared inference budget are present.

## Release evidence closed by root verification

Root completed the final release gates: all 257 backend tests passed (248 non-PostgreSQL plus nine real PostgreSQL cases), final conversation fixtures passed 56 checks, and the final deployed live replay passed twelve checks. The fresh direct/invited/council trial completed eleven advisor replies in eleven DeepSeek calls, retained unsupported output visibly, and resumed/replayed without new calls. Final deployment retained the old farm/run, new branch and quest, all fourteen completed-discussion messages and all five earlier partial-discussion messages. Fly is healthy; the Sprite web service is stopped and its registration removed. The detailed evidence and remaining synthetic-model limitations are recorded in `reports/interactive_world.md`.
