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
