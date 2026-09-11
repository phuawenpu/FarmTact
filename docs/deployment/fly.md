# FarmTact on Fly.io

Live: [edition chooser](https://farmtact.fly.dev/) and
[v7 council](https://farmtact.fly.dev/v7/research), Singapore (`sin`). This is a synthetic
development demonstration; actual farm operations remain disabled.

## Active runtime

One shared 4-vCPU/4096-MB Machine runs the gateway and v1–v7 as eight containers,
each pinned to its release image. One encrypted 3-GB volume provides isolated
subtrees for their PostgreSQL clusters, caches and saved state. The common storage
parent is unmounted before each app drops privileges. PostgreSQL uses private
Unix sockets. Only the gateway receives public HTTP traffic.

`config/hosting/shared.json` identifies the active Machine and volume;
`config/releases/registry.json` records the immutable editions. Six superseded
Machines and seven old volumes were deleted after verified migration. Empty
edition app registrations remain; unrelated Fly apps were untouched.

`Dockerfile.fly` builds the locked Python/Node application with PostgreSQL 18.
Encrypted runtime secrets supply credentials; never use build arguments or
committed files for keys. New edition containers receive the required secret
names from the existing app. Shared operational controls enforce inference and
abuse limits while each edition retains independent game state.

## Publish and inspect

Follow [Publishing immutable editions](editions.md). The publisher updates the
shared Machine, probes the next edition, then atomically appends the registry.
Do not run a generic `fly deploy`: root `fly.toml` is retained for image building
and historical bootstrap and does not describe the active container topology.

```bash
fly machines list --app farmtact
fly checks list --app farmtact
fly volumes list --app farmtact
.venv/bin/python -m pytest tests/deployment tests/editions -q
```

Operator configuration updates use `scripts/shared_host_config.py` as described
in the edition runbook. Do not scale horizontally without shared database/worker
coordination. One host is one failure boundary and shared updates can interrupt
all editions. Volume snapshots alone are not a verified database restore process.

## Verification and local development

[V7 rollout evidence](../../reports/v7/implementation.md) records public browser,
strategy, isolation, preservation and health checks. Its two explicit adviser
probes remain unsupported; numerical/browser checks are separately scoped. Historical provider reports retain their actual model settings
and limitations; do not treat a numerical test as a live advisor capability test.

The Sprite HTTP and private tunnel services are shut down; the local PostgreSQL
service is retained. Register temporary development services through the Sprite
skill. Do not expose backups, credentials or arbitrary filesystem paths over HTTP.
