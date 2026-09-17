# V14 bounded interaction review

Date: 2026-09-17  
Viewport: 360 × 800, touch enabled, reduced motion enabled  
Scope: one fresh isolated browser context; introduction plus the START checkpoint only. The season was not advanced and no provider action was submitted.

## Browser observations

| Check | Result | Evidence |
| --- | --- | --- |
| Vertical gesture confinement | Pass | A 90 px mostly-vertical pointer drag left the active introduction card on “Keep one promise”. |
| Horizontal swipe | Pass | A horizontal pointer drag changed the active card to “Compare two plans”. |
| Active-only introduction card | Pass | Exactly one `beginner-card` test target was exposed; inactive cards were `hidden` and `aria-hidden`. |
| Noninteractive introduction art | Pass | The scene contained no button, link, input, textarea, or focusable descendant. |
| Explain keyboard isolation | Pass | Pressing Enter on Explain opened the explanation and left the journey revision at 0. It did not invoke the primary action. |
| More keyboard isolation | Pass | Pressing Enter on More opened the utility deck and left the journey revision at 0. |
| Utility deck location | Pass | More replaced the decision card with `utility-next-step` in the same card location. |
| Back state restoration | Pass | After moving within the utility deck, Back restored the exact prior season card, `lesson-objective`. |
| Settings discovery | Pass | Settings was reachable using the same Next card control as the rest of the deck. |
| No automatic planning mutation | Pass | The bounded journey remained at revision 0 throughout these presentation and utility interactions. |

The first browser script stopped at the motion-control click because its locator expected an accessible name ending in “Pause”; the control’s icon/text combination did not provide that stable name. No second fresh context was opened, preserving the requested one-context limit. The control now has explicit `Pause motion` / `Play motion` accessible names. The remaining target-size and replay assertions are therefore implementation/build verified here, not claimed as observations from that browser run.

## Issues fixed during the review

- Keyboard events from Explain, More, and other native controls are ignored by the card-level Enter shortcut, preventing accidental primary actions.
- A stale plan selection can no longer focus an unavailable recovery choice. The current eligible server choice is selected instead.
- Settings is handled locally: it offers replay of the introduction and motion control without submitting an unknown backend action.
- The introduction and game expose stable shell, card, scene, action-area, stage, revision, and result identifiers for verification.
- The farm illustration uses only the backend scene projection. Four beds were enlarged and repositioned, their labels made legible, and the date strip moved below the art.
- Maintenance now shows a barrier on the actual highlighted bed instead of misleading rainfall. A recorded successful delivery shows a one-shot arriving truck, and crop-stage changes receive a one-shot visual transition.
- Illustrations pause for the user motion control, reduced-motion preference, and `document.hidden`.
- Choice cards now foreground Expected delivery, Growing space used, and Estimated cost from the stored result, rather than repeating four similar production totals.
- Raw entity IDs were removed from the primary card footer; it now shows concise provenance.
- Admission errors on the introduction are visible inline with a Try again action rather than failing silently.

## Static accessibility checks

- Action buttons define a minimum height of 44–50 px; the three primary dock controls are 50 px high.
- The card gesture region uses `touch-action: pan-y`, so vertical page scrolling remains available.
- The illustrated farm has no controls or focusable hotspots; decisions remain in the action area.
- Visible focus outlines, live calculation status, disabled reasons, and explicit button labels are present.
- Reduced motion collapses animation duration and the pause state stops all descendant animations.

## Verification

`npm run build` passed after the fixes: TypeScript checks completed and Vite produced the production bundle. The existing bundle-size profile remains an optimization item.
