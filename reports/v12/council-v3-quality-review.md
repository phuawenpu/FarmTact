# V12 Council V3 stored-evidence quality review

## Scope and disposition

This is a read-only review of `/tmp/v12-council-v3-workflow-final.json`. No source was changed and no inference was called. The artifact records six DeepSeek requests: Demand Planner, two Crop Planner attempts, Capacity & Cost Analyst, Farm Planner, and Plan Reviewer. Weather and Market were deterministically unavailable because their sources were absent.

The artifact correctly remains **FAIL / partial / withheld**: Crop Planner's final finding was rejected, so `actual_council_completed=false`, Council status is `partial`, and truth status is `withheld`. This review does not rescore that historical result after the later `3e30a63` crop-claim/context fix.

Across the other four actual validated findings, every cited ID resolves to the same frozen snapshot and every rendered number matches its verified claim. I found no numerical contradiction. Capacity & Cost's result has a material scope limitation: margin is an admitted financial constraint, but the finding does not assess workload, physical capacity, or projected cost and does not support all three dimensions named by its generic balance rationale.

## Transport, bounds, and validation truth

- All actual findings use provider `deepseek`, returned model `deepseek-flash`, `inference_origin=deepseek_api`, nonzero latency and positive token usage.
- Provider request IDs are null. The stored model, origin, input hashes, usage, latency, contract versions, and public-context hashes remain usable audit evidence; no request ID should be invented.
- The Council used six requests, within its bounded allowance. Replay was identical.
- Every finding is bound to snapshot `0ac1004b...13869`.
- Crop Planner is visibly `rejected` with `crop_mix_requires_crop_identity_or_allocation_evidence`, exposed as `truth_status=withheld` and `tool_status=validation_failed`.
- Weather and Market cite nothing, propose nothing, and are accurately `partial/source_absent` rather than presented as actual findings.

## Four validated actual findings

### Demand Planner — numerically correct; booked-service conclusion supported

It selects Resilient and cites:

- overall-demand fill rate 0.6213;
- booked delivery 518 kg;
- booked shortfall 306 kg.

Those values exactly match the frozen claims. The full frozen comparison confirms Resilient has the highest booked delivery (518 versus Balanced 446 and Lean 370 kg) and lowest booked shortfall (306 versus 378 and 454 kg). The two booked metrics directly support prioritizing booked service.

The fill-rate citation is explicitly **overall demand**, not booked demand. It must not be relabeled as booked fill rate. This does not invalidate the result because the booked-delivery and booked-shortfall claims independently support it.

Assessment: validated within the frozen numerical scope; no contradiction.

### Capacity & Cost Analyst — margin comparison correct; workload/capacity scope not established

It selects Balanced and cites only projected margins:

- Resilient SGD 3,193.15;
- Lean SGD 2,467.60;
- Balanced SGD 2,930.59.

All three values are correct. Balanced is the middle-margin strategy, so selecting it can be consistent with an unstated compromise. No cited fact contradicts that selection.

However, the rendered interpretation says “Balance customer service, expired waste, and projected margin,” while its evidence contains only margin. It cites no booked service, expired waste, labour, area, or projected-cost claim. The frozen facts available to the role include the following workload and cost comparison:

| Strategy | Labour | Sown area | Projected cost | Projected margin |
|---|---:|---:|---:|---:|
| Lean | 55.8 h | 120 m² | SGD 1,141.50 | SGD 2,467.60 |
| Balanced | 70.82 h | 180 m² | SGD 1,522.54 | SGD 2,930.59 |
| Resilient | 85.42 h | 240 m² | SGD 1,862.99 | SGD 3,193.15 |

The finding therefore makes **no supported workload claim** and does not show whether any capacity ceiling is approached. Passing the V3 semantic gate through `margin_sgd` establishes a financial fact only; it is not evidence that workload, space, cash availability, or projected cost was analyzed. The generic balance rationale is broader than the selected facts.

Assessment: no numerical contradiction; valid margin-only comparison; functional Capacity & Cost coverage remains partial. It should be described as comparing margin, not as confirming workload capacity or balancing service/waste. A stronger future gate would require selected facts for every dimension asserted by the rationale and at least one physical capacity/workload or direct cost fact when presenting this role as Capacity & Cost.

### Farm Planner — correct margin/waste facts; explicit waste penalty is necessary

It selects Resilient and cites:

- Resilient margin SGD 3,193.15;
- Resilient expired waste 220.98 kg;
- Balanced expired waste 175.99 kg.

These figures are correct. The complete frozen values show Resilient has the highest margin, but also the highest waste (Resilient 220.98, Balanced 175.99, Lean 153.99 kg). Thus the selection is coherent only as acceptance of higher waste in exchange for other benefits; it must not be described as waste-minimizing.

The generic rationale also names customer service, but this finding cites no service fact. Resilient does have the best booked-service values elsewhere in the frozen claim set, yet this particular finding did not select them. Reference validity does not turn uncited context into evidence for the finding.

Assessment: no contradiction; supported margin-versus-waste tradeoff, with service outside its selected evidence.

### Plan Reviewer — coherent three-dimensional tradeoff, not an optimum proof

It selects Resilient and cites:

- margin SGD 3,193.15;
- expired waste 220.98 kg;
- overall-demand fill rate 0.6213.

All values are correct and cover the three dimensions in its rendered balance rationale. Resilient has the highest margin and overall fill rate among the frozen strategies, but also the highest expired waste. The review is coherent as an explicit willingness to accept the waste penalty for service and margin. It does not establish that Resilient minimizes waste or is a mathematically unique optimum.

The fill rate remains an all-demand metric. The chair does not call it booked fill rate, so no scope contradiction is present.

Assessment: validated, internally coherent tradeoff; no contradiction.

## Historical Crop Planner result

The Crop Planner cited only aggregate sown areas (Resilient 240 m², Balanced 180 m², Lean 120 m²) while using the `preserve_crop_variety` rationale. Aggregate area cannot establish crop identity, allocation mix, or variety. The V3 validator correctly rejected the final output. The initial repair attempt was also rejected because it paired area claims with an insufficient-evidence rationale that those selected claims did not support.

This historical finding must remain withheld. The later source `3e30a63` adds initial-plan `crop_mix_snapshot` claims and context V4, but those changes were not part of this stored run and do not retroactively alter its status.

## Bounded conclusion

- **Numerical integrity:** no contradiction found in the four validated actual findings.
- **Demand:** supported by exact booked delivery and shortfall; overall fill rate must retain its scope.
- **Capacity & Cost:** exact margins, but no supported workload/capacity claim and no direct cost/area/labour evidence selected. Do not represent this output as capacity validation.
- **Farm Planner:** supported margin/waste tradeoff; Resilient carries the largest waste burden.
- **Plan Reviewer:** coherent service/margin versus waste tradeoff; not proof of a unique optimum.
- **Crop Planner:** correctly withheld historically; no post-hoc pass.
- **External roles:** Weather and Market correctly remain partial because sources were absent.

No agronomic, market, weather, or real-operation authority follows from this synthetic frozen-plan review.
