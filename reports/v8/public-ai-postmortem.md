# FarmTact V8 public AI postmortem

**Evidence date:** 11 September 2026<br>
**Published edition:** immutable V8<br>
**Source:** `a00e546b1270a5c532e8eae6b8b64e568c344c13`<br>
**Image digest:** `8ed6fc3b1a6632f88bbc2b6a20b200b44bba13d7583c70f40e1c31f85c1e8357`<br>
**Overall AI quality result:** **FAIL**

## Scope and claim boundary

This postmortem examines the retained public V8 mission and conversation outputs.
It distinguishes successful HTTP execution, local schema/reference validation and
simulation acceptance from whether an adviser's prose follows the meaning of its
selected facts. These are different gates.

The mission completed all seven provider calls and passed the implemented local
evidence gate. The conversation completed its direct turn but stopped partway
through its invited exchange. The combined automated quality report failed. The
published V8 source and image are immutable, so corrective prompt/contract work is
being prepared for V9 rather than rewriting V8.

The prose review below is **AI-assisted engineering review**, not human expert,
agronomic or usability validation. The quality artifact itself records
`semantic_review_status=PENDING` and contains no human reviews. Reference membership,
keyword checks and this postmortem do not establish agricultural truth.

Primary evidence:

- [public planning mission](planning-public.json)
- [public conversation replay](conversation-public-replay.json)
- [public conversation event stream](conversation-public-events.json)
- [combined public V8 quality score](ai-quality-public-v8.json)
- [cumulative live-call ledger](live-call-ledger.json)

Deployment evidence records all eight edition health checks passing and all captured
v1–v7 state remaining preserved after V8 publication: [deployment health](deployment-health.json)
and [preservation result](preservation-after.json).

## Results at a glance

| Surface | Transport and persistence | Local schema/reference gate | Quality result |
| --- | --- | --- | --- |
| Public V8 mission | PASS; seven calls completed, replay made zero calls | PASS; seven claims locally validated, mission evidence gate passed | FAIL in combined scorer: Weather, Supply Chain and Planning Chair failed role/evidence checks; additional meaning weaknesses are described below |
| Public V8 direct conversation | PASS; one request and one adviser reply persisted | Reply stored as `references_verified` | FAIL: Production reply failed the automated evidence check |
| Public V8 invited conversation | PARTIAL; one of two adviser turns persisted after three calls | Persisted Demand turn is `references_verified`; Production return was rejected | Workflow FAIL: shared repair was consumed on Demand, then Production exceeded the content schema and was not persisted |
| Public V8 conversation Council | Not started | Not evaluated | Required workflow missing |
| Retained research replay used by scorer | PASS case; zero new inference in replay | Exact references passed | This one case does not repair the missing/failed public workflows |
| Combined quality artifact | Ten stored cases scored; six PASS, four FAIL | Several individual reference-shape checks passed | Overall `status=FAIL`, workflow integrity FAIL, semantic review PENDING |

The top-level `PASS` in `planning-public.json` means that the integrated mission,
replay and numerical replan protocol completed. It is not the advisor-quality
verdict. The mission itself records `council_evidence_status=qualitative_unverified`
and `qualitative_prose_verified=false` even though its reference gate passed.

## Public mission: what passed

The public request ran against `https://farmtact.fly.dev/v8` with mission prompt
`farmtact-mission-council-prompt-v5` and mission context V5. Six specialists ran in
the declared order, followed by the Planning Chair:

1. Demand Analyst
2. Weather Analyst
3. Market Analyst
4. Production Analyst
5. Supply Chain Analyst
6. Profit Analyst
7. Planning Chair

All seven calls returned from exact `deepseek-flash`. Each output passed the local
schema and reference-membership validator, and no local validation issues were
recorded. The required Council gate therefore reported `passed`, the backend chose
Balanced under its separate automatic-development policy, and the result was
accepted for simulation. Replay returned the same recorded events and made zero
new inference calls. A subsequent numerical-only replan made no provider call.

The mission reserved nine calls, consumed seven and released two. Recorded usage
was 80,710 prompt tokens, 639 completion tokens and 81,349 total tokens. All 80,710
prompt tokens were recorded as cache misses.

| Role | Prompt | Completion | Total |
| --- | ---: | ---: | ---: |
| Demand | 15,201 | 93 | 15,294 |
| Weather | 2,913 | 72 | 2,985 |
| Market | 9,639 | 82 | 9,721 |
| Production | 12,954 | 85 | 13,039 |
| Supply Chain | 20,509 | 85 | 20,594 |
| Profit | 8,423 | 124 | 8,547 |
| Planning Chair | 11,071 | 98 | 11,169 |

## Public mission: why quality still failed

Mission V5 replaced long canonical references in the model-facing context with
opaque short aliases such as `F001` and `C001`. The server resolved those aliases
back to the exact canonical references, which solved reference corruption at the
mechanical gate. The model-facing aliases stripped metric names and other semantic
cues, however. The server could prove which fact was selected but could not prove
that the prose described that fact's meaning.

The automated quality scorer marked four of seven mission cases PASS and three FAIL:

| Role | Automated result | Selected-fact/prose finding |
| --- | --- | --- |
| Demand | PASS | Selected confirmed-demand, booked-delivery and residual-delivery facts. The prose stayed generic but did not visibly relabel those facts. |
| Weather | FAIL: role relevance | Selected three strategy fill-rate facts, while the prose discussed feasibility and absence of hard-constraint violations. It supplied no weather interpretation and did not describe the selected metric. |
| Market | PASS | Selected three `margin_sgd` facts, but called them “booked-value totals.” This semantic relabelling was not caught by the automated PASS. |
| Production | PASS | Selected sow, transplant and harvest dates and discussed their schedule consistency. The date references fit the subject of the prose, with lead-time context supplied separately. |
| Supply Chain | FAIL: evidence and role relevance | Selected no typed facts. The prose repeated that strategies had no declared hard-constraint violations and did not provide a supply-chain-specific finding. |
| Profit | PASS | Selected cost and revenue facts, but also referred broadly to hours and output without selecting those facts and declined to state margins because it saw only aliases. The automated gate did not treat that imprecision as failure. |
| Planning Chair | FAIL: role relevance | Selected Balanced and Resilient fill rates, then said the policy required both “withholding acceptance” and choosing by preference order. The backend actually accepted Balanced. The contradiction phrase check did not detect this semantic conflict. |

The final column is AI-assisted review of the stored prose against the server-rendered
canonical facts. It should be treated as a defect hypothesis and regression-test
input, not as human expert scoring.

## Public conversation: partial execution and content failure

The public conversation used prompt `farmtact-advisor-prompt-v4` and conversation
context V4. Its replay is correctly labelled `execution_mode=replay`,
`inference_triggered=false` and `new_calculation_occurred=false`; the four actual
provider requests belong to the original public execution.

The direct stage consumed one request and persisted one Production reply. That reply
was locally `references_verified`, yet the quality scorer failed its evidence check.
It claimed that the scenario shifted harvest and shortfall figures across Lean,
Balanced and Resilient while selecting no typed facts. Its tool references covered
scenario controls, Balanced constraints and Lean status, which did not substantiate
the full three-policy quantitative comparison in the prose.

The invited stage requested two adviser turns. The Demand turn first exceeded the
content schema, consumed the one shared repair, then passed and was persisted. Its
recorded successful-output usage was 18,210 prompt tokens and 145 completion tokens;
18,048 prompt tokens were cache hits. The Production return then exceeded the
content schema after the shared repair was already consumed. The request ended
`PARTIAL`, preserved the completed Demand reply, and started no Council stage.

The completed direct reply recorded 17,824 prompt and 168 completion tokens. Token
usage for rejected provider outputs is not present in the replay, so the two
persisted-message usage rows must not be presented as total usage for all four
conversation calls.

The event record contains 14 events:

- conversation creation: one event freezing the scenario snapshot;
- direct: queued, started, one reservation, one persisted adviser message, completed;
- invite: queued, started, initial reservation, repair event, repair reservation,
  one persisted Demand message, Production reservation, then partial failure.

The automated scorer marked the persisted Demand invitation case PASS, but workflow
integrity remained FAIL because only Demand appeared where Demand then Production
were required. The Council workflow had no observed roles and also failed workflow
integrity. Direct, planning and research role/count sequences passed their individual
integrity checks; planning's sequence pass does not override its three case failures.

## Combined quality interpretation

`ai-quality-public-v8.json` evaluates ten retained outputs without new inference.
Six cases pass its automated checks and four fail:

- Production direct conversation: evidence;
- Weather mission: role relevance;
- Supply Chain mission: evidence and role relevance;
- Planning Chair mission: role relevance.

The required workflows were Council, direct, invite, planning and research. Only
direct, planning and research passed exact workflow integrity. Invite was incomplete,
and Council was absent. The resulting automated status and overall status are both
**FAIL**.

This outcome also shows the limit of the automated pass cases. Market and Profit
passed even though AI-assisted comparison found that their prose did not cleanly
preserve the meaning and scope of every selected fact. A canonical reference can be
valid while the surrounding language misnames, overgeneralizes or declines to use
it. Local reference gates remain useful for preventing invented IDs and values;
they are insufficient as semantic entailment tests.

## Corrective work and immutable-edition policy

V8 remains immutable. Its public outputs, partial conversation and failed score are
retained as the evidence for that edition.

Mission V6 is being developed for V9 to keep compact, robust selection while
restoring canonical metric meaning that V5's opaque aliases removed. Conversation
V5 is being developed for V9 with shorter content guidance and a grounded-fact
requirement when conversation prose makes a numerical claim. These changes have
not passed a provider trial and are not V8 behavior. They must not be described as
fixes until new immutable-edition evidence passes both workflow and quality gates.

## Request accounting

The cumulative ledger records **55 actual provider requests**: 44 from the retained
local experiments, seven from the public V8 mission and four from the partial public
conversation. Failed and repair calls remain counted.

The internal experiment ceiling is now 96. The next V9 verification package may
consume at most 25 additional requests, which gives a maximum cumulative reserved
total of 80 from the current 55. The unused difference between 80 and 96 is headroom,
not authorization to spend it automatically and not consumed usage.

The application's shared daily ceiling remains **48 requests**. It was not raised
by the experiment-budget revisions. The internal multi-run experiment ceiling and
the runtime daily admission ceiling measure different scopes and must not be
substituted for one another.

## Disposition

- **PASS:** immutable V8 publication, all-edition health, prior-edition preservation,
  public mission transport, seven-role sequence, local schema/reference validation,
  replay without new inference and numerical-only replan.
- **PARTIAL:** public conversation completed direct and first invited adviser turns,
  then preserved partial history after the Production return failed content length.
- **FAIL:** combined automated quality and workflow integrity.
- **PENDING:** human expert semantic review and any V9 provider validation of mission
  V6 or conversation V5.
- **UNSUPPORTED:** claims that V8 AI quality passed, that valid references prove the
  prose follows their meaning, or that these synthetic adviser outputs validate farm
  decisions.

## Additional display finding from source review

The V8 server stores `fact_refs` and code-rendered `rendered_facts`, but both
`AdvisorEvidence.tsx` and the research `ActualConversation` display read only
legacy `tool_refs`. A typed-only reply therefore omits its authoritative values
in those views even though replay retains them. This is a display integration
defect, separate from provider response quality. The V9 candidate must render
typed facts in both views and verify exact values/units and missing/unsupported
states in a browser before publication.
