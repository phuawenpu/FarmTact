# DeepSeek trial and development cutover

FarmTact runtime inference uses the direct official DeepSeek Chat Completions API. The browser never receives the credential. The server route manifest is `config/deepseek_runtime.json`; callers select a registered role and cannot supply a provider, origin, or model.

The v8 candidate manifest version 1.2 allowlists exact canonical
`deepseek-flash` for every current text and native-vision route. This follows the
10 September 2026 provider migration and authenticated 11 September discovery in
`reports/v8/model-discovery.json`. The gateway still requires returned model ID to
equal requested model ID; it does not silently accept retired aliases or reroutes.

## Offline verification

Install the repository's Python development dependencies in the environment, then run:

```bash
.venv/bin/python -m pytest -q tests/deepseek/test_gateway.py
```

The tests use `httpx.MockTransport`. They do not prove authentication, account model access, image understanding, or model quality.

## Fresh authenticated trial

Supply `DEEPSEEK_API_KEY` through the process environment without placing it in a command argument, file, report, shell trace, or client bundle. Then run one combined trial:

```bash
FARMTACT_EXECUTION_MODE=test .venv/bin/python scripts/deepseek_trial.py --live --with-council
```

`--live` means real authenticated HTTP traffic. It does not authorize `execution_mode=live` or farm operations. A clean run reserves at most 14 requests: discovery, two JSON probes, two thinking/tool continuation calls, one vision call, one stream, and seven council roles. Its hard per-process ceiling is 16 requests, 8,192 reserved output tokens, one concurrent request, and 300 seconds. It performs no automatic retry.

If a run stops and code is corrected, `--resume PATH` may reuse explicitly recorded passing capability evidence while initializing the new process with the prior cumulative request and token counts. Use it only while the aggregate stays within the original ceiling. A resume report records its predecessor. Never use resume to turn a failed capability into a pass, raise a budget, or conceal a paid attempt.

Reports are written to `reports/deepseek/deepseek_authenticated_trial_<UTC>.json`, with a convenience copy at `reports/deepseek/latest.json`. They contain safe audit metadata, validated public outputs, hashes, and usage. They exclude credentials, request authorization headers, raw/base64 images, provider-private reasoning, and provider error bodies.

## Result interpretation

- `PASS` requires account discovery and actual content-level validation. A listed model is not proof that a modality works.
- `BLOCKED` means a provider, credential, capability, budget, or incomplete-generation gate prevented acceptance. It is never replaced by another LLM provider.
- Offline mocks, deterministic baselines, and replay are reported separately and cannot pass an authenticated gate.
- A `length`, `content_filter`, `insufficient_system_resource`, empty output, unexpected model, invalid schema, incomplete SSE stream, or unknown tool fails closed.

The final 8 September 2026 trial passed DS-G1 and DS-G2 in 15 cumulative requests and 7,232 reserved output tokens. Earlier stopped reports retain truncated and schema-invalid generations. Explicit JSON schemas corrected the format mismatch; resumed runs counted failed attempts and reused only passing evidence. The integrated application vision/council/replan demonstration also passed separately. See `reports/deepseek/authenticated_trial_summary.md`.

## Development cutover checks

Before routing an application role through the gateway:

1. Register its reviewed DeepSeek model and capability in `config/deepseek_runtime.json`.
2. Pass typed messages and a Pydantic output contract to `DeepSeekGateway.chat_json`, or use `run_tool_json`, `vision_json`, or `stream_text` for those explicit workflows.
3. Allocate a finite `RunBudget` before any request. Reserve enough output tokens for thinking responses; an incomplete response remains a failure.
4. Keep `development_phase=autonomous_development`, `decision_policy=automatic_development`, `execution_mode=test`, and an allowed development data mode in decision records.
5. Validate tool arguments, tenant scope, evidence references, and numerical constraints outside the model. Never expose plan acceptance as a model tool.
6. Persist only `SafeAudit` and reviewed public conclusions. Dispose of in-memory tool continuation messages when the workflow finishes.
7. Run the provider-leak and deployment egress checks. The Python allowlist complements network policy; it does not replace it.

Operational `execution_mode=live` remains disabled. Development rollback targets a previously tested DeepSeek configuration, deterministic simulation baseline, or replay, with an audited reason. It never selects another generative provider.


## Current-versus-archived scope — 11 September 2026

The current script's normal full trial has seven capability requests and seven
optional council requests (14 total, within 16). The checked-in `latest.json`
is historical six-role evidence with 15 cumulative requests, not a fresh seven-role
trial. Current application councils normally use seven calls plus at most two
shared schema repairs; optional synthetic-label vision adds one. Thinking is
disabled for application council JSON; the separate tool-continuation probe tests
thinking. There is no dynamic model-selected tool loop in the application council.

The two v7 actual adviser probes remain unsupported. Archived success and key
presence are not current model/account verification. Read the detailed
[AI report](../technical/ai-provider-and-council.md) for exact call triggers,
validation, configured-but-unused roles and request/token/deadline limits.
A documentation reproduction does not require a paid capability trial.

## V8 evidence before the final quality run

The V8 ledger had consumed 36 actual paid requests before the final V4 mission
run: 24 mission requests across four retained experiments, 11 conversation
requests and one research-adviser request. The conversation run submitted 805,878
prompt tokens and persisted ten adviser messages; the research request submitted
64,756 prompt tokens. These measurements describe the admitted test inputs and
provider usage, not answer quality or a production budget recommendation.

The pre-context-fix scorer evaluated 18 retained cases: eight passed and ten
failed. Its exact workflow-integrity checks passed for direct, invite, Council,
planning and research call sequences, while the overall automated status remained
**FAIL**. The machine record is
[`ai-quality-before-context-fix.json`](../../reports/v8/ai-quality-before-context-fix.json).
Preserve that result even if a later run improves.

The frozen application contract now uses prompt and projected-context V4. Role
projection admits at most 48 typed facts, 24 qualitative references, 16 prior
turns and six evidence records, subject to a hard 120,000 serialized-character
limit. Exact frozen research inputs are retained when normal ranking caps are
reached. A question that cannot be answered from admitted context must produce an
abstention. These bounds deliberately truncate context and do not establish that
every relevant record is present.

One format repair is permitted for an otherwise rejected reply. The audit retains
the rejected attempt, and the repair instruction preserves its lexical meaning,
relationships, proposed actions and references while removing or relocating only
the invalid quantity/date expression. A repair is another paid call and cannot
erase the original failure. The final mission reserves at most nine requests; its
result, the final PostgreSQL suite and deployment gate are pending. There is no
human release-approval checkpoint in this autonomous development phase: the
specified technical gates control advancement, while real farm execution remains
disabled.

For the bounded product-quality trial, run
`scripts/deepseek_conversation_trial.py` against the intended local or deployed base
URL. It persists a private 0600 state file and runs direct, invite and Council stages
with stable idempotency keys: ten normal calls and fourteen worst case. Then run
`scripts/research_advisor_trial.py --state <same-private-state> --report <path> --live`.
The research interpreter adds one normal call or two worst case and reuses the same
session, stable action receipts and request ID on restart. Finally,
`scripts/deepseek_quality_e2e.py` reads the stored conversations and makes zero
inference calls. Keep actual failures, repairs and consumed calls in the experiment
ledger; do not overwrite them with a later successful attempt.
