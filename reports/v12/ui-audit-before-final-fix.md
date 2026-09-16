# V12 UI final requirements audit (read-only)

Scope reviewed: `docs/v12-implementation-plan.md`, current `FarmerWorkflow.tsx`/styles/client contracts, `reports/v12/frontend-real.json` (PASS 26) and `reports/v12/frontend-browser.json` (PASS 15). No provider calls or mutations were made.

## Release blockers

1. **Inbox confirmation is not an actual field review.** Candidate cards show source name, status, source kind, authority and only an extracted-row count. They do not render extracted rows, warnings, provenance, or document/photo observations before **Confirm reviewed fields**. The real test proves candidate→confirmed persistence, but does not prove that the farmer could inspect the fields being confirmed. This conflicts with “optional uploads are provenance-bearing candidates requiring confirmation” and the stated review-before-confirm workflow. CSV/XLSX/document/photo all share this gap.

2. **Manual entry bypasses the Inbox candidate/review contract.** **Open manual entry** navigates to the existing Setup room; it does not create a `manual` farm-workflow candidate and cannot be explicitly confirmed/rejected in the Inbox. This misses the requested optional manual-input path with explicit review.

## Functional scope present

- The seven-stage observe→discuss→decide→approve→act→verify→replan workflow, central seven-role Council, withheld/unavailable truth display, evidence/tool fields, explicit numerical approval, revision-bound tasks, reporting, recovery and correction persistence are present. Real evidence covers the durable apply→approve→report→recover→correct→reload path.
- Specialist questions freeze the planning snapshot and cannot mutate state. Constraint/order/capacity/tentative-demand edits create a separate proposal through **Apply & Recalculate**, preserving the required explicit handoff. The latest role-binding browser test is incorporated in the 26-check report and sends no provider request.
- Partial/withheld Council behavior is implemented in source (`partial`, `withheld`, blocked/failed handling). Mock evidence proves rejected→withheld; it does not independently exercise a role whose exact truth value is `partial`. This is a test-coverage gap, not a source blocker.
- Synthetic Singapore data is the default. Confirmed planning-eligible candidates are linked to proposals; tentative demand remains separate from booked commitments; photos are observation-only.
- Coverage, surplus, expiry, rejection, margin and Waste Rescue are distinctly presented. Projected, simulated and farmer-reported/unverified labels are visible; recovery and outcome badges derive from persisted evidence.
- The contextual tutorial is dismissible and its dismissal persists. Reduced-motion CSS suppresses animation; videos never autoplay and remain user-controlled. All three videos have captions, downloads and 12 caption-matched transcript scenes.
- Responsive evidence passes at 360/390/430/1280 with no body overflow or page exceptions.

## Documented limitations / non-blocking gaps

- Specialist responses render content, validation status and evidence references, but do not prefill the proposal editor or render structured `proposed_actions`. This is consistent with the rule that answers cannot mutate state; the farmer must close the dialog and enter the challenge explicitly. A direct “Edit assumptions from this challenge” handoff would improve clarity.
- There is one persistent contextual tutorial rather than stage-specific tutorial panels. Workflow labels, callouts and modal boundary text provide contextual guidance at later stages; treat plural stage tutorials as a product enhancement unless the acceptance interpretation requires multiple independently dismissible tips.
- Reduced-motion behavior is source-verified and Playwright runs with `reducedMotion: reduce`, but the report asserts layout/captions rather than a computed-style animation assertion.
- The no-inference real run intentionally leaves Council review unrequested; rejected/withheld Council rendering is covered by the mocked branch. Provider-backed Council quality remains outside this UI-only audit and must rely on the bounded gateway regression.
