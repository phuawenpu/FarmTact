# FarmTact security hardening release

Status: **PASS — deployed** on 2026-09-08 at https://farmtact.fly.dev.

The audit found no application IP/session admission limits despite an existing
global provider-call budget. The release adds persistent request quotas, proxy
identity validation, session-creation throttles, write/probe limits, stream
concurrency and lifetime bounds, exact origin/host checks, server session expiry,
pre-body authentication, upload deadlines and disabled public API schemas.
DeepSeek requests now include server-derived tenant pseudonyms. A midnight budget
refund defect was also fixed. The detailed policy and limitations are in
[docs/security.md](../docs/security.md).

## Verification performed

- Final full regression: **300 passed**, two existing dependency deprecation
  warnings; `security_full_pytest.xml`.
- Independent admission suite: 29 cases, including three real PostgreSQL tests
  covering concurrent clients, atomic rollback, expiry and restart persistence.
  Three additional unauthenticated-upload cases bring the final focused admission
  run to 32 passes; `security_final_admission.xml`.
- Six new mocked AI-boundary cases exercise prompt-based provider overrides,
  pseudonymous provider IDs, extra output fields, injected tool tenant selectors,
  provider request-ID sanitization and foreign snapshot references.
- Existing schema-probe tests now advance an injected clock between independent
  probes so they reach schema validation without disabling production quotas.
- Review found an SSE bypass through the Accept header; shared classification now
  covers Accept and all supported true-valued query aliases before release.
- **Eleven live HTTP checks passed** (`security_live_probe.json`). Six invalid,
  unauthenticated AI requests returned 401, then the seventh returned 429 with
  Retry-After. Rotating invalid cookies and X-Forwarded-For did not reset the IP
  allowance; a forged Fly-Client-IP also remained blocked with 429. Cross-origin
  writes returned 403; schema/docs/generic proxy probes returned 404.
- No valid inference job was submitted by the live probes. Read-only PostgreSQL
  inspection showed the daily provider reservation count unchanged at 26 before
  and after them (`security_inference_accounting.json`). No paid inference was
  performed for this task.
- Twelve live browser replay checks passed after deployment, with zero inference
  POSTs. Six advisors, critic conclusion, blocked suggestions, frozen facts and
  390/1280px controls remained usable (`live_replay_browser.json`).
- Final deployment preserved the old farm/run, scenario result, quest progress,
  fourteen full-discussion messages and five partial-discussion messages
  (`security_deployment_persistence.json`).
- Fly and its health route return 200. The Sprite web service remains removed,
  port 8080 closed, and the development database intact (`gameplay_hosting.json`).

## Release identity

Image: `registry.fly.io/farmtact:deployment-01M21KKJYNF4E3TZ688WY7FESG`.
The existing machine `d8d2060c074438` and encrypted persistent volume were retained.
There were no queued/running planning or conversation jobs at the pre-deploy check.

## Limits of the result

This is application hardening, not an infrastructure penetration test or an edge
WAF deployment. Anonymous users can still compete for shared capacity; IP limits
do not identify a person or stop a distributed botnet. Provider user_id behavior
is documented and wire-tested with mock transport, not independently audited
inside DeepSeek. Prompt injection can still influence qualitative advice; it
cannot grant the reviewed HTTP workflows arbitrary tools or another tenant's
data. The independent audit records semantic and context-minimization limitations
in `ai_boundary_audit.md`. Real farm operations remain disabled.
