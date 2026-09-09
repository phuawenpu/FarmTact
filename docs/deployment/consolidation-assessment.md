# Fly consolidation assessment — v6 completed

Updated 9 September 2026. Low simultaneous usage justified testing a smaller host.
The verified deployment now uses **one shared 4-vCPU/4-GB Machine and one 3-GB
volume** in Singapore, running the gateway and v1–v6 in isolated containers.

## Recorded cost comparison

The rollout's region-specific Fly pricing review used USD, 30 days continuously
started, excluding network, snapshots and other billable items. These are base
estimates, not an invoice or a guarantee of future prices.

| Layout | Compute | Volumes | Base total |
| --- | ---: | ---: | ---: |
| Previous six × shared 1 vCPU / 2 GB; 19 GB volumes | $81.48 | $2.85 | $84.33 |
| Active shared 4 vCPU / 4 GB; one 3 GB volume | $28.92 | $0.45 | $29.37 |

Estimated reduction: **$54.96/month, about 65%**. The saving comes from lower
resource allocation and removal of old volumes. Equal-capacity consolidation
showed essentially no compute discount in the earlier assessment.
Sources: [Fly pricing](https://fly.io/docs/about/pricing/) and
[Machine sizing](https://fly.io/docs/machines/guides-examples/machine-sizing/).

## Capacity, preservation and cleanup

Two fresh concurrent public v5/v6 numerical jobs completed in 21.803s and 21.847s,
with three feasible strategies each and zero inference calls. Browsing p95 was
0.1993s, available memory ended at 2603.5 MiB, and no swap was used. Cross-edition
cookies were rejected; main farms were unchanged. See
[public capacity evidence](../../reports/v6/shared_capacity_public.json).

Pinned OCI images remain separate processes and filesystems; fixed volume
subtrees isolate PostgreSQL, caches and saved state. Source/destination table,
metadata and cache fingerprints matched before traffic opened. After public
checks, six old Machines and seven old volumes were deleted as authorized.
Exactly one Machine and one volume remain in the FarmTact app allowlist;
unrelated apps were not touched. See [final inventory](../../reports/v6/fly_inventory_after.json)
and [transfer evidence](../../reports/v6/data_transfer.json).

One Machine is a single availability boundary. Migration included a controlled
write pause; future shared-host updates can briefly interrupt all editions.
The benchmark supports light concurrent use, not unlimited traffic or editions.
Reassess memory, storage and latency as usage grows. Old Fly volumes are no longer
a rollback option. Use the [edition runbook](editions.md) for publication.

The [original v5 assessment](../../reports/v5/consolidation_architecture.md) and
[capacity review](../../reports/v5/consolidation_capacity_review.md) remain
historical evidence. Their recommendation to retain separate Machines preceded
the user's low-concurrency clarification and the successful v6 benchmark.
