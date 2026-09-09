# Fly consolidation capacity review

Date: 2026-09-09 UTC  
Scope: read-only architecture and evidence assessment; no load generation or infrastructure changes

## Decision

Retain the current topology until a representative concurrent benchmark proves consolidation safe.

A single 2-shared-vCPU / 4 GB Machine is not justified by the present evidence. It would place four independently serial edition workers onto two shared vCPUs. The important scenario path is CPU-bound and already took 22.6 seconds without a measured cross-edition load. Two CPUs would permit at least 2:1 solver oversubscription before accounting for the gateway, four web servers and PostgreSQL work.

A single 4-shared-vCPU / 8 GB Machine is economically interesting but not yet operationally justified. At the supplied prices it reduces the current monthly estimate from $67.90 to $54.32, a saving of $13.58 or 20%. Four cores nominally match the maximum of four simultaneous single-threaded edition solvers. That is only a concurrency-count match: it does not demonstrate acceptable tail latency, memory headroom, failure isolation, edition isolation or database behavior.

The 6-vCPU / 12 GB option does not provide a cost reason to consolidate. Its supplied $81.47 estimate is effectively identical to six separate 2 GB Machines at $81.48, modulo rounding, while increasing the failure blast radius.

## What the runtime actually does

Each edition application starts one `Worker` thread. That worker loops through three durable queues in order:

1. planning missions;
2. numerical scenario branches;
3. conversation jobs.

The worker executes each claimed job synchronously. There is no `ThreadPoolExecutor`, `ProcessPoolExecutor`, configurable `max_workers`, or per-edition numerical parallelism. Pending jobs within one edition therefore queue behind one another, including conversations behind long numerical work. Restart recovery returns abandoned missions and scenarios to their queues.

The CP-SAT configuration uses a fixed seed and one search worker to reduce variability, but a wall-time-bounded optimizer is not guaranteed to return identical results under different CPU contention:

- `num_search_workers = 1`;
- `max_time_in_seconds = 4` for each policy solve;
- Lean, Balanced and Resilient are solved sequentially inside one `plan()` call.

One plan therefore has a configured CP-SAT ceiling of 12 seconds, excluding candidate construction, forecasts, simulations, validation, serialization and database writes. A changed scenario may calculate both its frozen baseline and changed result. Its configured solver ceiling is consequently 24 seconds. When the input and baseline hashes/settings match, it can copy the baseline and avoid the second plan; the worst configured changed-input path cannot rely on that shortcut.

The live V4 Busy Market branch changed demand to 130% and reached UI results in 22,557 ms. That observation is consistent with a two-plan path operating near the aggregate solver budget. It is one end-to-end sample, not a latency distribution and not a concurrency benchmark.

Main planning missions call `plan()` once before any optional council work. Council calls are network-bound and serialized within the same edition worker. The DeepSeek gateway itself caps inference concurrency at one per process. Those calls do not add CP-SAT threads, but a slow council can hold an edition's only worker and delay later numerical and conversation jobs.

## Worst configured overlap across four editions

Under the current four-edition topology, one Worker runs in each of V1, V2, V3 and V4. The maximum numerical overlap is therefore four CPU-bound jobs, one per edition. A representative worst case is four changed scenario branches arriving together:

| Component | Per edition | Across four editions |
|---|---:|---:|
| Active worker jobs | 1 | 4 |
| Simultaneous CP-SAT solvers | 1 | 4 |
| Solver threads | 1 | 4 |
| Sequential policy solves per plan | 3 | 12 |
| Plans per changed scenario | up to 2 | up to 8 |
| Configured CP-SAT wall-time limits per scenario | up to 24s | up to 96 aggregate solver wall-seconds |

The 96-second figure is the sum of configured solver wall-time limits, not a CPU-work budget. Actual CPU time can be lower under contention because each solve's clock continues while its thread waits or time-shares. On four uncontended cores, the four jobs could in principle remain near their individual latency. On two shared cores, solver threads must time-share and CPU search effort per job can fall; end-to-end latency needs measurement rather than a linear prediction. Contention can also reduce search work completed inside each four-second window and change solution quality, solver status or the returned timed result despite the fixed seed and single search worker.

Queue depth is not globally bounded to one job. Admission and idempotency limit abuse, and each tenant cannot have multiple active main planning runs, but scenarios and conversations are durable queues. A burst across tenants or editions can accumulate behind each edition's worker. Consolidation must preserve edition-level fairness so a busy historical edition cannot starve the current one.

## CPU assessment

### One 2-vCPU / 4 GB host

Reject for now. Four edition workers can simultaneously enter single-threaded CP-SAT, producing 2:1 numerical oversubscription. The same CPUs must also serve:

- the public edition gateway;
- four Uvicorn application processes if process isolation is preserved;
- PostgreSQL processes and checkpoints;
- JSON serialization, forecast generation and validation;
- static/API traffic and event streams.

The current Uvicorn limit of 64 concurrent requests is an admission ceiling, not compute capacity. It does not protect solver latency. A two-core host would need an explicit global numerical queue, prioritization/fairness and measured acceptable wait times. That changes runtime behavior and would require new edition-aware scheduling tests.

### One 4-vCPU / 8 GB host

Benchmark candidate, not an approved migration. Four cores match the four currently possible solver threads on paper. Shared Fly CPUs do not guarantee four dedicated cores, and web/database work still competes with them. Consolidation also removes the present natural containment: a runaway process, PostgreSQL fault, deploy failure or memory pressure could affect every edition and the chooser at once.

Before considering it equivalent, preserve at least one process and one database/schema boundary per edition, distinct edition cookies and storage, immutable source/image identity, and per-edition worker fairness. A single application-global queue without edition-aware scheduling could preserve state isolation while still creating cross-edition performance coupling.

## Memory assessment

The existing memory sample does not prove that 4 GB or 8 GB is sufficient.

The prior observation that each 2 GB Machine reported roughly 1.6 GB “available” is a point-in-time operating-system value, not process peak RSS. Available memory includes reclaimable cache. Summing per-Machine RSS or available memory would also mishandle PostgreSQL shared pages and filesystem cache. No evidence currently covers:

- concurrent peak RSS of four CP-SAT jobs;
- Python heap growth while four large results and snapshots are serialized;
- four PostgreSQL server footprints and page caches on one kernel;
- gateway/web connection buffers under concurrent browser traffic;
- DeepSeek response buffers during concurrent edition councils;
- allocator high-water behavior after repeated jobs;
- OOM behavior, swap pressure, restart recovery or volume I/O contention.

Eight GB may be ample, especially because the current idle samples imply low steady-state use, but that is an inference to test. Four GB is materially less credible because it combines five current service groups and multiple databases with no measured peak margin.

## Required benchmark before migration

Use a staging host with the proposed topology and production-equivalent process/database separation. Do not benchmark on the public editions or relax admission controls. Capture at least:

1. idle and steady-state RSS/PSS by process, PostgreSQL shared memory, page cache and total available memory;
2. one changed scenario alone, repeated enough to report median, p95 and maximum wall time;
3. four changed scenarios launched together, one per edition, each forcing baseline plus changed planning;
4. mixed load: four scenarios, normal bootstrap/static traffic, one event stream per edition and queued conversation jobs using a no-provider fixture;
5. queue wait separately from execution time;
6. CP-SAT wall time, status and objective/bound consistency under contention;
7. CPU utilization and steal time per process and host;
8. peak memory, OOM/restarts, PostgreSQL checkpoint/write latency and volume throughput;
9. edition fairness and unchanged state isolation after worker restart;
10. gateway availability while one edition is saturated or deliberately crashed.

Acceptance thresholds should be chosen before the run. A reasonable starting gate is: four-way p95 scenario latency no worse than 1.25 times isolated p95, no solver-status regression attributable to contention, gateway p95 remaining responsive, at least 25% memory headroom after reclaim-resistant working sets, zero OOM/restarts, and no cross-edition state or queue leakage.

Benchmark both 2-vCPU / 4 GB and 4-vCPU / 8 GB only if the smaller host remains a real purchasing candidate. The architecture makes the 2-vCPU result predictably weak; skipping it avoids spending engineering time to confirm obvious oversubscription. Focus the useful trial on 4-vCPU / 8 GB.

## Cost and risk conclusion

| Topology | Supplied monthly estimate | Capacity conclusion | Recommendation |
|---|---:|---|---|
| Current five separate 2 GB Machines | $67.90 | Known working topology; separate failure and worker domains | Retain pending benchmark |
| One 2-vCPU / 4 GB Machine | Not supplied | CPU oversubscribed at four-edition peak; memory unproven | Do not migrate |
| One 4-vCPU / 8 GB Machine | $54.32 | Plausible 20% saving; CPU and memory only nominally sufficient | Benchmark in staging |
| One 6-vCPU / 12 GB Machine | $81.47 | More headroom, larger blast radius, no material cost advantage | No cost-led migration |

The current topology costs $13.58 per month more than the plausible 4-vCPU consolidation candidate. That premium is presently buying measured working behavior, natural edition-level worker capacity and fault isolation. Until a four-way numerical and memory benchmark passes, retaining it is the more defensible and likely more cost-effective decision once migration engineering and outage risk are included.

## Source locations

- Worker scheduling: `services/api/app.py`, `services/api/scenarios.py`
- Main-run per-tenant active guard: `services/api/store.py`
- Solver configuration: `packages/planner/engine.py`
- Server concurrency: `scripts/serve.py`
- Bundled PostgreSQL supervision and 128 MB shared buffer: `scripts/fly_boot.py`
- Current Machine sizing: `config/releases/fly-v1.toml` through `fly-v4.toml`, plus `fly-gateway.toml`
- Live single-scenario timing: `reports/v5/business_browser.json`
- Prior point-in-time memory note: `docs/deployment/consolidation-assessment.md`
