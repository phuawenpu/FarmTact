# V12 Council V4 stored-evidence quality review

## Scope and disposition

This is a read-only review of `/tmp/v12-council-v4-workflow-final.json`. No source was changed and no inference was called. The artifact reports a PASS workflow, completed Council, seven actual DeepSeek requests, two validated repair attempts, and identical replay. The recorded daily total is 31 calls.

Five provider-backed functional roles finish validated. Weather & Risk and Market & Price are deterministically partial because their sources were absent; they made no inference call. Council `truth_status=partial` therefore accurately reflects the two unavailable roles even though the five assessed roles validated.

I found no false quoted number or contradiction in the five final provider-backed findings. The Plan Reviewer has one presentation-scope defect in this stored run: its structured rationale legitimately accepts waste **or terminal stock**, and it cites terminal stock, but the old server-rendered interpretation says “expired waste.” The later display-only wording change to “Balance customer service, crop waste or remaining stock, and projected margin” accurately describes the typed evidence. It does not alter this historical artifact or its prompt, context, validator, claims, or provider output.

## Request and validation accounting

- Request count is seven: five final provider-backed findings plus one Crop Planner repair and one Farm Planner repair.
- Demand, Crop, Capacity & Cost, Farm Planner, and Plan Reviewer audits record provider `deepseek`, model `deepseek-flash`, `inference_origin=deepseek_api`, nonzero latency, and positive token usage.
- Provider request IDs are null. Input hashes, public-context hashes, usage, latency, model, and contract versions remain present; no missing request ID should be invented.
- All final findings and frozen claims use snapshot `0ac1004b...13869`.
- Replay is identical, the workflow remains operations-disabled, tenant isolation passes, and the main farm is unchanged.
- The two repair rejections are visible rather than silently accepted:
  - Crop Planner initially used crop-identity claims with the unrelated balanced service/waste/margin rationale; validation rejected both the unsupported rationale and missing metric groups.
  - Farm Planner initially returned a non-abstention balanced interpretation with no claims; validation rejected `unsupported_interpretation`.

## Final finding review

### Demand Planner — supported booked-service finding

It selects Resilient and cites:

- overall-demand fill rate 0.6213;
- booked delivery 518 kg;
- booked shortfall 306 kg.

All values match the frozen claims. The full comparison shows Resilient has the highest booked delivery (518 versus Balanced 446 and Lean 370 kg) and the lowest booked shortfall (306 versus 378 and 454 kg). Those two booked metrics support the service selection.

The 0.6213 figure remains an **overall-demand** fill rate, not a booked fill rate. The rendered claim preserves that scope, and the booked metrics independently support the result.

Assessment: validated; no contradiction.

### Crop Planner — crop identity is now directly supported, with equal mixes

After repair it selects Balanced and cites the allocated crop IDs for every strategy. Each set is exactly:

- caixin;
- kailan;
- lettuce;
- pak_choi.

The crop-specific identity facts directly support the `preserve_crop_variety` rationale and cure the prior aggregate-area defect. They also show all three strategies preserve the same four-crop identity set. The facts therefore support preservation of crop variety, but they do **not** show Balanced has a more diverse mix than Lean or Resilient, nor do they compare area shares within that mix.

Balanced is an eligible strategy and its own crop-set claim is selected, so the proposal is structurally supported. Its selection is not uniquely determined by crop identity because all sets are equal.

Assessment: validated for preserving the four-crop set; no contradiction; no evidence of a uniquely superior mix.

### Capacity & Cost Analyst — real workload and direct-cost scope, bounded to Resilient

It selects Resilient and cites:

- labour 85.42 hours;
- sown area 240 m²;
- projected cost SGD 1,862.99.

All three values match the frozen claims and satisfy the dedicated `capacity_over_volume / respect_capacity_cost` contract. Unlike the V3 margin-only result, this finding now has direct workload, physical-area, and cost evidence. The server text “Review projected cost and resource use in the frozen plan” accurately describes those facts.

The finding is a snapshot of Resilient's workload and cost, not a proof that those values fit an external labour, land, or cash ceiling. It cites no declared capacity limit and no alternative strategy values. The complete frozen comparison is Lean 55.8 h / 120 m² / SGD 1,141.50, Balanced 70.82 h / 180 m² / SGD 1,522.54, and Resilient 85.42 h / 240 m² / SGD 1,862.99. Resilient is the highest of all three on these measures.

Assessment: validated workload/area/cost description; no contradiction. It must not be expanded into “Resilient is within capacity,” “lowest cost,” or “most resource-efficient” without a cited constraint or comparison.

### Farm Planner — complete three-group tradeoff with a visible waste penalty

After repair it selects Resilient and cites:

- projected margin SGD 3,193.15;
- overall-demand fill rate 0.6213;
- expired crop waste 220.98 kg.

These exact claims satisfy all three required groups: margin, service, and waste/stock. Resilient has the highest margin and overall fill rate, but also the highest waste (Resilient 220.98, Balanced 175.99, Lean 153.99 kg). The balance rationale is coherent only as accepting the larger waste burden for service and margin; it does not say Resilient minimizes waste.

The service metric is overall-demand fill rate. This finding makes no booked-only service claim, so the scope is consistent.

Assessment: validated and semantically supported; no contradiction; explicit tradeoff rather than universal optimum.

### Plan Reviewer — typed stock-backed balance is valid; old rendered wording is mismatched

It selects Balanced and cites:

- overall-demand fill rate 0.534;
- remaining terminal stock 54 kg;
- projected margin SGD 2,930.59.

All values match the frozen claims and supply the validator's three required groups: service, waste-or-stock, and margin. Balanced sits between Lean and Resilient for overall fill rate and margin. Its terminal stock is 54 kg, equal to Resilient and above Lean's 35 kg. The selected facts support a middle service/margin option while disclosing its remaining stock; they do not establish that Balanced minimizes stock.

The stored `rendered_interpretation` says “Balance customer service, expired waste, and projected margin.” That sentence is too narrow because this finding cites terminal stock, not expired waste. The typed structure itself is sound: rationale `balance_service_waste_margin` permits the second group `{waste_kg, closing_stock_kg}`, and `closing_stock_kg` is present. Root's display-only replacement—“Balance customer service, crop waste or remaining stock, and projected margin.”—correctly represents both allowed variants. This is a presentation-scope fix, not a retroactive change to provider evidence.

Assessment: validated structured finding; no numerical contradiction; historical rendered wording should be disclosed as mismatched.

## Partial external roles

Weather & Risk and Market & Price have no supplied evidence, no claim IDs, no proposed strategy, no provider audit, and no inference request. Their `unavailable / partial / source_absent` state is accurate. They are not part of the five validated actual findings and the Council must not be described as weather- or market-validated.

## Bounded conclusion

- **Workflow artifact:** PASS, bounded, replay-identical, tenant-isolated, operations disabled, main farm unchanged.
- **Actual requests:** seven, including two visible repairs; five final provider-backed roles validated.
- **Numerical integrity:** no false quoted number or contradiction found in final findings.
- **Crop scope:** four crop identities are directly supported and equal across strategies; no unique diversity advantage is shown.
- **Capacity scope:** actual labour, area, and projected cost are cited for Resilient; no external capacity ceiling or efficiency conclusion is established.
- **Farm Planner:** complete service/waste/margin evidence, with Resilient's higher waste explicitly retained.
- **Plan Reviewer:** typed stock-backed balance is valid; the stored old text incorrectly says expired waste and is accurately corrected by the broader display phrase.
- **Overall truth:** partial because Weather and Market sources remain absent, despite validation of the five assessed roles.

No real-operation authorization or general agronomic, weather, or market capability follows from this synthetic frozen-plan run.
