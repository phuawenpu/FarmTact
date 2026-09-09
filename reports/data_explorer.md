# FarmTact Data Explorer implementation and verification

This release adds an authenticated explorer for selected farm versions, the
original generated fixture, immutable playground datasets and completed scenario
results. All farm quantities remain explicitly synthetic. Real operations are
disabled. EWMA is a statistical baseline and CP-SAT is an optimiser; neither is
trained on real farm outcomes.

## Architecture and persistence

The additive `explorer_snapshots` table is registered before the existing
SQLAlchemy schema bootstrap. It stores the actual generated records and forecast,
validated generator/forecast settings, versions, cutoff, reference baseline,
content hashes and provenance. `explorer-snapshot-v1` requires complete integrity
metadata. Reopening verifies dataset, forecast and reference hashes. Numerical
jobs inherit the frozen forecast configuration; smoothing-only changes calculate
a distinct result. Unsupported frozen numerical versions fail without model
substitution. Existing farm versions and planning runs are preserved.

`/api/v1/data-explorer` exposes enumerated snapshot/record/series/preview/export
interfaces and separate cached public-context interfaces. Source records are
curated fields; callers cannot request filesystem paths. Preview admission is
30/minute/session and 60/minute/IP within existing durable abuse limits. Queries,
pages and exports are bounded; CSV cells escape formula prefixes. Public exports
require verified redistribution terms. The explorer does not use global private
feature files. Its historical evaluation is explicitly labelled with the
original reference fixture hash and EWMA alpha 0.35.

Playground scenarios use the original generated fixture as their baseline.
Main-farm branches retain their existing baseline. Comparison validation includes
root, baseline snapshot, forecast settings and calculation version. Browsing,
filtering, previews, saves and numerical jobs make no inference requests. An
advisor discussion is attached to a completed frozen scenario and uses the
existing explicit DeepSeek message action.

## Verification recorded during implementation

- Exact HEAD-versus-new default fixture JSON equality. Original fixture hash:
  `00286779541fa9ed1245ea2aff65d08c1a05241cdc6a399706aa6601fdbc3f76`.
- 41 numerical/model/private-contract tests passed, including generator boundaries,
  formula parity, cutoff exclusion and preview/planner agreement.
- Full Python regression: 353 passed at the integrated backend milestone.
- Three independent adversarial review cases verified rejection of changed input,
  changed forecast, missing integrity metadata, idempotent replay and scenario use.
- Real PostgreSQL concurrent save/reload and interrupted numerical-worker
  continuation passed. A real local saved dataset at alpha 0.8 and its result
  remained byte-for-byte unchanged after API service restart; main farm unchanged.
- The cached public adapter exposes 145 weather observations, 40 forecast fields,
  15 trade observations and all 23 registry sources. Registry-only sources remain
  metadata-only; no observations are invented. Cache freshness is computed on read.
- Fly configuration validation and 22 deployment/adversarial checks passed.

The first independent integrity review uncovered missing checks for altered stored
JSON; the second uncovered optional integrity metadata. Both were fixed and the
previously failing tests now pass. A historical targeted test run recorded an
expected failure before the second fix; final review has no expected failures.

## Reproduction

```
.venv/bin/python -m pytest -q
.venv/bin/python scripts/generate_web_contracts.py --check
(cd apps/web && npm run build)
node tests/browser/data_explorer.mjs
.venv/bin/python scripts/explorer_persistence_probe.py --phase capture
# Restart the API service, then:
.venv/bin/python scripts/explorer_persistence_probe.py --phase verify
```

Final targeted explorer/model/public tests: 57 passed. Final deployment and
adversarial checks: 22 passed. Production TypeScript/Vite build and generated
contracts check passed. Public-context browser: 25 checks passed, including all
four requested widths and no inference or console errors.

Browser results, final release image, deployment preservation and hosting checks
are recorded below when completed. Reports preserve actual scope; synthetic
calculations do not demonstrate commercial farm performance.

## Final local acceptance

The complete decision journey passed all 72 checks in `reports/explorer_browser.json`.
It identifies a date with demand but no scheduled harvest, opens contributing
orders, changes historical demand and alpha, freezes a dataset, verifies exact
preview/planner forecast equality, continues the branch into infeasibility,
compares all three policies against the original baseline, and opens the frozen
advisor context without sending an inference message. It repeats changed-price
numerical runs and comparisons at 390, 430 and 1280 pixels after the 360-pixel
journey. Main farm and recorded run remain unchanged. Screenshots are under
`apps/web/screenshots/explorer` and `apps/web/screenshots/explorer-public`.

Browser findings repaired before release: empty crop export parameters,
out-of-range numeric controls, wrapped legends and grid children, long snapshot
selector overflow, shared policy exports, and stale advisor selection.

## Fly release

Deployed to https://farmtact.fly.dev on 2026-09-08 UTC using the existing
`d8d2060c074438` machine and its persistent volume. Release image:
`registry.fly.io/farmtact:deployment-01M21PK80ABTT3JE5792F676N6`. Fly machine
health and DNS checks passed. The packaged historical evaluation endpoint
returned the original fixture hash and alpha 0.35.

`reports/explorer_release_persistence.json` verifies that the pre-deployment
main farm, recorded planning run, scenario result, conversation and quest
progress survived unchanged. `reports/explorer_hosting.json` verifies Fly
HTTP/health 200, Sprite web registration removed, port 8080 closed, development
PostgreSQL retained, and the Sprite public URL no longer serving FarmTact.

The deployed public-context journey passed all 25 checks in
`reports/explorer_public_browser_live.json`. No provider inference was used.

The deployed complete decision journey also passed all 72 checks in
`reports/explorer_browser_live.json`, including five completed numerical branches,
all requested viewport widths, original-baseline comparisons, frozen advisor
context, zero inference messages and unchanged main farm/recorded run. Live
screenshots are in `apps/web/screenshots/explorer-live` and
`apps/web/screenshots/explorer-public-live`. Release verification is complete.
