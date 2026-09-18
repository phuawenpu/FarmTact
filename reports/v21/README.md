# V21: V12 restored, then improved

Published 18 September 2026 at https://farmtact.fly.dev/ and `/play`.
V20 restored the V12 workspace before V21 made targeted changes. Plan, Farm,
Council research, Farm tools, Crops, Data, Outcomes and Setup remain named
sections. The farm board, seven advisers and direct planning controls remain.

V21 improves stage navigation without inventing completion, moves Calculate
before the board, aligns comparison metrics and board previews, and exposes full
dated allocation schedules. Dialogs support keyboard focus, Escape and return to
the opener; unsent edits survive closing within the mounted workspace. Crop
profiles cannot reopen from late evidence responses. Failed calculations retain
saved inputs and show an explicit retry action. Polling permits one pending read
per job and never automatically resubmits a mutation.

Private verification exposed a numerical worker cleanup defect under host load.
The narrow correction preserves the original failure and guarantees admission
cleanup, while still preventing overlapping numerical children. Models, deadlines,
rate limits and provider budgets were not expanded.

## Immutable release

- Source: `b980180dbb49a5261e43ee1d8e4916cc24457d7f`.
- Image: `registry.fly.io/farmtact@sha256:e3564a72292fe9a7fca69dcf9a25c3ffd9b9adaa5e38536c4a2d64d0b4a17e20`.
- Publication commit: `2825f24`; source tag: `farmtact-v21`.
- [Comparative V12/V15/V19 walkthrough](../../docs/v12-restoration-ux-review.md).
- [Implementation scope](../../docs/v21-v12-ux.md).

## Verification

| Check | Result | Evidence |
| --- | --- | --- |
| Complete isolated PostgreSQL regression | 811 passed, one skipped | [regression](regression.json) |
| Exact-image responsive UX | 62 passed; 360, 390, 430 and 1280px; keyboard, reduced motion, 150% text | [UX](staged-ux.json) |
| Exact-image complete lifecycle | 50 passed; reviewed import, recalculate, approve, report, correction and recovery | [lifecycle](staged-lifecycle.json) |
| Exact-image operator trial | 20 passed; inverse, idempotency, approval and read-only replay | [operator](staged-operator.json) |
| Exact-image delayed/failed status UI fixtures | 11 passed | [polling](staged-polling.json) |
| Local draft UI fixtures | 25 passed | [drafts](local-drafts.json) |
| Postpublication preservation | Nine passed | [preservation](preservation-published.json) |
| Public root and play | Correct V12 experience, V21 identity and exact source; no browser errors | [entry](public-entry.json) |
| Frontend build and generated contracts | Passed | [summary](verification.json) |

Regression source `6b85b164058a2df640dd7962dfb4ffb8fcfed5d4` includes the final
backend correction. Subsequent changes were frontend polling, browser transport
and documentation. Final staged checks bind to the published image above.
All verification submitted zero provider requests. UI fixture successes do not
claim real provider acceptance or induce backend failure.

[Normal-motion lifecycle recording](staged-lifecycle.webm) runs 118.84 seconds.
Inspected frames show proposal submission and durable correction/recovery facts;
there is no claim of physical farm growth or actual field execution. Frame
samples: [workflow](staged-lifecycle-frame-0.2.png),
[proposal](staged-lifecycle-frame-0.5.png),
[recovery](staged-lifecycle-frame-0.75.png).

JS is 526.54kB raw / 153.87kB gzip; CSS 148.45kB / 30.57kB gzip. The existing
large-chunk warning remains. Drafts are memory-only and clear on workspace
unmount/reload, as disclosed. Human usability and sustained-load capacity remain
unverified; automated completion does not establish comprehension. Actual farm
operations remain disabled.

Earlier `local-*` and `initial-staged-*` reports retain the investigation history,
including the selector failure, numerical timeout and subsequent fixes. They are
not the final release result. Historical source, image and recoverable data remain
private; no automatic historical farm-state merge occurred. Shared abuse counters
and provider budgets survived cutover.
