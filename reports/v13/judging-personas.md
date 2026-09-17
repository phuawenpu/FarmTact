# V13 blind hackathon judging report

Review date: 17 September 2026 UTC. Evidence type: scripted AI-persona review,
not human usability research. Three judges received only the farm-planning problem
statement and seven-part hackathon rubric. They were not given a manual and did
not inspect source or project documentation before using a fresh local V13 tenant.

## Brief supplied to every judge

> Farm managers determine planting schedules based on expected customer demand,
> crop growth cycles, available land, and seasonal conditions. Planning is largely
> based on historical experience and manual records, making it difficult to balance
> production capacity with changing market demand while minimizing crop wastage.

The rubric covered goal/scope, architecture/reasoning loop, tool integration,
autonomy/human checkpoints, safety/security, observability/evaluation, and
platform/tooling. Each category was scored from zero to five.

## Personas and first-use findings

| Persona | Viewport and stance | Initial score | Most useful evidence |
|---|---|---:|---|
| Farm manager judge | 390 px mobile; evaluates whether the next decision and trade-off are understandable | 24/35 | Found real demand/supply calculations and the Reserve flow, but caught an infeasible reservation, blank booked gap, enabled approval on infeasible plans, and weak blocked-provider explanation. |
| Agent architect judge | 1280 px desktop; skeptical of decorative “multi-agent” claims | 23/35 | Verified the actual session → proposal → local job → result loop and contextual conversation traffic; traced the infeasibility to `bed-07`'s executed crop and found that inverse recovery incorrectly required a feasible current result. |
| Security/evaluation judge | 360 px, reduced motion, adversarial pointer/touch/keyboard use | 27/35 | Verified provenance, zero automatic provider traffic, focus binding, persisted jobs, backend duplicate rejection, keyboard/swipe/scroll behavior, and honest fail-closed provider messaging; identified sanitation occupancy, duplicate-click, basis, and metric-binding defects. |

These scores describe the pre-repair candidate. They are not averaged into a claim
about real judges, farmer comprehension, or competition outcome.

## Defects repaired from judging

1. The B3 reservation now begins on `2026-10-01`, the first day after the recorded
   crop's harvest **and two sanitation days**, using the planner's own occupancy
   contract. The post-reservation result has three feasible strategies.
2. Undo now queues an auditable inverse from the original feasible source even when
   the current result is infeasible; the original event is retained.
3. The header never presents an infeasible option as the active basis. Approval is
   enabled only for the selected feasible strategy and otherwise gives a reason.
4. Booked gap is derived server-side from requested and delivered booked demand.
5. Consequence metrics and signed deltas bind to the recalculated result's selected
   strategy. They no longer silently fall back to Lean when content-derived IDs
   change.
6. Reserve, Undo, and baseline calculation take a synchronous client lock on
   activation; server idempotency/revision guards remain the authority.
7. A blocked explicit Ask shows the persisted server reason and states that no
   fallback dialogue was invented. Opening Ask still sends nothing.
8. Conversation focus rejects a valid entity paired with a different card ID.
9. Infeasible strategy states, violations, recovery guidance, mobile comparison
   affordance, contextual Details priority, and a bounded Council-role card are
   visible in the shell.
10. Shared-network session admission increased from 10 to 30 new demo sessions per
    hour while retaining the 100/hour global cap and every API/write/AI-specific
    limit. This was prompted by three concurrent judges behind one address; it does
    not relax the narrower inference quotas.

## Targeted post-repair replay

The adversarial judge repeated baseline → B3 Details → Reserve → recalculation →
Undo on a freshly seeded tenant:

- reservation window `2026-10-01 → 2026-11-02`;
- exactly one proposal/apply pair and one inverse request under rapid activation;
- all three recalculated strategies feasible;
- Balanced remained the displayed basis;
- Undo restored 446 kg planned supply, 378 kg booked gap, and the feasible baseline;
- all mutation responses were 201/202; no duplicate 409/422 was produced.

The judge then found that the consequence panel still reflected Lean while the
header reflected Balanced. That final binding defect was repaired and regression
tested. The independent real-browser journey now shows one consistent Balanced
result after reservation: 442 kg production coverage, 41 kg closing surplus,
193 kg expiry exposure, and SGD 2,731.1 planner margin, with signed deltas.

## Remaining limitations

- Heavy Rainfall is deliberately scenario context and is strongly labelled, but
  the flagship mutation is the explicit capacity reservation. The interface should
  not imply that rainfall automatically changed the numerical plan.
- Details updates a contextual region farther down the mobile page; stronger
  disclosure/focus semantics remain desirable.
- Direct single-app development serving lacks the edition gateway's `/api/releases`
  endpoint, so local-only judging logs one harmless 404. Published routing supplies it.
- Raw hashes, revisions, and constraint codes remain useful audit evidence but need
  continued farmer-facing translation.
- The retained JavaScript bundle warning is a measured optimization item.
- Screen readers, physical devices, representative farmers, and real-farm efficacy
  were not tested. No human-usability or accessibility-conformance claim is made.

## Evidence files

- Real backend journey: `tests/browser/v13_real_journey.mjs`
- Responsive deterministic journey: `tests/browser/v13_tactical_cards.mjs`
- Final real mobile capture: `apps/web/screenshots/v13-real-mobile-390.png`
- Responsive captures: `apps/web/screenshots/v13-tactical-{360,390,430,1280}.png`
- Focus/inverse/admission regressions: `tests/gameplay/test_v13_conversation_focus.py`,
  `tests/gameplay/test_v13_inverse_proposal.py`, and
  `tests/review/test_abuse_limits.py`

