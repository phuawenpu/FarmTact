"""Adversarial admission-control checks using isolated in-memory databases.

These tests deliberately exercise security boundaries through both the ASGI
middleware and the lower-level durable limiter.  No provider call is made.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from starlette.requests import Request

from services.api.app import MissionRequest, create_app, create_mission
from services.api.conversation_store import (
    ConversationStore,
    conversation_requests,
)
from services.api.security import (
    AI_IP_BURST,
    AI_IP_HOUR,
    AI_TENANT,
    SESSION_IP,
    STREAM_IP,
    AbuseLimits,
    AbuseMiddleware,
    Limited,
    Rule,
    client_network,
    rate_counters,
)
from services.api.store import Store, now, runs, tenants


class MutableClock:
    def __init__(self, value: float = 1_000_000.0) -> None:
        self.value = value

    def __call__(self) -> float:
        return self.value


def request_for(
    path: str,
    *,
    peer: str = "203.0.113.8",
    method: str = "GET",
    headers: list[tuple[bytes, bytes]] | None = None,
    query: bytes = b"",
) -> Request:
    return Request(
        {
            "type": "http",
            "asgi": {"version": "3.0"},
            "http_version": "1.1",
            "scheme": "http",
            "method": method,
            "path": path,
            "raw_path": path.encode(),
            "root_path": "",
            "query_string": query,
            "headers": headers or [],
            "client": (peer, 43210),
            "server": ("testserver", 80),
        }
    )


def counter_value(limits: AbuseLimits, rule: Rule, principal: str) -> int | None:
    key = limits.opaque(f"{rule.name}:{principal}")
    with limits.store.engine.connect() as connection:
        return connection.execute(
            select(rate_counters.c.count).where(rate_counters.c.key == key)
        ).scalar_one_or_none()


def test_client_identity_ignores_spoofed_forwarding_and_groups_ipv6_64() -> None:
    spoofed = [(b"x-forwarded-for", b"198.51.100.1"), (b"fly-client-ip", b"198.51.100.2")]
    assert client_network(request_for("/", headers=spoofed), trust_fly=False) == "203.0.113.8"
    assert client_network(request_for("/", peer="198.51.100.9", headers=spoofed), trust_fly=True) == "198.51.100.9"

    first = request_for("/", peer="127.0.0.1", headers=[(b"fly-client-ip", b"2001:db8:abcd:12::1")])
    rotated = request_for("/", peer="172.20.1.4", headers=[(b"fly-client-ip", b"2001:db8:abcd:12:ffff::9")])
    other = request_for("/", peer="fdaa::1", headers=[(b"fly-client-ip", b"2001:db8:abcd:13::1")])
    assert client_network(first, trust_fly=True) == "2001:db8:abcd:12::/64"
    assert client_network(rotated, trust_fly=True) == "2001:db8:abcd:12::/64"
    assert client_network(other, trust_fly=True) == "2001:db8:abcd:13::/64"

    duplicate = request_for(
        "/",
        peer="127.0.0.1",
        headers=[(b"fly-client-ip", b"203.0.113.1"), (b"fly-client-ip", b"203.0.113.2")],
    )
    with pytest.raises(ValueError, match="Missing trusted client address"):
        client_network(duplicate, trust_fly=True)
    with pytest.raises(ValueError, match="Missing trusted client address"):
        client_network(request_for("/", peer="127.0.0.1"), trust_fly=True)
    with pytest.raises(ValueError, match="Invalid trusted client address"):
        client_network(
            request_for("/", peer="127.0.0.1", headers=[(b"fly-client-ip", b"not-an-ip")]),
            trust_fly=True,
        )


def test_consume_is_atomic_and_counters_expire_and_survive_restart() -> None:
    store = Store("sqlite://")
    clock = MutableClock()
    limits = AbuseLimits(store, clock=clock, trust_fly=False)
    charged = Rule("review_atomic_a", 5, 60)
    blocker = Rule("review_atomic_z", 1, 60)
    limits.consume([(blocker, "blocked")])

    with pytest.raises(Limited) as rejected:
        limits.consume([(charged, "must-roll-back"), (blocker, "blocked")])
    assert rejected.value.rule == blocker.name
    assert counter_value(limits, charged, "must-roll-back") is None
    assert counter_value(limits, blocker, "blocked") == 1

    restart_rule = Rule("review_restart", 2, 90)
    limits.consume([(restart_rule, "same-principal")])
    restarted = AbuseLimits(store, clock=clock, trust_fly=False)
    restarted.consume([(restart_rule, "same-principal")])
    with pytest.raises(Limited):
        restarted.consume([(restart_rule, "same-principal")])
    assert restarted.salt == limits.salt

    clock.value += 91
    restarted.consume([(restart_rule, "same-principal")])
    assert counter_value(restarted, restart_rule, "same-principal") == 1


def test_rotating_sessions_xff_and_fly_headers_cannot_bypass_ip_burst_limit() -> None:
    store = Store("sqlite://")
    app = create_app(store, start_worker=False)
    tokens = [store.new_session()[1] for _ in range(7)]
    with TestClient(app, client=("203.0.113.44", 50000)) as client:
        for index, token in enumerate(tokens):
            client.cookies.clear()
            client.cookies.set("farmtact_session", token)
            response = client.post(
                "/api/v1/conversations/missing/messages",
                json={"content": "probe"},
                headers={
                    "Idempotency-Key": f"rotated-{index}",
                    "X-Forwarded-For": f"198.51.100.{index + 1}",
                    "Fly-Client-IP": f"192.0.2.{index + 1}",
                },
            )
            if index < AI_IP_BURST.limit:
                assert response.status_code == 404
            else:
                assert response.status_code == 429
                assert response.json()["limit"] == AI_IP_BURST.name
                assert response.headers["Retry-After"] == "60"


def test_rotating_ips_cannot_bypass_ai_session_hour_limit() -> None:
    store = Store("sqlite://")
    clock = MutableClock()
    limits = AbuseLimits(store, clock=clock, trust_fly=False)
    tenant, token = store.new_session()
    cookie = [(b"cookie", f"farmtact_session={token}".encode())]
    for index in range(AI_TENANT.limit):
        limits.check(
            request_for(
                "/api/v1/planning-runs",
                peer=f"203.0.113.{index + 1}",
                method="POST",
                headers=cookie,
            )
        )
    with pytest.raises(Limited) as rejected:
        limits.check(
            request_for(
                "/api/v1/planning-runs",
                peer="203.0.113.200",
                method="POST",
                headers=cookie,
            )
        )
    assert rejected.value.rule == AI_TENANT.name
    assert counter_value(limits, AI_TENANT, tenant) == AI_TENANT.limit


def test_ai_hour_limit_remains_after_burst_windows_expire() -> None:
    store = Store("sqlite://")
    clock = MutableClock()
    limits = AbuseLimits(store, clock=clock, trust_fly=False)
    tenant, token = store.new_session()
    cookie = [(b"cookie", f"farmtact_session={token}".encode())]
    # Use different tenants so the twelve-per-session ceiling cannot mask the
    # twenty-per-network hourly ceiling under test.
    tokens = [token] + [store.new_session()[1] for _ in range(AI_IP_HOUR.limit)]
    for index in range(AI_IP_HOUR.limit):
        limits.check(
            request_for(
                "/api/v1/planning-runs",
                peer="198.51.100.77",
                method="POST",
                headers=[(b"cookie", f"farmtact_session={tokens[index]}".encode())],
            )
        )
        clock.value += AI_IP_BURST.seconds + 1
    with pytest.raises(Limited) as rejected:
        limits.check(
            request_for(
                "/api/v1/planning-runs",
                peer="198.51.100.77",
                method="POST",
                headers=[(b"cookie", f"farmtact_session={tokens[-1]}".encode())],
            )
        )
    assert rejected.value.rule == AI_IP_HOUR.name


@pytest.mark.parametrize(
    ("kind", "path_template", "payload"),
    [
        ("planning", "/api/v1/planning-runs", {"council": True}),
        ("replan", "/api/v1/planning-runs/{parent}/replan", {"disruption": "crop_delay"}),
        ("message", "/api/v1/conversations/{conversation}/messages", {"content": "Explain the risk."}),
        (
            "invite",
            "/api/v1/conversations/{conversation}/invite",
            {"advisor": "ravi", "question": "Challenge this.", "reply_to": "seed-advisor"},
        ),
        ("council", "/api/v1/conversations/{conversation}/council", {"question": "Compare choices."}),
    ],
)
def test_every_ai_route_returns_429_before_queueing(
    kind: str, path_template: str, payload: dict, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = Store("sqlite://")
    app = create_app(store, start_worker=False)
    peer = "203.0.113.61"
    with TestClient(app, client=(peer, 50000)) as client:
        assert client.get("/api/v1/bootstrap").status_code == 200
        tenant = store.authenticate(client.cookies.get("farmtact_session"))
        assert tenant

        parent = create_mission(store, tenant, MissionRequest(council=False), "review-parent")["id"]
        parent_run = store.get_run(tenant, parent)
        parent_run["status"] = "ACCEPTED_FOR_SIMULATION"
        store.save_run(tenant, parent_run)

        created = client.post(
            "/api/v1/conversations",
            json={"advisor": "mei"},
            headers={"Idempotency-Key": "review-conversation"},
        )
        assert created.status_code == 201
        conversation = created.json()["id"]
        ConversationStore(store).append_message(
            tenant,
            conversation,
            {
                "id": "seed-advisor",
                "speaker": "advisor",
                "speaker_id": "mei",
                "advisor_role": "crop_scientist",
                "content": "Stored review fixture.",
                "created_at": now(),
            },
        )

        limits = AbuseLimits(store, clock=MutableClock(), trust_fly=False)
        app.state.abuse_limits = limits
        for _ in range(AI_IP_BURST.limit):
            limits.consume([(AI_IP_BURST, peer), (AI_IP_HOUR, peer)])
        before_farm_version = store.latest_farm(tenant)["version"]
        with store.engine.connect() as connection:
            before_runs = connection.execute(select(func.count()).select_from(runs)).scalar_one()
            before_requests = connection.execute(
                select(func.count()).select_from(conversation_requests)
            ).scalar_one()

        monkeypatch.setattr(
            store,
            "reserve_calls",
            lambda *_: pytest.fail("rate-rejected request reached inference reservation"),
        )
        path = path_template.format(parent=parent, conversation=conversation)
        response = client.post(
            path,
            json=payload,
            headers={"Idempotency-Key": f"blocked-{kind}"},
        )
        assert response.status_code == 429
        assert response.json()["limit"] == AI_IP_BURST.name
        assert response.headers["Retry-After"] == "60"
        with store.engine.connect() as connection:
            assert connection.execute(select(func.count()).select_from(runs)).scalar_one() == before_runs
            assert (
                connection.execute(select(func.count()).select_from(conversation_requests)).scalar_one()
                == before_requests
            )
        assert store.latest_farm(tenant)["version"] == before_farm_version


def test_new_session_limits_cover_rotated_invalid_cookies_and_global_principal() -> None:
    store = Store("sqlite://")
    app = create_app(store, start_worker=False)
    with TestClient(app, client=("203.0.113.91", 50000)) as client:
        for index in range(SESSION_IP.limit + 1):
            client.cookies.clear()
            client.cookies.set("farmtact_session", f"invalid-rotated-{index}")
            response = client.get("/api/v1/bootstrap")
            assert response.status_code == (200 if index < SESSION_IP.limit else 429)
        with store.engine.connect() as connection:
            assert connection.execute(select(func.count()).select_from(tenants)).scalar_one() == SESSION_IP.limit

    global_store = Store("sqlite://")
    limits = AbuseLimits(global_store, clock=MutableClock(), trust_fly=False)
    for index in range(100):
        octet_2, octet_3 = divmod(index, 250)
        limits.check(request_for("/api/v1/bootstrap", peer=f"198.18.{octet_2}.{octet_3 + 1}"))
    with pytest.raises(Limited) as rejected:
        limits.check(request_for("/api/v1/bootstrap", peer="198.19.0.1"))
    assert rejected.value.rule == "new_session_global"


@pytest.mark.parametrize(
    ("query", "accept"),
    [
        (b"stream=1", None),
        (b"stream=TrUe", None),
        (b"stream=ON", None),
        (b"stream=YeS", None),
        (b"", b"application/json, Text/Event-Stream"),
    ],
)
def test_conversation_stream_modes_get_open_rate_limit(
    query: bytes, accept: bytes | None
) -> None:
    store = Store("sqlite://")
    limits = AbuseLimits(store, clock=MutableClock(), trust_fly=False)
    headers = [(b"accept", accept)] if accept else []
    request = request_for(
        "/api/v1/conversations/review/events",
        peer="203.0.113.101",
        headers=headers,
        query=query,
    )
    for _ in range(STREAM_IP.limit):
        limits.check(request)
    with pytest.raises(Limited) as rejected:
        limits.check(request)
    assert rejected.value.rule == STREAM_IP.name


def test_unknown_probe_limit_strict_origin_host_and_docs_disabled() -> None:
    store = Store("sqlite://")
    app = create_app(store, start_worker=False)
    with TestClient(app, client=("203.0.113.111", 50000)) as client:
        for index in range(30):
            assert client.get(f"/unknown-probe-{index}").status_code == 404
        response = client.get("/unknown-probe-blocked")
        assert response.status_code == 429
        assert response.json()["limit"] == "probe_ip"

    origin_store = Store("sqlite://")
    origin_app = create_app(origin_store, start_worker=False)
    with TestClient(origin_app, client=("203.0.113.112", 50000)) as client:
        origin_app.state.abuse_limits = AbuseLimits(
            origin_store,
            trust_fly=False,
            public_origin="https://farm.example",
        )
        assert client.get("/api/v1/bootstrap", headers={"Host": "evil.example"}).status_code == 403
        bootstrap = client.get("/api/v1/bootstrap", headers={"Host": "farm.example"})
        assert bootstrap.status_code == 200
        assert client.post(
            "/api/v1/imports",
            json={"fixture": "synthetic_demo"},
            headers={"Host": "farm.example", "Origin": "http://farm.example"},
        ).status_code == 403
        assert client.post(
            "/api/v1/imports",
            json={"fixture": "synthetic_demo"},
            headers={"Host": "farm.example", "Origin": "https://farm.example", "Sec-Fetch-Site": "cross-site"},
        ).status_code == 403
        assert client.post(
            "/api/v1/imports",
            json={"fixture": "synthetic_demo"},
            headers={"Host": "farm.example", "Origin": "https://farm.example", "Idempotency-Key": "origin-checked-import"},
        ).status_code == 201
        for path in ("/docs", "/redoc", "/openapi.json"):
            assert client.get(path, headers={"Host": "farm.example"}).status_code == 404


def test_admission_database_failure_is_fail_closed_before_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    store = Store("sqlite://")
    app = create_app(store, start_worker=False)
    with TestClient(app, client=("203.0.113.121", 50000)) as client:
        assert client.get("/api/v1/bootstrap").status_code == 200

        def unavailable(_request: Request) -> str:
            raise RuntimeError("database unavailable")

        monkeypatch.setattr(app.state.abuse_limits, "check", unavailable)
        monkeypatch.setattr(store, "latest_farm", lambda *_: pytest.fail("endpoint ran after admission failure"))
        response = client.get("/api/v1/crops")
        assert response.status_code == 503
        assert response.json() == {"detail": "Request admission temporarily unavailable"}


def test_server_rejects_session_older_than_24_hours_and_bootstrap_replaces_it() -> None:
    store = Store("sqlite://")
    app = create_app(store, start_worker=False)
    with TestClient(app, client=("203.0.113.131", 50000)) as client:
        assert client.get("/api/v1/bootstrap").status_code == 200
        old_token = client.cookies.get("farmtact_session")
        old_tenant = store.authenticate(old_token)
        expired = (datetime.now(timezone.utc) - timedelta(hours=25)).isoformat()
        with store.engine.begin() as connection:
            connection.execute(update(tenants).where(tenants.c.id == old_tenant).values(created_at=expired))
        assert store.authenticate(old_token) is None
        assert client.get("/api/v1/crops").status_code == 401
        replacement = client.get("/api/v1/bootstrap")
        assert replacement.status_code == 200
        assert client.cookies.get("farmtact_session") != old_token
        assert store.authenticate(client.cookies.get("farmtact_session")) not in {None, old_tenant}


class FakeStreamLimits:
    def check(self, request: Request) -> str:
        return request.headers.get("x-review-identity", "same-ip")


class HeldStreamApp:
    def __init__(self, release: asyncio.Event) -> None:
        self.release = release
        self.entered = 0

    async def __call__(self, scope, receive, send) -> None:
        self.entered += 1
        await self.release.wait()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"done"})


def stream_scope(
    identity: str, *, conversation_query: bytes = b"", accept: bytes | None = None
) -> dict:
    conversation_stream = bool(conversation_query or accept)
    path = (
        "/api/v1/conversations/review/events"
        if conversation_stream
        else "/api/v1/planning-runs/review/events"
    )
    headers = [(b"x-review-identity", identity.encode())]
    if accept:
        headers.append((b"accept", accept))
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "scheme": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "root_path": "",
        "query_string": conversation_query,
        "headers": headers,
        "client": ("203.0.113.150", 50000),
        "server": ("testserver", 80),
        "app": SimpleNamespace(state=SimpleNamespace(abuse_limits=FakeStreamLimits())),
    }


async def invoke_stream(
    middleware: AbuseMiddleware,
    identity: str,
    *,
    conversation_query: bytes = b"",
    accept: bytes | None = None,
) -> int:
    status: list[int] = []

    async def receive() -> dict:
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message: dict) -> None:
        if message["type"] == "http.response.start":
            status.append(message["status"])

    await middleware(
        stream_scope(identity, conversation_query=conversation_query, accept=accept),
        receive,
        send,
    )
    return status[0]


def test_stream_slots_enforce_per_ip_and_global_caps_then_release() -> None:
    async def scenario() -> None:
        release = asyncio.Event()
        held = HeldStreamApp(release)
        middleware = AbuseMiddleware(held)
        active = [asyncio.create_task(invoke_stream(middleware, "same-ip")) for _ in range(4)]
        while held.entered < 4:
            await asyncio.sleep(0)
        assert await invoke_stream(middleware, "same-ip") == 429
        release.set()
        assert await asyncio.gather(*active) == [200] * 4
        assert middleware.streams == {}
        assert await invoke_stream(middleware, "same-ip") == 200

        global_release = asyncio.Event()
        global_held = HeldStreamApp(global_release)
        global_middleware = AbuseMiddleware(global_held)
        global_active = [
            asyncio.create_task(invoke_stream(global_middleware, f"ip-{index}"))
            for index in range(32)
        ]
        while global_held.entered < 32:
            await asyncio.sleep(0)
        assert await invoke_stream(global_middleware, "thirty-third") == 429
        global_release.set()
        assert await asyncio.gather(*global_active) == [200] * 32
        assert global_middleware.streams == {}

    asyncio.run(scenario())


def test_stream_lifetime_uses_the_360_second_deadline(monkeypatch: pytest.MonkeyPatch) -> None:
    import services.api.security as security_module

    deadlines: list[int] = []

    class TimeoutProbe:
        def __init__(self, seconds: int) -> None:
            deadlines.append(seconds)

        async def __aenter__(self) -> None:
            return None

        async def __aexit__(self, *_args) -> None:
            return None

    release = asyncio.Event()
    release.set()
    middleware = AbuseMiddleware(HeldStreamApp(release))
    monkeypatch.setattr(
        security_module,
        "asyncio",
        SimpleNamespace(timeout=lambda seconds: TimeoutProbe(seconds)),
    )
    assert asyncio.run(invoke_stream(middleware, "deadline-review")) == 200
    assert deadlines == [360]


@pytest.mark.parametrize(
    ("query", "accept"),
    [
        (b"stream=1", None),
        (b"stream=TrUe", None),
        (b"stream=ON", None),
        (b"stream=YeS", None),
        (b"", b"application/json, Text/Event-Stream"),
    ],
)
def test_conversation_stream_modes_use_active_slot_and_deadline(
    monkeypatch: pytest.MonkeyPatch, query: bytes, accept: bytes | None
) -> None:
    import services.api.security as security_module

    deadlines: list[int] = []

    class TimeoutProbe:
        def __init__(self, seconds: int) -> None:
            deadlines.append(seconds)

        async def __aenter__(self) -> None:
            return None

        async def __aexit__(self, *_args) -> None:
            return None

    release = asyncio.Event()
    release.set()
    middleware = AbuseMiddleware(HeldStreamApp(release))
    monkeypatch.setattr(
        security_module,
        "asyncio",
        SimpleNamespace(timeout=lambda seconds: TimeoutProbe(seconds)),
    )
    assert asyncio.run(
        invoke_stream(
            middleware,
            "conversation-sse",
            conversation_query=query,
            accept=accept,
        )
    ) == 200
    assert deadlines == [360]
    assert middleware.streams == {}
