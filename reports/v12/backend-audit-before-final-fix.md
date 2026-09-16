# V12 Farm Workflow backend final audit

Date: 2026-09-16. Source reviewed: `7746b2f`. Scope is the current Farm Workflow, financial ingestion, planning-session workflow hooks, conversation proposal boundary, and the stored Council quality review. This was a read-only source/test audit: no source edits, deployment, or provider calls.

## Release blockers

### B1 — Conversation proposed actions do not become reviewed workflow proposals

**Requirement:** “Conversation changes become reviewed proposals; Apply & Recalculate invokes local numerics.”

The conversation validator accepts and validates `reply.proposed_actions` (`services/api/conversations.py`, around `_validate_reply`), and its authority copy says state changes require a reviewed proposal. However, there is no backend relationship or endpoint that converts a selected conversation request/action into a `farm_workflow_proposals` record. The Farm Workflow proposal endpoint accepts caller-supplied `changes`, `session_id`, and optional import candidate IDs only; it accepts no `conversation_id`, `request_id`, action ID, conversation snapshot hash, or validated action provenance. Repository search finds no Farm Workflow integration in the conversation router. The current UI rendering of content/references therefore cannot close this backend gap.

**Impact:** a user can discuss a change, but the state-changing proposal is a separate manually authored request. The backend cannot prove that a reviewed proposal is the action the advisor proposed, cannot bind it to the frozen conversational evidence, and cannot reject a substituted change. This breaks the required discuss → decide provenance chain.

**Concrete fix needed:** add a tenant-scoped conversion/review boundary that takes an owned completed conversation request plus a specific validated proposed action (or a reviewed deterministic translation), binds conversation/request/snapshot/action hashes into the proposal, maps only supported controls into `planning_assumptions`, and still requires Apply & Recalculate. It must reject stale snapshots, absent/rejected actions, cross-tenant IDs, and changed idempotency payloads. Do not allow free-form model text to mutate assumptions.

### B2 — Correction endpoint can bypass task completion invariants and leave recovery state inconsistent

`record_task_result` correctly requires an actual quantity for completed harvests, accepted and rejected quantities for completed deliveries, complete checklists, matching units, and accepted+rejected delivery quantity within allocated lots. `correct_task_result` validates an edited field in isolation and does not revalidate the resulting task as a whole.

Concrete invalid states currently admitted include:

- a failed harvest with no actual quantity can be corrected only to `status=completed`;
- a failed/incomplete delivery can be corrected to `status=completed` without both accepted and rejected quantities or a complete checklist;
- lowering a completed harvest/sow/transplant actual below planned does not update task status to `recovery_required`;
- setting a delivery rejected quantity above zero can leave task status `completed` (provided the allocation bound is met).

The forecast refresh can independently set its aggregate `recovery_required` flag for a short actual, but the task payload/status and recovery metadata remain contradictory. Subsequent approval preserves any task with `event_revision>0`, so the contradiction is durable. Queue locking also treats every `completed` task as executed even if a correction created an invalid completed state.

**Impact:** corrected evidence can claim completion without the evidence required by the initial result path, and future replans can lock work based on that invalid status.

**Concrete fix needed:** after applying any correction, run the same whole-task invariant function used by result recording, derive status/recovery/forecast feedback consistently, and prohibit `completed` unless required quantities/checklist/unit constraints hold. A quantity/rejection correction should deterministically recompute recovery state. Add HTTP/PostgreSQL tests for failed→completed without quantity, delivery missing rejected quantity/checklist, short corrected quantities, and idempotent correction replay.

### B3 — Accounting “correction” reconciliation has no account/category target and can invert meaning

`FinancialDataConnector` sets `corrects_reference` to the correction row’s own `reference`; there is no separate correction target or corrected transaction kind. `reconcile_financial_rows` then interprets every positive correction amount as revenue and every negative amount as expense. That rule cannot represent ordinary corrections to an expense versus a sale. For example, an expense of SGD 100 plus a positive SGD 10 expense correction is reported as SGD 10 revenue and SGD 100 expense (net -90), rather than SGD 110 expense (net -110). Likewise, the schema cannot reliably bind the correction to the source row it corrects.

**Impact:** the advertised per-candidate revenue/expense/net reconciliation can be materially wrong while labeling its semantics `explicit_signed_delta`. Confirmation does not mutate the farm, which contains the damage, but the reviewed accounting summary itself is unreliable for corrections.

**Concrete fix needed:** require an explicit correction target reference and target category (or resolve the target uniquely within a frozen source ledger), then apply the signed delta to that category. Reject missing, ambiguous, duplicated, or category-mismatched targets. Preserve both source and correction rows and test expense increase/decrease, sale increase/decrease, unknown targets, and duplicate replay.

## Significant non-blocking truth/coverage gaps

### Unsupported crops are warned but the whole candidate becomes `planning_eligible`

The connector correctly preserves unknown crop IDs and emits `unsupported_crop:<id>` without fabricating a recipe. After confirmation, `review_import` marks every non-photo candidate `planning_eligible=true`, including candidates containing unsupported crop rows. Current proposal application accepts the candidate as provenance but the numerical change remains separately constrained to validated `planning_assumptions`, so this does not directly inject the unsupported crop into the planner. Still, the public eligibility flag overstates support. Prefer row-level accounting-only eligibility or candidate partial eligibility and prevent unsupported rows from being represented as numerical crop evidence.

### Two Council roles passed transport/reference validation without fulfilling their functional contract

The independent stored review `/tmp/v12-council-quality-review.md` found no numerical contradiction, but identified concrete semantic gaps:

- Crop Planner inferred a “useful crop mix” from total sown area only; cited area facts do not establish crop diversity or mix.
- Capacity & Cost Analyst cited service/shortfall facts only despite available labour and projected-cost facts, and did not substantively analyze capacity or cost.

These should be fixed in role-scoped claim admission/validation, not merely prompt wording: crop-mix claims must require crop composition/diversity evidence; Capacity & Cost must cite at least one admitted capacity or cost constraint/comparison for a validated finding. Otherwise mark the role partial/withheld rather than validated.

## Boundaries found correct

- Import parsing creates candidates only; explicit tenant-scoped review is required before planning eligibility. Photo observations remain observation-only with `yield_authority=false`.
- CSV/XLSX bounds cover byte/row/cell/column/archive expansion, reject formulas/macros, handle the 1900 and 1904 Excel epochs, reject ambiguous numeric dates, reject foreign currencies, and warn when accounting currency is undeclared.
- Uploaded source blobs are bounded, tenant scoped, fixed-ID addressed, served with safe media/disposition headers, absent from workflow state, and replayed by tenant/content/source-kind identity.
- Proposal creation/application/approval uses tenant scope, idempotency receipts with changed-input rejection, base/proposal revisions, the exact recalculation job/result ID, completed session status, input snapshot binding, and feasible selected strategy checks.
- Action IDs are stable by tenant/session/allocation/action (and order/date/crop for delivery). Approval preserves all event-bearing task history and cancels superseded unreported work. Historical sow/transplant/harvest stages before the planning date are omitted as new actions while biological dates remain attached.
- Initial task results enforce finite nonnegative values, quantity dimensions, delivery allocation bounds, optional owned reviewed photo references, and append events atomically before recalculating the labeled user-reported forecast.
- Reported forecasts preserve the approved result, identify source task event revisions, adjust harvested quantities, and separately expose accepted delivery, rejected delivery, revenue and contribution-margin deltas.
- Accounting duplicate references are excluded within a candidate and source row/count/unit totals are exposed. This does not cure B3’s correction-category ambiguity.
- Confirmation does not mutate the original farm. Confirmed historical sales are not silently converted into future booked orders; proposal changes remain explicit.
- Tenant isolation, stale revisions, changed idempotency payloads, source path traversal, rollback on event failure, restart persistence, delivery lot bounds, and replay are covered by focused HTTP/PostgreSQL tests.

## Verification

Focused command (isolated PostgreSQL test database):

```text
FARMTACT_DATABASE_URL='postgresql+psycopg://sprite@/farmtact_test?host=/tmp/farmtact-pg' \
  .venv/bin/pytest -q \
  tests/data/test_financial_ingestion.py \
  tests/gameplay/test_farm_workflow.py \
  tests/gameplay/test_v12_acceptance_adversarial.py \
  tests/gameplay/test_v12_integration.py \
  tests/data/test_v12_pdf_trial.py
```

Result: **23 passed, 2 deprecation warnings in 72.32 seconds**. The captured output is `/tmp/v12-backend-audit-pytest.txt`. The PDF helper tests exercise native text extraction and rejection of PDF-as-photo before any provider reservation. No real inference was called.
