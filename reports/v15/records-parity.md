# V15 Records & work capability evidence

Evidence was collected against the local PostgreSQL-backed application, with real API mutations unless a row explicitly says **controlled fixture**. The baseline browser run passed 16 checks on `http://127.0.0.1:4194`; the extended run passed 20 checks on the disposable `http://127.0.0.1:4196` service. API-created objects in the extended suite are declared prerequisites; all review, approval, result and recovery decisions named below use card UI actions.

| Requirement | Card path and transition | Evidence | Status |
|---|---|---|---|
| One active card and one action area | Records & work → Farm records → Manual record | `v15_records.mjs`: “records uses one shared action area”, “form decision controls render outside card body”, and “shared action area has at most three controls” | Covered |
| Persistent manual draft | Farm records → Manual record → reload → return to Manual record | `v15_records.mjs`: “manual draft survives reload” | Covered |
| Uncertain-write recovery and stable mutation identity | Manual record → Create review candidate; the response is replaced with 503 after the real mutation commits; reload and resubmit | `v15_records.mjs`: retained draft, retained record reference, identical Idempotency-Key, and exactly one candidate | Covered; labelled transport fault |
| Admission throttling | Manual record → Create review candidate with one controlled 429 and `Retry-After`, then retry | `v15_records.mjs`: immediate retry suppressed and later request reaches the real API | Covered; labelled transport fault |
| Manual accounting candidate and explicit review | Farm records → Manual record → candidate card → Review candidate → Confirm reviewed fields | `v15_records.mjs`: stable candidate card and confirmed state from `/api/v1/farm-workflow` | Covered |
| CSV accounting upload | Farm records → Add candidate → Upload accounting candidate | `v15_records_extended.mjs`: real CSV creates an `accounting_export` candidate with its parsed reference and amount | Covered |
| Original source inspection | Accounting candidate → Source → Inspect source | `v15_records_extended.mjs`: authenticated `/farm-workflow/imports/{candidate_id}/source` returns the uploaded reference and the UI opens the source view | Covered |
| Accounting confirmation | Accounting candidate → Review candidate → Confirm reviewed fields | `v15_records_extended.mjs`: real candidate becomes `confirmed` | Covered |
| XLSX parsing and validation | Farm records → Add candidate → Upload accounting candidate | `v15_records_gaps.mjs`: generated workbook reaches the real API, parses its dated expense/reference, and appears as an accounting candidate; backend tests cover date epochs and formula rejection | Covered |
| Photo/document provider boundary | Add candidate → select PDF/image → Submit for AI extraction | `v15_records_extended.mjs`: card states one bounded provider request; controlled 503 retains the selected PDF and invokes no provider | UI/outage covered; labelled fixture |
| Extracted fields remain non-authoritative | Document candidate → Inspect extracted fields | `v15_records_extended.mjs`: controlled response retains labelled fields and shows “Inactive until reviewed” | Covered with labelled fixture; no provider call |
| Photo constraints | Add candidate → select PNG → Submit for AI extraction | `v15_records_gaps.mjs`: labelled image 503 proves disclosure, one controlled request and retained file; backend tests validate media/dimensions | UI/outage covered; no provider call |
| Candidate rejection | XLSX candidate → Review candidate → Reject candidate | `v15_records_gaps.mjs`: real candidate becomes `rejected` and gains no planning authority | Covered |
| Full farm JSON import review | Records & work → Farm setup → Review farm JSON → Review parsed farm → Confirm atomic import | `v15_plan_history.mjs`: distinct parsed review, fresh remembered workflow session, old sessions retained, return to Farm setup | Covered |
| Synthetic demo transition | Farm setup → Review demo load → Confirm atomic demo load | `v15_records_extended.mjs`: real atomic transition followed by session-isolation checks | Covered |
| Atomic farm/session boundary | Import confirmation calls `/planning-sessions/import` with reviewed farm version and creates the new workflow as one operation | Plan/history and extended browser checks verify the remembered new session and retained old sessions | Covered |
| Orders, beds and inventory browse cards | Records & work → Confirmed orders / Growing spaces / Inventory → Open | `v15_records_gaps.mjs`: order identity/quantity/date and bed identity/area/system/crop are rendered; inventory renders facts or an explicit empty state | Covered; also caught and fixed missing bed-stage crash |
| Proposal identity and review | Proposal approvals → exact proposal card → Review approval | `v15_records_extended.mjs`: exact real prerequisite proposal ID is visible before action | Covered |
| Stale approval fails closed | Approval review → Approve revision & create tasks with controlled 409 | `v15_records_extended.mjs`: alert retains the review and the real workflow has zero tasks for that proposal | Covered; labelled 409 transport fixture, with server eligibility covered by backend tests |
| Explicit approval creates simulation tasks | Approval review → Approve revision & create tasks | `v15_records_extended.mjs`: real API state contains tasks bound to the exact proposal | Covered |
| Task result form stays bound under alternate navigation | Tasks & results → exact task → Record result → ArrowRight and swipe on form | `v15_records_extended.mjs`: task-specific heading and Result form remain active; no navigation mutation occurs | Covered |
| Failed result and recovery trigger | Result form → select Blocked or failed → checklist/note → Save reported result | `v15_records_extended.mjs`: exact task reaches `recovery_required` with a new event revision | Covered |
| Completed result | Tasks & results → exact task → Record result → Completed → Save reported result | `v15_records_gaps.mjs`: exact task becomes completed with quantity, checklist, note and event revision through UI | Covered |
| Auditable correction | Tasks & results → task with event revision → Correct record → Reason → Save auditable correction | `v15_records.mjs`: correction reaches the real API and returns an incremented event revision | Covered for default quantity field |
| Other correction fields | Correction card supports actual quantity, rejected quantity, unit, result note and result status using the public request names | `v15_records_gaps.mjs`: result-note correction is saved as a second auditable event revision | Note covered; each remaining field is not repeated in browser |
| Farmer-reported verification | Verify & recover card displays server-derived reported forecast, source result and recovery-required tasks | `v15_records_gaps.mjs`: farmer-reported outcome, source result and “not independently verified” boundary are visible after real task events | Covered |
| Future-only recovery | Recovery-required task → Replan future work → Resources & assumptions → Review → Create proposal → Apply & recalculate | `v15_records_extended.mjs`: real recalculation completes after failed task | Covered |
| Retained schedule comparison | Plan → Strategies & schedules → Compare retained schedule | `v15_records_extended.mjs`: saved “Changed allocations and metrics” comparison opens without recalculating | Covered |
| Executed work preservation | Return from future-only recovery and reread exact failed task | `v15_records_extended.mjs`: actual quantity, farmer note and event revision are byte-for-byte unchanged | Covered |
| Return context | Replan future work → Plan → Back | `v15_records_extended.mjs`: originating action regains focus and original scroll position after Records refresh | Covered |
| Per-session isolation | Atomic demo transition → Proposal approvals and Tasks & results | `v15_records_extended.mjs`: old proposal and task IDs are absent from the new session DOM | Covered |
| Workflow history | Records & work → Workflow history → exact task event | `v15_records_gaps.mjs`: task event is reachable by subject identity and marked “Saved replay only” | Covered |
| Canonical card bindings | Candidate/proposal/task/order/bed/inventory cards publish entity ID/kind, frozen session/revision/result references, provenance, targets, outcome basis and action eligibility | `BoundCard` adapter in `IntegratedRecords.tsx`; shared contract acceptance is recorded separately in `bound-card-contract.json` | Shared contract suite owns final verification |

## Evidence boundaries

- The extended suite never calls a real AI provider. Its document success and outage responses are clearly recorded in `controlled_fixtures`; they prove UI disclosure, retained fields and authority boundaries only.
- Proposal calculation is an API setup prerequisite in the extended suite. Approval, failed task reporting and recovery are performed through the UI.
- CSV and XLSX reach the real local parser. The image test deliberately intercepts one labelled outage before backend/provider access; provider extraction quality remains outside this acceptance.
- Result-note correction proves the non-numeric form and audit transition. Repeating every accepted correction field would duplicate the same transition and is not claimed.

## Primary artifacts

- `tests/browser/v15_records.mjs` and `reports/v15/records-browser.json`
- `tests/browser/v15_records_extended.mjs` and `reports/v15/records-extended-browser.json`
- `tests/browser/v15_records_gaps.mjs` and `reports/v15/records-gaps-browser.json`
- `tests/browser/v15_plan_history.mjs` and `reports/v15/plan-history-browser.json`
- `tests/data/test_financial_ingestion.py`
- `tests/data/test_document_extraction.py`
- `tests/security/test_upload_preflight.py`
