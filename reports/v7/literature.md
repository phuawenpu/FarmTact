# V7 council literature review

Research cutoff: 9 September 2026 UTC (10 September in Singapore). Primary sources were reviewed in full where available; this report distinguishes published findings from proposed FarmTact experiments. No runtime provider calls were made.

## Evidence summary

| Source | Supported finding used here | Transfer limit |
|---|---|---|
| [Co-STORM, EMNLP 2024](https://aclanthology.org/2024.emnlp-main.554.pdf), pp. 2–9 | Users can interrupt an auto-steered multi-agent discussion; a dynamic mind map supports tracking; moderator ablation weakened discovery-oriented discourse. | Open-domain learning, partly simulated evaluation, 20-person human comparison; not farm planning. |
| [Mateas & Stern 2005](https://users.soe.ucsc.edu/~michaelm/publications/mateas-aiide2005.pdf), pp. 3–4 | Short authored dialogue units and responsive mix-ins reconnect player contributions to a coherent episode. | Architecture report for one interactive drama, not decision-support evidence. |
| [DataBreeze 2020](https://arxiv.org/pdf/2004.10428), pp. 6–9 | Direct selection can supply referents/parameters for language; visible ambiguity controls support repair. | Proof of concept centered on pen/touch/speech on a large display. |
| [TalkToModel, 2023 version](https://arxiv.org/pdf/2207.04154), pp. 3–16 | Parsing to constrained operations, executing tools, and composing grounded replies are separable; explicit prior-filter/operation state supports follow-ups. A study with 45 healthcare workers and 13 ML professionals favored conversation over its comparison dashboard on task outcomes and ratings. | Explains predictive models through a defined grammar; does not validate farm mutations or councils. |
| [Madumal et al. 2019](https://arxiv.org/pdf/1903.02409), pp. 3–8 | Explanation dialogues include clarification, follow-up, affirmation/counterargument, and returns from argument to explanation; protocol derived from 398 dialogues and evaluated with 14 participants across 101 human-agent dialogues. | Scripted dialogue domains; fit does not establish evidence truth or planning quality. |
| [Horvitz 1999](https://erichorvitz.com/chi99horvitz.pdf), pp. 1–2, 6–8 | Mixed initiative should account for goal/attention uncertainty and action cost, ask about material uncertainty, minimize bad guesses, and retain interaction history. | Calendar-assistant examples provide principles, not FarmTact thresholds. |
| [Heer & Robertson 2007](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/InfoVis2007-DynaVis.pdf), pp. 1–4, 6–8 | Simple, predictable, semantically valid transitions can improve graphical perception; effects and timing are task-dependent. | Statistical graphic transitions, not council causality or mobile farm boards. |
| [W3C WCAG 2.2 SC 2.3.3 guidance](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html) | Avoid or disable non-essential interaction-triggered motion and support reduced-motion preferences. | Accessibility guidance, not a comparative FarmTact usability result. |

## Brief and baseline implications

The official page-13 rubric asks for business scope, explicit reasoning/state, typed tools, calibrated human oversight, security, observability/evaluation, and clean orchestration. Sumin's brief adds the preferred experience: scenario changes should visibly cause business specialists and a Planner to reformulate a plan. Visible seven-speaker debate is not an official criterion; disagreement must arise from evidence or constraints rather than scripting.

V6 already has frozen discussions, selected-bed labels, targeted advisor invitation, a full-council action, replay, bounded proposals, scenario branches and explicit simulation handling. Browser audit evidence at 360/390/430/1280 shows the selected context is not removable/inspectable and the task's bed-reservation and order-confirmation operations are absent. The research therefore recommends reinforcement, not a replacement interface.

## Decision package

- **Council flow:** select visible objects → clarify ambiguous reference → run named local lookup → hear only materially relevant roles → record outstanding constraint/evidence state → preview an input operation → accept into a new scenario version → solve → inspect persistent deltas → explicitly choose or reject the simulated version.
- **45-second storyboard:** ask about selected Bed 4/order; clarify “later”; inspect computed coverage; propose dated Bed 4 reservation; apply and solve; challenge one assumption; inspect evidence and comparison; explicitly choose/reject. Farm time stays fixed during computation.
- **Selection alternatives:** (A) removable multi-object chips in the composer; (B) one contextual reply card with “add another object.” Both store exact IDs/version, clarify ambiguity, support keyboard/touch, and treat device voice typing as optional.
- **Intent boundary:** explanation performs frozen evidence/result lookup; a what-if creates a visible proposed operation; only accepted mutations create a scenario version and solver run; compatible completed versions may be compared; selection requires an explicit farmer action.
- **Clarification:** ask when ambiguity affects an input, constraint, comparison root, feasibility or approval target. Label low-impact uncertainty. Preserve unresolved and rejected recommendations. Silence and council consensus are never approval or evidence.
- **Animation:** agent concern → object highlight → named tool state → affected quantities → persistent deltas. Motion is restrained and optional; reduced motion gets instant highlights and static old/new values.

## Provisional next-iteration candidates

1. Context-bound conversational operations with visible parse, confirmation and versioned numerical consequence.
2. Selective council participation plus a shared map of outstanding questions, constraints and evidence.
3. A challenge-to-evidence lifecycle with resolved, unsupported, rejected and approval-blocking states.

These candidates still require the controlled v7 browser comparison. Paper support applies to their component mechanisms; effectiveness in FarmTact, on phones, and for farm decisions remains a hypothesis. Full rationale, matrices, storyboard and limits are in `docs/research/council-participation.md`.
