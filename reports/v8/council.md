# V8 Council and DeepSeek remediation

**Implementation date:** 11 September 2026  
**Scope:** AI-01 through AI-12 server paths, bounded quality harness and offline evidence  
**Provider activity:** root-owned bounded trials are recorded in `reports/v8/live-call-ledger.json`; this package made no paid calls itself

## Result

V8 replaces numeric coincidence and citation membership as the primary answer-grounding mechanism. A model now selects a frozen `fact_ref`; server code attaches its exact value, unit, entity, period and snapshot hash. The model cannot supply or alter those fields. Model-authored numbers and dates remain unsupported even when their value happens to match an unrelated reference. Qualitative interpretation is always labelled `qualitative_unverified`.

Mission and persistent-conversation outputs now expose execution, evidence and decision-influence status independently. New completions retain prompt-template, output-schema, validator, context and source versions, plus a hash of the public context. Historical JSON remains readable because the new fields are additive.

## Gap disposition

| Gap | V8 behavior and evidence | Residual limit |
| --- | --- | --- |
| AI-01 | `packages/ai_quality.py` scores role relevance, expected references, unsupported quantity, forbidden conclusions, abstention, evidence state and usefulness separately. `scripts/deepseek_quality_e2e.py` scores stored actual direct, invite, council and research outputs, retains per-message usage and repair/failure events, and fails missing workflow coverage. Root's early actual planning trials exposed a retired model identity, numeric-reference misuse, count words and missing role context; every failed attempt and consumed call remains in the ledger. | The stored direct/invite/conversation-Council/research suite still needs its final bounded run. Human expert scoring remains required before claiming agronomic answer quality. |
| AI-02 | `packages/ai_contracts.py` builds typed facts from server-owned references. Conversation messages and mission claims persist `fact_refs` and `rendered_facts`. Wrong entity, wrong unit, wrong meaning, citation laundering and authored quantities have adversarial tests. | Qualitative entailment is deliberately not claimed; it stays unverified. |
| AI-03 | Conversation responses expose `workflow_type`, `source_workflow_type`, `inference_origin`, `model_call_status`, `new_calculation_occurred`, and replay origin. Mission events label the sequential workflow and DeepSeek origin. Root integration labels scripted research and numerical work separately. | Historical records without these fields use conservative compatibility values. |
| AI-04 | Root integration separates configured credentials, archived probe evidence and tenant-scoped last observed execution without triggering a background request. | Provider availability remains unknown until an explicit requested execution. |
| AI-05 | `config/deepseek_runtime.json` contains a fail-closed caller inventory. It distinguishes active product/API integrations from the diagnostic trial; helper/evaluator routes have no implied active caller. Manifest 1.2 records the dated provider migration and routes every current text/native-vision role to exact canonical `deepseek-flash`. | The registry is compiled policy and requires code/config review for additions; it is not dynamic call-graph discovery. |
| AI-06 | `RunBudget.cancel()` blocks transmission and stops bounded response consumption between chunks. Direct/invite/council reserve their exact maxima of 2/3/9 calls. Usage already records input, output, cache and reasoning token fields. Interrupted requests are never automatically retried. | No USD guarantee is claimed. Dated provider prices, cost reservation, midnight reconciliation and shared-edition accounting remain deployment controls outside this package. Synchronous transport may need one chunk boundary to observe cancellation. |
| AI-07 | Both mission and conversation contexts expose canonical `forecast:batch_<id>.marketable_kg`, harvest date, crop, endpoint, origin, value status, observation flag and unit. `expected_kg` is retained only when an older frozen forecast actually contains that field. | Existing persisted snapshots are not rewritten. |
| AI-08 | The truthful sequence remains six independent specialists over the same frozen context followed by the chair. Only the chair receives bounded prior claims, including evidence status and validation issues. Budget remains seven roles plus two shared repairs. A semantic-format repair is allowed only for authored-number/count prose or a typed fact placed in qualitative refs; the original rejected claim, issues, usage and audit remain stored. Unknown references and unsupported semantics are never retried. | No challenge round or phantom debate was added. Its value must be measured before spending more calls. |
| AI-09 | `RESPONSE_LIMITS` is the single schema and prompt authority: 400 content characters, one evidence ref, three context refs, three typed facts, one highlight and one proposed action. Boundary and one-over tests cover every field. | Sentence count is guidance rather than a brittle structural validator. |
| AI-10 | `validated_turn_projection()` sends bounded issue codes/messages, evidence status and `eligible_as_evidence` to later roles. The prompts forbid use of ineligible earlier turns as evidence. Mission chair context follows the same rule. | A model can ignore instructions, but the local gate still prevents an unsupported turn from becoming validated. |
| AI-11 | Every gateway completion gets a complete contract-version set. Main callers pass named versions; generic callers receive deterministic prompt/schema/context hashes and an explicit unspecified-source version. New messages/claims retain `public_context_sha256` and named versions. | Public context is reconstructable from frozen records; private provider reasoning is neither persisted nor exposed. |
| AI-12 | New requests and messages separate execution, evidence and decision influence. All-unsupported successful transport becomes `execution_status=completed`, `evidence_status=unsupported_all`, `decision_influence=advisory_only`. Mission claims expose withhold requests independently. Root integration implements explicit required/advisory policy. | The legacy `validation_status` field remains as a compatibility alias and must not be interpreted alone. |

## Request budget for the actual quality run

The deployed main conversation trial uses one direct reply, a two-person invitation and the seven-role council: **10 normal calls, 14 maximum with structural repairs**. One explicit direct question attached to a completed research snapshot adds **1 normal call, 2 maximum**. The combined experiment is therefore **11 normal calls and 16 maximum**. The quality scorer reads persisted outputs and events and makes **zero** inference calls.

```bash
/tmp/farmtact-docs-venv/bin/python scripts/deepseek_conversation_trial.py \
  --base-url https://farmtact.fly.dev/v8 \
  --state /tmp/farmtact-v8-ai-trial.json --live

/tmp/farmtact-docs-venv/bin/python scripts/research_advisor_trial.py \
  --state /tmp/farmtact-v8-ai-trial.json \
  --report reports/v8/research-advisor.json --live

/tmp/farmtact-docs-venv/bin/python scripts/deepseek_quality_e2e.py \
  --base-url https://farmtact.fly.dev/v8 \
  --conversation-id <main-id> \
  --research-conversation-id <research-id> \
  --state /tmp/farmtact-v8-ai-trial.json \
  --output reports/v8/ai-quality.json
```

The authenticated run must preserve failures and usage rather than retrying them away. A schema or transport pass is insufficient: the quality report fails unsupported replies, missing expected references, wrong-role responses, forbidden conclusions, authored quantities, unhelpful answers and missing workflow coverage independently.

## Offline verification

```bash
/tmp/farmtact-docs-venv/bin/python -m pytest -q \
  tests/seven_agents tests/deepseek tests/gameplay/test_conversations.py \
  tests/review/test_ai_quality.py tests/review/test_ai_injection_boundaries.py \
  tests/review/test_provider_isolation.py
```

This group covers the roster and gate, typed fact semantics, canonical harvest references, response boundaries, chair rejection context, replay compatibility, execution/evidence status separation, caller manifest, cancellation, provider isolation, safe audit versions and the no-inference quality scorer. PostgreSQL-only cases skip when the configured test database is SQLite.

Latest package verification: **227 passed, 1 skipped, 1 PostgreSQL concurrency case deselected** in 51.05 seconds; the deselection avoided interference from a simultaneously running repository-wide worker. A final frozen gate/gateway/cancel/quality subset then passed **96 tests** in 35.54 seconds. Root integration runs the complete suite after all concurrent packages settle.

## Scientific boundary

These changes improve traceability and make unsupported answers visible. They do not validate a growth, yield, quality, demand or weather-response model, and they do not authorize real farm operations. The typed facts inherit the status of the frozen numerical or source record; code rendering prevents value mutation but does not turn a synthetic assumption into an observation.
