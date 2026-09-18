# Publishing immutable editions

## Current-game publication policy

V20 restores the V12 farmer workspace at `/` and `/play`, from
`6054b6f5a4dba6ba77a9090d2141c0c45fc045db`. The experience is explicitly selected
in the entry point, independently of the immutable edition identity. V19 and
previous source/image/data remain privately retained. V21 is the separate small
UX follow-up; V12 remains its product baseline. Always inspect the current registry
before choosing the next edition number.

V15 replaces the historical first-season introduction with the same full card
application at `/` and `/play`. From V14 onward the active
manifest has `previous: null`; edition numbers remain immutable operational
identities, not player navigation. Old public routes return a retirement notice
linking to `/`. Public release-list/history APIs are unavailable in current-game
mode; authenticated operator tooling reads the retained private manifests.

Stage the exact next image privately and verify its numerical/browser journey.
After atomic activation and current-game checks, stop older application workers.
Take a recovery snapshot and retain retired data subtrees; do not apply historical
destructive retirement cleanup to this scope. Historical source/image manifests and
archived state are not rewritten or automatically migrated into the new season.
The shared inference budget and abuse counters survive cutover. Cookie names and
browser progress remain release-specific even though the public URL is unversioned.

V14 hosting follow-up: the current gateway health route proxies the current
application. Configure the container/public HTTP probes with the fixed
`Fly-Client-IP: 127.0.0.1` health-probe header, and make the edition depend on gateway
`started`, not `healthy`, to avoid a readiness cycle. Keep actual HTTP readiness
checks for both components. Fly updates may merge omitted fields; inspect the
applied configuration and live check results, not only the generated JSON. These
are host metadata changes and do not replace the immutable application image.

The procedures below describe earlier pair-based releases unless explicitly updated
for this policy. Use the publisher's current validation and the checked-in registry
to determine the next number; do not infer it from historical examples.

## Active editions and immutable history

`config/releases/registry.json` is the append-only publication ledger. It keeps
every edition number, source commit, pinned image and release evidence. Runtime
routing is controlled separately by `config/releases/active.json`, whose complete
shape is `{"previous": "vN", "latest": "vN+1"}`. `previous` may be null before
the next edition is published. The chooser and `/api/releases` expose only this
active set; `/api/releases/history` exposes the immutable ledger.

Published routes outside the active set return 410 for reads and mutations and
list the available editions. Unknown edition numbers return 404. Shared control
admission accepts only active editions plus the exact explicitly staged next
number. Backend ingress repeats that check, so a retired worker cannot accept
authenticated forwarded mutations if it was accidentally left running.

Generic local tooling follows the same boundary. `serve_editions_local.py`
starts and maps only `active.json` editions by default, with an optional exact
next `FARMTACT_STAGED_EDITION`; asking it to run a historical retired worker is
an error. `verify_editions.py` derives its one- or two-edition journey from
`/api/releases`, verifies the full append-only ledger separately through
`/api/releases/history`, and checks both read and mutation routes for a retired
edition return 410. Version-specific historical release evidence scripts remain
frozen and are not runtime inventory.

Candidate staging keeps the active manifest unchanged and adds the next pinned
worker for private acceptance checks. It also updates the gateway to the candidate
image while retaining its shared control database and V14 public routing. Capture
shared budget/abuse preservation evidence before staging as well as after cutover. Publication updates the Machine to
the intended pair, verifies the candidate, then replaces history and active
manifests together. A failed candidate leaves the public pair unchanged. Edition
numbers always follow the history ledger and are never reused.

After recording a recovery snapshot, `scripts/retire_editions.py` inventories
direct `vN` storage children and reports checksums, disk use, memory, load,
process count and image references. It defaults to dry run. Apply mode requires a
snapshot identifier, protects active and staged editions plus gateway/control
paths, requires the current Machine container set, rejects symlinks, and rereads
the active manifest and target checksums immediately before deletion. It
never removes the shared volume. Image rows are candidates only; prove a digest
is unused by every retained container before removing it.

Each numbered edition remains a frozen source commit and image digest. The gateway
and only the active edition set run in separate containers on one Singapore Fly
Machine (4 shared vCPUs, 4096 MB) and one encrypted 3-GB
`farmtact_shared_data` volume. Retained editions keep fixed, isolated database,
cache, settings and progress subtrees. The public gateway owns the chooser,
active release API, shared 48-call inference budget and abuse counters. Actual
farm operations remain disabled.

The publisher never resolves an image tag. You may supply a previously verified `sha256` digest. When `--image` is omitted, it runs the fixed gateway Fly build with `--build-only --push --remote-only`, labels it from the edition and short source hash, passes the full source commit as a build argument, and accepts only the pinned registry digest reported by Fly. Commit the complete candidate source first. The publisher rejects dirty worktrees, abbreviated commits, non-HEAD commits, mutable image references, skipped edition numbers, changes to existing registry entries, and reuse of a locally reserved number with different inputs.

Prepare a notes file containing exactly `title`, `summary`, and `changes`. Each change contains `title`, `description`, `feedback_ids`, and `evidence`. Then validate without Fly mutations:

```bash
.venv/bin/python -m scripts.publish_edition \
  --edition v12 \
  --notes /absolute/private/path/v12-notes.json \
  --image registry.fly.io/farmtact@sha256:<64-hex-digest> \
  --source-commit "$(git rev-parse HEAD)" \
  --dry-run
```

Omit `--image` to use the fixed build-and-push path. Run without `--dry-run` to publish. A dry run performs validation without reserving the number or changing `.git`. The active shared-host publisher performs these steps:

1. Requires a clean, committed source and the next contiguous edition number.
2. Reserves that edition/source/image identity under `.git` to prevent reuse.
3. Builds or accepts the pinned OCI digest, then regenerates the shared Machine
   configuration with the retained active container(s) plus the staged edition.
4. Updates the exact Machine in `config/hosting/shared.json`, reusing its volume
   and existing runtime secrets. It checks the new edition's health, ID and full
   source commit through authenticated operator SSH.
5. Keeps the previous public pair during startup, then atomically replaces one
   validated public bundle containing the appended history and new active pair.
   Compatibility copies of `registry.json` and `active.json` are refreshed only
   after that cutover point.
6. Mirrors the registry and release manifest, commits them, tags the frozen
   source as `farmtact-vN`, and pushes the commit and tag.
7. Regenerates the Machine from the new active pair, which stops the displaced
   oldest worker; creates a Fly recovery snapshot and polls the bounded snapshot
   inventory until Fly reports `created`/`complete`; starts the service-less,
   secret-free retirement operator; and applies checksum-guarded cleanup using
   `public.json` as the authoritative history/active bundle. It then removes the
   operator and re-probes the latest worker. A failed, unknown, or still-pending
   snapshot prevents every storage deletion. The cleanup report remains under
   `gateway/releases/retirement-vN.json` on the shared volume.

If post-cutover cleanup fails, publication remains valid and its local reservation
is marked `published_cleanup_pending`. The operator is deliberately left in the
Machine configuration for inspection; active and staged storage remains protected.
After correcting the external failure, resume the same idempotent cleanup without
republishing or allocating another edition number:

```bash
.venv/bin/python -m scripts.publish_edition --resume-cleanup
```

Resume reads the current public pair and immutable history from the gateway,
removes workers outside that pair, records a new recovery snapshot, and rechecks
the authoritative public bundle and current container set at the deletion
boundary. Missing retired directories are treated as already complete. A failed
candidate before atomic cutover never enters this cleanup path and leaves the
existing public pair unchanged.

The current next unused number is v15; always check the registry before publishing.
The V12 command examples below document its completed rollout; substitute the next
unused edition for future publication.
The legacy separate-app provisioning path remains for environments without a
shared-host record. Do not remove that record to publish on this deployment.
No credential values enter generated configuration, command output or manifests.
Publication performs no inference calls.

Long release work must still follow the project’s 20-minute Git push cadence: keep implementation and verification commits pushed before starting publication. The publisher makes and pushes the final registry/manifests commit and immutable source tag after the live registry swap.

If a step fails, inspect the reported Fly command and rerun with the same edition,
source commit, and digest after repairing the external state. Do not delete the
`.git/farmtact-publications.json` reservation or choose a different build under
the same number. Check `/api/releases` and `/api/releases/history`: if the atomic
`public.json` cutover occurred, treat that pair/history as published and repair
only the compatibility copies. If it did not occur, the prior public pair remains
authoritative. Never construct a mixed history/active rollback.

The gateway refreshes its validated destinations and control edition allowlist after atomic publication. Updating the shared Machine can restart the gateway and all edition containers.


## Active shared-host deployment (v10)

The verified deployment uses one 4-shared-vCPU/4-GB Machine with one persistent volume.
The public chooser and at most two active editions run in separate containers,
each with its registered exact OCI image. Historical releases remain in Git and
release evidence without consuming a running worker. A deployment adapter binds only the
edition's fixed volume subtree to /data, removes the common parent, and hands off
to the original image entrypoint. Application code and source/image pins are not
rewritten. Each image keeps its own PostgreSQL cluster, cache, worker and session
state; the gateway retains the existing shared operational budgets.

config/hosting/shared.json records the verified host. publish_edition.py
updates that Machine instead of creating another app/Machine/volume. It starts
the next exact-image container, checks health/source/edition over operator SSH,
then atomically appends the public registry. Restarts preserve the last published
registry; they do not expose a pending edition. A new container uses another
subtree of the same volume. This may require a brief shared-host restart.

The private capacity relay uses no Fly public service, hides storage and drops
privileges. It is excluded from production configurations. Private tests use the
actual local peer address; production keeps Fly's trusted client-address checks.
Migration and cleanup are complete: six superseded FarmTact Machines and seven
old volumes were deleted after verification. Exactly one Machine and one shared
volume remain. Unrelated resources were untouched. See
[final inventory](../../reports/v6/fly_inventory_after.json).

Public capacity evidence: two fresh concurrent v5/v6 numerical scenarios finished
in 21.803s and 21.847s, read p95 was 0.1993s, and 2603.5 MiB remained available. This validates light concurrent use, not arbitrary scale. Archived V6 Singapore planning estimate: $28.92 compute + $0.45 volume =
$29.37 per 30-day month, excluding other billable items. This audit did not refresh
pricing or inspect an invoice. One host is one availability boundary; deployments may
briefly interrupt all editions. Reassess memory before accumulating many more
editions. See [capacity](../../reports/v6/shared_capacity_public.json) and
[transfer evidence](../../reports/v6/data_transfer.json).

Use the immutable publisher for new app releases. Do not run a generic
`fly deploy` against this shared host: root fly.toml is retained for image
building and historical bootstrap, and does not describe the active containers.
To regenerate the V11-only configuration before staging V12:

```bash
python scripts/shared_host_config.py --registry config/releases/registry.json \
  --active config/releases/active.json \
  --volume vol_vdejexpzm8ydn5x4 --public --output /tmp/farmtact-shared.json
fly machine update 2871575b4544d8 -a farmtact \
  --machine-config /tmp/farmtact-shared.json --yes
```

The one-time migration tools preserve full database rows/owners/ACLs and cached
bytes; their source Machine allowlist becomes historical after cleanup. They
are not a routine deployment step. Never run their restore action on production.

V7 publication used the same Machine and volume, adding its isolated subtree and
pinned container. Invoke the publisher as a module (`python -m scripts.publish_edition`)
from the repository root so its shared-host helper imports resolve. The first v7
file-style invocation built and reserved the image, then stopped before deployment
on a module-path error. Retrying as a module reused the same reserved source and
digest; it did not rebuild or reuse a number for different contents.

The post-publication operator correction also makes file-style execution resolve
the same helper module. An isolated subprocess regression and the deployment /
publisher suite pass 48 tests. This changes development tooling only; the v7
application retains its frozen source and image.

V7 public capacity verification: overlapping fresh v6/v7 numerical jobs completed
in about 22 seconds each, browsing p95 0.2053 seconds, at least 2.34 GiB available
memory in sampled readings, no inference or main-farm changes, and cross-edition
cookie rejection. This bounded smoke test supports retaining the current size;
it does not establish capacity under sustained load. See
[the v7 capacity report](../../reports/v7/shared_capacity_public.json).

## V8 publication evidence — 11 September 2026

V8 is published at [the immutable v8 application](https://farmtact.fly.dev/v8/),
from source `a00e546b1270a5c532e8eae6b8b64e568c344c13` and image
`sha256:8ed6fc3b1a6632f88bbc2b6a20b200b44bba13d7583c70f40e1c31f85c1e8357`.
The first machine-update command exited unsuccessfully before publication; its
underlying stderr was not retained. A retry with the same reserved source and
digest completed successfully. No alternate v8 image was built or substituted.

All eight public edition health endpoints match their recorded source commits,
and the live registry equals the append-only Git registry. The before/after
preservation audit covers the seven prior editions, their source hashes and all
existing tables in the expanded state/event/research snapshot allowlist. It
passed before new capacity-test sessions were created. See
[health evidence](../../reports/v8/deployment-health.json) and
[preservation evidence](../../reports/v8/preservation-after.json).

## V9 publication evidence — 11 September 2026

V9 is published at [the immutable v9 application](https://farmtact.fly.dev/v9/),
from source `89d29cc3e071e12373204ff234d0a261ce71b5a1` and image
`registry.fly.io/farmtact@sha256:42702ca38566d87c359ae2f92f924b403dbf8fb2ae8166f5377cc829e8d725e4`.
The append-only registry publication commit is
`6731992757ffb0dd219696b219ca3e7f304a238b`.

All nine public edition health endpoints matched their registered edition and
full source commit, and the live registry matched the Git registry. The v1–v8
source and state preservation audit passed. See
[health evidence](../../reports/v9/deployment-health.json) and
[preservation evidence](../../reports/v9/preservation-after.json). Publication
made no inference calls. These checks establish source identity, availability and
edition isolation. The separate V9 provider-backed trial used 21 actual requests
and failed its quality gate: 12 of 18 automated cases passed while workflow
integrity passed, and a scorer-missed false-fulfilment claim independently prevents
acceptance. V10 is the published remediation edition.

## V10 publication evidence — 11 September 2026

V10 is published at [the immutable v10 application](https://farmtact.fly.dev/v10/),
from source `ec4e29874b2c7408f2bd93d012912e3c0cb8d2f3` and image
`registry.fly.io/farmtact@sha256:874530e73f481b1197e528bb5f124b958a74be64c9934292c14438b4cdd503bf`.
The first update attempt failed because Fly returned `MANIFEST_UNKNOWN` for the
new image. A retry with the same pinned source and digest succeeded; no alternate
image was rebuilt or substituted. All ten edition health/source checks passed.
Captured v1–v9 preservation passed. See
[health evidence](../../reports/v10/deployment-health.json) and
[preservation evidence](../../reports/v10/preservation-after.json). Publication made no inference call. The
separate Council-only trial used nine requests for seven messages and failed its
targeted quality gate, with five of seven cases passing. A later mission was withheld before inference at the
request-budget boundary. The next unused edition is v11.


V10 final capacity evidence is **FAIL** (`reports/v10/shared-capacity-public.json`):
the isolated pair exceeded the 180-second job deadline and browse p95 reached
15.0367 seconds. An earlier mixed-load probe also failed. HTTP health, farm/cookie
isolation and zero inference passed; they do not imply loaded performance passed.
Future acceptance requires queue/execution tracing, CPU/platform-quota measurement,
shared numerical admission control evaluation and bounded cancellation testing.
No host resource increase or threshold relaxation was made. See the V10 technical
follow-up and capacity protocol note for exact scope and cleanup.


## V12 candidate acceptance and retirement

Stage the exact committed candidate while V11 remains the sole public edition:

```bash
.venv/bin/python -m scripts.stage_edition_candidate \
  --edition v12 --source-commit "$(git rev-parse HEAD)" \
  --notes /absolute/private/path/v12-notes.json \
  --image registry.fly.io/farmtact@sha256:<64-hex-digest> \
  --record /absolute/private/path/v12-stage.json
```

The command adds only the V12 candidate worker and leaves `active.json`
unchanged. Candidate requests require authenticated operator access. Validate
source identity, state isolation, numerical/Council journeys and capacity before
publishing the identical source and image. Failed candidates do not change the
public pair and may be restaged with the same identity.

Application containers intentionally hide `/persist`, and a root SSH session in
the gateway cannot remount the block device. After the recovery snapshot is
recorded, generate a temporary Machine configuration containing the explicitly
service-less, secret-free retirement operator. It receives the existing volume
at `/persist` and only sleeps until an operator invokes the bounded CLI:

```bash
python scripts/shared_host_config.py --registry config/releases/registry.json \
  --active config/releases/active.json --staged v12 \
  --volume vol_vdejexpzm8ydn5x4 --public --retirement-operator \
  --output /tmp/farmtact-retirement-machine.json
fly machine update 2871575b4544d8 -a farmtact \
  --machine-config /tmp/farmtact-retirement-machine.json --yes
fly ssh console -a farmtact --machine 2871575b4544d8 --container retirement-operator \
  --user root --command \
  'cd /app && python -m scripts.shared_retirement_operator --output /tmp/retirement-before.json --staged v12'
fly ssh sftp shell -a farmtact --machine 2871575b4544d8 --container retirement-operator <<'SFTP'
get /tmp/retirement-before.json /tmp/retirement-before.json
quit
SFTP
```

Review the exact `v1`–`v10` targets, V11/V12 exclusions, checksums and resource
readings. Apply only that unchanged plan after the snapshot is available:

```bash
fly machine list -a farmtact --json > /tmp/farmtact-machine-list.json
python - <<'PY'
import json
rows = json.load(open('/tmp/farmtact-machine-list.json'))
matches = [row for row in rows if row.get('id') == '2871575b4544d8']
assert len(matches) == 1
open('/tmp/farmtact-runtime.json', 'w').write(json.dumps(matches[0]))
PY
fly ssh sftp shell -a farmtact --machine 2871575b4544d8 --container retirement-operator <<'SFTP'
put /tmp/farmtact-runtime.json /tmp/farmtact-runtime.json
quit
SFTP
fly ssh console -a farmtact --machine 2871575b4544d8 --container retirement-operator \
  --user root --command \
  'cd /app && python -m scripts.shared_retirement_operator --output /tmp/retirement-after.json --staged v12 --runtime-config /tmp/farmtact-runtime.json --apply --snapshot-id <recorded-fly-snapshot-id>'
```

Remove the operator immediately afterward by regenerating the same active/staged
configuration without `--retirement-operator` and updating the Machine again.
Apply mode removes only direct inactive `vN` subtrees whose checksums still
match. It cannot delete
gateway controls, manifests, credentials, budgets, V11, V12, or the shared
volume. Registry image rows remain advisory until registry/container inspection
proves a digest unused. Keep the Machine size unchanged until separate capacity
and billing evidence supports a change.

The staged V12 image supplies the gateway code needed for the active-manifest
cutover. V11 keeps its frozen application image and independent state.

Staged candidate admission is explicitly configured with `FARMTACT_STAGED_EDITION` on
the gateway. The control service admits only that exact next unpublished number,
under the same authentication, rate limits and shared provider cap. Public routing
continues to require the published registry. When restaging an unlisted candidate,
the staging helper verifies and resets only its local release manifest to the
published prefix; candidate game data and all published containers' manifests are
retained. Keep the staging record for safe retries. Stage and publish on the same
UTC date, because release metadata includes that date.
