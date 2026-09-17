# V15 private implementation status

Private branch: `feature/v15-integrated-cards`. V14 remains the public immutable
release. V15 has been privately staged but has not been published or accepted as a complete replacement. The first candidate failed mobile wrapping and slow-response UI acceptance; fixes are in progress.

The root entry now loads the integrated shell and lazy card decks for Plan,
Records & work, Knowledge & evidence, Experiments and History & preferences.
The ordinary sandbox replaces the separate four-bed teaching product. Server
onboarding progress has its own revision; it never changes planning revisions.

Domain additions are versioned guidance, read-only frozen planning-result replay,
structured deterministic proposal explanations and semantic scene transitions.
Proposal comparisons retain the explicitly selected source policy after result
IDs change. Existing mutation validation and cumulative admission remain in place.
The browser client retains uncertain mutation identity, including body-key APIs,
and honors Retry-After without automatic paid retries.

## Evidence so far

- Generated contracts check passed.
- Frontend TypeScript/production build passed; main JS approximately 231.81 kB
  (72.74 kB gzip), main CSS 132.3 kB (27.8 kB gzip). Tool decks load separately.
- Focused guidance, inverse and workflow suite: 19 passed (SQLite unit checks).
- Records real browser journey: 13 passed on isolated PostgreSQL, including real
  candidate confirmation/correction and labelled transport fault simulation for
  post-commit 503/idempotency and 429/Retry-After.
- Initial full isolated PostgreSQL regression: 776 passed, 3 failed, 2 errors,
  1 skipped. Gateway fixtures duplicated V14 registry entries; fixed and all 16
  gateway checks pass. Static-asset setup raced a concurrent build; focused
  simulation/conversation rerun passed 19 checks. Final full rerun passed: **790 passed, 1 skipped, 3 warnings in 820.83 seconds**;
  see `regression-final.xml`. PostgreSQL was isolated in `farmtact_v15_regression`.
- Plan/History real browser: 26 checks passed, including reviewed import/new attempt.
- Tools real browser passes dataset save/export, scenario execution, research
  calculate/preview/apply/challenge, mobile overflow and provider-free browsing.
- PostgreSQL guidance concurrent receipt/stale revision/restart test passes.
- Atomic reviewed farm transition added: save farm and create workflow in one
  tenant transaction. Four focused transition/guidance checks pass, including
  replay, stale review, session-cap rejection and rollback after interrupted save.
- Records one-card refinement and extended Knowledge replay tests have browser evidence;
  earlier passing browser evidence does not certify these latest revisions.
- Expanded tools suite passed real presentation/context/scripted discussion and
  history flows, plus labelled recorded-adviser and provider-503 UI fixtures.
- Explorer browser suite: 13 passed, including Enter on a read-only tool
  causing no underlying mission mutation. Filtered JSON export retains crop/date filters
  and numeric descending sort; back restores filters, relationships are inspectable,
  360/390/430/1280 widths and 200% text size fit, and reads cause no mutations.
- A second local card-test database exhausted anonymous-session admission after
  repeated development runs (429 `new_session_ip`, Retry-After 1563 seconds).
  Its counters were retained. The final card suite uses a separate disposable
  acceptance database and one browser tenant across viewport checks. No production
  counter was changed or limit raised.

Browser suites use separate disposable databases and retain unchanged production
rate limits. Earlier combined reruns exhausted the local anonymous-session quota;
no public counters were touched and no limit was raised. Runtime provider secrets
are removed from these local test services. No new provider-quality claim is made.

## Pending release gates

Complete the capability checklist and end-to-end evidence, resolve regression and
browser findings, inspect all responsive screenshots and causal motion recordings,
verify recoverable interruption/stale/concurrent paths, run final clean checks,
then stage and verify an immutable candidate before public cutover. Human usability
remains unverified. Actual farm operations remain disabled.

Latest verification command (provider credentials removed):

```sh
env -u DEEPSEEK_API_KEY -u MOONSHOT_API_KEY -u MINIMAX_API_KEY \
  FARMTACT_DATABASE_URL="postgresql+psycopg://sprite@/farmtact_v15_regression?host=/tmp/farmtact-pg" \
  .venv/bin/python -m pytest -q --junitxml=reports/v15/regression-final.xml
```

Additional browser evidence: real scenario continuation/compatible comparison/Waste
Rescue suite passed 8 checks; controlled scenario queued/cancel/retry/quest and
incompatible-root transport suite passed 6. These transport fixtures are explicitly
labelled and do not claim real numerical or provider results. The sole Python skip
is the optional generated News-cache contract because that cache is absent.

Additional recovery verification (17 September, 12:25 UTC): Knowledge's labelled
gateway fixtures pass 10 assertions, including retained uncertain-request identity
and read-only refresh after an accepted POST followed by a failed transcript GET.
Plan/History return navigation passes six real-browser assertions: original focus
and scroll are restored, including after asynchronous replay loading, with zero
POST requests. The shared return helper captures focus before disabling a pending
action. Recorded simulation playback has separate passing evidence in
`browser-cards-recorded.json`; a complete fresh reservation-to-approval run is still
being verified. Records extended verification exposed a session-filter mismatch in
rendered proposals/tasks/events; its corrected rendering is awaiting the full rerun.
These checks do not establish completed parity or authorize publication.

Further acceptance findings and fixes:

- A complete fresh reservation/apply/inverse/approval/simulation journey passed
  19 checks (`browser-cards-fresh.json`), with an actual mutation log and normal
  motion recording. Separate responsive and guide skip/resume checks passed 26
  assertions (`responsive-guide-contract.json`); they retain the ordinary farm.
- Queued calculations no longer block opening tools. The controlled planning
  cancellation suite passes five checks, including an interrupted cancellation
  retried with the same request key. This is transport recovery evidence, not
  an additional real numerical run.
- The extended Records workflow found that batchless delivery reports caused a
  crop-cycle exclusion sort to mix null and string IDs. Replanning now excludes
  only real crop-cycle IDs while retaining delivery reports in the forecast and
  execution hash. A real isolated PostgreSQL test proves recorded sowing and
  delivery, idempotent recalculation, retained allocation locks and unchanged
  task reports. The fresh full regression run after this fix passed **791 tests,
  one skipped, three warnings in 835.28 seconds**; `regression-final.xml` is the
  current authoritative full-suite artifact.
- Shared `BoundCard` metadata now carries canonical entities, nullable frozen
  bindings, provenance, affected entities and action authority across all decks.
  Local UI guards are distinguished from server-returned eligibility. Adapter
  checks are still verifying frozen proposal/task/result identities; a current
  planning result must not replace an older object's own saved binding.
- Release notes have been prepared and schema-validated. They are candidate
  notes only; no staging or public cutover has occurred.

Private integration checkpoint (17 September, 13:05 UTC): the combined production
build passes with the final Knowledge snapshot parser and unified Back/submit
footer. The parser retains the complete frozen snapshot identity, decodes its
planning session/result IDs, and does not confuse farm-schema version with
planning revision. A new real-API operator acceptance script passes 20 checks
locally (`acceptance-local.json`), including ordinary-farm guidance, reservation,
inverse, approval, simulation, reported delivery/correction and read-only replay.
It made zero provider submissions. This is local evidence only; staging and
publication remain pending. Final focused browser reruns are in progress and
any failing report remains a release gate until resolved.

Final parity audit follow-up (17 September, 13:18 UTC): Records' narrow real-service
journey passes 12 checks, including XLSX review/rejection, completed task reporting,
non-default note correction, reported forecast and event replay. Final Knowledge,
Research and broad tools runs pass 12, 18 and 30 checks. Planning now displays
confirmed totals, separate tentative demand and the planning horizon, and offers
a reviewed demand-edit path. History sorts saved objects and shows their status,
date and provenance; saved-plan replay offers a reviewed new attempt from the
current imported farm. Seven additional real-service Plan/History checks pass.

The audit also found missing conversation-to-experiment branching and unclear
dataset policy semantics; those are being tested against existing supported APIs.
The scenario API always calculates all policies, so the UI now says that explicitly.
Card-binding verification found form eligibility metadata out of step with disabled
buttons; final checks are verifying the correction. A resumed shell also needs to
distinguish general proposals from reservation-specific drafts. These remain
acceptance work, not waived limitations. No V15 staging or publication has occurred.

Private checkpoint (17 September, 13:33 UTC): the concurrent HTTP/PostgreSQL
proposal test passes, covering create/apply/inverse/approval exactly-once behavior
with four simultaneous retries per action. The full suite is rerunning with this
additional case. Proposal routing passes six checks: mixed drafts never hijack tool
navigation and a saved reservation remains recognized from its frozen inverse
assumptions. Bound card metadata passes 46 checks. Knowledge passes 27 checks,
including all 12 profiles, all 20 crop SVG assets, source fields and an explicitly
labelled planning-Council budget failure. Strategy inspection passes 12 checks;
all engine metrics and dated bed allocations are visible for each policy, while
the infeasible display case is a labelled transport fixture.

The latest retained-assets build succeeds (main JS 232.72 kB / 72.99 kB gzip;
main CSS 132.35 kB / 27.81 kB gzip). Final source/approval/import/context-return
checks and exact dataset reload verification remain in progress. A final clean
build and private staging still precede public cutover.

Private integration checkpoint (17 September, 13:50 UTC): the final isolated
PostgreSQL regression is **792 passed, one skipped, four warnings in 857.27 seconds**.
No backend product changes followed this run. Generated web contracts pass their
check. Real-service Plan/History checks pass seven assertions after the native
resource and demand editor replaced default raw JSON; seven focus/scroll-return
checks also pass. JSON import remains an optional disclosure. Responsive coverage
passes 101 cross-deck assertions plus 25 checks of the final native Plan editor
at 360, 390, 430 and 1280 px. Native field combinations and the final clean build
are still being verified. Recorded future-only replanning preserves executed work;
its nine-check browser report and the twelve-check history replay report pass.

The current motion recording was inspected at seven timestamps, including settled
recorded quantities after finite consequences. This is automated/visual inspection,
not a representative-user study. V14 is still public; V15 remains unpublished.

Private verification checkpoint (17 September, 14:02 UTC): the final native form
suite passes 36 checks after fixing inherited Add → Amend values. A separate
eight-check real-service journey verifies the uncalculated strategy placeholder,
valid selection after calculation and preservation of an explicit choice on
refresh. Cross-width keyboard/swipe/zoom/reduced-motion checks pass 25 assertions.
The complete 360 px reservation episode passes 20 checks; a 430 px run timed out
waiting for the initial calculation and is being diagnosed, so the complete
cross-width release gate remains open.

A new SSH-only browser transport pins the staged source, checks runtime health,
loads exact image assets with SHA-256 hashes and forwards requests to fixed
loopback port 8095. It exposes no listening endpoint and keeps gateway credentials
remote; its staged acceptance awaits deployment. Shared-control and retained-data
preservation tooling was live-validated read-only and passes five focused tests.
A private before-staging capture now exists. No V15 Fly mutation has occurred.

Local release gate (17 September, 14:06 UTC): complete 360/430/1280 journeys
pass 20 checks each, supplementing 390 px normal/reduced-motion and recorded-event
evidence. The 430 px timeout was a harness readiness race; the session was still
DRAFT and no calculation request had been sent. Session binding and exact guidance
POST/GET reconciliation replace fixed timing assumptions. The clean production
build passes, with 405,241 bytes total JS across main/lazy chunks and 147,347 bytes
CSS; main JS is 232.72 kB / 72.99 kB gzip. Generated contracts pass. The final
responsive native Plan rerun passes 25 checks on that clean build. One initial
read-only rerun used cookies from a different isolated local database and was
corrected to its actual 4196 service; no quota or server state was reset.

`local-acceptance-gate.json` records the current local evidence, including the
792-pass PostgreSQL regression and five additional preservation-tool tests.
Staging and publication are still pending; the next step pins this committed
candidate for private Fly numerical and browser acceptance before public cutover.

Staged acceptance follow-up (17 September, 14:20 UTC): source `a3ba834` was
privately staged with public V14 routing unchanged. Shared preservation passed
nine checks and the real operator numerical trial passed 20 checks with zero
provider submissions. The browser/visual gate failed: a 32-character proposal ID
widened the 390 px review screenshot to 468 px, and a late terminal poll could
clear mutation-owned busy state and expose a result before its workflow facts.
The candidate is rejected for publication. CSS wrapping and session/workflow
reconciliation are being fixed; delayed-response regression and repeated full
width journeys must pass before building a new pinned candidate. No counter was
reset, no farm operation was enabled, and V14 remains the public application.
