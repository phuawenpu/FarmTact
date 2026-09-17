# V16: completed integrated rewrite and explanation correction

The full rewrite is published at **https://farmtact.fly.dev/** and **/play**.
Both routes open the same ordinary-farm card experience. V16 is the immutable
correction to V15; it preserves all restored workflows and fixes the final
semantic-audit findings. There is no public edition chooser or older-interface
escape. V17 is the next unused edition.

- Application source: `3487faf90ec9205c903f8a6e40fc09aa94614dcc`.
- Image: `registry.fly.io/farmtact@sha256:e3bedff080dbdcebc2e6619210e91bce5faeeeef51388656f1c9e75743883493`.
- Publication commit: `b7a3eec`; branch: `feature/v16-explanation-completion`.
- Previous V15 source/image/data remain preserved; no historical farm state was
  automatically migrated. Cookie, audio and browser progress use the V16 namespace.

## What changed and why

V15 restored the full Plan, Records & work, Knowledge & evidence, Experiments and
History & preferences workflows. A postpublication audit then found that a saved
general proposal could expose raw assumption JSON and supply the same explanation
to unrelated mission cards. The goal was reopened rather than treating five headings
as sufficient. Its original failing evidence remains in
`../v15/final-semantics-published-failure.json`.

Each core stage now explains its own frozen facts: order and full-demand context;
compatible strategy comparisons and dated allocations; exact reservation before/after
records; current-result or previously saved tasks with owning proposal IDs; and
recorded simulation events and totals. Mixed proposals expose target dates without
attributing whole-plan differences to that reservation. Missing baseline, metrics,
allocations and event facts remain explicitly unknown. Explanation identity agrees
with card metadata. Reading and replay never request inference.

The numerical engine, API/domain services, validations, admission budgets and all
other restored workflows are unchanged. The original capability-by-capability
inventory and evidence remain in `docs/v15-capability-checklist.md`.

## Verification

| Gate | Result | Evidence |
| --- | --- | --- |
| Every core stage, bindings, missing/mixed facts, keyboard, SVGs | 49 passed | `final-semantics.json` |
| Independent API-checked explanation/layout/focus/zoom/reduced motion | 97 passed at 360/390/430/1280 | `explanation-layout.json` |
| Complete real reservation → inverse → approval → recorded result | 27 per width, 108 total | `browser-cards-widths.json` and four width reports |
| Exact hosted candidate operator workflow | 20 passed, zero provider submissions | `release/operator-acceptance.json` |
| Exact hosted image browser journey | 28 passed, zero transport failures/provider submissions | `release/staged-browser.json`, adjacent screenshots/video |
| Published root/play, tools and saved replay | 67 passed at all four widths, zero unsafe methods/provider calls | `release/public-browser.json` |
| Published route/session/dataset isolation | 13 passed | `release/public-isolation.json` |
| Shared counters, provider budgets, release history and retained data | Nine checks passed before and after cutover | `release/preservation-staged.json`, `release/preservation-public.json` |
| Exact running image and retired worker | Gateway and V16 only; accepted digest | `release/runtime-image.json` |
| Recovery/retention | Archive-only, V15 worker stopped, no storage deleted; created Fly snapshot | `release/retention.json` |
| Build/contracts/operator helpers | Clean build/contracts pass; 12 helper tests pass | `frontend-build.json`, `frontend-build.txt`, `operator-guards.txt` |
| Backend regression | 792 passed, one skipped; API/packages unchanged | `../v15/regression-final.xml`, unchanged tree recorded in `frontend-build.json` |

Main JS is 240.25 kB / 75.06 kB gzip; total main/lazy JS and CSS bytes are measured
in `frontend-build.json`. The one Python skip is the clean checkout's absent generated
News cache. This frontend follow-up does not claim a second full backend run.

`final-motion-review.json` and its frames inspect actual normal-motion recordings
at start/mid/end/settled times on 390px and desktop. Bed stages and finite emphasis
change once, then retain the recorded September 14 facts: harvested +190 kg,
delivered +136 kg and disposed +5 kg. Reduced motion retains identical facts.
The unchanged motion implementation also has 11 explicit lifecycle/DOM/viewport
checks in `../v15/final-accessibility.json`, including a labelled inert-layout
fixture that puts a real recorded event fully offscreen and proves finite settling
and no replay on return/reload. These are not physical screen-reader tests.

The first Fly machine update failed before changing the running configuration.
Read-only reconciliation confirmed V15 remained started/healthy on its original
image. Retrying the same pinned candidate succeeded; no new image, counter reset
or state replacement was used. Private staging passed before V16 publication.
Authenticated state and salted control-table captures remain outside Git.

## Scope and limits

The complete user-approved V15 scope is retained: one ordinary sandbox, skippable
resumable guidance, five integrated tools, reviewed imports and mutations,
server-owned eligibility, append-only corrections/history, local numerical planning,
explicit optional inference, and preserved shared admission limits. See
`completion-audit.md` for requirement-to-evidence mapping.

Human usability/comprehension remains unverified until tested with representative
new users. DOM and viewport emulation do not establish physical mobile keyboard or
screen-reader compatibility. No new live-provider prose quality or agricultural
calibration is claimed. Four numerical crop recipes and twelve knowledge profiles
retain their documented limitations. Actual farm operations remain disabled.
No autonomous inference, custom transcription, new agricultural model, rewards or
drag-and-drop system was added.
