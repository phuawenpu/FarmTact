# V7 research: conversation as a playable farm council

Research cutoff: 9 September 2026 UTC (10 September in Singapore). This is a targeted interaction review, not a human usability study. The application observations come from the v6 baseline audit at 360, 390, 430, and 1280 CSS pixels. The literature findings below are separated from FarmTact hypotheses.

## What the briefs require, and what the team prefers

Page 13 of the official hackathon briefing evaluates: goal and business scope; architecture and reasoning loops with explicit state and memory; purpose-fit, typed tool integration; risk-calibrated autonomy and human escalation; safety and least privilege; observable decisions and adversarial evaluation; and clean multi-agent platform use. It does **not** require seven visible speeches, a chat-first layout, artificial disagreement, or a particular visual metaphor.

Sumin Lee's seven-page product thesis makes a separate product argument: production planning is coordination among demand, weather, market, production, supply-chain, and profit perspectives, resolved by a Planner; changing a scenario should make that organization visibly adapt. It warns against a generic farming chatbot, seven vague outputs, a beautiful dashboard without a decision loop, and a literal farming game. Its line about making agents disagree is best treated as a demonstration prompt, not permission to fabricate conflict. Disagreement is useful only when attributable evidence or constraints actually conflict.

### Short gap map

| Capability | V6 observation | Classification | Treatment |
|---|---|---|---|
| Frozen state, replay, bounded proposals, typed numerical planning, and automatic development-phase simulation acceptance | Present in code and visible scenario/conversation flows | Already present | Preserve the numerical and state boundaries; distinguish the backend policy actor from an explicit research-participant choice. |
| Address one specialist, invite another, or convene the council | Visible at every audited width | Already present | Preserve targeted participation. Do not require the full council for a follow-up. |
| Selected-bed context | The panel labels `A1 · caixin`, but the baseline check could not verify a durable contextual object control | Needs reinforcement | Add a removable, inspectable context representation linked to the board. |
| Conversation-to-plan consequence | Five bounded proposal controls can open the scenario lab, but the test task's bed reservation and order-confirmation changes are absent | Needs reinforcement | Add explicit proposed operations, confirmation, version creation, and linked deltas. |
| Farmer challenge and evidence resolution | Free text and evidence affordances exist, but unresolved/rejected challenges have no compact lifecycle | Needs reinforcement | Represent the challenged claim, evidence state, response, and whether it blocks selection. |
| Shared council representation | A roster and recorded messages are present | Needs reinforcement | Show outstanding questions, agreed constraints, and tool results; avoid a second general-purpose dashboard. |
| Repetition and participation policy | Full council is user-triggered; selective invite exists. No visible rationale for who should speak next | Missing | Let the Planner/moderator call only materially relevant roles and explain omissions. |
| Bed/date reservation and confirmed/unconfirmed order semantics | Absent from current experiment controls in the baseline audit | Missing | Implement only inside the isolated research scenario until numerical semantics are verified. |
| Voice | Device-keyboard voice-typing guidance is present | Already present | Leave alone; voice remains optional and no recording/transcription service is needed. |

## What the research supports

### Participation and moderation

Co-STORM lets users observe an automatically advancing multi-agent discussion and jump in at any time. It maintains a dynamic mind map and uses a moderator to inject questions based on unused retrieved information and already-covered concepts ([Jiang et al. 2024, PDF pp. 2–5](https://aclanthology.org/2024.emnlp-main.554.pdf)). In its automatic ablations, removing the moderator hurt discovery-oriented discourse more than removing multiple experts; one expert plus a moderator retained much of the measured benefit (PDF pp. 6–7). In the 20-person human comparison, participants were encouraged to participate rather than only watch; Co-STORM improved self-reported engagement and supported discovery, while the authors report mixed feedback about information density and mind-map usability (PDF pp. 7–9 and appendices). The study concerns open-domain learning, uses simulated users for much of the automatic evaluation, and does not establish that a farm council improves planning decisions.

FarmTact hypothesis: combine continuous availability to steer with **designated safe boundaries** after a claim or tool result. An interrupt stops future contributions; it does not pretend an in-flight provider request was cancelled. A moderator should nominate only roles whose evidence or responsibility can change the decision.

### Conversation as consequential action

Façade structures interaction into beats with a canonical sequence, short one-to-five-line joint dialogue behaviours, and beat-specific “mix-ins” that respond to player discourse acts before reconnecting to the sequence ([Mateas and Stern 2005, PDF pp. 3–4](https://users.soe.ucsc.edu/~michaelm/publications/mateas-aiide2005.pdf)). It shows how a contribution can alter subsequent events without requiring unconstrained story generation. This is an architecture account of one authored interactive drama, not evidence that scripted dramatic pacing transfers directly to decision support.

FarmTact hypothesis: use short planning episodes—question, acknowledged operation, calculation, consequence, review—while avoiding scripted suspense and forced disagreement. The meaningful “game score” is a traceable change in feasibility, shortfall, labour, cash, margin, or unresolved evidence.

### Direct selection plus language

DataBreeze combines direct manipulation with natural language so one modality can supply targets or parameters omitted by the other. Its design uses simple touch/pen actions, visible speech feedback, and ambiguity widgets; a selection can provide the referent for a later command ([Srinivasan, Lee, and Stasko 2020, PDF pp. 6–9](https://arxiv.org/pdf/2004.10428)). Its formative work and proof-of-concept focus on a large pen/touch display and speech. It does not test FarmTact's phone layouts, typed conversation, agricultural semantics, or long-lived scenario state.

FarmTact hypothesis: explicit object selections should be removable and inspectable. If “these,” “it,” or “later” maps to zero or multiple valid objects/windows, present choices instead of guessing.

### Interpretation and execution

TalkToModel separates a dialogue engine that parses language into a constrained executable representation, an execution engine that runs analytical operations, and a response layer grounded in those outputs ([Slack et al., 2023 version, PDF pp. 3–7, 11–16](https://arxiv.org/pdf/2207.04154)). It represents previous filters and operations explicitly to resolve follow-ups. Its user study compared its conversational model-explanation interface with a dashboard among 45 healthcare workers and 13 ML professionals; the conversational condition completed more questions correctly and received stronger ease, confidence, speed, and preference ratings (PDF pp. 7–10). This system explains predictive models and uses a defined grammar; it does not validate free-form farm operations or autonomous multi-agent planning.

FarmTact hypothesis: parse dialogue into a visible proposed operation. Explanations read a frozen result; accepted input mutations create a new scenario version; comparisons run only after compatible numerical results exist. The language model cannot write authoritative quantities into results.

### Challenges and mixed initiative

Madumal et al. derive an explanation dialogue protocol from 398 collected dialogues across six dialogue types, then evaluate its fit with 14 participants across 101 human-agent explanation dialogues. Their protocol permits clarification, follow-up, and embedded argumentation—an explainee can counter a claim and then return to explanation ([Madumal et al. 2019, PDF pp. 3–8](https://arxiv.org/pdf/1903.02409)). The source dialogues include scripted scenarios and the evaluation measures dialogue-model fit, not correctness of evidence or farm decisions.

Horvitz argues that mixed-initiative systems should reason about uncertainty in user goals, attention, expected costs and benefits, use dialogue for key uncertainties, minimize the cost of poor guesses, scope precision to uncertainty, and retain interaction history ([Horvitz 1999, PDF pp. 1–2, 6–8](https://erichorvitz.com/chi99horvitz.pdf)). Its LookOut examples illustrate the principles in calendar assistance; they do not yield numerical thresholds for FarmTact.

FarmTact hypothesis: low-cost ambiguity can remain a labelled assumption; ambiguity that changes an input, comparison root, feasibility, or approval target requires clarification. Silence and agent consensus never count as farmer approval.

### Transitions as explanation

Heer and Robertson found appropriately designed animated transitions could improve graphical perception. Their principles preserve valid graphics, avoid semantic ambiguity, use simple predictable motion, stage complex changes, and keep transitions only as long as needed; their controlled studies also show task-dependent trade-offs and do not make animation universally beneficial ([Heer and Robertson 2007, PDF pp. 1–4, 6–8](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/InfoVis2007-DynaVis.pdf)). W3C's WCAG 2.2 explanation for SC 2.3.3 says non-essential interaction-triggered motion must be disableable at Level AAA and recommends avoiding it, providing a control, or respecting the user-agent reduced-motion preference ([W3C 2023](https://www.w3.org/WAI/WCAG22/Understanding/animation-from-interactions.html)).

FarmTact hypothesis: motion can direct attention from the speaking agent to affected objects and then to deltas, but persistent numbers and a static before/after view carry the meaning. Reduced motion substitutes instant highlight and state changes rather than removing information.

## Annotated council flow

```text
Farmer selects Bed 4 + order 17
  → UI stores visible context chips [farmer/direct manipulation]
  → Farmer: “Could these cover the later delivery?” [ask]
  → Interpreter proposes: compare Bed 4 harvest with order 17 due window
  → If “later” is ambiguous, UI asks which delivery [clarification; no tool]
  → Numerical lookup checks dates, shelf life, allocation and capacity [local tool]
  → Production or Supply Chain speaks only if its evidence changes the answer
  → Board highlights Bed 4/order 17; result card cites exact records [shared visual state]
  → Planner states answered facts, assumptions, and one outstanding choice [moderator]
  → Farmer: “Keep Bed 4 free from 21–28 Sept” [constraint]
  → UI previews a typed reservation operation and asks farmer to apply it
  → Accepted operation creates scenario version N+1; solver runs [local tool]
  → Quantities transition to new values; old/new deltas remain visible
  → Relevant specialist may challenge evidence; others abstain visibly or remain silent by policy
  → Planner compares current compatible versions and asks farmer to choose
  → Explicit “Choose this simulated version” records selection; no farm operation occurs
```

Continuous participation is available whenever the composer is enabled. Designated intervention boundaries occur after a specialist claim and after tool completion. This gives the farmer control without allowing mid-result messages to corrupt version identity. The moderator contributes only when it can clarify, introduce uncovered material evidence, resolve a recorded disagreement, or close the episode.

Repetition control should use structured discourse state: covered question, cited records, operations already run, unresolved claims, and roles already heard. A role speaks only when it adds a new material claim, cites different evidence, challenges a premise, or changes the next operation. Otherwise it abstains without generating a decorative message.

## A 45-second interaction storyboard

| Time | Farmer and council | Board and state consequence |
|---:|---|---|
| 0–5s | Farmer taps Bed 4 and an order, then asks, “Could these cover the later delivery?” | Two removable chips appear; linked objects receive a static focus outline. |
| 5–10s | The interface asks which of two later orders is meant. Farmer taps the intended order. | The ambiguous chip is replaced by an exact order/date chip. No scenario changes. |
| 10–17s | Production acknowledges the question; a local allocation check runs. | Tool status names the operation. Farm time remains fixed. |
| 17–23s | Result: Bed 4 contributes a stated quantity but leaves an exact shortfall. | The board preserves before values and reveals persistent quantity deltas with record links. |
| 23–29s | Farmer says, “Keep Bed 4 free from 21–28 September.” | A proposed reservation card shows bed and inclusive dates; farmer applies it. |
| 29–38s | Solver creates version N+1. Only specialists affected by capacity, delivery, or margin contribute. | Bed 4 changes to reserved; comparison shows feasibility, shortfall, labour, cash and margin. |
| 38–45s | Farmer challenges one assumption, opens evidence, then chooses or rejects the current simulated version. | Challenge stays unresolved/resolved/rejected; selection is blocked only if the matrix says it must be. |

The timings are interface pacing targets, not a promise about provider or solver latency. A slow operation leaves the episode resumable and clearly says that farm time is not advancing.

## Two lightweight selection alternatives

### Alternative A: removable context chips

Tap a bed, crop, order, or harvest window; the composer displays compact chips with name, date, and type. Tapping a chip refocuses the object, and its remove button has a labelled keyboard/touch equivalent. The sent message stores immutable object IDs and snapshot version. Context persists across replies until removed or invalidated by a version change. This is strongest for multi-object questions and precise correction, but chips can consume phone space.

### Alternative B: contextual reply card

Tap an object and choose **Ask council**. A small card above the persistent composer contains the object, suggested actions, and the latest relevant council claim. Replying automatically binds the object and cited claim; “Add another object” permits comparison. This reduces clutter and makes challenges natural, but multi-object context is less visible and requires an explicit context summary before send.

Both alternatives use typed conversation first, device-keyboard voice optionally, explicit ambiguity choices, board highlights, keyboard-accessible controls, and no gesture-only action. The research prototypes should compare them rather than combine them prematurely.

## Intent to execution mapping

| User intent | State change | Tool invocation | Visible result |
|---|---|---|---|
| “Why less lettuce?” | None; retain frozen result and referenced plan version | Evidence/result lookup only | Explanation card cites the exact strategy metrics, constraints and inputs. |
| “What changes if the customer confirms?” | Show proposed `order_confirmation` operation; apply creates N+1 | Re-run numerical planner after confirmation | Pending → calculating → completed version with persistent deltas. |
| “Compare again without extra labour.” | Proposed labour setting on a branch from the same root | Validate input, solve, then compare compatible results | Comparison identifies changed assumption and feasibility/deltas. |
| “Keep Bed 4 free.” | No mutation until reservation dates are known and accepted | No solver during clarification; solve after acceptance | Date question, then proposed operation and board reservation. |
| “This is indoors; why does rainfall matter?” | Create challenge linked to the rainfall/yield claim | Evidence lookup; planner only if a corrected input is accepted | Claim becomes resolved, unsupported, or an explicitly labelled assumption. |
| “Ask Production, not everyone.” | Add a targeted council turn to the same frozen context | At most the requested provider role; no numerical rerun unless needed | One attributed response and any referenced tool result. |
| “Use this plan.” | Record explicit selection of the current completed version | Backend policy validates currency, ownership, compatibility and feasibility | Chosen **simulated** version; actual farm operations remain disabled. |

Context that persists: tenant and edition, research session, frozen baseline/root hash, scenario/result version, selected object IDs, accepted operations, unresolved claims, tool-result references, and explicit selection/rejection. Ephemeral prose, hover state, and animation progress do not become authoritative state.

## Clarification and escalation matrix

| Condition | System response | May calculate? | May choose simulated version? |
|---|---|---:|---:|
| One safe referent; no material input change | State the interpreted referent and answer | Yes | Yes |
| Multiple beds/orders/windows match “this/later/these” | Offer exact choices; do not guess | Only non-mutating lookup | No affected mutation until clarified |
| Missing low-impact contextual fact | Label assumption and show correction action | Yes, if result labels it | Yes, unless policy declares it material |
| Missing value that changes constraint, quantity, comparison root, or target | Ask a bounded question | No mutation | No |
| Farmer corrects an assumption | Preview typed change; create N+1 only after apply | After apply | Yes if checks pass |
| Farmer challenges an evidence claim | Show evidence, source state, and agent response; preserve counterargument | Lookup yes | Yes unless the challenged claim is required for feasibility/safety |
| Evidence absent or stale | Mark unsupported/stale; do not turn consensus into support | Deterministic what-if may run with labelled assumption | Block only when required input or safeguard depends on it |
| Specialists disagree | Planner identifies exact conflicting claims and requests evidence/tool resolution or farmer preference | Yes when a tool can adjudicate | No if material conflict remains unresolved |
| Plan infeasible | Preserve result and violations for inspection | Comparison yes | No under existing acceptance policy |
| Recommendation rejected | Record rejection and rationale; do not re-offer unchanged | Yes for a materially changed branch | No for rejected version |
| No response or farmer silence | Keep pending state | Existing computation may finish | Never counts as approval |

## Event-to-feedback map

| Event | Meaningful feedback | Motion-enabled | Reduced-motion equivalent |
|---|---|---|---|
| Agent raises a concern | Speaker emphasis, claim card, evidence status | Brief emphasis then path to object | Instant emphasis and focus outline |
| Object reference resolves | Exact context chip/card and object focus | Short shared-color connection | Simultaneous static highlight |
| Tool starts | Named operation, frozen version and status | Restrained progress indicator | Text status; no looping spatial motion |
| Tool completes | Persistent before/after values and evidence links | Stage object highlight, then changed values | Instant state swap plus “changed” badges |
| Values change | Signed deltas remain available | Simple predictable interpolation, about one second where useful | Static old/new columns |
| Claim becomes stale after N+1 | Stale badge and link to original version | Gentle opacity change only | Immediate badge change |
| Decorative council presence | Optional portrait idle state | Ambient motion only when enabled | Static portraits |

Animations never encode a value unavailable elsewhere. Current observations, stale records, forecasts, and simulations use persistent labels and visual treatments; motion only directs attention between them.

## Provisional recommendations

These are candidates pending the full browser concept evaluation; they are not claimed as established FarmTact usability improvements.

1. **Context-bound conversational operations.** Research basis: DataBreeze's selection-language complement and TalkToModel's parse/execute separation. Observed v6 gap: selected bed is named but not a durable removable control, and bed reservation/order confirmation are absent. Proposed interaction: object chips or reply card → visible proposed operation → accept → versioned numerical result. Smallest experiment: the Bed 4/order task in an isolated scripted research session. Success: correct referent and operation, no silent mutation, user identifies the resulting shortfall and current version. Effort: high because numerical semantics and persistence are required. Limitation: cited studies do not establish agricultural correctness or phone usability.

2. **Selective, steerable council with an outstanding-issues map.** Research basis: Co-STORM's user steering, moderation and dynamic shared representation; Sumin's business-role thesis. Observed v6 gap: targeted invite and full council exist, but the UI does not explain speaker selection or compactly preserve unresolved issues. Proposed interaction: safe turn-boundary steering, role nomination by material relevance, and shared constraints/questions/evidence state. Smallest experiment: compare one targeted path with one full-council path on identical frozen inputs. Success: fewer redundant contributions while preserving every material conflict and enabling successful correction. Effort: medium. Limitation: Co-STORM studies learning, not farm-plan quality; benefit needs FarmTact testing.

3. **Challenge-to-evidence lifecycle with persistent consequences.** Research basis: Madumal's embedded argumentation and Horvitz's uncertainty-sensitive dialogue. Observed v6 gap: free-text/evidence affordances exist, but a challenge does not have a visible resolved/unsupported/blocking state. Proposed interaction: **Show evidence**, **Correct assumption**, and **Consider another option**, each linked to a claim and frozen result. Smallest experiment: challenge the indoor-rainfall claim, correct it, and verify whether a new version is necessary. Success: user can state the final evidence status, no consensus substitutes for evidence, and material unresolved claims prevent selection. Effort: medium. Limitation: deciding which domain uncertainties block selection requires policy validation beyond the cited dialogue research.

## Evaluation limits

The current evidence supports interaction mechanisms, not a winning mobile layout. The v7 comparison must use identical synthetic inputs and scripts across inline council, expandable sheet, and contextual-card arrangements; presentation order should rotate. Its novice pass should begin without advance instructions and record whether one clear starting action and the next step are discoverable, whether selected context remains visible beside the composer, and whether engineering language blocks progress. The first meaningful planning choice within 30 seconds is a future human-test target, not a claimed result. Layout controls belong behind an optional **Compare research layouts** action so they do not precede the farm task. Completion time, correction success, feasible-current-version selection, evidence comprehension, recovery from ambiguity, and wrong actions are measurable in automated/AI walkthroughs. Enjoyment remains a future human-participant measure. Desktop mobile emulation cannot establish physical keyboard, touch ergonomics, or lived accessibility.
