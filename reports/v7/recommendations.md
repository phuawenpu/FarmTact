# V7 playable-council recommendations

Evaluation date: pending playable-concept walkthrough. Evidence baseline: published v6 audit on 9 September 2026 UTC. These recommendations are provisional until the same synthetic task has been completed in each v7 concept.

## Decision method

The comparison asks whether each concept helps a participant correctly complete this fixed sequence: request a plan; reserve Bed 4 for stated dates; mark the additional order unconfirmed; challenge an assumption; inspect the current same-policy comparison; and choose a feasible simulated version.

The release decision uses observable task outcomes rather than message count or appearance:

- immediate pickup: one clear starting action, an obvious next step, and a target of reaching the first meaningful planning choice within 30 seconds without reading instructions;
- correct understanding of selected context, assumptions, frozen version, and numerical deltas;
- successful correction of bed and order constraints without silent interpretation;
- selection of a feasible current result, with unresolved/rejected states preserved;
- elapsed task time, wrong actions, clarification failures, and recovery;
- reading continuity, evidence return, keyboard controls, touch-target geometry, and reduced-motion equivalence.

The default journey must use progressive disclosure: start the farm task before exposing layout/research controls, use plain words and visible units, keep selected context beside the composer, and reserve the three-concept comparison for an optional **Compare research layouts** action. The 30-second value is a design target for the upcoming human test, not an observed human result.

The walkthrough reviewers are Codex agents, not representative human participants. They can expose interaction defects and compare deterministic task paths; they cannot measure enjoyment, trust, learning, physical touch comfort, device-keyboard occlusion, or farming usefulness. Enjoyment and real-world usefulness remain future human-study measures.

## Concept comparison

| Concept | Immediate pickup | Understanding | Correction success | Feasible-current-version selection | Completion time | Accessibility and continuity | Result |
|---|---|---|---|---|---|---|
| Inline council | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Expandable conversation sheet | Pending | Pending | Pending | Pending | Pending | Pending | Pending |
| Contextual adviser cards with persistent composer | Pending | Pending | Pending | Pending | Pending | Pending | Pending |

Rankings will be filled only after the controlled browser walkthrough. The presentation order must rotate across independent reviews so the first concept does not gain a practice advantage.

## Candidate 1 — Context-bound conversational operations

**Research basis.** DataBreeze shows how direct selection can supply referents and parameters omitted from natural language, with visible controls for ambiguity. TalkToModel separates language parsing, constrained executable operations, tool execution, and replies grounded in tool output. These mechanisms were studied in visual data exploration and model explanation, not mobile farm planning.

**Observed v6 gap.** V6 shows one selected bed as plain context text and supports five scalar proposed controls. The context cannot be removed or extended to an order or harvest window. Bed reservations and order-confirmation changes are absent.

**Proposed interaction.** Bind exact bed, crop, order, or window IDs to visible removable context. Interpret a request into a typed proposal; require an explicit apply action; create a new frozen research version; run the local numerical planner; and retain old/new results with signed deltas. Clarify negation, multiple singular targets, and ambiguous references rather than guessing.

**Smallest experiment.** From a fresh session with no advance instructions, find the starting action and complete the Bed 4 and additional-order steps with each context presentation while holding data, copy, operation schema, and numerical result constant.

**Success measure.** The starting action and next step are discoverable without opening research settings; selected context stays visible by the composer; the reviewer identifies every bound object and proposed value before applying it, creates the intended inputs without a wrong mutation, recognizes the new current version, and explains one resulting numerical difference from the displayed evidence.

**Implementation effort.** High: typed research operations, version persistence, solver integration, stale-response protection, and linked visual states must agree.

**Limitation.** Automated and agent review cannot establish that free-form users will phrase constraints within the bounded grammar, or that the interaction works on a physical phone. Unsupported operations still require clear recovery.

**Walkthrough result and priority.** Pending.

## Candidate 2 — Selective, steerable council with shared outstanding issues

**Research basis.** Co-STORM supports user intervention in an automatically steered discussion and a dynamic shared representation; its moderator ablation weakened discovery-oriented discourse more than its multi-expert ablation. Façade shows how short responsive exchanges can reconnect a player contribution to a coherent episode. Sumin's brief supplies FarmTact's business-role thesis. None establishes that seven farm roles or visible debate improves plan quality.

**Observed v6 gap.** V6 can address one adviser, invite another, or convene all seven, but it does not visibly explain why a role should speak next or summarize outstanding constraints, disagreements, and evidence. Controls are disabled throughout a bounded active response.

**Proposed interaction.** Permit steering at safe turn boundaries; queue only specialists whose owned inputs changed or whose evidence can resolve the current issue; let the Planner close or escalate the episode; and keep a compact shared state of questions, constraints, evidence, tool results, and abstentions. Stop prevents future contributions without pretending to cancel an in-flight calculation/provider request.

**Smallest experiment.** Compare targeted and full-council paths for the identical frozen change. Count only material contributions and check whether every consequential conflict remains visible.

**Success measure.** The reviewer can redirect or stop safely, identify why each displayed role contributed, recover the outstanding issue after a tool update, and complete the plan without redundant turns obscuring the decision.

**Implementation effort.** Medium: most v6 primitives exist, but contribution routing, checkpoint state, continuity behavior, and shared issue presentation require work.

**Limitation.** Short scripted trials may favor selective routing and cannot reveal whether unexpected human questions benefit from broader council exploration. Co-STORM's learning results do not establish farm-decision accuracy.

**Walkthrough result and priority.** Pending.

## Candidate 3 — Challenge-to-evidence lifecycle

**Research basis.** Madumal et al. model clarification, follow-up, counterargument, and return to explanation. Horvitz recommends dialogue when uncertainty materially changes the value of acting and minimizing the cost of a bad guess. These sources support interaction structure, not the truth of any agricultural claim or a universal approval threshold.

**Observed v6 gap.** V6 supports free text and evidence details but lacks a compact state for a challenged claim, its evidence, correction, rejection, and effect on selection.

**Proposed interaction.** Attach **Show evidence**, **Correct assumption**, and **Consider another option** to a specific claim and frozen result. Preserve `unresolved`, `corrected`, and `rejected` states; prevent a material unresolved/rejected recommendation from being chosen; and never treat evidence viewing, adviser agreement, or silence as resolution.

**Smallest experiment.** Challenge the claim that outdoor rainfall changes a sheltered hydroponic crop's yield. Verify that the system identifies rainfall as contextual rather than a numerical yield input, preserves the challenge state, and requires an explicit participant resolution before selection.

**Success measure.** The reviewer states the claim and evidence boundary accurately, can reject or correct without losing the comparison, and cannot choose while the material challenge remains unresolved.

**Implementation effort.** Medium: challenge state and controls are bounded, but evidence linkage, version invalidation, and policy blocking must remain consistent across reload and replay.

**Limitation.** The scripted rainfall case has a known answer and may overstate success on genuinely uncertain or conflicting evidence. Domain policy still determines which unresolved facts block selection.

**Walkthrough result and priority.** Pending.

## Recommendation boundary

At most these three candidates will be recommended. Final ordering will cite the browser reports and distinguish observed v7 behavior from literature-derived rationale. A presentation concept may perform best without becoming a fourth recommendation: layout is the delivery mechanism for the three interaction changes. Concept controls belong in optional research comparison, not the first-time farm journey.
