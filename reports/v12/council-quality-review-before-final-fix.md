# V12 actual-AI evidence quality review

## Scope and conclusion

This is a bounded review of three stored artifacts only:

- `/tmp/v12-council-final.json`
- `/tmp/v12-specialist-final.json`
- `/tmp/v12-specialist-corrected.json`

It does not make a general model-capability claim. The Council artifact contains five actual DeepSeek calls: four numerical specialists and the Plan Reviewer. Two additional roles were withheld before inference because their required sources were absent. Within the frozen facts shown in the artifact, I found **no numerical contradiction in the five returned Council findings**. Two findings have material semantic-quality limits: the Crop Planner's crop-mix interpretation is not established by its cited area facts, and the Capacity & Cost Analyst does not analyze capacity or cost. Those are relevance/support weaknesses despite valid references, not transport failures or false quoted numbers.

The Council journey's overall file status is `FAIL` because a later `GET /farm-workflow` returned HTTP 401 after the Council, proposal, recalculation, approval, task result, and correction checks had passed. That late session failure does not negate the stored Council responses, but the artifact must not be represented as a complete passing end-to-end journey.

## Transport and reference integrity

- Council status is `completed`, request count is exactly 5, and replay is recorded as identical.
- All five actual findings report provider `deepseek`, returned model `deepseek-flash`, nonzero latency and token usage, `inference_origin: deepseek_api`, and the Council snapshot hash `0ac1004b...3869`.
- Provider request IDs are null in all five audits. Provider/model/usage/latency evidence exists, but there is no provider request-ID trace to correlate externally.
- Every cited Council claim ID resolves to a code-rendered verified claim in the same frozen snapshot. No rejected Council finding is being silently counted as validated.
- The two absent-source roles have no claim IDs and made no inference request. Their `unavailable`/`source_absent`/`partial` state accurately avoids fabricating weather or market evidence.

## Finding-by-finding semantic assessment

### Demand Planner — validated, numerically consistent

The finding selects Resilient and cites booked shortfall 306 kg, booked delivered 518 kg, and overall-demand fill rate 0.6213. Across the frozen strategies, booked shortfall is Resilient 306, Balanced 378, Lean 454 kg; booked delivered is Resilient 518, Balanced 446, Lean 370 kg. Resilient therefore has both the lowest booked shortfall and highest booked delivery. The service recommendation is supported.

The third citation is explicitly overall-demand fill rate, while the interpretation concerns booked commitments. It does not contradict the booked metrics, but it should not be treated as a booked fill-rate measurement. The first two citations are sufficient for the stated conclusion.

### Crop Planner — quoted numbers correct; interpretation under-supported

The finding selects Resilient and correctly cites sown areas of 240 m² for Resilient, 180 m² for Balanced, and 120 m² for Lean. It interprets this as preserving a useful crop mix. Area alone does not establish crop variety or mix; no crop-count, lot-diversity, or variety fact is cited. The selection is consistent with choosing the greatest sown area, but the stated crop-mix rationale is a qualitative inference not demonstrated by the cited facts.

Assessment: no factual contradiction in the numbers; semantic support is partial.

### Capacity & Cost Analyst — quoted numbers correct; functional-role coverage weak

The finding selects Resilient using Lean booked shortfall 454 kg, Resilient booked delivery 518 kg, and Resilient booked shortfall 306 kg. These values are correct and support a service-first choice.

It cites no labour, area, cost, margin, or other capacity/cost comparison even though the frozen set contains labour (55.8/70.82/85.42 hours) and projected cost (SGD 1,141.50/1,522.54/1,862.99 for Lean/Balanced/Resilient). Its `service_over_margin` tradeoff is not evidenced with a margin citation. Thus the response is not contradictory, but it does not substantively perform the advertised Capacity & Cost Analyst role.

Assessment: reference-valid service analysis; inadequate capacity/cost analysis.

### Farm Planner — validated, numerically consistent

The finding selects Resilient and cites booked shortfall 306 kg, booked delivery 518 kg, and projected margin SGD 3,193.15. The first two are the best booked-service values. The complete frozen margin comparison is Resilient SGD 3,193.15, Balanced SGD 2,930.59, Lean SGD 2,467.60, so the selected strategy also has the highest projected margin.

The finding does not cite the other two margins, so the comparative margin claim is implicit rather than fully displayed. Still, its chosen strategy and cited values do not conflict with the frozen facts.

### Plan Reviewer — validated, tradeoff is internally coherent

The reviewer selects Resilient and cites booked shortfall 306 kg, margin SGD 3,193.15, and expired waste 220.98 kg. Across the frozen set, Resilient has the lowest booked shortfall and highest margin, but also the highest waste (Resilient 220.98, Balanced 175.99, Lean 153.99 kg). Describing the decision as balancing service, waste, and margin is coherent only as an explicit acceptance of the waste penalty; it must not be read as saying Resilient minimizes waste.

The rendered text does not claim that Resilient has the lowest waste. No factual contradiction is present, and the tradeoff is visible rather than hidden.

### Weather & Risk Monitor — correctly withheld

Status is `unavailable`, truth status is `partial`, tool status is `source_absent`, and the text says site weather evidence was not supplied. It cites nothing and proposes no strategy. This is accurate partial handling, not an actual-AI finding.

### Market & Price Analyst — correctly withheld

Status is `unavailable`, truth status is `partial`, tool status is `source_absent`, and the text says site market evidence was not supplied. It cites nothing and proposes no strategy. It correctly avoids treating modeled demand or internal prices as sourced market evidence.

## Specialist demand comparison

The earlier specialist artifact at source `7fef7e9...` is a real semantic failure despite successful reference transport. It labels all-demand shortfalls 412.01/507.01/612.02 kg as “confirmed-demand shortfall.” Its references are valid members of that older snapshot, but they are the wrong metric scope. `references_verified` therefore establishes reference membership, not semantic correctness. The artifact appropriately has overall status `FAIL` and `actual_advisor_response: false`.

The corrected artifact at source `7746b2f...` passes the bounded booked-demand question. It cites booked shortfalls exactly: Resilient 306 kg, Balanced 378 kg, Lean 454 kg; states that Resilient is smallest and Lean largest; and explicitly excludes modeled residual demand. The ranking and scope match the frozen facts. Replay is stored, the planning snapshot remains bound and unchanged, and no new calculation occurred during replay.

The corrected specialist result supports only this booked-shortfall comparison. It does not erase the earlier failure, establish broad demand-analysis quality, or validate uncited market conditions.

## Bounded release assessment

- **Numerical/reference result:** five of five actual Council responses cite frozen values without a detected numerical contradiction.
- **Semantic result:** Demand Planner, Farm Planner, and Plan Reviewer are coherent for this snapshot. Crop Planner is under-supported on crop mix. Capacity & Cost Analyst misses its named functional focus.
- **Partial roles:** Weather and Market are correctly withheld due to absent sources and are not counted among actual calls.
- **Specialist correction:** the old overall-versus-booked scope error remains recorded as FAIL; the corrected 306/378/454 kg response passes its narrow question.
- **End-to-end result:** the Council artifact is not a general PASS because its later workflow request failed with HTTP 401.

No broader provider capability, agronomic validity, market validity, or operational authorization follows from these stored cases.
