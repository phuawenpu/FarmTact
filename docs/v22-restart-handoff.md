# V22 restart handoff

The V22 candidate is committed and pushed on `feature/v22-council-guidance` at
`57faeb96150f46635aac3198ecd3e75e270aba00`. The worktree was clean at this
handoff. V21 remains public.

Completed evidence:

- isolated PostgreSQL regression: 818 passed, one skipped;
- production web build and generated contracts;
- normal and reduced-motion guidance fixtures;
- Council, initialization and interrupted-proposal fixtures;
- real local lifecycle: 22 checks passed, including calculation, reviewed import,
  simulation-only approval, report/correction/recovery, room return, responsive
  widths and zero provider submissions.

See [the release report](../reports/v22/README.md) and
[the approved scope](v22-council-guidance.md).

## Resume order

1. Verify the process-scoped Fly credential without printing it:
   `sprite-auth-check fly && fly status --app farmtact`.
2. Capture the read-only preservation baseline with
   `.venv/bin/python scripts/v15_release_preservation.py --before /tmp/v22-preservation-before.json`.
3. Stage exact source commit `57faeb96150f46635aac3198ecd3e75e270aba00` as
   immutable `v22` using `scripts.stage_edition_candidate` and
   `/tmp/v22-notes.json`.
4. Run exact-image operator, browser, normal-motion and bounded Council smoke
   checks. Capture post-stage preservation evidence.
5. Publish only with `scripts.publish_edition`, then verify public root and
   `/play`, post-publication preservation and release registry/source identity.

The current blocker is external Fly authentication: `fly status --app farmtact`
returns an authentication error in this workspace despite both Fly environment
variables being present. Do not use a gateway connection, print tokens, reset
rate limits, use generic `fly deploy`, or publish a non-contiguous edition.
