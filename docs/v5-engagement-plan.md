# V5 engagement and hosting plan

Status: complete; immutable v5 is published and deployed checks are recorded. Updated 2026-09-09.

The published v5 edition turns Sumin Lee's decision-support proposal into
a clearer playable loop: find a delivery shortage, inspect its records, change an
assumption, calculate three strategies, compare the same policy and explain the
consequence using saved numerical evidence. Sumin's root PDF is the business
reference. The original hackathon briefing contributes only its page-13 rubric;
there are no stated weights and no claimed official scores.

## Packages and acceptance

| Package | Intended change | Acceptance evidence |
| --- | --- | --- |
| Decision journey | Clear problem, next action, adjustable assumptions and saved outcome comparison; distinguish a preview date, simulation step and real elapsed time | Complete shortage-to-evidence journey; biological lead times retained; reload and continuation |
| Crop recognition | Original SVG art informed by cited real-plant images, distinct silhouettes and growth forms for ten catalogue crops and four simulated crops | Morphology matrix; small-size/grayscale review; stage and accessible labels; no copied photography |
| Sound | Fix measured quiet playback, explicit test sound, comfortable optional channel controls and cues that distinguish calculation, shortage and failure | Signal measurements, real browser playback/lifecycle tests and honest limits on physical-device listening |
| News support | Bounded public-source collector with source, publication, retrieval and event dates; current and announced-future context for the council | Actual accessible source records, missing-source states, frozen evidence, injection/reuse/cutoff tests; no automatic conversion of reactions into demand |
| Hosting | Compare current Fly layout with a shared host preserving exact edition runtimes and all saved state | Official Singapore prices, actual inventory, memory/worker benchmarks, isolation and migration/rollback proof before cutover |

News is a supporting retrieval role, not an eighth voting council member. The
decision council remains Demand, Weather, Market, Production, Supply Chain,
Profit and Planner. No additional inference is permitted for browsing, filters,
previews, numerical experimentation or source refresh. Explicit advisor requests
use frozen evidence and the existing allowlisted DeepSeek gateway/budgets.

## Rubric mapping

| Page-13 category | Product or implementation evidence |
| --- | --- |
| Goal & Scope Definition | Buyer shortfall and feasible farm decision; concrete before/after numerical consequence |
| Architecture & Reasoning Loop | Six specialist findings plus constrained Planner; saved inputs, strategies and evidence |
| Tool Use & Integration | Typed numerical tools and bounded provenance-aware News retrieval |
| Autonomy & Human-in-the-Loop | Autonomous synthetic experiments; explicit paid advisor action; actual farm operations disabled |
| Safety, Security & Guardrails | Tenant/edition isolation, injection-resistant source data, reuse controls and spending limits |
| Observability & Evaluation | Reproducible result hashes, evidence links, traces and adversarial/complete-journey tests |
| Platform & Tooling Usage | Existing worker/council orchestration and independently reviewed deployment tooling |

## Ownership and sequence

Root owns contracts, dependencies, database changes, integration, deployment and
the Fly cost decision. Three bounded gpt-5.6-sol specialists conduct real Codex
reviews, not purported human user studies: `v5_game_review` owns the business and
browser baseline, `v5_audio_review` owns audibility/browser analysis and then a
separate read-only hosting assessment, and `v5_crop_review` owns crop research
and then source-viability research. No recursive delegation or overlapping app
edits. Implementation packages receive explicit ownership after these baselines.

Hosting assessment completed: retain the existing topology; safe net savings
from a shared host were not established (see the linked assessment). Resolve
source contracts next. Then implement the
decision, art and sound improvements and review them independently. Run backend,
security and browser checks serially where build artifacts conflict. Exercise
360, 390, 430 and 1280 pixel layouts, keyboard/touch, reduced motion, empty and
stale sources, infeasibility, interrupted jobs and saved-state isolation. Publish
only the next unused edition after checks; preserve every old source/image and
recorded run. Shut down Sprite public HTTP services after final verification.

Keep specifications and evidence current and push meaningful Git progress at
least every 20 minutes during active work. Baseline reports are findings, not
proof that their proposed fixes have shipped.


## Completed release

V5 is live at https://farmtact.fly.dev/v5/. Candidate acceptance passed 443 backend
tests and the full browser journeys. Deployed game 30, explorer 73, audio 22,
News 24, release chooser 6, snapshot race 3, decision semantics 6 and API smoke 17
checks pass. News live uses a documented latency-tolerant test harness. Earlier
concurrent navigation timeouts remain visible, and concurrent service capacity is
not certified by the later isolated passes. Source/image and captured owned state
for v1-v4 are preserved. Sprite public HTTP is shut down. See
[implementation and limitations](../reports/v5/implementation.md).
