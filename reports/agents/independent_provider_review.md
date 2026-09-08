# Independent A11 DeepSeek provider-isolation review

## Scope and conclusion

Reviewed the DeepSeek gateway and its current application call sites independently of their author. The reviewed implementation routes current FarmTact inference through one fixed DeepSeek origin, rejects caller-selected models/roles/modes before transmission, disables redirects and environment-derived proxy settings, exposes no provider reasoning text, and uses explicit synthetic provenance for the only integrated vision workflow.

No paid or live inference was performed. Every HTTP interaction in this review used `httpx.MockTransport`; process-egress checks ran in isolated subprocesses with fake DNS/socket events.

Files inspected:

- `runtime/deepseek_gateway.py`
- `config/deepseek_runtime.json`
- `services/api/council.py`
- `services/api/vision.py`
- `services/api/app.py` worker/error-publication path
- `services/api/egress.py`
- `scripts/serve.py` (the repository has no `services/api/serve.py`)

Review tests were added only at `tests/review/test_provider_isolation.py`.

## Verified controls

| Area | Evidence from code and adversarial tests | Result |
|---|---|---|
| Provider and origin | Config load rejects non-DeepSeek provider, deceptive/HTTP origins, absolute or changed API paths and non-allowlisted models. Requests observed only at `https://api.deepseek.com/chat/completions`. | Pass for current config |
| Role routing | The loader pins the exact reviewed 13-role model/capability map; the six council roles are text routes. Added, missing, reassigned, malformed, case-changed and provider-like roles fail before transport. Council accepts no provider/model/origin parameter. | Pass |
| Modes | `live`, replay inference, `live_advisory`, real-private and other non-development combinations fail before text or image transmission. | Pass |
| Redirects and proxies | `httpx.Client` is constructed with `follow_redirects=False` and `trust_env=False`. Buffered and streaming 308 responses stop after one request. | Pass |
| Process egress | The server entrypoint installs the Python egress hook. Isolated tests allowed a mocked resolved DeepSeek address on 443 while rejecting an alternate hostname, an unapproved IP and port 80. | Pass as defense in depth |
| Provider failures | Mock 400/401/403/429/500/503 bodies, prompts and timeout details never appeared in raised public errors; exactly one DeepSeek-origin attempt occurred and no fallback ran. | Pass |
| Response validation | Unexpected returned models, incomplete output, invalid JSON/schema, oversized buffered responses and incomplete streams fail closed. | Pass |
| Privacy and reasoning | `reasoning_content` returned beside structured output is absent from `PublicCompletion`, `SafeAudit`, dataclass serialization and repr. Only an aggregate reasoning-token count is retained. The audit stores an input SHA-256 rather than prompt text. | Pass |
| Public failure path | A mocked provider body and test credential did not enter the public planning-run response, warnings, events or inference audit when the council failed. | Pass |
| Budgets and timeouts | Every integer/time limit has a reviewed ceiling, custom run budgets cannot exceed loaded limits, expired wall budget and excess token reservation stop before transport, and the remaining run time caps each HTTP phase. Request reservations remain consumed on attempted failures; HTTP timeouts become safe blocked states. | Pass |
| Images | Text roles, disallowed modes and forged remote image URLs fail before transport. Existing image normalization removes metadata and accepts only bounded, decoded, inline PNG input. | Pass |
| Synthetic visual provenance | The integrated vision path generates its own labelled fixture, uses the vision route once, verifies the visible fixture label and returns `origin=synthetic`, `agronomic_measurement=false`, source/normalized hashes and a DeepSeek audit. | Pass |
| Secret delivery | `scripts/serve.py` accepts no CLI secret, can load a user-owned mode-0600 server file, disables access logging, and rejects a group-readable file before server startup. Subprocess output and the test marker contained no credential value. | Pass for tested local delivery |

Provider-private reasoning in a tool workflow is intentionally copied into the second DeepSeek request because the API continuation needs the exact assistant tool-call message. It stays in local request memory, is cleared afterward and is not included in the public result. The current council uses structured chat rather than this tool workflow.

## Findings and limitations

### PR-01 — exact reviewed role routing (resolved during review)

The initial review found that the loader accepted added or reassigned roles using otherwise allowed models. The gateway author then pinned the exact 13-role model/capability map. Independent mutation cases now show that added, missing, reassigned, or capability-changed routes fail during config load.

### PR-02 — reviewed resource ceilings (resolved during review)

The initial review found that several resource and timeout values could be raised through config. The gateway author added exact limit fields, finite positive type checks, reviewed ceilings for every integer/time value, and validation that a caller-supplied `RunBudget` cannot exceed the loaded manifest. Independent mutations cover concurrency, requests, tokens, request/response bytes, image bounds, wall time, and all four HTTP timeout phases.

### PR-03 — process egress hook is not infrastructure isolation (known limitation)

The Python DNS/audit hook materially narrows ordinary Python socket connections, and the adversarial subprocess test passed. A Python hook cannot replace an OS firewall/network namespace and may not constrain a native extension or separately spawned executable. Production still needs infrastructure egress restricted to the reviewed DeepSeek origin/address path, with ingestion running separately.

### PR-04 — synchronous cancellation boundary (known limitation)

During review, buffered JSON was changed to an incrementally bounded response read and each HTTP phase is capped by the smaller of its configured timeout and the remaining run budget. Synchronous council cancellation is still checked between roles and cannot interrupt an active HTTP call. The in-flight operation remains bounded by the gateway timeout/run budget rather than an immediate user cancellation signal.

### PR-05 — local secret delivery shares the API process (low/deployment)

The local file path validates target ownership and group/other permission bits, then places the key in the API process environment. All Python code in that monolithic process can therefore read it. The test does not establish parent-directory/symlink hardening, secret-manager rotation or container-level worker separation. Deployment environment injection into a narrowly scoped inference process is preferable.

### PR-06 — future historical/private context needs a transmission minimizer (future scope)

Gateway policy permits `historical_replay`, while the integrated council currently constructs and labels a synthetic-only context. If authorized private history is later sent through that mode, the call site needs a reviewed minimization/redaction contract. Current code does not silently enable live/private inference, and the browser cannot select this mode.

### PR-07 — mocked review does not establish live capability or network identity

This review proves local policy and error behavior. It does not prove account model availability, provider-side behavior, DNS/TLS identity, deployment firewall rules, billable request limits or actual vision quality. Those require the separately controlled authenticated trial and infrastructure review. No statement in this report upgrades a mocked check to live verification.

## Tests actually run

Focused independent suite:

```bash
.venv/bin/python -m pytest tests/review/test_provider_isolation.py -q
```

Result: **59 passed**. This includes exact route-map and limit-ceiling mutation, unknown-role, pre-transmission mode/image, proxy/redirect, provider error/timeout, response-bound, private-reasoning, public-error sanitation, synthetic-vision provenance, local-secret delivery and isolated process-egress cases.

Combined regression:

```bash
.venv/bin/python -m pytest tests/deepseek tests/security/test_api.py tests/review/test_provider_isolation.py -q
```

Result: **104 passed**, with two existing Starlette/httpx deprecation warnings and no failures. No actual provider call was made.

## Recommended disposition

The current synthetic development integration passes provider-isolation review at the application layer. PR-01 and PR-02 were closed and independently revalidated during review. PR-03 remains an infrastructure release requirement. PR-04 and PR-05 should stay visible until immediate in-flight cancellation and deployment secret isolation are implemented. Live capability status must continue to come from the authenticated DeepSeek trial, not this mocked review.
