"""Explicit, bounded cleanup for expired anonymous tenants.

This module is an operator maintenance surface.  The application does not import
or schedule it, and the public API exposes no retention endpoint.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import delete, func, select

from services.api.conversation_store import conversation_requests
from services.api.council_research import JOBS as research_jobs
from services.api.scenarios import branches as scenario_branches
from services.api.store import metadata, runs as planning_runs, tenants
from services.api.planning_sessions import JOBS as guided_jobs


MIN_RETAINED_DAYS = 7
MAX_RETAINED_DAYS = 36_500
DEFAULT_RETAINED_DAYS = 30
MAX_TENANTS_PER_INVOCATION = 500
DEFAULT_TENANT_LIMIT = 100

# These records control all tenants or all editions.  Tenant retention must never
# alter them.  Edition-control tables are included because they may be registered
# when this module is used in an edition process.
PROTECTED_SHARED_TABLES = frozenset(
    {
        "abuse_rate_counters",
        "abuse_security_settings",
        "edition_control_releases",
        "edition_control_reservations",
        "inference_budget",
    }
)

ACTIVE_STATUSES = frozenset({"CREATED", "QUEUED", "RUNNING"})


def _validate_inputs(retained_days: int, limit: int) -> None:
    if (
        not isinstance(retained_days, int)
        or isinstance(retained_days, bool)
        or not MIN_RETAINED_DAYS <= retained_days <= MAX_RETAINED_DAYS
    ):
        raise ValueError(
            f"retained_days must be an integer from {MIN_RETAINED_DAYS} "
            f"through {MAX_RETAINED_DAYS}"
        )
    if (
        not isinstance(limit, int)
        or isinstance(limit, bool)
        or not 1 <= limit <= MAX_TENANTS_PER_INVOCATION
    ):
        raise ValueError(
            f"limit must be an integer from 1 through {MAX_TENANTS_PER_INVOCATION}"
        )


def _normalized_as_of(value: datetime | None) -> datetime:
    result = value or datetime.now(timezone.utc)
    if result.tzinfo is None or result.utcoffset() is None:
        raise ValueError("as_of must include a timezone")
    return result.astimezone(timezone.utc)


def _tenant_tables() -> list[Any]:
    """Return every registered tenant table in child-before-parent order."""

    unknown_shared = {
        table.name
        for table in metadata.tables.values()
        if table is not tenants
        and "tenant_id" not in table.c
        and table.name not in PROTECTED_SHARED_TABLES
    }
    if unknown_shared:
        names = ", ".join(sorted(unknown_shared))
        raise RuntimeError(
            f"Retention refused: registered shared tables need an explicit policy: {names}"
        )
    return [
        table
        for table in reversed(metadata.sorted_tables)
        if table is not tenants and "tenant_id" in table.c
    ]


def _parse_created_at(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (AttributeError, TypeError, ValueError):
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(timezone.utc)


def _active_reasons(connection: Any, tenant_id: str) -> list[str]:
    checks = (
        ("planning_mission", planning_runs),
        ("scenario", scenario_branches),
        ("conversation", conversation_requests),
        ("research", research_jobs),
        ("guided_planning", guided_jobs),
    )
    reasons = []
    for name, table in checks:
        active = connection.execute(
            select(table.c.tenant_id)
            .where(
                table.c.tenant_id == tenant_id,
                table.c.status.in_(ACTIVE_STATUSES),
            )
            .limit(1)
        ).first()
        if active is not None:
            reasons.append(name)
    return reasons


def _candidate_query(cutoff: datetime, limit: int, *, lock: bool, dialect: str):
    query = (
        select(tenants.c.id, tenants.c.created_at)
        .where(tenants.c.created_at < cutoff.isoformat())
        .order_by(tenants.c.created_at, tenants.c.id)
        .limit(limit)
    )
    if lock:
        query = query.with_for_update(skip_locked=dialect == "postgresql")
    return query


def _evaluate_candidates(
    connection: Any,
    *,
    cutoff: datetime,
    limit: int,
    lock: bool,
    dialect: str,
) -> tuple[list[str], list[dict[str, Any]], list[dict[str, str]]]:
    rows = connection.execute(
        _candidate_query(cutoff, limit, lock=lock, dialect=dialect)
    ).all()
    eligible: list[str] = []
    skipped_active: list[dict[str, Any]] = []
    skipped_invalid: list[dict[str, str]] = []
    for tenant_id, created_at in rows:
        parsed = _parse_created_at(created_at)
        if parsed is None:
            skipped_invalid.append(
                {"tenant_id": tenant_id, "reason": "invalid_created_at"}
            )
            continue
        if parsed >= cutoff:
            # SQL text ordering is only the bounded prefilter; parsed UTC time is
            # authoritative before any deletion.
            continue
        reasons = _active_reasons(connection, tenant_id)
        if reasons:
            skipped_active.append(
                {"tenant_id": tenant_id, "active_job_types": reasons}
            )
        else:
            eligible.append(tenant_id)
    return eligible, skipped_active, skipped_invalid


def _row_counts(connection: Any, tenant_ids: list[str], tables: list[Any]) -> dict[str, int]:
    if not tenant_ids:
        return {table.name: 0 for table in tables} | {tenants.name: 0}
    counts = {
        table.name: connection.execute(
            select(func.count())
            .select_from(table)
            .where(table.c.tenant_id.in_(tenant_ids))
        ).scalar_one()
        for table in tables
    }
    counts[tenants.name] = connection.execute(
        select(func.count())
        .select_from(tenants)
        .where(tenants.c.id.in_(tenant_ids))
    ).scalar_one()
    return counts


def prune_expired_tenants(
    store: Any,
    *,
    retained_days: int = DEFAULT_RETAINED_DAYS,
    limit: int = DEFAULT_TENANT_LIMIT,
    apply: bool = False,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    """Preview or atomically delete a bounded set of inactive expired tenants.

    ``apply`` defaults to false.  In apply mode candidate rows are locked, active
    jobs are checked inside the write transaction, and all tenant-owned child rows
    are deleted before their tenants.  Shared budget and security tables are never
    part of the deletion set.
    """

    _validate_inputs(retained_days, limit)
    instant = _normalized_as_of(as_of)
    cutoff = instant - timedelta(days=retained_days)
    tables = _tenant_tables()
    protected = sorted(
        name for name in PROTECTED_SHARED_TABLES if name in metadata.tables
    )

    if apply:
        with store.transaction() as connection:
            eligible, skipped_active, skipped_invalid = _evaluate_candidates(
                connection,
                cutoff=cutoff,
                limit=limit,
                lock=True,
                dialect=store.engine.dialect.name,
            )
            planned_counts = _row_counts(connection, eligible, tables)
            deleted_rows: dict[str, int] = {}
            if eligible:
                for table in tables:
                    result = connection.execute(
                        delete(table).where(table.c.tenant_id.in_(eligible))
                    )
                    deleted_rows[table.name] = result.rowcount
                result = connection.execute(
                    delete(tenants).where(tenants.c.id.in_(eligible))
                )
                deleted_rows[tenants.name] = result.rowcount
            else:
                deleted_rows = {name: 0 for name in planned_counts}
    else:
        with store.connection() as connection:
            eligible, skipped_active, skipped_invalid = _evaluate_candidates(
                connection,
                cutoff=cutoff,
                limit=limit,
                lock=False,
                dialect=store.engine.dialect.name,
            )
            planned_counts = _row_counts(connection, eligible, tables)
        deleted_rows = {}

    return {
        "schema_version": "farmtact-tenant-retention-1.0.0",
        "mode": "apply" if apply else "dry_run",
        "as_of": instant.isoformat(),
        "cutoff_exclusive": cutoff.isoformat(),
        "retained_days": retained_days,
        "tenant_limit": limit,
        "registered_table_count": len(metadata.tables),
        "tenant_table_count": len(tables),
        "protected_shared_tables": protected,
        "eligible_tenant_ids": eligible,
        "eligible_tenant_count": len(eligible),
        "skipped_active": skipped_active,
        "skipped_invalid_created_at": skipped_invalid,
        "would_delete_rows": planned_counts,
        "deleted_rows": deleted_rows,
        "automatic_schedule": False,
    }


__all__ = [
    "DEFAULT_RETAINED_DAYS",
    "DEFAULT_TENANT_LIMIT",
    "MAX_RETAINED_DAYS",
    "MAX_TENANTS_PER_INVOCATION",
    "MIN_RETAINED_DAYS",
    "PROTECTED_SHARED_TABLES",
    "prune_expired_tenants",
]
