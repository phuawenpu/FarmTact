# FarmTact · Command & Cultivate

A mobile tactical planning board for a fictional Singapore vegetable farm. Ten crop knowledge profiles connect to a versioned evidence register; caixin, pak choi, kailan and lettuce are exercised in the synthetic farm. Python calculates Lean, Balanced and Resilient plans; actual DeepSeek roles review frozen results. Development plans are automatically accepted for simulation after validation.

**This is a working development demonstration.** Farm orders, recipes, outcomes and financial results are synthetic. Public weather/trade/climate sources are separate, with observed/retrieved time, freshness, units, licence and source lineage. No planting, purchase or operational approval is sent to a real farm.

## Deployed app

**https://farmtact.fly.dev/** is the primary development deployment, running in Singapore with persistent PostgreSQL and DeepSeek configured through encrypted runtime secrets. The latest edition is [v3: seven perspectives, one farm](https://farmtact.fly.dev/v3/); v1 and v2 retain independent saved state and frozen deployments. See the [edition runbook](docs/deployment/editions.md) and [seven-agent verification](reports/seven_agents/implementation.md).

## Running in this Sprite

The Sprite HTTP services are retired after release verification. PostgreSQL remains available over a private Unix socket. Use the Sprite skill to register a temporary local service when developing; the public playable app is on Fly.

```bash
sprite-env services list
# Register a development service before trying to restart it.
```

The service command is `.venv/bin/python scripts/serve.py`, with `farmtact-db` as its dependency. The server reads `DEEPSEEK_API_KEY` from its process environment or the owner-only local secret-delivery file outside this repository. Never put keys in frontend variables, commands, logs or committed files. Missing provider access leaves numerical planning and explicit recorded replay available.

## Reproduce locally

Requirements: Python 3.13, Node 24, PostgreSQL 18. Create an empty PostgreSQL database, then set `FARMTACT_DATABASE_URL` to its connection string. In this Sprite the default is `postgresql+psycopg://sprite@/farmtact?host=/tmp/farmtact-pg`.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.lock.txt
npm ci --prefix apps/web
npm run build --prefix apps/web
.venv/bin/python scripts/initialize_database.py
.venv/bin/python -m packages.fixtures
.venv/bin/python scripts/build_dataset.py --with-power
.venv/bin/python scripts/build_features.py
.venv/bin/python scripts/serve.py
```

In Sprite, use `sprite-env services create` for the final server command, rather than launching an unmanaged background process. Public ingestion has bounded timeouts and explicit failure/cache states. For offline normalization from already fetched bytes, use `scripts/build_dataset.py --offline`; raw snapshots are deliberately not committed. A fresh checkout needs the bounded live fetch to obtain them.

A Docker/Compose definition is also included. Generate the ignored local database secret with `python scripts/bootstrap_env.py`, build the public context with the command above, then run `docker compose up --build`. This optional Compose definition remains unverified. The separate `Dockerfile.fly` has been built and deployed successfully on Fly.io.

## Verify

```bash
.venv/bin/python -m pytest -q
.venv/bin/python scripts/evaluate_numerical.py
node tests/browser/run.mjs
.venv/bin/python scripts/generate_web_contracts.py --check
```

Original development verification: **191 Python tests and 44 browser checks passed**, plus an isolated clean-checkout build and numerical workflow. See [the completion audit](reports/completion_audit.md) and [clean-checkout report](reports/clean_checkout.json).

The PostgreSQL concurrency tests use isolated test tenants and clean their own rows. Browser checks use Chromium against the running app at widths 360, 390, 430 and 1280; they select numerical-only planning to avoid paid calls. Install the browser once with `cd apps/web && npx playwright install chromium`.

Authenticated checks make real, metered calls:

```bash
FARMTACT_EXECUTION_MODE=test .venv/bin/python scripts/deepseek_trial.py --live --with-council
.venv/bin/python scripts/integrated_demo.py --council --vision --replan --deterministic-replan
```

The trial is bounded to sixteen requests and an 8,192-output-token reservation. Application runs have their own finite per-run request/token/time limits and a global daily reservation cap; unused reservations are reconciled. There is no alternate LLM provider. Format repairs are bounded and recorded. Replaying a recorded run makes zero new inference calls.

## Evidence and limits

- [Autonomous-development build specification](FarmTact_Build_Specification.md)
- [DeepSeek runtime specification](FarmTact_DeepSeek_Runtime_Specification.md)
- [Completion audit](reports/completion_audit.md)
- [Execution plan and ownership](docs/execution-plan.md)
- [Dataset coverage and quality](data/reports/data_quality.json)
- [Dataset manifest](data/manifests/dataset_manifest.json)
- [Numerical evaluation](reports/numerical_evaluation.json)
- [Authenticated provider trial](reports/deepseek/latest.json)
- [Integrated application demonstration](reports/integrated_demo.json)
- [Independent backend review](reports/agents/independent_backend_review.md)
- [Mobile browser review and screenshots](reports/agents/mobile_ui.md)
- [Decision log](docs/decision-log.md)

Unsupported claims are rejected visibly. Feasible schedules may still have explicit unmet demand; the planner never moves future harvest into an earlier delivery. The fixture models whole beds, four single-harvest recipes and declared scenario weights. Multi-cut crops are knowledge profiles only. No synthetic model is production-validated, and no claimed savings are measured farm impact.

The demo service combines gateway checks with a Python socket egress policy. Production requires infrastructure-level egress controls, operational authorization and real-farm validation. Current source coverage is bounded: one SingStat page/period and seven NASA climate days supplement the NEA feeds; this is not a complete historical trade warehouse.
