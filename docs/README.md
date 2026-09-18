## Current V21 workspace

V12 is the product base; V20 restored it and V21 adds targeted improvements.
Read [V21 scope](v21-v12-ux.md), [walkthrough](v12-restoration-ux-review.md),
[release verification](../reports/v21/README.md) and [handoff](workspace-handoff.md).
Older edition descriptions below are historical.

# FarmTact documentation

Documentation updated **17 September 2026**. Latest public application: **V16**,
frozen from source `3487faf90ec9205c903f8a6e40fc09aa94614dcc` and image
`registry.fly.io/farmtact@sha256:e3bedff080dbdcebc2e6619210e91bce5faeeeef51388656f1c9e75743883493`.
The public `/` and `/play` routes now serve the same integrated card shell for one
ordinary synthetic farm. Historical release artifacts remain immutable; older UI
and edition descriptions below are evidence of their dated state, not descriptions
of the current public interface. V16 corrects V15's post-publication raw-JSON and
wrong-stage proposal explanation defects. V15 remains immutable and preserved.
The next unused application number is **V17**.

Start with the [V16 implementation report](../reports/v16/implementation.md),
the preserved [V15 capability checklist](v15-capability-checklist.md), and
[current workspace handoff](workspace-handoff.md). V16 publication evidence is
automated technical evidence: 49 semantic, 97 layout, 108 complete-journey,
20 operator and 28 exact staged-image checks, with zero provider requests. Human
usability and farmer comprehension remain
unverified, no new provider-quality result is claimed, and actual farm operations
remain disabled.

## Start here

- [Fresh-workspace handoff](workspace-handoff.md): durable state, restart instructions and outstanding work.

| Reader / question | Document |
| --- | --- |
| What does the app do, and how do I run it? | [Repository README](../README.md) |
| How do all the AI and numerical components fit together? | [Scientific implementation report](technical/README.md) |
| Which actions call DeepSeek, and what does the council actually do? | [AI provider and council](technical/ai-provider-and-council.md) |
| How are demand, plant development and plans calculated? | [Numerical models and growth](technical/numerical-models-and-growth.md) |
| How do missions, quests, proposals, acceptance, replay and simulated work behave? | [Complete game backend](technical/game-backend-and-state-machines.md) |
| Where do records, evidence and public context come from? | [System, data and evidence](technical/system-data-and-evidence.md) |
| What remains missing or misleading after v8–v10? | [Gap register and acceptance criteria](technical/gaps-and-next-iteration.md) |
| What does V10 correct and leave unresolved? | [V10 grounding follow-up](technical/v10-grounding-followup.md) |
| Which AI defects did the public trial expose, and how are they corrected? | [V9 AI follow-up](technical/v9-ai-followup.md) |
| What did v8 change, verify and leave unresolved? | [V8 remediation report](technical/v8-remediation-report.md) |
| What do the bounded v8 work packages report? | [Council](../reports/v8/council.md), [planner](../reports/v8/planner.md), [data/ML](../reports/v8/data-ml.md) |
| How can I reproduce the documentation and its checks? | [Reproducibility guide](technical/reproducibility.md) |
| Short inventory of datasets and models | [Data and models](data-and-models.md) |
| Security and inference boundaries | [Security](security.md) |
| Hosting, deployment and edition preservation | [Fly runtime](deployment/fly.md), [immutable publication](deployment/editions.md) |
| Provider capability tests | [DeepSeek trial runbook](runbooks/deepseek_trial_and_cutover.md) |
| How are expired anonymous workspaces pruned? | [Retention runbook](runbooks/retention.md) |
| What was actually tested for v7? | [V7 release evidence](../reports/v7/implementation.md) |
| Development history and ownership | [Execution plan](execution-plan.md), [decision log](decision-log.md) |

## Reading evidence correctly

The [build specification](../FarmTact_Build_Specification.md) and
[runtime specification](../FarmTact_DeepSeek_Runtime_Specification.md) contain both
requirements and implemented amendments. Their 11 September v8 amendments, the
remediation report and the gap register distinguish these explicitly. A requirement
or candidate source file is not proof of a deployed or successfully trialled feature.

Release reports describe the dates, fixtures, models, source commits and tests they
actually exercised. Historical six-role council results remain historical; they
are not seven-role or v7 adviser-quality evidence. Headless browser tests and AI
persona reviews are not human usability studies. Public observations, fictional
farm inputs, model interpretations and simulated outputs have different provenance.

The v5 plans, consolidation assessment and older execution-log entries preserve
historical decisions. Use the current deployment runbook for operations. Historical
numbered editions retain their frozen source/image records; documentation changes
do not publish a new application edition or change the current V15 service.

V9's final repository regression passed 606 tests with one skip; its mobile
typed-fact display check passed 21 assertions with fixture-shaped responses and
zero provider calls. All nine edition health/source checks and captured v1–v8
state preservation passed. V8's public combined AI scorer remains failed (6 of 10
completed cases passed; workflows incomplete). Read the
[V8 postmortem](../reports/v8/public-ai-postmortem.md) and
[V9 correction report](technical/v9-ai-followup.md) together. V9's automated
quality result is FAIL (12 of 18 passed; workflow integrity passed) after 21 new
actual requests, bringing the cumulative ledger to 76. The
[AI-assisted semantic review](../reports/v9/ai-assisted-semantic-review.md) found
10 sound messages, 5 sound with limits and 3 materially contradictory. The narrow
published [V10 remediation edition](technical/v10-grounding-followup.md)
addresses the Supply and absence-context mechanisms. Its full suite passed 611
tests with one skip in 441.23 seconds. Its Council-only live run used nine requests
for seven messages and passed 5 of 7 targeted cases. A fresh mission used zero
provider calls because seven remaining daily requests could not satisfy its nine-call
reservation; the three numerical strategies were retained. Direct, invite, research
and vision were not rerun. General prose/crop-mix entailment remains unresolved.

The [authenticated public V9 UI replay](../reports/v9/ui-live-replay.json) passed 38 of 38 checks across mobile and
desktop widths. It used saved mission, conversation and research state; mutation
attempts and direct provider traffic were intercepted before network dispatch.

V9's public capacity check passed two overlapping numerical jobs and 58 browse
samples with zero provider calls. Its 56-day synthetic execution run passed mass,
cash and lot-receipt checks with 60 task events, 64 demand-service events, one
future replan and zero provider calls; an actual application restart was not
exercised.

The final [V10 semantic audit](../reports/v10/ai-assisted-semantic-review.md)
examines seven messages and 26 assertions: two sound, four with limits, one
contradictory. Profit mislabels a negative Lean margin delta as a gain. This is
AI-assisted review, not human expert validation. The [V10 execution trial](../reports/v10/execution-public.json)
passed 56 days of numerical reconciliation and receipt replay with zero provider
calls; these are separate evidence dimensions.


V10 final capacity evidence is **FAIL** (`reports/v10/shared-capacity-public.json`):
the isolated pair exceeded the 180-second job deadline and browse p95 reached
15.0367 seconds. An earlier mixed-load probe also failed. HTTP health, farm/cookie
isolation and zero inference passed; they do not imply loaded performance passed.
Future acceptance requires queue/execution tracing, CPU/platform-quota measurement,
shared numerical admission control evaluation and bounded cancellation testing.
No host resource increase or threshold relaxation was made. See the V10 technical
follow-up and capacity protocol note for exact scope and cleanup.


V11: [organizer brief and implementation plan](v11-implementation-plan.md), [technical methods and boundaries](technical/v11-guided-production-planning.md), [acceptance evidence](../reports/v11/). These records distinguish V11 evidence from preserved historical editions.
