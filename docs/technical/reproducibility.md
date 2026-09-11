# Reproducing the implementation report

The report audits source baseline `a96025e`; released v7 uses the source/image in
[`config/releases/v7.json`](../../config/releases/v7.json). Documentation and code
can evolve after an edition is frozen. Record which source is being checked.

## 1. Distinguish the kinds of reproduction

| Activity | Dependencies | Changes / external calls |
| --- | --- | --- |
| Read source and archived JSON | Git checkout | None |
| Regenerate report figures | Python application requirements; optional CairoSVG + native Cairo for PNG | Writes documentation figures/data; no database, solver or network call |
| Offline provider/contracts tests | Locked Python requirements | In-process HTTP mocks; no real inference |
| Local numerical checks | Locked Python requirements | Real local solver; no inference; timings/feasible schedules can vary |
| PostgreSQL lifecycle/concurrency tests | Explicit dedicated local test databases | Writes isolated test state; never target a live farm database |
| Browser journeys | Built frontend, running dev service, Playwright Chromium | Real API/numerical work; some scripts intercept adviser fixtures; check each script |
| Public-data rebuild | Approved public source access or archived raw bytes | Live fetch creates new snapshots; offline needs raw files absent from Git |
| Authenticated DeepSeek trial | Explicit server credential, registered model access, finite budget | Metered calls; not needed for documentation reproduction |
| Edition publication | GitHub/Fly access and clean committed source | Updates hosting and immutable release registry; not part of this audit |

## 2. Local application prerequisites

Use Python 3.13+, Node 24, PostgreSQL 18, the committed
[`requirements.lock.txt`](../../requirements.lock.txt) and
[web lockfile](../../apps/web/package-lock.json). From repository root:

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
npm ci --prefix apps/web
npm run build --prefix apps/web
```

Provision a **development** database and supply `FARMTACT_DATABASE_URL` through
the process environment. `Store()` defaults to the Sprite-specific Unix socket
`/tmp/farmtact-pg` and database `farmtact`; it does not create the PostgreSQL server
or database. `.env.example` lists settings; the entrypoint does not automatically
read a `.env` file. The application otherwise defaults to `test` execution and
synthetic data; a key must not switch it to real farm operations.

```bash
.venv/bin/python scripts/initialize_database.py
.venv/bin/python -m packages.fixtures
.venv/bin/python scripts/build_dataset.py --with-power
.venv/bin/python scripts/build_features.py
```

The fixture command writes the fixture and shared schema. Feature/dataset commands
write artifacts; do not mistake regeneration for a read-only check. Raw and normalized
public files are ignored. `build_dataset.py --offline` requires already retrieved
bytes and cannot reconstruct historical source contents from a manifest alone.

Outside Sprite, run `.venv/bin/python scripts/serve.py`. Inside Sprite, register
it through `sprite-env services create` using the platform skill; do not create an
unmanaged background server. For example, after provisioning the database service:

```bash
sprite-env services create farmtact-doc-dev \
  --cmd /home/sprite/workspaces/Code2/.venv/bin/python \
  --args /home/sprite/workspaces/Code2/scripts/serve.py \
  --http-port 8080
```

Use absolute paths appropriate to the actual checkout. This example does not
provision the database or credentials. Inspect service CLI help for dependency
registration and logs. The public Sprite URL must serve only the application,
never repository roots, dumps or private files. No local HTTP service was required
or started during this documentation audit.

## 3. Offline and numerical verification

These representative groups avoid a running PostgreSQL server and metered calls.
The separate broader conversation test module has a known implicit D04 public-cache
dependency (DATA-06); its failed fresh-checkout assertion is preserved in the audit:

```bash
.venv/bin/python -m pytest -q \
  tests/deepseek/test_gateway.py \
  tests/contracts/test_private_data.py \
  tests/contracts/test_features.py \
  tests/models/test_explorer_numerics.py \
  tests/seven_agents/test_council.py \
  tests/review/test_provider_isolation.py

.venv/bin/python -m pytest -q \
  tests/numerical/test_planner.py \
  tests/planner/test_research_constraints.py

.venv/bin/python -m pytest -q \
  tests/council_research/test_sessions.py \
  tests/council_research/test_independent_review.py \
  tests/gameplay/test_scenarios.py

.venv/bin/python scripts/generate_web_contracts.py --check
```

The full `pytest -q` suite also includes PostgreSQL recovery/concurrency tests.
Inspect each database fixture first. Research tests explicitly require a separate
`farmtact_research_test` database; other historical test modules use their documented
local test configuration and may recover queues. **Do not run them against a
running application database.** SQLite tests establish local behavior but do not
prove PostgreSQL lock/concurrency semantics.

`node tests/browser/run.mjs` is the original journey. Later features have separate
scripts under `tests/browser/` and their release reports record invocation details.
Install Chromium with `cd apps/web && npx playwright install chromium` when needed.
An intercepted adviser fixture verifies UI behavior, not DeepSeek response quality.

`scripts/evaluate_numerical.py` rewrites `reports/numerical_evaluation.json`.
Run it only when intentionally producing a new versioned evaluation artifact. Its
four-second per-policy solver limit means exact allocations, bounds and timing are
not guaranteed identical between environments. Preserve the archived report and
compare constraints/semantics, not only JSON equality. The metadata gap DATA-03
must be fixed before treating regeneration as complete evaluation provenance.

## 4. Report figures and rendering

The committed SVG/PNG figures can be read without Python. To regenerate SVGs and
source data from the fixture:

```bash
.venv/bin/python docs/technical/figures/generate.py
```

For PNGs, install the optional documentation tools in a separate environment using
[`requirements-docs.txt`](requirements-docs.txt), plus the native Cairo library
and DejaVu fonts supplied by your operating system. These packages are not runtime
application dependencies. Then run the generator with `--png`. The figure generator
imports the locked application's fixture/contracts/forecast modules and makes no
provider, source-ingestion, database or optimization request.

The [figure data](figures/data.json) records the fixture hash, crop parameters,
caixin observations and one-step EWMA values. Architecture arrows are authored
annotations from source inspection. SVG text includes descriptions for accessibility.
The figures were visually inspected as PNGs during the documentation audit.

The committed [diagram manifest](figures/diagrams/manifest.json) records the 20
rendered Mermaid SVGs and hashes of their chapter source blocks. To regenerate
those images, use a separate documentation tool directory:

```bash
npm install --prefix /tmp/farmtact-doc-tools \
  @mermaid-js/mermaid-cli@11.17.0 mathjax-full@3.2.1
node /tmp/farmtact-doc-tools/node_modules/puppeteer/install.mjs
.venv/bin/python docs/technical/render_diagrams.py \
  --mmdc /tmp/farmtact-doc-tools/node_modules/.bin/mmdc
```

Chromium requires its native system libraries. A restricted local VM may require
an explicit Puppeteer launch configuration; `--puppeteer-config` passes that file
to Mermaid CLI. This audit used a local `--no-sandbox` browser solely for trusted
authored documentation, with no public HTTP service. Mermaid parsing caught one
sequence-label semicolon error, which was corrected before all 20 diagrams rendered.

[Render the report](render_report.py) with Python Markdown and the optional local
MathJax module to produce a single printable HTML document:

```bash
.venv/bin/python docs/technical/render_report.py \
  --mathjax-module /tmp/farmtact-doc-tools/node_modules/mathjax-full \
  --output /tmp/farmtact-technical-report.html
python docs/technical/check_docs.py
```

The renderer embeds scientific figures, Mermaid SVGs, existing screenshot evidence
and MathJax-rendered equations. It includes all seven chapters and makes no network
request. Without `--mathjax-module`, TeX remains source notation; without rendered
diagram files, Mermaid remains source notation. The committed reading copies use
both renderers. Source/evidence links point to GitHub; there are no external scripts,
fonts or CDN dependencies in the HTML. [The PDF exporter](export_pdf.cjs) can print
that HTML using local Puppeteer and also checks image loading, internal links and
page overflow. See the audit record for the actual invocation and limits.

## 5. Authenticated trials and archival discipline

The [DeepSeek runbook](../runbooks/deepseek_trial_and_cutover.md) describes the
bounded real trial. `--live` means authenticated transport, not operational farm
mode. Never print a credential or include it in command arguments. Provider
failure must remain blocked/failed; do not substitute another provider.

Keep separate records for source inspection, offline mocks, fresh authenticated
calls and archived replay. A full suite pass does not validate crop biology or
human decision benefit. The exact checks run for this audit, including counts,
limitations and generated files, are in
[the audit record](../../reports/documentation/2026-09-11.md).
