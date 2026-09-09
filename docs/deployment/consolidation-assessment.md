# Fly consolidation assessment

Measured 2026-09-09 in Singapore (`sin`). Decision: **retain the existing topology**.
The assessment does not establish a safe net saving from consolidation. A smaller
shared host is a possible future downsizing experiment, not an approved sizing
result. No Machine, volume, routing, image or production state was changed.

## Current resource run rate

Read-only Fly inventory found five started shared-CPU Machines: the public
`farmtact` gateway and private `farmtact-edition-v1` through `v4`. Each has one
shared vCPU and 2 GB RAM. Total provisioned volume capacity is 16 GB, including
an unattached 3 GB v4 volume; its contents have not been established and it must
not be deleted based on this inventory alone.

Official Singapore pricing was read from the region-specific
`started-machines-pricing-matrix-sin` table, rather than the pricing page's default
region. USD estimates assume 30 days continuously started; they are resource run
rates, not an invoice or a claim about credits, taxes or existing reservations.

| Layout | Compute per 30 days | Existing volumes | Base total | Compute saving |
| --- | ---: | ---: | ---: | ---: |
| Current five × shared 1 vCPU / 2 GB | $67.90 | $2.40 | $70.30 | — |
| One shared 2 vCPU / 4 GB, if workload fits | $27.16 | $2.40 | $29.56* | $40.74 / 60% |
| One shared 4 vCPU / 8 GB | $54.32 | $2.40 | $56.72* | $13.58 / 20% |
| One shared 6 vCPU / 12 GB | $81.47 | $2.40 | $83.87* | −$13.57 |
| Current pattern plus separate v5 | $81.48 | At least $2.40 | At least $83.88 | — |

*Comparison retains current volumes for rollback. New consolidated storage and
stopped-Machine root filesystems add costs and must be included before deciding.
Volumes cost $0.15/GB/month whether attached or detached; stopped rootfs costs
$0.15/GB/month. Snapshot storage is $0.08/GB/month after the first 10 GB. Network,
inference, support, taxes and credits are excluded. Same-region internal traffic
is already free under granular rates, so do not count an invented network saving.

The lower-priced hosts also allocate fewer resources. Two vCPUs / 4 GB costs
exactly the same as two of today's Machines, and four vCPUs / 8 GB costs exactly
the same as four. Six separate 2 GB Machines cost $81.48 versus $81.47 for the
6-vCPU / 12-GB host, a rounding difference. There is no material consolidation
discount at those equal-capacity configurations. The $13.58 apparent saving
reduces aggregate allocation from five vCPUs / 10 GB to four vCPUs / 8 GB.

The 12 GB preset provides more capacity than today's allocation. A custom
6-vCPU / 10-GB size would be approximately $68.77 by interpolation between the
official 6-GB and 12-GB prices, still slightly above $67.90; this is an estimate,
not a separately quoted preset. Five independent 1-GB Machines would cost
$36.15, showing that downsizing can also save money without changing topology.
Neither that size nor the 4-GB shared candidate has been workload-validated, and
neither was applied.

Sources: [Fly resource pricing](https://fly.io/docs/about/pricing/),
[billing](https://fly.io/docs/about/billing/),
[CPU performance](https://fly.io/docs/machines/cpu-performance/),
[Machine sizing](https://fly.io/docs/machines/guides-examples/machine-sizing/).

## Capacity evidence and decision gate

A read-only light-load `/proc` sample found about 2.04 GB total process RSS across
all five Machines; each reported approximately 1.6 GB available memory. Summed
RSS double-counts shared PostgreSQL pages and is not peak memory. A 4 GB host is
a candidate, not a verified sizing recommendation. Shared vCPU quotas mean the
number of vCPUs is not equivalent to dedicated CPU capacity.

For any later reconsideration, consolidate only when the total retained-resource cost is lower and a bounded
benchmark shows capacity for concurrent numerical jobs plus normal browsing,
with memory headroom, no OOM/restarts and acceptable latency. Preserve exact old
code and dependencies, private data/cache directories, sessions, settings and
worker state per edition; preserve global operational admission/spending limits.
Different versions must not be imported into the same Python interpreter.

Before any cutover: establish immutable runtime packaging; test process/data
isolation; record active work; freeze writes during the final consistent copy;
back up every database and public-cache manifest; compare restored record hashes;
verify all endpoints and budgets; retain a rollback path. A shared host has one
failure/restart domain. Merely reducing the Machine count is not sufficient proof
that the change is more cost-effective. If the gates fail, retain the existing
layout and record why.

## Why retain the current layout

The shared host would require a new supervisor, exact pinned runtime packaging,
per-edition operating-system/database permissions, a consistent migration of all
databases and cache directories, and a recovery procedure for the combined host.
Identical dependency locks do not prove identical underlying image layers.
Separate Fly process groups would still create separate Machines and do not
implement the requested design. See the independent
[architecture assessment](../../reports/v5/consolidation_architecture.md).

Today's light-load memory evidence is insufficient to promise that reducing CPU
quotas and memory preserves simultaneous strategy-run performance. No concurrent
capacity benchmark or prototype has passed. We therefore preserve the current
working separation rather than assert that the cheapest hypothetical size is
sufficient. This is an evidence-limited decision, not a claim that consolidation
or right-sizing could never become worthwhile. Reassess when workload evidence
or the number of active editions materially changes.

The independent [capacity review](../../reports/v5/consolidation_capacity_review.md)
found one serial worker per edition and one solver thread per policy. Four
editions can therefore run four CPU-bound numerical jobs at once. A changed
scenario can perform six policy solves with four-second wall-time limits; the
browser baseline observed 22.6 seconds for one scenario. Moving those workers to
two shared vCPUs could reduce responsiveness or solution quality within the same
time limits. An 8-GB / four-vCPU host is a plausible benchmark candidate, but its
nominal $13.58/month saving has not been shown to cover the migration and ongoing
isolation complexity. No financial value has been invented for engineering time.

Read-only final checks: all four published health endpoints returned 200 and
their exact registered source commits; the public registry matched the repository.
No sessions or inference calls were created by the hosting assessment. Curated
inventory/prices/memory are in
[fly_cost_evidence.json](../../reports/v5/fly_cost_evidence.json), with checks in
[fly_readonly_checks.json](../../reports/v5/fly_readonly_checks.json).

## Post-v5 inventory update

V5 was subsequently published on 9 September 2026 using the retained topology.
Its one shared-vCPU/2GB Machine has one attached encrypted 3 GB volume, bringing
the total to six started Machines and 19 GB of provisioned volumes. The base run
rate is therefore $81.48 compute + $2.85 volumes = **$84.33 per 30 days** before the
other charges above. A single 6-vCPU / 12-GB shared host is quoted at $81.47 compute,
a one-cent rounding difference at equal allocated capacity, before migration,
new storage or retained rollback resources. The original comparison table remains
the inventory measured when only v1-v4 were published. No consolidation was made.
