# V8 human usability study protocol

Protocol version: 1.0
Pre-registration date: 11 September 2026
Status: protocol only; recruitment has not started and no participant results exist

## Purpose and claim boundary

This study asks whether adults who have not worked on FarmTact can understand and
complete a small set of synthetic planning tasks in the V8 interface. It does not
test crop yield, commercial benefit, advisor accuracy, or safe autonomous farm
operation. All sessions use the synthetic demo and simulation-only actions.

The study has two descriptive cohorts. The novice cohort measures first-use
clarity. The practitioner cohort tests whether people with relevant operating
experience can inspect assumptions, detect unsupported constraints, and
interpret the plan without mistaking it for an operational recommendation.
Results from one cohort will not be generalized to the other.

## Participants

- Recruit 12 novices who are at least 18 years old, have no professional crop
  production or farm-planning role, and did not contribute to FarmTact.
- Recruit 8 practitioners who are at least 18 years old and have at least two
  years of responsibility for protected-crop production, crop scheduling,
  inventory, fulfillment, or farm operations. Record role and experience band,
  but do not collect employer or customer names.
- Exclude project contributors, prior study participants, anyone unable to give
  informed consent, and anyone whose accessibility needs cannot be supported by
  the tested setup. Report exclusion counts and reasons in aggregate.
- Recruit through neutral invitations. Compensation, consent language, and any
  required ethics review must be approved before recruitment. Participation is
  voluntary and withdrawal does not affect compensation.

The sample is deliberately small and supports formative, descriptive usability
findings. It is not powered for population estimates or practitioner-versus-
novice hypothesis testing. We will report counts, medians, ranges, and all
pre-registered denominators, without significance tests.

## Frozen build and setup

Before the first session, record the source commit, immutable edition, image
digest, browser version, viewport, input device, simulation capability-registry
hash, fixture hash, planner/model versions, and study-script hash. Use the same
build and synthetic fixture for every participant. If a blocking defect requires
a new build, stop recruitment, record the deviation, and begin a separately
versioned cohort rather than pooling results silently.

Each participant receives a fresh tenant with no saved history. Provider-backed
advisor calls are disabled. The moderator may explain that the farm and outcomes
are synthetic and that no real operation can be triggered, but may not explain
where controls are or how to choose a strategy before the unaided tasks.

Half of each cohort begins at a 390 by 844 CSS-pixel viewport and half at a 1280
by 800 viewport. Participants then repeat the short inspection task at the other
viewport. Assignment alternates within cohort using a pre-generated sequence.
Viewport results are descriptive; mobile emulation does not establish physical
touch ergonomics, keyboard behavior, or accessibility on a real device.

## Task script

The moderator reads the quoted goal and then remains silent unless the participant
asks for clarification or reaches a safety stop. Hints and moderator interventions
are timestamped and make the affected task assisted rather than unaided.

1. **Orientation:** “Tell me whether this is a real farm control system, what date
   the plan starts from, and what action you would take first to inspect the
   farm.” The first meaningful action and time to it are recorded.
2. **Plan inspection:** “Find a dated delivery need, run the local planning
   calculation without an advisor council, and compare the Balanced and
   Resilient choices. Choose the one you would inspect further and explain why.”
3. **Traceability:** “For one booked order, show how much was requested and
   delivered, identify the inventory lot if any, and tell me what an unavailable
   price means.”
4. **Constraint comprehension:** “Find two constraints the simulation enforces
   and two farm constraints it does not support. Explain what you would need
   before trusting it for a real operation.”
5. **Scenario recovery:** “Create a bounded what-if scenario, start its local
   calculation, and recover from the supplied failed/cancelled example without
   creating a duplicate result.” The moderator uses a pre-seeded failure; no
   provider call is made.
6. **Execution and replan:** “Create a synthetic execution world, advance seven
   days, inspect one completed task and one inventory change, replan the future,
   and verify that past actions were not changed.”
7. **Final comprehension:** Without looking back, answer five fixed questions:
   data provenance; whether a forecast is an observation; whether Resilient is a
   calibrated probability guarantee; whether the interface can operate farm
   equipment; and what information is missing for real use.

The session ends after 35 minutes or earlier at participant request. A task stops
after 8 minutes, three wrong submissions, or a participant statement that they
cannot continue. The moderator then resets the task and proceeds.

## Outcomes and coding

Primary outcomes are defined before data collection:

- **Orientation success:** correct synthetic/non-operational identification and
  one meaningful inspection action within 60 seconds, without a hint.
- **Core workflow success:** tasks 2, 3, and 6 completed with the correct stored
  objects and no moderator hint. Record completion separately for each task.
- **Safety comprehension:** at least four of five final questions correct,
  including both “forecast is not observation” and “cannot operate equipment.”
- **Critical error:** accepting an infeasible/stale result, reporting an unknown
  price as observed zero, treating synthetic execution as a real event, asserting
  a calibrated guarantee, or claiming an unsupported constraint is enforced.

Secondary outcomes are time per task, wrong action count, backtracks, hints,
abandonment, successful retry/cancel recovery, correct order/lot explanation,
correct supported/unsupported-constraint explanation, and a post-task Single
Ease Question scored 1–7 for tasks 2, 3, and 6. A final five-item System Usability
Scale may be reported as descriptive context, not as evidence of farm benefit.

Two researchers independently code screen/event logs against the fixed rubric.
They reconcile disagreements while retaining both original codes. Report raw
agreement and the reconciliation count. Free-text themes use an inductive codebook
created after collection and are labeled exploratory.

## Pre-registered readiness thresholds

V8 meets this formative usability gate only if all conditions hold:

- at least 10 of 12 novices and 7 of 8 practitioners meet orientation success;
- at least 9 of 12 novices and 6 of 8 practitioners complete each core workflow
  task unaided;
- at least 10 of 12 novices and all 8 practitioners meet safety comprehension;
- neither cohort has any unresolved critical error repeated by two or more
  participants; and
- median Single Ease Question score is at least 5 in each cohort for every core
  workflow task.

A participant who withdraws contributes completed-task observations only and is
included in denominators for tasks they started. A technical failure before a task
begins is excluded from that task denominator and reported separately. Missing
answers after a started task count as unsuccessful. No threshold or denominator
will be changed after seeing outcomes. Failure means the interface needs further
work; it does not justify searching for a favorable subgroup.

## Data handling

Collect a random participant code, cohort, broad experience band, assigned
viewport order, timestamps, task events, coded outcomes, rating answers, and
optional comments. Do not collect farm, employer, buyer, or customer records.
Screen recordings are optional and require separate consent; pause recording on
request and never capture passwords or unrelated screens. Device-keyboard
dictation, if tried, remains device-local and the study does not record audio.

Keep the code-to-contact mapping outside the research dataset with access limited
to the recruitment lead. Encrypt stored data, restrict access to the named study
team, define a deletion date before consent, honor withdrawal where feasible,
and publish only aggregate counts and short de-identified excerpts. The study
owner must document the applicable ethics and privacy basis before recruitment.

## Reporting

Publish participant flow, technical failures, deviations, every registered
outcome, threshold results, cohort-specific denominators, viewport limitations,
and unresolved critical errors. Clearly distinguish direct observation, coded
interpretation, and exploratory themes. Do not replace absent participants with
AI walkthroughs and do not describe this protocol as a completed study.
