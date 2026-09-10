# V7 playable council — implementation record

Status: complete; published and publicly verified, 10 September 2026 UTC.
Play https://farmtact.fly.dev/v7/research. Frozen source: `6efbbfd5a57cb557683e636d1fe20ae63b6b9eda`.
Pinned image: `registry.fly.io/farmtact@sha256:6e3145bb60f39a1c0a53c934f5057f837b413b631dc0a521003265697f2403bc`.

The council study extends the existing application with a guided synthetic task:
calculate a plan, reserve Bed 4 after its protected harvest/sanitation period, mark
the additional lettuce order unconfirmed, challenge the rainfall assumption,
compare one policy across frozen versions, and choose a feasible simulation.
Three optional presentation concepts share these same numerical inputs. The
default uses an expandable council in normal document flow; layout research is
secondary to the task. No research action changes the main farm or authorizes
operations.

## Evidence and interpretation

- [Primary-paper synthesis](../../docs/research/council-participation.md) separates
  the official page-13 rubric from Sumin's conversational product proposal.
- [Baseline audit](baseline_audit.md) records observed v6 desktop/mobile behavior.
- [Recommendations](recommendations.md) rank three improvements following
  independent browser review. These are agent walkthroughs, not human trials.
- [Persistence](persistence.md) and [independent backend review](research_backend_review.md)
  cover isolation, idempotency, interrupted jobs, constraints and clarification.
- [Actual advisor probe](advisor_local.json) used one DeepSeek request. The frozen
  context, replay and main-farm boundaries passed; the answer was flagged unsupported.
  This is not evidence of a correct farming recommendation. The experiment ledger
  counts attempts and repairs under a maximum of sixteen calls.

## Candidate verification

The final contracts/research group passes **33 tests**. The full regression ran
492 passing tests and exposed one generated AppView drift failure; the generator
was corrected and its contract check passes in the final focused group. Web
build, TypeScript and generated-contract checks pass.

Independent browser reviews pass **111 planning/UI checks** and **48 novice
checks** across 360, 390, 430 and 1280 pixels, all three layouts and reduced motion.
See [planning review](browser_review.md) and [novice review](novice_review.md).
The novice automated run reached initial calculated choices in 15.319 seconds;
its complete guided three-calculation task took 53.475 seconds. These are local
machine timings, not measurements from first-time human players.

Review found and repaired mobile control overlap, proposal scroll clearance,
pending draft preservation, study reload and stale response handling. Browser
checks use labelled authentication fixtures and an intercepted adviser fixture;
only the separately reported advisor probe calls the actual provider.

Reproduce with `.venv/bin/python -m pytest -q`,
`.venv/bin/python scripts/generate_web_contracts.py --check`, and
`npm run build --prefix apps/web`. PostgreSQL research tests require a dedicated
`farmtact_research_test` database on `/tmp/farmtact-pg`; never point job-recovery
tests at a running application database. Browser commands are recorded in their
reports. Public verification is recorded below.

## Limits

Default dialogue is explicitly scripted and recognizes a bounded set of intents;
it proposes typed edits rather than executing free text. Unsupported questions
receive clarification. Optional actual DeepSeek interpretation uses the existing
gateway and displays evidence validation separately. Numerical outputs use demo
biological recipes, EWMA and CP-SAT; they are not validated commercial farm outcomes.

Thirty seconds to a first planning choice is a proposed human-test target.
Automated latency, headless mobile geometry and agent opinions cannot establish
enjoyment, learning, physical touch comfort, software-keyboard behavior or accessibility
with an actual screen reader. Existing optional audio is preserved; this study
does not add or claim a new physical-device listening evaluation.

Publication reused the existing four-shared-vCPU/4-GB Machine and single volume.
Read-only hashes of recorded games in all six earlier editions were captured before
deployment. Prior editions must preserve their pinned source/images and captured
records. Temporary Sprite HTTP services were removed after verification.

## Publication

The registry/source tag was pushed in `4ef9ff3`. The first file-style publisher
invocation stopped on a Python module-path error after image reservation, before
any host update. Module invocation reused that exact source and image and
completed publication. The runbook now documents module invocation.

[Public route checks](routes_public.json) pass for all seven edition health/source
pins, the research route, its canonical redirect, the curated research report and
ordinary HTTPS bootstrap. [Public browser review](browser_public.json) passes **111 checks**, with zero
failures/runtime errors and fifteen screenshots. The complete guided task uses
real numerical results. Adviser response rendering uses labelled intercepted
fixtures and makes zero actual provider calls. The first public attempt passed
functional assertions but its log matcher expected the local text for an
intentional HTTP 409; a narrowly scoped harness correction passed the rerun.
Initial timing of 22.674 seconds includes a deliberate seven-second stale-poll
wait; the full deliberately paced task took 72.169 seconds. These are automation
measurements, not a first-time human study. The separate provider check is recorded below.

Post-publication operator correction: both module and file entrypoints now resolve
the shared-host helper from the repository root. An isolated subprocess regression
and the deployment/publisher suites pass **48 tests**; v7's immutable application
source/image remain unchanged.

[Preservation](preservation_public.json) verifies all **196 captured game rows**
across v1–v6 and all prior source pins. [Hosting inventory](hosting_public.json)
confirms the same Machine `2871575b4544d8` and volume `vol_vdejexpzm8ydn5x4`.
[Sprite shutdown](sprite_shutdown.json) confirms local HTTP ports 8080/8087 closed
and temporary API/gateway registrations removed; the private database remains.

## Shared capacity

[Public capacity check](shared_capacity_public.json): two fresh concurrent v6/v7
scenario jobs completed in **22.017 / 21.996 seconds**. Across 58 timed requests,
browsing p95 was **0.2053 seconds** with no browse failures. Available memory was
at least **2.34 GiB** in the three samples. Both main farms stayed unchanged,
cross-edition cookies were rejected, and numerical jobs made zero inference calls.
This is a bounded two-job smoke test, not a saturation or long-duration benchmark.
No resizing, additional Machine or volume was necessary.

## Explicit actual adviser probe

[Public probe](advisor_public.json) completed with **one actual DeepSeek request**
against frozen research version 3. Input hash, snapshot version, tool context,
main-farm preservation and replay-without-inference checks pass. The response
provided no verified evidence references and is marked **unsupported**. It is
not accepted as numerical or farming evidence. The local probe also used one
request and remained unsupported. [The ledger](advisor_experiment_budget.json)
records **two actual calls across this goal**, below the maximum of sixteen;
one earlier pre-submission authentication failure consumed zero calls.

## Completion and limits of the claim

The three recommended improvements are implemented as a labelled, isolated
playable study: context-bound operations, a challenge/evidence lifecycle, and
selective council participation. See [final recommendations](recommendations.md)
and [public browser review](browser_public_review.md). The default starts with one
clear action and guides the next decision; optional comparison layouts remain
available. This is an implemented interaction experiment, not proof of improved
human learning/enjoyment or production-valid farm advice. Unsupported provider
interpretation remains a visible limitation. V1–v6 remain frozen and preserved;
main-farm behavior and operational prohibitions remain in force.
