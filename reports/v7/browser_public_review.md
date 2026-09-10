# V7 public playable-council browser review

The immutable public v7 candidate passed the complete council study at
`https://farmtact.fly.dev/v7/research` on 10 September 2026.

- **111 checks passed**, with zero failures or browser errors.
- Fifteen public screenshots cover 360, 390, 430, and 1280 CSS pixels.
- Thirty-eight writes remained more than one second apart.
- The initial result took 22.674 seconds including the intentional seven-second
  stale-poll replay; the revised calculation took 15.718 seconds.
- The deliberately paced full research journey took 72.169 seconds. This is an
  automation measurement, not evidence that a first-time person can choose a
  plan within 30 seconds.
- The main farm remained unchanged, reload resumed the selected research
  version, and no real provider-capable request was submitted.
- Two provider-shaped requests were intercepted locally in the page and served
  a clearly labelled unsupported-response fixture. That check establishes the
  public UI warning behavior only. Actual provider calls: **0**.

The public run used one ordinary authenticated HTTPS test workspace created by
the published bootstrap flow. It did not use the local Store-provisioned test
tenant described by the local report. Exact assertions, timings, request paths,
limitations, and prior harness corrections are recorded in
`reports/v7/browser_public.json`; captures are under
`apps/web/screenshots/v7-council-public/`.
