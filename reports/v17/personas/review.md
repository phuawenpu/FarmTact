# V15 persona review for the V17 rewrite

This review combines two kinds of evidence. The three AI personas below used the exact preserved V15 frontend (`a5ab2a8`, `index-C89Jrp2Y.js`) against the local API. They reused one existing revision-13 acceptance session, with every API write blocked. They therefore show how a populated V15 workspace reads; they do **not** reproduce a first arrival, represent independent tenants, or demonstrate human comprehension.

Fresh-arrival evidence comes from the earlier root-run walkthrough: [first arrival](../../v15/first-use-review/completed/01-first-arrival.png), [first calculated situation](../../v15/first-use-review/completed/02-calculated-situation.png), [first plan](../../v15/first-use-review/completed/02-first-plan.png), [reservation challenge](../../v15/first-use-review/completed/04-reservation-challenge.png), and [Tools index](../../v15/first-use-review/completed/06-tools-index.png). That run began on the ordinary demo farm and performed the calculation needed to expose choices. Its captured transcript is in [walkthrough.json](../../v15/first-use-review/completed/walkthrough.json). The persona observations remain AI heuristics, not usability findings.

## Novice farm manager · 390 px mobile

Evidence: [saved-session arrival](novice-mobile/01-arrival.png), [strategy preview](novice-mobile/02-strategy-preview.png), [B3 challenge](novice-mobile/03-b3-challenge.png), [B3 explanation](novice-mobile/04-b3-explanation.png), and [Tools index](novice-mobile/05-tools-index.png).

- **Observed:** The objective and disabled-real-operations boundary stay visible. Strategy cards say “Preview—not saved,” while the primary button says “Continue.” The B3 challenge says “Keep B3 available” and later introduces reservation/unavailability. More retains the objective and scene above the five-card tool deck.
- **Interpretive risks to test with people:** “Continue” may sound like a save; the B3 wording may sound contradictory without the effective dates; “recorded batch,” “saved projection,” “preview,” and “recorded simulation” may need a short legend; the retained planning chrome may make Tools look like another plan step.
- **Rubric:** Goal & Scope Definition is strong on the objective and sandbox boundary but weaker on the purpose of More. Human-in-the-Loop and Safety are visible through review language and disabled physical operations. Observability uses precise evidence labels whose comprehension remains unverified.

## Expert production planner · 1280 px desktop

Evidence: [baseline](expert-desktop/01-baseline.png), [lean choice](expert-desktop/02-strategy-1.png), [balanced choice](expert-desktop/03-strategy-2.png), [coverage choice](expert-desktop/04-strategy-3.png), and [reservation explanation](expert-desktop/05-reservation-explanation.png).

- **Observed:** Three choices expose delivery coverage, shortfall, and cost at first view. Signed differences and sampled allocations require Explain. The farm scene displays 8 of 16 spaces. The V15 B3 explanation places plan-wide numerical differences beneath a bed-specific statement.
- **Interpretive risks to test with planners:** The explanation can overstate B3-specific causality because its numbers describe the whole proposal. Offscreen beds depend on IDs and details. Tool cards communicate scope but not current counts or pending work.
- **Rubric:** Architecture & Reasoning Loop benefits from frozen identities and deterministic comparison, but causal scope must remain exact. Tool Use is broad and integrated. Human control is explicit across review, recalculation, approval, and inverse actions.

## Skeptical architecture/evaluation judge · keyboard desktop

Evidence: [keyboard strategy card](architecture-judge/01-keyboard-card.png), [deterministic explanation](architecture-judge/02-deterministic-explain.png), [History tool](architecture-judge/03-history-tool-card.png), and [integrated History card](architecture-judge/04-history-integrated.png).

- **Observed:** ArrowRight changes cards, Enter opens Explain, and Back restores focus to Explain. The active card exposes canonical entity/session/result/input-hash/revision bindings, a projection outcome basis, board targets, and action authority/eligibility. Explain, History, and replay caused no provider requests.
- **Evidence boundary:** This golden path does not by itself prove tenant isolation, stale-revision handling, concurrency, outage recovery, rate limits, or append-only persistence. Those claims require named service and browser regressions. DOM metadata exposes the contract but does not prove the server enforces it.
- **Rubric:** Architecture and Observability are directly inspectable. Explicit provider submission supports Human-in-the-Loop. Safety and evaluation guarantees need the separate regression artifacts rather than interface inference.

## V17 acceptance implications

V17 should preserve the observed keyboard/focus and immutable-binding strengths while making category, selected farm context, and return origin explicit. Its agent acceptance must exercise direct adviser submission, specialist invitation, Council review, cited saved reply, reload of the frozen thread, and discussion-to-proposal handoff. A labelled browser transport fixture can test the full rendered provider-result contract without live inference; a separate real-API smoke should verify persistence and replay using GETs only. Neither substitutes for human usability testing.

The implemented V17 candidate passed those ten bounded checks on `index-X6-Yr6Ln.js`; see [v17-acceptance.json](v17-acceptance.json). The real-service portion used GET requests only. The labelled transport portion issued one explicit thread creation, direct question, specialist invitation, and Council request without contacting an external provider. It preserved a canonical entity ID containing colons, rendered cited frozen facts and partial/withheld/validated states, restored the originating category control, reopened the same focused six-message thread after reload without resubmission, and carried exact conversation/message IDs into a separately reviewed proposal and explicit apply action.

Machine-readable evidence and the disclosure are in [summary.json](summary.json) and each persona's `walkthrough.json`.
