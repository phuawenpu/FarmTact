"""Real-PostgreSQL atomicity checks for persistent abuse counters.

Cleanup removes only the exact opaque counter keys created by each test.  The
shared salt, settings row, application data, and tables are never removed.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import secrets
import threading

import pytest
from sqlalchemy import delete, select

from services.api.security import AbuseLimits, Limited, Rule, rate_counters
from services.api.store import Store


class MutableClock:
    def __init__(self, value: float = 2_000_000.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


@pytest.fixture
def postgres_rate_context():
    store = Store()
    assert store.engine.dialect.name == "postgresql", "Abuse review requires local PostgreSQL"
    clock = MutableClock()
    rate = AbuseLimits(store, clock=clock, trust_fly=False)
    # Keep production cleanup from touching unrelated expired rows while these
    # tests use an artificial epoch. Teardown still removes our exact keys.
    rate.last_cleanup = clock.value
    owned_keys: set[str] = set()

    def principal(rule: Rule) -> str:
        value = f"a11-rate-{secrets.token_hex(16)}"
        owned_keys.add(rate.opaque(f"{rule.name}:{value}"))
        return value

    def own(rule: Rule, value: str) -> str:
        owned_keys.add(rate.opaque(f"{rule.name}:{value}"))
        return value

    yield store, clock, rate, principal, own

    if owned_keys:
        with store.engine.begin() as connection:
            connection.execute(delete(rate_counters).where(rate_counters.c.key.in_(owned_keys)))
    store.engine.dispose()


def persisted_count(rate: AbuseLimits, rule: Rule, principal: str) -> int | None:
    key = rate.opaque(f"{rule.name}:{principal}")
    with rate.store.engine.connect() as connection:
        return connection.execute(
            select(rate_counters.c.count).where(rate_counters.c.key == key)
        ).scalar_one_or_none()


def test_postgres_concurrent_instances_never_exceed_limit(postgres_rate_context) -> None:
    store, clock, rate, new_principal, own = postgres_rate_context
    rule = Rule(f"review_pg_concurrent_{secrets.token_hex(8)}", 7, 120)
    principal = new_principal(rule)
    instances = [AbuseLimits(store, clock=clock, trust_fly=False) for _ in range(12)]
    for instance in instances:
        instance.last_cleanup = clock.value
    own(rule, principal)
    barrier = threading.Barrier(24)

    def consume(index: int) -> bool:
        barrier.wait(timeout=10)
        try:
            instances[index % len(instances)].consume([(rule, principal)])
            return True
        except Limited as error:
            assert error.rule == rule.name
            return False

    with ThreadPoolExecutor(max_workers=24) as pool:
        accepted = list(pool.map(consume, range(24)))

    assert sum(accepted) == rule.limit
    assert persisted_count(rate, rule, principal) == rule.limit


def test_postgres_rejected_group_rolls_back_every_counter(postgres_rate_context) -> None:
    _store, _clock, rate, new_principal, _own = postgres_rate_context
    first = Rule(f"review_pg_a_{secrets.token_hex(8)}", 4, 90)
    blocked = Rule(f"review_pg_z_{secrets.token_hex(8)}", 1, 90)
    first_principal = new_principal(first)
    blocked_principal = new_principal(blocked)
    rate.consume([(blocked, blocked_principal)])

    with pytest.raises(Limited) as rejected:
        rate.consume([(first, first_principal), (blocked, blocked_principal)])
    assert rejected.value.rule == blocked.name
    assert persisted_count(rate, first, first_principal) is None
    assert persisted_count(rate, blocked, blocked_principal) == 1


def test_postgres_counter_survives_recreation_and_resets_only_after_expiry(
    postgres_rate_context,
) -> None:
    store, clock, rate, new_principal, own = postgres_rate_context
    rule = Rule(f"review_pg_restart_{secrets.token_hex(8)}", 2, 75)
    principal = new_principal(rule)
    rate.consume([(rule, principal)])

    restarted = AbuseLimits(store, clock=clock, trust_fly=False)
    restarted.last_cleanup = clock.value
    assert restarted.salt == rate.salt
    own(rule, principal)
    restarted.consume([(rule, principal)])
    with pytest.raises(Limited) as rejected:
        second_restart = AbuseLimits(store, clock=clock, trust_fly=False)
        second_restart.last_cleanup = clock.value
        second_restart.consume([(rule, principal)])
    assert rejected.value.retry_after == 75
    assert persisted_count(rate, rule, principal) == 2

    clock.value += 76
    after_expiry = AbuseLimits(store, clock=clock, trust_fly=False)
    after_expiry.last_cleanup = clock.value
    after_expiry.consume([(rule, principal)])
    assert persisted_count(rate, rule, principal) == 1
