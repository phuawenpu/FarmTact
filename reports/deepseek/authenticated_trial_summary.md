# DeepSeek authenticated trial evidence

**Date:** 8 September 2026
**Provider:** DeepSeek direct API at `https://api.deepseek.com`
**Modes:** `execution_mode=test`, `data_mode=synthetic_demo`
**Retry policy:** none
**Aggregate budget:** 16 requests, 8,192 reserved output tokens, one concurrent request, 300 seconds per bounded process

## Outcome

DS-G1 core capability verification passed with real authenticated calls:

- Account discovery returned all three reviewed aliases: `deepseek-v4-flash`, `deepseek-v4-pro`, and `deepseek-v4-flash-vision-exp`.
- Flash and Pro returned JSON that passed local Pydantic and semantic checks.
- The thinking/tool workflow called the one allowlisted supply tool, preserved the returned assistant `reasoning_content` only in memory for the next request, retained the tool-call ID, and returned validated quantities. No private reasoning was written to a report.
- The vision model read `SG-CX-4827`, which existed in the synthetic PNG and was absent from the text prompt. The normalized asset hash and explicit uncertainty fields passed checks. Raw and base64 image content was not persisted.
- The SSE probe returned the exact content marker, final `stop`, `[DONE]`, and usage.

DS-G2 now **PASS**. The final bounded aggregate completed all six actual DeepSeek roles, preserved the impossible-lead-time constraint and recorded backend acceptance for simulation. The passing report is `deepseek_authenticated_trial_20260908T084144Z.json`, also copied to `latest.json`: 15 cumulative requests of 16, 7,232 reserved output tokens of 8,192. Resumed processes included every earlier request and output reservation in this aggregate.

Earlier blocked reports remain unchanged. The first experiment stopped after truncated council outputs. A fresh bounded experiment exposed two output-schema mismatches; explicit JSON schemas and correctly sized image text/output allowances resolved them. Passing probes were reused from their recorded reports; failed calls were retained in the cumulative budget. No provider was substituted and no failure was counted as a pass.

The separate integrated application run `014966c917b7d2d0ce0bc1d94a41e256` completed synthetic-image vision and six roles against the real numerical planner. Five claims passed local validation; one unsupported numerical claim was rejected visibly. The independent critic and backend cleared the Balanced simulation. Its recorded replay incurs no new inference. See `reports/integrated_demo.json`.

## Compatibility finding

The first thinking/tool attempt returned HTTP 400. Official DeepSeek V4 integration guidance states that thinking tool calls reject `tool_choice`, even though the generic Chat Completions schema documents that field. Removing `tool_choice` for thinking mode produced a successful two-call continuation. The stable endpoint and local argument validation remained unchanged.

## Limits of this evidence

The trial establishes transport compatibility and content-level seed behavior for the account at the recorded time. It does not establish production quality, operational farm benefit, a finished optimizer, deployment egress enforcement, or readiness for operational live execution. DS-G1, DS-G2 and the integrated DS-G3 demonstration have separate evidence; passing a toy probe is not evidence of farm-level efficacy.
