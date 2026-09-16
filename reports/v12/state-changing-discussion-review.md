# V12 state-changing discussion review

Source: `/tmp/v12-state-changing-discussion.json`, commit `8dc760d86c3fedddfdd4a97da315d4adec4592f1`. Read-only review; no inference or source change.

## Result

The action and state-change boundary pass. The advisor produced one bounded structured hypothesis:

```text
labour_percent = 80%, target = whole-farm labour capacity, status = hypothesis_only
```

The discussion itself did not mutate the session. The reviewed proposal retained the original action, remained draft-only until explicit Apply & Recalculate, and applied labour capacity as exactly `32 × 0.80 = 25.6` hours/week. Orders and crop-yield assumptions stayed unchanged, the main farm stayed unchanged, and real operations remained disabled. The source conversation is frozen to the current planning result; backend proposal provenance binds the owned validated advisor message hash, original proposed actions, snapshot reference, farmer-reviewed changes hash, and `translation=farmer_reviewed_assumptions`. This supports a reviewed interpretation rather than claiming that model text applied itself.

No unsupported numerical value appears in advisor prose. The numerical facts are separately typed and code-rendered: Balanced labour 70.82 hours, projected margin SGD 2,930.59, and projected cost SGD 1,522.54. The proposed 80% is a structured user-requested hypothesis, not a model-calculated sensitivity result.

## Semantic limitation

The sentence that reducing labour capacity “would pressure margins through higher labour hours per unit” is unsupported and its mechanism is questionable. Reducing the available weekly labour ceiling does not itself cause labour hours per unit to rise. The frozen plan contains no capacity-sensitivity calculation, which the response correctly admits in its next clause.

This is a material qualitative quality limitation, separate from the passing action/apply controls. The backend labels the interpretation `qualitative_unverified`, the relationship advisory-only, and `planner_conclusion=false`; those statuses are honest. A new general entailment validator is not justified by this single case. The targeted remedy is presentation and prompt discipline: visibly separate typed facts from qualitative interpretation and instruct capacity discussions to say the change *may affect feasibility, service, cost, or margin and requires recalculation*, without asserting a causal mechanism before simulation. The UI work exposing `qualitative_unverified` and rendered facts is therefore the appropriate immediate correction.

## Remaining V12 requirement check

I found no additional concrete unmet Farmer Workflow functional requirement beyond already recorded bounds:

- Weather and market Council roles remain partial because reviewed external sources were absent.
- Actual photo evidence used a synthetic labeled graphic and therefore does not establish real agronomic-image quality; photos remain optional, observation-only, and without yield authority as required.
- Exact-source and public publication gates remain pending acceptance activities rather than missing workflow behavior.

The artifact is sufficient to demonstrate discuss → farmer review → proposal → explicit recalculation with preserved provenance. It should not be cited as evidence that the advisor's qualitative margin mechanism was validated.
