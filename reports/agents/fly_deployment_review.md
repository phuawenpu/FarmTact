# Independent Fly deployment review

Reviewed: 2026-09-08

Scope: `Dockerfile.fly`, `fly.toml`, `scripts/fly_entrypoint.sh`, and
`scripts/fly_boot.py`. This was a source-level and mocked-process review. It did
not deploy, mutate Fly resources, use credentials, or make external API calls.

## Disposition

No open source-level blocker remains for the single-machine development
deployment. The deployment still needs validation against the final rebuilt
image and persistent volume because this review did not execute the container or
exercise Fly's signal and mount behavior directly.

Ten focused tests pass in `tests/deployment/test_fly_boot.py`. They cover the
Unix-only PostgreSQL command, credential partitioning, root refusal, PostgreSQL
major-version rejection, volume reuse, bounded termination, termination during
startup, fail-closed schema initialization, runtime file permissions, compiled
Python dependency smoke checks, and absence of a published database port.

## Findings and resolutions

### FD-01 — HIGH — Shutdown could exceed the platform deadline (resolved)

The first reviewed configuration allowed Fly 45 seconds to stop the machine,
while sequential forced cleanup could consume 52 seconds before scheduler and
filesystem latency. That could have caused Fly to kill PID 1 before PostgreSQL
completed its fast shutdown.

`fly.toml` now allows 90 seconds. The supervisor's worst declared forced-cleanup
wait is 52 seconds, leaving 38 seconds for loop and platform latency. PostgreSQL
receives `SIGINT`; refresh and web receive `SIGTERM`, followed by bounded kill
escalation (`scripts/fly_boot.py:42-50`, `scripts/fly_boot.py:122-125`). The test
derives its assertion from the configured Fly deadline rather than duplicating a
constant.

### FD-02 — HIGH — Termination during startup could continue launching services (resolved)

The first reviewed supervisor installed signal handlers after volume
initialization and did not check the termination flag between database setup
commands. A rolling stop during startup could therefore continue through schema
setup and launch the web or refresh process.

Handlers are now installed before initialization, `initdb` is bounded to 45
seconds, and the flag is checked after every potentially blocking startup phase
and immediately after web launch (`scripts/fly_boot.py:53-74`,
`scripts/fly_boot.py:90-108`). Tests inject termination during `initdb` and the
database-existence probe and prove that no later service starts.

### FD-03 — MEDIUM — Child processes inherited unrelated credentials (resolved)

The first reviewed web launch inherited the complete supervisor environment.
PostgreSQL and public ingestion already used a credential-free environment, but
the web process only needs the DeepSeek credential.

`public_environment()` removes every named provider and deployment credential.
`web_environment()` selectively restores only `DEEPSEEK_API_KEY`
(`scripts/fly_boot.py:18-33`). The database and refresh receive the public
environment, and the web process receives the restricted web environment
(`scripts/fly_boot.py:77`, `scripts/fly_boot.py:106-112`). A sentinel-based test
checks all three child environments without exposing a real credential.

### FD-04 — HIGH — Initial image made the unprivileged boot script unreadable (resolved)

The first built image preserved restrictive source-worktree permissions, so the
`farmtact` account could not read `fly_boot.py`. The failed rollout was canceled.

The image now normalizes `/app` readability while retaining root ownership and
runs an actual import/fixture smoke check as `farmtact`
(`Dockerfile.fly:31-36`). This also avoids making application code writable by
the network-facing account. Only fixed volume and socket directories are handed
to `farmtact` at runtime (`scripts/fly_entrypoint.sh:3-6`).

### FD-05 — MEDIUM — Copied Python runtime had no compiled-extension check (resolved)

Copying `/usr/local` from `python:3.13-slim-bookworm` into
`postgres:18-bookworm` depends on compatible shared libraries. Matching Bookworm
bases reduces the risk but `python --version` alone did not exercise the binary
packages used by planning and persistence.

The build now imports psycopg, SQLAlchemy, PyArrow, DuckDB, OR-Tools, and Pillow
after the copy (`Dockerfile.fly:12-20`). Missing runtime libraries therefore fail
the image build rather than a user request.

## Confirmed boundaries

- PostgreSQL is configured with an empty `listen_addresses` value and a fixed
  Unix socket directory (`scripts/fly_boot.py:36-39`). Neither the Dockerfile nor
  Fly service configuration exposes port 5432.
- A missing cluster is initialized with peer authentication locally and rejected
  host authentication. An existing cluster is reused only when `PG_VERSION` is
  exactly 18; a different major version fails before a process starts
  (`scripts/fly_boot.py:66-72`). A nonempty unknown directory remains subject to
  `initdb`'s fail-closed refusal.
- Database readiness and schema creation complete before Uvicorn starts. A
  schema command failure unwinds through `finally`, stops PostgreSQL, and never
  starts the web process (`scripts/fly_boot.py:77-106`).
- The public refresh runs as a separate credential-free process and has a
  120-second runtime bound (`scripts/fly_boot.py:109-119`). Its failure does not
  replace persisted provenance with a fabricated successful source.
- The mounted PostgreSQL and public-data directories are fixed paths, mode 0700,
  and owned by the unprivileged runtime account. The application process refuses
  to supervise while running as root (`scripts/fly_entrypoint.sh:3-6`,
  `scripts/fly_boot.py:53-55`).

## Residual operational limits

PostgreSQL and the web service intentionally share one development VM and one
regional volume. This design has no database high availability and depends on
Fly volume snapshots for recovery. Before considering the rollout complete,
validate the final image boot, health check, authenticated application flow,
volume reuse across one restart, and graceful machine stop in Fly. A restore test
from a volume snapshot remains separate operational work.
