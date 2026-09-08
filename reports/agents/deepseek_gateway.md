# A09/A12 DeepSeek gateway implementation report

## Delivered

- `runtime/deepseek_gateway.py`: direct `httpx` DeepSeek-only gateway with a fixed HTTPS origin, model and role allowlists, redirects and inherited proxies disabled, safe bounded errors, request/response byte limits, finite request/output/wall/concurrency budgets, typed JSON validation, allowlisted tools, private in-memory thinking continuation, inline image normalization, and SSE parsing.
- `config/deepseek_runtime.json`: reviewed role/capability manifest and server limits.
- `scripts/deepseek_trial.py`: bounded authenticated DS-G1/DS-G2 runner with synthetic image and computed-plan fixtures, content checks, cumulative resume accounting, and safe reports.
- `tests/deepseek/test_gateway.py`: offline transport, policy, failure, image, tool, schema, mode, and streaming checks.
- `research/deepseek_api_sources.json`: date-stamped official documentation registry.
- `docs/runbooks/deepseek_trial_and_cutover.md`: execution and development cutover procedure.

## Verification

` .venv/bin/python -m pytest -q tests/deepseek/test_gateway.py ` passed 37 tests after final mode preflight coverage was added. Python compilation passed for the gateway and trial script.

The authenticated trial made 11 aggregate requests across explicitly linked stopped/resumed attempts, never exceeding the 16-request ceiling. DS-G1 passed; DS-G2 remained blocked on incomplete council output. Full evidence and limitations are in `reports/deepseek/authenticated_trial_summary.md`.

## Integration interface

Construct with `DeepSeekGateway.from_config(path, budget=RunBudget(...))`. Use `chat_json(role, messages, output_model, ...)` for typed role output, `run_tool_json(...)` for a validated single-tool continuation, `vision_json(...)` for normalized synthetic or authorized images, and `stream_text(...)` for bounded SSE. Public returns contain validated data and `SafeAudit`; they never contain `reasoning_content` or image bytes.

No shared contracts, lockfiles, environment files, frontend files, or alternate-provider configuration were changed.
