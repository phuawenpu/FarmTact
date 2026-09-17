# V15 proposal: one farm table, full planning depth

Status: implementation in progress, 17 September 2026. Requested after the live V14
animation/explanation and functionality review. Nothing in this document claims
implementation, validation, publication or permission to change a published edition.
V14 remains immutable. A future implementation uses a new feature branch and a new
numbered release after acceptance. Historical source, images and private state stay
preserved; old public editions are not restored.

Evidence: [live review and capability comparison](../reports/v14/animation-explanation-review.md).
The [V13 asset and workflow reuse map](v15-v13-reuse-map.md) identifies exact reusable
SVGs/components, prior implementation limits and additional acceptance A12–A14.
This proposal supersedes V14's **beginner-only application entrypoint**, not its
isolation, numerical authority, abuse protection or single-interaction-model rules.

## 1. Product idea and gameplay

One farm table: **read the situation → swipe to compare → use the action area →
watch the recorded consequence → inspect why → make the next decision.**

The farm scene explains the selected card; it is not another navigation system.
Cards are different views of real records and decisions, not collectible rewards.
Success means meeting an explicit order/resource objective, understanding its
tradeoffs and preserving an auditable record. No points, streaks or fabricated wins.

The beginner lesson teaches the same controls used for the full sandbox farm.
Completing a tutorial must not be the end of the product. Simplify access to the
existing capabilities rather than replacing them with explanatory placeholders.

One ordinary tenant-owned sandbox farm serves beginners and returning users. Start
with the general demo records; introduce one order while retaining all demand in
calculations. Versioned guidance belongs to the ordinary planning session and never
copies farm state. Guidance is skippable/resumable and unlocks no capability.
Importing another farm requires an explicit reviewed transition. There is no
separate teaching fixture, lesson product, advanced mode or old-interface escape.
Every card labels simulation and disabled real operations. Historical edition data
is never silently migrated.

## 2. One interaction grammar, not a new screen maze

**UX-01** The shell always has an objective, noninteractive 2.5D scene, one active
card and one action area immediately below the card. On desktop, scene and compact
card/action column sit alongside each other; do not stretch the card into a large
dashboard. No independent Council sidebar, bed hotspots, top-level tabs or room menu.

The action area contains Previous/Next and a named deck counter, followed by at most
three contextual action keys. The emphasized center is the primary action.

- Decision: **Explain / primary verb / More**.
- Detail: **Back / inspect or advance detail / Ask**, replacing Ask with More when
  no validated conversation focus exists.
- Form/review: **Back / Review or Confirm / Details**. Editing a field never submits.
- Pending: **Details / non-actionable status / More**. Browsing remains possible;
  duplicate writes are disabled. Cancel is offered only where the server supports it.

Swipe and arrow keys change selection, never commit. Enter invokes the primary only
when focus is in the navigation/card surface, not while editing or on another native
control. Previous/Next, Back, context switching, pagination, motion settings and
replay all use this same area. Links, source opening and downloads are explicit
actions there; cards may contain selectable text and accessible input fields.

**UX-02** Explain opens a small contextual deck, not an ever-growing paragraph that
pushes the action below the fold. Breadcrumb: “Recovery › Why”; counter: “Reason 1
of 3,” not an anonymous fraction. Back restores the exact parent card, scroll,
selection and focus. Explanation/detail decks are at most two levels deep.

More starts with contextual actions and one “Farm tools” entry. Farm tools is a
five-card index: **Plan**, **Records & work**, **Knowledge & evidence**,
**Experiments**, **History & preferences**. Primary opens that tool's card deck.
Each leaf deck contains real available capabilities, not inert summaries. At most
seven cards per page; explicit page actions preserve total counts and position.
Every parity capability below must have a documented path and no more than three
explicit opens from the farm-tools entry. No mandatory linear tour of all tools.

**UX-03** At 360×800, 390×844 and 430×844 at default text size, core decision cards
must show their title, one-sentence consequence, up to three headline facts and all
three action keys without page scrolling. Fit by shortening/splitting content and
compacting the scene, not by reducing readable text or targets. At 200% text zoom,
use normal document scrolling; no clipping, nested scroll traps or covered controls.
Normal flow remains default. Sticky variants need separate safe-area/keyboard tests.
Offscreen consequences remain available as text and through Replay change.

## 3. Teach the controls and decision, not just the theme

**LEARN-01** Replace the three thematic intro illustrations with an authored,
clearly marked “Illustrated example · not your farm” demonstration using the actual
card/action grammar. It must work without creating a session or calling a provider.

1. **Promise:** show an example customer order, amount and due date, and the goal
   “Deliver what you promised.” Explain that saved simulated time advances only by
   explicit action, not while away.
2. **Compare:** demonstrate swiping between two genuinely different illustrated
   layouts, with a visible “Preview—not saved” badge. One plan saves space but falls
   short; the other covers the example order at greater resource cost. Label all
   illustrative figures as examples; do not imply they are the player's calculation.
3. **Act and inspect:** user presses “Try example action.” Show a finite consequence
   and the Explain key revealing cause/effect. Then offer Start first lesson. This
   practice is local illustration, not a saved farm action. Skip remains available.

**LEARN-02** The real lesson first card names the customer's request, the starting
crop, remaining growing time and the immediate next move in plain language. Before
choosing, the learner can answer “what do I gain, what do I give up, what is uncertain?”
Feasible means technically allowed, not necessarily enough to fulfil the order.
Display shortfall directly and never celebrate feasibility as fulfilment.

Every advance shows the current date, target date, why the simulation stops there,
and what can change. A no-event checkpoint says so. Preserve bounded server advances;
do not invent intermediate decisions just to make clicking feel active. A later
optional “Advance to next decision” needs its own explicit server contract and must
stop at every required intervention. Do not silently introduce autoplay.

Delivery cards must use delivery-stage copy and recorded quantities, not the initial
“compare two plans” instructions. Distinguish the ledger's recorded delivery from
the user's subsequent review acknowledgement. Debrief separates predicted outcome,
recorded simulation outcome, changed decisions, uncertainty and next available action.

## 4. Explainability is a first-class deterministic feature

**EX-01** Each decision/result exposes server-authored or locally deterministic
structured explanation, tied to the frozen result, with these ordered cards:

1. **What this means:** action/decision, exact affected entities and dates, before
   and after facts with units, scope and projection/recorded labels.
2. **Why / tradeoff:** binding constraint, changed allocations and alternative
   outcome from a compatible calculation; separate correlation from proved cause.
3. **Evidence / limits:** source record, observation/retrieval time where applicable,
   assumptions, freshness, missing information and exact record identity.

Provenance answers “where from,” not “why.” Repeating the card summary or saying
“beginner-teaching-farm-v1” does not satisfy Explain. If the server lacks causal
evidence, say “Reason not available for this saved result” and show the facts it does
have. No invented rationale, implicit AI completion or claim that a strategy name
proves it is safer/cheaper. Headline and detail rounding must agree or explicitly
mark approximation; retain full server precision in record details.

**EX-02** Choice comparisons use the same baseline, horizon, demand scope and
scenario. Show server-derived signed changes for delivery, shortfall, space, cost and
other available metrics. Unsupported or incompatible comparison is disabled with a
reason. A maintenance explanation identifies B3, the unavailable date interval,
affected future allocations, what remains executed, and the recalculated changes.
Do not hard-code the observed fixture's cost/delivery values into presentation logic.

**EX-03** Keep an open explanation associated with its cause across a save; show
“Result of your choice” when the response arrives. Retain a complete event/history
deck, not only the final four messages. Each event opens its original explanation,
snapshot and recorded state; replay never invokes the planner/provider or writes.

**EX-04** Adviser cards retain the question, ordered thread, role, cited facts,
validation/withheld state, frozen focus and recorded answer. “Read saved answer” is
not “Ask again.” Do not downgrade card-grounded questions to generic Asha context
silently: show the actual validated focus or disable unsupported focus with a reason.
Council is optional specialist review, not a mysterious required game system.
Introduce it as “Ask specialists to review this plan,” with cost/quota implications
before explicit submission. Read existing findings without inference.

## 5. Restore capability, progressively, in the same shell

**PAR-01** The integration target is capability parity, not re-exposing old rooms.
Reuse existing services/contracts. These are release acceptance items, even when
optional for a learner. Backend availability alone is not user-facing completion.

| Earlier capability | New card/deck and primary action | Required depth and safeguards |
| --- | --- | --- |
| Farm setup/import | Records & work → Farm records → Load demo / Review import | Validated JSON, preview errors and explicit commit; version, data origin, tenant isolation |
| Orders, tentative demand, beds, inventory, accounting | Records & work → entity cards → Inspect / Review change | Real records, units, dates, reported versus projected; correction targets and signed deltas retained |
| Crop library and sources | Knowledge & evidence → crop/source cards → Inspect evidence | Profiles, supported recipes, warnings, citations and freshness; unsupported crops remain accounting-only |
| General planning and allocation board | Plan → objective/strategy cards → Calculate / Compare | Lean/Balanced/Resilient where supported; allocation schedules, yield, resource/cost facts; noninteractive scene plus bed detail cards |
| Reviewed Inbox and photo evidence | Records & work → candidate/evidence cards → Review | Accept/reject with existing validation; uploaded observation is not truth or authority to alter yield |
| Assumption proposals and approvals | Plan → proposal → Review / Apply & recalculate → result → Approve for simulation | Separate proposed, applied and approved states; job status, revisions, idempotency and trace to source discussion |
| Reserve-space inverse | Plan → active constraint → Review inverse | New inverse proposal at current eligible revision, stale reason, recalculation; never erase history |
| Sandbox tasks, results, corrections, recovery | Records & work → task/result cards → Record / Review correction | Existing event/checklist/quantity invariants; executed work retained, only future work replanned; no real operations |
| Council and contextual conversation | Knowledge & evidence → specialist/review cards → Submit question/review | Existing roles, transcript, evidence, withheld/partial findings, frozen focus, request budget and explicit provider admission |
| Branches, quests, numerical comparison | Experiments → scenario/objective cards → Preview / Compare | Frozen root/hash, compatible baselines, isolation and existing server eligibility |
| Data Explorer, generated datasets, forecasts, exports | Experiments → dataset/forecast cards → Preview / Save / Export | Existing charts/tables within cards, dataset provenance, EWMA parameters, immutable snapshots and permitted exports |
| Research and reviews | Experiments → study/review cards → Run local study / Request interpretation | Study version/hash, source refs and limits; numerical runs separate from explicit optional provider interpretation |
| Waste Rescue | Plan → eligible surplus card → Compare options | Dated surplus, lot/expiry and numerical result; never authorizes sale, donation or disposal |
| Saved lessons, plans, scenarios, discussions and audit history | History & preferences → saved entity cards → Open record | Exact identity/version, full event sequence, no recalculation/inference on replay; new attempt distinct from reading old one |
| Accessibility, motion, intro replay and existing audio preferences | History & preferences → preference cards → Apply / Replay intro | Persistent per-edition preferences; preserve applicable existing audio controls, no new recording/transcription integration |

Optional does not mean hidden behind completing both lessons. Contextual prompts can
introduce a tool when useful; the tools index remains available to experienced users.
No “go to old version” escape hatch. Unsupported tools get an honest unavailable
card and reason during development, but this does not count as restored parity.

## 6. Motion is a visual explanation of saved facts

**MOT-01** Preview and saved state have different visual grammar. Preview displays a
persistent “Preview—not saved” label and ghost/dashed future allocations from the
chosen stored result. Swiping changes that projection only. Saved state has a
“Saved plan” or “Recorded simulation” label and stable result/revision identity.
Never animate completed planting merely because a future plan was selected.

**MOT-02** Introduce an explicit server transition description, not tone-to-animation
guesswork: event ID, originating action/proposal, context/snapshot/revision, before
and after states, affected entity IDs, effective date, semantic event kind, fact
deltas and explanation references. Timing and rendering remain frontend concerns.
Unknown event kinds fall back to readable static state. Animations cannot calculate
yield, allocation, eligibility, causality or elapsed simulated time.

| Trigger | Finite 2.5D storyboard | Static/reduced-motion equivalent |
| --- | --- | --- |
| Select alternative | 180–220 ms card depth/focus; dashed future allocation changes; saved layer unchanged | Immediate selected card and named preview layout |
| Submit choice/proposal | Pending label while server works; no speculative success | Same persisted queued/running/failed status |
| Successful plan/replan | Cause label → affected beds → old/new allocation projection → signed metric change → settled result | Before/after allocation and metric cards, reason text |
| Upcoming maintenance | Outline B3 with start/end dates and “Upcoming”; do not depict already blocked space | Same upcoming notice |
| Recorded maintenance effective | Barrier on exact unavailable bed; preserve existing/executed crops; show affected future work | Bed status and reason including effective dates |
| Simulated sow/transplant/growth/harvest | Show only the matching saved crop-stage change; produce moves into recorded inventory on harvest | Dated batch and inventory change summary |
| Recorded delivery | Inventory-to-order movement and truck once for delivery event, quantity and date labelled | Recorded delivered/shortfall quantities and order identity |
| Inverse succeeds | Reverse only changed future projection after inverse job completes | New inverse event and resulting metrics; original event remains |

After server completion, target sequence: cause 0–200 ms, affected area 200–450 ms,
state transition 450–1000 ms, settled explanation by 1200 ms (maximum 1500 ms).
These are presentation targets, not simulated time or artificial server progress.
Controls must not depend on `animationend`: reduced motion, interruption or dropped
frames must not block the next valid action. Render authoritative final state/text
before enabling the next mutation; animation itself must not impose a mandatory wait.

**MOT-03** Play a consequence once per unseen committed event ID, never merely on
React remount, progress update, card swipe or generic success tone. Delivery truck
requires a delivery event, not “success.” Repeated render/reload does not imply a new
delivery. If returning to multiple saved events, show “Changes since you last looked”
cards, not a burst of misleading simultaneous animations. Replay change is explicit,
read-only and marked replay. Keep the current scene static while explaining history,
or clearly mark a historical scene with its date; never mix current and historical.

**MOT-04** Remove endless educational loops and idle crop growth. A stationary
season should not look as though it is progressing. Limit subtle decorative motion,
disable offscreen/hidden-card motion and stop when document is hidden. One persistent
motion preference controls animations AND transitions; no duplicate Pause controls.
Pause must take effect within 100 ms and survive reload/context switches. OS reduced
motion immediately shows final states and equivalent text; do not offer a misleading
Play control that cannot override the active system preference. No rapid flashes.

**MOT-05** Fixed-camera readable composition: each bed's friendly label must remain
unobscured at all tested sizes, with crop/state/date on its detail card. Distinguish
empty beds from harvested crop residue. Preserve hatch/icon/text distinctions instead
of color-only targets. The four-bed lesson illustration must not become the general
farm renderer: larger farms use server-bound bed groups and a swipeable “Area X of Y”
inspection deck; the scene frames the selected group without hiding total scope.
Do not invent rack/domain entities to support the art.

## 7. Contracts, failure states and abuse protection

**SAFE-01** Every card/action retains context kind/ID, entity kind/ID, source label,
frozen snapshot kind/ID/hash, revision, result ID/hash where applicable, and explicit
server eligibility/disabled reason. Include farm/version in sandbox and journey ID
in lessons. Friendly labels never replace identity. Full IDs belong in Record
identity detail cards, not the introductory headline. Server resolves trusted focus;
no client-supplied title/context may expand a conversation's data access.

**SAFE-02** Preserve all cumulative global/IP/tenant API limits, stricter write
admission before body parsing, inference burst/hour/concurrency/run budgets and
shared provider reservations. New card adapters, import/export, polls, studies,
replay and streaming must not bypass these gates. Poll with bounded backoff, respect
Retry-After and cancel obsolete polling on context switches. No client retry storm.
No provider calls for intro, navigation, Explain, saved reviews, comparisons, local
calculations or scene playback. Every provider invocation needs explicit submission
through the allowlisted gateway and validated snapshot. Do not auto-retry paid calls.

**SAFE-03** Preserve form drafts on 429/network failure. Show what is known saved,
what remains unsent, allowed retry time and deterministic help. Stale revision
fetches current state and asks for review, never silently applies the stale choice.
Retries retain idempotency identity for the same operation. Unknown mutation outcome
is reconciled before resubmission. Failure animation never resembles success.
Invalid/withheld AI leaves deterministic explanation and planning fully usable.

## 8. Verification and implementation order

Acceptance is pending. Existing V14 test passes do not prove these requirements.

1. **P0 — integrity and truthful explanation:** SAFE-01–03, preview/saved distinction,
   dated maintenance/delivery meaning, deterministic Explain, full thread evidence,
   and explicit lesson/sandbox roots. Restore a reachable farm entry without old UI.
2. **P1 — useful capability parity:** implement the PAR-01 planning/records/work/
   evidence/history adapters, reviewed proposals, task corrections and Council;
   verify each complete user workflow, not only presence of a card.
3. **P1 — teaching and meaningful motion:** LEARN-01–02, UX-01–03 and MOT-01–05,
   read-only replay, accessible summaries and full journal.
4. **P2 — remaining parity and polish:** integrate experiments/explorer/research/
   Waste Rescue and preferences; complete parity audit and performance work. These
   are still release gates for calling the new version a full replacement.

| Check | Required scripted evidence |
| --- | --- |
| A01 first use | Fresh intro makes zero API/provider calls until Start; illustrative practice teaches swipe vs save; full real lesson reaches correctly worded debrief |
| A02 context and reachability | Fresh/returning user can open lesson or sandbox; every PAR-01 path completes; return preserves exact state; no edition menu |
| A03 domain integrity | Cross-context/tenant IDs rejected; B3 identity checked in each fixture; historic edition data untouched; preview/swipe/replay causes zero mutations |
| A04 explanation | Every core stage answers what/why/tradeoff/source/next; expected vs recorded and units asserted against frozen facts; missing evidence explicitly marked |
| A05 numerical workflows | Same-baseline comparison, proposal → job → result → approval → task → correction, stale inverse and inverse recalculation, accounting invariants and task history |
| A06 motion | Normal-motion event clips plus start/mid/end frames; semantic event IDs, no false truck/maintenance, no repeated event on reload; pause/reduced/offscreen equivalent |
| A07 layout/input | 360/390/430 and 1280 desktop; long labels, 200% text zoom, on-screen keyboard; swipe vs vertical scroll; visible focus and 44–48 px targets |
| A08 assistive technology | Active card alone exposed; focus restored on Back; polite once-per-event causal summary; friendly bed status/date/mode; no stale card-name announcement |
| A09 optional AI and admission | No automatic provider calls; explicit focused Ask/Council, saved transcript/citations, withheld responses; concurrent burst/tenant/IP/global quotas and Retry-After; provider-down completion |
| A10 recovery | Reload each checkpoint, network interruption before/after commit, stale revision, repeated taps, draft retention and server-job resume; no duplicate ledger event |
| A11 release | Generated-contract drift, frontend build, full Python plus isolated PostgreSQL, responsive Playwright, measured bundle warning and immutable candidate release evidence |
| A12–A14 V13 reuse | Asset identity/stage truthfulness, actual V13 workflow parity and minimalist containment, as detailed in the reuse map |

Retain screenshots, timed motion recordings, action/capability matrix and audit
traces in the future release report. Use actual local numerical results, not mocked
outcomes. Automated/heuristic review can assert visible content and behavior; human
comprehension remains unproven until observed with new users. Future human tasks:
explain preview versus save, choose a tradeoff, explain B3 recovery, locate the
original evidence, return from a tool and find a saved task correction without help.
Do not claim beginner usability merely because the browser can click through.
