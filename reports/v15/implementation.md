# V15 private implementation status

Private branch: `feature/v15-integrated-cards`. V14 remains the public immutable
release. V15 has not been staged, published or accepted as a complete replacement.

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
- Frontend TypeScript/production build passed; main JS approximately 223.6 kB
  (70.8 kB gzip), main CSS 132.3 kB (27.8 kB gzip). Tool decks load separately.
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
