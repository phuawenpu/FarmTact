# V8 remediation and verification plan

Active user objective: rectify the comprehensive report gaps; improve data synthesis
and ML/numerical pipelines; test complete game journeys including meaningful actual
AI calls; update all documentation; publish a new immutable edition and push GitHub.
Baseline: `a21304e`. The inspected published registry ends at v7. No earlier edition
may be overwritten or share game progress with the new release.

## Ownership and integration

Root owns shared contracts, persistence migrations, simulation execution/canonical
state, worker and game reliability, interface integration, root dependencies,
requirements/evidence tracking, independent acceptance and publication.
Three real gpt-5.6-sol specialists work concurrently without recursive delegation:

| Package | Files | Acceptance |
| --- | --- | --- |
| `v8_council` | Council/conversation/gateway code, role config, related tests | Typed grounded output, prompt/schema versions, meaningful failure/support statuses, bounded call harness |
| `v8_planner` | Planner engine/research wrapper and numerical tests | Explicit scenario/objective semantics, FIFO reconciliation, terminal stock, order allocation and small enumerated cases |
| `v8_data_ml` | Fixtures/models/ingestion/features/evaluation and their tests | Preserved reference fixture, independent seeded synthetic cohorts, rolling-origin benchmarks, provenance and promotion gates |

Interface changes are additive or explicitly versioned. Root integrates shared
contracts; specialists coordinate forecast/ledger dependencies before consuming them.
Subsequent UI and independent review packages reuse these slots with new bounded
ownership. Meaningful progress is committed/pushed at least every twenty minutes.

## Deliverables and acceptance

1. A versioned simulation clock, idempotent sow/transplant/harvest/delivery/expiry
   events, conserved inventory and finances, and a usable game interface. Execution
   remains synthetic; physical farm integrations remain disabled.
2. Canonical crop state and horizon semantics shared by backend and display.
   Research challenges bind to input versions; action replay/history, job retry,
   cancellation, admission and numerical/provider worker isolation are verified.
3. A truthful, useful Council: explicit workflow and acceptance policy, structured
   evidence and code-rendered quantities, consistent schemas, replay provenance,
   support/transport distinction, capabilities with timestamps and no paid badge polls.
4. Improved synthetic data and numerical/model pipelines with reproducible independent
   cohorts, temporal tests, report schemas and data availability/provenance. Synthetic
   model results cannot be promoted as observed farm validation. Where a report gap
   needs real crop outcomes or human participants, implement collection/evaluation
   contracts and maintain the unvalidated gate; never invent observations or users.
5. Offline/unit/adversarial tests, dedicated PostgreSQL concurrency/recovery tests,
   full browser journeys at 360/390/430/1280px, and bounded actual provider tests that
   evaluate answer meaning, references, changes and no-call replay. All attempts count.
6. Current README/specs/docs and report artifacts, linked gap dispositions with actual
   evidence, immutable new edition publication, prior-edition preservation and public
   E2E verification, then clean synchronized GitHub state.

The gap register in `reports/v8/gap-status.json` starts with every AI/NUM/DATA/GAME/
OPS/UX item and is updated only with code and verification evidence. A successful
HTTP request, green fixture or plan alone does not close an answer-quality gap.
The final completion audit must cover the original full objective, not merely a
subset that happens to pass.

## Actual provider experiment policy

Use the existing server-only DeepSeek routes and shared 48-call daily ceiling.
Root coordinates an additional per-goal ledger including failed attempts/repairs;
initial reservation is at most 40 actual requests across local and deployed
acceptance. Increase only with explicit recorded technical justification while
remaining inside application admission. No specialist submits paid calls alone.
Numerical/browser checks use zero-call tripwires until the final real AI journeys.
No provider fallback, private farm uploads, speech integration or real operations.
