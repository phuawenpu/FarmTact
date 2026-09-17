# V13 tactical interface accessibility review

Review date: 17 September 2026 UTC. Scope: V13 plan, implemented tactical shell,
and scripted responsive journey. Method: heuristic/code-contract review plus
headless browser assertions. This is not a screen-reader study, physical-device
test, accessibility conformance audit, or human usability result.

## Review conclusion

The card model can preserve V12's keyboard, status, provenance, and dialog foundations, but the stacked presentation introduces four high-risk areas that must be treated as release gates for the prototype: inactive-card exposure, swipe/vertical-scroll conflict, dock occlusion, and focus management for contextual Ask. The safest implementation keeps all state-changing operations available as ordinary buttons and treats motion/gesture as supplemental.

The implemented scripted journey passed its active-card isolation, swipe versus
vertical scroll, button/keyboard equivalence, 44 px primary target, focus restoration,
reduced-motion, and 360/390/430/1280 px overflow assertions. These automated passes
close the prototype's scripted gate only; the manual/screen-reader/physical-device
items below remain open.

The blind 360 px keyboard review also found that Details updates the contextual
region farther down the page without disclosure semantics or focus movement. The
content is present and the action is keyboard-operable, but adding `aria-controls`,
an appropriate expanded relationship/status announcement, and intentional
scroll/focus behavior remains a priority before a conformance claim.

## Acceptance checklist

| Area | Required behavior | Verification |
|---|---|---|
| Active card semantics | Exactly one card is readable and interactive. Decorative adjacent layers use `aria-hidden="true"`, `inert` or equivalent descendant tab suppression, and `pointer-events: none`. | At each index, enumerate accessibility/tab targets and assert no adjacent-card name/action is present. |
| Card position | Expose “Card N of M” and the selected title without announcing every decorative layer. | Accessible-name snapshot and screen-reader smoke test. |
| Buttons and swipe | Previous/Next and Left/Right keys produce the same selection as horizontal swipe. Vertical scrolling remains native. | Touch/pointer journeys at all mobile widths plus keyboard journey. |
| Gesture intent | Begin horizontal navigation only after a directional threshold; cancel when vertical movement dominates. Do not prevent default before intent is established. | Script vertical drags over the card and horizontal swipes; assert scroll/index outcomes. |
| Target size | Primary and secondary controls are 44–48 CSS px minimum in both dimensions or have equivalent spacing; close buttons meet the same target. | Bounding-box assertions at 360/390/430/desktop. |
| Visible focus | Every interactive element has a high-contrast focus indicator unaffected by overflow clipping or card transforms. | Keyboard screenshots and computed-style assertions. |
| Action order | DOM, reading, and keyboard order match the visible left → center → right order, even when the center is visually emphasized. | Tab-order assertion. |
| Disabled reasons | Unavailable Compare/Approve/Undo/Record Result exposes a visible, stable reason associated with the control; not tooltip-only. | DOM text/description assertion with keyboard and touch. |
| Live job status | Queue/running/completed/failure is announced in a polite live region; errors use an alert where immediate action is necessary. Repeated polling does not repeat unchanged text. | Mutation/live-region test with mocked and real persisted states. |
| Progress semantics | Indeterminate planner work is not assigned a fabricated percentage. | DOM role/value check. |
| Metric changes | New server values and signed deltas are textual. Color and animation are supplemental. | Reduced-motion snapshot and text assertions. |
| Provenance | `SIMULATION · SCENARIO ONLY`, source kind, date/freshness where applicable, and projected/advisory/reported distinctions remain visible and reachable. | Provenance assertions on compact and expanded views. |
| Board highlight | B3 highlight includes an accessible label/state connection to the selected constraint; not color-only. | DOM relation/text assertion for `bed-07`. |
| Ask dialog | Mobile sheet and desktop panel have a programmatic name, contained focus, sensible initial focus, Escape and visible close, background containment, and focus restoration. | Automated dialog journey plus manual assistive-technology smoke test. |
| Card remains in context | Opening Ask preserves the card or selected-card summary in view without leaving duplicate focusable controls behind the dialog. | Viewport and tab-order assertions. |
| Suggested questions | Suggestions are ordinary buttons with clear labels; activation populates or submits only according to explicit copy. Prefer populate-first to avoid accidental provider calls. | Network assertion that open/focus/populate makes zero provider calls. |
| Reduced motion | No card transforms, animated reorder, smooth scroll, or pulsing progress under `prefers-reduced-motion: reduce`; state/status remains complete. | Computed-style checks and full reduced-motion journey. |
| Sticky dock | Development-only sticky mode reserves space and safe-area padding; no content or focused control is covered. Default remains normal flow. | Element intersection/viewport assertions, including final page controls. |
| Zoom/reflow | Content remains operable at narrow reflow and 200% browser zoom; cards do not require two-dimensional scrolling. | Manual zoom/reflow review. |
| Contrast/non-color | Card depth, states, provenance, errors, B3 highlight, and deltas do not depend on subtle color alone. | Automated contrast scan followed by visual review. |

## Static findings from the V12 baseline

- V12 already uses semantic buttons, labelled progress/status regions, visible error roles, reduced-motion CSS, and bottom-sheet/modal patterns. These are reusable foundations, not proof that the new card stack passes.
- V12 conversation creation accepts an optional `selected_bed_id` and validates it against the frozen snapshot. V13 focus must retain that safety behavior and must not create a second, contradictory accessible context label.
- V12 polling displays a running status and leaves calculations local unless the user explicitly asks a specialist. V13 should reuse that separation and deduplicate repeated status announcements.
- V12's responsive evidence covers 360, 390, 430, and desktop widths, but it does not exercise a horizontally swipeable card stack, a three-action dock, or the new selected-card summary.

## Priority risks and mitigations

### 1. Decorative cards become duplicate interfaces

Opacity and off-screen transforms do not remove content from the accessibility tree. Render decorative backs without actionable content when possible. If real adjacent cards remain in the DOM, combine `inert`, `aria-hidden`, tab suppression, and pointer suppression; test after every index change.

### 2. Swipe blocks ordinary reading

The stack sits in a vertically scrolling page. Use pointer/touch direction locking with a threshold and do not capture until horizontal displacement clearly exceeds vertical displacement. Keep buttons and arrow keys as the normative path.

### 3. Dock covers content or the software keyboard

Use normal flow by default. Sticky experimentation must reserve space, honor safe areas, and be disabled/fallback when the visual viewport contracts. Physical-phone keyboard occlusion remains unverified by headless responsive tests.

### 4. Ask loses context or triggers work unexpectedly

The selected card/summary should remain perceptible while the dialog contains keyboard focus. Opening, closing, selecting a suggestion, or changing specialists must not invoke inference unless the control explicitly says it sends a question. Restore focus to the invoking action on close.

### 5. Meaning depends on movement

Card relocation and metric flashes are transient. Keep persistent Active constraints membership, B3 state, signed deltas, result identity, and textual status so reduced-motion users receive the same decision evidence.

## Human validation still required

Automated checks cannot establish thumb comfort, actual screen-reader comprehension, dictation/software-keyboard interaction, vestibular comfort, cognitive load, or whether growers understand “reserve,” provenance, stale Undo, and strategy deltas. A moderated test with representative farmers and assistive-technology users remains deferred. No accessibility conformance claim should be made from this heuristic report alone.
