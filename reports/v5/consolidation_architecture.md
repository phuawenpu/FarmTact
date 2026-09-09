# Fly edition consolidation assessment

Assessment date: 2026-09-09 UTC  
Scope: read-only review of the five running Singapore Fly applications, measured
memory inventory, immutable edition registry, container build, boot supervisor,
gateway and publisher. No Machine, volume, dependency, service or application was
changed.

## Recommendation

**Retain the current per-edition Machine topology.** Fly offers no packing discount in
the supplied Singapore figures. A shared-cpu-2x/4 GB Machine costs $27.16, exactly the
price of two present shared-cpu-1x/2 GB Machines; a shared-cpu-4x/8 GB Machine costs
$54.32, exactly four. Their apparent 60% and 20% savings come from buying 60% and 20%
less total CPU/RAM respectively, not from consolidation. A shared-cpu-6x/12 GB
configuration is $81.47, effectively the same unit price as six current Machines at
$81.48 after rounding, before migration and rollback storage. It has one more CPU and
2 GB more RAM than today's allocation, so this is a pricing comparison rather than a
recommended size.

Consolidation would therefore trade physical isolation, independent failure domains and
simple immutable-image provenance for greater engineering cost without a like-for-like
infrastructure saving. Do not build or deploy the shared host for v5.

If lower spend becomes necessary, benchmark **right-sizing each existing Machine to 1 GB**
as a separate exercise. The supplied estimate is $36.15 total compute, retaining five
process/database failure domains. Current low-load use makes this a candidate for testing,
but the measurements do not cover numerical bursts. This assessment does not establish
that 1 GB is safe or authorize resizing production.

These are compute figures supplied from the current Singapore inventory. They exclude
volume storage, snapshots, outbound transfer and any taxes. During a cautious migration,
old volumes continue to incur storage cost until rollback retention ends. Fly bills
started Machines by their CPU/RAM configuration; its public pricing varies by region and
is documented at <https://fly.io/docs/about/pricing/>.

## What is running now

The inventory contains five started `shared-cpu-1x`, 2 GB Machines in `sin`: the public
gateway/control app plus private v1, v2, v3 and v4 apps. Gateway and v1–v3 each have an
attached 3 GB volume. V4 has an attached 1 GB volume and an unattached 3 GB volume, for
16 GB provisioned across the inventory.
The gateway and v1/v2 use image digest `6dcd…750b`; v3 uses `c71c…efb6`; v4 uses
`a676…6b92`. Thus v1 and v2 share an application payload but deliberately keep separate
databases and processes; v3 and v4 contain different backend/frontend source.

Low-load RSS summed across the five VMs is about 2.04 GB. Per-Machine measurements are:

| App | Total RSS | Python RSS | PostgreSQL RSS | Available RAM |
|---|---:|---:|---:|---:|
| Gateway/control | 358 MB | 197 MB | 135 MB | 1,634 MB |
| v1 | 398 MB | 209 MB | 163 MB | 1,608 MB |
| v2 | 426 MB | 243 MB | 158 MB | 1,587 MB |
| v3 | 426 MB | 240 MB | 161 MB | 1,589 MB |
| v4 | 429 MB | 241 MB | 163 MB | 1,588 MB |

RSS double-counts shared pages even within one VM and is not a direct prediction of
consolidated physical memory. A shared host would replace five PostgreSQL clusters with
one and could share interpreter/library pages, so it should use less than this sum at idle.
Conversely, this sample says nothing about concurrent CP-SAT calculations, Arrow/DuckDB
exports, uploads, browser streams, database maintenance or release startup. Four GB is a
plausible benchmark candidate, not a proven capacity.

The current `Dockerfile.fly` intentionally creates one source tree, one built frontend,
one Python environment and one PostgreSQL 18 server. `fly_boot.py` creates one database,
runs its migrations, starts one Uvicorn process and supervises it with PostgreSQL. The
edition gateway proxies each `/vN/` request to a distinct `farmtact-edition-vN.flycast`
host, strips cookies, maps the public cookie to an edition-specific cookie name, and
authenticates its private hop. The publisher creates an app, one private Machine, one
volume and deploys one pinned image digest. None of those components currently supports
multiple immutable payloads in one Machine.

Fly allows multiple processes, but process groups normally create separate Machines; they
do not make several image versions coexist inside one Machine. More decisively, a Fly
Machine can mount only one volume at a time. The official volume documentation states this
constraint at <https://fly.io/docs/volumes/overview/>. Therefore the five existing volumes
cannot simply be mounted into one VM. Consolidation requires a controlled logical database
migration onto one new volume.

## Runtime identity

The three distinct published source commits inspected were:

- v1/v2: `e9c3edfe10da162e4f50fd5a69df5a4394aa0812`
- v3: `f8e04999fba5a82dcb1435c7a4c920e004e76607`
- v4: `f1510825ab60ea0c70d0144d859bdf6266c1ac9d`

Across all three, `requirements.lock.txt`, `pyproject.toml`,
`apps/web/package-lock.json` and `Dockerfile.fly` are byte-identical. Representative
runtime pins include Python 3.13 base image, PostgreSQL 18, FastAPI 0.141.1, Uvicorn
0.52.4, Psycopg 3.3.5, DuckDB 1.5.5, PyArrow 25.0.1, NumPy 2.5.3, OR-Tools 9.15.6755,
Pillow 12.3.0 and the common npm lock.

That lock identity makes one shared Python dependency layer plausible for v1–v4. It does not
make their applications identical: backend and frontend tree hashes differ across those
commits. Running every URL from current `main` would overwrite edition behavior and violate
the registry’s source/image claims. Future releases may also change dependencies. The host
must treat each edition as a pinned artifact and fail publication when its runtime identity
is incompatible, or package a separate runtime for that edition.

Identical lock and Dockerfile bytes do not prove identical base layers. The Dockerfile uses
mutable tags (`node:24-bookworm-slim`, `python:3.13-slim-bookworm` and
`postgres:18-bookworm`) rather than OCI digests. V1/v2 have the same final image digest;
v3 and v4 have different final digests. Exact layer manifests, interpreter patch builds,
Debian packages and linked libraries were not inventoried here. A shared-runtime decision
requires exact OCI/base-layer and installed-runtime verification, followed by digest-pinned
builds.

## Concrete shared-host design, if future non-cost requirements justify it

No implementation is recommended from the present cost case. If a future operational
requirement makes a single host desirable despite the common failure domain, use one new
private edition-host Fly app/Machine and keep the public endpoint at the existing gateway
during a benchmark. A final consolidation could move the gateway into the same Machine
only after routing and rollback are proven.

The host image should contain:

1. A small, versioned supervisor and gateway payload, separately identified from every
   game edition.
2. Read-only application bundles under fixed paths such as
   `/app/editions/v1/<payload-hash>/`. Build each frontend from its registered source commit
   and copy that commit’s backend/config files. Record a manifest of source commit,
   dependency-lock hashes, frontend hash and backend hash. Verify it before startup.
3. One shared pinned Python environment only while the complete Python lock and base-runtime
   identity match. If a new edition differs, the publisher must either include an isolated
   virtual environment/interpreter for it or leave that edition on a separate Machine.
   Silent use of the newest dependencies is forbidden.
4. One PostgreSQL 18 cluster on the Machine’s single volume, with databases
   `farmtact_control`, `farmtact_v1`, `farmtact_v2`, and so on. Give every edition a unique
   database role; revoke cross-database `CONNECT`, schema and role membership. Current
   processes all use the same `farmtact` OS/database role, which is insufficient isolation
   inside one cluster.
5. One separately configured Uvicorn process per edition on loopback-only ports or Unix
   sockets. Each process starts from its own bundle, receives only its edition identifier,
   database URL, bounded control URL and required runtime secret, and writes no shared
   directory. Run migrations sequentially against the matching database before accepting
   traffic.
6. An explicit, registry-derived edition-to-socket map in the gateway. The current upstream
   validator only permits `.flycast` hosts; extend it with a second strictly enumerated
   local transport rather than accepting arbitrary URLs. Keep cookie rewriting, upload
   bounds, stream bounds, header stripping and the shared admission/control database.

Do not run editions as in-process FastAPI mounts. Python module caches and process-global
state—including audio-independent edition configuration, egress policy, stores, worker
queues and environment—would undermine version isolation. Separate OS processes create a
clear boundary and let one failed edition restart without importing another edition’s code.
Use distinct unprivileged UIDs if practical; otherwise `/proc` and filesystem permissions
need hardening because every process would share a VM and secret boundary.

The release registry needs two identities after consolidation:

- `payload`: immutable source commit plus application/frontend/runtime hashes that define
  what `/vN/` executes;
- `host`: the currently deployed supervisor/container digest and deployment identifier.

Existing `image_digest` values describe the images that currently execute those editions.
After migration, claiming those same image digests as the running host would be false.
Retain them as original publication evidence and append migration/host provenance; never
rewrite prior registry entries. A host update may change operational code without changing
an edition payload, but it must be independently versioned and regression-tested across all
published endpoints.

## Data migration and rollback

Because only one volume can attach to the new Machine, migrate with logical, edition-scoped
PostgreSQL dumps rather than filesystem copies:

1. Provision the candidate host and new encrypted volume without changing public routing.
2. Quiesce one source edition briefly, take a checksummed custom-format dump, resume it, and
   restore into the matching new database/role. Repeat for control, v1–v4. Copy only the
   documented per-edition public-data/cache paths; do not collapse them into a mutable
   global cache unless their content hashes and reuse rules permit it.
3. Compare table counts, immutable run/snapshot hashes, tenant/session boundaries and
   representative read-only API responses. Repeat a final delta/quiesced migration before
   cutover if writes occurred during the first copy.
4. Route one internal/canary hostname to the host, then switch the public gateway’s
   edition map atomically. Keep the old Machines stopped but not destroyed, and volumes
   attached or recoverable, for a declared rollback interval.
5. Rollback is a routing change back to the old private apps. Do not allow writes to both
   old and new databases after cutover; a rollback after new writes requires a reverse
   migration, not merely changing a hostname.

Adding v5 and later becomes a payload build, a new database/role, one supervised process
and an atomic registry/map update. The publisher must refuse a duplicate edition number,
payload mutation, incompatible shared runtime, failed migration or missing resource budget.
Eventually, retaining every old backend process forever will recreate memory growth inside
one VM. Set a capacity rule—for example, benchmark each added resident edition and move
incompatible or cold historical editions to a static/read-only archive where product
requirements allow. Do not silently make a playable edition static.

## Risk comparison

| Property | Current five Machines | One shared host |
|---|---|---|
| Compute estimate | $67.90/month for 5 CPU/10 GB total | $27.16 at 2 CPU/4 GB; $54.32 at 4 CPU/8 GB; $81.47 at 6 CPU/12 GB |
| Edition data | Physical volume/cluster separation | Logical database/role separation |
| Application code | One pinned image per edition | Multiple pinned bundles in one host image |
| Failure scope | Usually one edition | Gateway and every edition |
| CPU capacity | Five shared vCPUs across VMs | Two shared vCPUs total |
| Idle memory overhead | Five OS/PG stacks | One OS/PG stack, several API processes |
| Release operation | Create app/Machine/volume | Rebuild host, migrate one DB, restart or add process |
| Rollback | Edition-specific image/Machine | Host-wide unless old apps are retained |
| Security boundary | VM/app/volume | Process/role/filesystem within one VM |

The primary technical risk is CPU and failure-domain consolidation, not idle RAM. CP-SAT is
CPU-intensive, and four editions can currently calculate independently. A 2-vCPU host must
use the existing global admission service plus a host-wide numerical-work semaphore so a
burst cannot starve the gateway or PostgreSQL. Reserve one execution slot initially and
measure before allowing two. Provider-call budgeting remains global and must not be reset
by host restart or per-edition process failure.

The single volume and single PostgreSQL cluster are also a larger blast radius. Existing
topology is already single-Machine per edition, but one disk/database incident does not
currently remove every version. Consolidation should therefore include verified logical
dumps to storage outside that volume and a tested restore. Seven-day Fly snapshots are not
the same as an application-consistent multi-database restore test.

## Benchmark and cutover acceptance if the decision is revisited

Any 2x/4 GB capacity-reduction candidate is acceptable only if all of the following pass with copies of
production-sized databases and v1–v5 payloads:

- Idle resident memory remains below 2.5 GB after 30 minutes; under the worst permitted
  concurrent journey, peak memory remains below 3.4 GB, no swap thrash/OOM occurs, and at
  least 600 MB remains available. Measure cgroup memory, PostgreSQL, each edition and the
  supervisor, rather than summing RSS alone.
- Run simultaneous imports/exports, scenario calculations, a seven-agent council path,
  polling/SSE and asset loads across every edition. With a host-wide numerical concurrency
  cap of one, p95 cached/API latency stays below 500 ms, p95 static asset latency below
  250 ms, gateway health below 100 ms, and no request exceeds its existing deadline.
  Exercise council admission, budgeting, response size and persistence with the existing
  deterministic HTTP transport fixture and zero provider inference calls. Infrastructure
  benchmarking does not require live inference. Separately test two concurrent numerical
  jobs to quantify the queue/CPU tradeoff.
- A forced crash of each edition process restarts only that edition; gateway/control and
  other versions stay responsive. A failed migration prevents only the new payload from
  publication. A supervisor restart restores all processes without changing stored state
  or inference counters.
- Full browser journeys pass at 360, 390, 430 and 1280 px for every edition. Verify exact
  source/payload manifest, audio/art paths, CSP, cookies and API headers remain edition
  pinned. Cross-edition use of cookies, farm IDs, scenario IDs, snapshots and conversation
  IDs must return 401/404 without disclosing existence.
- Before/after table counts and content hashes match for farms, runs, scenarios, snapshots,
  branches, conversations, inference ledger, abuse counters and release registry. Replay
  makes no new provider call. Interrupted jobs reach the documented terminal/recoverable
  state rather than being silently lost.
- Deny every database role access to every other edition database in automated tests.
  Verify child environments contain no GitHub/Fly credentials, HTTP routes expose no
  environment or arbitrary file, and local upstream selection cannot be influenced by a
  request or registry text outside the signed/curated map.
- Perform a full restore of all databases and required cached data onto a blank candidate
  volume, then verify the restored host. Exercise routing rollback before allowing writes
  on the new host. Keep old volumes through the agreed rollback window.
- Soak for 24 hours with representative scheduled and interactive traffic. Zero OOMs,
  process restart loops, database corruption, unexplained 5xx responses or cross-edition
  records are permitted.

If any capacity criterion fails, a 4x/8 GB host may be tested only as a reliability
comparison. Its 20% lower bill buys 20% less aggregate capacity and is too small to
recommend production consolidation given the engineering and common-mode risk. A
capacity-equivalent host is slightly more expensive. The default outcome remains the
current topology.

## Decision

Stay with the five current Machines. No capacity/isolation benchmark has established that a
2x/4 GB shared host is safe, and its lower price buys proportionally fewer resources rather
than a packing discount. A 4x/8 GB host has the same property; the 6x/12 GB price confirms
the near-linear unit cost. Migration would add temporary storage and engineering cost.
Explore per-Machine right-sizing first if a cost reduction is required, subject to its own
benchmark. A future 2x/4 GB prototype remains an optional, separately bounded capacity
experiment within the user's conditional scope; it is not a proven production
configuration. Passing technical gates would not require another routine approval.

The immutable-edition promise could survive a future consolidation only through pinned
per-edition bundles, distinct processes, separate database roles/databases, append-only
migration provenance and tested rollback. A simple “route every `/vN/` into current main
and select a database” design must be rejected because it changes historical behavior and
makes the published image/source evidence inaccurate.
