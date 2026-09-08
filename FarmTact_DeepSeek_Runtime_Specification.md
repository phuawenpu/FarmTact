# FarmTact — DeepSeek-only runtime and test specification

**Version 1.1 · Documentation checked: 8 September 2026 · Applies to all application LLM execution**

This is a mandatory amendment to `FarmTact_Build_Specification.md`, the master prompt, all specialist briefs and deployment acceptance criteria. On runtime-provider questions, this amendment takes precedence over version 1.0. The agricultural evidence, ten-crop scope, data provenance, forecasting, optimization and human-approval requirements remain in force.

## 1. The provider boundary

**Build-time:** the developer's GPT/Codex master and coding/research subagents may research, author files, review code and generate explicitly labelled development fixtures. Their model configuration remains in `.codex/`. This configuration must never be loaded by the FarmTact server.

**Application execution:** every actual LLM inference made by FarmTact—in development, interactive test, staging, evaluations, demo sessions, scheduled jobs or production—must go directly to the official DeepSeek API. This includes specialists, chair, critic, helpers, runtime literature extraction, alias resolution, translation, visual analysis, summarization and any LLM judge. A helper hidden behind a tool is still runtime inference. No OpenAI, Anthropic, Gemini, OpenRouter, other hosting provider or local generative LLM fallback is permitted.

A developer may use GPT to inspect code or review research. They may not run a GPT-backed FarmTact council and label it a test of the deployed system. Do not build on GPT and defer discovering DeepSeek incompatibilities until the presentation: implement and exercise the DeepSeek gateway early.

Conventional local computation remains allowed: statistical forecasts, optimization, geospatial processing, image normalization, OCR-free document text parsing, SQL/full-text/BM25 retrieval, image measurements and unit conversion. These are not LLM-provider calls. Do not invent a DeepSeek embeddings or hosted-search endpoint. Start with local full-text retrieval; any future learned encoder needs its own explicit design/licence review and cannot become a hidden alternative generative agent.

## 2. Current documented API and the selected application contract

DeepSeek's current quick-start lists `deepseek-v4-flash`, `deepseek-v4-pro` and `deepseek-v4-flash-vision-exp`. Its changelog records the vision model's experimental release on 21 August 2026. Use these documented aliases rather than assuming self-hosted model names or old `deepseek-chat`/`deepseek-reasoner` tutorials remain appropriate. Recheck official documentation and account access during deployment. [DS01, DS02]

| FarmTact request | Exact selected route | Required model/capability |
|---|---|---|
| Text generation, discussion, extraction and function calls | `POST https://api.deepseek.com/chat/completions` | An approved Flash or Pro alias |
| Farm images, scanned-page images, charts and rendered geospatial images | **The same** `POST https://api.deepseek.com/chat/completions` | **`deepseek-v4-flash-vision-exp`** |
| Account model discovery | `GET https://api.deepseek.com/models` | Bearer authentication; model list is not proof of modality quality |
| Optional future reusable-image upload | `POST https://api.deepseek.com/files` | Separate permission, lifecycle and integration tests |
| Optional future strict tool schema mode | `POST https://api.deepseek.com/beta/chat/completions` | Separate reviewed beta adapter; disabled in this seed |

There is no FarmTact dependency on an invented `/vision` or `/images/analyze` path. Our chosen wire format is **Chat Completions**, even when using a compatibility SDK. DeepSeek also documents other API formats; supporting them is unnecessary for this vertical slice and would add a second compatibility surface. [DS03, DS04, DS06, DS08]

The seed implementation uses `httpx` directly. Using the OpenAI Python SDK as a transport library would not itself mean using OpenAI inference, but it is not necessary here. Do not initialize an SDK with a default provider URL, inherit a developer's OpenAI key, or activate framework tracing/exporters that send application content to another LLM vendor.

### 2.1 Capability routing

| Runtime role or helper | Proposed default | Input contract |
|---|---|---|
| Demand Analyst | `deepseek-v4-flash` | Typed customer-demand and tool-result text |
| Crop Scientist | `deepseek-v4-pro` | Reviewed agronomic evidence and approved recipes |
| Supply & Weather Scout | `deepseek-v4-flash` | Weather, trade and remote-sensing **tool outputs** |
| Resources & Margin Analyst | `deepseek-v4-flash` | Validated capacities, costs and solver outputs |
| Planning Chair | `deepseek-v4-pro` | Comparable strategies and evidence-backed dissent |
| Independent Critic | `deepseek-v4-pro` | Claims, provenance and constraint results |
| Evidence Extractor / Crop Alias Resolver | `deepseek-v4-flash` | Source text; structured but untrusted proposed extraction |
| Runtime Researcher | `deepseek-v4-pro` | Approved retrieval tools; no unrestricted browser or shell |
| Visual Observer / Document Vision / Satellite Visual Reviewer | `deepseek-v4-flash-vision-exp` | Validated images plus bounded questions |
| Test Evaluator, if LLM-based | `deepseek-v4-pro` | Evaluation evidence; never substitutes for numerical assertions |

These assignments are project defaults, not a proven ranking of model suitability. Compare capability and cost on FarmTact tasks. A text specialist asks a vision helper for an image observation rather than sending the image to its own text model. Cross-role messages contain reviewed observation fields and provenance, not copied private reasoning.

All newly added agents must register a reviewed DeepSeek route. Model choices are server-controlled, not taken from a user prompt, retrieved document or browser request. Missing roles fail closed. A failed vision capability check disables image-dependent features; it must not silently route the image to Pro, Flash, GPT or another provider. Text-only planning can remain available with an explicit missing-visual-evidence warning.

## 3. Correct image requests and agricultural limits

DeepSeek documents images in `user` messages for Chat Completions, using content blocks. Non-vision models do not accept them. The initial FarmTact integration sends normalized inline PNG data, keeping remote URL fetching and persistent uploads out of the first implementation. [DS03, DS04]

```python
# HTTP JSON payload; DEEPSEEK_API_KEY belongs only in the Authorization header.
payload = {
    "model": "deepseek-v4-flash-vision-exp",
    "thinking": {"type": "disabled"},
    "max_tokens": 1024,
    "response_format": {"type": "json_object"},
    "messages": [{
        "role": "user",
        "content": [
            {"type": "text", "text": "Return JSON describing visible observations and uncertainty. Do not infer crop yield."},
            {"type": "image_url", "image_url": {
                "url": normalized_png_data_url,
                "detail": "original"
            }}
        ]
    }]
}
```

**FarmTact limits, deliberately stricter than provider ceilings:** four images per request, 4 MiB per decoded/normalized image, 4096 pixels per side, static frames only, and a 16 MiB serialized request ceiling. Verify bytes rather than a filename or client MIME label. Reject decompression bombs; remove EXIF/location metadata; select and label relevant frames; and keep an immutable source hash. Dense tables need appropriate crops/tiles and provenance—do not assume one downsized page preserves every small number.

For born-digital papers, parse available text and tables locally first. Use DeepSeek vision only for pages, figures or scans that actually require it. Never upload a PDF, spreadsheet, raw GeoTIFF or radar product and pretend it is a supported photo. Render the relevant view and retain page/band/geographic metadata through a separate scientific preprocessing tool.

A field photograph can support a tentative visual observation. It does not independently establish pathogen identity, future marketable kilograms, nutrient dosage or crop safety. Structured visual output must include `asset_id`, `source_sha256`, observation time, crop/system context supplied by the farm, visible findings, unknowns, ambiguity, model/route version and review status. Any count or chart extraction is a proposed measurement until validated. It cannot mutate an approved recipe.

For satellite work, deterministic geospatial tools calculate masks, georeferencing, indices and regional summaries. The visual helper may explain a rendered map, not replace that computation. Preserve acquisition date, processing version, cloud validity and pixel support. A render of a flood or vegetation anomaly is not a validated percentage yield loss.

The official Files API is optional. If adopted, use its documented image upload contract, explicit expiry, tenant-to-file mappings, and deletion/cleanup tests. The documentation says omitting expiry keeps uploaded files permanently; do not copy that default into FarmTact. Inline encoding should not be described as a guarantee of zero provider retention. Review service/privacy terms and obtain authorization before transmitting private farm assets. [DS08]

## 4. Tool calls, structured output and reasoning

The application—not the model—executes approved tools. Parse returned function arguments, validate a local schema, verify tenant and role permissions, and then call an allowlisted implementation. Preserve tool-call identifiers when returning results. No tool can run arbitrary shell commands, execute model-written SQL, approve a plan, modify recipes or make purchases. DeepSeek documents tools in both thinking and non-thinking workflows. [DS06]

For the stable endpoint, use `response_format={"type":"json_object"}` plus an explicit JSON instruction and a server-side Pydantic/JSON Schema validator. JSON syntax is not the same as conformity to a FarmTact schema or scientific truth. Reject empty, truncated, malformed and semantically invalid output. Do not copy OpenAI-specific `json_schema` settings into this interface without separate documented support. [DS04, DS07]

Strict function schemas are a separate beta feature. They require the beta URL and supported schema subset. The supplied gateway rejects `strict=true` rather than silently claiming enforcement on the standard URL. An optional later adapter needs its own allowlisted route, schema normalization and authenticated compatibility tests; it must never weaken business validation. [DS06]

Set thinking mode explicitly rather than relying on provider defaults. Begin with disabled thinking for short extraction and image transport tests; use enabled thinking with a declared effort for deeper council work. The current API lists `low`, `high` and `max` effort values. These are provider controls, not forecast confidence scores. [DS04]

Maintain the original assistant tool-call message—including provider-returned `reasoning_content` when present—in **private, in-memory continuation state** for that same tool workflow. This is a conservative interoperability requirement to be verified by the authenticated round-trip test. Do not discard fields inadvertently in a framework conversion, synthesize missing private reasoning, or publish it in the strategy-room transcript. The full thinking guide was not retrievable in this review; its indexed text and the tool/API references were reviewed, and the live continuation test remains required. [DS04, DS05, DS06]

Public traces show concise conclusions, citations, tool names/status, latency and usage. They do not show private reasoning, raw credentials, complete customer orders or image base64. Dispose of continuation state after the workflow; use restricted, encrypted short-lived state only if recovery truly requires it.

## 5. Runtime architecture and configuration

The browser calls FarmTact, never DeepSeek directly. A server-only gateway owns the environment key, validates model/capability routing and emits safe audit metadata. Application workers receive only the permissions their jobs require. Public-data ingestion calls remain permitted to approved government/scientific APIs; that permission is separate from LLM egress.

```text
GPT/Codex development workspace -- authors/reviews --> FarmTact repository
                         (not part of deployed inference)

FarmTact browser --> authenticated backend / council state machine
                                      |
                           numerical and retrieval tools
                                      |
                           DeepSeek-only model gateway
                                      |
                         api.deepseek.com/chat/completions
                       text: Flash / Pro     images: Vision-Exp
```

Use `.env.example` for names, but supply the actual `DEEPSEEK_API_KEY` through the environment or secret manager. Never place it in a `NEXT_PUBLIC_*` variable, command-line argument, client bundle, committed `.env`, screenshot or report. Do not print environment dumps. Sharing a development machine with Codex does not authorize reusing its credentials in runtime.

Distinguish **data mode** from **execution mode**:

| Data mode | Meaning |
|---|---|
| `synthetic_demo` | Fictional orders/crops; no farm-performance claims |
| `historical_replay` | Historical inputs with an explicit decision cutoff |
| `live_advisory` | Current farm inputs; human approval still required |

| Execution mode | Meaning |
|---|---|
| `test` | Every actual LLM request goes to DeepSeek; can use synthetic inputs |
| `live` | Every actual LLM request goes to DeepSeek; release gates required |
| `replay` | No new inference; clearly labelled stored events or deterministic outputs |
| `contract_test` | Developer-only in-process HTTP mocks; not an interactive platform agent mode |

An API key's presence must not silently change either mode. Replaying a stored DeepSeek response is not a fresh DeepSeek call. GPT-authored mock conversation is a **development fixture**, not a DeepSeek replay. Persist `execution_mode`, `data_mode`, `provider`, `requested_model`, `returned_model`, prompt/tool-schema version, input hashes and `inference_origin` on decision records and exports.

### 5.1 Defense in depth

The seed permits only the exact direct HTTPS origin and the reviewed model list. It disables redirects and inherited HTTP proxy settings; it has no fallback client. Production must also enforce network policy: the inference service can reach only approved DeepSeek endpoints, while ingestion services get separate data-source permissions. A Python allowlist is not a substitute for deployment egress controls.

Exclude `.codex/`, developer provider credentials and developer-only tools from runtime images. Do not add provider auto-detection. New runtime helper prompts or evaluation jobs must be included in the route registry and provider-leak audit. Scan bundles/configuration and exercise failures at runtime; a string scan alone cannot establish correct egress.

Use opaque tenant/user isolation identifiers generated by the server, never buyer names or email addresses. DeepSeek documents a `user_id` parameter for isolation; this complements but does not replace FarmTact authorization and tenant-scoped storage. [DS10]

### 5.2 Failures and cost

Authentication or balance failures become a clear blocked state, not a provider switch. Invalid requests need a code/configuration correction. Rate limits and temporary service errors may get bounded backoff with jitter **only to DeepSeek**, under the same run budget. Do not blindly retry an interrupted billed generation or a business write. The seed deliberately performs no automatic retries. [DS09]

Stop on unavailable required models, incomplete completions, unknown finish reasons, schema errors or unexpected response models. The farmer may explicitly use a deterministic baseline without agents, but it must be labelled as such. Never manufacture an agent conversation to conceal an outage.

Meter input, output, cached-input and reasoning usage where returned. Load any USD cost schedule from an operator-approved, date-stamped source; do not hard-code a remembered price. The pricing page did not expose a dependable price table in this retrieval, so this amendment makes no numerical pricing claim. The trial enforces request and reserved-output-token ceilings, not an independently verified USD billing cap. Production requires a conservative total-cost reservation and a hard wall-clock cancellation mechanism.

## 6. Implement and test DeepSeek before integrating the council

### DS-G0 — Static policy and offline contracts

A09 and A12 inspect the existing repo for provider SDK defaults, hosted tracing, third-party OCR/vision, cloud embeddings, LLM evaluation services and runtime GPT settings. Build the shared gateway, remove runtime alternate-provider credentials and publish a route/capability manifest. A11 runs negative tests against endpoint overrides, missing keys, unknown roles/models and prompt-selected providers.

**Included implementation:** `runtime/deepseek_gateway.py`, synthetic image fixture, and `tests/deepseek/test_gateway.py`. The offline tests use `httpx.MockTransport` and exercise wire-format/error handling only; they do not test DeepSeek's actual service or model quality.

### DS-G1 — Authenticated capability trial

Run `scripts/deepseek_trial.py --live` with an environment key and `FARMTACT_EXECUTION_MODE=test`. This performs model discovery, Flash/Pro JSON probes, an actual thinking/tool-result round trip, an actual image-reading request and a streaming/usage probe. The image contains a batch identifier absent from the text prompt, so the test verifies image input rather than a model repeating a supplied textual answer.

The default full probe uses at most seven HTTP requests: model listing, two text calls, two calls for tool continuation, one vision call and one stream. No automatic retry is enabled. A failure stops the sequence and is reported honestly. Missing credentials are `BLOCKED` with zero calls and a nonzero exit code, not `SKIP` disguised as a passing release check.

Require both a discovered model and a successful content-level probe. An experimental vision alias being listed does not prove the user's account can execute the required request. Do not promote image features when that probe fails.

### DS-G2 — Actual DeepSeek council on synthetic farm inputs

Run the same script with `--with-council`. Six actual role calls discuss a labelled toy Singapore caixin snapshot after the capability probes. It presents a seven-day delivery window and a 35-day new-crop lead time; agents must not claim that new sowing can solve this delivery. The test validates evidence references and human-approval requirements.

This option adds six model calls, taking the successful script to thirteen HTTP requests, within its sixteen-request ceiling. It is a transport/workflow seed, not the finished optimizer, full agricultural council evaluation or evidence of production benefit. The complete app must subsequently run its real forecast and optimization tools rather than relying on this toy snapshot.

### DS-G3 — Application shadow run and promotion

Once the app exists, replay the same frozen farm data through the deterministic planning baseline and the DeepSeek-only council. Compare constraint compliance, citation validity, unresolved evidence, rejected claims and decision completion. Do not introduce GPT as a runtime judge or competitor. Build-time human/Codex review remains permitted and must be attributed separately from runtime evaluation.

Add a real image-to-observation-to-text-council workflow; verify that the underlying image never reaches a text model. Introduce a weather or order change and test replanning, including the impossible-near-term-sowing counterexample. Record actual elapsed time and provider usage, not promised performance.

Promotion requires authenticated core and vision probes, the full app's read-only shadow run, independent review, zero unexplained non-DeepSeek LLM egress and a deliberate operator setting change to `live`. Do not require all application development to stop while credentials are unavailable, but keep runtime-verified/release-ready claims blocked.

### DS-G4 — Rollback

Rollback is to a previously tested DeepSeek configuration, an explicitly labelled read-only deterministic baseline, or replay. It is never automatic migration to another provider. A changed model alias/backend fingerprint triggers reevaluation of relevant golden cases. Keep the original input and tool artifacts so model upgrades can be compared fairly.

## 7. Mandatory acceptance cases added to the original forty

| ID | Release requirement |
|---|---|
| DS-01 | Every runtime/helper/evaluation role resolves to a reviewed DeepSeek model |
| DS-02 | GPT/Codex build settings are isolated from deployment configuration |
| DS-03 | Missing/invalid key blocks agent execution without key disclosure |
| DS-04 | Wrong origins, downgrade to HTTP, redirects and alternate-provider fallback are blocked |
| DS-05 | Actual model discovery runs against the user's account |
| DS-06 | Actual text JSON probes succeed and pass local schema validation |
| DS-07 | Actual thinking/tool-result continuation succeeds with preserved private state |
| DS-08 | Actual image probe succeeds on the vision model and correct endpoint |
| DS-09 | Text-model image requests fail before transmission |
| DS-10 | Invalid image roles, oversized/deceptive files and unsafe remote URLs are blocked |
| DS-11 | Empty/truncated/invalid outputs never become approved claims |
| DS-12 | Unknown tools, invalid arguments and unauthorized tenant scope are rejected |
| DS-13 | SSE keep-alives, usage and termination are parsed; incomplete streams are failures |
| DS-14 | A six-role DeepSeek-only synthetic council preserves lead time and approval rules |
| DS-15 | Actual app image-to-council workflow preserves visual provenance and uncertainty |
| DS-16 | 401/402/429/5xx scenarios never route to another LLM provider |
| DS-17 | Provider/model/mode/usage metadata is retained without keys, image payloads or private reasoning |
| DS-18 | Production egress and bundled dependency audit finds no hidden runtime provider calls |
| DS-19 | Test/live/replay labels remain distinct across UI, logs and exported strategies |
| DS-20 | Promotion and rollback require explicit action; completed business tools are not executed twice |

A09 owns gateway and council implementation; A12 owns isolated environments, network policy, trial execution and release evidence; A11 independently verifies the policy and tests. A04 adds audit/mode fields to shared contracts. A05/A06 route any LLM-assisted ingestion interpretation through the gateway. A02/A03 separate initial GPT-assisted research provenance from later DeepSeek runtime extraction. A07/A08 keep calculations local and send only their validated results to agents. A10 displays model/mode/vision availability and blocked states honestly. A01 records new runtime extraction lineage.

## 8. Handoff implementation status and remaining work

Included code is a **tested gateway and trial seed**, not a production application. Offline tests cover the policy and selected wire-format behaviours. No environment key was available during this amendment; the bundled authenticated trial report is `BLOCKED`, with zero calls. Do not convert that report to `PASS` by editing it—rerun the script with real credentials.

A09/A12 must still integrate tenant authorization and secret delivery; implement production async cancellation, bounded streaming tool-argument assembly, cost reservation, idempotent jobs, concurrency management and safe retry policy; connect real farm tools; and enforce deployment egress. The seed's per-request timeouts and buffered-response size checks are not a complete resource-exhaustion defense. Optional beta strict schemas and Files API are documented but not implemented/tested in the seed.

The gateway gives the master a real starting point and tests to extend. It does not waive any agricultural, data-quality, security or human-approval requirements in the original specification.

## 9. Primary documentation

Documentation was checked on **8 September 2026**. Exact URLs and access notes are also in `research/deepseek_api_sources.json`. Source summaries describe the checked material; they are not claims of account-level API testing.

- **DS01 — Quick start:** https://api-docs.deepseek.com/
- **DS02 — Changelog:** https://api-docs.deepseek.com/updates/
- **DS03 — Vision guide:** https://api-docs.deepseek.com/guides/vision/
- **DS04 — Chat Completions reference:** https://api-docs.deepseek.com/api/create-chat-completion/
- **DS05 — Thinking mode:** https://api-docs.deepseek.com/guides/thinking_mode/ — indexed official excerpts reviewed; repeated full-page retrieval failed.
- **DS06 — Tool calls:** https://api-docs.deepseek.com/guides/tool_calls/
- **DS07 — JSON output:** https://api-docs.deepseek.com/guides/json_mode/ — indexed official excerpts plus DS04 reviewed; full-page retrieval failed.
- **DS08 — Files API:** https://api-docs.deepseek.com/guides/files_api/
- **DS09 — Error codes:** https://api-docs.deepseek.com/quick_start/error_codes/
- **DS10 — Rate limits and isolation:** https://api-docs.deepseek.com/quick_start/rate_limit/
- **DS11 — Model listing:** https://api-docs.deepseek.com/api/list-models/
- **DS12 — Pricing:** https://api-docs.deepseek.com/quick_start/pricing — retrieval displayed quick-start content; no numerical price table adopted.
