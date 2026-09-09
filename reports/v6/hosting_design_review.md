# V6 single-Machine hosting design review

Review date: 2026-09-09 UTC. This review used current official Fly documentation,
the official `flyctl` v0.4.100 CLI in read-only mode, and the repository's published
edition registry and boot code. This reviewer did not create, update, stop, or deploy
a Fly resource. During the review, the root migration agent separately created a
private, service-less candidate in `appfarmtact`; the observed results supplied by
that agent are recorded below and do not constitute a public cutover.

## Finding

Fly now supports **multi-container Machines**. One Machine can run a `containers`
array under Pilot, with a distinct OCI image, environment, command/entrypoint/user,
files, restart/stop policy, health checks, dependencies, and mounts per container.
The containers share the Machine's kernel, VM resources, and network namespace,
but have isolated process trees and filesystems. This materially supersedes the
older repository assessment that a Machine necessarily has one application image.

Use this feature for the consolidation trial. It is the strongest available way
to preserve the exact published edition payloads: keep every registry entry's full
`registry.fly.io/farmtact@sha256:...` reference directly in the Machine config.
V1 and v2 may reference the same digest in two separately named containers; v3-v6
retain their distinct digests. Do not unpack or rebuild old images, and do not use
tags. A chroot/rootfs-bundle design is now an inferior fallback.

This does **not** preserve VM-level isolation. All containers compete inside one
4-shared-vCPU/4096-MB VM and a Machine restart or host failure affects every
edition. Fly explicitly says containers in a Machine provide less isolation than
separate VMs.

Official sources:

- [Multi-container Machines](https://fly.io/docs/machines/guides-examples/multi-container-machines/)
- [Machines API and Machine configuration](https://fly.io/docs/machines/api/machines-resource/)
- [Fly Volumes overview](https://fly.io/docs/volumes/overview/)
- [App configuration](https://fly.io/docs/reference/configuration/)

## FarmTact-specific compatibility

The current published images can coexist at the application layer. `scripts/serve.py`
uses `FARMTACT_PORT`, so assign unique loopback ports, for example gateway 8080 and
v1-v6 8101-8106. Fly documents that containers share one network namespace and can
reach each other on `localhost`; therefore the gateway should use explicit
`http://127.0.0.1:810N` upstreams. Only the gateway port 8080 should appear in the
Machine `services` configuration. Do not register or expose edition ports.

Each image's unchanged entrypoint also starts PostgreSQL 18, however, and hard-codes
its cluster to `/data/postgres` and Unix socket to `/tmp/farmtact-pg`. Filesystem
isolation keeps each container's `/tmp` distinct. The data path is the migration
constraint: every edition must see its own migrated tree at its own `/data`.

Fly Volumes remain app-owned, local to one host, and one volume can attach to only
one Machine. Existing volumes in six different apps cannot be attached directly to
the consolidated Machine or shared across apps. They must remain untouched for
rollback while consistent logical/filesystem copies are restored into new storage
owned by the consolidated app.

Current `fly-go` Machine types expose two different mechanisms:

- top-level `mounts` are persistent Fly Volume attachments;
- `volumes` referenced by a container's `mounts` are named `temp_dir` (ephemeral
  disk/memory) or OCI image-backed resources. They are not arbitrary existing Fly
  Volumes.

The public guide still says to attach a Fly Volume through the Machine's top-level
mount configuration, while also warning that Compose `volumes:` declarations are
ignored and ephemeral overlay data is wiped on restart/redeploy. It does not
document that one persistent Fly Volume can be mounted at different subdirectories
for different containers. Do not assume that behavior.

The selected storage design is one new encrypted persistent volume mounted into
the participating containers at a common path such as `/persist`, containing
`gateway/`, `v1/`, ..., `v6/`, with a startup wrapper bind-mounting only the matching
subdirectory onto `/data` before executing the image's original entrypoint. This
preserves each exact application image while changing only its launch configuration.

The root agent's private probe used Machine `2871575b4544d8`, four shared CPUs,
4096 MB, and new 3 GB volume `vol_vdejexpzm8ydn5x4`. Two containers using exact old
image digests both received the top-level `/persist` mount. In each container, a
root launch wrapper successfully bind-mounted `/persist/probe` onto `/data`, then
unmounted `/persist`; the logs recorded `bind_ok` and `unmount_ok`, and the parent
path was hidden afterward. This proves the required mount operations are available
in this Pilot configuration and supports distinct `/persist/<edition>` subtrees.
It does not yet prove restart persistence, production-data fidelity, or sibling
denial after privilege drop; retain those as cutover gates.

The wrapper has a short, privileged window in which the common parent exposes every
edition subtree. Keep the wrapper immutable and minimal: validate an allowlisted
container name-to-subdirectory mapping, reject symlinks and unexpected ownership,
bind the fixed directory to `/data`, unmount `/persist`, verify the parent is no
longer mounted/readable, then `exec` the original `/app/scripts/fly_entrypoint.sh`.
That entrypoint prepares fixed paths and uses `gosu` to run the supervisor as the
unprivileged `farmtact` user. Never accept an edition/path from a request or mutable
environment without validating it against the generated manifest. Because all old
images use the same UID, directory modes alone are not a sufficient boundary while
the parent remains mounted; hiding the parent in each container mount namespace is
the material control.

If the complete isolation test fails, build a tiny digest-pinned supervisor/storage
sidecar and run the old image's web process with a shared TCP PostgreSQL service and
explicit per-edition database/cache paths; that preserves image files but changes
more of the historical runtime and needs broader regression testing.

Secrets require special care. Fly's current multi-container guide states that
secrets set with `fly secrets` are global and available to every container in the
Machine; they cannot be scoped to a Compose service. The lower-level Machine schema
has per-container `secrets`, but no official page reviewed here establishes that it
can conceal app secrets from sibling containers, and all containers share a kernel.
Treat the shared Machine as one secret trust boundary. FarmTact currently uses the
same DeepSeek/control credentials across editions, so this can be acceptable only
if that is intentional. Supply values through Fly secrets or secret-backed files,
never config JSON, command arguments, build arguments, metadata, or logs.

## Concrete candidate Machine config

Generate this JSON from the immutable release registry. The file passed to
`fly machine run --machine-config` has `containers` at its root; a direct Machines
API POST wraps the same object in `{ "config": ... }`. The blueprint deliberately
uses placeholders for the not-yet-published v6 digest and for a separately pinned
gateway/supervisor image.

```json
{
  "guest": {"cpu_kind": "shared", "cpus": 4, "memory_mb": 4096},
  "metadata": {
    "farmtact-layout": "multi-container-v1",
    "farmtact-registry-hash": "<sha256-of-canonical-registry>"
  },
  "mounts": [
    {"volume": "<new-consolidated-volume-id>", "path": "/persist", "name": "farmtact_data"}
  ],
  "services": [
    {
      "protocol": "tcp",
      "internal_port": 8080,
      "autostop": "off",
      "autostart": true,
      "min_machines_running": 1,
      "ports": [
        {"port": 80, "handlers": ["http"], "force_https": true},
        {"port": 443, "handlers": ["tls", "http"]}
      ],
      "checks": [{"type": "http", "port": 8080, "method": "GET", "path": "/api/v1/health", "interval": "30s", "timeout": "5s", "grace_period": "90s"}]
    }
  ],
  "containers": [
    {
      "name": "gateway",
      "image": "registry.fly.io/farmtact@sha256:<gateway-supervisor-digest>",
      "env": {"FARMTACT_ROLE": "gateway", "FARMTACT_PORT": "8080", "FARMTACT_DATA_ROOT": "/persist/gateway"},
      "healthchecks": [{"name": "gateway", "http": {"port": 8080, "method": "GET", "path": "/api/v1/health", "scheme": "http"}, "interval": 10, "timeout": 5, "grace_period": 60, "success_threshold": 1, "failure_threshold": 3}]
    },
    {
      "name": "v1",
      "image": "registry.fly.io/farmtact@sha256:6dcd86da3a282935c6fc595e36ca8ac140050b23d5ba9480903759d38f8c750b",
      "env": {"FARMTACT_EDITION": "v1", "FARMTACT_PORT": "8101", "FARMTACT_PUBLIC_ORIGIN": "https://farmtact.fly.dev", "FARMTACT_EXECUTION_MODE": "test", "FARMTACT_DATA_MODE": "synthetic_demo", "FARMTACT_SECURE_COOKIES": "true", "FARMTACT_TRUST_FLY_PROXY": "true"},
      "healthchecks": [{"name": "v1", "http": {"port": 8101, "method": "GET", "path": "/api/v1/health", "scheme": "http"}, "interval": 10, "timeout": 5, "grace_period": 60, "success_threshold": 1, "failure_threshold": 3}]
    }
  ]
}
```

Repeat the v1 object for v2-v6, changing name, edition, port and exact registry
digest. V2 deliberately repeats v1's digest. Add `depends_on` only when the chosen
gateway implementation truly needs all editions healthy before it starts; otherwise
one broken historical edition would prevent the public chooser from serving.

The JSON above omits the small wrapper expression for readability. The private probe
has established that it can be expressed as a root `entrypoint`/`exec` override and
then hand off to the unchanged old-image entrypoint. Generate one fixed wrapper per
container or one wrapper with a strictly allowlisted name/path manifest. Do not
launch with one common writable `/data`, because all PostgreSQL clusters would target
the same directory.

## Publication, migration, and rollback sequence

1. Freeze the candidate registry and compute a canonical registry hash. Resolve
   every container image to a full digest already recorded by `/api/releases`;
   reject tags, missing digests, digest substitutions, and a v6 source/image pair
   that has not completed the immutable publisher checks.
2. Inventory each old Machine's reported `config.image`, OCI revision/health source
   commit, volume ID, and database/cache manifest. Require equality with the
   registry. Store the generated Machine config and its hash as release evidence.
3. Create a new app/volume and a **cordoned or otherwise non-public candidate
   Machine**. The Machines API documents `skip_service_registration` specifically
   for starting and validating a green Machine before uncordoning it. Do not mutate
   the existing public Machine for the first trial.
4. Complete the storage-wrapper validation beyond the successful bind/unmount probe:
   restart and Machine-update persistence; correct per-container `/data`; inability
   to traverse, remount, read, or write sibling data after privilege drop; unique
   ports; independent health; termination behavior; and no secret values in
   config/status/logs. Fail closed if any unprivileged sibling can access another
   tree or if the common parent remains visible.
5. Quiesce writes and workers in the old apps. Take consistent PostgreSQL backups
   plus public-data/cache/session manifests. Restore each edition to its own target
   and compare row counts and cryptographic hashes before permitting traffic.
6. Run health/source-commit probes for gateway and every edition, `/api/releases`,
   cookie/session isolation, replay, one numerical job, two overlapping jobs, and
   repeated-job memory. Observe peak RSS, OOM/restarts, CPU throttling and latency.
   Keep actual farm operations disabled.
7. Cut over atomically at the gateway/routing layer only after all checks pass.
   Preserve old apps, Machines, volumes, secrets and registry unchanged and stopped
   only after cutover confidence. Do not delete them during the rollback window.
8. Roll back by routing to/restarting the original gateway and private edition
   Machines. If consolidated writes occurred, freeze first and explicitly reconcile
   them before rollback; blindly returning to stale old volumes loses new sessions
   and runs. Document the point-in-time decision.

Machine update is a whole-Machine failure domain. Adding v7 or changing one container
can restart/replace the host and interrupt every edition. Use a generated full config,
an exclusive Machine lease/current-version guard, immutable digests, and a preflight
diff. Fly documents leases for exclusive modification and cordon/un-cordon for
blue/green routing. A second temporary candidate Machine requires its own persistent
volume and a consistent restore because Fly Volumes are one-to-one with Machines.

## Chroot/rootfs bundle fallback

Do not choose chroot bundles while multi-container support is available. Extracting
OCI root filesystems into a supervisor image loses direct platform-level digest
identity, requires preserving image config (entrypoint, command, user, environment,
ownership, modes, links and whiteouts), and shares the host kernel/process controls
with weaker filesystem isolation unless mount namespaces are built correctly. It
also makes vulnerability and provenance review harder: the running Machine reports
the wrapper image rather than every historical digest.

If forced to use it, fetch manifests by digest, verify every manifest/blob digest,
apply OCI layers including whiteouts into read-only per-edition roots, record the
ordered manifest and config digests, create separate mount/PID/user namespaces,
provide only that edition's data bind mount, drop privileges/capabilities, assign
unique loopback ports, and reproduce the OCI image's configured entrypoint/user/env.
This is more custom security-sensitive code than Pilot and should require the same
behavioral, data-isolation, restart, provenance and rollback gates above.

## Decision

Proceed with the private multi-container candidate based on exact published image
digests. The successful bind/unmount probe removes the immediate `/data` feasibility
block, and multi-container support removes the largest code-provenance objection to
a single Machine. Production cutover remains conditional on full sibling isolation,
restart persistence, secret-boundary acceptance, complete state restore/hash
comparison, and the specified 4-vCPU/4-GB workload benchmark. If any of these fails,
do not expose a shared writable `/data`; retain the old Machines while correcting the
design or implementing the shared-database/storage-sidecar alternative.

## Implementation review addendum

The uncommitted `scripts/shared_host_config.py` preserves each registry image digest,
assigns a bounded unique port, projects only secret names per container, embeds the
append-only registry, exposes only gateway port 8080, and hands each container to
an absolute adapter path. `scripts/shared_container_entrypoint.py` binds the fixed
subtree, hides `/persist`, installs loopback `.flycast` aliases, then executes the
original absolute image entrypoint; the original script establishes its own `/app`
working directory through `fly_boot.py`'s source-derived `ROOT`, so inherited cwd is
not a boot dependency. The local control Host and loopback-client checks match the
generated alias and URL.

Two corrections are required before public use:

1. Registry installation currently performs privileged `Path.read_text()` and
   `Path.write_text()` on predictable paths in a persistent tree previously writable
   by the application user. A planted `registry.json` or `registry.json.next` symlink
   could be followed as root on reboot. Require a root-owned, non-group/world-writable
   releases directory; reject symlinks and unexpected files with `lstat`; create the
   temporary file using `O_CREAT|O_EXCL|O_NOFOLLOW` mode 0600; flush it and atomically
   replace the manifest; then fsync the directory. Apply equivalent no-follow logic
   to the target-subtree checks where practical.
2. The public Machine service's port 80 entry omits `force_https: true`, even though
   the official Machine port schema supports it and the existing deployment requires
   HTTPS. Add it at the Fly Proxy boundary rather than relying solely on application
   middleware and forwarded headers.

Independent bounded tests are in
`tests/deployment/test_shared_host_review.py`; the initial 13 passed. They cover exact
registry-image retention, the 4-shared-CPU/4096-MB bound, one persistent mount,
bounded namespaces, fixed ports/aliases/control URLs, rejection of tags and foreign
images, per-container secret-name projection, no secret values in ordinary env,
and the absolute no-shell handoff to the historical entrypoint.

### Fix verification and transfer-helper review

Both required corrections were subsequently verified. Port 80 now has
`force_https: true`. Registry installation now requires a protected root-owned
release directory and manifest, rejects symlinks, creates the pending file with
`O_EXCL|O_NOFOLLOW`, fsyncs file content, atomically replaces the manifest, and
fsyncs the directory. Before migrating the gateway tree, ensure its existing
`/data/releases` directory and registry are root-owned and not group/world writable;
the adapter correctly fails closed otherwise.

The operator-only `scripts/shared_host_transfer.py` uses the local PostgreSQL Unix
socket, fixed `/data/shared-transfer` paths, no HTTP endpoint, and refuses root.
Restore additionally requires the private candidate origin
`http://127.0.0.1:8088` and a deployment container identity. Keep the candidate
service-less and invoke the helper as `farmtact` through authenticated container
SSH. Official Fly networking documentation explains the failed external private
probe: direct 6PN needs the process bound to `fly-local-6pn`, while FarmTact binds
IPv4 `0.0.0.0`; Fly Proxy would require a service definition. An empty-ports
service is not a documented safe bridge, and adding a routable service inside the
existing public `farmtact` app can expose or load-balance the candidate prematurely.

For capacity browsing only, the private config now adds a fixed temporary relay
bound to `fly-local-6pn:8080`, forwarding bytes only to `127.0.0.1:8080`. It has no
Fly `services`, dynamic destination, file route, or configuration endpoint. Its
bootstrap unmounts `/persist`, verifies the common volume is hidden, clears its
environment, drops supplementary groups/GID/UID to `farmtact`, and only then opens
the IPv6-only listener. The public config omits the relay entirely. This provides
private 6PN access without registering the candidate with the public Fly Proxy;
it remains organization-network reachable and must remain temporary and excluded
from the production config.

The helper now verifies that its recorded database matches and every recorded
service PID is still an expected stopped process before export or restore. Database
connections and dump/restore operations have bounded timeouts. It hashes the dump,
preflights every cache member and file payload before `pg_restore` or cache deletion,
rejects traversal and all non-file/non-directory members, extracts with Python's
`data` filter, and compares every public-table row fingerprint and cache byte after
restore. These controls address stale freeze markers, partial destructive restore,
and archive confinement.

PostgreSQL source and destination are initialized by the same exact image as the
same `farmtact` database superuser, so archived ownership and ACL restoration should
resolve to that role. Before cutover, explicitly query `pg_class`, `pg_proc`, and
schemas after restore to confirm all application tables, sequences, functions and
the public schema have the expected owner and no unexpected grants. Cache extraction
runs as `farmtact`, so restored regular files receive the runtime owner; confirm no
special files, symlinks, hardlinks, unexpected paths, or group/world-writable modes.
The post-restore fingerprints cover public table rows and cache bytes, while this
ownership/privilege check covers metadata those hashes intentionally omit.

The independent deployment test file now has 15 passing tests, including the two
fixes, transfer preflight-before-destruction ordering, archive constraints, current
stopped-process validation, and bounded database operations.

The final transfer identity issue was corrected: evidence now includes the fixed
container identity and `/app/config/build-source.txt` commit, and restore/verify
requires exact equality. This distinguishes v1 and v2 even though their source and
image are intentionally identical, and prevents a valid `farmtact` dump from being
restored into the wrong edition. Database metadata hashing now covers table/sequence
owners and ACLs, public-schema ownership/ACLs, public function definitions/owners/
ACLs, and database owner/ACLs in addition to row fingerprints. Transfer only
`database.dump`, `fingerprint.json`, and `cache.tar.gz`; never copy the source
`frozen.json`, because the candidate must create and validate its own stopped PID
record. The latest test expansion has 16 passing checks and verifies that the relay
exists only in the service-less private config, unmounts shared storage, drops
privilege, uses an IPv6-only fixed listener, and is absent from public production.

### Shared publication workflow review

The shared-host publisher preserves the publication boundary. When the deployment-
owned shared settings file exists, it generates a complete public Machine config
from the previous public registry plus exactly one new immutable entry and updates
only the pinned Machine ID. Production generation omits the private relay, restores
proxy trust, retains exact image digests, and adds the new container on its unique
loopback port.

The adapter validates that every existing on-volume registry edition is an immutable
prefix of the incoming registry, but seeds the incoming registry only when a
container's manifest is missing. Thus existing gateway state remains on the old
public registry across the Machine update, while the new edition's private subtree
can initialize. The publisher then uses authenticated SSH into the pinned gateway
container to probe the new unique localhost port and require its registered source
commit. Only after this succeeds does it upload a pending registry and atomically
replace the gateway registry with a validator that requires the previous editions
unchanged and exactly one appended entry. A failure before the replace leaves the
new container unreachable through the public chooser and can be retried with the
reserved identity.

The final hardening points were applied: the shared settings object must contain
exactly `app`, `machine_id`, and `volume_id`, rejecting ignored extra fields. The
health probe now requires `status == "ok"`, the exact edition ID, and the exact
source commit on the unique new port.

Independent tests now cover the public/private proxy-trust split, production relay
exclusion, exact Machine update and image selection, unique localhost source probe,
seed-only registry behavior, immutable-prefix check, and atomic publication through
the pinned gateway container. The combined shared-host and existing publisher test
selection completed with 29 passing tests.
