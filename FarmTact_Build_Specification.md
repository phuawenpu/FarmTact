# FarmTact

### Current implementation — v6, 9 September 2026

V6 is published at https://farmtact.fly.dev/v6/. This current-state amendment
supersedes earlier hosting and crop-count descriptions; the v1.2 development
policy remains in force. The catalogue contains twelve researched knowledge
profiles, adding garlic chives and sawtooth coriander. Both have original SVG
illustrations and primary-paper evidence; neither adds an unvalidated numerical
recipe. The deterministic caixin/pak choi/kailan/lettuce fixture remains unchanged.

One Singapore Fly Machine (4 shared vCPUs, 4096 MB) runs the gateway and v1–v6
as isolated containers with their exact registered OCI images. One encrypted
3-GB volume contains separate database/cache subtrees. Settings, sessions and
saved game state remain independent; operational abuse/inference limits are
shared. Data fingerprints and public capacity checks passed. Six old Machines
and seven old volumes were deleted; unrelated Fly resources were untouched.
Future editions reuse this host through the immutable publisher. A shared restart
can interrupt all editions; capacity must be reassessed as editions accumulate.
See [release evidence](reports/v6/implementation.md),
[execution status](docs/execution-plan.md) and [publication](docs/deployment/editions.md).

V5 introduced the engagement loop based on Sumin's proposal and the briefing's
page-13 rubric. Its News, audio and gameplay behavior below remains in v6.
Historical release reports retain the dataset, role and model settings actually tested.

### V5 News and decision evidence implementation

The News scout is a deterministic supporting collector outside the seven council
roles. It refreshes four allowlisted RSS endpoints at most once per six hours in
a separate credential-free process. The application only reads the bounded cache.
SFA Newsroom/Circulars, AFSIS and ASEAN Agri-food metadata retain source title,
publication/retrieval dates, exact record hash, geography and explicit event fields.
No article bodies or social profiles are fetched. Reddit and unsupported community
feeds remain visibly unconnected; the CDC calendar is excluded under its reuse terms.

Every new scenario and planning mission freezes News context in its existing
immutable JSON payload; conversations about a scenario use that same context.
Continuation inherits the parent's context. Replays never substitute fresh news.
The synthetic farm's planning date remains distinct from the current decision's
News cutoff. Historical replay uses the farm cutoff and excludes records published
or retrieved later. Future events require explicit structured event dates; an empty
future-events view is valid when none were supplied. News never changes numerical
inputs automatically. Only explicit advisor actions invoke the existing DeepSeek
routes, with source text treated as untrusted evidence and exact citation keys.

The entry mission groups actual booked orders by crop and due date, subtracts
harvest within its declared shelf life and usable inventory, and labels the gap as
provisional because earlier orders have not been allocated. A weekly EWMA estimate
is context, not a same-day delivery quantity. New sowing matures after nursery plus
grow days; sanitation is post-harvest turnaround. Main-farm missions derive from the
current owned import; saved experiments retain their own selected snapshot/root.
Calculation waiting does not advance the biological calendar. Exact scenario
inputs accompany sliders; result comparisons retain signed changes and expose
frozen numerical evidence. Seven role perspectives are deterministic templates,
explicitly distinct from paid advisor interpretations.

The revised original SVG set distinguishes ten crop forms and four crop stage
sequences through leaves, stems and growth habit. V5 sound starts silent, defaults
to 55% music/70% effects after activation, and offers channel toggles, test and retry.
Remastered PCM assets retain sample headroom; failure/withheld/shortfall cues follow
actual result status. Digital signal and browser tests do not establish physical
speaker audibility or human preference. Independent AI reviews and these limits
must remain visible in release evidence.

The verified source was published as immutable v5 at /v5/, while v1-v4 retained
their source/image and recorded state. Test/release evidence belongs in reports/v5.

### Release amendment — 9 September 2026

The public root is an edition chooser. The initial mobile/data-explorer/review
release was preserved as `/v1/`; `/v2/` added edition navigation, feedback/change/verification
notes, and optional original gentle music/effects. Each published application
iteration receives a new immutable numbered edition with an isolated
container, database, worker, cached sources, browser storage and session cookie.
Returning to an edition resumes its own farm; new editions start with fresh
reference fixtures. The v1 compatibility adaptation preserves existing gameplay
and recorded data. Operational abuse counters and inference spending ceilings
remain shared across editions; they contain no shared game settings or progress.

The side menu and mobile menu expose Edition & evolution, edition-specific
changes and reviews. The public review archive retains original tested-build
provenance; targeted retests link feedback to verified changes without rewriting
earlier reviews or requiring a new full panel for each edition.

Audio is muted until deliberately enabled, is locally bundled and originally
composed, and has separate music/effects controls and edition-specific volume
preferences. It pauses in hidden tabs and never substitutes for visible feedback.
Keep textareas compatible with device-keyboard voice typing and add a short hint
where appropriate. No custom recording/transcription service is included now.
Update these specifications as implementation evolves and push progress to GitHub
at least every 20 minutes during active development.

## Dataset-first research and coding specification for a master Codex agent and specialist subagents

**Version:** 1.2 — Autonomous development phase · **Research cut-off:** 8 September 2026 · **Market:** Singapore · **Product:** SME farm production planning web application

**Implementation status:** a deployed synthetic development demonstration with curated evidence, bounded public-data ingestion, numerical planning and DeepSeek advisor integration. Requirements below include future operational capabilities; release reports establish what was actually verified. No model is trained on real farm outcomes, and no achieved farm savings are claimed.

**Mandatory runtime amendment:** Read `FarmTact_DeepSeek_Runtime_Specification.md`. GPT/Codex may build and research; every actual FarmTact LLM call in development, platform test, demo, staging or live use must use the official DeepSeek API. No alternative-provider fallback. The amended environment template supersedes the old GPT runtime defaults.

## 0. Current phase: autonomous development

**No human approval is required to complete this development phase.** This section takes precedence over conflicting approval, sign-off, manual review or operator-confirmation language in these specifications and referenced development briefs. The DeepSeek amendment continues to control runtime-provider policy.

The coding agents may make implementation decisions, construct and validate datasets, research permitted sources, create synthetic recipes and fixtures, change schemas and development migrations, implement models and UI, run bounded authenticated DeepSeek tests with the supplied environment credential, perform independent agent review, integrate changes and advance development gates without asking the user to approve each step. Record decisions and evidence in `docs/decision-log.md`. Reviews and gates are technical checks performed by code and reviewing agents; passing checks advance the work automatically. A failed check triggers repair, exclusion or a recorded blocker, never an invented pass or a request for routine sign-off.

This phase covers local development, isolated test/staging environments and synthetic demonstrations. Set `development_phase=autonomous_development`, `decision_policy=automatic_development` and `execution_mode=test` by default; replay and contract tests use their explicit execution modes. Use `data_mode=synthetic_demo` by default. Lawfully available public data and already-authorized historical data may be used with their original provenance. Account/API access and source licence failures block only dependent capabilities; continue independent work. Missing farm facts become explicit unresolved fields or separately labelled fixture assumptions, never fabricated real observations.

The application backend automatically selects a feasible strategy under a versioned policy after numerical, provenance, scope and evidence checks pass. Default selection uses the Balanced policy, then a validated deterministic baseline if Balanced has no feasible candidate; rank candidates by the configured numerical objective and use stable strategy IDs to break ties. In an explicitly deterministic baseline run, an independently tested validator supplies the audit report in place of a completed LLM council; record `council_status=not_run` or `failed` as applicable, and do not count this as passing council tests. Never relax constraints to force a selection. Unmet buyer conditions exclude a strategy from automatic selection unless an explicitly synthetic scenario supplies that condition. A deterministic simulation runner records simulated work and outcomes so the full planning/replanning loop runs unattended. A council message alone cannot accept or execute a plan.

Automatic acceptance is restricted server-side to isolated development tenants with `synthetic_demo` or `historical_replay` data and `test` or `replay` execution. Historical outcomes remain immutable; simulated counterfactual outcomes are stored separately. Use `ACCEPTED_FOR_SIMULATION`, never a fabricated human approval. Persist policy version, service actor, input/strategy hashes, validation report IDs, modes and timestamp. Changed inputs invalidate acceptance and trigger validation and selection again. No approval button, human-review queue or manual fixture entry may be required for the default development workflow.

Throughout these docs, **approved**, **reviewed** and **validated** for development sources, mappings, recipes, models, configuration and gates mean recorded technical validation by code and an independent reviewing agent where specified. They do not require a human signature. Synthetic recipe/model acceptance is `demo_only`; it cannot establish commercial or agronomic validation. Preserve scientific, licensing, tenant-isolation, credential, budget and feasibility checks.

Real planting, purchases, buyer communications, contract changes, actuator control, private-asset transmission without existing authorization and promotion to live farm operations are outside this phase. Keep those integrations disabled and exercise their simulated equivalents without pausing development. Future operational human-approval flows may be implemented and tested with service actors/fixtures, but are not a development completion gate. Changing to a future operational phase is a separate scope decision; an API key, passing demo or agent decision must not switch it automatically.

**Initial repository baseline:** before implementation, the checkout contained the README and three specification/research Markdown files. At that baseline, referenced registries, master prompt, runtime seed, scripts, tests and reports were intended deliverables rather than verified existing artifacts. Subsequent implementation status and evidence belong in the execution plan and completion audit. Inventory the checkout, create missing development artifacts autonomously and record actual test results. No missing handoff file requires human approval to begin implementation.

---

## 1. Product mandate

Build **FarmTact**, an evidence-grounded farming strategy room. A Singapore farmer supplies the farm's actual orders, production system, growing spaces, crop recipes and current crop batches. A small council of specialist agents uses typed retrieval, forecasting and optimization tools to discuss feasible planting strategies. The farmer sees disagreements, underlying evidence, uncertainty, trade-offs and the exact work implied by each strategy, then sees one versioned plan selected automatically for simulation during development. Future operational use includes farmer approval.

The central question is:

> Given customer demand, crops already growing, available space and resources, crop development time and uncertainty, what should this farm sow or transplant, how much, where and when—and which sales can that production realistically fulfil?

The application must connect **evidence → data → forecasts → feasible alternatives → a decision → actual outcomes**. A persuasive conversation without this chain is not success.

### 1.1 Intended users and decisions

Primary user: an owner-manager or production planner of a Singapore vegetable SME. Secondary users: a grower who records field/batch observations, a commercial manager who confirms demand, and a read-only reviewer. The product supports outdoor, sheltered/greenhouse, hydroponic and indoor multi-tier production as distinct operating systems. A tenant can have multiple zones, but a recipe cannot silently move between incompatible systems.

Near-term decisions concern current crops, harvest timing within safe maturity windows, labour and buyer allocation. Medium-term decisions concern sowing, transplanting, crop mix, staggered batches and optional partner supply. Long-term capital investment is scenario analysis, not automatically available capacity.

Default demo: one fictional Singapore SME growing four crops from the researched twelve-crop portfolio. All twelve must appear in the crop knowledge base; only crops with a technically validated, explicitly synthetic recipe are selectable for simulated commitments in this phase. Real production commitments require future farm-specific validation. A farm can activate more crops by supplying the missing parameters. This prevents a demo from pretending that twelve experimentally validated local models already exist.

### 1.2 Non-goals

Do not build an autonomous chemical-dosing, pesticide-selection, machinery-control or crop-destruction system. Do not promise national food security forecasting, guaranteed profitability or universal optimal growth recipes. Do not treat an LLM as a numerical optimizer, a paper as a farm dataset, or imported food statistics as a customer's order book. Do not build a global remote-sensing platform before the local planning loop works.

### 1.3 Success criteria

A user can inspect data quality; understand the origin and applicability of an agronomic assumption; generate at least three genuinely different feasible strategies; see quantitative trade-offs produced by code; observe automatic acceptance of a strategy for simulation; and replan after a new observation without reversing executed work. Every material quantitative recommendation links to a calculation, model version and input snapshot. Every research claim links to its source and context.

Business outcomes are measured as customer fill rate, marketable output, physical waste, contribution margin, resource use and planning time. Prototype simulation gains must be labelled **simulated**, not described as actual SME impact.

---

## 2. Singapore crop scope and evidence policy

### 2.1 An honest interpretation of “top ten”

No crop-level commercial sales or production ranking sufficient to establish Singapore's ten most popular farm-grown produce items was verified in this review. The initial portfolio uses NParks' ten commonly cultivated leafy vegetables, supplemented by SFA local-produce examples and local farm catalogue checks [C01–C04]. It is a defensible **unranked Singapore cultivation portfolio**, not a national popularity leaderboard. Eggs, seafood and other food categories are outside this planting-planning product.

Display `popularity_rank = null`. When a tenant has sales data, separately compute that tenant's crop ranking by ordered kilograms, delivered kilograms, revenue and order frequency over a stated period. Never replace that with search popularity or the frequency of a crop in papers.

### 2.2 Twelve-crop knowledge portfolio

| Crop ID | Singapore-facing label | Important boundary | Initial evidence |
|---|---|---|---|
| `caixin` | Caixin / chye sim / choy sum | Nursery biomass and flowering shoots are different endpoints | P01, P02 |
| `pak_choi` | Xiao bai cai / pak choi; cultivar-specific nai bai | Cultivar and product specification matter | P03, P04, P05 |
| `kailan` | Kailan / gai lan / Chinese broccoli | Not curly kale | P05, P06, P07 |
| `bayam` | Bayam / Chinese spinach | Amaranthus, not true spinach | P10 |
| `kangkong` | Kangkong / water spinach | Ipomoea; not bayam or true spinach | P12 |
| `lettuce` | Lettuce | Head, baby leaf and loose leaf require separate recipes | P08, P09, P16, P17, P19 |
| `kale` | Kale | Confirm cultivar/taxon in external studies | P15 |
| `mustard_greens` | Chinese mustard / mustard greens | Red mustard is not every mustard SKU | P11 |
| `malabar_spinach` | Ceylon / Malabar spinach | Trellised, potentially repeated harvesting | P14 |
| `sweet_potato_leaves` | Sweet-potato leaves/shoots | Do not use tuber maturity or tuber yield | P13, P18 |
| `garlic_chives` | Garlic chives / Chinese chives | Allium tuberosum, not hollow-leaved common chives; knowledge profile only | P21, P22 |
| `sawtooth_coriander` | Sawtooth coriander / culantro | Eryngium foetidum, not Coriandrum sativum; knowledge profile only | P23, P24 |

Canonical taxon concepts, aliases, ambiguity warnings and evidence links are in `research/crop_catalogue.json`. Local names are convenience labels, not authoritative taxonomic identifiers. Resolve identifiers to an appropriate botanical authority during dataset construction and record the chosen taxonomy/version. Ambiguous invoice descriptions must enter a review queue.

### 2.3 Research findings that change the code

**Growth is stage-specific.** The choy-sum light/time model concerns seedling production [P01]. FarmTact therefore stores nursery, transplant establishment and grow-out separately. A seedling experiment cannot populate mature marketable kilograms per square metre.

**Light is not a single number.** Pak-choi research with SFA participation separates photoperiod from light intensity even at constant daily light integral [P04]. Store PPFD, spectrum, photoperiod and DLI independently. A candidate recipe must carry its energy assumptions. Do not say two recipes are biologically equivalent merely because their DLI is equal.

**Root-zone and ambient temperature differ.** Local tropical lettuce work and other hydroponic experiments demonstrate why root-zone conditions deserve a separate field [P08, P09, P19]. Their differences are a reason to model experimental context, not average every reported temperature into a universal optimum.

**Marketable yield is not total biomass.** The kangkong lighting study includes physiological defects [P12]; kailan work includes nutritional/quality considerations [P06, P07]. Predict marketable fraction or retain it as a separately justified assumption. Bigger plants need not satisfy buyer requirements.

**Repeated harvest is a stateful process.** Basella and sweet-potato leaf systems cannot be represented as a field becoming empty after each cut [P13, P14, P18]. Preserve occupied capacity, cutting dates and regrowth intervals. Leaf, stem, tuber, fresh weight and dry matter remain distinct outputs.

**A good retrospective ML fit may answer the wrong question.** P16 measures predictors including dry weight at harvest. Those features cannot be available to a model making a planting decision weeks earlier. Feature availability must be validated before accepting model performance.

### 2.4 Evidence hierarchy

Use separate dimensions, not a single magical credibility score:

- Publication class: original peer-reviewed experiment, review, thesis, extension guide, official dataset, farm observation or synthetic example.
- Access/review status: metadata only, abstract reviewed, methods reviewed, full relevant results extracted, independent verification complete.
- Applicability: taxon, cultivar, stage, harvested part, production system, geography/climate, scale and commercial endpoint.
- Study design: experimental unit, replication, controls, randomization, uncertainty, possible confounding and repeated use of the same underlying experiment.

An experiment in Singapore is not automatically a commercial validation. A non-Singapore study may be useful when conditions match, but transfer uncertainty must remain explicit. A review and the original study it cites must not count as two independent trials.

The 20 publication records in `research/evidence_register.json` are a starting research set, not an exhaustive systematic review. Some full texts were inaccessible. Records disclose that; no production coefficient is approved merely because its title is listed.

---

## 3. Phase one: construct the comprehensive dataset

**The first delivery gate is a versioned, reproducible dataset—not a chatbot screen.** Build a connected data product with four distinct components:

1. A research/evidence knowledge base describing crops and conditional agronomic findings.
2. Public observations and forecasts describing weather and market context.
3. Private tenant observations describing demand, operations and outcomes.
4. Derived, availability-aware feature and scenario snapshots used by numerical tools.

These components can join through identifiers, time and geography. They must never be collapsed into one table with invented labels.

### 3.1 Required phase-one outputs

Produce a crop catalogue for all twelve crops; source registry with access/licence states; article evidence register; approved and unresolved crop/HS mappings; machine-readable data contracts; raw-snapshot manifest; normalized tables; quality report; lineage graph; reproducible feature build; and a deterministic synthetic farm used only for integration testing.

For each source, report `discovered`, `metadata_verified`, `licence_reviewed`, `downloaded`, `parsed`, `validated`, `quarantined` or `blocked`. “Publicly available” must not be displayed as “integrated.” Missing credentials, unavailable files and unknown licences are explicit blockers, not reasons to fabricate substitute data.

### 3.2 Storage layers

**Raw:** immutable original responses/files, query parameters, response headers excluding secrets, checksum, byte count, retrieval timestamp, licence snapshot and source version. Do not commit large raw files or copyrighted full text to the repository.

**Normalized:** canonical IDs, explicit units, UTC timestamps plus original time representation, resolved categorical values and quality flags. Keep raw values alongside transformed values or link them to the immutable snapshot.

**Features:** point-in-time joins and derived variables with a cutoff, dependency IDs and transformations. Features must be rebuildable from versioned inputs.

**Decision artifacts:** frozen demand/yield predictions, scenario draws, candidate actions, solver status, council claims, development acceptance state and outcome accounting. A later data correction creates a new version; it does not overwrite the evidence used for an earlier decision.

### 3.3 Core tables and grains

| Table | Grain and essential columns |
|---|---|
| `source` | Provider/dataset; URL, licence state, access method, data kind, terms checked date |
| `source_snapshot` | One fetched response/file; checksum, query, retrieval time, coverage, version |
| `crop` | Canonical crop concept; aliases, taxon, family, harvested part |
| `cultivar` | Crop-specific cultivar or confirmed unknown; seed source and identifier |
| `product_sku` | Saleable product; cultivar/grade/pack size/unit/customer constraints |
| `crop_hs_mapping` | Crop/SKU ↔ commodity code; nomenclature version, mapping scope/confidence/reviewer |
| `evidence_document` | DOI/publication/version; access, licence, correction and review status |
| `evidence_claim` | One contextual result; source locator, endpoint, treatment, comparator, scope |
| `crop_parameter` | Parameter + crop/cultivar/stage/system/endpoint; value or range, unit, provenance, technical validation status and permitted use scope |
| `tenant` / `farm` | Owner and production location; timezone, currency, permissions |
| `zone` | Outdoor/protected/indoor environment; coordinate/polygon, nutrient/light/HVAC grouping |
| `growing_space` | Bed/rack/bench layer; effective canopy m², sites, physical footprint, allowed crops |
| `resource_calendar` | Resource × interval; nursery slots, labour, water, energy, cooling and packing limits |
| `recipe_version` | Approved crop/system recipe; nursery, grow-out, sanitation, density, yield semantics |
| `customer` | Pseudonymous buyer; delivery windows, grade and substitution permissions |
| `order_event` | Immutable order/change/cancellation event; booked time, due time, kg, price, status |
| `delivery_line` | Delivered amount for an order; grade, lot, date, rejection and return |
| `planting_batch` | Sowing/transplant event; space, crop, recipe, quantity, area, status |
| `crop_observation` | Batch × time; stage, counts, size, defects, method and observer |
| `harvest_event` | Batch × cut/date; gross kg, marketable kg, reject kg and reason |
| `inventory_lot` | Harvest/received lot; grade, available kg, age, temperature history, expiry assumptions |
| `inventory_movement` | Sale, carry, transfer, processing, donation, disposal; quantity and reason |
| `weather_observation` | Station/grid/variable/time; value, unit, interval and quality |
| `weather_forecast` | Model/run/location/valid time/variable/member; issued time and horizon |
| `trade_observation` | Reporter/partner/code/period/measure; value, unit, flags, release/version |
| `market_indicator` | Specific derived indicator with all contributing observation IDs |
| `remote_sensing_asset` | Scene/parcel/band/product; acquired time, processing, cloud validity and pixel support |
| `feature_snapshot` | Cutoff + entity/horizon; feature dependencies, schema and build hash |
| `model_run` | Training and prediction versions, split definitions, metrics, artefact hash |
| `planning_run` | Farm/cutoff/horizon/input hashes/scenario seed/state and budget |
| `strategy` | Candidate plan + objective, constraints, uncertainty, feasibility and model versions |
| `agent_claim` | Runtime assertion/proposal/challenge; referenced evidence/tools, status and concise rationale |
| `decision_event` | Immutable acceptance/rejection/invalidation; service actor, policy version, strategy/input hashes, validation report IDs, phase, data/execution modes and timestamp; future human approval uses a distinct event type |
| `audit_event` | Security and operational changes; actor, reason, target and trace ID |

All private tables require tenant scope. Composite keys and foreign keys must prevent a batch, lot or order from accidentally linking across tenants. Use decimals for money; use explicitly bounded integers or validated decimals for solver quantities. Financial models use SGD by default and record any exchange-rate source and date when another currency is present.

### 3.4 Required temporal fields

`observed_at` is when the phenomenon occurred. `available_at` is when the value became available to a decision-maker. `retrieved_at` is when FarmTact fetched it. Forecasts also need `issued_at`, `valid_from`, `valid_to` and `lead_hours`. Publications need publication date, version and any later correction date. All timestamps are timezone-aware.

An as-of query for cutoff C may only use dependencies with `available_at <= C`. A revised import statistic published later cannot be inserted into an earlier backtest. An observation of tomorrow's temperature cannot replace the weather forecast available today. Historical reanalysis and historically archived forecasts are different data products.

When exact historical release times cannot be established, mark availability uncertain and exclude the source from causal/point-in-time performance claims, or use a declared conservative lag and test sensitivity. Do not quietly assign the observation date as publication date.

### 3.5 Parameters and units

Store time to germination, nursery duration, transplant establishment, grow-out duration, harvest tolerance and sanitation separately. A paper's “days after transplanting” is not “days after sowing.” For repeated cuts, store establishment duration, minimum recovery time and cut-specific yield.

Store density in plants per effective growing m²; area as effective canopy m²; yield as fresh marketable kg per cycle per effective m² or kg per surviving plant, with exactly one defined basis. Retain whole-building footprint and rack layers separately. Do not multiply effective canopy area by the number of layers twice.

Store gross yield, survival, packout and handling loss distinctly. When a historical yield already means marketable kg per planted m², survival and packout are already embodied in that measure; do not reduce it again. Preserve the endpoint definition on every model output.

For light, store original units. Lux cannot be converted to PPFD without an appropriate spectrum-dependent calibration. DLI can be derived from time-integrated PPFD with unit validation. For weather, sum valid interval rainfall amounts, not cumulative counters repeatedly. For trade, never convert currency into mass.

### 3.6 Targets and missing private data

Demand targets come from customer orders and bookings, not just shipments. Keep ordered, fulfilled and cancelled quantities separate. Shipments during a shortage may underestimate demand. Missing lost-sales data remains uncertainty rather than a newly invented target.

Production targets are actual marketable harvest and actual maturity dates by batch/recipe/system. Weather, imagery and papers provide explanatory features or priors; they do not create the missing outcome labels.

For the hackathon, implement the referenced synthetic generator as a deterministic starting fixture if it is absent. Every synthetic row carries its origin. Synthetic relationships and coefficients must never be inserted into the scientific evidence register. A model trained only on synthetic data must be labelled `demo_only` and blocked from `production_validated` status.

---

## 4. Public-data ingestion specifications

The complete source list, access limitations and integration priorities are in `research/dataset_registry.json`. This review verified public pages and documentation, not successful authenticated bulk downloads. Connector implementation must perform its own schema and access smoke tests.

### 4.1 Singapore weather: first live connector

Implement NEA rainfall, air temperature, relative humidity, 24-hour and four-day forecasts [D01–D05]. Retrieve official API specifications from the dataset pages; save a versioned contract. Rainfall's documented endpoint is `https://api-open.data.gov.sg/v2/real-time/api/rainfall`. Discover and verify sibling endpoints instead of guessing them.

Normalize station IDs and coordinates. Choose a weather mapping per farm/zone, preserving station distance and coastal/elevation or coverage caveats where relevant. Missing station data triggers a visible fallback with changed provenance. Do not treat all stations as independent farm observations.

Aggregate to the intended model interval only after respecting observation intervals. Build recent rain totals, temperature summaries, humidity exposure and data completeness. Apply direct weather exposure only to the appropriate growing system. A sheltered or indoor farm may have indirect light/cooling/power exposure but not the same rainfall-to-yield relationship as an exposed bed.

As-issued forecasts support near-term operations. Beyond their valid horizon, use historical seasonal distributions or explicit long-horizon scenarios—not fabricated day-specific weather. A short forecast must not be stretched over the full crop cycle.

### 4.2 Singapore trade and market context

Prioritize **T010002 for trade volume**, and T010001 for trade value [D06, D07, T08]. This distinction matters. Verify commodity nomenclature, partner definition, period, quantity unit, missing values and flags. Read exact code descriptions before mapping crops; maintain a versioned many-to-many mapping and an explicit `unresolved` state. It is acceptable for a code to cover several vegetables; it is not acceptable to invent a separate chye-sim series.

Fetch an initial multi-year monthly history for only the relevant categories and partners; use provider limits and pagination. Store the unfiltered response snapshot and transformation manifest. Create supplier shares only from comparable units and a complete denominator. Compute value/volume unit values only where categories, partner, period and units match; label them customs unit values, not farmer selling prices.

CPI and annual local production are secondary context [D08–D10]. Annual broad vegetable output is not a weekly crop-level target. Market-price pressure may arise from reduced supply rather than greater consumer demand. Regressors must earn inclusion through out-of-time testing.

### 4.3 Global weather and production sources

NASA POWER is a convenient historical climate baseline, not a forecast [D11]. Its time-standard option must be explicit; local solar time is not Singapore civil time. Read variable units and missing-value sentinels. Grid-cell weather is not a weather sensor on a tiny plot.

ERA5-Land is a historical reanalysis source [D12]. Use the selected product's documented accumulation convention. Store product version and release timing. NASA IMERG adds rainfall observations; choose Early, Late or Final deliberately and preserve their latency differences [D14]. NOAA GFS supplies forecast runs for source-region risk [D13]. Forecasts are stored by model run rather than overwritten with the newest run.

Open-Meteo can simplify a non-commercial prototype, but its free hosted API excludes commercial use; data licensing, service terms and server-software licensing are separate [D19]. Keep it behind an adapter so a commercial deployment can use an appropriate plan or another permitted provider. Do not advertise an unlimited zero-cost commercial weather service.

FAOSTAT provides structural country/item context [D17, T07]. Discover official bulk/API metadata and record country/item/unit mappings. Annual data and broad vegetable categories cannot be converted into farm-specific weekly sales. UN Comtrade is an optional international comparison source with account and reuse restrictions to verify [D18]. Cross-reporting of the same flow is corroboration, not an additional independent signal.

### 4.4 Satellite branch: optional and explicitly gated

Use Copernicus Data Space's current STAC discovery interface `https://stac.dataspace.copernicus.eu/v1/` [T06]. Inspect collections and asset metadata rather than coding to a deprecated endpoint. Limit requested bounding boxes, dates and assets. Keep free data access distinct from processing quotas, account requirements and cloud-storage cost.

For Sentinel-2, process level-appropriate imagery, masks, scaling and spatial support. Output clear-pixel fraction, number of valid pixels, scene date and the method used for compositing/anomaly comparison. Only compare equivalent phenological periods where enough information exists. Recent harvest, changed crop mix, water, shade and cloud contamination can all confound a vegetation index.

For Sentinel-1, preserve orbit, polarization, geometry and processing choices. Radar is useful in cloudy conditions but is not a direct crop-yield sensor. Do not mix uncalibrated scenes or pretend a generic change map estimates kailan kilograms.

Satellite data is most defensible as an optional regional early-warning layer for verified supplier areas or open-field parcels. It cannot inspect crops through greenhouse or indoor-farm roofs. A country-level trade record does not identify a source district; an assumed region must be labelled a scenario proxy and cannot produce a purportedly verified supply-loss forecast.

### 4.5 Scholarly-data pipeline

Use Crossref for DOI metadata, deduplication, correction/licence discovery and citation expansion [D22]. Resolve full text through lawful publisher/repository paths. Never bypass paywalls or scrape indefinitely. Read article HTML/XML before using PDF extraction; parse embedded PDF text before considering expensive visual/OCR methods. Any numeric result taken from a figure/table requires explicit source location and verification.

Extract only a bounded schema: taxon, cultivar, stage, system, location, environmental treatments, comparator, experimental unit, replication, endpoint, unit, effect direction, reported uncertainty, access scope and limitations. Store an exact short locator or excerpt where legally appropriate, not entire papers in prompts. The independent reviewer must reject a number whose context is missing.

P04's Zenodo supplement is described as LC-MS data [D21]; treat its utility accordingly. WUR's lettuce climate/image dataset [D20] is a candidate experimental benchmark, but its file licence and schema require confirmation before download and reuse. External experiments may support feature development without proving local model validity.

### 4.6 Connector common contract

Each connector implements `discover()`, `fetch(query, checkpoint)`, `normalize(snapshot)`, `validate(batch)` and `describe_licence()`. Fetching must have connect/read timeouts, bounded retries with jitter, `Retry-After` handling, byte limits, pagination safeguards and provider-specific request budgets. Idempotency uses source, parameters, snapshot version and content hash.

No runtime LLM writes arbitrary SQL, executes downloaded Python, chooses unrestricted URLs or edits connector code. An LLM can propose a schema mapping or ask a typed connector to refresh an approved source. Schema changes require automated validation and recorded migration review by a coding agent; apply passing development migrations without human confirmation.

### 4.7 Dataset quality gate

Before modeling, produce coverage by crop, source, date and farm system; completeness; invalid units; duplicates; unresolved aliases/codes; licence blockers; freshness; missing outcomes; and evidence applicability. Assign no fabricated row-count target. Report actual rows fetched versus requested, plus exclusions.

The gate passes when all twelve crop records and their caveats exist; the activated development recipes have technically validated parameters with explicit provenance and `demo_only` scope where synthetic; at least one real public connector has successfully produced validated records; the synthetic/private-data boundary is enforceable; and every feature can be traced back to a source snapshot. A source whose endpoint is blocked may remain in the backlog but cannot be displayed as live.

---

## 5. ML and analytical strategy design

There are **38 candidate strategies** in `research/strategy_catalogue.json`. They form a research/engineering backlog, not a demand to train 38 models during a hackathon. Each specifies inputs, outputs, evaluation and a guardrail. Four numerical capabilities constitute the first complete vertical slice.

### 5.1 Demand forecast

Start with a contract-aware seasonal naive/EWMA baseline by product/week, plus an explicit method for bookings versus residual unbooked demand. Include cancellation status and distinguish actual orders from inferred lost demand. Backtest on rolling time cutoffs. At a given cutoff, forecast the same horizons relevant to the growing cycles.

A quantile gradient-boosting challenger may use demand lags, known promotions, calendar variables and availability-correct public covariates. Train only where there are enough independent periods and events to evaluate. Choose the baseline whenever the challenger fails to beat it. Explain missing data rather than manufacturing an 80% confidence interval from an LLM's verbal confidence.

For cold starts, use confirmed orders, buyer-supplied forecasts and cautious hierarchical pooling. A public-data-only mode can show market context and ask for bookings, but it must not claim a personalized demand forecast.

### 5.2 Harvest timing and marketable-yield forecast

Start with recipe-specific observed duration and marketable-yield distributions. Model nursery and grow-out time independently where data allows. Current crop observations update the remaining time and yield uncertainty; distinguish initial forecast from revised forecast.

Use farm/system/cultivar partial pooling when observations are sparse. Optional weather/light features must be available before the prediction cutoff and appropriate to the environment. Hold out entire crop batches/cycles, not randomly selected daily observations from the same batch. Record the number of independent cycles, not merely the number of rows.

Produce distributions or scenario samples for harvest timing, gross mass, marketable mass and relevant quality, with uncertainty semantics stated. Do not infer exact physiological outcomes from a paper's qualitative conclusion.

### 5.3 Risk and uncertainty engine

Generate joint scenarios for demand, crop timing, marketable yield and selected costs. Preserve plausible correlations: nearby exposed beds may share a rain shock, crops in one indoor room may share an equipment or climate shock, and multiple suppliers may share regional hazards. Never assume independent crop failures solely because they are different database rows.

Use historical block/residual sampling as a transparent first method. Quantile or conformal-style calibration is an optional extension evaluated for temporal coverage. Under distribution shift, empirically measured coverage matters more than an advertised guarantee.

Global supply indicators are evidence about possible exposure. A chain from regional rainfall to lower crop output to fewer Singapore imports to this farm's higher demand requires separate support at each step. Where a link is unvalidated, produce a conditional scenario and exclude the unsupported uplift from automatic selection. An explicitly labelled synthetic buyer condition may exercise that branch in development; no buyer contact or confirmation is required to finish this phase. Do not automatically increase acreage on an unsupported assumption.

### 5.4 Optimization

The numerical planner is a tool, not an LLM monologue. Start with an auditable backward-scheduling baseline; then implement a constrained solver using CP-SAT or a documented MILP formulation. CP-SAT operates on integers, so use a deliberate scaling convention such as whole plant sites, area units and cents, test rounding, and guard against integer overflow [T05]. Do not silently mix float objectives with unscaled integer quantities.

Record solver status, time limit, feasible objective, bound/gap where available and the exact input version. `FEASIBLE` is not `OPTIMAL`. A timeout without a feasible solution is not a successful plan. Fall back to an independently validated baseline or explain infeasibility.

### 5.5 Model promotion and evaluation

Track demand MAE/WAPE where denominators are nonzero, pinball loss for quantiles, harvest-date error, marketable-yield error, interval coverage and sharpness. WAPE/percentage metrics require explicit handling of zero-demand periods. Keep metrics by crop, horizon and growing system.

Compare decision outcomes against a fixed baseline on identical held-out scenarios. Model prediction accuracy and decision value are separate. A slightly more accurate forecast that causes excess planting may produce worse margin or waste.

Promotion requires versioned training data, temporal/grouped splits, reproducible seeds, baseline comparisons, leakage checks and recorded independent agent review. Passing checks automatically promote models within development scope; synthetic-only models remain `demo_only`. Actuals can trigger a proposed model update; one unexpected harvest must not instantly “teach” a permanent agronomic law. Preserve rollback capability.

---

## 6. Planning mathematics and strategy families

### 6.1 Decision variables

Let candidate action j represent a crop/cultivar/recipe, growing space and sow/transplant date. Let `x_j` be the number of selected planting units or allocated sites. Candidate j has a stage-specific resource occupancy profile, expected harvest distribution and cost profile. Let scenarios s carry probabilities or declared simulation weights.

Demand `D[c,t,s]` is saleable product demand. Existing pipeline `H_existing[c,t,s]` is separate from new production. `y[j,t,s]` gives marketable yield per planting unit available in period t for candidate j. New harvest is the sum of `x_j * y[j,t,s]`. Coefficients come from approved models or labelled scenario assumptions.

For a simple area calculation:

`required_area_m2 = uncovered_marketable_kg / expected_marketable_kg_per_m2_per_cycle`

This is only a diagnostic. It does not establish that an eligible bed, nursery space, labour or harvest window exists. Round allocations to physically executable units and rerun constraints.

### 6.2 Hard constraints

Enforce crop/system compatibility, effective growing area or site capacity, nursery capacity, stage transitions, seed/seedling availability, bed occupancy across the entire crop cycle, sanitation time, configured rotation rules, harvest maturity windows, and crop-specific allowed harvest modes.

Also enforce worker hours for planting/harvest/packing, water/energy/HVAC constraints where supplied, cash budget, buyer grade and packaging, delivery windows, safe lot eligibility and contractual commitments. Indoor shared light/nutrient/climate zones may constrain which recipes can operate together. A different recipe in the same room must not imply an independently controllable environment.

Freeze already executed actions. Preserve the current occupancy of partially grown crops. Later supply cannot satisfy an earlier order. Do not permit an agent to create land, shorten a crop cycle without evidence, borrow an unapproved supplier, or count reserve seedlings as finished production without grow-out capacity.

### 6.3 Perishability and mass balance

Maintain lot-age inventory when shelf-life/quality constraints matter. The simplified identity per product/period is:

`opening eligible stock + marketable harvest + eligible purchases = delivered + closing stock + recoverable diverted stock + disposed stock`

Gross harvest also separates marketable output from field/packhouse rejects. If only aggregate totals are available, expose uncertainty in where loss occurred rather than double-counting it as both rejection and unsold waste. Unsold production can remain inventory or be diverted lawfully; it is not automatically waste. No processing/donation option exists unless an approved feasible channel is configured.

### 6.4 Objective

Maximize expected contribution margin minus explicitly configured shortage/waste/risk costs, subject to service and resource constraints. Revenue and penalties must be traceable to user inputs or approved assumptions. Margin includes seed/seedling, variable labour, energy/water, packing, purchasing and disposal costs as appropriate. Keep sunk costs distinct when comparing marginal decisions.

A later version can use downside-risk measures such as CVaR. Do not obscure business preferences in an unexplained 84/100 “AI score.” The user chooses service targets and risk appetite; the optimizer reports the consequence.

### 6.5 Strategy catalogue shown to the farmer

**Lean:** minimize surplus and capital commitment while meeting the chosen lower service target.

**Balanced:** target the user's standard service level with staggered sowing and moderate risk protection.

**Resilient:** prioritize service/downside protection using feasible buffer capacity, recipe/space diversification or verified partner supply. More planting is not automatically more resilience.

Optional strategies are energy-conscious indoor scheduling, repeated-harvest smoothing, buyer-confirmed import-disruption opportunity, harvest allocation and surplus recovery. All use the same underlying constraints and comparable scenario draws. If the farm is capacity-limited, the UI may show only two feasible options and one infeasible request; it must not fabricate a third solution for aesthetic symmetry.

### 6.6 Demonstration case without biological shortcuts

A future harvest week has an uncovered requirement and enough time remains for a new crop. The council compares staggered sowing against one large batch. After automatic acceptance for simulation, a later event reduces the forecast of crops already growing.

If the affected orders are due before any new sowing can mature, the planner must switch to feasible actions: verify harvestable adjacent lots, evaluate a substitution or partner quote already present in the fixture, or show an unavoidable shortfall. Buyer negotiation and quote acquisition are simulated events in this phase; no external communication or purchase is required. It must **not** claim that planting additional seedlings today resolves a shortage next week.

All quantities, prices and shocks used in this demonstration come from a fixture labelled synthetic. Never present fixture percentages as findings from NEA, satellite data or a crop paper.

---

## 7. Runtime farming council: substantive discussion, not theatre

The agents building FarmTact in Codex are different from the agents running inside FarmTact. The coding team produces software; the runtime council operates only through bounded application tools. No runtime council member gets a developer shell, a browser with arbitrary write access, or permission to alter model code.

All actual role/helper inference—including runtime research and LLM-based evaluation—uses the DeepSeek routes in the runtime amendment. Image-dependent tasks delegate to its vision model, never a text-only model. Codex developer subagents and their GPT configuration are not part of this runtime council.

### 7.1 Runtime roles

| Runtime role | Responsibility | Authorized tools | Must challenge |
|---|---|---|---|
| Demand — Ravi | Crop quantities and delivery dates; bookings versus baseline demand | Orders and numerical demand model | Bookings double-counting; unconfirmed sales counted as orders |
| Weather — Hana | Conditions, freshness and environmental uncertainty | Cached weather observations and quality metadata | Unsupported yield changes and forecast horizons |
| Market — Idris | Price assumptions, commercial context and sourced produce reactions | Prices; read-only community evidence summary | Popularity mistaken for measured demand; missing or biased sources |
| Production — Mei | Recipes, biological lead times and growing space | Approved recipes, batches and harvest forecast | Impossible maturity, invented yield and occupied beds |
| Supply Chain — Lina | Inventory, expiry, inputs and delivery timing | Lots, resource calendars and numerical allocations | Missing logistics represented as solved constraints |
| Profit — Ben | Costs, cash, labour and margins | Computed resource and strategy metrics | Surplus counted as sales; unpriced risks |
| Planner — Asha | Reconcile six findings and explain eligible strategies | Frozen numerical results and validated findings | Unsupported consensus and unresolved dependencies |

These seven responsibilities follow Sumin Lee's interactive research brief and the user's 2026-09-09 direction. They are roles in an auditable workflow, not a claim that more model calls improve accuracy. The independent critic persona is removed in v3. Deterministic numerical, provenance, scope and evidence checks remain independent of every persona. Old editions and recorded critic messages keep their original semantics.

The current bounded council runs six specialist findings followed by the Planner's conclusion, using the same frozen numerical snapshot. Up to two shared repair requests fit inside nine reserved requests (ten with optional vision), with the existing 16,384-token and 300-second ceilings. Dialogue councils also have seven turns. A new `planner_conclusion` closes those conversations; historical `critic_conclusion` remains a historical record.

### 7.2 State machine

`CREATED → VALIDATING_INPUTS → SNAPSHOTTING → ANALYSING → PROPOSING → CHALLENGING → OPTIMIZING → SIMULATING → EVIDENCE_VALIDATION → VALIDATING_ACCEPTANCE → ACCEPTED_FOR_SIMULATION`

Terminal/exception states: `MISSING_INPUT`, `NO_FEASIBLE_PLAN`, `SOURCE_UNAVAILABLE`, `BUDGET_EXCEEDED`, `FAILED`, `CANCELLED`, `REVIEW_WITHHELD`. The backend applies the automatic-development policy after all required checks pass; failure produces the relevant exception state. Simulated execution records come from the deterministic runner with fixture/run provenance. Historical actuals remain separate. The future operational branch `READY_FOR_APPROVAL → APPROVED` is disabled for this phase and cannot block its workflow.

The backend validates inputs and freezes the cutoff, numerical strategy results and Market context. Six specialists inspect these results, followed by the Planner. The backend validates every finding and runs the versioned acceptance policy; an advisor cannot accept a plan. Partial, rejected or unresolved findings withhold automatic acceptance while feasible numerical alternatives stay inspectable (`REVIEW_WITHHELD`). A council with no returned findings may expose the explicitly labelled deterministic baseline, never a claimed council success.

Default policy: at most two challenge rounds, bounded tool calls, deadline and per-run spending budget, configured in versioned development settings by the coding agents without human confirmation. Limits are engineering defaults, not a claim about optimal agent behaviour. On timeout, preserve completed evidence and expose the deterministic baseline or a partial-data state. Never manufacture agent messages to conceal a failed LLM call. Replay fixtures must say `REPLAY`.

### 7.3 Claim types and discussion rules

Each message is one of `observation`, `hypothesis`, `proposal`, `challenge`, `rebuttal`, `decision` or `abstention`. It includes its author role, run/snapshot IDs, evidence/tool references, affected crop/time window and concise rationale. Quantitative statements cite a field in a tool result or a verified evidence claim; a model-generated number with no supporting reference is rejected.

An agent can say, “The demand increase is not buyer-confirmed, so evaluate it as a scenario.” It cannot say, “Satellite data proves we should plant 12% more,” unless a validated quantitative chain and optimizer result actually support that statement. Agreement is not evidence. Disagreement must be resolved by data, constraints or a clearly stated user preference, not a majority vote between LLMs.

Store concise explanations suitable for audit, not private model chain-of-thought. The transcript shows source-backed conclusions and tool events, including missing data and rejected claims.

### 7.4 Example discussion

Demand Analyst: “Bookings cover the baseline requirement. The additional opportunity is conditional on buyer confirmation.”

Production: “The proposed new sowing cannot mature in time for the earliest orders. The later delivery window is eligible.”

Profit: “The nursery is constrained on the first date; the second staggered date is feasible.”

Chair: “Evaluate the confirmed-demand plan and a separate buyer-confirmed uplift scenario using the same resource calendar.”

Backend evidence check: “Both outputs pass lead-time and occupancy checks. The uplift plan is excluded from automatic selection while the buyer condition is unresolved; the confirmed-demand plan can proceed. A separate synthetic scenario can supply a labelled buyer confirmation.”

The implementation displays actual figures only when returned by tools. This example is a behavioural specification, not a claim about a particular farm.

---

## 8. Typed tool and API contracts

### 8.1 Runtime tools

Implement a typed tool registry with a JSON schema, permission, timeout, retry policy, cost classification and audit policy for each tool. Recommended initial tools:

- `get_farm_snapshot(farm_id, cutoff)` and `validate_planning_inputs(snapshot_id)`.
- `search_crop_evidence(crop_id, cultivar_id, system, stage, endpoint)`.
- `forecast_demand(snapshot_id, crop_ids, horizon)` and `forecast_harvest(snapshot_id, horizon)`.
- `get_weather_context(snapshot_id, zone_ids, horizon)` and `get_import_context(snapshot_id, approved_mapping_ids)`.
- `list_feasible_candidates(snapshot_id, horizon, policy_id)`.
- `optimize_plan(snapshot_id, scenario_set_id, policy_id)`.
- `simulate_strategy(strategy_id, scenario_set_id)` and `validate_strategy(strategy_id)`.
- `request_missing_input(field, reason, affected_decision)`.

All data retrieval is tenant-scoped and read-only. The runtime tool set does not include `execute_sql`, `run_shell`, unrestricted `fetch_url`, `change_recipe`, `purchase_crop` or `control_irrigation`. Automatic development acceptance and simulated execution are authenticated backend operations with dedicated service permissions, not ordinary LLM tools. They follow Section 0 and require no human action. Future operational approval routes remain disabled in this phase.

### 8.2 Evidence claim shape

```json
{
  "claim_id": "claim-example",
  "claim_type": "hypothesis",
  "crop_id": "pak_choi",
  "statement": "This study is relevant to lighting features but does not establish this farm's yield.",
  "evidence_ids": ["P04"],
  "tool_result_refs": [],
  "applicability": {
    "system_match": "partial",
    "cultivar_match": "unknown",
    "stage_match": "verified",
    "commercial_validation": "absent"
  },
  "numeric_values": [],
  "review_policy": "independent_agent_and_schema_validation",
  "review_status": "pending",
  "requires_human_review": false,
  "development_scope": "simulation_only"
}
```

This is a development contract example. Pending claims receive automated and independent agent review; unsupported claims are rejected or excluded without waiting for a human. In future production, the statement, evidence access rights and applicability fields are generated and validated against retrieved records; the example is not a pre-approved claim for every farm.

### 8.3 Planning-run input

Require `farm_id`, `cutoff`, `horizon_start`, `horizon_end`, `recipe_version_ids`, `demand_policy`, `resource_version`, `scenario_seed` and `run_mode`. `run_mode` is one of `synthetic_demo`, `historical_replay` or `live_advisory`. Use `data_mode` as the canonical field; `run_mode` is its legacy alias and conflicting values must be rejected. Also require server-derived `development_phase`, `decision_policy` and `execution_mode`. Enforce Section 0 eligibility for automatic acceptance. Do not infer mode from the presence of an API key. Display modes on every strategy and exported plan.

Optional inputs include service target, risk penalty, cash cap, opportunity conditions with provenance, locked actions and enabled data sources. Supply versioned fixture defaults for the unattended demo; do not require manual entry. Validate horizon ordering and ensure the cutoff is not in the future for a live run. Any input change creates a new version and invalidates prior acceptance; the backend reruns validation and selection automatically.

### 8.4 Strategy output

Require allocations with crop/cultivar/recipe, space, sow date, transplant date where relevant, expected harvest window, site count or area, quantity distribution, resource use and dependencies. Also require status, model/calc versions, gross versus marketable semantics, cost assumptions, fill-rate definition, physical waste accounting, scenario count/seed and unresolved assumptions.

Report hard violations as structured records: `constraint_code`, `entity_id`, `period`, `required`, `available`, `unit`, `severity` and `repair_options`. An impossible request returns `NO_FEASIBLE_PLAN`, not a JSON object full of zeros masquerading as a valid strategy.

### 8.5 HTTP interface

| Route | Method | Contract |
|---|---|---|
| `/api/v1/health` | GET | Service state without secrets |
| `/api/v1/sources` | GET | Metadata, freshness, licence and integration state |
| `/api/v1/imports` | POST | Validated upload/import request; returns job ID |
| `/api/v1/imports/{id}` | GET | Status, row counts, quarantine reasons |
| `/api/v1/crops` | GET | Twelve-crop catalogue and activated recipe coverage |
| `/api/v1/crops/{id}/evidence` | GET | Filtered evidence cards and applicability |
| `/api/v1/farms/{id}/snapshot` | GET | Tenant-authorized as-of snapshot |
| `/api/v1/planning-runs` | POST | Idempotent creation; returns 202 and run ID |
| `/api/v1/planning-runs/{id}` | GET | Run state, outputs, budget and warnings |
| `/api/v1/planning-runs/{id}/events` | GET | Server-sent events with sequence IDs |
| `/api/v1/planning-runs/{id}/cancel` | POST | Authorized cancellation |
| `/api/v1/strategies/{id}` | GET | Full strategy, assumptions and constraint audit |
| `/api/v1/strategies/{id}/accept-for-simulation` | POST | Development service actor only; checks phase/modes, expected versions, policy and validation reports; idempotent, 409 if stale; called automatically by the backend |
| `/api/v1/actuals/harvests` | POST | Validated actual records or explicitly synthetic simulation records, stored separately |
| `/api/v1/actuals/work` | POST | Service-recorded simulated execution in development; preserve imported historical actuals separately |
| `/api/v1/outcomes/compare` | GET | Baseline comparison with mode and cohort definitions |
| `/api/v1/reports/{id}` | GET | Audit-safe export; redact private data appropriately |

Use request IDs, pagination, size limits, validation errors, tenant checks and clear 401/403/409/422/429 handling. Treat uploads as untrusted. Implement optimistic concurrency and idempotency on automatic acceptance and simulated work; stale versions trigger recomputation without a human approval prompt. Plan creation must accept an idempotency key so UI retries do not launch duplicate expensive council runs.

### 8.6 Streaming events

Events include `run_started`, `input_warning`, `source_state`, `tool_started`, `tool_completed`, `agent_claim`, `claim_rejected`, `strategy_ready`, `evidence_validation`, `acceptance_validating`, `accepted_for_simulation`, `acceptance_invalidated`, `run_failed` and `run_completed`. Payloads carry `run_id`, monotonic `sequence`, `occurred_at`, `event_type`, `schema_version` and a typed body. SSE reconnects must resume from the last event ID. A stream disconnection is not a reason to restart the calculation.

---

## 9. Recommended application architecture

### 9.1 Stack and boundaries

Use a TypeScript/React frontend, preferably Next.js; a Python FastAPI/Pydantic backend; PostgreSQL for transactional state and tenancy; Parquet/DuckDB for analytical snapshots; and an object-store abstraction for raw assets and model artefacts. Use a small background worker for ingestion and planning runs. Redis or a heavier scheduler is optional until the job workload warrants it.

These are design choices, not a claim that a particular version is currently best. The master agent verifies current compatible versions and locks dependencies at implementation time. Do not guess future package versions. Use containers for reproducible local execution and separate real integration tests from fixture-only CI.

Run the numerical models and optimizer in Python. Generate frontend types from Pydantic/OpenAPI or checked shared JSON schemas to prevent drift. Use the DeepSeek-only server adapter and its documented Chat Completions tool/JSON contract; schema conformance still requires local validation and semantic checks. Use `deepseek-v4-flash` / `deepseek-v4-pro` for approved text roles and `deepseek-v4-flash-vision-exp` for image input. Both use `https://api.deepseek.com/chat/completions`. See the mandatory runtime amendment and its DS01–DS12 source register. Deterministic replay is explicitly labelled and makes no new inference calls. No secret or provider key belongs in frontend code.

### 9.2 Repository layout

```text
farmtact/
  AGENTS.md
  .codex/config.toml
  .codex/agents/
  apps/web/
  services/api/
  services/worker/
  packages/contracts/
  packages/ingestion/
  packages/features/
  packages/models/
  packages/planner/
  packages/council/
  research/                  # Curated evidence and source metadata
  data/manifests/             # Small committed metadata only
  data/raw/                  # Ignored; external object store in deployment
  data/normalized/           # Ignored generated artefacts
  tests/unit/
  tests/contracts/
  tests/integration/
  tests/science/
  tests/security/
  tests/e2e/
  scripts/
  docs/adr/
  reports/
```

The supplied handoff folders can be copied into this repository, but they are not a completed application scaffold. Preserve their provenance notices when implementation files are added.

### 9.3 Configuration

Use environment variables for database/object storage, data provider credentials, runtime model names, explicit allowed hostnames, operating mode, logging, maximum run duration and spending limits. Build-time Codex model configuration and runtime FarmTact council model configuration are separate.

Current official documentation lists GPT-6 Astra and GPT-5.6 Sol and documents Codex subagents [T01–T03, T09]. The supplied configuration uses `gpt-6-astra` for the master and `gpt-5.6-sol` for specialist build agents. Check availability in the account and installed Codex version before spawning. Do not silently replace unavailable models or promise their cost/latency. Runtime council/helper/evaluation models are independently configured **within the DeepSeek-only allowlist**. GPT/Codex build models are never runtime defaults. The live/test platform reads `DEEPSEEK_API_KEY` server-side and rejects alternate LLM provider origins/models, even if developer credentials exist in the surrounding environment.

### 9.4 Security and governance

Use authenticated sessions, server-side authorization and tenant-scoped data access. A farmer, operator and reviewer have different write permissions. A tenant can inspect and delete its private uploads and derived datasets subject to the chosen retention policy. Minimize buyer names and personal data sent to LLMs; use pseudonymous IDs wherever possible.

Treat external documents as untrusted data, not instructions. A paper saying “ignore previous instructions” or requesting access to credentials must have no effect on the runtime. Enforce source/hostname allowlists; block local/private-network and cloud-metadata URLs; validate redirects; bound decompression/file size; sanitize exported CSV cells; reject malicious archive paths. Do not execute formulas or code embedded in imported files.

During development, coding agents may version and validate synthetic recipes and the backend may record simulated planting work automatically. Real planting commitments, external communications, purchases, contract changes and actuator integrations remain disabled. Future operational human-approval controls may be tested using fixtures; no human interaction is required to complete this phase. This is a technical safeguard design, not a legal compliance certification.

### 9.5 Observability and operating cost

Track source freshness, failed imports, quarantine counts, model/run duration, solver status, token usage, tool budgets and acceptance/version conflicts. Audit prompts using redacted or hashed references where possible. Do not log credentials or full private datasets by default.

Use cached context/evidence, incremental ingestion and bounded parallelism. Define project performance budgets—for example a cached demo completing within a chosen presentation limit—but benchmark before promising them. Show measured runtime rather than an invented SLA. A failed remote integration must produce a labelled cached/replay state, not a fake “live” badge.

---

## 10. Web experience and gamification

### 10.1 Product language

FarmTact is a tactical planning board, not a generic ERP dashboard and not a casino. Game mechanics should make trade-offs visible and encourage evidence-based decisions. Avoid rewarding maximum planting, speculative production, wasted inputs or concealed uncertainty.

### 10.2 Required screens

**Farm setup:** load a complete versioned fictional farm automatically for the default demo; optional editing lets a user choose growing systems, enter effective capacity, customer commitments, crop recipes and available resources. Import CSVs with a mapping preview. Show missing fields and unresolved crop names before allowing a plan.

**Data room:** source cards labelled live/cached/synthetic/blocked; last observation and retrieval times; licence/access status; coverage, quality and unresolved mappings. Let a judge see that public data and fictional farm records are different layers.

**Crop library:** twelve crop cards with local aliases, harvested part, system compatibility, research references, stage/time-basis warnings and approved-versus-provisional parameters. Clicking a parameter opens its source and applicability. No fake nationally ranked “top ten” badge.

**Strategy room:** load the configured planning horizon and goal automatically, with optional user editing. Show specialist evidence briefs, tool activity and two bounded challenge rounds. Highlight disagreements and the actual input that would resolve them. Provide compact view by default and an expandable audit view.

**Tactical board:** bed/rack occupancy timeline, nursery-to-grow-out transitions, harvest windows and customer due dates. Strategy cards compare service, margin, waste, resources and downside—not just a composite score. The automatically accepted strategy populates the board; selecting another card previews it. No approval click is required. Locked/executed actions remain locked.

**Outcome/replay:** automatically generate labelled simulated work and harvest from fixed-seed fixtures; optional actual-data import remains separate; reconcile stock, delivery, rejects and waste; compare the decision against the stated baseline. Explain forecast error versus execution shortfall. Replay event scenarios using fixed seeds and clear synthetic labels.

### 10.3 Gamified interaction

A “mission” might be to cover a future buyer requirement while remaining within available beds and a waste threshold. The development policy selects among feasible strategies automatically; a user can optionally explore alternatives or request a modification. Event cards represent a confirmed order change, an observed crop delay, source-data loss or a simulated hazard. Every card identifies whether the event is real, imported or synthetic.

Earn progress for data completeness, resolving ambiguities, respecting constraints and making a well-documented decision. Keep this learning score separate from farm profitability and measured service. Avoid public farmer leaderboards without consent and comparability controls; otherwise different crop mixes and resources produce unfair comparisons.

After a turn, show which assumptions were wrong and what measurement would improve the next decision. Say “model update proposed from this outcome,” not “the AI has proved rainfall causes a precise yield reduction.”

### 10.4 Accessibility and usability

Support keyboard navigation, readable contrast, non-colour warning indicators, explicit units, Singapore dates/timezone, SGD defaults and mobile-friendly cards. Chinese/Malay/English crop aliases may appear while the interface remains English initially. Do not translate ambiguous crop names automatically into an unverified taxon.

Provide an accessible table alternative to the timeline. Prefer short evidence cards over animated conversations that the user must wait through. Respect reduced-motion settings. Export a practical sow/transplant/harvest worklist with version, modes, automatic-acceptance status and a simulation-only label.

---

## 11. Codex master orchestration and work packages

### 11.1 Coordination principles

The master coding agent owns scope, shared interfaces, migrations, dependencies, integration and development acceptance. No human sign-off is required for these decisions. Specialists work on bounded packages with explicit input/output contracts and file ownership. Run at most three specialists plus the master concurrently, for four running agents total, as required by the latest kickoff. No specialist recursively spawns additional agents without master approval.

Use separate git worktrees or disjoint owned paths. The contract owner proposes schema changes; the master merges them and announces a version before dependents proceed. Specialists must not race to rewrite lockfiles, shared types, global configuration or database migrations. A blocked agent returns a concrete blocker and a minimal proposed resolution rather than fabricating an interface.

Distinguish `specified`, `implemented`, `tested`, `integrated` and `validated on real farm data`. Status does not advance because a subagent says “done.” Require committed files, commands/results, test evidence and unresolved risks.

### 11.2 Specialist work packages

| ID / role | Owned work | Inputs | Required output and acceptance |
|---|---|---|---|
| A01 — Evidence/taxonomy steward | Source/licence registry, aliases and crop/HS mapping proposals | C01–C04, D22, curated registries | Twelve clean crop concepts, mapping review queue, publication/licence status; no invented popularity ranking |
| A02 — Brassica researcher | Caixin, pak choi, kailan, kale, mustard evidence | P01–P07, P11, P15, P20 | Contextual evidence cards; stage/cultivar/system distinctions; independently check critical numbers |
| A03 — Other-leafy researcher | Bayam, kangkong, lettuce, Basella, sweet-potato leaves | P08–P10, P12–P14, P16–P19 | Fresh/dry, multi-cut and leaf/tuber boundaries; local-transfer gaps stated |
| A04 — Data contracts/fixtures | Schemas, manifests, synthetic generator, private templates | All schema decisions | Reproducible builds, provenance, temporal fields, mass-balanced labelled fixtures |
| A05 — Singapore ingestion | NEA, SingStat, optional CPI/annual data | D01–D10, T08 | Snapshot/normalize/validate connectors; quantity units; safe cached failure mode |
| A06 — Global intelligence ingestion | POWER/GFS/ERA5/IMERG; optional FAO/satellite | D11–D23, T06–T07 | Versioned global context; verified exposure mapping; licence/latency restrictions |
| A07 — Forecast modeling | Demand, maturity, yield, uncertainty | Validated data and recipe contracts | Baselines first, grouped temporal tests, challenger report, no leakage |
| A08 — Planning/optimization | Candidates, capacity, perishability, scenarios | Forecast/resource contracts | Deterministic baseline + solver, infeasibility explanations and constraint tests |
| A09 — Runtime agents/API | Council, tools, job lifecycle, automatic development acceptance | Shared schemas and numerical tools | Bounded cited discussion, semantic validation, tenant security and replay mode |
| A10 — Frontend/gamification | Six screens, timeline, strategy comparison | OpenAPI/types, UI fixtures | Real data bindings, accessible states, visible modes, no client-calculated invented forecasts |
| A11 — QA/scientific/security reviewer | Independent adversarial tests and audit | All outputs | Leakage, taxonomy, units, constraints, citation and security findings; release recommendation |
| A12 — Integration/release engineer | Containers, CI, smoke/e2e runs, demo runbook | Reviewed feature packages | Reproducible local launch, dependency lock, measured tests and known-issues list |

The master can combine roles on a small team, but must preserve independent reviewing-agent assessment. Agent review and deterministic checks satisfy development review requirements without a human reviewer. Research agents deliver facts and gaps; they do not approve their own extracted numerical recipes for production.

### 11.3 Dependency graph and merge gates

**Gate G0 — preflight:** inspect repository, tool/model availability, budget and existing files; create decision log; freeze minimal interfaces. Also start DS-G0 and the authenticated DS-G1 DeepSeek capability trial as soon as the environment key exists. A09 may take an early bounded gateway task before broader council/UI work; preserve the subagent concurrency cap.

**Gate G1 — evidence/data:** A01–A06 work in controlled parallelism. A11 reviews taxonomy, units, licences and temporal contracts. A04 publishes the first dataset manifest. No personalized forecast is represented as real until private data and public inputs are correctly separated.

**Gate G2 — numerical core:** A07 and A08 implement baseline forecasts, candidate schedules and constraints. A10 may build against versioned fixtures. A09 creates the tool facade but does not invent result formats. A11 runs counterexamples before council integration.

**Gate G3 — council/UI:** integrate actual numerical tools and citations; add automatic development acceptance, simulated execution, event stream and replay. All actual agent calls use DeepSeek. Pass the authenticated text/tool/vision probes and DS-G2/DS-G3 workflow checks. Compare the council with a simpler DeepSeek tool-based or deterministic baseline, not a different runtime LLM provider. Reject simulated dialogues presented as live execution.

**Gate G4 — release:** A12 runs the full workflow from a clean checkout; A11 records a development review result or concrete blockers; the master advances passing gates without human sign-off. The master audits every public claim in the pitch against a real source or labelled simulation.

### 11.4 Specialist handoff report

Every specialist returns: objective; files changed; sources consulted and access gaps; interface/schema changes; commands and tests actually run; outputs/metrics; assumptions; security/data-quality risks; blockers; proposed next task. Include concise rationale, not hidden reasoning transcripts. The master stores reports under `reports/agents/` and maintains `docs/decision-log.md`.

### 11.5 Suggested timeboxing

For a short hackathon, deliver G0–G1 first, then a narrow numerical loop and one credible council/replanning demo. A sensible initial allocation is roughly one-third evidence/data, one-third models/planning/council, and one-third UI/integration/tests/presentation. These are planning suggestions, not a promise of completion in a particular number of hours.

P0 does not require satellite processing, deep learning or all optional external sources. P1 adds stronger calibration, public-market history, multi-cut models and partner allocation. P2 adds validated imagery, richer economic experiments and broader risk models. A comprehensive roadmap and a focused MVP are compatible.

---

## 12. Test plan and release criteria

### 12.1 Scientific/data tests

1. “Spinach” without context is unresolved; bayam, water spinach, Basella and true spinach never silently share a recipe.
2. Kailan/Chinese kale does not map to curly kale without explicit taxon resolution.
3. Sweet-potato tuber maturity and forage dry-matter yield cannot become leaf-market parameters.
4. A seedling-only study cannot authorize a mature-harvest coefficient.
5. Days-after-transplant and days-after-sowing are not interchangeable.
6. A value-only trade table cannot be used as imported kilograms.
7. Missing/estimated/suppressed trade quantity is not converted into zero.
8. Latest revised public data cannot leak into an earlier cutoff.
9. Historical realized weather cannot masquerade as a forecast available at planting.
10. Indoor zones do not receive an automatic direct rainfall crop-loss effect.
11. Satellite outputs require valid spatial support and cloud/quality metadata; an indoor roof produces an unsupported-use warning.
12. Non-commercial or unknown full-text/data licences block unauthorized corpus redistribution.
13. Duplicate references to the same experiment do not increase independent sample size.
14. Full-text/abstract-only and verified/unverified numeric claims remain distinct.

### 12.2 Numerical/planning tests

15. No field/rack layer exceeds available capacity during any occupied interval.
16. Nursery and grow-out calendars can bottleneck independently.
17. New sowing cannot satisfy an order before the permitted harvest date.
18. Executed plantings remain immutable during replanning.
19. Reserve seedlings yield no saleable crop without allocated grow-out capacity.
20. Multi-cut crop space stays occupied between cuts.
21. Marketable yield is not reduced twice by survival/packout.
22. Inventory and harvest mass balances hold within declared numeric tolerance.
23. All strategies are compared on identical scenario draws and horizon.
24. Solver timeout, feasible-not-optimal and infeasible states are honestly distinct.
25. Increasing a binding resource limit cannot produce a false new hard violation due to a unit conversion.
26. Zero demand, zero capacity, missing prices, absent buyer forecasts and 100% uncertainty all produce defined states.
27. A simulated partner purchase appears only with a validated fixture quote and feasible lead time; no real purchase is sent.
28. Proposed margin arithmetic reconciles to modelled quantities and stated costs.

### 12.3 Agent/security/UX tests

29. Every numeric recommendation references a validated tool field or approved evidence claim.
30. A malicious instruction embedded in a paper or CSV cannot trigger tools or reveal secrets.
31. A runtime council agent cannot mutate recipes, accept its own plan or bypass tenant authorization; only the backend policy may accept a validated plan for simulation in an eligible development tenant. Reject browser/prompt attempts to override phase, modes or service identity, and reject automatic acceptance for operational tenants or `live_advisory`/`live` runs.
32. Two challenge rounds and budget limits are enforced even when agents disagree.
33. Stale acceptance returns a conflict; the backend invalidates it and replans/revalidates automatically without waiting for a human.
34. Cross-tenant order, evidence-upload, plan and job access is denied.
35. Source failure shows cached/stale/blocked status instead of a fabricated live response.
36. SSE reconnect does not create duplicate planning jobs.
37. The seeded workflow completes acceptance, simulated execution and replanning with zero human clicks; optional setup, comparison and inspection support keyboard-only navigation.
38. Demo/replay/live labels persist in screenshots, exports and outcome comparisons.
39. Baseline and council versions can be evaluated on the same input fixture.
40. Performance/cost claims in the demo are measured or explicitly described as targets.

### 12.4 Required release evidence

The twenty additional DS-01–DS-20 acceptance cases in `FarmTact_DeepSeek_Runtime_Specification.md` are mandatory. Offline HTTP mocks are contract tests, not successful platform/live agent calls. Authenticated DeepSeek checks without a key must remain blocked, not counted as passing. Development release requires account-level text/tool/vision tests and actual application egress review by code and reviewing agents. Future operational approval and promotion are not part of this gate.

A clean repository must build from documented commands with pinned dependencies. Include unit/contract/e2e test reports, source coverage report, dataset manifest, model evaluation report, solver feasibility report, security/scientific issue list and demo runbook. Real APIs may be tested separately from deterministic CI; never make public endpoints a hidden hard dependency of every unit test.

The production-readiness label stays off until real tenant data, farm-specific recipe validation, operational approval flows and adequate evaluation exist. Hackathon readiness means a working, transparent vertical slice—not agricultural certification.

---

## 13. How the master should begin

Read available `AGENTS.md` instructions, this specification and any existing master prompt/research registries. Create missing handoff artifacts under Section 0 without waiting for their delivery. Check the current Codex configuration and available models. Inventory the repository before writing. Spawn the evidence/taxonomy, two crop research and contracts roles within the parallelism cap. Ask them to improve and verify the supplied starting records, not erase access limitations or invent new facts.

The first review must answer: Which sources are actually fetched? Which parameters can be used for this specific farm? Which remain literature-only? Which data is synthetic? Which fields prevent a feasible plan? Only then promote the numerical and UI branches.

The desired final product is not “agents confidently discussing vegetables.” It is **a Singapore farmer seeing competing, evidence-backed strategies whose quantities, timing, constraints and uncertainty can be independently checked**.

---

## 14. References and accompanying files

Source IDs in this specification are listed in the existing root-level `RESEARCH_REVIEW.md`, which contains publication titles, DOIs, access status and limitations. Populate the planned `research/source_registry.json` from those records; preserve a single canonical research review when organizing the repository. `research/dataset_registry.json` records source priorities, costs/access distinctions and ingestion traps. `research/strategy_catalogue.json` contains all 38 proposed analytical/agent strategies and their evaluation criteria.

The handoff does not redistribute the referenced third-party papers, imagery or large datasets. Live endpoint access and file-level licences must be checked during the build. The supplied JSON/CSV tables are curated metadata and design artefacts; the synthetic generator creates test records only.


## 15. DeepSeek implementation handoff (mandatory v1.1 amendment)

Read `FarmTact_DeepSeek_Runtime_Specification.md`; create `docs/runbooks/deepseek_trial_and_cutover.md` if absent and keep it consistent with this development policy. Implement the referenced server-only gateway seed, fourteen-route DeepSeek role/helper manifest, offline provider contract tests and authenticated trial if absent. These artifacts are implemented; inspect the existing runtime, scripts and tests before extending them. The original data-first objective remains: run the API capability work early and in parallel, not as an excuse to replace data engineering with chat.

Once those artifacts exist, run `python -m pytest tests/deepseek -q`, then automatically within the configured development budget—when the key is available—`python scripts/deepseek_trial.py --live --with-council` in test execution mode. The second command must make real billable calls within recorded request/token limits; no additional human confirmation is required for this development trial. It tests provider compatibility and a toy council, not the completed web app. Its full workflow uses synthetic input and preserves the impossible-lead-time counterexample.

A09 owns `runtime/` and `config/deepseek_runtime.json` until these are integrated into the application package layout. A12 owns trial/runbook/release execution; A11 independently extends `tests/deepseek/`. Coordinate shared edits through the master. Authenticated success must be established in the target environment. This documentation rewrite makes no inference calls and creates no trial report; record the actual results when implementation and trials run.


## Seven-agent release amendment — 2026-09-09

Publish this change as a fresh `/v3/` instance; preserve `/v1/` and `/v2/` images and game state. `packages/agents.py` defines the canonical roles. Acceptance policy `automatic-development-v2` records `council-evidence-gate-v1`, with its issues and either seven-agent findings or numerical-baseline basis.

Market is distinct from Demand: it describes prices and commercial/community context; Demand computes required quantities and dates. `GET /api/v1/market-signals?crop=...` is tenant scoped, read only and makes no inference/network calls. No social or field-reaction source is connected in this release. Show an explicit empty state, never generated reactions presented as observations. Future supplied observations must have crop/source IDs, UTC observation/retrieval times, reuse permissions and point-in-time eligibility. Aggregate reported directions deterministically; preserve provenance and source restrictions. No reaction changes demand, price or yield automatically. Frozen mission/conversation context retains the selected evidence on replay.


### V4 dialogue usability correction

Native device-keyboard voice typing remains the simplest supported speech-entry
path. Keep its explanatory hint below the editable message row, never competing
for the same horizontal flex space. Message fields must remain at least 180 pixels
wide at 360-pixel viewport width; field and send touch targets are at least 44 pixels
high. V4 corrects this presentation issue without changing seven-agent roles,
numerical calculations or source connections. V3 and earlier instances stay frozen.
