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
- Frontend TypeScript/production build passed; main JS approximately 219 kB
  (69.5 kB gzip), main CSS 131.2 kB (27.5 kB gzip). Tool decks load separately.
- Focused guidance, inverse and workflow suite: 19 passed (SQLite unit checks).
- Records real browser journey: 13 passed on isolated PostgreSQL, including real
  candidate confirmation/correction and labelled transport fault simulation for
  post-commit 503/idempotency and 429/Retry-After.
- Full isolated PostgreSQL regression and broader real browser acceptance are in
  progress. Failures are not release acceptance.

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
