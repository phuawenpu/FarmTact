# Runtime implementation audit — 11 September 2026

The latest published application edition is **v10**, built from source
`ec4e29874b2c7408f2bd93d012912e3c0cb8d2f3` and image
`registry.fly.io/farmtact@sha256:874530e73f481b1197e528bb5f124b958a74be64c9934292c14438b4cdd503bf`.
Frozen earlier source/images and historical probe results are unchanged. See the
[V10 grounding follow-up](docs/technical/v10-grounding-followup.md), [V10 evidence](reports/v10/),
[V9 AI follow-up](docs/technical/v9-ai-followup.md), [V9 evidence](reports/v9/),
[V8 remediation report](docs/technical/v8-remediation-report.md),
[Council package evidence](reports/v8/council.md), and [AI/provider report](docs/technical/ai-provider-and-council.md),
[game backend report](docs/technical/game-backend-and-state-machines.md) and
[gap register](docs/technical/gaps-and-next-iteration.md).

**Implemented call semantics:** planning findings, conversation turns and optional
research adviser interpretations call the server-only gateway against frozen data.
Default research dialogue, numerical scenarios, News collection, artwork, audio and
recorded replay make no inference calls. The registered helper/evaluator/vision
roles are capability allowlists, not proof of integrated feature callers. The
main council consumes precomputed tool results; the gateway's tool round trip is
separately implemented/tested and is not an open-ended application agent loop.

The three Council workflows are intentionally different: a mission makes six
independent specialist calls and one chair call, with only the chair receiving
validated prior findings; persistent conversations offer direct, two-turn invite
and seven-turn sequential Council requests; guided research is scripted/local until
an explicit separate direct adviser request interprets a frozen result. No workflow
implements two challenge rounds or an unrecorded debate loop. Mission policy is
explicitly `required` or `advisory`; required withholds incomplete/unsupported
Council results, while advisory leaves numerical acceptance available with issues.

**Evidence semantics:** local JSON/reference/numeric checks constrain output, but
reference membership is not factual entailment. Both v7 recorded actual adviser
responses were unsupported. Transport, replay, frozen context and tenant-isolation
passes do not override that result or establish agricultural answer quality.

**V8–V10 implementation:** AI-01 through AI-12 have published server changes and
offline regression evidence. Current responses use code-rendered typed facts whose
entity, unit, period and snapshot hash come from server-owned context; qualitative
interpretation remains unverified. Prompt, schema, validator, context and source
versions are retained. Execution, evidence and decision influence are separate
statuses. The active caller manifest distinguishes product/API integrations from
diagnostic routes. Actual quality trials remain dated evidence and may fail.

V10 conversation prompts and context projection are V6. Mission prompts and context
are V7, validation is V5 and schema is V3: short per-role `F001` / `C001` aliases map by exact lookup to canonical frozen facts and qualitative references; unknown aliases fail closed. Every completion audit retains the supplied mapping and returned aliases. Role projection is
bounded to 48 typed facts, 24 qualitative references, 16 prior conversation turns
and six evidence records, with a hard 120,000 serialized-character limit. Exact
research inputs referenced by the frozen result remain admitted when normal rank
caps are reached. Truncation is explicit; a user question that cannot be answered
from admitted context must produce an abstention. A format repair retains the
rejected attempt and must preserve lexical meaning, relationships, proposed actions
and references while removing or relocating only the invalid number/date form.

V8's final ledger records 55 actual requests. Its completed public quality trial
failed: 6 of 10 completed quality cases passed, and invited return and conversational
Council were incomplete. Preserve the earlier 8/18 checkpoint and the later public
postmortem as dated evidence. V9's frozen offline suite passed 606 tests with one
skip; its mobile typed-fact check passed 21 of 21 assertions against intercepted
server-shaped fixtures with zero provider calls. All nine deployed-edition
health/source checks and preservation of v1–v8 passed. The authenticated public UI
replay passed 38 of 38 mobile/desktop checks without forwarding mutation or
inference requests. V9 used 21 actual requests
(nine mission, eleven conversation and one research), bringing the cumulative
ledger to 76. Its automated quality result is FAIL: 12 of 18 cases passed while
workflow integrity passed. Weather and Market Council abstentions persisted
unsupported with `abstention_payload`; the scorer also missed Supply's false
full-fulfilment claim for an 824 kg booked request against 370/446/518 kg scenario
deliveries. The completed AI-assisted review of 18 messages and 62 atomic assertions
found 10 sound, 5 sound with limits and 3 materially contradictory: Planning Supply
and two Production replies. Keep every actual request
and rejected attempt in its edition ledger; deployment and workflow counts do not
convert either trial into a quality pass.

V9's public capacity check passed two overlapping numerical jobs and 58 browse
samples with zero provider calls. Its 56-day synthetic execution run passed mass,
cash and lot-receipt checks with 60 task events, 64 demand-service events, one
future replan and zero provider calls. It did not exercise an actual application
restart.

Remaining work includes:

- Preserve the implemented distinction between archived probe evidence, configured
  credential readiness and the latest tenant execution. None is silently labelled
  as a fresh account capability probe.
- Continue the bounded grounded-answer benchmark with explicit abstention,
  contradiction and unsupported-claim reporting; transport success is insufficient.
- Keep route-to-caller/prompt/schema/budget inventory current. Prompts cannot select
  a provider, register tools, spend without reservations or authorize farm operations.
- Treat output-token and request ceilings as the limits actually implemented, not
  a guaranteed USD cap. Cancellation now prevents later request/repair calls and
  preserves a visible terminal state; a verified monetary reservation remains a
  separate future requirement.

The original provider-documentation review date below is historical. Configured
aliases and archived successful calls do not imply continuing account availability.
Any fresh provider-documentation review in the technical chapter is documentary
verification only; this audit performs no new authenticated inference trial.

### V7 research context amendment — published 10 September 2026

Scripted council concepts make no provider calls. Explicit actual advisor requests
may freeze a completed tenant-owned research result using snapshot_kind=research,
snapshot_id and research_version. The conversation retains the exact result hash,
reservation/order/labour controls and existing numerical evidence references.
An explanation never applies a proposal or changes research/main-farm inputs.
No provider fallback or new model route is added. The implementation experiment
ceiling is 16 requests including repairs, subordinate to shared admission/budgets;
unavailable or interrupted actual responses remain visibly distinct from scripts.

### V5 News support amendment — 9 September 2026

News collection, filtering, date interpretation and deterministic context selection
are conventional local operations with no inference route. The scout supports the
seven existing decision roles; it does not add an eighth council request. New
mission/scenario/conversation payloads freeze News evidence, and exact news reference
keys enter existing advisor tool results. Headlines are untrusted source assertions;
no automatic demand, price or yield adjustment is permitted. Browsing and numerical
runs continue to make zero provider calls. Explicit advisor requests use the existing
allowlisted DeepSeek models and finite shared limits. Older records with no News
context remain explicitly missing it; replay cannot fetch or invent a replacement.

# FarmTact — DeepSeek-only runtime and test specification

### Edition and voice-input amendment — 9 September 2026

Versioned editions keep independent game databases and application workers.
Existing public abuse limits and the 48-call daily application inference ceiling
apply across all editions through authenticated private operational controls.
An unavailable control service blocks paid work; it never falls back to an
independent per-edition allowance. Edition browsing, change summaries, reviews,
numerical experimentation and locally bundled sound perform no inference calls.

For initial voice input, users may use their device keyboard's dictation where
available. FarmTact receives ordinary text input and does not request microphone
access or transmit audio. A future custom transcription integration requires a
separate capability/provider decision; mentioning a future key does not configure
a speech endpoint or change the current DeepSeek-only application runtime.


**Version 1.2 · Autonomous development phase · Provider documentation review date retained: 8 September 2026 · Applies to all application LLM execution**

This is a mandatory amendment to `FarmTact_Build_Specification.md`, the master prompt, all specialist briefs and deployment acceptance criteria. On runtime-provider questions, this amendment takes precedence over earlier versions. Section 0 of the build specification controls the current autonomous-development phase: no human approval is required for implementation, testing, independent agent review or development acceptance. Agricultural evidence, twelve-profile/four-recipe scope, data provenance, forecasting, optimization and security requirements remain in force.

## 0. Autonomous development execution

All review, route registration, configuration, schema acceptance, trial execution and development promotion in this document can be completed by coding agents and technical checks. Terms such as “approved” and “reviewed” do not imply a human checkpoint during this phase. Record review results and apply passing changes automatically within Section 0 of the build specification.

The backend accepts only eligible development plans as `ACCEPTED_FOR_SIMULATION`, using a service identity and versioned policy after numerical, evidence, scope and evidence checks pass. It never invents a human actor or approval. Keep `development_phase=autonomous_development`, `decision_policy=automatic_development` and `execution_mode=test` for actual DeepSeek calls; explicit replay and contract-test modes remain distinct. The default data is `synthetic_demo`; already-authorized historical inputs may be used in `historical_replay` with separate simulated outcomes. Real farm execution and operational `live` promotion remain disabled.

Use supplied development credentials solely for the bounded official DeepSeek calls specified here. Record finite request, token, concurrency and wall-clock limits before execution; preserve the sixteen-request ceiling for the full trial and do not raise budgets automatically to bypass failures. If a required capability or credential is unavailable, record that dependency as blocked and continue work that does not need it. A synthetic fixture or deterministic baseline must never be reported as successful live inference.

## 1. The provider boundary

**Build-time:** the developer's GPT/Codex master and coding/research subagents may research, author files, review code and generate explicitly labelled development fixtures. Their model configuration remains in `.codex/`. This configuration must never be loaded by the FarmTact server.

**Application execution:** every actual LLM inference made by FarmTact—in development, interactive test, staging, evaluations, demo sessions, scheduled jobs or production—must go directly to the official DeepSeek API. This includes seven specialists/planner roles and helpers, runtime literature extraction, alias resolution, translation, visual analysis, summarization and any LLM judge. A helper hidden behind a tool is still runtime inference. No OpenAI, Anthropic, Gemini, OpenRouter, other hosting provider or local generative LLM fallback is permitted.

A developer may use GPT to inspect code or review research. They may not run a GPT-backed FarmTact council and label it a test of the deployed system. Do not build on GPT and defer discovering DeepSeek incompatibilities until the presentation: implement and exercise the DeepSeek gateway early.

Conventional local computation remains allowed: statistical forecasts, optimization, geospatial processing, image normalization, OCR-free document text parsing, SQL/full-text/BM25 retrieval, image measurements and unit conversion. These are not LLM-provider calls. Do not invent a DeepSeek embeddings or hosted-search endpoint. Start with local full-text retrieval; any future learned encoder needs its own explicit design/licence review and cannot become a hidden alternative generative agent.

## 2. Current documented API and the selected application contract

On 11 September 2026, authenticated model discovery returned `deepseek-flash` and
`deepseek-v4-pro`. DeepSeek's 10 September V4.1 notice and current pricing page
retired the previous Flash and experimental-vision identifiers and identify
`deepseek-flash` as canonical. V8 therefore allowlists only exact
`deepseek-flash` for current routes. Returned model identifiers must equal the
requested identifier; temporary provider rerouting is not accepted as an implicit
FarmTact alias. Evidence is retained in `reports/v8/model-discovery.json` and the
dated `model_migration` block in `config/deepseek_runtime.json`.

| FarmTact request | Exact selected route | Required model/capability |
|---|---|---|
| Text generation, discussion, extraction and function calls | `POST https://api.deepseek.com/chat/completions` | Exact `deepseek-flash` |
| Farm images, scanned-page images, charts and rendered geospatial images | **The same** `POST https://api.deepseek.com/chat/completions` | Exact `deepseek-flash`, native image content |
| Account model discovery | `GET https://api.deepseek.com/models` | Bearer authentication; model list is not proof of modality quality |
| Optional future reusable-image upload | `POST https://api.deepseek.com/files` | Separate capability configuration, lifecycle and integration tests; synthetic assets only by default in development |
| Optional future strict tool schema mode | `POST https://api.deepseek.com/beta/chat/completions` | Separate reviewed beta adapter; disabled in this seed |

There is no FarmTact dependency on an invented `/vision` or `/images/analyze` path. Our chosen wire format is **Chat Completions**, even when using a compatibility SDK. DeepSeek also documents other API formats; supporting them is unnecessary for this vertical slice and would add a second compatibility surface. [DS03, DS04, DS06, DS08]

Implement the development gateway with `httpx` directly. Using the OpenAI Python SDK as a transport library would not itself mean using OpenAI inference, but it is not necessary here. Do not initialize an SDK with a default provider URL, inherit a developer's OpenAI key, or activate framework tracing/exporters that send application content to another LLM vendor.

### 2.1 Capability routing

| Runtime role or helper | Proposed default | Input contract |
|---|---|---|
| Demand, Production, Weather, Profit, Planning Chair, Market and Supply Chain | `deepseek-flash` | Role-specific frozen context and typed fact IDs |
| Evidence Extractor / Crop Alias Resolver / Runtime Researcher | `deepseek-flash` | Source text; structured but untrusted proposed extraction |
| Visual Observer / Document Vision / Satellite Visual Reviewer | `deepseek-flash` | Validated native images plus bounded questions |
| Test Evaluator, if LLM-based | `deepseek-flash` | Evaluation evidence; never substitutes for numerical assertions |

These assignments are project defaults, not a proven ranking of model suitability. Compare capability and cost on FarmTact tasks. A text specialist asks a vision helper for an image observation rather than sending the image to its own text model. Cross-role messages contain reviewed observation fields and provenance, not copied private reasoning.

All newly added agents must register a reviewed DeepSeek route. Model choices are server-controlled, not taken from a user prompt, retrieved document or browser request. Missing roles fail closed. A failed vision capability check disables image-dependent features; it must not silently route the image to Pro, Flash, GPT or another provider. Text-only planning can remain available with an explicit missing-visual-evidence warning.

## 3. Correct image requests and agricultural limits

DeepSeek documents images in `user` messages for Chat Completions, using content blocks. Non-vision models do not accept them. The initial FarmTact integration sends normalized inline PNG data, keeping remote URL fetching and persistent uploads out of the first implementation. [DS03, DS04]

```python
# HTTP JSON payload; DEEPSEEK_API_KEY belongs only in the Authorization header.
payload = {
    "model": "deepseek-flash",
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

The official Files API is optional. If adopted, use its documented image upload contract, explicit expiry, tenant-to-file mappings, and deletion/cleanup tests. The documentation says omitting expiry keeps uploaded files permanently; do not copy that default into FarmTact. Inline encoding should not be described as a guarantee of zero provider retention. Coding agents review service/privacy terms as a technical task. Use synthetic or otherwise already-authorized assets for development probes without a confirmation step; exclude private assets lacking existing transmission authorization and continue with synthetic fixtures. [DS08]

## 4. Tool calls, structured output and reasoning

The application—not the model—executes approved tools. Parse returned function arguments, validate a local schema, verify tenant and role permissions, and then call an allowlisted implementation. Preserve tool-call identifiers when returning results. No runtime LLM tool can run arbitrary shell commands, execute model-written SQL, accept a plan, modify recipes or make purchases. The backend independently applies the automatic-development acceptance policy and records simulated work; it is not a council tool and does not need human approval. DeepSeek documents tools in both thinking and non-thinking workflows. [DS06]

For the stable endpoint, use `response_format={"type":"json_object"}` plus an explicit JSON instruction and a server-side Pydantic/JSON Schema validator. JSON syntax is not the same as conformity to a FarmTact schema or scientific truth. Reject empty, truncated, malformed and semantically invalid output. Do not copy OpenAI-specific `json_schema` settings into this interface without separate documented support. [DS04, DS07]

Strict function schemas are a separate beta feature. They require the beta URL and supported schema subset. The development gateway must reject `strict=true` rather than silently claiming enforcement on the standard URL. An optional later adapter needs its own allowlisted route, schema normalization and authenticated compatibility tests; it must never weaken business validation. [DS06]

Set thinking mode explicitly rather than relying on provider defaults. Begin with disabled thinking for short extraction and image transport tests; enabled thinking with a declared effort is a future option for deeper council work. Current application councils explicitly disable thinking; the authenticated tool-continuation probe exercises thinking separately. The current API lists `low`, `high` and `max` effort values. These are provider controls, not forecast confidence scores. [DS04]

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
                       text: deepseek-flash  images: deepseek-flash native vision
```

Use `.env.example` for names, but supply the actual `DEEPSEEK_API_KEY` through the environment or secret manager. Never place it in a `NEXT_PUBLIC_*` variable, command-line argument, client bundle, committed `.env`, screenshot or report. Do not print environment dumps. Sharing a development machine with Codex does not authorize reusing its credentials in runtime.

Distinguish **data mode** from **execution mode**:

| Data mode | Meaning |
|---|---|
| `synthetic_demo` | Fictional orders/crops; no farm-performance claims |
| `historical_replay` | Historical inputs with an explicit decision cutoff |
| `live_advisory` | Future operational mode; unavailable to automatic development acceptance |

| Execution mode | Meaning |
|---|---|
| `test` | Default development mode; every actual LLM request goes to DeepSeek; automatic acceptance is simulation-only |
| `live` | Future operational execution; disabled in the current development phase; separate operational release requirements apply |
| `replay` | No new inference; clearly labelled stored events or deterministic outputs |
| `contract_test` | Developer-only in-process HTTP mocks; not an interactive platform agent mode |

An API key's presence must not silently change either mode. Replaying a stored DeepSeek response is not a fresh DeepSeek call. GPT-authored mock conversation is a **development fixture**, not a DeepSeek replay. Persist `development_phase`, `decision_policy`, acceptance policy/version and actor, `execution_mode`, `data_mode`, `provider`, `requested_model`, `returned_model`, prompt/tool-schema version, input hashes and `inference_origin` on decision records and exports.

### 5.1 Defense in depth

The development gateway must permit only the exact direct HTTPS origin and the reviewed model list, disable redirects and inherited HTTP proxy settings, and have no fallback client. Production must also enforce network policy: the inference service can reach only approved DeepSeek endpoints, while ingestion services get separate data-source permissions. A Python allowlist is not a substitute for deployment egress controls.

Exclude `.codex/`, developer provider credentials and developer-only tools from runtime images. Do not add provider auto-detection. New runtime helper prompts or evaluation jobs must be included in the route registry and provider-leak audit. Scan bundles/configuration and exercise failures at runtime; a string scan alone cannot establish correct egress.

Use opaque tenant/user isolation identifiers generated by the server, never buyer names or email addresses. DeepSeek documents a `user_id` parameter for isolation; this complements but does not replace FarmTact authorization and tenant-scoped storage. [DS10]

### 5.2 Failures and cost

Authentication or balance failures become a clear blocked state, not a provider switch. Invalid requests need a code/configuration correction. Rate limits and temporary service errors may get bounded backoff with jitter **only to DeepSeek**, under the same run budget. Do not blindly retry an interrupted billed generation or a business write. The initial trial must perform no automatic retries. [DS09]

Stop on unavailable required models, incomplete completions, unknown finish reasons, schema errors or unexpected response models. The development backend may automatically use an independently validated deterministic baseline without agents, labelled as such, if the run policy permits it. Record the failed DeepSeek capability separately; baseline completion cannot pass authenticated council gates. Never manufacture an agent conversation to conceal an outage.

Meter input, output, cached-input and reasoning usage where returned. For development, coding agents verify and record any USD cost schedule from official, date-stamped provider documentation without waiting for operator sign-off; do not hard-code a remembered price. The pricing page did not expose a dependable price table in this retrieval, so this amendment makes no numerical pricing claim. The trial enforces request and reserved-output-token ceilings, not an independently verified USD billing cap. Production requires a conservative total-cost reservation and a hard wall-clock cancellation mechanism.

## 6. Implement and test DeepSeek before integrating the council

### DS-G0 — Static policy and offline contracts

A09 and A12 inspect the existing repo for provider SDK defaults, hosted tracing, third-party OCR/vision, cloud embeddings, LLM evaluation services and runtime GPT settings. Build the shared gateway, remove runtime alternate-provider credentials and publish a route/capability manifest. A11 runs negative tests against endpoint overrides, missing keys, unknown roles/models and prompt-selected providers.

**Required implementation:** `runtime/deepseek_gateway.py`, synthetic image fixture, and `tests/deepseek/test_gateway.py`. These artifacts are implemented; inspect the existing gateway, fixture and tests before extending them. The offline tests must use `httpx.MockTransport` and exercise wire-format/error handling only; they do not test DeepSeek's actual service or model quality.

### DS-G1 — Authenticated capability trial

Once implemented, run `scripts/deepseek_trial.py --live` automatically with the supplied environment key and `FARMTACT_EXECUTION_MODE=test`, under the recorded development request/token budget. No human confirmation is required. Here `--live` means real authenticated HTTP calls; it does not select `execution_mode=live` or authorize farm operations. The current trial must discover and request the exact canonical manifest model for JSON, thinking/tool-result, native-image and streaming probes. The image contains a batch identifier absent from the text prompt, so the test verifies image input rather than a model repeating a supplied textual answer. Historical Flash/Pro/experimental-vision reports remain archival evidence for their original configuration only.

The default full probe uses at most seven HTTP requests: model listing, two text calls, two calls for tool continuation, one vision call and one stream. No automatic retry is enabled. A failure stops the sequence and is reported honestly. Missing credentials are `BLOCKED` with zero calls and a nonzero exit code, not `SKIP` disguised as a passing release check.

Require both a discovered model and a successful content-level probe. A listed
model does not prove native-image execution or quality. Do not promote image
features when that probe fails.

### DS-G2 — Actual DeepSeek council on synthetic farm inputs

Run the same script with `--with-council`. Seven actual role calls discuss a labelled toy Singapore caixin snapshot after the capability probes. It presents a seven-day delivery window and a 35-day new-crop lead time; agents must not claim that new sowing can solve this delivery. The test validates evidence references, automatic simulation acceptance after backend checks, and rejection of real operational execution. It must complete without a human approval event.

This option adds seven model calls, taking the successful script to fourteen HTTP requests, within its sixteen-request ceiling. It is a transport/workflow seed, not the finished optimizer, full agricultural council evaluation or evidence of production benefit. The complete app must subsequently run its real forecast and optimization tools rather than relying on this toy snapshot.

### DS-G3 — Application shadow run and promotion

Once the app exists, replay the same frozen farm data through the deterministic planning baseline and the DeepSeek-only council. Compare constraint compliance, citation validity, unresolved evidence, rejected claims and decision completion. Do not introduce GPT as a runtime judge or competitor. Build-time human/Codex review remains permitted and must be attributed separately from runtime evaluation.

Add a real image-to-observation-to-text-council workflow; verify that the underlying image never reaches a text model. Introduce a weather or order change and test replanning, including the impossible-near-term-sowing counterexample. Record actual elapsed time and provider usage, not promised performance.

Development promotion requires authenticated core and vision probes, the full app's read-only shadow run, independent agent review and zero unexplained non-DeepSeek LLM egress. Passing checks advance the development gate automatically while keeping `execution_mode=test`. A change to operational `live` is outside this phase; it is not needed for development completion. Do not require all application development to stop while credentials are unavailable, but keep runtime-verified/release-ready claims blocked.

### DS-G4 — Rollback

Development rollback is automatic under a versioned policy to a previously tested DeepSeek configuration, an explicitly labelled deterministic simulation baseline, or replay; record the reason and resulting mode without human confirmation. It is never automatic migration to another provider. A changed model alias/backend fingerprint triggers reevaluation of relevant golden cases. Keep the original input and tool artifacts so model upgrades can be compared fairly.

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
| DS-14 | A seven-role DeepSeek-only synthetic council preserves lead time; independent backend validation accepts eligible simulation plans without any human action |
| DS-15 | Actual app image-to-council workflow preserves visual provenance and uncertainty |
| DS-16 | 401/402/429/5xx scenarios never route to another LLM provider |
| DS-17 | Provider/model/mode/usage metadata is retained without keys, image payloads or private reasoning |
| DS-18 | Egress and bundled dependency audit of the isolated development deployment finds no hidden runtime provider calls; repeat for future production |
| DS-19 | Test/live/replay labels remain distinct across UI, logs and exported strategies |
| DS-20 | Development promotion/rollback are automatic, policy-versioned and audited; stale acceptance is recomputed; projected simulation records are preserved; a future work-execution engine requires separate idempotency tests (GAME-01); operational live promotion remains disabled |

A09 owns gateway and council implementation; A12 owns isolated environments, network policy, trial execution and release evidence; A11 independently verifies the policy and tests. A04 adds audit/mode fields to shared contracts. A05/A06 route any LLM-assisted ingestion interpretation through the gateway. A02/A03 separate initial GPT-assisted research provenance from later DeepSeek runtime extraction. A07/A08 keep calculations local and send only their validated results to agents. A10 displays model/mode/vision availability and blocked states honestly. A01 records new runtime extraction lineage.

## 8. Implementation status and remaining operational work

V10 is deployed. The server-only gateway, capability routes, offline tests,
bounded authenticated trial, tenant authorization, reservations, idempotent jobs
and replay are implemented. See `runtime/deepseek_gateway.py`, `tests/deepseek/`,
`reports/deepseek/authenticated_trial_summary.md`, `reports/v9/` and the versioned
technical reports.
Historical trial reports establish only the capabilities and settings actually
exercised; v6's hosting and crop verification requested zero inference calls, while
v7 records two actual adviser calls whose interpretations remain unsupported.
Missing credentials or unavailable capabilities must still produce a visible
blocked state, never fabricated success or another-provider fallback.

The gateway and ten editions share one Fly Machine and volume while retaining
separate application databases/workers. Authenticated operational controls retain
the shared 48-call daily ceiling and abuse limits. This hosting change adds no
provider route, speech service or background inference. The News scout remains
a deterministic supporter of the seven-role council.

Real farm execution remains disabled. Infrastructure-level egress enforcement
and farm-specific operational validation remain requirements for future production.
Optional beta strict schemas and the Files API are not adopted merely because
the provider documents them. This specification is a requirements contract;
implementation and release reports are the evidence of tested behavior.

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


## Seven-agent routing amendment — 2026-09-09

Current runtime roles, in council order: `demand_analyst`, `weather_analyst`, `market_analyst`, `production_analyst`, `supply_chain_analyst`, `profit_analyst`, `planning_chair`. Remove the independent-critic route in v3. Existing v1/v2 deployments retain their frozen configuration. Numerical/evidence validation is local code, not a hidden replacement critic call. Each numerical council finding reserves at most 1,536 output tokens; seven calls plus two shared repairs reserve at most 13,824, leaving optional vision inside the unchanged 16,384 ceiling. No new provider, feed scraping, sentiment classifier or background inference is introduced. Market context is frozen with the result; no connected social feed is claimed. Historical evaluation reports retain their original six-role labels and settings.

## V9 AI follow-up — published 11 September 2026

The public V8 quality trial failed despite mission transport/reference success:
6 of 10 completed quality cases passed, and the invited return and conversational
Council were incomplete. See `reports/v8/public-ai-postmortem.md`. V9 uses mission
prompt/context V6, conversation prompt/context V5 and
validator V4. It preserves semantic names alongside exact aliases, passes the
actual required/advisory policy, bounds role-specific facts, balances comparison
segments, requires typed numerical evidence and enforces absent-source abstention
for Council source specialists. Direct/invited numerical questions remain
answerable from their frozen facts. Conversation prose targets 220 characters
under the unchanged 400-character hard limit. V9 is published from source
`89d29cc3e071e12373204ff234d0a261ce71b5a1` and the immutable image recorded above;
all nine edition health/source checks and preservation of v1-v8 passed. The frozen
offline suite passed 606 tests with one skip and the mobile typed-fact fixture check
passed 21 of 21 assertions. The actual-provider run used 21 requests: nine mission
requests for seven roles, eleven conversation requests for ten messages and one
research request. Mission and research transport passed; all conversation workflows
completed, but Weather and Market abstentions persisted `unsupported` with
`abstention_payload`. The combined automated result is FAIL: 12 of 18 cases passed
with workflow integrity PASS. The completed AI-assisted semantic review determined
that four automated failures were conservative prefix/word false negatives and two
were real abstention-contract failures. Separately, the scorer passed Supply's false claim that
an 824 kg booked request was fully delivered despite strategy deliveries of 370,
446 and 518 kg. The cumulative actual-request ledger is 76.

## V10 grounding-remediation edition — published 11 September 2026

V10 advances mission prompt/context to V7, conversation prompt/context to V6 and
validator to V5 while retaining schema V3. Code derives Supply's booked-fulfilment
status and applies a bounded phrase guard without semantic repair. Required-absence
conversation context strips numerical and prior-conversation prose and supplies
explicit empty arrays with `typed_required=false`. The absence-only projection
applies only to Weather/Market in conversational Council mode when their source is
absent; numerical direct/invite and research retain their existing projections. See
the [V10 grounding follow-up](docs/technical/v10-grounding-followup.md). V10 is
published from source `ec4e29874b2c7408f2bd93d012912e3c0cb8d2f3` with image
`registry.fly.io/farmtact@sha256:874530e73f481b1197e528bb5f124b958a74be64c9934292c14438b4cdd503bf`.
Its full suite passed 611 tests with one skip in 441.23 seconds, and all ten
health/source checks plus captured v1-v9 preservation passed. The Council-only
live trial used nine requests for seven messages and passed 5 of 7 targeted cases:
Weather/Market absence handling passed, Supply was withheld for model-authored
`zero`, and Chair missed a topic word. A fresh mission was correctly withheld with
zero provider calls because 41 public requests were used and seven remained, below
its nine-request reservation; all three numerical strategies were retained. The
cumulative ledger is 85 (44 local and 41 public). No new direct, invite, research
or vision result is claimed. The narrow fix does not establish
general prose or crop-mix entailment; the two V9 Production contradictions remain
unresolved evidence. V8 and V9 stay unchanged.

**Future acceptance requirement — not implemented in V10:** Replace ad hoc prose
guarantees with typed comparison propositions carrying the metric, operands,
relation and scope, verified locally before rendering. Derive crop-allocation
composition changes in code, and represent causal limits when multiple controls
change or the optimizer reruns. Evaluate semantic gates on a calibrated set that
measures both false positives and false negatives, including false claims that cite
valid references. Phrase guards remain bounded safety checks, not proof of meaning.


Final V10 semantic evidence: `reports/v10/ai-assisted-semantic-review.md` audits
seven messages and 26 assertions: two sound, four sound with limits, one
contradiction. Profit incorrectly labels Lean's −SGD 52.87 margin delta as a gain.
This AI-assisted review is not human expert validation. V10 quality remains failed
and its fresh mission-provider path was budget-blocked; publication and numerical
regression do not close this semantic acceptance requirement. The public 56-day
execution passed mass/cash/order-lot reconciliation and historical receipt replay
with zero provider calls (`reports/v10/execution-public.json`).


V10 final capacity evidence is **FAIL** (`reports/v10/shared-capacity-public.json`):
the isolated pair exceeded the 180-second job deadline and browse p95 reached
15.0367 seconds. An earlier mixed-load probe also failed. HTTP health, farm/cookie
isolation and zero inference passed; they do not imply loaded performance passed.
Future acceptance requires queue/execution tracing, CPU/platform-quota measurement,
shared numerical admission control evaluation and bounded cancellation testing.
No host resource increase or threshold relaxation was made. See the V10 technical
follow-up and capacity protocol note for exact scope and cleanup.
