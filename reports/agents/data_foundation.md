# A01–A06 data foundation handoff

## Objective and result

Implemented the first versioned FarmTact evidence and public-context data product. It contains ten unranked crop profiles, twenty faithfully transcribed publication records, the complete 56-source index, 23-dataset integration registry, explicit HS mapping decisions, real NEA/SingStat/NASA connectors, immutable content-addressed raw snapshots, normalized traceable rows, freshness/failure states, a deterministic manifest and offline rebuild.

This is development evidence and public context. It is not a commercial crop recipe, farm observation, customer demand series, market price, or real-farm validation.

## Files changed

- `research/crop_catalogue.json`: ten profiles, aliases, boundary warnings, evidence links, taxonomy states and gaps; every popularity rank is null.
- `research/evidence_register.json`: P01–P20 with the review's access state, scope, finding, implication, limitation, licence gap and permitted-use state.
- `research/source_registry.json`: C01–C04, P01–P20, D01–D23 and T01–T09 (56 sources), using JSON references to avoid duplicating canonical publication/dataset states.
- `research/dataset_registry.json`: D01–D23 with access, licence, priority, unit, freshness and integration traps.
- `research/crop_hs_mappings.json`: exact provider-description mappings for lettuce and Chinese mustard; broad spinach/cabbage/other-vegetable codes remain unresolved.
- `research/api_contracts/nea_v2.json`: live-smoke-verified NEA v2 endpoint shapes.
- `packages/ingestion/`: dependency-free HTTP, snapshot, normalization, validation, cache/failure, live refresh and offline rebuild implementation. Cached fallbacks restore the immutable `SnapshotRecord` objects referenced by their rows so manifests and lineage stay closed.
- `scripts/build_dataset.py`: bounded live/offline dataset CLI.
- `tests/data/test_ingestion.py`: registry, taxonomy, unit/time, non-finite value, immutable snapshot, header redaction, freshness, stale-cache and offline-rebuild tests.

Generated artifacts are under `data/`: raw provider payloads stay ignored in `data/raw/`; normalized/runtime outputs are ignored; small `data/manifests/*.json` and `data/reports/data_quality.json` remain reviewable according to the repository ignore policy.

## Public Python interface

```python
from pathlib import Path
from packages.ingestion import get_public_context, rebuild, refresh

context = refresh(Path("data"), include_singstat=True, include_power=True)
payload = get_public_context(Path("data")).as_dict()
offline = rebuild(Path("data"))
```

`payload["sources"]` supplies `source_id`, provider, kind, status, data mode, source/retrieval time, freshness recalculated at read time, age, units, coverage, snapshot ID, licence state and failure reason. Detail rows carry stable IDs, source/snapshot IDs and raw JSON locators. Observations without verified availability timestamps set `eligible_for_point_in_time_features=false`.

## Official sources checked and access gaps

- D01–D05: official data.gov.sg dataset pages and Singapore Open Data Licence reviewed on 2026-09-08. All five official endpoints returned HTTP 200 and passed live schema/unit normalization. Pages state five-minute station updates, six-hour 24-hour forecast updates, twelve-hour four-day updates, possible gaps/corrections and local station effects.
- D06/T08: official SingStat developer page was opened but requires JavaScript. The public `tabledata/T010002` endpoint was independently smoke-tested. It requires a month-form `timeFilter`; its response supplies an `endPeriod` and cursor. The latest available period was 2026 Jul, returning 5,000 first-page rows and 15 selected HS8/flow rows for six reviewed fresh/chilled vegetable descriptions. Exact release timestamp, nomenclature version and redistribution licence remain unresolved, so freshness is unknown and `available_at` is null.
- D11: official NASA POWER daily API documentation reviewed. The connector requests UTC explicitly, limits requests to three parameters at one Singapore grid point for seven days, records returned units/fill values, and labels the data historical grid context rather than forecast or farm sensing. Live response passed after availability probing.
- P01–P20 and C01–C04 were reconstructed from the root `RESEARCH_REVIEW.md`; no new claim of full-text access was made. Every original access limitation and licence gap remains visible.
- D12–D23 remain discovered/metadata-only/blocked as recorded. No satellite or international dataset is presented as integrated.

## Actual build and output

Live command:

```bash
python scripts/build_dataset.py --data-dir data --with-power
```

Result at 2026-09-08T08:23:56.436644Z:

- dataset ID `a6ada7a03c2aca0975580daba9ad997eda9f8e80bdd20f8d7d6c29e22de80f2a`
- 8 immutable raw snapshots; 7 validated public sources; 0 connector failures
- 145 weather observations: D01 88, D02 18, D03 18, D11 21
- 40 weather forecast fields: D04 20, D05 20
- 15 SingStat T010002 volume observations from 5,000 returned rows
- 200 of 200 normalized rows traceable to a source, snapshot and raw locator
- quality status `passed`; no duplicate IDs, invalid units/timestamps, non-finite values, untraceable rows, orphaned snapshot references or unsafe uncertain-availability feature flags

Output hashes and every source snapshot checksum are in `data/manifests/dataset_manifest.json`; transformation edges are in `data/manifests/lineage.json`; quality details and known gaps are in `data/reports/data_quality.json`.

Offline reproduction from the recorded raw bytes:

```bash
python scripts/build_dataset.py --data-dir data --offline
```

This rebuilt all 200 normalized rows successfully. The live command was run again afterward so the checked runtime context remains labelled `live_public_refresh`.

## Tests actually run

```bash
python -m unittest discover -s tests/data -v
.venv/bin/python -m pytest tests/data -q
.venv/bin/python -m pytest tests/review/test_backend_adversarial.py::test_cached_rows_keep_their_immutable_snapshot_in_refreshed_context -q
python -m compileall -q packages/ingestion scripts/build_dataset.py
for f in research/*.json research/api_contracts/*.json; do jq empty "$f"; done
```

Eight unittest cases and the same eight pytest cases passed. The A11 cached-snapshot-lineage regression passed independently (one test). Compilation and all registry JSON parses passed. The system Python does not have pytest installed; the repository virtual environment does, and no dependency or lock/config change was made by this work package.

## Assumptions, risks and blockers

- The NEA API does not expose a separate observation publication timestamp. `available_at` is provisionally equal to `observed_at`, marked uncertain, and prohibited from point-in-time feature use. Source cards may use it only as current context.
- D06 quantities preserve the provider unit `TNE` as normalized `tonne`; no silent conversion to kilograms occurs. Missing/suppressed/non-finite values are excluded, never changed to zero.
- Broad HS codes are market context and cannot become named-crop demand. Only exact description matches are approved, with scope limitations.
- D11 units remain provider-returned (`C`, `%`, `mm/day`) and its grid point does not represent an on-farm sensor.
- Local commercial yields, cultivar recipes, packout, shelf life, harvest costs, repeated-cut performance, buyer demand and farm-specific weather mapping remain unavailable. The research records do not authorize those values.
- No ingestion blocker remains for the bounded demo context. Pytest availability is an environment/dependency gap, not a test failure.
