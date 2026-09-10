# FarmTact v6 interaction baseline

Audit date: 2026-09-09 UTC. Published baseline: `v6` from the live
`/api/releases` registry. The browser audit used a fresh synthetic tenant and
submitted no messages, invitations, councils, scenarios, planning runs,
acceptances, or provider requests. Opening the advisor panel created only the
empty, frozen conversation record needed to inspect the interface.

## Short gap map

| Area | Status | Observed v6 behaviour | Preserve, improve, or leave alone |
|---|---|---|---|
| Business purpose and visible specialist roles | Already present | Seven named advisors have distinct Demand, Weather, Market, Production, Supply Chain, Profit, and Planner roles. The board makes their locations and farm focus visible. | Preserve. It already expresses Sumin Lee's organizational thesis and rubric goal/scope criterion. |
| Numerical reasoning loop | Already present | A dated supply-gap mission leads to a three-step Scenario Lab and Lean/Balanced/Resilient comparison. Farm time and calculation time are explicitly separated. | Preserve. Conversation experiments must continue to call the numerical path rather than invent quantities. |
| Frozen state and replay | Already present | Conversations identify a frozen farm/scenario and optionally one selected bed; saved discussions and replay are visible. Editions retain independent state. | Preserve the snapshot identity and stale-state warnings. |
| Human oversight | Already present | Proposed supported controls enter an experiment; unsupported advice cannot authorize a change. Simulation selection remains separate from real operations. | Preserve. Add explicit review of interpreted changes before calculation. |
| Evidence and observability | Needs reinforcement | Messages distinguish checked references from unverified interpretation and can expose evidence/tool references. Evidence is mostly inside message details and plots are linked only when the response supplies highlight references. | Keep validation labels but connect messages, selected objects, calculations, and persistent deltas more directly. |
| Farmer participation | Needs reinforcement | The farmer can address one advisor, reply to a specific message, invite another advisor, or convene all seven. During a bounded response all send/invite/council controls are disabled. | Add safe turn-boundary steering and selective participation. Do not require every advisor to speak. |
| Contextual conversation | Needs reinforcement | Selecting A1 then choosing **Ask Mei** opens `Current context: A1 · caixin`. The context is plain text, limited to one bed, and cannot be removed or extended with an order/harvest window. | Add explicit removable object references and clarify ambiguous pronouns before executing. |
| Conversation-to-state mapping | Missing | Existing proposed actions map to scalar scenario controls. `Keep Bed 4 free` and changing order confirmation are not supported controls. | Add typed experimental operations with visible proposed edits and new frozen scenario versions. |
| Challenge and correction protocol | Missing | Free text and **Show me the evidence** exist, but there are no contextual **Correct assumption**, **Consider another option**, or unresolved/rejected recommendation controls. | Add small explicit challenge actions and states; evidence, not consensus, resolves factual disputes. |
| Reading continuity | Needs reinforcement | The transcript uses `scrollTo(...scrollHeight, behavior: 'smooth')` whenever message count changes. This can pull a reader away from an earlier message. | Auto-scroll only when already near the end; otherwise show a new-update affordance. |
| Mobile composition | Needs reinforcement | At 360/390/430 px the panel becomes a bottom sheet, the composer and send target are at least 44 px, and device-keyboard dictation is explained. Selected board context is hidden behind the modal sheet. | Compare layouts that retain selected context while typing and viewing evidence. Physical keyboard/dictation testing remains necessary. |
| Motion | Already present | Reduced-motion preference is detected and audited; screenshots disable animation. | Leave ambient motion alone. Use restrained, optional transitions only for causal state changes and retain final deltas. |

## Brief alignment

The official briefing page 13 asks for goal and scope, an architecture and
reasoning loop with explicit state, purpose-fit tools and schemas, calibrated
human oversight, safety, observability/evaluation, and clean multi-agent
orchestration. V6 visibly supports much of this foundation. The largest product
gap is not another advisor or dashboard: it is making a farmer's conversational
act become a reviewable state transition whose numerical consequence remains on
the board.

Sumin Lee's brief asks users to change a scenario and watch specialist
perspectives produce a revised plan. V6 supports scenario changes and council
conversation, but the two are joined only through a narrow proposed-action
handoff. The next experiment should strengthen that joint without manufacturing
debate: relevant specialists contribute when their evidence or responsibility is
affected, and the Planner identifies unresolved trade-offs.

## Evidence and limitations

The companion JSON contains live checks and request observations. Screenshots in
`apps/web/screenshots/v7-baseline/` cover the farm board, selected bed,
bed-scoped conversation, and unopened Scenario Lab at 360, 390, 430, and 1280
pixels. Code inspection confirms the message-count auto-scroll and busy-state
control behavior; no paid response was invoked to manufacture these states.

Responsive results are headless Chromium emulation, not a physical phone. The
software keyboard, keyboard occlusion, native device dictation, touch accuracy,
audio, provider response pacing, and active-request interruption were not
observed. These must not be represented as passed human or hardware tests.
