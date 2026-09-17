# V17 persona-led integrated workflow rewrite

Status: V17 was published on 17 September 2026 from `e9528b2`. V18 is the next unpublished immutable correction: it makes card-detail return focus synchronous and preserves the action's visible reading position. Published V12–V17 sources and assets remain unchanged.

## User objective and evidence

Use at least three distinct persona walkthroughs of V15, including beginners and experts, to implement a clearer, engaging integrated experience. Recover relevant entry points and overviews for earlier Crops, Research, Data and other workflows. Retain real specialist-agent capabilities and assess the design against the GitHub judging rubric. Prior technical parity is not evidence of discoverability or human comprehension.

Baseline: `reports/v15/first-use-review/review.md` and exact V15 frontend `a5ab2a8`. Compare V12 `9fd5789` and V13 `30f4e97`. GitHub API confirmed the organizer PDF still has blob `b5a05dc8e0b849d9f8b1566cbd865151984a1730`; page 13 is transcribed in `reports/panel/judging-rubric.txt`. Its seven criteria have no official weights or numerical scale.

Three scripted AI personas: novice farm manager on mobile, experienced planner seeking direct access on desktop, and agent architecture/evaluation judge using keyboard and evidence. Observations must distinguish actual interaction from design hypotheses and technical inspection. No real-user testing is claimed.

## Required outcome

- One ordinary sandbox, one card/action-area shell, progressive skippable/resumable guidance and full expert access.
- Visible named entry points and scanable indexes for all five groups. Crops have a searchable atlas and precise profile/evidence entry. Research and Data regain clear purpose, overview and sequence.
- Explicit selected-order versus all-demand scope, preview versus save, reservation purpose/date window, approval versus simulation, and meaningful next actions.
- Finite replayable demonstrations explain saved facts and transitions. Reduced motion conveys identical facts. No invented farm stage, relocated allocation, success, or autonomous growth.
- Direct advisers, invited specialists, conversational Council, planning Council, saved threads, cited facts, validated frozen focus, partial/withheld results and discussion-to-reviewed-proposal flows remain available. Reading and navigation do not invoke inference.
- Contextual tools restore their exact origin/focus/scroll; expert jumps do not require tutorial completion. Preserve revision, stale/duplicate protection, tenant isolation, recoverable drafts, API quotas and provider budgets.
- Preserve all V15 capability checklist workflows. Reuse numerical and provider services; no new agricultural model or physical farm authorization.

## Ownership

Root: contracts, IntegratedApp adapters, History/help integration, edition identity, specifications, integration/regression, release and preservation.
`card_shell`: IntegratedCards.tsx/CSS, first-use shell, tool index, contextual navigation and demonstration.
`workflow_cards`: IntegratedKnowledge/Experiments/Research and their styles, atlas/categories/overviews, agent preservation.
`parity`: three persona evidence reports and browser acceptance journeys. No recursive delegation.

## Acceptance and rubric mapping

1. Goal & Scope Definition: novice can locate objective, its scope and next decision; optional experiments are identified.
2. Architecture & Reasoning Loop: inspect → alternatives → reviewed change → local calculation → saved consequence; bound state/history visible.
3. Tool Use & Integration: every earlier capability remains reachable and completes through current cards; contextual crop/data/agent entry preserves identities.
4. Autonomy & Human-in-the-Loop: no automatic inference, review and explicit submit/apply, separate approval and simulation.
5. Safety, Security & Guardrails: unchanged provider/admission boundaries, validated focus, tenant/revision/idempotency and no real operations.
6. Observability & Evaluation: saved citations and withheld findings, replay, before/after facts, scenario comparisons, persona and adversarial evidence.
7. Platform & Tooling Usage: existing typed contracts, seven-role orchestration, purpose-fit tools and complete agent workflows; no decorative replacement.

Verification includes real browser journeys at 360/390/430/desktop, keyboard/scroll/text zoom/reduced motion, normal-motion recordings, interruption/reload/error recovery, complete agent-flow preservation checks, generated contracts/build and measured bundle, full isolated PostgreSQL regression, immutable candidate/public verification before any replacement. Automated completion is not human comprehension or new provider-prose-quality evidence. Any required live-provider testing must be explicitly bounded and use existing admission without reset or fallback.
