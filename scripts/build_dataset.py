#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))

from packages.ingestion import install_fixture_bundle,rebuild,refresh


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build FarmTact's bounded public-context dataset")
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--offline", action="store_true", help="rebuild only from immutable snapshots in the manifest")
    parser.add_argument("--without-singstat", action="store_true", help="skip the SingStat T010002 volume connector")
    parser.add_argument("--with-power", action="store_true", help="also fetch a seven-day NASA POWER historical baseline")
    parser.add_argument("--fixture-bundle",type=Path,
        help="build offline from an integrity-checked project-authored synthetic source-contract bundle")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.offline and args.fixture_bundle:
        raise SystemExit('--offline and --fixture-bundle are mutually exclusive')
    if args.fixture_bundle and (args.with_power or args.without_singstat):
        raise SystemExit('--fixture-bundle uses its declared bounded source set; live source flags are not accepted')
    context = (install_fixture_bundle(args.fixture_bundle,args.data_dir) if args.fixture_bundle else
        rebuild(args.data_dir) if args.offline else refresh(
            args.data_dir, include_singstat=not args.without_singstat, include_power=args.with_power))
    summary = {
        "built_at": context.built_at,
        "execution_mode": context.execution_mode,
        "data_mode": (context.sources[0].get("data_mode") if context.sources else "unavailable"),
        "quality_status": context.quality.get("status"),
        "row_counts": context.quality.get("row_counts", {}),
        "sources": [{"source_id": row["source_id"], "status": row["status"], "freshness": row["freshness"]}
                    for row in context.sources],
        "failure_count": len(context.failures),
        "manifest": str(args.data_dir / "manifests" / "dataset_manifest.json"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if context.quality.get("status") == "passed" else 2


if __name__ == "__main__":
    sys.exit(main())
