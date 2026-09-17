# V14 scripted first-use review

## Scope and limits

- Date: 2026-09-17
- Candidate: `http://127.0.0.1:4190/`
- Viewport: desktop, 1440 × 900
- Prompt given to the evaluator: **“Use FarmTact.”** No walkthrough or product manual was provided.
- Method: one fresh Playwright browser context; interaction used only visible buttons and cards. The repository and implementation were not inspected during the journey. Network observations were limited to browser-visible requests and one action response used to understand delayed feedback.
- This is a **scripted agent review**, not a blind human usability study. The evaluator had general familiarity with production-planning concepts and prior high-level familiarity with FarmTact’s synthetic/demo safety model. Findings are reproducible observations and heuristic judgments, not claims about human comprehension.

## Outcome

The lesson was finishable. The reviewer started at the intro, created a season, compared two calculated plans, chose the 25 kg plan, encountered and recorded B3 maintenance, selected an eligible recovery, advanced the simulation, delivered 25 of 25 kg, reviewed consequences, and reloaded the completed journey successfully.

The opening and ending communicate the product unusually well. The weakest part is the middle simulation: delayed state transitions, a step counter that moved backward after recovery, and seven repetitive “Advance to next crop event” actions made progress feel uncertain and exposed event labels that appeared contradictory.

## Comprehension scorecard

| Question | Score | Browser evidence |
| --- | ---: | --- |
| What is the objective? | 5/5 | The intro says “Keep one promise”; Step 1 repeats “Grow 25 kg of lettuce for 23 Feb” and explains the confirmed order. |
| What should I do next? | 4/5 initially; 2/5 mid-lesson | The emphasized actions “Start playing,” “Calculate two plans,” and “Choose this plan” are clear. During execution, the unchanged screen and repeated advance action made it unclear whether a click had worked. |
| What changed because of my decision? | 4/5 | Delivery, space use, maintenance conflict, recovery placement, cost, waste, and final fulfillment are shown. The debrief explicitly says future work moved after B3 maintenance. |
| How do I know I am finished? | 4/5 | “STEP 8 OF 8,” “Completed,” and “Delivered 25 of 25 kg” are strong. The three-card debrief requires Next navigation, and the first result card initially presented a disabled “Waiting for next step” action rather than an immediately conclusive finish action in this reviewed build. |

## Reproducible journey observations

1. `/` opened a polished three-part intro. It clearly distinguished illustrated examples from live readings and simulation from real operations. The primary “Start playing” action was visually dominant.
2. `/play` opened Step 1 of 8 with a single objective and primary action, “Calculate two plans.” The farm was labelled “Simulated farm · noninteractive” and the card was labelled “SYNTHETIC TEACHING SIMULATION.”
3. Calculation produced two eligible plans:
   - Lean: expected delivery 23 kg; growing space 62.5%.
   - Resilient: expected delivery 25 kg; growing space 81.2%.
4. The reviewer chose Resilient because it visibly met the 25 kg promise. The farm advanced and exposed “Advance to next checkpoint.”
5. After one advance click, the visible card and primary action remained unchanged for more than seven seconds. A second deliberate click was accepted as another valid action; the journey then appeared at Step 5. This creates a realistic accidental-skip risk even though each backend action was accepted sequentially.
6. B3 maintenance was explicit: unavailable 18–31 January, with a “SCHEDULED TEACHING EVENT” provenance label.
7. Recovery comparison was strong: “Saved plan (conflicts)” was unavailable, its Choose button was disabled, and the page stated “B3 maintenance conflicts with the saved placement.” The alternate Lean recovery remained eligible at 25 kg and 68.8% space.
8. After choosing recovery, the header moved from Step 6 back to Step 4. The reviewer then needed seven “Advance to next crop event” clicks before delivery. Several dates displayed the same “Harvest Lettuce in A1” event, while another later date showed “Transplant Lettuce in A1,” making the sequence difficult to trust at a glance.
9. Delivery was clear at Step 7: “Customer delivery,” dated 23 February, with “Review recorded delivery.”
10. Step 8 reported “Delivered 25 of 25 kg,” SGD 79.14 cost, and 6.9 kg disposed. The comparison card explained that maintenance moved future work to beds A1, A2, and B4. A final card offered the next isolated challenge.
11. Reloading `/play` preserved the completed journey and returned to the first debrief result card. No new journey was created.

## What worked especially well

- The first screen answers purpose, scope, and safety before asking for commitment.
- The main action is consistently centered and visually prominent.
- Real-operation boundaries are stated repeatedly without overwhelming the primary task.
- Quantities and dates make the planning decision concrete.
- The conflict card provides an explicit disabled reason rather than silently blocking selection.
- The final result connects fulfillment with cost and waste, then provides a stored-plan comparison.
- Reload persistence makes the lesson feel recorded rather than ephemeral.

## Prioritized fixes

### P0 — Preserve a monotonic, trustworthy journey

The visible step counter must never move backward. Choosing a recovery at Step 6 returned the UI to Step 4. Keep the high-level lesson step monotonic even if the backend re-enters an execution substage.

### P0 — Lock actions through the complete visible transition

Disable the primary action immediately on activation and keep it disabled until the new stage/card is rendered. Show status such as “Advancing to 17 Jan…” during the transition. The reviewed build allowed another advance after the first click had been accepted but before visible state caught up.

### P0 — Correct or clarify crop-event labels

The repeated “Harvest Lettuce in A1” labels across multiple dates, followed by “Transplant Lettuce in A1,” read as a chronology error. Each checkpoint should name the event that caused that checkpoint, or use a neutral label such as “Farm advanced to 5 Feb” when no singular event is being taught.

### P1 — Reduce the execution click loop

Seven near-identical advance clicks dilute the consequence of the planning decision. Collapse uneventful weeks into one transition, or show a compact timeline and stop only at sow/transplant/harvest/maintenance/delivery events that introduce new information.

### P1 — Explain why 23 kg is “Eligible” for a 25 kg promise

The Lean starting plan was labelled Eligible while showing expected delivery below the confirmed order. Rename the state (for example, “Feasible with 2 kg shortfall”) or place the shortfall next to the badge so eligibility is not mistaken for meeting the goal.

### P1 — Replace optimizer language on the beginner card

“Maximize the worst declared scenario fill rate, then improve weighted policy utility” is precise but not beginner-facing. Prefer a decision explanation such as “Uses more space so the full order still fits under the tested conditions,” with technical detail under More.

### P2 — Make the debrief’s navigation model explicit

Label the three cards “Result,” “What changed,” and “Next challenge,” and show “1 of 3 debrief cards.” This would make the disabled primary on the first result feel intentional rather than stalled.

## Recommendation

Proceed as a public prototype once the P0 transition/counter/event-sequence issues are resolved or explicitly accepted as known limitations. The concept, first action, safety boundary, plan choice, conflict handling, and final consequence story are strong enough for scripted evaluation. Human comprehension, perceived trust, and willingness to continue still require moderated usability sessions; this review does not establish those claims.

## Integration follow-up

The report above preserves the independent observations before final remediation.
Root and package owners subsequently fixed the three P0 presentation defects:
recovery growth stays at step 6; advance cards are keyed and titled by the current
recorded date; event labels use only tasks recorded on that date and distinguish
existing/planned/recovery crop cycles. A no-task date receives a neutral dated
checkpoint instead of a stale harvest label. Pending actions use explicit progress
copy and remain disabled during the request. No simulation chronology was edited.

`browser-local.json` now passes 75 checks, including monotonic progress and visible
checkpoint changes after every advance. Backend tests assert exact-date event
projection and the neutral fallback. Feasible-with-shortfall badges, plain-language
tradeoffs and a local Next card action on the first debrief also address the related
P1/P2 findings. Seven explicit event advances remain intentional in this prototype;
whether they feel repetitive is an open human-usability question, not a claimed fix.
