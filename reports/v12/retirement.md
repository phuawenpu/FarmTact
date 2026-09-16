# V1–V10 retirement — 16 September 2026

Post-publication rolling cleanup initially remained pending because the installed
Fly CLI does not support `fly machine status --json`. The supported readback is
`fly machine list --app farmtact --json`; cleanup tooling now selects exactly one
row matching the configured Machine ID and rejects a missing or duplicated host
before inspecting its applied container configuration. No storage deletion was
attempted by the incompatible status command.

The next resume reached snapshot scheduling. This Fly CLI returned exit zero with
plain text (`Scheduled to snapshot volume …`) despite `--json`, rather than a
snapshot ID. The safe fallback now captures the completed-snapshot inventory
before scheduling and accepts only one newly completed, nonempty, digest-bearing,
recent snapshot absent from that baseline. It does not select an older snapshot;
a transient `running` alias cannot hide a valid completed row with the same ID,
and multiple new completed rows fail as ambiguous. The JSON-ID response remains
the preferred fast path. The newly scheduled recovery snapshot
`vs_GqKyy47KvAqmSAymJmBD38q8` was independently observed as `created` at
2026-09-16T15:12:22Z with positive size and digest before cleanup resumed.

V1–V10 application/database workers were removed from the shared Machine configuration.
The public active manifest is V11 only; the infrastructure V12 candidate remains
private and unlisted. V11 retains its exact image/source and independently mounted
state. Captured V11 record hashes passed after worker retirement.

A completed Fly volume snapshot `vs_7PORRqmOvDPGt1a37GGe0J4` preceded deletion.
The snapshot has seven-day retention; it is recovery evidence, not permanent archive.
Git commits, tags, release manifests and technical reports remain the durable history.

A service-less operator container inspected the shared volume. It received no
runtime secrets or public service. The verified plan named exactly V1–V10; active
V11, staged V12, gateway budgets/credentials and the volume itself were excluded.
The apply step rechecked checksums and runtime membership before removing those
tenants' edition subtrees. It removed no other directory. The operator is removed
after collecting its evidence.

The measured filesystem-used reduction during deletion was **694,558,720 bytes**
(662.38 MiB). Logical retired-file bytes totalled 691,787,851; filesystem accounting
includes allocation/metadata differences. Shared-volume used space fell from
900,390,912 to 205,832,192 bytes across the cleanup.

Before worker retirement, `/proc/meminfo` reported 1,913,200 kB available, and
load averages 6.51 / 6.36 / 6.81. The post-deletion reading reported 3,271,600 kB
available and 0.53 / 0.26 / 0.11. These are point-in-time readings across Machine
restarts, not a controlled performance comparison. CPU/load changes cannot be
attributed solely to cleanup. The operator's process count changed 3→2 during its
own commands; that is a container PID namespace, not host-wide process reduction.
The reliable application-container reduction is eleven published workers to one
retained published worker plus one private candidate. No pre-retirement host-wide
process count was successfully captured (`ps` was absent in the application image).

The Machine remains 4 shared vCPUs / 4096 MB and one 3-GB volume. No reduced hosting
bill is claimed. Fly manages image layers outside the mounted application volume;
no broad image prune or registry deletion was attempted. Historical image pins remain.
The available Fly tooling did not provide a verified exact-digest inventory and
reference/deletion boundary sufficient to prove that an artifact was unused by
every retained or staged container. Image cleanup remains blocked rather than
guessing from tags or broadly pruning the registry. Retirement-plan image rows
are advisory until a provider-supported exact inventory is available.

Public route checks: all ten retired GET and POST paths returned 410, without
redirecting mutation requests. Public listing contains only V11; V12 is 404 to
public routing. See the JSON inventory, preservation, snapshot and route evidence
in this directory. Final post-cleanup V11 verification is recorded separately.

Fly's managed Prometheus also supplied one-minute historical samples for the
retirement window. In 11 samples from 12:45–12:55 UTC versus 11 from 13:30–13:40,
mean active VM memory was approximately 936.6 MiB versus 235.5 MiB; mean available
memory was approximately 1868.9 MiB versus 3172.7 MiB. Mean one-minute load was
6.42 versus 0.58. These are VM-level gauges across different workloads and
restarts, not per-process RSS or a causal benchmark. The query and full samples
are in `host-metrics-retirement-window.json`; `host-metrics-summary.json` retains
the exact window means. Metric definitions follow the
[Fly monitoring documentation](https://fly.io/docs/monitoring/metrics/).
