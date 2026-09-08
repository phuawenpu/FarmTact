"""Reservations crossing midnight must never refund another day's allowance."""
from sqlalchemy import select
import pytest

from services.api.store import Store, budget


def test_reconciliation_uses_original_reservation_day(monkeypatch):
    store = Store("sqlite://")
    previous, today = "2026-09-08", "2026-09-09"
    assert store.reserve_calls(10, 48, previous)
    assert store.reserve_calls(48, 48, today)
    monkeypatch.setattr("services.api.store.now", lambda: today + "T00:00:01+00:00")
    store.release_unused_calls(3, previous)
    with store.engine.connect() as connection:
        values = dict(connection.execute(select(budget.c.id, budget.c.reserved_calls)).all())
    assert values == {previous: 7, today: 48}
    assert not store.reserve_calls(1)


@pytest.mark.parametrize("limit", [0, 49, 1000, True])
def test_global_daily_ceiling_cannot_be_raised_by_caller(limit):
    with pytest.raises(ValueError):
        Store("sqlite://").reserve_calls(1, limit)
