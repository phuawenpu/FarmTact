# Original V12, V15 and V19 comparative walkthrough

Captured 18 September 2026 from private original-source copies: V12 `9fd57898`,
V15 `a5ab2a8` and V19 `ef4cba0`. These artifacts support the
[UX comparison](../../docs/v12-restoration-ux-review.md). APIs used isolated local
databases. Provider routes were blocked and credentials removed. Historical app
sources were unchanged; local Vite routing adapters supplied API and asset paths.

## Curated evidence

| Version | Observations | Complete local workflow | Normal motion |
| --- | --- | --- | --- |
| V12 | [Board/metrics and modal checks](v12-specific.json), [section/rail observations](walkthrough.json) | Restoration lifecycle tested separately; this set records original UI behavior | No V12 recording in this comparison |
| V15 | [Numerical result and strategy text](v15-calculation.json) | [26 mutation checks](v15-mutation.json), [7 recovery checks](v15-recovery.json) | [43.72-second recording](v15-normal-motion.webm) |
| V19 | [Numerical result and strategy text](v19-calculation.json) | [26 mutation checks](v19-mutation.json), [7 recovery checks](v19-recovery.json) | [43.04-second recording](v19-normal-motion.webm) |

Mutation checks cover reviewed reservation, apply/recalculate, inverse, sandbox
approval, seven-day recorded advance, finite transitions and reduced-motion facts.
Recovery checks cover a failed task report, future-only replan, retained reported
work and exact focus/scroll return. They use the existing full-card browser journey
and recovery scenario, adapted only for private ports and temporary output paths.

## Selected visually inspected screenshots

- V12: [first visit, 390px](v12-initial-390.png), [desktop](v12-desktop.png),
  [crop catalogue, 390px](v12-crops-390.png).
- V15: [first visit, 390px](v15-initial-390.png),
  [crop knowledge, 390px](v15-knowledge-390.png).
- V19: [desktop](v19-desktop.png), [knowledge index, 390px](v19-knowledge-390.png),
  [calculated strategy, 390px](v19-strategy-390.png).

The V12 crop screenshot was recaptured after fixing the private asset-prefix
adapter; all twelve original images loaded. Before/after video frames were
inspected using Chromium video seeking, with no video modification. The normal
recordings include real waits and end with reduced-motion verification.

Package size is approximately 9.03 MiB. Only selected screenshots and one mutation
recording per later edition are retained; interim images and recovery videos are
omitted. JSON reports retain their assertions and identify the curated paths.
No browser cookies, storage state or full planning-session snapshots are included.
All farm identities and task references are synthetic local test data.

These observations establish bounded behavior and interface differences. They do
not establish representative-user comprehension or validate agricultural outcomes.
