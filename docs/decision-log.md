# Implementation decisions and evidence

2026-09-08 — Latest attachment is authoritative kickoff. Missing standalone CODEX_START_PROMPT/MASTER/brief/runtime artifacts were confirmed with git fetch and ls-tree. Attachment copied verbatim to CODEX_START_PROMPT.md; no unseen kickoff text is claimed. A01–A12 work packages reused from build Section 11; bounded ownership recorded in execution-plan.

The current phase is autonomous development. Numerical/backend policy accepts simulation plans automatically; public API users/council agents cannot call operational approval or change phase. Historical/source truth, licensing and provider checks remain gates.

Local configuration reports master gpt-6-astra/high; harness lists gpt-5.6-sol and accepted three actual specialist spawns. Official model page: https://developers.openai.com/api/docs/models/gpt-5.6-sol . Build-model configuration is separate from runtime DeepSeek routing.

Frontend uses TypeScript/React with Vite, served by FastAPI on one origin. The spec recommends Next.js but does not require it; this avoids a second public server and keeps keys behind backend. PostgreSQL 18 runs via Sprite service over a local Unix socket; SQLAlchemy models provide tenant-scoped versioned storage. SQLite exists only for isolated tests. Raw/normalized data remains outside served paths.

Planner uses OR-Tools CP-SAT with grams, cents, minutes and whole-bed allocations. Source: https://developers.google.com/optimization/cp/cp_solver . Every feasible candidate obeys stage lead times, all-day occupancy, nursery, worst-scenario harvest labour and cash reservation. An independent validator and FIFO mass-balance simulator check outputs. The fixed synthetic default has unavoidable early shortages; no seeded claim promises full coverage.

Policy differences are explicit: Lean/Balanced/Resilient shortage and surplus costs, and capital envelopes of 65%/85%/100% of fixture cash. Same forecast and joint three-scenario set are used for all. No weights are represented as empirical confidence probabilities. Yield is marketable mass, so packout/survival is not applied a second time.

Provider capability trials run early using the supplied environment credential; key values never enter source, reports, command arguments or browser. Official text/tool/vision documentation is checked by the gateway specialist. Failed trials are retained; technical corrections precede reruns. Account model listing alone cannot pass a content capability.

Independent A11 review reproduced six defects and verified fixes: active order/recipe dependency validation, Asia/Singapore civil planning dates, composite run/tenant event ownership, transactional replan version/job creation, cached snapshot closure, and positive budget reservations. Real PostgreSQL concurrency exposed an additional same-key replan retry race; idempotency is now rechecked inside the tenant lock.

The first image-to-council app attempt failed locally before gateway creation because a platform font path was absent. The fixture now uses Pillow's bundled font. Its unused nine-call reservation was reconciled with a persisted explanation; the 48-call daily cap was not raised. New runs log request reservations and release only proven unused reservations after completion. Prior uncertain/failed provider calls remain charged to the conservative counter.

The final integrated app run includes one actual synthetic-label vision call, six actual DeepSeek role calls, tool-referenced numeric validation, independent critic review, automatic simulation acceptance, stored replay and deterministic replanning after a synthetic disruption. Some sentences were rejected for uncited numerical assertions, as required; they are never numerical authority. A curated synthetic-only recording is available to fresh sessions with an explicit REPLAY mode so no paid inference is needed to inspect the demonstration.

A Python process socket policy permits only official DeepSeek HTTPS outbound connections from the inference service; ingestion runs separately. Negative socket probes and one authenticated official model-list request were exercised. This complements gateway checks but is not OS-level network isolation; future production infrastructure egress remains a separate release requirement.


## Final verification corrections

Explicit Pydantic JSON schemas were added to the standalone vision/council probes after locally rejected output shapes. The final aggregate passed at 15 requests / 7,232 output-token reservations without increasing its ceiling. Earlier failures remain in reports. The app's separate vision/council run preserved rejected unsupported claims rather than reporting every model assertion as valid.

Development input changes now invalidate old worklists and automatically start a numerical refresh; they do not require a sign-off or silently repeat paid inference. Replan idempotency includes the request body. Acceptance and farm imports serialize on the same tenant lock. Recorded public demo replay uses a fixed curated synthetic artifact and has no owned-run mutation privileges.

The service's Python egress hook allows only DeepSeek HTTPS and the configured PostgreSQL host/port (or local Unix socket); this is defense in depth, not an OS firewall claim. Docker is an optional unverified deployment definition; Sprite services are the tested runtime.


## Verified development delivery

Final full suite: 191 Python cases passed; real browser suite: 44/44, zero console/page errors. New standalone dependency environments and an isolated PostgreSQL database reproduced public ingestion (200 rows), feature build, frontend build and numerical import/acceptance/replay/replan without inference. Application source digest was compared to the final tree and matched. Supplied credential values were absent from repository candidates. Optional Docker startup and operational farm promotion are explicitly unverified/out of scope.

Screenshot inspection corrected an animation-timing capture and exposed a resource-label mismatch: total-horizon labour is now compared to horizon capacity, while summed new sowing area is distinguished from peak bed occupancy. Numerical downside metrics now take each metric's minimum across declared scenarios rather than assuming the low-yield scenario always has the lowest margin. Historical integration/replay quantities remain immutable.


## Fly deployment addendum — 2026-09-08

The primary development instance is now https://farmtact.fly.dev/ on the existing `farmtact` app in Singapore. The separate `Dockerfile.fly` is built and deployed, with PostgreSQL on an encrypted persistent volume. Fly health checks and 44 remote browser checks passed; saved farm/session data survived deployment, and logs confirmed graceful PostgreSQL shutdown and cluster reuse. Twelve targeted deployment/security tests passed.

Actual Fly vision and six DeepSeek roles completed, but an unsupported critic threshold caused claim validation to withhold acceptance; that composite report remains INCOMPLETE. Numerical mission acceptance and disruption replanning passed separately. Historical Sprite verification above retains its original scope and counts. See [Fly deployment evidence](../reports/fly_deployment.md) and the deployment runbook for current results and limitations.

### Interactive world: frozen numerical branches

Scenario controls change only a private frozen synthetic copy. Delay and yield target one existing batch; demand scales the selected simulated crop's synthetic orders and historical demand together, with cancelled quantities scaled consistently. Labour changes the weekly allowance throughout the current horizon; cash changes the horizon allowance. Controls on a continued branch are relative to that parent; comparisons retain the original frozen root baseline. Comparison rejects unrelated baselines. Numerical jobs are restartable and make no inference calls. A failed or infeasible plan never modifies main-farm acceptance; infeasibility remains a valid learning result. The six human characters are original role presentations, not new numerical models.

Conversation-backed experiments carry `source_conversation_id`; the scenario service resolves the tenant-owned frozen input itself. A later main-farm import cannot silently alter an earlier advisor proposal's baseline. Scenario conversations continue their original branch and preserve its root comparison baseline. Same-policy comparison deltas are calculated locally and exposed as referenceable tool values. Advisor validation checks references, numerical literals, supported controls and scope; it does not turn illustrative cultivar choices or synthetic recipes into scientific validation.

### Interactive world: explanation and learning acceptance

Advisor prose is qualitative interpretation. Digit-form quantities, common spelled quantities and date expressions are conservatively rejected; authoritative figures are rendered separately from immutable backend references with backend-derived labels and units. `references_verified` means reference membership and supported-control validation, not evidence entailment or agronomic correctness. Proposed actions are hypotheses that open editable frozen experiments. They never authorize farm operations.

Quest completion requires a changed assumption relevant to that quest and changed frozen inputs. A completed numerical experiment may earn a discovery badge even if infeasible or if output metrics do not change. Inspecting tradeoffs is a separate persisted learning action. Completed map highlights derive from computed allocation differences across policies, including future allocations on empty beds; draft previews use changed controls. Delivery highlights identify changed inputs or dates with changed aggregate totals, without claiming per-order fulfilment. Branch comparisons use the same Lean, Balanced or Resilient policy and display fill-rate changes in percentage points.

The release acceptance exercises real numerical browser journeys for every quest and branch continuation, plus separately labelled intercepted conversation and infeasibility fixtures for deterministic UI error/reconnect testing. A bounded live deployed conversation, invitation and council trial remains the provider acceptance check; it does not require a favourable recommendation.

The farm public view now includes authoritative `batch_id`, `transplant_date`, and Singapore civil `planning_date` for accurate preview/target selection. Existing NEA forecast-card selection incorrectly filtered forecast sources as observation IDs; this was corrected to D04/D05 so Hana and the Data room can use the actual recorded forecast summary and freshness metadata.

### Public hosting

The user clarified that the Sprite URL is acceptable only as the temporary development server. After the verified Fly rollout, stop and remove the Sprite web service registration so it cannot auto-start through its public HTTP URL. Preserve the workspace and development database. `https://farmtact.fly.dev` is the public application address. Sprites' HTTP proxy and Fly's application hostname are independent services, as confirmed in their official service/networking documentation.

### Live dialogue validation corrections

Live acceptance exposed oversized reply formatting and semantically invalid action combinations. The prompt now requests compact replies with explicit action units, ranges and targets, and schema-repair feedback includes only safe field/type diagnostics. Structural JSON errors retain the existing bounded repair allowance. Well-formed replies containing out-of-range or mistargeted actions are persisted visibly as unsupported, with actions blocked; they do not consume a repair or discard the rest of the dialogue. Global inference limits and backend scenario validation remain unchanged. Earlier failed and partial discussions remain recorded.

### Interactive-world release completed

Final verification passed 257 backend tests, 281 local browser checks, 87 deployed numerical checks and 12 deployed live-replay checks. A fresh live direct/invited/council exchange completed with eleven replies and eleven DeepSeek calls; its earlier partial attempt remains saved. A final redeployment preserved the old farm/run, new branch and quest, fourteen complete-discussion messages and five partial-discussion messages. The Sprite web service was stopped and its registration removed after Fly passed; its database/workspace remain. See [the complete release report](../reports/interactive_world.md).

### Public-demo abuse boundaries — 2026-09-08

Added persistent IP/session request limits, trusted Fly address handling, anonymous-session creation throttles, early authentication, strict origin/host checks, server-side expiry, bounded streams and upload deadlines. DeepSeek receives opaque tenant pseudonyms. Reservations crossing midnight reconcile against their original day. Final verification passed 300 backend tests, eleven live negative HTTP checks and twelve browser replay checks; probe accounting remained at 26 calls before/after, with no valid inference jobs submitted. The security deployment preserved existing data and kept Sprite web retired. See [security release evidence](../reports/security_hardening.md) and [the data/model inventory](data-and-models.md).


## 11 September 2026 — implementation documentation and game/Council audit

User requested a comprehensive scientific account of all ML/AI/provider calls and
the entire simulation/gamified backend, plus corrected README/docs/specifications.
Source audit separates precomputed numerical authority, optional DeepSeek
interpretation and scripted research interactions. Acceptance is a stored
projection/worklist; no farm-time/work-event execution engine exists. The report
records Council quality/versioning, queue/retry/history, crop-state, numerical
policy and evaluation gaps with acceptance criteria.

Documentation-only changes preserve v7 and earlier source/images/game state.
Three bounded specialist audits were integrated by root. Offline checks, archived
evidence, one cache-dependent fresh-test failure and rendered report validation
are separately recorded in [the audit](../reports/documentation/2026-09-11.md).
The next release remains the next unallocated immutable edition; no deployment or
paid inference was needed for this documentation task.

## 11 September 2026 — post-audit implementation and retained failed trials

The user subsequently authorized remediation and deployment. V8 added the
recorded synthetic execution engine, stronger numerical allocation/accounting,
point-in-time synthetic evaluation and bounded AI evidence contracts. V9 exposed
canonical fact meaning in all adviser views and improved role/context admission.
The original audit's statement that no execution engine exists is historical;
current mechanics are documented in the V8 remediation chapter.

Actual-provider tests exposed substantive errors after mechanical gates passed.
Retain each frozen edition and failed output. Do not equate reference membership,
completed transport, a synthetic regression or an automated topic-word score with
semantic truth or agronomic validity. V10's fulfillment and absence corrections
are bounded safeguards, not a proof of arbitrary interpretation. The scientific
follow-up records final deployment, call accounting, tests and remaining gaps.
