# FarmTact documentation

Documentation audit: **11 September 2026**. Published application: **v9**, frozen
from source `89d29cc3e071e12373204ff234d0a261ce71b5a1`. All nine health/source
checks and captured v1–v8 preservation passed. Earlier edition source, images,
state and trial reports remain immutable. V8 public AI quality failed. V9 is the
separate published corrective edition, but its live quality gate also failed:
12 of 18 automated cases passed while workflow integrity passed. The completed
AI-assisted review classified 10 messages as sound, 5 as sound with limits and 3
as materially contradictory. V10 is the unpublished grounding-remediation candidate.

## Start here

| Reader / question | Document |
| --- | --- |
| What does the app do, and how do I run it? | [Repository README](../README.md) |
| How do all the AI and numerical components fit together? | [Scientific implementation report](technical/README.md) |
| Which actions call DeepSeek, and what does the council actually do? | [AI provider and council](technical/ai-provider-and-council.md) |
| How are demand, plant development and plans calculated? | [Numerical models and growth](technical/numerical-models-and-growth.md) |
| How do missions, quests, proposals, acceptance, replay and simulated work behave? | [Complete game backend](technical/game-backend-and-state-machines.md) |
| Where do records, evidence and public context come from? | [System, data and evidence](technical/system-data-and-evidence.md) |
| What remains missing or misleading after v8/v9? | [Gap register and acceptance criteria](technical/gaps-and-next-iteration.md) |
| What does the unpublished V10 candidate correct? | [V10 grounding follow-up](technical/v10-grounding-followup.md) |
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
historical decisions. Use the current deployment runbook for operations. Existing
numbered editions retain their frozen source/image and independent progress;
documentation changes do not publish a new application edition.

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
unpublished [V10 remediation candidate](technical/v10-grounding-followup.md)
addresses the Supply and absence-context mechanisms. Its full suite passed 611
tests with one skip in 441.23 seconds; publication and provider-backed verification
remain pending, and general prose/crop-mix entailment remains unresolved.

The [authenticated public V9 UI replay](../reports/v9/ui-live-replay.json) passed 38 of 38 checks across mobile and
desktop widths. It used saved mission, conversation and research state; mutation
attempts and direct provider traffic were intercepted before network dispatch.

V9's public capacity check passed two overlapping numerical jobs and 58 browse
samples with zero provider calls. Its 56-day synthetic execution run passed mass,
cash and lot-receipt checks with 60 task events, 64 demand-service events, one
future replan and zero provider calls; an actual application restart was not
exercised.
