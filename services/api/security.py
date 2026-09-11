"""Durable abuse limits. Forwarded headers are never identities on local servers."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import hashlib
import hmac
import ipaddress
import logging
import math
import os
import re
import secrets
import threading
import time
from urllib.parse import urlsplit

from sqlalchemy import Column, Float, Integer, String, Table, case, delete, or_, select
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse

from services.api.store import metadata

rate_counters = Table(
    "abuse_rate_counters", metadata,
    Column("key", String, primary_key=True),
    Column("count", Integer, nullable=False),
    Column("expires", Float, nullable=False, index=True),
)
security_settings = Table(
    "abuse_security_settings", metadata,
    Column("key", String, primary_key=True),
    Column("value", String, nullable=False),
)


@dataclass(frozen=True)
class Rule:
    name: str
    limit: int
    seconds: int


API_IP = Rule("api_ip", 600, 60)
API_GLOBAL = Rule("api_global", 3000, 60)
WRITE_IP = Rule("write_ip", 60, 60)
SESSION_IP = Rule("new_session_ip", 10, 3600)
SESSION_GLOBAL = Rule("new_session_global", 100, 3600)
AI_IP_BURST = Rule("ai_ip_minute", 6, 60)
AI_IP_HOUR = Rule("ai_ip_hour", 20, 3600)
AI_TENANT = Rule("ai_session_hour", 12, 3600)
PREVIEW_IP = Rule("explorer_preview_ip", 60, 60)
PREVIEW_TENANT = Rule("explorer_preview_session", 30, 60)
PROBE_IP = Rule("probe_ip", 30, 60)
STREAM_IP = Rule("stream_open_ip", 12, 60)
AI_PATH = re.compile(r"^/api/v1/(?:planning-sessions/[^/]+/review|conversations/[^/]+/(?:messages|invite|council)|planning-runs(?:/[^/]+/replan)?)$")


class Limited(Exception):
    def __init__(self, rule: str, retry_after: int):
        self.rule, self.retry_after = rule, retry_after


def is_event_stream(request: Request) -> bool:
    path = request.url.path.rstrip("/")
    return path.endswith("/events") and (
        "/planning-runs/" in path
        or request.query_params.get("stream", "").lower() in {"1", "true", "on", "yes"}
        or "text/event-stream" in request.headers.get("accept", "").lower()
    )


def client_network(request: Request, trust_fly: bool) -> str:
    """Fly owns the public HTTP ingress; never parse caller-supplied XFF.

    Trust is deployment-only, with an unrewritten private transport peer.
    Direct public peers cannot opt themselves into proxy trust using headers.
    IPv6 addresses share their /64 allowance to prevent privacy-address rotation.
    """
    peer = request.client.host if request.client else "unknown"
    try:
        peer_ip = ipaddress.ip_address(peer)
    except ValueError:
        peer_ip = None
    trusted_peer = peer_ip is not None and (
        peer_ip.is_loopback or peer_ip in ipaddress.ip_network("172.16.0.0/12")
        or peer_ip in ipaddress.ip_network("fdaa::/16")
    )
    address = peer
    if trust_fly and trusted_peer:
        supplied = request.headers.getlist("fly-client-ip")
        if len(supplied) != 1:
            raise ValueError("Missing trusted client address")
        address = supplied[0]
    try:
        value = ipaddress.ip_address(address)
    except ValueError:
        if trust_fly:
            raise ValueError("Invalid trusted client address") from None
        return "unresolved-peer"  # Tests/Unix transports share a conservative bucket.
    if getattr(value, "ipv4_mapped", None):
        value = value.ipv4_mapped
    return str(ipaddress.ip_network(f"{value}/64", strict=False)) if value.version == 6 else str(value)


class AbuseLimits:
    def __init__(self, store, *, clock=time.time, trust_fly=None, public_origin=None):
        self.store, self.clock = store, clock
        self.trust_fly = os.environ.get("FARMTACT_TRUST_FLY_PROXY") == "true" if trust_fly is None else trust_fly
        self.public_origin = (os.environ.get("FARMTACT_PUBLIC_ORIGIN", "") if public_origin is None else public_origin).rstrip("/")
        self.lock = threading.RLock()
        self.last_cleanup = 0.0
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        self.insert = pg_insert if store.engine.dialect.name == "postgresql" else sqlite_insert
        with store.engine.begin() as connection:
            connection.execute(self.insert(security_settings).values(key="ip_hmac", value=secrets.token_hex(32)).on_conflict_do_nothing(index_elements=[security_settings.c.key]))
            self.salt = connection.execute(select(security_settings.c.value).where(security_settings.c.key == "ip_hmac")).scalar_one().encode()

    def opaque(self, value: str) -> str:
        return hmac.new(self.salt, value.encode(), hashlib.sha256).hexdigest()

    def consume(self, rules: list[tuple[Rule, str]]) -> None:
        """Atomic, shared across processes/redeployments; failed groups roll back."""
        if getattr(self.store, 'control', None) is not None:
            return self.store.control.consume(rules)
        timestamp = self.clock()
        with self.lock, self.store.engine.begin() as connection:
            for rule, principal in sorted(rules, key=lambda item: item[0].name):
                key = self.opaque(f"{rule.name}:{principal}")
                expired = rate_counters.c.expires <= timestamp
                statement = self.insert(rate_counters).values(key=key, count=1, expires=timestamp + rule.seconds).on_conflict_do_update(
                    index_elements=[rate_counters.c.key],
                    set_={"count": case((expired, 1), else_=rate_counters.c.count + 1), "expires": case((expired, timestamp + rule.seconds), else_=rate_counters.c.expires)},
                    where=or_(expired, rate_counters.c.count < rule.limit),
                ).returning(rate_counters.c.count)
                if connection.execute(statement).first() is None:
                    expires = connection.execute(select(rate_counters.c.expires).where(rate_counters.c.key == key)).scalar_one()
                    raise Limited(rule.name, max(1, math.ceil(expires - timestamp)))
            if timestamp - self.last_cleanup > 300:
                connection.execute(delete(rate_counters).where(rate_counters.c.expires < timestamp - 86400))
                self.last_cleanup = timestamp

    def check(self, request: Request) -> str:
        network = client_network(request, self.trust_fly)
        path = request.url.path.rstrip("/") or "/"
        api = path.startswith("/api/")
        self.consume([(API_GLOBAL, "all"), (API_IP if api else PROBE_IP, network)])
        if self.public_origin and request.headers.get("host", "").lower() != urlsplit(self.public_origin).netloc.lower():
            raise PermissionError("Unrecognized application host")
        tenant = self.store.authenticate(request.cookies.get("farmtact_session")) if api else None
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            self.consume([(WRITE_IP, network)])
            origin = request.headers.get("origin")
            expected = self.public_origin or f"{request.url.scheme}://{request.headers.get('host', '')}"
            if request.headers.get("sec-fetch-site") == "cross-site" or (origin and origin != expected):
                raise PermissionError("Cross-origin write rejected")
        if path == "/api/v1/bootstrap" and request.method in {"GET", "HEAD"} and not tenant:
            self.consume([(SESSION_IP, network), (SESSION_GLOBAL, "all")])
        if path == "/api/v1/data-explorer/preview" and request.method == "POST":
            self.consume([(PREVIEW_IP, network)])
            if not tenant:
                raise PermissionError("Session required")
            self.consume([(PREVIEW_TENANT, tenant)])
        if AI_PATH.fullmatch(path) and request.method == "POST":
            # Charge attempts even for missing IDs, invalid payloads and rotated cookies.
            self.consume([(AI_IP_BURST, network), (AI_IP_HOUR, network)])
            if not tenant:
                raise PermissionError("Session required")
            self.consume([(AI_TENANT, tenant)])
        if api and request.method not in {"GET", "HEAD", "OPTIONS"} and not tenant:
            raise PermissionError("Session required")
        if is_event_stream(request):
            self.consume([(STREAM_IP, network)])
        return self.opaque(network)


class AbuseMiddleware:
    """Request admission precedes parsing/queueing; SSE slots span the response."""
    def __init__(self, app):
        self.app = app
        self.streams: dict[str, int] = {}
        self.last_notice: dict[str, float] = {}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        request = Request(scope)
        path = request.url.path
        # Fixed read-only health and static artwork need neither DB admission nor sessions.
        if request.method in {"GET", "HEAD"} and (path == "/api/v1/health" or path.startswith(("/assets/", "/art/", "/review-evidence/", "/audio/"))):
            return await self.app(scope, receive, send)
        limits = scope["app"].state.abuse_limits
        headers = {"Cache-Control": "no-store", "X-Content-Type-Options": "nosniff"}
        try:
            identity = await run_in_threadpool(limits.check, request)
        except Limited as error:
            headers["Retry-After"] = str(error.retry_after)
            timestamp = time.monotonic()
            if timestamp - self.last_notice.get(error.rule, -60) >= 60:
                logging.getLogger("farmtact.security").warning("Abuse limit triggered: %s", error.rule)
                self.last_notice[error.rule] = timestamp
            return await JSONResponse({"detail": f"Too many requests. Retry in {error.retry_after} seconds.", "limit": error.rule}, 429, headers=headers)(scope, receive, send)
        except PermissionError as error:
            status = 401 if str(error) == "Session required" else 403
            return await JSONResponse({"detail": str(error)}, status, headers=headers)(scope, receive, send)
        except ValueError:
            return await JSONResponse({"detail": "Invalid client address"}, 400, headers=headers)(scope, receive, send)
        except Exception:
            logging.getLogger("farmtact.security").warning("Request admission unavailable; request rejected")
            return await JSONResponse({"detail": "Request admission temporarily unavailable"}, 503, headers=headers)(scope, receive, send)
        stream = is_event_stream(request)
        if stream:
            if self.streams.get(identity, 0) >= 4 or sum(self.streams.values()) >= 32:
                return await JSONResponse({"detail": "Too many active event streams"}, 429, headers={**headers, "Retry-After": "5"})(scope, receive, send)
            self.streams[identity] = self.streams.get(identity, 0) + 1
        try:
            if stream:
                async with asyncio.timeout(360):
                    await self.app(scope, receive, send)
            else:
                await self.app(scope, receive, send)
        finally:
            if stream:
                self.streams[identity] -= 1
                if not self.streams[identity]:
                    del self.streams[identity]
