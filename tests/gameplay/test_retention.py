from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import func, select

from services.api.conversation_store import (
    conversation_events,
    conversation_messages,
    conversation_requests,
    conversations,
)
from services.api.council_research import (
    ACTIONS as research_actions,
    HISTORY as research_history,
    JOBS as research_jobs,
    RECEIPTS as research_receipts,
    SESSIONS as research_sessions,
)
from services.api.data_explorer import snapshots
from services.api.retention import (
    MAX_RETAINED_DAYS,
    MAX_TENANTS_PER_INVOCATION,
    prune_expired_tenants,
)
from services.api.scenarios import branches, quest_progress
from services.api.security import rate_counters, security_settings
from services.api.simulation import EVENTS as simulation_events
from services.api.simulation import RECEIPTS as simulation_receipts
from services.api.simulation import WORLDS as simulation_worlds
from services.api.store import (
    Store,
    budget,
    events as run_events,
    farms,
    metadata,
    mutation_receipts,
    runs,
    tenants,
)
from scripts.prune_expired_tenants import parser


AS_OF = datetime(2026, 9, 11, 12, tzinfo=timezone.utc)


@pytest.fixture
def store():
    value = Store("sqlite://")
    yield value
    value.engine.dispose()


def _create_tenant(store, tenant_id: str, age_days: int) -> None:
    created_at = (AS_OF - timedelta(days=age_days)).isoformat()
    with store.connection(write=True) as connection:
        connection.execute(
            tenants.insert().values(
                id=tenant_id,
                session_hash=f"hash-{tenant_id}",
                created_at=created_at,
            )
        )


def _seed_every_tenant_table(store, tenant_id: str) -> None:
    """Put one terminal row in each of the 19 current tenant-owned tables."""

    run_id = f"run-{tenant_id}"
    conversation_id = f"conversation-{tenant_id}"
    request_id = f"request-{tenant_id}"
    research_id = f"research-{tenant_id}"
    action_id = f"action-{tenant_id}"
    world_id = f"world-{tenant_id}"
    with store.connection(write=True) as connection:
        connection.execute(
            farms.insert().values(
                id=f"farm-{tenant_id}",
                tenant_id=tenant_id,
                version=1,
                input_hash="farm-hash",
                payload={},
            )
        )
        connection.execute(
            runs.insert().values(
                id=run_id,
                tenant_id=tenant_id,
                idempotency_key=f"run-key-{tenant_id}",
                request_hash="run-hash",
                status="COMPLETED",
                payload={},
            )
        )
        connection.execute(
            run_events.insert().values(
                run_id=run_id,
                tenant_id=tenant_id,
                sequence=1,
                payload={},
            )
        )
        connection.execute(
            mutation_receipts.insert().values(
                tenant_id=tenant_id,
                idempotency_key=f"mutation-{tenant_id}",
                request_hash="mutation-hash",
                payload={},
            )
        )
        connection.execute(
            branches.insert().values(
                id=f"scenario-{tenant_id}",
                tenant_id=tenant_id,
                idempotency_key=f"scenario-key-{tenant_id}",
                request_hash="scenario-hash",
                status="COMPLETED",
                payload={},
            )
        )
        connection.execute(
            quest_progress.insert().values(
                tenant_id=tenant_id,
                quest_id="late_harvest",
                payload={},
            )
        )
        connection.execute(
            snapshots.insert().values(
                id=f"snapshot-{tenant_id}",
                tenant_id=tenant_id,
                idempotency_key=f"snapshot-key-{tenant_id}",
                request_hash="snapshot-request",
                content_hash="snapshot-content",
                payload={},
            )
        )
        connection.execute(
            conversations.insert().values(
                id=conversation_id,
                tenant_id=tenant_id,
                idempotency_key=f"conversation-key-{tenant_id}",
                request_hash="conversation-hash",
                status="OPEN",
                payload={},
            )
        )
        connection.execute(
            conversation_messages.insert().values(
                id=f"message-{tenant_id}",
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                sequence=1,
                payload={},
            )
        )
        connection.execute(
            conversation_requests.insert().values(
                id=request_id,
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                idempotency_key=f"request-key-{tenant_id}",
                request_hash="request-hash",
                status="COMPLETED",
                payload={},
            )
        )
        connection.execute(
            conversation_events.insert().values(
                conversation_id=conversation_id,
                tenant_id=tenant_id,
                request_id=request_id,
                sequence=1,
                payload={},
            )
        )
        connection.execute(
            research_sessions.insert().values(
                id=research_id,
                tenant_id=tenant_id,
                idempotency_key=f"research-key-{tenant_id}",
                request_hash="research-hash",
                payload={},
            )
        )
        connection.execute(
            research_jobs.insert().values(
                id=f"research-job-{tenant_id}",
                tenant_id=tenant_id,
                session_id=research_id,
                version=1,
                status="COMPLETED",
                payload={},
            )
        )
        connection.execute(
            research_actions.insert().values(
                id=action_id,
                tenant_id=tenant_id,
                session_id=research_id,
                idempotency_key=f"action-key-{tenant_id}",
                request_hash="action-hash",
            )
        )
        connection.execute(
            research_history.insert().values(
                session_id=research_id,
                revision=0,
                tenant_id=tenant_id,
                payload={},
            )
        )
        connection.execute(
            research_receipts.insert().values(
                action_id=action_id,
                tenant_id=tenant_id,
                revision=0,
            )
        )
        connection.execute(
            simulation_worlds.insert().values(
                id=world_id,
                tenant_id=tenant_id,
                payload={},
            )
        )
        connection.execute(
            simulation_events.insert().values(
                world_id=world_id,
                sequence=1,
                tenant_id=tenant_id,
                payload={},
            )
        )
        connection.execute(
            simulation_receipts.insert().values(
                tenant_id=tenant_id,
                key=f"simulation-key-{tenant_id}",
                request_hash="simulation-hash",
                payload={},
            )
        )


def _counts(store) -> dict[str, int]:
    with store.connection() as connection:
        return {
            table.name: connection.execute(
                select(func.count()).select_from(table)
            ).scalar_one()
            for table in metadata.tables.values()
        }


def _tenant_exists(store, tenant_id: str) -> bool:
    with store.connection() as connection:
        return connection.execute(
            select(tenants.c.id).where(tenants.c.id == tenant_id)
        ).first() is not None


def test_dry_run_reports_full_schema_without_changing_rows(store):
    _create_tenant(store, "old-complete", 40)
    _seed_every_tenant_table(store, "old-complete")
    with store.connection(write=True) as connection:
        connection.execute(budget.insert().values(id="2026-09-11", reserved_calls=7))
        connection.execute(
            rate_counters.insert().values(key="global", count=3, expires=99_999)
        )
        connection.execute(
            security_settings.insert().values(key="mode", value="strict")
        )
    before = _counts(store)

    report = prune_expired_tenants(
        store, retained_days=30, limit=20, as_of=AS_OF
    )

    assert report["mode"] == "dry_run"
    assert report["automatic_schedule"] is False
    assert report["eligible_tenant_ids"] == ["old-complete"]
    assert report["deleted_rows"] == {}
    assert report["registered_table_count"] >= 23
    assert report["tenant_table_count"] >= 19
    assert report["would_delete_rows"]["tenants"] == 1
    assert all(
        count == 1 for count in report["would_delete_rows"].values()
    )
    assert {
        "abuse_rate_counters",
        "abuse_security_settings",
        "inference_budget",
    }.issubset(report["protected_shared_tables"])
    assert _counts(store) == before


def test_apply_purges_old_inactive_tenant_and_every_child_but_not_shared_state(store):
    _create_tenant(store, "old-complete", 40)
    _seed_every_tenant_table(store, "old-complete")
    with store.connection(write=True) as connection:
        connection.execute(budget.insert().values(id="2026-09-11", reserved_calls=11))
        connection.execute(
            rate_counters.insert().values(key="global", count=4, expires=99_999)
        )
        connection.execute(
            security_settings.insert().values(key="mode", value="strict")
        )

    report = prune_expired_tenants(
        store, retained_days=30, limit=20, apply=True, as_of=AS_OF
    )

    assert report["mode"] == "apply"
    assert report["eligible_tenant_count"] == 1
    assert report["deleted_rows"] == report["would_delete_rows"]
    assert all(count == 1 for count in report["deleted_rows"].values())
    assert not _tenant_exists(store, "old-complete")
    with store.connection() as connection:
        for table in metadata.tables.values():
            if "tenant_id" in table.c:
                assert connection.execute(
                    select(func.count())
                    .select_from(table)
                    .where(table.c.tenant_id == "old-complete")
                ).scalar_one() == 0
        assert connection.execute(select(budget.c.reserved_calls)).scalar_one() == 11
        assert connection.execute(select(rate_counters.c.count)).scalar_one() == 4
        assert connection.execute(select(security_settings.c.value)).scalar_one() == "strict"


def test_recent_and_each_active_job_type_are_retained(store):
    for tenant_id, age in (
        ("recent", 2),
        ("active-plan", 40),
        ("active-scenario", 41),
        ("active-conversation", 42),
        ("active-research", 43),
        ("eligible", 44),
    ):
        _create_tenant(store, tenant_id, age)

    with store.connection(write=True) as connection:
        connection.execute(
            runs.insert().values(
                id="active-plan-run",
                tenant_id="active-plan",
                idempotency_key="active-plan-key",
                request_hash="hash",
                status="CREATED",
                payload={},
            )
        )
        connection.execute(
            branches.insert().values(
                id="active-scenario-branch",
                tenant_id="active-scenario",
                idempotency_key="active-scenario-key",
                request_hash="hash",
                status="RUNNING",
                payload={},
            )
        )
        connection.execute(
            conversations.insert().values(
                id="active-conversation-parent",
                tenant_id="active-conversation",
                idempotency_key="active-conversation-parent-key",
                request_hash="hash",
                status="OPEN",
                payload={},
            )
        )
        connection.execute(
            conversation_requests.insert().values(
                id="active-conversation-request",
                conversation_id="active-conversation-parent",
                tenant_id="active-conversation",
                idempotency_key="active-conversation-request-key",
                request_hash="hash",
                status="QUEUED",
                payload={},
            )
        )
        connection.execute(
            research_sessions.insert().values(
                id="active-research-session",
                tenant_id="active-research",
                idempotency_key="active-research-session-key",
                request_hash="hash",
                payload={},
            )
        )
        connection.execute(
            research_jobs.insert().values(
                id="active-research-job",
                tenant_id="active-research",
                session_id="active-research-session",
                version=1,
                status="RUNNING",
                payload={},
            )
        )

    report = prune_expired_tenants(
        store, retained_days=30, limit=20, apply=True, as_of=AS_OF
    )

    assert report["eligible_tenant_ids"] == ["eligible"]
    skipped = {
        row["tenant_id"]: row["active_job_types"]
        for row in report["skipped_active"]
    }
    assert skipped == {
        "active-research": ["research"],
        "active-conversation": ["conversation"],
        "active-scenario": ["scenario"],
        "active-plan": ["planning_mission"],
    }
    assert not _tenant_exists(store, "eligible")
    for tenant_id in (
        "recent",
        "active-plan",
        "active-scenario",
        "active-conversation",
        "active-research",
    ):
        assert _tenant_exists(store, tenant_id)


def test_invocation_limit_bounds_candidate_deletion(store):
    for tenant_id, age in (("oldest", 60), ("middle", 50), ("newest-old", 40)):
        _create_tenant(store, tenant_id, age)

    report = prune_expired_tenants(
        store, retained_days=30, limit=2, apply=True, as_of=AS_OF
    )

    assert report["eligible_tenant_ids"] == ["oldest", "middle"]
    assert not _tenant_exists(store, "oldest")
    assert not _tenant_exists(store, "middle")
    assert _tenant_exists(store, "newest-old")


@pytest.mark.parametrize(
    ("retained_days", "limit"),
    [
        (6, 1),
        (True, 1),
        (MAX_RETAINED_DAYS + 1, 1),
        (7, 0),
        (7, True),
        (7, MAX_TENANTS_PER_INVOCATION + 1),
    ],
)
def test_explicit_input_bounds(retained_days, limit, store):
    with pytest.raises(ValueError):
        prune_expired_tenants(
            store,
            retained_days=retained_days,
            limit=limit,
            as_of=AS_OF,
        )


def test_naive_as_of_is_rejected(store):
    with pytest.raises(ValueError, match="timezone"):
        prune_expired_tenants(store, as_of=datetime(2026, 9, 11))


def test_operator_cli_is_dry_run_by_default_and_rejects_out_of_range_values():
    defaults = parser().parse_args([])
    assert defaults.apply is False
    assert defaults.retained_days == 30
    assert defaults.limit == 100
    with pytest.raises(SystemExit):
        parser().parse_args(["--retained-days", "6"])
    with pytest.raises(SystemExit):
        parser().parse_args(["--limit", "501"])
