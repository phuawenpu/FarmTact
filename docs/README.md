# FarmTact documentation

Documentation audit: **11 September 2026**. Published application: **v7**.
The implementation audit starts from repository commit
`a96025e` and distinguishes current source, frozen release evidence and future requirements.

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
| How can I reproduce the documentation and its checks? | [Reproducibility guide](technical/reproducibility.md) |
| Short inventory of datasets and models | [Data and models](data-and-models.md) |
| Security and inference boundaries | [Security](security.md) |
| Hosting, deployment and edition preservation | [Fly runtime](deployment/fly.md), [immutable publication](deployment/editions.md) |
| Provider capability tests | [DeepSeek trial runbook](runbooks/deepseek_trial_and_cutover.md) |
| What was actually tested for v7? | [V7 release evidence](../reports/v7/implementation.md) |
| Development history and ownership | [Execution plan](execution-plan.md), [decision log](decision-log.md) |

## Reading evidence correctly

The [build specification](../FarmTact_Build_Specification.md) and
[runtime specification](../FarmTact_DeepSeek_Runtime_Specification.md) contain both
requirements and implemented amendments. Their 11 September audit amendments and
the gap register distinguish these explicitly. A requirement is not proof of delivery.

Release reports describe the dates, fixtures, models, source commits and tests they
actually exercised. Historical six-role council results remain historical; they
are not seven-role or v7 adviser-quality evidence. Headless browser tests and AI
persona reviews are not human usability studies. Public observations, fictional
farm inputs, model interpretations and simulated outputs have different provenance.

The v5 plans, consolidation assessment and older execution-log entries preserve
historical decisions. Use the current deployment runbook for operations. Existing
numbered editions retain their frozen source/image and independent progress;
documentation changes do not publish a new application edition.
