# Fly consolidation assessment

Measured 2026-09-09 in Singapore (`sin`). Decision pending workload and runtime
isolation verification; production remains unchanged during assessment.

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
| Current pattern plus separate v5 | $81.48 | At least $2.40 | At least $83.88 | — |

*Comparison retains current volumes for rollback. New consolidated storage and
stopped-Machine root filesystems add costs and must be included before deciding.
Volumes cost $0.15/GB/month whether attached or detached; stopped rootfs costs
$0.15/GB/month. Snapshot storage is $0.08/GB/month after the first 10 GB. Network,
inference, support, taxes and credits are excluded. Same-region internal traffic
is already free under granular rates, so do not count an invented network saving.

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

Consolidate only when the total retained-resource cost is lower and a bounded
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
