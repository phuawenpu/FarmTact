# Publishing immutable editions

Each numbered edition is a frozen source commit and image digest with its own private Fly app and encrypted `farmtact_data` volume. The public `farmtact` gateway owns the chooser, `/api/releases`, the shared 48-call inference budget and shared abuse counters. Edition applications are reachable through Flycast and accept application traffic only from the authenticated gateway. Actual farm operations remain disabled.

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

Omit `--image` to use the fixed build-and-push path. Run without `--dry-run` to publish. A dry run performs validation without reserving the number or changing `.git`. Publication performs these bounded steps:

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
