"""A11 real-PostgreSQL concurrency and tenant-integrity checks.

Every test creates opaque tenants and removes only those exact tenant rows and
their dependent farm/run/event records. The shared schema is never dropped.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
import secrets
import threading

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import IntegrityError

from packages.contracts import content_hash
from packages.fixtures import synthetic_farm
from services.api.app import create_app
from services.api.store import Store, events, farms, now, runs, tenants


@pytest.fixture
def postgres_store():
    store = Store()
    assert store.engine.dialect.name == "postgresql", "Concurrency review requires the FarmTact PostgreSQL service"
    owned_tenants: list[str] = []

    def new_tenant() -> tuple[str, str]:
        tenant, token = store.new_session()
        owned_tenants.append(tenant)
        return tenant, token

    yield store, new_tenant

    # Delete only records attached to the opaque tenants allocated above.
    if owned_tenants:
        with store.engine.begin() as connection:
            connection.execute(
                update(runs).where(runs.c.tenant_id.in_(owned_tenants)).values(status="A11_TEST_CLEANUP")
            )
            connection.execute(delete(events).where(events.c.tenant_id.in_(owned_tenants)))
            connection.execute(delete(runs).where(runs.c.tenant_id.in_(owned_tenants)))
            connection.execute(delete(farms).where(farms.c.tenant_id.in_(owned_tenants)))
            connection.execute(delete(tenants).where(tenants.c.id.in_(owned_tenants)))
    store.engine.dispose()


def _run_payload(run_id: str, *, status: str = "A11_TEST_HOLD", **extra) -> dict:
    return {
        "id": run_id,
        "status": status,
        "created_at": now(),
        "warnings": [],
        **extra,
    }


def test_concurrent_same_idempotency_key_creates_exactly_once(postgres_store) -> None:
    store, new_tenant = postgres_store
    tenant, _ = new_tenant()
    barrier = threading.Barrier(8)

    def create(index: int):
        barrier.wait(timeout=10)
        return store.create_run(
            tenant,
            "a11-same-key",
            "a11-same-request-hash",
            _run_payload(f"a11pg-{secrets.token_hex(12)}", caller=index),
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(create, range(8)))

    returned_ids = {payload["id"] for payload, _created in results}
    assert len(returned_ids) == 1
    assert sum(created for _payload, created in results) == 1
    with store.engine.connect() as connection:
        count = connection.execute(
            select(func.count()).select_from(runs).where(
                runs.c.tenant_id == tenant,
                runs.c.idempotency_key == "a11-same-key",
            )
        ).scalar_one()
    assert count == 1


def test_concurrent_same_replan_is_idempotent_and_versions_once(postgres_store, monkeypatch) -> None:
    store, new_tenant = postgres_store
    tenant, token = new_tenant()
    initial = store.save_farm(tenant, synthetic_farm().model_dump(mode="json"))
    parent_id = f"a11pg-parent-{secrets.token_hex(10)}"
    parent = _run_payload(
        parent_id,
        status="ACCEPTED_FOR_SIMULATION",
        input_version=initial["version"],
        input_hash=content_hash(initial),
        input_snapshot=initial,
        council_requested=False,
        with_vision=False,
        strategies=[],
        claims=[],
        events=[],
        execution_mode="test",
        data_mode="synthetic_demo",
    )
    store.create_run(tenant, "a11-parent-key", "a11-parent-hash", parent)

    # Keep the shared service worker from consuming this review-only child. The
    # create/idempotency transaction remains the production Store implementation.
    original_create_run = store.create_run

    def create_held_run(selected_tenant, key, request_hash, payload):
        if key == "a11-concurrent-replan":
            payload = dict(payload, status="A11_TEST_HOLD")
        return original_create_run(selected_tenant, key, request_hash, payload)

    monkeypatch.setattr(store, "create_run", create_held_run)

    # Ensure both requests complete their pre-transaction idempotency lookup before
    # either acquires the tenant row lock. The transactions themselves remain real.
    entry_barrier = threading.Barrier(2)
    original_transaction = store.transaction

    @contextmanager
    def synchronized_transaction(selected_tenant=None):
        entry_barrier.wait(timeout=10)
        with original_transaction(selected_tenant) as connection:
            yield connection

    monkeypatch.setattr(store, "transaction", synchronized_transaction)
    app = create_app(store, start_worker=False)
    headers = {
        "Idempotency-Key": "a11-concurrent-replan",
        "Cookie": f"farmtact_session={token}",
    }

    with TestClient(app) as client:
        def request_replan():
            return client.post(
                f"/api/v1/planning-runs/{parent_id}/replan",
                json={"disruption": "crop_delay", "council": False},
                headers=headers,
            )

        with ThreadPoolExecutor(max_workers=2) as pool:
            responses = list(pool.map(lambda _: request_replan(), range(2)))

    assert [response.status_code for response in responses] == [202, 202]
    bodies = [response.json() for response in responses]
    assert len({body["id"] for body in bodies}) == 1
    assert {body["reused"] for body in bodies} == {False, True}
    with store.engine.connect() as connection:
        versions = connection.execute(
            select(farms.c.version).where(farms.c.tenant_id == tenant).order_by(farms.c.version)
        ).scalars().all()
        child_count = connection.execute(
            select(func.count()).select_from(runs).where(
                runs.c.tenant_id == tenant,
                runs.c.idempotency_key == "a11-concurrent-replan",
            )
        ).scalar_one()
    assert versions == [1, 2]
    assert child_count == 1


def test_concurrent_event_append_has_contiguous_unique_sequences(postgres_store) -> None:
    store, new_tenant = postgres_store
    tenant, _ = new_tenant()
    run_id = f"a11pg-events-{secrets.token_hex(10)}"
    store.create_run(tenant, "a11-events-key", "a11-events-hash", _run_payload(run_id))
    count = 16
    barrier = threading.Barrier(count)

    def append(index: int):
        barrier.wait(timeout=10)
        return store.append_event(tenant, run_id, "concurrent_test", {"caller": index})

    with ThreadPoolExecutor(max_workers=count) as pool:
        emitted = list(pool.map(append, range(count)))

    assert sorted(event["sequence"] for event in emitted) == list(range(1, count + 1))
    persisted = store.get_events(tenant, run_id)
    assert [event["sequence"] for event in persisted] == list(range(1, count + 1))
    assert len({event["body"]["caller"] for event in persisted}) == count


def test_postgres_fk_denies_mismatched_event_tenant(postgres_store) -> None:
    store, new_tenant = postgres_store
    tenant_a, _ = new_tenant()
    tenant_b, _ = new_tenant()
    run_id = f"a11pg-owner-{secrets.token_hex(10)}"
    store.create_run(tenant_a, "a11-owner-key", "a11-owner-hash", _run_payload(run_id))

    with pytest.raises(ValueError, match="not owned"):
        store.append_event(tenant_b, run_id, "mismatch", {})

    mismatched = {
        "run_id": run_id,
        "sequence": 99,
        "occurred_at": now(),
        "event_type": "direct_fk_probe",
        "schema_version": "1.0",
        "body": {},
    }
    with pytest.raises(IntegrityError):
        with store.engine.begin() as connection:
            connection.execute(
                events.insert().values(
                    run_id=run_id,
                    tenant_id=tenant_b,
                    sequence=99,
                    payload=mismatched,
                )
            )
    assert store.get_events(tenant_b, run_id) == []
