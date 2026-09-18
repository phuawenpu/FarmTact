# V22: Council-led planning on the V12 workspace

V22 retains the restored V12 workspace and its named rooms while making the
Council the planning surface: specialist roles are short and explicit, the Chair
facilitates rather than replaces specialist decisions, and every discussion is
bound to the current reviewed result. The opening demonstration is a skippable,
captioned illustration of the ordinary farm workflow. It cannot create a farm
record, calculate, or submit an AI request.

The release is published and served from `/` and `/play`. The live machine reports
edition `v22`, source commit `ac6c84d09d515eac51802138baceabf84a3c01a8` (tag
`farmtact-v22`) and image digest
`registry.fly.io/farmtact@sha256:e05b00a575983dfc79d83a41563c3cfe762579475e57d885df414d6705ecdee1`,
which matches the `v22` entry in `config/releases/registry.json`. Earlier editions
are retired and return 410. The exact-image operator, preservation and public-entry
checks performed during publication were not recorded as repository evidence; only
the verification table below and the live identity above are recorded.

## Completed verification

| Check | Result | Scope |
| --- | --- | --- |
| Isolated PostgreSQL regression | 818 passed, 1 skipped | Full Python suite; provider credentials removed |
| Frontend build | Passed | TypeScript plus production bundle: JS 555.49 kB raw / 162.10 kB gzip; CSS 159.44 kB raw / 32.79 kB gzip |
| Generated web contracts | Passed | Current source contracts |
| Council workspace fixture | 11 passed | Revision-bound threads, explicit Send/Ask Council, drafts, 429 recovery; no provider endpoint |
| Interrupted proposal fixture | 10 passed | Exact receipt reconciliation without duplicate create/apply; no provider endpoint |
| First-load fixture | 10 passed | Strict Mode deduplication, dated objective, 360/390 px text-zoom visibility |
| Guidance fixture | 22 passed, normal motion; 22 passed, reduced motion | 360/390/430/1280 px, keyboard, captions, focus, no inference or mutations in the demo |
| Real local lifecycle | 22 passed | Calculation, reviewed import, approval, simulated tasks, result, correction, recovery, room return and 360/390/430/1280 px layouts; zero provider requests |

The existing bundle-size warning for the main JavaScript chunk remains measured;
it is not a claim that the bundle meets an unrecorded size budget. These isolated
browser fixtures prove the listed UI behavior only. The local lifecycle does
not substitute for the pending exact-image operator, preservation and public-entry checks.

Actual farm operations remain disabled. Numerical calculation is local; browsing,
previewing, the demo, and replay do not invoke the provider. Human usability is
still unverified until representative new users test the completed release.

See [implementation scope](../../docs/v22-council-guidance.md).
