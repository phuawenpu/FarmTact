from __future__ import annotations

from datetime import date
import threading

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import select

from services.api.edition_control import (
    ControlUnavailable, RemoteControl, control_reservations, create_control_router,
)
from services.api.security import AI_IP_BURST, AI_TENANT, Limited
from services.api.store import Store, budget


SECRET = "s" * 40
DAY = "2026-09-09"


@pytest.fixture
def control():
    store = Store("sqlite://")
    app = FastAPI()
    app.include_router(create_control_router(store, SECRET))
    return store, TestClient(app)


def post(client, operation, payload, secret=SECRET):
    return client.post(f"/_control/{operation}", json=payload, headers={"Authorization": f"Bearer {secret}"})


def reservation(edition="v1", key="reserve-1", count=8):
    return {"edition_id": edition, "reservation_id": key, "day": DAY, "count": count}


def test_control_auth_and_strict_bounded_schema(control):
    _store, client = control
    assert client.post("/_control/reserve", json=reservation()).status_code == 401
    assert post(client, "reserve", reservation(), "wrong").status_code == 401
    assert post(client, "reserve", {**reservation(), "count": 17}).status_code == 422
    assert post(client, "reserve", {**reservation(), "secret": SECRET}).status_code == 422
    unknown = {"edition_id": "v1", "charges": [{"rule": "invented", "principal": "x"}]}
    assert post(client, "consume", unknown).status_code == 422
    assert post(client, "reserve", reservation("v999")).status_code == 409


def test_shared_budget_is_atomic_and_reservations_are_idempotent(control):
    store, client = control
    first = post(client, "reserve", reservation(count=16))
    assert first.json()["accepted"] is True
    assert post(client, "reserve", reservation(count=16)).json() == first.json()
    assert post(client, "reserve", reservation(key="reserve-2", count=16)).json()["accepted"] is True
    assert post(client, "reserve", reservation("v2", "reserve-3", 16)).json()["accepted"] is True
    assert post(client, "reserve", reservation("v2", "reserve-4", 1)).json()["accepted"] is False
    assert post(client, "reserve", reservation(count=7)).status_code == 409
    with store.engine.connect() as connection:
        assert connection.execute(select(budget.c.reserved_calls).where(budget.c.id == DAY)).scalar_one() == 48
        assert len(connection.execute(select(control_reservations)).all()) == 4


def test_release_is_idempotent_and_cannot_exceed_own_reservation(control):
    store, client = control
    assert post(client, "reserve", reservation(count=8)).json()["accepted"]
    release = {"edition_id": "v1", "reservation_id": "reserve-1", "release_id": "release-1", "day": DAY, "count": 3}
    assert post(client, "release", release).json()["released"] == 3
    assert post(client, "release", release).json()["released"] == 3
    assert post(client, "release", {**release, "release_id": "release-2", "count": 6}).status_code == 409
    assert post(client, "release", {**release, "edition_id": "v2", "release_id": "release-3"}).status_code == 409
    with store.engine.connect() as connection:
        assert connection.execute(select(budget.c.reserved_calls).where(budget.c.id == DAY)).scalar_one() == 5


def test_abuse_counters_share_ip_but_scope_tenant_by_edition(control):
    _store, client = control
    def consume(edition, rule, principal):
        return post(client, "consume", {"edition_id": edition, "charges": [{"rule": rule.name, "principal": principal}]})

    for _ in range(AI_IP_BURST.limit):
        assert consume("v1", AI_IP_BURST, "203.0.113.8").status_code == 200
    blocked = consume("v2", AI_IP_BURST, "203.0.113.8")
    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"] == str(AI_IP_BURST.seconds)

    for _ in range(AI_TENANT.limit):
        assert consume("v1", AI_TENANT, "tenant-1").status_code == 200
    assert consume("v1", AI_TENANT, "tenant-1").status_code == 429
    assert consume("v2", AI_TENANT, "tenant-1").status_code == 200


def test_remote_adapter_matches_store_and_limiter_contracts():
    calls = []
    def transport(url, payload, headers, timeout):
        calls.append((url, payload, headers, timeout))
        if url.endswith("/reserve"):
            return 200, {"accepted": True, "reservation_id": payload["reservation_id"]}
        if url.endswith("/release"):
            return 200, {"released": payload["count"]}
        return 429, {"detail": {"limit": AI_IP_BURST.name, "retry_after": 9}}

    remote = RemoteControl("https://control.invalid", SECRET, "v1", transport=transport)
    assert remote.reserve_calls(8, 48, DAY)
    remote.release_unused_calls(3, DAY)
    with pytest.raises(Limited) as blocked:
        remote.consume([(AI_IP_BURST, "203.0.113.8")])
    assert blocked.value.rule == AI_IP_BURST.name
    assert calls[0][2]["Authorization"] == f"Bearer {SECRET}"
    assert calls[1][1]["reservation_id"] == calls[0][1]["reservation_id"]

    assert remote.reserve_calls(5, 48, DAY)
    remote.release_unused_calls(0, DAY)
    with pytest.raises(ControlUnavailable):
        remote.release_unused_calls(1, DAY)
    with pytest.raises(ValueError):
        remote.reserve_calls(17, 48, DAY)


def test_remote_reservation_fails_closed_without_control():
    def unavailable(*_args):
        raise TimeoutError
    remote = RemoteControl("https://control.invalid", SECRET, "v1", transport=unavailable)
    assert remote.reserve_calls(8, 48, DAY) is False
    with pytest.raises(ControlUnavailable):
        remote.consume([(AI_IP_BURST, "203.0.113.8")])


def test_concurrent_editions_never_exceed_daily_ceiling(control):
    store, client = control
    barrier = threading.Barrier(8)
    def reserve_one(index):
        barrier.wait()
        return post(client, "reserve", reservation(f"v{index % 2 + 1}", f"r-{index}", 8)).json()["accepted"]
    threads = []
    results = [None] * 8
    for index in range(8):
        thread = threading.Thread(target=lambda i=index: results.__setitem__(i, reserve_one(i)))
        threads.append(thread); thread.start()
    for thread in threads:
        thread.join()
    assert sum(results) == 6
    with store.engine.connect() as connection:
        assert connection.execute(select(budget.c.reserved_calls).where(budget.c.id == DAY)).scalar_one() == 48
