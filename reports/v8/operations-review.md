# V8 operations and recovery review

Date: 11 September 2026  
Scope: local isolated recovery exercise and source-level review of the current
edition namespace, process egress policy, and shared-host recovery tools  
External mutations: none; no Fly deployment or provider request was made

## Findings

The local logical PostgreSQL recovery path was exercised successfully with
synthetic state. The current shared-host configuration generator also reproduced
the expected gateway plus v1–v7 container set with pinned images and unique
ports. Process-level Python egress denied an undeclared hostname while retaining
private Unix-socket database access.

These checks do not close OPS-01. The deployed editions share one Fly Machine and
one persistent volume, so the host, volume attachment, and gateway are common
availability boundaries. No multi-host failover, remote Fly snapshot restore,
disaster recovery time, sustained load, or infrastructure-enforced egress policy
was tested. The Python socket hook is defense in depth and is not an OS firewall.

## Isolated PostgreSQL dump and restore

Only these purpose-created local databases were used:

- source: `farmtact_v8_ops_source`
- restore target: `farmtact_v8_ops_restore`
- private socket: `/tmp/farmtact-pg`

Neither the development app's `farmtact` database nor a queue worker was used.
The source contained one synthetic tenant, one frozen synthetic farm version, one
zero-council planning mission, and one synthetic recovery-probe event. No
provider call was requested.

The exercised command sequence was:

```bash
createdb -h /tmp/farmtact-pg -U sprite farmtact_v8_ops_source

pg_dump -h /tmp/farmtact-pg -U sprite \
  --format=custom --no-owner --no-privileges \
  --file=/tmp/farmtact-v8-operations.dump \
  farmtact_v8_ops_source

createdb -h /tmp/farmtact-pg -U sprite farmtact_v8_ops_restore

pg_restore -h /tmp/farmtact-pg -U sprite \
  --no-owner --no-privileges \
  --dbname=farmtact_v8_ops_restore \
  /tmp/farmtact-v8-operations.dump
```

After restore, an independently constructed `Store` loaded the target. A
canonical JSON hash over tenant identity, stored session hash, farm payload,
mission payload, and ordered event list matched source and target:

```json
{
  "status": "PASS",
  "state_sha256": "ac59588855fb774e77de8e2ff556ffa05780f933fc8217ddb35c8d925dbd1b29",
  "table_count": 23,
  "nonempty_table_counts": {
    "farm_versions": 1,
    "planning_runs": 1,
    "run_events": 1,
    "tenants": 1
  },
  "row_counts_equal": true,
  "content_equal": true,
  "provider_calls": 0
}
```

This proves that the installed local `pg_dump`/`pg_restore` pair can preserve the
current schema and this bounded synthetic state between fresh databases. It does
not prove point-in-time recovery under concurrent writes, WAL recovery, a backup
from another PostgreSQL major version, encrypted off-host backup custody, Fly
snapshot integrity, or a production recovery-time/recovery-point objective.

The repository's operator-only `shared_host_transfer.py` is stricter than this
exercise: it freezes recognized writers, refuses active jobs, records table,
owner, ACL, metadata, cache, and dump hashes, restores in one transaction, and
verifies the result. That production-oriented path was inspected but not run.

## Edition namespace and persistence boundaries

The generated active-machine configuration passed the following local checks:

```json
{
  "status": "PASS",
  "containers": ["gateway", "v1", "v2", "v3", "v4", "v5", "v6", "v7"],
  "unique_ports": true,
  "pinned_images": true,
  "single_shared_volume": true,
  "config_sha256": "9211ff6b1f1377a9003bdefacecb870404f3c54a865f6a621b5f3cc296255be0"
}
```

`shared_host_config.py` accepts a contiguous immutable registry, exact registry
image digests, a fixed public origin, and a validated Fly volume ID. It generates
separate containers and local ports for the gateway and editions. The injected
entrypoint binds `/persist/<container>` to that container's `/data`, rejects
symlinks and unsafe ownership, unmounts the common `/persist` parent, and then
starts that image's original entrypoint. Each edition consequently starts its
own Unix-socket PostgreSQL cluster inside its fixed data subtree.

The gateway strips incoming cookies and forwards only the selected edition's
path-scoped session cookie. Edition ingress requires the shared gateway secret
for every application route except read-only health. Shared control endpoints
hold inference-budget and abuse-limit coordination; they do not merge Farm game
tables. These are meaningful application, process, and mount-namespace
boundaries, backed by repository tests and prior deployment evidence.

They are not independent availability domains. One Machine supplies compute,
network attachment, and lifecycle for every container; one volume contains all
fixed subtrees; one gateway routes every public edition. A Machine update can
restart all containers. Root in the host configuration can see the shared volume
before the per-container entrypoint removes that view. The checked-in legacy
per-app Fly TOML files describe the earlier topology and do not describe the
active shared Machine.

## Egress boundary

`scripts/serve.py` installs `services/api/egress.py` before importing and starting
the API. The hook wraps Python name resolution and installs a Python audit hook
for socket connects. It allows the fixed DeepSeek HTTPS destination, the
configured PostgreSQL destination or local Unix socket, and validated private
edition/control destinations for the relevant role. A fresh subprocess produced:

```json
{
  "status": "PASS",
  "undeclared_hostname_denied": true,
  "private_unix_database_allowed": true,
  "scope": "python_process_only"
}
```

This is process-level enforcement in the Python service. It does not configure a
host firewall, container network policy, Fly egress rule, security group, or
separate proxy. Native code or another process does not inherit this Python hook
merely because the web process installed it. No claim of OS-level denial is
supported by this review.

## Recovery and worker behavior

The runtime supervises PostgreSQL and web processes, uses Unix-socket-only
PostgreSQL, rejects an unexpected database major version, waits for readiness,
and performs bounded shutdown. Numerical jobs have explicit local recovery
paths; inference-bearing abandoned work is not silently repeated. Simulation
world mutations use tenant transactions, revisions, and durable idempotency
receipts. Those behaviors reduce duplicate work after application restarts, but
they do not replace database backup or host redundancy.

The following focused repository checks passed after the source review:

```text
29 passed in 0.46s
```

The set comprised `tests/deployment/test_shared_host_review.py`,
`tests/deployment/test_shared_transfer_operator.py`, and
`tests/security/test_process_egress.py`. These are local tests with mocked or
isolated boundaries. No public Fly state was read or changed.

## Work required to close OPS-01

Before an operational claim, define recovery-point and recovery-time objectives;
create an encrypted, access-controlled off-host backup; restore it into an
isolated environment using the production PostgreSQL major version; verify all
table, metadata, and required cache fingerprints; run application read/replay
checks; and document secure deletion. Repeat on a schedule and alert on missed or
unrestorable backups.

Separately enforce and test outbound destinations at the infrastructure or
container-network layer, including negative DNS/IP/IPv6 and subprocess probes.
Provision and fail over to an independent host and storage failure domain, then
measure gateway, database, worker, and in-flight idempotency behavior. Run bounded
sustained capacity and fault-injection tests. Until those steps pass, availability
and OS-level egress remain explicitly unproven.
