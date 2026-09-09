# Publishing immutable editions

Each numbered edition is a frozen source commit and image digest. Since v6, the gateway and v1–v6 run in separate containers on one Singapore Fly Machine (4 shared vCPUs, 4096 MB) and one encrypted 3-GB `farmtact_shared_data` volume. Fixed, isolated subtrees preserve each edition’s own database, cache, settings and saved progress. The public `farmtact` gateway owns the chooser, `/api/releases`, the shared 48-call inference budget and shared abuse counters. Edition applications are reachable through Flycast and accept application traffic only from the authenticated gateway. Actual farm operations remain disabled.

The publisher never resolves an image tag. You may supply a previously verified `sha256` digest. When `--image` is omitted, it runs the fixed gateway Fly build with `--build-only --push --remote-only`, labels it from the edition and short source hash, passes the full source commit as a build argument, and accepts only the pinned registry digest reported by Fly. Commit the complete candidate source first. The publisher rejects dirty worktrees, abbreviated commits, non-HEAD commits, mutable image references, skipped edition numbers, changes to existing registry entries, and reuse of a locally reserved number with different inputs.

Prepare a notes file containing exactly `title`, `summary`, and `changes`. Each change contains `title`, `description`, `feedback_ids`, and `evidence`. Then validate without Fly mutations:

```bash
.venv/bin/python scripts/publish_edition.py \
  --edition v3 \
  --notes /absolute/private/path/v3-notes.json \
  --image registry.fly.io/farmtact@sha256:<64-hex-digest> \
  --source-commit "$(git rev-parse HEAD)" \
  --dry-run
```

Omit `--image` to use the fixed build-and-push path. Run without `--dry-run` to publish. A dry run performs validation without reserving the number or changing `.git`. Without a shared-host record, the legacy publisher performs these bounded steps (the active shared-host path is described below):

1. Reads the current public registry and requires the next contiguous number.
2. Persists the edition/source/image reservation under `.git`; failed attempts retain that identity and published numbers can never be reused.
3. Creates `farmtact-edition-vN` without public IPs, inventories its networking, allocates a private IPv6 Flycast address when absent, creates its Singapore volume when absent, then deploys only the pinned digest with one Machine. Any public IP allocation blocks publication.
4. Probes the fixed private health URL from the gateway app and requires both healthy status and the requested full source commit.
5. Uploads a temporary registry, validates that every existing entry is structurally unchanged, copies the exact current registry to `registry.json.previous`, and atomically replaces the live registry.
6. Mirrors the registry, Fly manifest, and source/image release manifest under `config/releases`, commits them, tags the frozen source as `farmtact-vN`, and pushes the commit and tag.

For a new app, the publishing process must contain `FARMTACT_CONTROL_SECRET` and `DEEPSEEK_API_KEY`; the command fails before provisioning when either is absent. It stages them through `fly secrets import --stage` using subprocess stdin bytes. For an existing app, absent process credentials preserve its already-staged secrets, while supplied values are staged. Secret values never enter command arguments, output, generated manifests, or publication records. The command performs no inference calls.

Long release work must still follow the project’s 20-minute Git push cadence: keep implementation and verification commits pushed before starting publication. The publisher makes and pushes the final registry/manifests commit and immutable source tag after the live registry swap.

If a step fails, inspect the reported Fly command and rerun with the same edition, source commit, and digest after repairing the external state. Do not delete the `.git/farmtact-publications.json` reservation or choose a different build under the same number. If failure occurs after remote registry replacement, verify `/api/releases` before retrying; published history remains authoritative. A registry rollback may only restore the exact previous complete file when the new edition was never made public. Never edit or reorder earlier entries.

The gateway refreshes its validated registry-derived Flycast destinations and control edition allowlist after atomic publication, so a numbered edition does not require a gateway redeploy.


## Active shared-host deployment (v6)

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
After successful migration, the user requests deletion of the superseded
FarmTact Machines AND volumes. Only the exact FarmTact app allowlist is eligible;
unrelated Fly resources must not be altered. Final evidence must show one active
FarmTact Machine and one shared volume, and preserved migrated edition data.

Capacity evidence: two fresh concurrent v5/v6 numerical scenarios finished in
about ten seconds each, read p95 was 0.1674 seconds, and about 2.5 GiB remained
available. This validates light concurrent use, not arbitrary scale. Singapore
base estimate: $28.92 compute + $0.45 volume = $29.37 per 30-day month, excluding
other billable items. One host is one availability boundary; deployments may
briefly interrupt all editions. Reassess memory before accumulating many more
editions. See reports/v6/shared_capacity_v6.json and data_transfer.json.

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
