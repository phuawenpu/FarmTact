# V7 novice, mobile, and accessibility walkthrough

Review date: 10 September 2026 UTC. Target: local immutable-candidate route `/v7/research`. Result: 48 automated browser checks passed, with no recorded failure, page/console error, or provider-capable request. Ten screenshots accompany `reports/v7/novice_review.json`.

This was an independent Codex walkthrough using a novice heuristic. It is not a human usability study and provides no evidence about enjoyment, trust, learning, or usefulness to farmers. The test used a root-provisioned, mode-0600 local authentication fixture to avoid consuming public session allowances; each measured width explicitly reset to a fresh isolated research session. Fixture setup is not counted as public onboarding behavior.

## Immediate pickup

At 360, 390, 430, and 1280 CSS pixels, the fresh page presented one orange **Ask council for a plan** action beneath a plain **Start here** heading. Research evidence was demoted to an icon and the layout/pacing controls remained closed behind **Compare research layouts and pacing**. The five farm actions were visible as a compact progression. The page preserved the requested CSS width and had no horizontal overflow.

The first three-policy result appeared 15.319 seconds after activating the start action in the 390px local run. That duration includes the local numerical worker. It is a diagnostic observation, not a human completion result; the “first meaningful planning choice within 30 seconds” remains a future human-test target.

[Fresh 360px view](../../apps/web/screenshots/v7-novice/first-view-360.png) shows the starting action, task progression, and beginning of the farm context without opening instructions or research controls.

## Guided correction journey

The walkthrough followed only the current **Next council action**, rather than using duplicate quick actions:

1. Calculate the baseline and expose Lean, Balanced, and Resilient.
2. Select Bed 4; verify that `Bed 4 · A4` appears beside the composer with a labelled removal action.
3. Review a dated reservation proposal. Its heading and start date scrolled below the fixed header; ordinary touch click activated both Bed 4 and **Apply to new version**.
4. Recalculate version 2, mark the additional order unconfirmed, apply, and recalculate version 3.
5. Challenge the rainfall assumption. The unresolved challenge prevented silent selection; inline evidence stated that outdoor weather is not a numerical yield input.
6. Open research sources in a named modal, close it with Escape, and verify focus returned to the invoking control. Explicitly correct the assumption.
7. Inspect six same-policy values with plain labels and units, then choose the feasible current simulated version. The result stated that no operational commitment was made.

The full guided sequence completed in 53.475 seconds of automated local runtime and included baseline, version-2, and version-3 numerical calculations. No manual shortcut or provider interpretation was used. [Reservation review at 390px](../../apps/web/screenshots/v7-novice/reservation-review-390.png) shows dates, recorded occupancy, apply/discard controls, feasibility, and values together. [Completed task](../../apps/web/screenshots/v7-novice/completed-task-390.png) preserves deltas, the chosen-version statement, earlier frozen results, and the optional actual-advisor action.

## Concept and accessibility observations

- Inline, council-sheet, and adviser-card settings all retained the selected-context, council-discussion, and planning-consequence regions after the task. The controls were keyboard-reachable only after opening the optional comparison disclosure.
- Some labels in the optional layout controls truncate at narrow widths. The controls remain operable and are collapsed during the default task; this is a presentation limitation of the research comparison.
- The default sheet kept selected context in the council region beside the composer. Context selection and proposal actions no longer suffered the pointer interception observed in the earlier candidate.
- Reduced-motion preference was active at every width. The final numerical values and signed deltas remained persistent, so the task did not depend on observing motion.
- The evidence modal had a programmatic name, Escape close behavior, a visible close action, and focus restoration. Bed selection, chip removal, apply/discard, policy choice, and layout selection had non-gesture controls.
- Labels such as **Delivery covered 53.9 %**, **Delivery shortfall 505.0 kg**, **Labour 71.4 hours**, and **Margin 2957.4 SGD** expose their units. Whether a first-time human understands fill/shortfall trade-offs still requires testing.

The automated path does not establish reading comprehension, whether users notice stale-version meaning, or whether the three visual concepts feel meaningfully different. Screenshots taken at a common scrolled position mainly prove state preservation and do not justify choosing a layout on appearance.

## Physical and human testing still required

Headless Chromium emulated responsive widths and touch capability. It did not test a physical phone, thumb accuracy, a native software keyboard, keyboard occlusion, device dictation, screen-reader announcements, vestibular response, network variability, or hardware performance. Enjoyment must be asked of people; message count and reviewer aesthetic preference are not proxies.

The next human test should start without instructions, preserve the same synthetic task and data, rotate concept order, and measure correct context identification, wrong mutations, clarification recovery, feasible-current-version choice, time to first meaningful choice, total completion time, and participant-rated enjoyment separately.
