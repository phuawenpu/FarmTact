# V9 AI-assisted semantic review

> **Review status:** AI-assisted record audit completed 2026-09-11. This is not a human agronomy, logistics, market, accounting, or ML-expert review. No provider request, numerical rerun, deployment, or farm mutation was made for this review.

This report checks every qualitative assertion in the 18 final V9 outputs against the complete frozen records. It separates whether a statement is true of the frozen record, whether the application accepted its reference shape, and whether the automated phrase scorer passed it.

The source artifacts are [planning-public.json](./planning-public.json), [conversation-public-replay.json](./conversation-public-replay.json), [conversation-public-events.json](./conversation-public-events.json), [research-public.json](./research-public.json), and [ai-quality-final.json](./ai-quality-final.json). Exact message IDs, JSON pointers, selected references, and atomic findings are in [ai-assisted-semantic-review.json](./ai-assisted-semantic-review.json). See [AI provider and Council implementation](../../docs/technical/ai-provider-and-council.md) and [the gap register](../../docs/technical/gaps-and-next-iteration.md) for system context.

## Result

Of 18 final messages, 10 are sound, 5 are sound with scope or citation limits, and 3 contain a material contradiction.

| Outcome | Count | Cases |
|---|---:|---|
| Sound | 10 | Planning Demand, Weather, Market, Profit; direct Production; invite Demand; Council Supply, Profit, Chair; Research Chair |
| Sound with limits | 5 | Planning Production and Chair; Council Demand, Weather, Market |
| Contradiction | 3 | Planning Supply; invite Production; Council Production |

The most consequential defect is Planning Supply. It says booked routing is fully delivered although every strategy has a positive booked shortfall. That false premise passed V4 reference validation and the automated contradiction check, then participated in a required Council gate before ACCEPTED_FOR_SIMULATION. Balanced remains a reproducible numerical candidate, but the Council record does not establish that every required interpretation was correct.

Two Production replies overstate the scenario evidence. Growing-space totals stay fixed, but Lean and Balanced change allocation composition by crop. The scenario changes delay and yield together and reruns the allocator, so a sole-cause attribution to reduced yield is not identifiable.

## Method

1. Freeze the V9 run, hashes, messages, events, references, validation states, strategy outputs, policy record, and research controls.
2. Split every response into independently checkable assertions, including caveats and causal language.
3. Recompute universal comparisons from all strategies and relevant order lines. Selected references are citations, not the whole evidence universe.
4. Use one authenticated, read-only GET of the persisted V9 scenario to inspect baseline/result allocations omitted from the public conversation projection. Only aggregate crop counts are retained; no credential was retained.
5. Classify each assertion and its containing message, then compare semantic results with application validation and automated scoring without changing either scorer.

A references_verified state proves known-reference membership, value rendering, response shape, and local guard results. It does not prove arbitrary prose entailment. The planning artifact expressly records qualitative_prose_verified as false.

## Frozen numerical evidence

### Planning run

| Strategy | Booked requested kg | Booked delivered kg | Fully delivered booked lines | Fill rate | Total shortfall kg | Waste kg | Margin SGD |
|---|---:|---:|---:|---:|---:|---:|---:|
| Lean | 824 | 370 | 14/32 | 0.4375 | 612.02 | 153.99 | 2467.60 |
| Balanced | 824 | 446 | 17/32 | 0.5340 | 507.01 | 175.99 | 2930.59 |
| Resilient | 824 | 518 | 20/32 | 0.6213 | 412.01 | 220.98 | 3193.15 |

Booked demand exceeds booked delivery for Lean by 454 kg, Balanced by 378 kg, and Resilient by 306 kg. Planning Demand is correct. Planning Supply directly contradicts the same record.

### Conversation scenario

The frozen controls delay batch-01 by 3 days and reduce its yield setting to 90%; demand, labour, and cash controls remain at 100%. Every policy remains FEASIBLE in both states.

| Policy | Δ fill | Δ harvest kg | Δ booked delivered kg | Δ shortfall kg | Δ margin SGD | Δ labour h | Δ area m² | Δ closing stock kg |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Lean | -0.0248 | -9.52 | -28.00 | +27.00 | -80.53 | -0.66 | +0.00 | +0.00 |
| Balanced | -0.0267 | -7.52 | -26.00 | +29.01 | -129.26 | -0.52 | +0.00 | +13.00 |
| Resilient | -0.0285 | -3.52 | -24.00 | +31.00 | -177.87 | -0.24 | +0.00 | +0.00 |

Requested booked quantity remains 824 kg for every policy. Delivery losses occur on 2 Lean, 3 Balanced, and 1 Resilient affected lines; other lines can remain unchanged or gain allocations. The Supply conversation claim that some orders lose delivery is accurate.

### Allocation-composition check

| Policy | Baseline counts: caixin / pak choi / kailan / lettuce | Scenario counts | Mix unchanged? | Area unchanged? |
|---|---|---|---|---|
| Lean | 3 / 4 / 3 / 4 | 3 / 3 / 3 / 5 | No | Yes |
| Balanced | 4 / 5 / 3 / 5 | 4 / 4 / 4 / 5 | No | Yes |
| Resilient | 6 / 5 / 4 / 5 | 6 / 5 / 4 / 5 | Yes | Yes |

The crop-ID set remains the same, but crop mix ordinarily includes allocation composition. On that meaning both Production claims are false for Lean and Balanced. Because delay, yield and replanning occur together, the comparison does not isolate a sole cause.

## Application validation and automated scoring

The frozen automated suite reports 12 passes and 6 failures. Two failures are real application-contract failures: Weather and Market abstentions attach numerical facts and receive abstention_payload. Four are conservative keyword or reference-prefix misses:

- Planning Demand uses strategy metrics while the scorer expects another prefix; all strategy totals support the claim.
- Council Supply uses comparison totals while the scorer expects another prefix; the full delivery lines support the claim.
- Council Chair says “policy” without the expected “plan” or “strategy” token; its comparisons are correct.
- Research Chair says “excluded from booked commitments” without repeating “unconfirmed”; the research record supports it.

The inverse failure matters more: automated checks pass Planning Supply and both Production crop-mix contradictions. This follows the suite’s declared scope. Phrase and reference checks are guards, not general semantic verification.

## Case-by-case assertion audit
### 1. planning:planning:0:demand_analyst

**Record:** reports/v9/planning-public.json · **Application:** validated / grounded_facts_qualitative_unverified · **Automated:** FAIL · **Semantic:** sound

> Booked demand exceeds planned deliveries for every strategy; fill ratios differ across strategies, with residual forecasts only partly covered and unfilled demand recorded in each. Values are synthetic calculations, not observed market demand.

| Assertion | Finding | Record evidence |
|---|---|---|
| Booked demand exceeds planned deliveries for every strategy. | **sound** | Requested/delivered kg: Lean 824/370, Balanced 824/446, Resilient 824/518. |
| Fill ratios differ across strategies. | **sound** | Lean 0.4375, Balanced 0.5340, Resilient 0.6213. |
| Residual forecasts are only partly covered and every strategy records unfilled demand. | **sound** | Residual requested/delivered kg: 264.032/106.014, 264.032/135.017, 264.032/158.020; total shortfalls: 612.02, 507.01, 412.01 kg. |
| The values are synthetic calculations rather than observed market demand. | **sound** | Run data_mode is synthetic_demo; price status is booked-weighted synthetic input and source snapshot is empty. |

**Citation and scope limit:** Selected refs omit Lean requested/delivered, Resilient requested, all residual metrics and one fill/shortfall value; the full frozen run supports the prose. Automated expected-reference failure is a prefix-rule false negative.

### 2. planning:planning:1:weather_analyst

**Record:** reports/v9/planning-public.json · **Application:** validated / qualitative_unverified · **Automated:** PASS · **Semantic:** sound

> Site weather evidence is absent, so no supported environmental adjustment or yield conclusion can be drawn; the numerical plan carries no weather adjustment.

| Assertion | Finding | Record evidence |
|---|---|---|
| Site weather evidence is absent. | **sound** | source_snapshot is empty and source:site_weather_availability says absent. |
| No environmental adjustment or yield conclusion is supported. | **sound** | The required interpretation requires abstention from weather feasibility/yield claims. |
| The numerical plan carries no weather adjustment. | **sound** | The frozen mission context explicitly records no weather adjustment. |

**Citation and scope limit:** This proves absence in the frozen application context, not absence of real weather or environmental risk.

### 3. planning:planning:2:market_analyst

**Record:** reports/v9/planning-public.json · **Application:** validated / qualitative_unverified · **Automated:** PASS · **Semantic:** sound

> Supplied buyer, grower, and observed-price evidence is absent, so no market reaction, opportunity, marginal-return, or cross-strategy comparison is supported; internal plan metrics are not substituted.

| Assertion | Finding | Record evidence |
|---|---|---|
| Buyer, grower and observed-price evidence is absent. | **sound** | market_signals is unavailable/not connected with no observations. |
| Market reaction, opportunity, marginal return and cross-strategy market comparisons are unsupported. | **sound** | No supplied market observations exist; internal plan metrics are not market observations. |
| Internal plan metrics are not substituted. | **sound** | The absent-market role context contains no internal typed metrics. |

**Citation and scope limit:** The statement concerns observed/external market evidence; the frozen plan still contains synthetic booked-price inputs.

### 4. planning:planning:3:production_analyst

**Record:** reports/v9/planning-public.json · **Application:** validated / grounded_facts_qualitative_unverified · **Automated:** PASS · **Semantic:** sound_with_limits

> Balanced schedule shows declared sow-to-harvest lead times with no declared hard-constraint violation, so recipe timing and space feasibility are supported only against declared constraints.

| Assertion | Finding | Record evidence |
|---|---|---|
| Balanced contains declared sow-to-harvest schedule dates. | **sound** | Balanced has 17 allocations; sampled batch-01 includes sow and harvest dates. |
| No declared hard-constraint violation is reported. | **sound** | Balanced status is FEASIBLE and violations is empty. |
| Timing and space feasibility are supported only against declared constraints. | **sound_with_limits** | The caveat matches the validator scope; it does not cover biology, weather or unmodelled constraints. |

**Citation and scope limit:** The selected refs sample one allocation and total area, so they do not independently prove every schedule row; full frozen allocations and empty violations support only declared-model feasibility.

### 5. planning:planning:4:supply_chain_analyst

**Record:** reports/v9/planning-public.json · **Application:** validated / grounded_facts_qualitative_unverified · **Automated:** PASS · **Semantic:** contradiction

> Across the strategies, the frozen plans leave unfilled demand and projected disposed quantity nonzero, while booked order routing is fully delivered and no declared hard-constraint violation is reported. Per-order routing feasibility therefore does not imply complete demand coverage; the recipe timing constraint states new sowing cannot meet an earlier delivery.

| Assertion | Finding | Record evidence |
|---|---|---|
| Every strategy has nonzero unfilled demand and projected disposal. | **sound** | Shortfall kg: 612.02, 507.01, 412.01; waste kg: 153.99, 175.99, 220.98. |
| Booked order routing is fully delivered. | **contradiction** | Booked requested is 824 kg for each strategy, but delivered is 370, 446 and 518 kg. Only 14/32, 17/32 and 20/32 booked lines are fully delivered. |
| No declared hard-constraint violation is reported. | **sound** | All three strategies are FEASIBLE with empty violation arrays. |
| Per-order routing feasibility does not imply complete demand coverage. | **sound_with_limits** | The logical distinction is valid, but the artifact does not define a transport-routing feasibility model. |
| New sowing cannot satisfy a delivery before its recipe harvest date. | **sound** | forecast:lead_times states this exact declared timing constraint. |

**Citation and scope limit:** Material contradiction. The cited booked_delivered metric states an amount, not total fulfillment; booked_requested was omitted. Demand correctly states the opposite. The format repair removed a count but preserved the false meaning, and V4 validation accepted it.

### 6. planning:planning:5:profit_analyst

**Record:** reports/v9/planning-public.json · **Application:** validated / grounded_facts_qualitative_unverified · **Automated:** PASS · **Semantic:** sound

> Rendered synthetic strategy metrics show Resilient carrying the largest modeled margin, followed by Balanced and Lean; these are calculated values under the synthetic booked-price assumption, not observed market outcomes.

| Assertion | Finding | Record evidence |
|---|---|---|
| Resilient has the largest modeled margin, followed by Balanced and Lean. | **sound** | Margins SGD: Resilient 3193.15, Balanced 2930.59, Lean 2467.60. |
| Margins are calculated under a synthetic booked-price assumption and are not observed outcomes. | **sound** | Run is synthetic_demo and policy:price_status_meaning defines the price as synthetic. |

**Citation and scope limit:** This ranking is arithmetic within the frozen model; it is not a profitability forecast validated against real costs or prices.

### 7. planning:planning:6:planning_chair

**Record:** reports/v9/planning-public.json · **Application:** validated / grounded_facts_qualitative_unverified · **Automated:** PASS · **Semantic:** sound_with_limits

> The server policy names Balanced as the numerical candidate before the Council gate; its declared hard-constraint result reports no violation, and required review by itself does not withhold acceptance. Synthetic fill, shortfall, and margin values remain modeled calculations, not observed outcomes, so acceptance stays policy-driven rather than evidence of demand coverage.

| Assertion | Finding | Record evidence |
|---|---|---|
| Server policy names Balanced as candidate before the Council gate. | **sound** | balanced-service-margin-id-v1 ranks the eligible Balanced name first; accepted_strategy_id is Balanced. |
| Balanced has no declared hard-constraint violation. | **sound** | Balanced is FEASIBLE with an empty violations array. |
| Required review alone does not withhold acceptance. | **sound** | The frozen policy record explicitly sets review_completion_alone_requires_withholding false. |
| Acceptance is policy-driven and does not establish demand coverage. | **sound_with_limits** | Balanced fill is 0.5340 with 507.01 kg shortfall; acceptance is simulation_only. |

**Citation and scope limit:** The conclusion accurately describes server policy, not an expert endorsement. It inherited the Supply finding only as qualitative-unverified evidence; no full entailment check ran.

### 8. conversation:direct:0:production_analyst

**Record:** reports/v9/conversation-public-replay.json · **Application:** references_verified / grounded_facts_qualitative_unverified · **Automated:** PASS · **Semantic:** sound

> The frozen trial applies a delayed batch at reduced yield; each policy still simulates as feasible, while fill rate and harvest decline under every policy. These are synthetic scenario-minus-baseline deltas, not observed effects, and no biological cause is established.

| Assertion | Finding | Record evidence |
|---|---|---|
| The trial delays a batch and reduces its yield. | **sound** | Controls: batch-01 delay 3 days and yield 90%. |
| Every policy remains feasible. | **sound** | Baseline and scenario statuses are FEASIBLE for Lean, Balanced and Resilient. |
| Fill rate and harvest decline under every policy. | **sound** | Fill deltas -0.0248/-0.0267/-0.0285; harvest deltas -9.52/-7.52/-3.52 kg. |
| Results are synthetic and establish no biological cause. | **sound** | Snapshot data_mode is synthetic_demo and combines two controls with replanning. |

**Citation and scope limit:** Selected refs include only Balanced fill delta and status examples; the full comparison supports the universal claim.

### 9. conversation:invite:0:demand_analyst

**Record:** reports/v9/conversation-public-replay.json · **Application:** references_verified / grounded_facts_qualitative_unverified · **Automated:** PASS · **Semantic:** sound

> Mei's point on feasibility does not settle booked demand: the frozen comparison shows booked delivered quantities falling under every policy even though requested quantities are unchanged. These are synthetic scenario-minus-baseline deltas, so the shortfall is a modelled gap, not an observed loss.

| Assertion | Finding | Record evidence |
|---|---|---|
| Feasibility does not settle booked-demand coverage. | **sound** | All policies remain FEASIBLE while booked delivery falls. |
| Booked delivered quantity falls under every policy while requested quantity is unchanged. | **sound** | Booked-delivered deltas: Lean -28, Balanced -26, Resilient -24 kg; booked-requested deltas are zero. |
| The gap is modeled rather than an observed loss. | **sound** | Synthetic scenario-minus-baseline comparison. |

**Citation and scope limit:** The model selected all delivered deltas but omitted requested-delta refs; the full comparison supplies them.

### 10. conversation:invite:1:production_analyst

**Record:** reports/v9/conversation-public-replay.json · **Application:** references_verified / grounded_facts_qualitative_unverified · **Automated:** PASS · **Semantic:** contradiction

> The crop mix and growing space are unchanged across policies; the delayed batch carries reduced yield, so the frozen comparison shows harvest falling while feasibility still holds. That gap is a synthetic scenario-minus-baseline result, not an observed shortfall or cause.

| Assertion | Finding | Record evidence |
|---|---|---|
| Crop mix is unchanged across policies. | **contradiction** | Authenticated frozen scenario shows Lean allocation counts by crop 3/4/3/4 to 3/3/3/5 and Balanced 4/5/3/5 to 4/4/4/5; only Resilient is unchanged. The set of four crop IDs remains the same, but the mix does not. |
| Growing space is unchanged. | **sound** | Area deltas are zero for Lean, Balanced and Resilient. |
| The delayed batch has reduced yield. | **sound** | Controls delay batch-01 and reduce expected marketable quantity from 35.20 to 31.680 kg. |
| Harvest falls and feasibility remains. | **sound** | Harvest deltas are negative and all scenario statuses are FEASIBLE. |
| The result is synthetic and establishes no observed cause. | **sound** | It is a synthetic scenario comparison. |

**Citation and scope limit:** Material wording error if crop mix means allocation composition, its ordinary planning meaning. If it means only the set of crop IDs, that narrower claim is true.

### 11. conversation:council:0:demand_analyst

**Record:** reports/v9/conversation-public-replay.json · **Application:** references_verified / grounded_facts_qualitative_unverified · **Automated:** PASS · **Semantic:** sound_with_limits

> On booked demand, all policies request the same quantities while scenario delivered quantities fall under each policy; the gap is largest under Lean, then Balanced, then Resilient by delivered margin. These are synthetic within-policy deltas, not observed losses, and no policy is claimed sufficient.

| Assertion | Finding | Record evidence |
|---|---|---|
| Booked requested quantity is unchanged and delivered quantity falls for every policy. | **sound** | Requested deltas are zero; delivered deltas are -28, -26 and -24 kg. |
| The delivered drop ranks Lean, Balanced, Resilient from largest to smallest. | **sound_with_limits** | Absolute drops are 28, 26 and 24 kg. “Delivered margin” is undefined and could be confused with profit margin. |
| These are synthetic within-policy deltas and no policy is claimed sufficient. | **sound** | All scenario booked delivery totals remain below 824 kg requested. |

**Citation and scope limit:** The selected refs support delivered changes but omit requested deltas and total sufficiency.

### 12. conversation:council:1:weather_analyst

**Record:** reports/v9/conversation-public-replay.json · **Application:** unsupported / unsupported · **Automated:** FAIL · **Semantic:** sound_with_limits

> Weather context is unavailable for this frozen snapshot, so I cannot speak to observed conditions or environmental uncertainty. The frozen comparison shows fill-rate and harvest deltas applying under every policy, with no cause established.

| Assertion | Finding | Record evidence |
|---|---|---|
| Weather context is unavailable, so observed conditions/environmental uncertainty cannot be assessed. | **sound** | weather:source_context is unavailable and warns against current-condition claims. |
| Fill-rate and harvest deltas occur under every policy. | **sound** | All six relevant deltas are negative. |
| No cause is established. | **sound** | The frozen comparison is synthetic and has no weather evidence. |

**Citation and scope limit:** Application status is unsupported because an abstention attached internal fact refs (abstention_payload). The numerical clauses are true but outside the absent-weather role; this scope contamination should be removed rather than treated as weather evidence.

### 13. conversation:council:2:market_analyst

**Record:** reports/v9/conversation-public-replay.json · **Application:** unsupported / unsupported · **Automated:** FAIL · **Semantic:** sound_with_limits

> As the market specialist, I have no connected community or buyer evidence for this frozen snapshot, so I cannot speak to prices or demand. The frozen comparison shows revenue and margin deltas are scenario-minus-baseline synthetic results, not observed market reactions.

| Assertion | Finding | Record evidence |
|---|---|---|
| No connected community or buyer evidence is available. | **sound** | market signals are not_connected with zero observations. |
| Observed/current prices or demand cannot be assessed. | **sound_with_limits** | Correct for external market evidence; the wording is overbroad because synthetic contract prices and booked quantities exist. |
| Revenue and margin deltas are synthetic, not observed market reactions. | **sound** | Revenue and margin deltas exist for all policies and data_mode is synthetic_demo. |

**Citation and scope limit:** Application status is unsupported because an abstention attached internal fact refs. The numeric sentence is true but should not be attached to the required market abstention.

### 14. conversation:council:3:production_analyst

**Record:** reports/v9/conversation-public-replay.json · **Application:** references_verified / grounded_facts_qualitative_unverified · **Automated:** PASS · **Semantic:** contradiction

> Production view: the crop mix and growing space are unchanged under every policy, so the harvest and fill-rate deltas come from the delayed batch's reduced yield, not from more area. Feasibility still holds; these are synthetic within-policy deltas, not observed outcomes.

| Assertion | Finding | Record evidence |
|---|---|---|
| Crop mix and growing space are unchanged under every policy. | **contradiction** | Area is unchanged, but Lean and Balanced allocation composition changes; only Resilient crop counts are unchanged. |
| Harvest and fill deltas come from the delayed batch’s reduced yield and not more area. | **unsupported** | Area did not increase, but delay and yield changed together and replanning changed crop allocation, so the artifact cannot isolate a sole cause. |
| Feasibility remains and outcomes are synthetic. | **sound** | All scenario statuses are FEASIBLE; data_mode is synthetic_demo. |

**Citation and scope limit:** The automatic scorer passed this case because its phrase and reference checks do not test crop allocation composition or causal entailment.

### 15. conversation:council:4:supply_chain_analyst

**Record:** reports/v9/conversation-public-replay.json · **Application:** references_verified / grounded_facts_qualitative_unverified · **Automated:** FAIL · **Semantic:** sound

> Supply-chain view: the frozen delivery lines show requested quantities unchanged while scenario delivered quantities drop for some orders, so availability losses are modelled allocations, not observed. Logistics data on transport timing is absent, so I cannot attribute these gaps to delivery scheduling.

| Assertion | Finding | Record evidence |
|---|---|---|
| Requested quantities are unchanged while some delivery lines lose delivered quantity. | **sound** | Every affected line retains its request; drops occur on 2 Lean, 3 Balanced and 1 Resilient line, alongside unchanged and some increased lines. |
| Availability losses are modeled allocations, not observations. | **sound** | The records are synthetic lot allocations in a scenario result. |
| Transport-timing data is absent, so the gaps cannot be attributed to delivery scheduling. | **sound** | The frozen context contains order due dates and harvest lots but no transport/logistics observations. |

**Citation and scope limit:** Automated expected-reference failure is a prefix-rule false negative: the case used comparison metrics while the scorer required a different prefix. The prose remains sound against full delivery lines.

### 16. conversation:council:5:profit_analyst

**Record:** reports/v9/conversation-public-replay.json · **Application:** references_verified / grounded_facts_qualitative_unverified · **Automated:** PASS · **Semantic:** sound

> Both closing stock and cost deltas differ across policies, but only Balanced shows a nonzero stock change; labour falls slightly under each. These are synthetic scenario-minus-baseline results, not observed effects, and they say nothing about causes or market reaction.

| Assertion | Finding | Record evidence |
|---|---|---|
| Closing-stock and cost deltas differ by policy. | **sound** | Closing-stock deltas 0/13/0 kg; cost deltas -3.47/-7.74/-8.13 SGD. |
| Only Balanced has a nonzero closing-stock delta. | **sound** | Balanced +13 kg; Lean and Resilient zero. |
| Labour falls slightly under every policy. | **sound** | Labour-hour deltas -0.66/-0.52/-0.24. |
| The synthetic deltas establish neither causes nor market reaction. | **sound** | No observed market evidence or controlled single-factor causal design exists. |

**Citation and scope limit:** Selected refs cover stock only; cost and labour assertions require the full comparison.

### 17. conversation:council:6:planning_chair

**Record:** reports/v9/conversation-public-replay.json · **Application:** references_verified / grounded_facts_qualitative_unverified · **Automated:** FAIL · **Semantic:** sound

> Closing position: each policy stays feasible, yet all show lower fill rate, lower margin and greater shortfall relative to its own baseline; Resilient holds the highest fill rate and margin in both states. These are synthetic within-policy deltas, so no policy is a causal winner.

| Assertion | Finding | Record evidence |
|---|---|---|
| Every policy stays feasible. | **sound** | All baseline and scenario statuses are FEASIBLE. |
| Every policy has lower fill and margin and greater shortfall than baseline. | **sound** | All fill and margin deltas are negative; shortfall deltas are +27.00/+29.01/+31.00 kg. |
| Resilient has the highest fill and margin in baseline and scenario. | **sound** | Fill 0.6213/0.5928 and margin 3201.87/3024.00 exceed both alternatives in each state. |
| No causal winner follows from synthetic within-policy deltas. | **sound** | The scenario is not a controlled comparison of all causal factors. |

**Citation and scope limit:** Automated role-relevance failure is a keyword false negative (“policy” without “plan” or “strategy”). Selected refs are incomplete for all universal comparisons, but full context supports them.

### 18. research:research:0:planning_chair

**Record:** reports/v9/research-public.json · **Application:** references_verified / grounded_facts_qualitative_unverified · **Automated:** FAIL · **Semantic:** sound

> The bed reservation is research-only and not an operational change; the extra order is explicitly excluded from booked commitments and is not observed demand. Both remain planning evidence only.

| Assertion | Finding | Record evidence |
|---|---|---|
| The bed reservation is research-only and not an operational change. | **sound** | research:reservation:bed-04 has kind research_only_bed_reservation and operational_execution false; report says main_farm_unchanged true. |
| The extra order is excluded from booked commitments and is not observed demand. | **sound** | research:unconfirmed_order:research-extra-order records excluded_from_booked_commitments true and observed_demand false. |
| Both inputs remain planning evidence only. | **sound** | Research calculation operates on a copy and the public report states no farm mutation. |

**Citation and scope limit:** Automated role-relevance failure is an exact-keyword false negative: the prose says “excluded from booked commitments” without repeating “unconfirmed”. Date fact refs do not prove the qualitative claims; the two qualitative tool refs and frozen research controls do.

## Recorded repair attempts

The 21 provider calls comprise 9 planning calls, 11 conversation calls, and 1 research call. Eighteen final messages appear above. Two rejected responses preserve reviewable prose:

- Planning Supply event 25 first says “each booked order is fully delivered.” It has the same contradiction as the final response. The server rejects it only for a number word; format repair removes the count and preserves the false meaning.
- Conversation event 5 has the same substantively sound interpretation as the final direct reply. It is rejected only for a number word.

The malformed Planning Chair response behind the ninth planning call is unavailable. Event 36 preserves only a schema-repair notice, so its original semantics cannot be reviewed.

## Implications and next acceptance tests

The bounded V10 candidate fix adds code-derived booked requested, delivered, shortfall, and coverage state to Supply context. It rejects clear positive total/full-booked-fulfillment language when the relevant frozen strategy has positive booked shortfall. This semantic issue is outside format-only repair codes and consumes no format repair. Focused positive, truthful-negative, mixed-strategy, and no-repair tests cover the V9 failure.

The guard is deliberately narrow and does not establish general entailment. The next iteration should:

1. Re-run this planning input and require false full fulfillment to be rejected while truthful “not fully delivered” phrasing passes.
2. Supply code-derived crop-composition deltas, or forbid “crop mix unchanged” unless every policy’s allocation multiset matches.
3. Reject sole-cause language when multiple controls change or replanning changes allocation composition.
4. Give absent Weather and Market roles only the availability record and require a fact-free abstention.
5. Test valid-but-insufficient selected refs for universal claims and require support from every compared strategy.
6. Require independent human expert review before synthetic interpretations become real-world farm advice.

## Limits
- AI-assisted review can detect record contradictions and missing support but is not an independent human expert assessment.
- Synthetic model consistency does not establish agronomic realism, causal validity, market validity, profitability, logistics feasibility, or safe real-farm action.
- A selected typed reference verifies membership/value rendering, not that prose follows from it.
- The phrase scorer is intentionally conservative and is neither a semantic oracle nor a substitute for reviewing full frozen context.
- The authenticated allocation read was GET-only; no provider call, calculation, deployment or farm mutation was performed.

These findings concern frozen V9 software records observed on 2026-09-11. They do not validate crop biology, weather response, customer demand, transport operations, accounting, or outcomes on a real farm.
