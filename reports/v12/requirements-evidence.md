# V12 requirement evidence map — pre-publication

Current release status is authoritative in acceptance-status.md and the active
manifest. This map records scope, including failures and limits; it does not assert
publication before the final public checks.

| Requirement | Implementation and inspected evidence | Remaining gate / limit |
|---|---|---|
| Guided observe/discuss/decide/approve/act/verify/replan, farm board, mission, tutorials | FarmerWorkflow.tsx; frontend-real.json and frontend-browser.json; workflow-private-7746b2f.json; council-v4-workflow-8dc760d.json | Final built UI and public routes |
| Seven versioned functional roles, evidence, tools, partial/withheld | planning_council.py; council-v4-workflow-8dc760d.json and independent council-v4-quality-review.md | Weather/Market have no source; numerical scope is bounded |
| Questions/challenges/alternatives and reviewed state changes | conversation contracts V7; discussion-proposal-8dc760d.json; state-changing-discussion-8dc760d.json; discussion proposal isolation tests | Causal prose remains explicitly unverified, see independent review |
| Synthetic default, isolated optional uploads, provenance, operations disabled | v12_upload_trial.py; upload-review-8dc760d.json; frontend-real.json | No real farm operation |
| FinancialDataConnector CSV/XLSX/accounting, manual/corrections, reviewed PDF/image | financial_ingestion.py; financial tests; upload-review-8dc760d.json; pdf-private.json; actual-vision-evidence.json | Native PDF and synthetic invoice tested; not all scanned documents |
| Confirm extraction, separate observations, photographs cannot authorize yield/action | Inbox candidate/review contracts and upload isolation tests; vision-quality-review.json | Synthetic photo abstention only, not field diagnosis validation |
| Confirmed coverage, surplus, expiry/rejection, contribution margin; tentative/market distinction | farm_workflow metrics; v12 integration/adversarial tests; complete live workflow | Numerical projections, not observed commercial results |
| Dated Waste Rescue and calculated comparison | farm_workflow.py and FarmerWorkflow.tsx; frontend-real.json; numerical workflow tests | Hypothetical scenario outcomes labelled projected |
| Explicit revision-bound approvals, idempotent actions | farm workflow and integration/adversarial tests; live workflow trial | No automatic physical execution |
| Full task fields, append-only reports/corrections, forecast/recovery, completed-work preservation | farm_workflow tests; adversarial PostgreSQL restart test; restart-replay-8dc760d.json | Final deployment restart comparison pending |
| Three captioned downloadable MP4s, playback, transcript, reduced motion | media-verification.json; browser reports; ui-media-completion-audit.md | Final image serves same artifacts |
| Evidenced rewards, projected/simulated/reported distinctions | frontend-real.json, workflow integration tests | Farmer reports remain independently unverified |
| Immutable history, active pair, numbering, V11 frozen state, 410 methods/admission | editions tests; retired-route-checks.json; retired-admission.json; v11 preservation records | Final public V11/V12 cutover pending |
| Inventory/snapshot/precise retirement, excluded controls, resource accounting | retirement.md, retirement-storage-before/after.json, recovery-snapshot.json, host metrics | No safe verified removable registry artifact inventory; no broad prune or bill claim |
| Rolling candidate failure/atomic activation/restartable cleanup | publication/retention/operator tests; fresh actual Machine readback gate | Final publication exercises new readback; concurrent external operator serialization not claimed |
| Numerical feasibility, biology, identity, reconciliation, tenant/revision/idempotency | full regression; gameplay/data focused tests; original failure reports retained | Final full rerun in progress |
| Tentative/reservations/rejections/seedling shortfalls/stale/duplicate/corrections | v12 integration and adversarial tests; upload and workflow trials | Covered through combined scoped tests, not one giant browser script |
| Council invalid/missing/cancel/replay, bounded real DeepSeek | Council and worker tests; actual V4/vision/PDF/discussion evidence; shared ledger32/48 | No provider fallback; qualitative limitations preserved |
| Mobile360/390/430/desktop, keyboard, tutorials, exports | frontend reports and media verification | Final visible interpretation-boundary browser assertion pending |
| V11/V12 capacity, exact verified source/image publication and final resources | capacity-private-7746b2f.json; staging record; publication tools | Final exact-source capacity and post-publication evidence pending |

Live accounting connectors, public webhooks, full ERP, buyer outreach and actual
operational automation remain explicitly deferred by the user plan.
