# Publishing immutable editions

Each numbered edition is a frozen source commit and image digest. Since v6, the gateway and v1–v8 run in separate containers on one Singapore Fly Machine (4 shared vCPUs, 4096 MB) and one encrypted 3-GB `farmtact_shared_data` volume. Fixed, isolated subtrees preserve each edition’s own database, cache, settings and saved progress. The public `farmtact` gateway owns the chooser, `/api/releases`, the shared 48-call inference budget and shared abuse counters. Edition applications use fixed local destinations and accept application traffic only from the authenticated gateway. Actual farm operations remain disabled.

The publisher never resolves an image tag. You may supply a previously verified `sha256` digest. When `--image` is omitted, it runs the fixed gateway Fly build with `--build-only --push --remote-only`, labels it from the edition and short source hash, passes the full source commit as a build argument, and accepts only the pinned registry digest reported by Fly. Commit the complete candidate source first. The publisher rejects dirty worktrees, abbreviated commits, non-HEAD commits, mutable image references, skipped edition numbers, changes to existing registry entries, and reuse of a locally reserved number with different inputs.

Prepare a notes file containing exactly `title`, `summary`, and `changes`. Each change contains `title`, `description`, `feedback_ids`, and `evidence`. Then validate without Fly mutations:

```bash
.venv/bin/python -m scripts.publish_edition \
  --edition v9 \
  --notes /absolute/private/path/v9-notes.json \
  --image registry.fly.io/farmtact@sha256:<64-hex-digest> \
  --source-commit "$(git rev-parse HEAD)" \
  --dry-run
```

Omit `--image` to use the fixed build-and-push path. Run without `--dry-run` to publish. A dry run performs validation without reserving the number or changing `.git`. The active shared-host publisher performs these steps:

1. Requires a clean, committed source and the next contiguous edition number.
2. Reserves that edition/source/image identity under `.git` to prevent reuse.
3. Builds or accepts the pinned OCI digest, then regenerates the shared Machine
   configuration with all previous pinned containers plus the new edition.
4. Updates the exact Machine in `config/hosting/shared.json`, reusing its volume
   and existing runtime secrets. It checks the new edition's health, ID and full
   source commit through authenticated operator SSH.
5. Keeps the previous public registry during startup, then atomically appends
   the verified edition without changing any previous entry.
6. Mirrors the registry and release manifest, commits them, tags the frozen
   source as `farmtact-vN`, and pushes the commit and tag.

The current next unused number is v9; always check the registry before publishing.
The legacy separate-app provisioning path remains for environments without a
shared-host record. Do not remove that record to publish on this deployment.
No credential values enter generated configuration, command output or manifests.
Publication performs no inference calls.

Long release work must still follow the project’s 20-minute Git push cadence: keep implementation and verification commits pushed before starting publication. The publisher makes and pushes the final registry/manifests commit and immutable source tag after the live registry swap.

If a step fails, inspect the reported Fly command and rerun with the same edition, source commit, and digest after repairing the external state. Do not delete the `.git/farmtact-publications.json` reservation or choose a different build under the same number. If failure occurs after remote registry replacement, verify `/api/releases` before retrying; published history remains authoritative. A registry rollback may only restore the exact previous complete file when the new edition was never made public. Never edit or reorder earlier entries.

The gateway refreshes its validated destinations and control edition allowlist after atomic publication. Updating the shared Machine can restart the gateway and all edition containers.


## Active shared-host deployment (v8)

The verified deployment uses one 4-shared-vCPU/4-GB Machine with one persistent volume.
The public chooser and every immutable edition run in separate Pilot containers,
each with its registered exact OCI image. A deployment adapter binds only the
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
in 21.803s and 21.847s, read p95 was 0.1993s, and 2603.5 MiB remained available. This validates light concurrent use, not arbitrary scale. Singapore
base estimate: $28.92 compute + $0.45 volume = $29.37 per 30-day month, excluding
other billable items. One host is one availability boundary; deployments may
briefly interrupt all editions. Reassess memory before accumulating many more
editions. See [capacity](../../reports/v6/shared_capacity_public.json) and
[transfer evidence](../../reports/v6/data_transfer.json).

Use the immutable publisher for new app releases. Do not run a generic
`fly deploy` against this shared host: root fly.toml is retained for image
building and historical bootstrap, and does not describe the active containers.
To regenerate the active configuration for an operator-reviewed update:

```bash
python scripts/shared_host_config.py --registry config/releases/registry.json \
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
