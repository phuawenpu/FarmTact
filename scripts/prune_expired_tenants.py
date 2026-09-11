#!/usr/bin/env python3
"""Preview or explicitly apply bounded anonymous-tenant retention."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.api.retention import (
    DEFAULT_RETAINED_DAYS,
    DEFAULT_TENANT_LIMIT,
    MAX_RETAINED_DAYS,
    MAX_TENANTS_PER_INVOCATION,
    MIN_RETAINED_DAYS,
    prune_expired_tenants,
)
from services.api.store import Store


def bounded_integer(name: str, minimum: int, maximum: int):
    def parse(value: str) -> int:
        try:
            parsed = int(value)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"{name} must be an integer") from exc
        if not minimum <= parsed <= maximum:
            raise argparse.ArgumentTypeError(
                f"{name} must be from {minimum} through {maximum}"
            )
        return parsed

    return parse


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        description=(
            "Preview expired anonymous tenants, or delete them with --apply. "
            "The database URL comes from FARMTACT_DATABASE_URL."
        )
    )
    result.add_argument(
        "--retained-days",
        type=bounded_integer("retained days", MIN_RETAINED_DAYS, MAX_RETAINED_DAYS),
        default=DEFAULT_RETAINED_DAYS,
        help=f"retain tenants this many days (default {DEFAULT_RETAINED_DAYS})",
    )
    result.add_argument(
        "--limit",
        type=bounded_integer("tenant limit", 1, MAX_TENANTS_PER_INVOCATION),
        default=DEFAULT_TENANT_LIMIT,
        help=f"maximum old tenants inspected per invocation (default {DEFAULT_TENANT_LIMIT})",
    )
    result.add_argument(
        "--apply",
        action="store_true",
        help="perform the reported deletion; omission is always a dry run",
    )
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    store = Store()
    try:
        report = prune_expired_tenants(
            store,
            retained_days=args.retained_days,
            limit=args.limit,
            apply=args.apply,
        )
    finally:
        store.engine.dispose()
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
