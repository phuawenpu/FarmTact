# V10 AI-assisted semantic review

> **Status:** AI-assisted consistency review completed 2026-09-11. This is not a human agronomy, logistics, market, accounting, or ML-expert review. The review made no provider calls, calculations, farm mutations, deployments, or capacity bypasses.

This report audits every final response in the V10 Council-only actual trial. Sources are [conversation-public-replay.json](./conversation-public-replay.json), [conversation-public-events.json](./conversation-public-events.json), [conversation-public.json](./conversation-public.json), and the separate capacity result in [planning-public.json](./planning-public.json). Exact message IDs, references, and atomic findings are in [ai-assisted-semantic-review.json](./ai-assisted-semantic-review.json).

## Result

| Semantic result | Count | Cases |
|---|---:|---|
| Sound | 2 | Weather, Market |
| Sound with limits | 4 | Demand, Production, Supply, Chair |
| Contradiction | 1 | Profit |

Weather and Market demonstrate the intended V10 correction: both are clean, fact-free, references-verified abstentions. Supply is semantically supportable within a narrow timing interpretation, but the application correctly marks it unsupported because its prose authors the quantity “zero.”

Profit contains the material contradiction. Lean margin falls by SGD 52.87; it does not gain. Chair correctly says margins fall for every policy and Lean has the smallest decline.

## Frozen comparison

The scenario delays batch-01 by 3 days and applies 90% yield. Demand, labour, and cash controls remain at 100%. Every policy is FEASIBLE in baseline and scenario.

| Policy | Δ fill | Δ harvest kg | Δ booked delivered kg | Δ shortfall kg | Δ cost SGD | Δ margin SGD |
|---|---:|---:|---:|---:|---:|---:|
| Lean | -0.0230 | -2.40 | -22.00 | +25.00 | +13.88 | -52.87 |
| Balanced | -0.0303 | -0.40 | -20.00 | +33.01 | -9.39 | -225.61 |
| Resilient | -0.0285 | -4.40 | -22.00 | +31.00 | -9.00 | -177.00 |

Booked requested quantity stays at 824 kg for every policy. The earliest affected booked line, order-0-0, is due 2026-09-14. In every baseline it receives 22 kg from batch-01 harvested that day. In every scenario batch-01 harvest moves to 2026-09-17, the line receives zero, and the delayed batch supplies no order allocation.

Most affected later policy-lines remain fully met: Lean 6/7, Balanced 9/11, and Resilient 11/11. The phrase “later orders stay met in most policies” is directionally supported but ambiguous because Lean and Balanced each have later misses.

## Method

1. Split all seven final replies into 26 independently checkable assertions.
2. Compare universal and comparative prose with all policy metrics and affected delivery lines, not only model-selected references.
3. Make one authenticated, read-only GET of the immutable V10 scenario for batch-to-order allocation detail omitted from the public replay projection. No secret was printed or retained.
4. Keep semantic correctness distinct from response validation.
5. Review both rejected format attempts, while making no paid inference request.

## Case audit
### 1. demand_analyst

**Message:** 73cfded9c5192e22a0217c6d280d3215 · **Application:** references_verified / grounded_facts_qualitative_unverified · **Semantic:** sound_with_limits

> Booked demand is identical across policies, yet scenario booked deliveries fall in every policy versus baseline, so the delay leaves booked orders short. Limit: these are synthetic policy comparisons, not observed outcomes.

| Assertion | Finding | Full-record evidence |
|---|---|---|
| Booked requested demand is identical across policies. | **sound** | Baseline and scenario booked requested quantity is 824 kg for Lean, Balanced and Resilient; every requested delta is zero. |
| Scenario booked delivery falls for every policy. | **sound** | Booked-delivery deltas are Lean -22 kg, Balanced -20 kg and Resilient -22 kg. |
| The delay leaves booked orders short. | **sound_with_limits** | The delayed batch moves from 2026-09-14 to 2026-09-17, and the 2026-09-14 booked line falls from 22 kg delivered to zero in every policy. Because yield also changes and the allocator reruns, the delay alone does not explain every aggregate delivery delta. |
| The comparison is synthetic rather than observed. | **sound** | Snapshot data_mode is synthetic_demo. |

**Citation and scope limit:** Selected refs cover all booked-delivery deltas but omit booked-requested deltas and the affected order record. Full frozen context supports the comparison; causal scope should be limited to the near-term line.

### 2. weather_analyst

**Message:** c9afdacd79f7a5bc9e76c95fba73e8e7 · **Application:** references_verified / qualitative_unverified · **Semantic:** sound

> No frozen public weather observation is supplied for this experiment, so I cannot assess conditions or their uncertainty. Any comparison across the policies would exceed that evidence limit; abstaining.

| Assertion | Finding | Full-record evidence |
|---|---|---|
| No frozen public weather observation is supplied. | **sound** | weather source context is unavailable. |
| Observed conditions and their uncertainty cannot be assessed. | **sound** | No weather observations, forecast or uncertainty record is present. |
| Cross-policy weather interpretation would exceed the evidence, so the role abstains. | **sound** | The response remains within the Weather role and contains no numerical plan facts. |

**Citation and scope limit:** This is a clean fact-free abstention under conversation context v6 and validator v5. “Any comparison” is read within the Weather role; numerical plan comparison exists for other roles.

### 3. market_analyst

**Message:** b8a05514c5a857d2966d63f526c70727 · **Application:** references_verified / qualitative_unverified · **Semantic:** sound

> No connected frozen community-market observation is available, so market consequences cannot be assessed. This abstains for lack of that source, not from evidence of no effect.

| Assertion | Finding | Full-record evidence |
|---|---|---|
| No connected frozen community-market observation is available. | **sound** | Market status is not_connected with zero observations. |
| Market consequences cannot be assessed. | **sound** | There is no observed buyer/community response evidence. |
| Missing evidence is not evidence of no effect. | **sound** | The abstention correctly avoids converting source absence into a market conclusion. |

**Citation and scope limit:** This is a clean fact-free abstention. It does not deny synthetic booked quantities or contract-price inputs; it declines observed market interpretation.

### 4. production_analyst

**Message:** a437a4202d2bdb3a424df8a4f96a10b6 · **Application:** references_verified / grounded_facts_qualitative_unverified · **Semantic:** sound_with_limits

> The delay leaves the delayed batch's harvest unsold in the near-term order across policies, while later orders stay met in most policies. Limits: these are synthetic scenario-minus-baseline deltas, not observed outcomes. Relevant metrics are fill rate and harvest weight.

| Assertion | Finding | Full-record evidence |
|---|---|---|
| The delayed batch's harvest is unsold in the near-term order across policies. | **sound** | In every baseline policy batch-01 harvests 44 kg on 2026-09-14 and supplies 22 kg to order-0-0; in every scenario it harvests 39.6 kg on 2026-09-17, supplies no order line, and order-0-0 delivery is zero. |
| Later orders stay met in most policies. | **sound_with_limits** | Among affected later policy-lines, 6/7 Lean, 9/11 Balanced and 11/11 Resilient are fully met. The wording is ambiguous: not every later order remains met for Lean or Balanced. |
| The deltas are synthetic rather than observed. | **sound** | The scenario is synthetic_demo. |
| Fill rate and harvest weight are relevant metrics. | **sound** | Both metrics decline for every policy. |

**Citation and scope limit:** The selected refs only show harvest deltas. They do not prove sale/allocation or later-order claims; those require full persisted order allocations and affected delivery lines inspected through the read-only scenario GET.

### 5. supply_chain_analyst

**Message:** 0b2419ace351cfc2d3c49b1a8382083a · **Application:** unsupported / unsupported · **Semantic:** sound_with_limits

> Delivery timing is the binding issue: the delayed batch's near-term booked line drops to zero delivered in all policies, while later dated lines remain filled in most policies. This is a synthetic comparison, not an observed outcome.

| Assertion | Finding | Full-record evidence |
|---|---|---|
| Delivery timing is the binding issue for the delayed near-term line. | **sound_with_limits** | The booked line is due 2026-09-14; its baseline lot comes from batch-01 harvested that day, while the scenario batch harvests 2026-09-17. This supports timing for that line, not every aggregate loss. |
| The delayed batch's near-term booked line drops to zero delivered in all policies. | **sound** | order-0-0 delivery changes 22 kg to zero for Lean, Balanced and Resilient. |
| Later dated lines remain filled in most policies. | **sound_with_limits** | Most affected later policy-lines are filled: Lean 6/7, Balanced 9/11, Resilient 11/11. Some later Lean and Balanced lines are unfilled. |
| The comparison is synthetic, not observed. | **sound** | Snapshot data_mode is synthetic_demo. |

**Citation and scope limit:** Application status is unsupported because “zero” is a model-authored quantity. Selected fact refs are fill-rate deltas rather than the order-line facts needed for the prose. Full frozen context supports the narrow timing statement, but validator v5 does not verify that entailment.

### 6. profit_analyst

**Message:** 16d27ed18cee1ce95988fd5f275a063a · **Application:** references_verified / grounded_facts_qualitative_unverified · **Semantic:** contradiction

> Cost and margin effects differ by policy: Lean shows a small margin gain versus both Balanced and Resilient, which each show margin losses. Limit: these are synthetic scenario-minus-baseline deltas, not observed outcomes.

| Assertion | Finding | Full-record evidence |
|---|---|---|
| Cost and margin effects differ by policy. | **sound** | Cost deltas are +13.88, -9.39 and -9.00 SGD; margin deltas are -52.87, -225.61 and -177.00 SGD. |
| Lean shows a small margin gain. | **contradiction** | Lean margin falls from 2467.60 to 2414.73 SGD, a -52.87 SGD delta. |
| Balanced and Resilient show margin losses. | **sound** | Their margin deltas are -225.61 and -177.00 SGD. |
| The values are synthetic, not observed. | **sound** | Snapshot data_mode is synthetic_demo. |

**Citation and scope limit:** Material contradiction despite correct selected margin references and references_verified status. The following Chair response correctly states that every margin falls.

### 7. planning_chair

**Message:** 3b74bd2076275f645b9b89e4f62909d9 · **Application:** references_verified / grounded_facts_qualitative_unverified · **Semantic:** sound_with_limits

> Across policies, scenario fill rates sit below their baselines and shortfalls rise, with Resilient highest and Lean lowest. Margins fall under all policies, though Lean's decline is smallest. These are synthetic deltas, not observed effects.

| Assertion | Finding | Full-record evidence |
|---|---|---|
| Every scenario fill rate is below baseline and every shortfall rises. | **sound** | Fill deltas are -0.0230, -0.0303 and -0.0285; shortfall deltas are +25.00, +33.01 and +31.00 kg. |
| Resilient is highest and Lean lowest. | **sound_with_limits** | This is true for scenario fill rate: 0.5928 versus 0.5037 and 0.4145. It is false for shortfall, where Resilient is lowest and Lean highest; the sentence does not name the ranked metric. |
| Margins fall under all policies and Lean has the smallest decline. | **sound** | Margin deltas are Lean -52.87, Balanced -225.61, Resilient -177.00 SGD. |
| The deltas are synthetic, not observed effects. | **sound** | Snapshot data_mode is synthetic_demo. |

**Citation and scope limit:** Selected refs contain only fill-rate deltas, so shortfall and margin assertions require the full frozen comparison. The margin statement correctly contradicts the Profit response, but the Chair does not explicitly rebut it.

## Repair and validation behavior

The request uses 9 provider calls for 7 final messages:

- Weather’s first response is substantively sound but rejected for the model-authored number word in “three policies.” Its repaired response removes the count and validates without facts.
- Production’s first response has the same limited meaning as its final response but puts a typed fact in context references. The repaired response validates.
- Supply arrives after both bounded repairs are spent. It remains preserved as unsupported because “zero” is a model-authored quantity.

The Production references verify only harvest deltas. The sale/allocation and later-order assertions require records the model did not select. Full frozen context supports the core observation, but references-verified remains a structural result rather than a prose-entailment result.

Chair’s phrase “with Resilient highest and Lean lowest” is true for fill rate and false for shortfall. Because the sentence names both metrics and never identifies which one is ranked, the review treats it as sound with an ambiguity limit.

## Separate V10 mission capacity result

The V10 planning run is REVIEW_WITHHELD with Council status blocked, no claims, and no inference-audit entries. The shared daily ledger had 41 calls used and only 7 remaining; a required mission must reserve 9 calls, so preflight stopped it before any provider request.

This is useful negative budget evidence. It is not a live provider test of the new mission Supply fulfillment guard, and no additional paid call or capacity bypass should be inferred.

## Required follow-up

1. Add a deterministic sign guard for margin language such as gain, rise, loss, and fall when the selected delta sign is known.
2. Require the Chair to name the metric in ranking clauses when several differently ordered metrics share a sentence.
3. Give Production and Supply exact affected-order and batch-allocation facts when the prompt asks them to discuss sale or timing.
4. Prefer “the near-term line misses delivery after the harvest-date shift” over claiming the delay explains every aggregate change; delay, yield, and replanning occur together.
5. Keep the V10 absent-source context projection that produced clean Weather and Market abstentions.
6. Exercise the mission Supply guard in a later authorized budget window; this documentation audit provides no live claim about it.

## Limits
- This is an AI-assisted consistency review, not independent human expert validation.
- The combined delay, yield reduction and allocator rerun do not identify a unique cause for aggregate outcomes.
- Reference validation does not prove that arbitrary qualitative prose follows from selected references.
- Synthetic results do not establish real agronomy, demand, market, logistics, costs, or farm safety.
- No further paid request or capacity bypass was attempted.

These findings concern the frozen V10 software record as observed on 2026-09-11. They do not validate real crop biology, demand, weather, transport, accounting, or operational safety.
