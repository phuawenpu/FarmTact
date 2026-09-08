# FarmTact AI injection, exfiltration, provider, and tenant-boundary audit

Date: 2026-09-08  
Scope: deployed API-to-DeepSeek paths, council, vision, persistent conversations, provider output/tool handling, tenant-scoped storage, and the root-owned request-admission changes present during this review. No paid inference was performed.

## Result

No remotely reachable cross-tenant read/write path, provider-selection override, arbitrary tool execution path, or secret-reflection path was found in the reviewed application routes. One provider-side tenant-isolation gap and one inference-budget reconciliation defect were found and repaired during review. Request admission now limits AI-triggering requests by source network and tenant before body parsing or job lookup. Remaining issues are defense-in-depth and product-semantics limitations, not demonstrated remote data-exfiltration vulnerabilities.

## Findings

### Repaired: DeepSeek requests lacked provider-side user isolation

Before this audit, every application tenant shared an otherwise identical provider request identity. The application database remained tenant-scoped, but the gateway did not send DeepSeek's documented `user_id`, so provider content-safety, KV-cache, and scheduling isolation could not distinguish FarmTact tenants.

DeepSeek's current official documentation confirms that Chat Completions accepts a top-level `user_id` matching `[a-zA-Z0-9\-_]+` with a maximum length of 512, and describes content-safety, KV-cache, and scheduling isolation: <https://api-docs.deepseek.com/quick_start/rate_limit/> and <https://api-docs.deepseek.com/api/create-chat-completion/>.

The repaired gateway validates this field at `runtime/deepseek_gateway.py:385-400`, includes it in all chat, tool-continuation, vision, and stream payloads at `runtime/deepseek_gateway.py:747-758`, and derives `farmtact_<sha256>` from the random internal tenant ID at `runtime/deepseek_gateway.py:1004-1011`. The raw tenant ID, session cookie, IP address, buyer identity, and other personal data are not sent as the provider identifier. Conversation jobs pass the pseudonym at `services/api/conversations.py:1233-1239`; mission council and vision calls pass it from the root-owned worker at `services/api/app.py:85-101`. Standalone bounded trials use the explicit non-tenant scope `farmtact_standalone_trial`.

Impact before repair: defense-in-depth privacy and provider scheduling isolation were absent. This was not a database authorization bypass and no cross-tenant response was observed.

### Repaired: inference reservations could reconcile against the wrong UTC day

The prior `release_unused_calls()` selected the current UTC day rather than the day on which calls were reserved. A job crossing midnight could fail reconciliation, leave the prior day's reservation inflated, and turn an otherwise handled provider failure into a cleanup error. Root added an explicit bounded day parameter in `services/api/store.py:115-132`. Conversation execution now freezes `reservation_day` before reserving at `services/api/conversations.py:1191-1192` and uses the same day when releasing at `services/api/conversations.py:1422-1424`. The root worker applies the same pattern to planning missions.

Impact before repair: availability and accounting inconsistency. A release after midnight could decrement reservations already charged to the new day, incorrectly reopening daily allowance and creating additional spend risk. No cross-tenant disclosure resulted. The repaired code refunds only the original reservation bucket.

### Open, medium defense-in-depth: reference validation does not prove qualitative entailment

The council marks a claim validated when its tool/evidence references are members of the supplied sets and every numeric literal exactly matches a cited numeric tool value (`services/api/council.py:50-56`). Conversation output similarly checks frozen-reference membership, quantitative prose, highlights, and bounded proposed controls (`services/api/conversations.py:860-918`). Those checks stop invented numbers, foreign reference IDs, and unauthorized scenario controls. They do not prove that arbitrary qualitative prose is entailed by the cited source.

An injected sentence in a farm field, source summary, prior turn, or user question could influence a model to emit misleading qualitative prose while citing an unrelated valid reference. In planning missions, the independent critic recommendation participates in simulation acceptance (`services/api/app.py:125-133`), although local feasibility and allocation validation remain authoritative and all accepted work is simulation-only. In conversations, accepted references are explicitly labelled `interpretation_status=unverified_advisor_interpretation` (`services/api/conversations.py:437-446`) and proposed actions are hypotheses that the conversation path never executes.

Recommended follow-up: keep `references_verified` distinct from semantic validation; derive acceptance gates from deterministic validator fields; add claim-specific predicates where a qualitative assertion affects eligibility. Do not describe reference membership as factual entailment.

### Open, medium privacy hardening: provider context is broader than each role needs

Council roles receive every strategy's metrics, risk, status, assumptions, shared tool results, and selected evidence context (`services/api/council.py:19-40`). Persistent-conversation roles receive the shared frozen tool-result dictionary, evidence context, and as many as 32 recent public turns (`services/api/conversations.py:1003-1075`). The context is tenant-local, bounded, and intentionally sent to the approved DeepSeek route; no cross-tenant context source was found. However, a role-specific minimum is smaller for many questions.

Recommended follow-up: build per-role context projections and per-question reference selection, particularly before real tenant use. Continue pseudonymizing customer data and avoid sending complete orders or farm snapshots when a derived aggregate answers the question.

### Open, low trusted-code hardening: tool allowlisting is per invocation

`run_tool_json()` validates that the provider-selected tool is in the caller-supplied list, requires one call, validates arguments with the caller's Pydantic model, and invokes the caller's executor only after those checks (`runtime/deepseek_gateway.py:483-536`). This correctly rejects a remote/model-selected unknown tool or an extra tenant selector when argument models forbid extras. The gateway does not independently compare caller-supplied `ToolSpec` values with a global reviewed application registry.

No deployed HTTP route currently lets a remote caller register a `ToolSpec`, replace `execute_tool`, or access this generic tool workflow. Exploitation would require a trusted Python-code change. Before adding model tools to an HTTP workflow, introduce a reviewed role-to-tool registry and require server-derived tenant authorization in every executor.

### Open, low output-policy mismatch: prose shape relies partly on prompting

The persistent-conversation prompt requests exactly two sentences and at most 400 characters (`services/api/conversations.py:921-958`), while `AdvisorReply.content` permits up to 900 characters (`services/api/conversations.py:183-191`) and `_validate_reply()` does not enforce sentence count or the 400-character limit. A schema-valid model response can therefore violate the concise presentation rule. React text rendering and the response schema still bound the output; no script execution or secret access follows from this mismatch.

Recommended follow-up: enforce the same 400-character and sentence-count contract in deterministic validation if it remains a product requirement.

## Existing boundaries verified

- Provider configuration is exact and closed: only DeepSeek, `https://api.deepseek.com`, reviewed paths, reviewed models, and reviewed role mappings load (`runtime/deepseek_gateway.py:130-172`). The HTTP client disables redirects and inherited proxy configuration (`runtime/deepseek_gateway.py:408-420`). Prompt text cannot select a provider, origin, model, execution mode, or data mode.
- Model responses fail closed on non-`stop` completion, unexpected returned model, empty content, malformed JSON, and Pydantic/schema failure (`runtime/deepseek_gateway.py:798-837`, `runtime/deepseek_gateway.py:938-959`). Provider error bodies are discarded; request IDs are allow-character/length validated. Public completion and audit objects omit provider-private reasoning.
- Tool calls require one allowlisted name and strict local argument validation before execution (`runtime/deepseek_gateway.py:499-536`). Model-added tenant fields are rejected by strict argument models. Strict beta schemas are rejected on the stable route.
- Vision accepts only normalized inline PNG data on reviewed vision roles; text-role images, remote URLs, animations, oversized bytes/dimensions, and unsafe decodes fail before transmission (`runtime/deepseek_gateway.py:563-591`, `runtime/deepseek_gateway.py:684-719`, `runtime/deepseek_gateway.py:776-800`). The deployed vision workflow uses a generated synthetic label and checks the observed label exactly (`services/api/vision.py:15-26`).
- Conversations treat snapshots, prior messages, and user text as untrusted data in the system prompt (`services/api/conversations.py:941-957`). Output references must belong to the frozen tenant context; quantitative/temporal prose is rejected; scenario-control targets and ranges are validated (`services/api/conversations.py:860-918`). Invalid output gets bounded schema-only repair context rather than raw validation input (`services/api/conversations.py:961-1000`, `services/api/conversations.py:1263-1301`).
- Tenant ownership is applied before route access and on persistent selects/updates. Farm/run/event queries include tenant predicates (`services/api/store.py:65-108`); scenario and source-conversation lookups include the authenticated tenant (`services/api/scenarios.py:66-72`, `services/api/scenarios.py:172-220`); conversations, messages, requests, and events use tenant predicates and composite foreign keys (`services/api/conversation_store.py:33-107`, `services/api/conversation_store.py:120-507`). Cross-tenant object IDs return the same not-found behavior as nonexistent IDs.
- Sessions use random tokens, store only token hashes, expire authentication after one day, and use HTTP-only, strict-site cookies (`services/api/store.py:57-64`, `services/api/app.py:202-207`). Operational acceptance remains inaccessible to browser callers, and planning acceptance independently checks tenant-local frozen versions and numerical feasibility.
- Root-owned request admission persists hashed counters and applies global API, per-IP, per-tenant AI, session-creation, write, unknown-path probe, and event-stream limits (`services/api/security.py:25-55`, `services/api/security.py:96-156`). Admission happens before request parsing and object lookup, returns generic 429/401/403/503 bodies, and caps concurrent/elapsed event streams (`services/api/security.py:159-205`). The AI matcher includes direct conversations, invitations, councils, initial planning runs, and replans.
- Runtime egress uses the exact DeepSeek HTTPS origin plus the configured database destination and rejects other socket destinations (`services/api/egress.py:13-52`). This Python audit hook is defense in depth; the runtime specification correctly says it is not a substitute for infrastructure egress controls.

## New negative tests

`tests/review/test_ai_injection_boundaries.py` adds six mocked-inference cases:

1. Prompt text attempting to select OpenAI, an attacker origin, a GPT model, and live mode remains user content; the wire request stays on the reviewed DeepSeek route and includes the server pseudonym.
2. Provider `user_id` derivation is stable, does not contain the internal random tenant ID, and rejects invalid characters/length before transport.
3. Schema-valid JSON carrying uncontracted tenant, credential, and provider fields fails local validation without reflecting marker values in the error.
4. A model-added foreign `tenant_id` in strict tool arguments fails before the executor runs.
5. Unsafe provider-controlled request-ID header text is dropped from public audit metadata.
6. A schema-valid advisor response citing another tenant's frozen-object reference remains unsupported after membership validation.

All HTTP provider behavior uses `httpx.MockTransport`; placeholder credentials are passed directly to the constructor and no environment secret is read or printed.

## Verification

Passing focused regression after the provider-user and reservation-day changes:

```text
.venv/bin/python -m pytest -q tests/review/test_ai_injection_boundaries.py tests/deepseek/test_gateway.py tests/review/test_provider_isolation.py tests/gameplay/test_conversations.py
163 passed, 2 warnings in 21.52s
```

The warnings are existing FastAPI/Starlette deprecations. A broader run including `tests/security/test_api.py` initially produced 172 passes and one test-ordering regression because the new six-request AI burst limit masked a later schema assertion with HTTP 429. Root changed the test clock between independent schema probes without disabling limits. The corrected boundary/security subset then passed:

```text
.venv/bin/python -m pytest -q tests/security/test_api.py tests/review/test_ai_injection_boundaries.py
16 passed, 2 warnings in 78.70s
```

## Limitations

- This was a source review plus mocked provider testing. It did not send a live DeepSeek request, inspect provider-side cache behavior, or establish provider data-retention guarantees.
- It did not penetration-test Fly's edge, PostgreSQL roles, container isolation, DNS rebinding, or infrastructure egress policy. The Python egress hook cannot provide a kernel/container boundary against arbitrary native code.
- Anonymous development sessions remain intentionally weaker than production identity and role-based access. The new rate limits and 24-hour expiry constrain abuse; they do not constitute production authentication or farm authorization.
- Prompt injection cannot be eliminated by a system prompt. The meaningful boundary is that untrusted text cannot choose routes or tools, outputs are locally constrained, and deterministic code remains authoritative. Qualitative entailment and context minimization remain the principal follow-up items.
