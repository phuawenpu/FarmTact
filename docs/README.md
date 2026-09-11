# FarmTact documentation

Documentation audit: **11 September 2026**. Published application: **v8**.
The working tree contains the **v9 AI follow-up candidate**. V8 publication,
health and prior-state preservation passed, but public AI quality failed; the
follow-up report separates those results from V9's pending live verification.
Earlier edition source, images, state and trial reports remain immutable.

## Start here

| Reader / question | Document |
| --- | --- |
| What does the app do, and how do I run it? | [Repository README](../README.md) |
| How do all the AI and numerical components fit together? | [Scientific implementation report](technical/README.md) |
| Which actions call DeepSeek, and what does the council actually do? | [AI provider and council](technical/ai-provider-and-council.md) |
| How are demand, plant development and plans calculated? | [Numerical models and growth](technical/numerical-models-and-growth.md) |
| How do missions, quests, proposals, acceptance, replay and simulated work behave? | [Complete game backend](technical/game-backend-and-state-machines.md) |
| Where do records, evidence and public context come from? | [System, data and evidence](technical/system-data-and-evidence.md) |
| What is missing or misleading, and what should v8 address? | [Gap register and acceptance criteria](technical/gaps-and-next-iteration.md) |
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

V8's isolated PostgreSQL suite passed 589 tests with one skip; its final 56-day
network trial passed across an actual application restart. It is published and
all eight edition health endpoints match their source pins. Prior-seven state
preservation and public numerical concurrency passed. Its public combined AI
scorer failed (6 of 10 completed cases passed; workflows incomplete). Read the
[V8 postmortem](../reports/v8/public-ai-postmortem.md) and
[V9 correction report](technical/v9-ai-followup.md) before interpreting current
AI quality. The final V9 provider result is a separate required evidence item.
