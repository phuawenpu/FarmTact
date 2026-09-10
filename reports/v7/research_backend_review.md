# Independent council-research backend review

Review date: 9 September 2026 UTC. Scope: `services/api/council_research.py`, the research snapshot bridge in `services/api/conversations.py`, and their existing tests. This was a static and local API review; no provider calls were made.

## Outcome

The backend has the right safety boundary: scripted text creates a visible proposal, explicit `apply` creates a new research input version, local planning owns quantities, and `choose` records a `research-participant` actor with `simulation_only: true`. Research lookup, jobs, actions, and the conversation bridge are tenant-scoped. A completed result must match the current research input version before a paid-advisor conversation can be created. Late numerical completion is archived without replacing current inputs. Opening a new challenge now clears a previous simulated choice, and evidence inspection alone does not resolve it.

The initial independent adversarial pass found three material interpreter failures. All were proposal-stage failures—the main farm and operational systems remained untouched—but they violated the research contract that ambiguous language must be clarified rather than guessed. The root implementation corrected them during review; the table records the tested resolution.

| Initial severity | Finding | Reproduction | Verified resolution |
|---|---|---|---|
| High | Reservation negation was ignored. | “Do not reserve Bed 4” and “Don't keep Bed 4 free” created a `reserve_bed` proposal. | Fixed: no proposal; a `negated_reservation` clarification is recorded. |
| High | Multiple explicit bed targets were collapsed to the first regex match. | “Keep Bed 4 and Bed 5 free” silently proposed only `bed-04`. | Fixed: singular operation requires clarification and does not select either bed. |
| High | Common negative confirmation forms inverted the requested state. | “The additional order is not confirmed” and “hasn't confirmed” proposed `confirmed: true`; only the literal token `unconfirmed` mapped to false. | Fixed: bounded negative forms propose `confirmed: false`; application still requires an explicit apply action. |
| Low | The research report published a dead Horvitz link. | Microsoft publication URL returned HTTP 404. | Fixed: endpoint uses the working primary-author PDF, `https://erichorvitz.com/chi99horvitz.pdf`. |

These cases are captured in `tests/council_research/test_independent_review.py`. Before fixes, the independent file reported five failing parser cases and one passing choice-invalidation invariant. The established session suite remained green at seven tests.

## Safeguards verified

- **No silent application:** `say` can propose but cannot apply; `apply` increments `input_version`; input changes clear `chosen` and pending turns. `choose` requires the current completed version, no pending proposal, no unresolved/rejected challenge, and a feasible policy without violations.
- **Actor distinction:** selection records the participant actor and simulation-only status. This is distinct from the existing automatic development-phase simulation acceptance policy and from operational approval, which remains disabled.
- **Stale results:** the numerical job payload freezes farm, research inputs, version, and input hash. Completion for an older version remains archived and cannot become `result_current` or be chosen.
- **Tenant isolation:** session reads and action updates filter by tenant; jobs are claimed and restored with tenant plus job ID; research-to-conversation lookup uses the requesting tenant. A foreign session returns 404.
- **Conversation freezing:** the bridge requires a current completed result and exact requested research version, then persists the numerical planning output, input hash, research inputs, source context, and evidence context into the conversation. Subsequent research changes do not rewrite the saved conversation.
- **Bounded execution:** supported mutations are enumerated and validated; query/session/action/result limits are finite; scripted research reserves no inference budget. An advisor provider call starts only through the separate explicit conversation-message action.
- **Evidence control:** a generic challenge no longer receives the stock rainfall answer; non-rainfall challenges remain unresolved. Only the known rainfall boundary can be marked corrected in the scripted study, and advisor agreement is explicitly not evidence.
- **Selective contributions:** completed jobs queue Production, Demand, or Profit only when their owned input changed (or for the initial review), followed by Planner. `stop` removes future scripted turns while stating that a running numerical job continues.

## Residual design observations

The `apply` request may supply reservation dates that differ from dates already present in the proposal. The UI must render those final values as the operation being applied; if it treats the earlier proposal card as the confirmation surface, the backend should reject changed values and require a replacement proposal. This is a review/contract issue rather than an exploit because the apply action is itself explicit and validation still runs.

Action idempotency prevents duplicate effects, but a replay after later actions returns the session's latest state rather than the exact earlier response because the action record stores no response payload. That is safe for mutations but should be documented as “idempotent effect with current-state response,” or changed if clients require byte-equivalent replay.

The research conversation freezes current source/news context when the conversation is created, potentially later than the numerical result. Numerical planning does not consume that public context, and the frozen tool fields keep it separate; the UI should show both timestamps so later contextual evidence is not mistaken for a planning input.

## Acceptance rerun

Release acceptance:

1. Run `pytest -q tests/council_research/test_sessions.py tests/council_research/test_independent_review.py`.
2. Confirm all negated/multiple-target cases yield no incorrect proposal and produce a clarification event where specified.
3. Recheck the report endpoint's eight source URLs and `git diff --check`.
4. Retain the existing tenant, stale-result, no-provider, infeasible-choice, and challenge tests in the release gate.
