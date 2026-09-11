# FarmTact on Fly.io

Live: [edition chooser](https://farmtact.fly.dev/) and
[v9 application](https://farmtact.fly.dev/v9/), Singapore (`sin`). This is a synthetic
development demonstration; actual farm operations remain disabled.

## Active runtime

One shared 4-vCPU/4096-MB Machine runs the gateway and v1–v9 as ten containers,
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

[V9 deployment evidence](../../reports/v9/deployment-health.json) records nine
passing edition health/source checks; its
[preservation audit](../../reports/v9/preservation-after.json) records preserved
v1–v8 source and state. The deployed V9 source is
`89d29cc3e071e12373204ff234d0a261ce71b5a1`, pinned to image
`registry.fly.io/farmtact@sha256:42702ca38566d87c359ae2f92f924b403dbf8fb2ae8166f5377cc829e8d725e4`.
The authenticated public UI replay passed 38 of 38 mobile/desktop checks without
forwarding mutation or inference requests. These are deployment and isolation
results. The separate live V9 trial used 21
actual requests and failed its quality gate: 12 of 18 automated cases passed while
workflow integrity passed, and a scorer-missed false-fulfilment claim independently
prevents acceptance. V10 is the next unpublished remediation candidate.

[V7 rollout evidence](../../reports/v7/implementation.md) records public browser,
strategy, isolation, preservation and health checks. Its two explicit adviser
probes remain unsupported; numerical/browser checks are separately scoped. Historical provider reports retain their actual model settings
and limitations; do not treat a numerical test as a live advisor capability test.

The Sprite HTTP and private tunnel services are shut down; the local PostgreSQL
service is retained. Register temporary development services through the Sprite
skill. Do not expose backups, credentials or arbitrary filesystem paths over HTTP.
