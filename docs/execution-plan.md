# FarmTact implementation status

Kickoff: 2026-09-08. Latest user attachment copied to CODEX_START_PROMPT.md because the separately referenced kickoff file is absent. Initial authoritative tree: README and three specifications only. v1.2 autonomous development changes are preserved. Missing master/brief/runbook artifacts are implementation work, never assumed tested.

## Milestones and ownership

1. G0/G1: master owns contracts, fixture generation, dependency locks, decision log. Real specialist `data_foundation` (A01–A06) owns research registries, ingestion, data tests and dataset builder. Real specialist `deepseek_gateway` (A09/A12) owns gateway, capability route manifest, provider tests, bounded authenticated trial and trial runbook. They work independently.
2. G2: master owns numerical demand/harvest baselines, CP-SAT planner, constraints, mass balance and API persistence. Data and provider outputs integrate only through reviewed interfaces.
3. G3: real specialist `mobile_ui` (A10) owns apps/web and visual mobile implementation. Master owns shared API contracts, jobs, events, automatic simulation acceptance, replay and integration.
4. G4: assign A11 independent review after initial specialists complete; master runs numerical/security/provider/browser tests, inspects 360/390/430/desktop screenshots and fixes findings. Checkpoint verified milestones. Maintain exact results and remaining requirements here and in reports.

At most three specialists plus master run concurrently. No recursive delegation. Specialist file ownership is disjoint; only master changes root locks/shared contracts. Current Codex configuration is gpt-6-astra, high reasoning. Harness explicitly offers gpt-5.6-sol; all three actual specialist spawns requested that model and succeeded. No runtime GPT inference is permitted.

## Acceptance scope

Ten crop knowledge profiles; synthetic caixin/pak choi/kailan/lettuce farm; real source snapshots and coverage/quality/units/freshness; authenticated DeepSeek text/tool/vision checks; numerical Lean/Balanced/Resilient strategies on same scenarios; lead times, nursery/bed/labour/cash/commitments/inventory constraints; visual board and concise evidence cards; persistent versioned mission/council/automatic simulation acceptance/disruption/replay; mobile/browser/security tests. Optional broad satellite/ML roadmap remains separate from this vertical slice, with full spec requirements tracked in completion audit.

## Current status

G0–G3 implemented and demonstrated. Ten crop profiles, twenty evidence records and seven real public connectors produced 200 normalized records with eight source snapshots. Private synthetic contracts, point-in-time features, numerical baselines, CP-SAT alternatives, versioned PostgreSQL jobs and the mobile interface are integrated.

DeepSeek DS-G1/DS-G2 passed with real authenticated discovery/text/tool/vision/stream/six-role calls; the final bounded aggregate used 15/16 requests. The integrated app run `014966c917b7d2d0ce0bc1d94a41e256` passed vision, all six roles, automatic Balanced acceptance, recorded replay and a separately labelled numerical disruption replan. A rejected unsupported claim remains visible.

G4 development verification passed: 191 Python tests, 44 real browser checks, generated-contract drift checks, and isolated clean-checkout reproduction. The clean build fetched 200 public rows and completed numerical import/planning/replay/replan with no inference calls. Final application source digest matches the clean tested tree. Mobile screenshots were inspected, including corrected total-horizon resource labels and stable opaque dialogs. See `reports/completion_audit.md` for commands, source/probe evidence and explicit non-production scope.


## Fly deployment addendum — 2026-09-08

The primary development instance is now https://farmtact.fly.dev/ on the existing `farmtact` app in Singapore. The separate `Dockerfile.fly` is built and deployed, with PostgreSQL on an encrypted persistent volume. Fly health checks and 44 remote browser checks passed; saved farm/session data survived deployment, and logs confirmed graceful PostgreSQL shutdown and cluster reuse. Twelve targeted deployment/security tests passed.

Actual Fly vision and six DeepSeek roles completed, but an unsupported critic threshold caused claim validation to withhold acceptance; that composite report remains INCOMPLETE. Numerical mission acceptance and disruption replanning passed separately. Historical Sprite verification above retains its original scope and counts. See [Fly deployment evidence](../reports/fly_deployment.md) and the deployment runbook for current results and limitations.

## Interactive farming world — active implementation, 2026-09-08

User-approved plan: painted isometric tap-to-explore farm; persistent typed six-character dialogue and bounded council; four repeatable numerical quests and isolated frozen scenario branches; ten recognizable crop illustrations and four growth-stage sets; mobile, accessibility, security, inference and persistence verification; deploy to existing farmtact app after passing checks. Actual operations remain disabled.

Ownership: root (GPT-6-Astra) owns shared API integration, additive schema review, scenario service/quest persistence, numerical and integration tests, release verification and deployment. Three actual GPT-5.6-Sol specialists run without recursive delegation: `world_ui` owns web application/components/styles except Visuals crop renderer and assets; `conversation_backend` owns new conversation service/persistence modules and their tests; `crop_art` owns original crop/advisor SVG assets, Visuals crop renderer and provenance documentation. Root dependency files and main store/app remain root-only. Branches never enter planning_runs or farm_versions, preserving the main worklist. New tables are additive and created through the existing SQLAlchemy schema bootstrap.

Acceptance remains technical: full automated regression, focused scenario/conversation tests, 360/390/430/1280 browser interaction and screenshot inspection, bounded real DeepSeek dialogue/council test, no repeated inference on replay, deployment preserving saved old/new state. Record actual counts and limitations in `reports/interactive_world.md` as work completes.

User acceptance emphasis (2026-09-08): after first game iteration, run thorough end-to-end tests of the whole game, including functionality and UI/UX. Prioritize clearly explained strategic decisions and easy simulation: problem discovery → editable assumption → numerical consequence → same-baseline comparison → grounded explanation/debrief. Repair usability and correctness issues exposed by realistic complete journeys before declaring completion.

## Data Explorer — implemented and deployed, 2026-09-08 UTC

User-authorized scope: replace the Data source cards with a linked farm-data explorer, deterministic generation playground, immutable saved datasets, parameterized EWMA previews and strategy runs, source-aware public context, browser/API verification and Fly rollout preserving recorded state. Actual operations remain disabled.

Ownership: root owns explorer API contracts, immutable snapshot table, scenario/forecast integration, admission limits, integration/security/persistence tests and release. Real specialists requested using the harness-offered gpt-5.6-sol: `explorer_numerics` owns fixture/settings and shared forecast/planner implementation and numerical tests; `explorer_public` owns cached public-context adapter and its tests; `explorer_ui` owns web explorer, accessible SVG components and browser journey. No recursive delegation; root retains shared contracts/dependencies/migrations. Baseline compatibility distinguishes playground reference roots from main-farm roots. No inference on browsing, preview, save or numerical runs.

Backend milestone: exact original fixture JSON/hash parity; 353-test full Python regression passed, followed by focused changed-path checks. Independent review found and verified repairs for saved input/forecast hash integrity and missing-metadata downgrade. Saved snapshots now require `explorer-snapshot-v1`, complete reference/forecast metadata and matching hashes. Three adversarial review cases pass; combined explorer/model verification passed 53 tests. PostgreSQL concurrent save and interrupted numerical-worker reload passed. Public export permission is enforced from the registry. The existing Fly farm/run/branch/quest/conversation release probe has been captured privately for post-deploy preservation checks. Web chart ownership was explicitly reassigned to the numerical specialist for accurate date axes, separate series and accessible selection; main UI specialist retains the remaining web files.

Data Explorer release complete: full backend milestone 353 passing tests; final
changed-path 57 passing tests and 22 deployment/adversarial checks; production
build/contracts pass. Complete browser journey passed 72 checks locally and
72 on Fly, public context passed 25 locally and 25 on Fly, including widths
360/390/430/1280 and no inference calls. Released image
`farmtact:deployment-01M21PK80ABTT3JE5792F676N6` on the existing machine/volume.
Pre-existing farm, run, branch, conversation and quests survived. Sprite web
registration removed and port 8080 closed; PostgreSQL retained. Evidence and
limitations: `reports/data_explorer.md`.

## Mobile navigation and ten-persona public review — complete, 2026-09-09

Root owns gesture implementation, shared public review schema/page/API, integration and preserving Fly deployment. Ten independent reviewer agents ran in batches of at most three specialists concurrently, using the installed gpt-5.6-sol as requested by AGENTS.md. They own separate persona reports/browser scripts/screenshots only. All completed mobile and desktop journeys and read the supplied rubric page 13, retrieved through its GitHub git blob; other briefing instructions were excluded. Reviews are labelled AI personas, never real users or official judging results. All ten reports were curated with 94 evidence references, including 68 mobile/desktop screenshots. Local final verification: 58 navigation checks, 93 public-page checks, 28 panel/security tests, production build and generated contracts passed. Live release verification is recorded in reports/mobile_and_panel.md.

Released `farmtact:deployment-01M22EM68AXASMMMMZB6V715BR` on the existing Fly machine and volume. Live 58 navigation and 93 public-review checks passed; saved farm/run/branch/conversation/quest preservation passed. `/review` publishes all ten reports. Sprite web registration removed, port 8080 closed and PostgreSQL retained; hosting checks passed.

## Independent editions and optional audio — deployed, 2026-09-09

User-approved plan: root edition chooser, preserved v1, fresh v2, independent private Fly deployments/databases, immutable numbered releases, edition navigation, feedback/change/verification links, optional original gentle audio. Root owns gateway, release registry contract, shared-file hooks, migrations, publishing and acceptance. Three bounded gpt-5.6-sol specialists: edition_ui owns frontend routing/storage/menu/changes/reviews; edition_audio owns new audio subsystem/assets/provenance/tests; edition_control owns new private shared-budget/admission service and its tests. No recursive delegation. Baseline commit 705b640 and original image retained; compatibility changes are explicitly distinguished from original gameplay. New inference calls are not needed for implementation verification.

Goal additions: update the build/runtime specifications and push meaningful progress to GitHub at least once every 20 minutes during active work. The initial custom microphone scaffold request was superseded by the user's simpler choice: retain native free-text fields and explain device-keyboard voice typing where available. No browser audio capture, transcription upload, new provider, or custom microphone integration is included in this iteration.


Edition rollout passed: original game tables match restored v1 counts/hashes;
fresh v2 uses a separate private application/database/volume. Public chooser and
`/v1/`, `/v2/` are live. Live checks: 21 API preservation/isolation, 41 edition
browser, 16 audio state/failure, 58 mobile navigation and 94 archived public
review checks. Sprite web/test registrations removed, ports 8080–8082 closed,
PostgreSQL retained. See `reports/editions/implementation.md` and release manifests
for source/image pins, evidence and physical-device testing limitations.


## Seven-agent council and mobile dialogue — deployed as v3/v4, 2026-09-09

User-approved scope: Sumin's Demand, Weather, Market, Production, Supply Chain, Profit and Planner roles; remove the independent critic persona and repurpose Idris as Market, with Lina joining Supply Chain. Keep deterministic evidence and numerical acceptance checks. No community feed is connected: expose a truthful read-only scaffold with provenance, bounds and cutoff checks, never fake reactions or automatic demand changes. Publish as fresh v3, preserving earlier editions.

Root owns canonical roles, provider routing, mission acceptance, release/spec integration and verification. Three bounded gpt-5.6-sol specialists, without recursive delegation: seven_council owns council/dialogue backend and focused tests; seven_ui owns web roster/world/Market panel and browser checks; market_signals owns pure market summary adapter and tests. Root keeps shared contracts/dependencies and deployment. Continue meaningful GitHub progress pushes at least every 20 minutes during active implementation. Verification covers seven ordered roles, planner conclusion, rejected/partial evidence, bounded requests, provenance/no-feed behavior, tenant isolation, mobile/keyboard/replay and unchanged prior editions.


V3 publication passed 412 backend tests, 28 local and 28 live responsive checks,
58 conversation-fixture checks and 19 live API checks. Ten local and one deployed
DeepSeek requests completed; unsupported citations stay flagged. Earlier images
and saved-state hashes are unchanged. Live manual inspection additionally found
that the native voice-typing hint crowded the message field to four pixels at 360px.
Root owns the small flex-wrap correction, explicit usable-width/draft-entry tests,
and its immutable v4 publication. This is not an in-place patch to v3.


V4 completed: 36 candidate CSS checks, 36 live responsive checks and seven live
API/worker/isolation checks. V1–V3 remain immutable. The v4 source is f151082;
release manifests pin its complete commit and image. Native keyboard guidance
now wraps below a usable 44px message row. Original records still match; no extra
inference for the v4 checks. Sprite HTTP services are removed. Full release
scope, counts and remaining no-feed/unsupported-citation limits are in
reports/seven_agents/implementation.md.


## V5 engagement and hosting — planning, 2026-09-09

The v4 task is complete; a new active goal covers Sumin's business proposal, the
page-13 judging rubric, realistic playable decisions, distinctive crops, audible
optional sound and provenance-aware News support. Three bounded real reviewer
agents are collecting business/browser, audio and crop/source evidence. Root
owns integration and the user's conditional Fly consolidation assessment.
See docs/v5-engagement-plan.md and docs/deployment/consolidation-assessment.md.
The hosting figures are measured inventory and official-price estimates; no
consolidation or v5 feature is claimed deployed at this planning milestone.
