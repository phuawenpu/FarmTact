# V10 grounding follow-up: fulfillment and evidence-absence boundaries

**Date:** 11 September 2026 UTC<br>
**State:** candidate; publication and targeted actual-provider verification pending<br>
**Scope:** corrections from retained public V9 failures<br>
**Operational boundary:** synthetic simulation only; actual farm operations disabled

## Abstract

V9 completed all five actual-provider workflows but failed its quality evaluation. Its Supply adviser asserted full booked-order delivery despite a positive booked shortfall in every strategy. Its conversational Weather and Market roles abstained but attached numerical claims, which the validator rejected. V10 addresses those concrete mechanisms without treating arbitrary prose as verified. It adds code-derived fulfillment evidence and a conservative contradiction check, and supplies a minimal absence-only context to external-source specialists who must abstain. Synthetic data, numerical models, execution mechanics and the browser implementation remain those verified in V8/V9.

## 1. Observations and falsifiable corrections

| Observed failure | Frozen evidence | Implemented correction | Remaining limitation |
| --- | --- | --- | --- |
| Supply said booked-order routing was fully delivered | V9 requested 824 kg under each policy; Lean/Balanced/Resilient delivered 370/446/518 kg | Derive booked shortfall and fulfillment status locally; include requested/delivered/shortfall in Supply context; reject explicit positive full-fulfillment assertions when the relevant status is partial | A finite phrase guard cannot establish general free-form entailment |
| A format repair preserved the false fulfillment assertion | The initial reply said each booked order was fully delivered; repaired prose removed the prohibited count word | The new semantic contradiction code is ineligible for format repair, so the unsupported premise cannot be repaired as punctuation or schema | Semantic rejection may withhold a required Council; a numerical plan is not thereby disproven |
| Absent-source conversational specialists attached numeric facts | Weather/Market returned `relationship=abstention` with nonempty `fact_refs`, rejected as `abstention_payload` | Required absence turns receive no numerical facts, scenario summary, evidence records, highlights or prior prose; typed evidence is explicitly not required and all output arrays must be empty | The model can still disobey; the existing local validator remains authoritative |
| The automated score missed Supply's contradiction while flagging other wording | V9 scored 12/18; six failures included prefix and keyword checks | Preserve the score and separately inspect meaning against frozen evidence | Human expert review, calibrated semantic evaluation and empirical farming outcomes remain absent |

The [V9 report](v9-ai-followup.md), [planning record](../../reports/v9/planning-public.json), [conversation replay](../../reports/v9/conversation-public-replay.json) and [quality result](../../reports/v9/ai-quality-final.json) retain the original observations. A new iteration does not overwrite those records or retroactively change their scores.

## 2. Evidence and rejection paths

```mermaid
flowchart TD
    Frozen[Frozen requested and delivered booked quantities] --> Derived[Local shortfall and fulfillment status]
    Derived --> Supply[Supply interpretation with paired metric meaning]
    Supply --> Guard[Explicit full-fulfillment contradiction check]
    Guard --> Accepted[Supported reference shape; prose remains unverified]
    Guard --> Rejected[Preserved semantic rejection; no format repair]
    Sources[Frozen external-source availability] --> Scope{Council specialist must abstain?}
    Scope -->|Yes| Empty[Absence reason; no numeric facts or prior prose]
    Scope -->|No| Normal[Existing bounded numerical or source context]
    Empty --> Validator[Empty-reference abstention validation]
    Normal --> Validator
```

For strategy $s$, the implementation derives booked shortfall as the nonnegative difference between booked requested mass and booked delivered mass, rounded to six decimal places. This is bookkeeping over the existing gram-based numerical result, not a fitted model or new yield calculation. The derived typed fact retains the strategy identifier and kilogram unit. Zero shortfall gives `fully_delivered`; positive shortfall gives `partial_delivery`. This status does not mean that residual forecast demand is covered, nor that a physical delivery occurred.

The phrase guard addresses explicit positive statements of full, complete or universal booked fulfillment. It preserves truthful negatives such as “not fully delivered,” and permits a named fully covered policy in a mixed context. It does not prove arbitrary paraphrases, sentence scope or causal claims. The original quantity/date blocker, exact reference gate and finite repair policy remain in force.

The absence-only projection applies specifically to Weather or Market in conversational Council mode when their declared external source is absent. It changes only the provider projection: the full frozen snapshot and dialogue remain durable. Direct and invited questions about answerable numerical results retain their facts. Research advisers retain the existing research projection. The system still calls the absent-source specialist and labels actual execution truthfully; replacing those calls with explicitly labelled deterministic notices is future work.

Mission prompt/context is **V7**, conversation prompt/context **V6**, and shared validator **V5**. Output schema remains **V3**, including its 400-character content bound, three typed references and existing repair ceilings. Numerical solver, data/evaluation and execution versions are unchanged.

## 3. Verification and paid-experiment scope

The [conversation focus](../../reports/v10/conversation-focused.xml) passed 45 tests. Mission tests cover exact derived coverage, false total-fulfillment assertions, truthful negative and mixed-policy cases, and semantic rejection without consuming a format repair. The final [PostgreSQL regression](../../reports/v10/full-regression.xml) passed **611 tests with one skip** in 441.23 seconds against its own isolated database and the frozen V9 browser assets.

Through V9, the [task ledger](../../reports/v8/live-call-ledger.json) records **76 actual requests**: 44 local and 32 public. The public application retains its **48-request daily ceiling**, leaving at most 16 further requests today in the absence of unrelated usage. The internal experiment ceiling remains 96 and is not a runtime spending override.

V10's targeted paid follow-up exercises the two changed paths: the planning Council and the conversational Council. Each normally uses seven requests; each workflow can allow up to nine including repairs, but combined execution is additionally constrained by the unchanged shared daily limit and a 16-request remaining experiment envelope. No extra direct, invite, research or vision call is claimed for V10. Their retained V8/V9 evidence and deterministic regression have distinct source scopes. A blocked or partial result will be retained rather than bypassing the cap or retrying for a favorable answer.

Replaying stored outputs, reading the UI, checking edition identity and prior-state preservation, and advancing a synthetic execution world make no provider calls. Numerical acceptance is separate from interpretation quality. Actual-provider results below must state completed roles, repairs, rejection state and semantic limitations rather than collapse them into a single success label.

## 4. Publication and final evidence

Publication identity, final regression, preservation and targeted actual-provider results are pending in this candidate. V9 remains the latest published edition until the immutable publisher completes V10. The next unused edition must always be checked in the registry.

## 5. Open semantic acceptance criteria

The completed [V9 AI-assisted review](../../reports/v9/ai-assisted-semantic-review.md) examined 18 messages and 62 atomic assertions: ten messages were sound, five sound with limits, and three materially contradictory. Besides the Supply error targeted here, two Production replies described crop mix as unchanged even though Lean and Balanced changed their allocation composition. Unchanged total growing area does not establish unchanged crop mix. Simultaneously changing delay and yield and rerunning allocation cannot identify a sole cause.

These broader Production interpretation defects remain open; V10 does not claim to close them through its fulfillment or absence corrections. The next acceptance criteria are: expose code-derived per-crop allocation comparisons when discussing composition; reject or abstain on composition claims without that evidence; explicitly distinguish the crop-ID set from allocation counts/areas; and test causal wording against multi-control changes and replanning. A semantic evaluation should contain truthful paraphrases and false claims with valid references, measuring both false rejections and missed contradictions. Human expert review and real-farm outcome calibration are separate future requirements.
