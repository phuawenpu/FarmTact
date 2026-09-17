# V14 bounded interaction review

Date: 2026-09-17  
Viewport: 360 × 800, touch enabled; normal and reduced-motion media states tested in the same context
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
| Pause and resume | Pass | Pause illustrations changed the shell to `paused`; Play illustrations restored `playing`. The in-game Pause motion control was also local and left revision unchanged. |
| Reduced motion | Pass | Switching the same page to `prefers-reduced-motion: reduce` changed the shell to `paused`; returning to `no-preference` restored motion. |
| Replay introduction | Pass | Replay introduction stayed on `/play`, exposed Return to season, and returned to the exact selected card and revision. |
| Action target size | Pass | Visible targets measured 82.1 × 50 px, 143.7 × 50 px, 82.1 × 50 px, and 95 × 44 px. |
| Active-only game card | Pass | Exactly one `beginner-card` was exposed in the game and introduction. |
| Action-area confinement | Pass | Every visible game button, link, input, textarea, and select was inside `beginner-action-area`. |
| Vertical pan support | Pass | The decision gesture surface reported `touch-action: pan-y`. |
| No automatic gameplay/provider mutation | Pass | Starting created the expected isolated journey. Explain, More, Back, Settings, pause, replay introduction, and return produced zero `/actions` or conversation mutations; revision remained 0. |

The final bounded run completed **23 of 23 checks** with no browser-script error. It used one fresh context and did not advance beyond START.

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

## Accessibility checks

- All visible action buttons met the 44 px minimum in the live browser measurement.
- The card gesture region reported `touch-action: pan-y`, and a vertical drag did not trigger horizontal navigation.
- The introduction and game farm scenes contained no controls or focusable hotspots; all game controls were confined to the action area.
- Visible focus outlines, live calculation status, disabled reasons, and explicit button labels are present.
- Reduced-motion and explicit pause behavior were observed in the browser, including state restoration.

## Verification

The final bounded presentation run passed 23/23 checks. The preceding `npm run build` passed after the frontend fixes: TypeScript checks completed and Vite produced the production bundle. The existing bundle-size profile remains an optimization item.
