# FarmTact on Fly.io

The active topology is now defined in [the editions runbook](editions.md).
`config/hosting/shared.json` identifies the active 4-vCPU/4-GB Machine and
single 3-GB shared volume. The immutable publisher updates that Machine with
separate, pinned gateway/edition containers. `fly.toml` remains an image-build and
historical bootstrap input: a generic `fly deploy` would replace the shared
container configuration and must not be used for current publication.

The sections below document the historical single-app deployment. Follow the
editions runbook for current deployment, resource sizes and verification.

Target: `farmtact`, https://farmtact.fly.dev, Singapore (`sin`). Deployment preserves the autonomous-development/synthetic-simulation policy. This is a development instance, not operational farm promotion.

## Runtime

`Dockerfile.fly` builds the web bundle and locked Python environment, then combines Python 3.13 and PostgreSQL 18 on matching Debian Bookworm images. Its build smoke imports native dependencies and the actual app as the unprivileged runtime user. Source/configuration remain root-owned and read-only to that user.

One shared-CPU Machine with 2 GB RAM runs the API worker and PostgreSQL. The encrypted 3 GB `farmtact_data` volume holds PostgreSQL and public-data snapshots. PostgreSQL listens only on a private Unix socket; only HTTP port 8080 is routed by Fly. The supervisor checks the database/schema before starting the web app, strips unrelated credentials from children, and allows bounded graceful shutdown. Existing PostgreSQL data is reused and mismatched major versions fail closed.

A bounded public refresh runs separately at boot without provider credentials; its snapshots, source times and failures persist. DeepSeek credentials are supplied with Fly encrypted secrets at runtime, never build arguments or image files. The passwordless Unix-socket database URL is intentionally non-secret. Fly's secret behavior is described in the [official secrets documentation](https://fly.io/docs/apps/secrets/).

## Deploy and inspect

```bash
fly config validate
.venv/bin/python -m pytest tests/deployment -q
fly deploy --app farmtact --remote-only --ha=false --yes
fly status --app farmtact
fly checks list --app farmtact
```

The initial deployment creates one Machine; `--ha=false` avoids a second independent database on a separate volume. Do not scale the process horizontally without first introducing shared database/worker coordination. One Machine means deployment/host failures can interrupt availability. Scheduled volume snapshots retain seven days; that is not a tested database restore procedure. See [Fly's volume documentation](https://fly.io/docs/volumes/overview/).

For initial setup, create `farmtact_data` in `sin` and stage the supplied DeepSeek key using `fly secrets import --stage --app farmtact` through stdin from a credential manager. The active app is already configured; do not rotate or reprint credentials to redeploy.

## Verify the remote application

```bash
FARMTACT_BASE_URL=https://farmtact.fly.dev FARMTACT_BROWSER_REPORT=reports/fly_browser.json FARMTACT_SCREENSHOT_DIR=apps/web/screenshots/fly node tests/browser/run.mjs
.venv/bin/python scripts/integrated_demo.py --url https://farmtact.fly.dev --council --vision --replan --deterministic-replan --report reports/fly_integrated_demo.json --browser-state /tmp/farmtact-fly-browser-state.json
```

Browser checks create numerical missions only. The second command makes bounded actual DeepSeek calls. Replay makes none. Browser session-state files stay private and outside the repository. A fresh Fly session receives its own synthetic tenant; it does not automatically migrate Sprite session cookies or private databases.

Latest rollout: health and 44 browser checks passed, and saved farm/session data survived image replacement with clean PostgreSQL shutdown. The actual DeepSeek council completed provider calls but acceptance was withheld for an unsupported critic threshold. See [deployment verification](../../reports/fly_deployment.md) for the separate results and exact deployed image.
