# FarmTact v6 — published 2026-09-09

Live: https://farmtact.fly.dev/v6/ . Source is frozen at
`f4606222af6658986b491250de66cb12f6422f32`; OCI digest ends in
`2415d2a861c83dfda71e13fb25c3187d3082c2f49a987ef3e68751208f63d334`.
The v6 manifest and immutable source tag record the full identities. Later commits
contain operational migration, publication, tests and evidence, not changes to
the frozen application image. All earlier edition image/source pins are unchanged.

## Delivered

The crop atlas has twelve profiles, including garlic chives (Allium tuberosum)
and sawtooth coriander (Eryngium foetidum), original SVG illustrations, local
NParks background, four primary papers and explicit evidence/mapping gaps. The
two new species are knowledge profiles; they do not invent commercial yield or
recipe parameters. The existing four-crop synthetic fixture is unchanged.

Gateway plus v1–v6 run as seven isolated containers on one Singapore shared-CPU
Machine (4 vCPU, 4096 MB). One encrypted 3-GB volume provides fixed per-container
subtrees; the common parent is unmounted before the app drops privileges. Each
edition retains its own PostgreSQL database, cache, sessions and saved progress.
The existing global operational budget remains centralized in the gateway.
Future immutable publications update this same Machine using the shared-host
record; they do not create another app, Machine or volume.

After verified transfer and public checks, six superseded FarmTact Machines and
seven old volumes were deleted under the user's explicit authorization. Inventory
shows exactly one remaining Machine and one shared volume. Unrelated Fly apps
were never selected. The old edition app registrations remain empty.

## Evidence

- Full backend suite: 458 passed; frontend type/build and contract drift checks passed.
- Final operator/shared-host/publisher suite: 36 passed.
- Crop atlas: 45/45 local, 45/45 exact-image private Fly, 45/45 public checks;
  widths 360, 390, 430 and 1280, keyboard/reduced motion and evidence links.
- Public edition selector: 7/7 checks, exactly v1–v6, no POST/provider requests.
- Private seven-service capacity: two fresh concurrent jobs ~10 seconds each,
  read p95 0.1674s, ~2.5 GiB available, no swap.
- Public capacity: two fresh concurrent v5/v6 jobs 21.803s/21.847s; all three
  strategies feasible, no inference calls, read p95 0.1993s, main farms unchanged,
  cross-edition cookies rejected with 401. Available memory ended at 2603.5 MiB.
- Six source/candidate database and cache fingerprints matched before opening
  traffic, including row contents/counts, owners/ACLs and original source identity.
- Public registry and all six health/source identities passed after cleanup.
- Sprite HTTP and private tunnel services were deleted; ports 8080/8086/8088 are
  closed and the temporary tunnel credential file removed. Local DB retained.

See the adjacent JSON reports and `hosting_design_review.md`. Browser testing is
headless Chromium emulation, not physical mobile hardware or a human recognition
study. No application inference calls were requested by this rollout.

## Migration and operational limits

An initial candidate restore guard correctly stopped before mutation because a
container cannot SIGSTOP its own namespace PID 1. Original services were resumed.
A fixed ancestor-namespace helper, using exact command lines, NSpid, namespace
inode and mount identity (never process environments), was reviewed and proved on
a private restore rehearsal. A fresh source freeze/export/copy/restore then passed
all six fingerprints. Cutover required several minutes of controlled write pause
and a shared Machine restart; this was not a zero-downtime migration.

The final inventory is `fly_inventory_after.json`; the source fingerprint summary
is `data_transfer.json`. Protected local transfer artifacts remain outside the
repository and HTTP service. Old Fly volumes were not kept for rollback.

Base Singapore estimate from official Fly pricing: $28.92 compute plus $0.45
for 3 GB storage = $29.37 per 30-day month, compared with the old $84.33 compute
and volume estimate (about 65% lower). Other billed items are excluded.
Sources: https://fly.io/docs/about/pricing/ and
https://fly.io/docs/machines/guides-examples/multi-container-machines/ .

The concurrency test supports light use, not arbitrary traffic. One Machine is a
single availability boundary, and each future edition adds memory/storage demand.
Review capacity as editions accumulate. Generic `fly deploy` is not the current
publication path: use `publish_edition.py` and the shared-host runbook.
