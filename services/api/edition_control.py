"""Private shared controls for isolated FarmTact editions.

The public gateway owns these tables and exposes the router only on its private
Fly address.  Edition applications use :class:`RemoteControl` instead of
allocating their own inference budget or abuse counters.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
import hmac
import json
import os
import re
import threading
from typing import Callable
from urllib.parse import urlsplit
from uuid import uuid4

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import Boolean, Column, Integer, PrimaryKeyConstraint, String, Table, select, update
from sqlalchemy.exc import IntegrityError

from services.api.security import (
    AI_IP_BURST, AI_IP_HOUR, AI_TENANT, API_GLOBAL, API_IP, PREVIEW_IP,
    PREVIEW_TENANT, PROBE_IP, SESSION_GLOBAL, SESSION_IP, STREAM_IP, WRITE_IP,
    AbuseLimits, Limited,
)
from services.api.store import budget, metadata


MAX_DAILY_CALLS = 48
MAX_RESERVATION_CALLS = 16
MAX_RULES_PER_REQUEST = 12
ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")

CONTROL_RULES = {
    rule.name: rule for rule in (
        API_IP, API_GLOBAL, WRITE_IP, SESSION_IP, SESSION_GLOBAL, AI_IP_BURST,
        AI_IP_HOUR, AI_TENANT, PREVIEW_IP, PREVIEW_TENANT, PROBE_IP, STREAM_IP,
    )
}
EDITION_SCOPED_RULES = frozenset({AI_TENANT.name, PREVIEW_TENANT.name})

control_reservations = Table(
    "edition_control_reservations", metadata,
    Column("edition_id", String(64), nullable=False),
    Column("reservation_id", String(64), nullable=False),
    Column("day", String(10), nullable=False),
    Column("requested_calls", Integer, nullable=False),
    Column("accepted", Boolean, nullable=False),
    Column("released_calls", Integer, nullable=False, default=0),
    PrimaryKeyConstraint("edition_id", "reservation_id"),
)
control_releases = Table(
    "edition_control_releases", metadata,
    Column("edition_id", String(64), nullable=False),
    Column("release_id", String(64), nullable=False),
    Column("reservation_id", String(64), nullable=False),
    Column("released_calls", Integer, nullable=False),
    PrimaryKeyConstraint("edition_id", "release_id"),
)


def _identifier(value: str) -> str:
    if not ID_PATTERN.fullmatch(value):
        raise ValueError("Invalid control identifier")
    return value


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class ReserveRequest(StrictModel):
    edition_id: str
    reservation_id: str
    day: str
    count: int = Field(ge=1, le=MAX_RESERVATION_CALLS)

    @field_validator("edition_id", "reservation_id")
    @classmethod
    def identifiers(cls, value: str) -> str:
        return _identifier(value)

    @field_validator("day")
    @classmethod
    def valid_day(cls, value: str) -> str:
        if len(value) != 10 or date.fromisoformat(value).isoformat() != value:
            raise ValueError("Invalid reservation day")
        return value


class ReleaseRequest(StrictModel):
    edition_id: str
    reservation_id: str
    release_id: str
    day: str
    count: int = Field(ge=1, le=MAX_RESERVATION_CALLS)

    @field_validator("edition_id", "reservation_id", "release_id")
    @classmethod
    def identifiers(cls, value: str) -> str:
        return _identifier(value)

    @field_validator("day")
    @classmethod
    def valid_day(cls, value: str) -> str:
        if len(value) != 10 or date.fromisoformat(value).isoformat() != value:
            raise ValueError("Invalid reservation day")
        return value


class RuleCharge(StrictModel):
    rule: str
    principal: str = Field(min_length=1, max_length=256)

    @field_validator("rule")
    @classmethod
    def known_rule(cls, value: str) -> str:
        if value not in CONTROL_RULES:
            raise ValueError("Unknown control rule")
        return value


class ConsumeRequest(StrictModel):
    edition_id: str
    charges: list[RuleCharge] = Field(min_length=1, max_length=MAX_RULES_PER_REQUEST)

    @field_validator("edition_id")
    @classmethod
    def edition(cls, value: str) -> str:
        return _identifier(value)


def _authorize(secret: str, authorization: str | None) -> None:
    # Compare fixed byte strings in constant time.  Neither value enters errors/logs.
    supplied = authorization[7:] if authorization and authorization.startswith("Bearer ") else ""
    if not secret or not hmac.compare_digest(supplied.encode(), secret.encode()):
        raise HTTPException(401, "Control authentication required")


class ControlService:
    def __init__(self, store, *, abuse_limits: AbuseLimits | None = None):
        self.store = store
        self.abuse_limits = abuse_limits or AbuseLimits(store)
        self.lock = threading.RLock()
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert
        self.insert = pg_insert if store.engine.dialect.name == "postgresql" else sqlite_insert
        metadata.create_all(store.engine)

    def _known_edition(self, edition_id: str) -> None:
        # The gateway registry is atomically replaced during publication; read
        # its validated current contents so a new edition needs no process restart.
        from services.api.release_registry import registry
        if edition_id not in {item["id"] for item in registry()["editions"]}:
            raise ValueError("Unknown edition")

    def reserve(self, request: ReserveRequest) -> dict:
        self._known_edition(request.edition_id)
        with self.lock:
            return self._reserve(request)

    def _reserve(self, request: ReserveRequest) -> dict:
        values = dict(
            edition_id=request.edition_id, reservation_id=request.reservation_id,
            day=request.day, requested_calls=request.count,
            accepted=False, released_calls=0,
        )
        try:
            with self.store.engine.begin() as connection:
                connection.execute(control_reservations.insert().values(**values))
                connection.execute(self.insert(budget).values(
                    id=values["day"], reserved_calls=0,
                ).on_conflict_do_nothing(index_elements=[budget.c.id]))
                accepted = connection.execute(
                    update(budget).where(
                        budget.c.id == values["day"],
                        budget.c.reserved_calls + request.count <= MAX_DAILY_CALLS,
                    ).values(reserved_calls=budget.c.reserved_calls + request.count)
                ).rowcount == 1
                connection.execute(update(control_reservations).where(
                    control_reservations.c.edition_id == request.edition_id,
                    control_reservations.c.reservation_id == request.reservation_id,
                ).values(accepted=accepted))
            return {"accepted": accepted, "reservation_id": request.reservation_id}
        except IntegrityError:
            # Concurrent duplicate inserts wait for the winner before reaching here.
            with self.store.engine.connect() as connection:
                old = connection.execute(select(control_reservations).where(
                    control_reservations.c.edition_id == request.edition_id,
                    control_reservations.c.reservation_id == request.reservation_id,
                )).mappings().one_or_none()
                if old is not None:
                    if old["day"] != values["day"] or old["requested_calls"] != request.count:
                        raise ValueError("Reservation identifier reused with changed inputs")
                    return {"accepted": bool(old["accepted"]), "reservation_id": request.reservation_id}
            raise

    def release(self, request: ReleaseRequest) -> dict:
        self._known_edition(request.edition_id)
        with self.lock:
            try:
                return self._release(request)
            except IntegrityError:
                # A simultaneous retry may have committed the same release while
                # this transaction waited on the reservation row.
                with self.store.engine.connect() as connection:
                    previous = connection.execute(select(control_releases).where(
                        control_releases.c.edition_id == request.edition_id,
                        control_releases.c.release_id == request.release_id,
                    )).mappings().one_or_none()
                if previous is None:
                    raise
                if previous["reservation_id"] != request.reservation_id or previous["released_calls"] != request.count:
                    raise ValueError("Release identifier reused with changed inputs")
                return {"released": request.count, "release_id": request.release_id}

    def _release(self, request: ReleaseRequest) -> dict:
        with self.store.engine.begin() as connection:
            previous = connection.execute(select(control_releases).where(
                control_releases.c.edition_id == request.edition_id,
                control_releases.c.release_id == request.release_id,
            )).mappings().one_or_none()
            if previous is not None:
                if previous["reservation_id"] != request.reservation_id or previous["released_calls"] != request.count:
                    raise ValueError("Release identifier reused with changed inputs")
                return {"released": request.count, "release_id": request.release_id}
            reservation = connection.execute(select(control_reservations).where(
                control_reservations.c.edition_id == request.edition_id,
                control_reservations.c.reservation_id == request.reservation_id,
            ).with_for_update()).mappings().one_or_none()
            if reservation is None or not reservation["accepted"] or reservation["day"] != request.day:
                raise ValueError("Unknown reservation")
            if reservation["released_calls"] + request.count > reservation["requested_calls"]:
                raise ValueError("Release exceeds reservation")
            result = connection.execute(update(budget).where(
                budget.c.id == reservation["day"], budget.c.reserved_calls >= request.count,
            ).values(reserved_calls=budget.c.reserved_calls - request.count))
            if result.rowcount != 1:
                raise RuntimeError("Invalid budget reconciliation")
            connection.execute(update(control_reservations).where(
                control_reservations.c.edition_id == request.edition_id,
                control_reservations.c.reservation_id == request.reservation_id,
            ).values(released_calls=control_reservations.c.released_calls + request.count))
            connection.execute(control_releases.insert().values(
                edition_id=request.edition_id, release_id=request.release_id,
                reservation_id=request.reservation_id, released_calls=request.count,
            ))
        return {"released": request.count, "release_id": request.release_id}

    def consume(self, request: ConsumeRequest) -> dict:
        self._known_edition(request.edition_id)
        rules = []
        for charge in request.charges:
            principal = charge.principal
            if charge.rule in EDITION_SCOPED_RULES:
                principal = f"{request.edition_id}:{principal}"
            rules.append((CONTROL_RULES[charge.rule], principal))
        self.abuse_limits.consume(rules)
        return {"accepted": True}


def create_control_router(store, secret: str, *, abuse_limits: AbuseLimits | None = None) -> APIRouter:
    service = ControlService(store, abuse_limits=abuse_limits)
    router = APIRouter(prefix="/_control", include_in_schema=False)

    @router.post("/reserve")
    def reserve(body: ReserveRequest, authorization: str | None = Header(default=None)):
        _authorize(secret, authorization)
        try:
            return service.reserve(body)
        except ValueError as error:
            raise HTTPException(409, str(error)) from None

    @router.post("/release")
    def release(body: ReleaseRequest, authorization: str | None = Header(default=None)):
        _authorize(secret, authorization)
        try:
            return service.release(body)
        except ValueError as error:
            raise HTTPException(409, str(error)) from None

    @router.post("/consume")
    def consume(body: ConsumeRequest, authorization: str | None = Header(default=None)):
        _authorize(secret, authorization)
        try:
            return service.consume(body)
        except Limited as error:
            raise HTTPException(429, {"limit": error.rule, "retry_after": error.retry_after}, headers={"Retry-After": str(error.retry_after)}) from None
        except ValueError as error:
            raise HTTPException(409, str(error)) from None

    return router


def install_control_routes(app, store) -> None:
    """Install gateway routes from process configuration."""
    secret = os.environ.get("FARMTACT_CONTROL_SECRET", "")
    if not secret:
        raise RuntimeError("FARMTACT_CONTROL_SECRET is required for control routes")
    app.include_router(create_control_router(store, secret))


class ControlUnavailable(RuntimeError):
    pass


class RemoteControl:
    """Synchronous fail-closed adapter matching Store/AbuseLimits call sites."""
    def __init__(self, url: str, secret: str, edition_id: str, *, timeout: float = 3.0,
                 transport: Callable[[str, dict, dict, float], tuple[int, dict]] | None = None):
        parsed = urlsplit(url.rstrip("/"))
        if transport is None and (
            parsed.scheme not in {"http", "https"} or not parsed.hostname
            or not parsed.hostname.endswith(".flycast") or parsed.username or parsed.password
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment
        ):
            raise ValueError("Control URL must be a private Fly address")
        if not secret:
            raise ValueError("Control secret required")
        self.url, self.secret, self.edition_id = url.rstrip("/"), secret, _identifier(edition_id)
        self.timeout, self.transport = timeout, transport or self._http
        self._local = threading.local()

    @classmethod
    def from_environment(cls) -> "RemoteControl":
        return cls(
            os.environ.get("FARMTACT_CONTROL_URL", ""),
            os.environ.get("FARMTACT_CONTROL_SECRET", ""),
            os.environ.get("FARMTACT_EDITION", ""),
        )

    @staticmethod
    def _http(url: str, payload: dict, headers: dict, timeout: float) -> tuple[int, dict]:
        # Private control credentials must never be sent through process proxy settings.
        with httpx.Client(timeout=timeout, follow_redirects=False, trust_env=False) as client:
            response = client.post(url, json=payload, headers=headers)
        try:
            body = response.json()
        except (json.JSONDecodeError, ValueError):
            body = {}
        return response.status_code, body

    def _post(self, operation: str, payload: dict) -> tuple[int, dict]:
        try:
            return self.transport(
                f"{self.url}/_control/{operation}", payload,
                {"Authorization": f"Bearer {self.secret}"}, self.timeout,
            )
        except Exception as error:
            raise ControlUnavailable("Shared control service unavailable") from error

    def _reservations(self) -> dict[str, list[dict[str, str | None]]]:
        if not hasattr(self._local, "reservations"):
            self._local.reservations = defaultdict(list)
        return self._local.reservations

    def reserve_calls(self, count: int, limit: int = MAX_DAILY_CALLS, day: str | None = None) -> bool:
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0 or count > MAX_RESERVATION_CALLS:
            raise ValueError("Reservation must be between 1 and 16 calls")
        if limit != MAX_DAILY_CALLS:
            raise ValueError("Remote daily limit is fixed at 48")
        day = day or date.today().isoformat()
        reservation_id = uuid4().hex
        payload = {"edition_id": self.edition_id, "reservation_id": reservation_id, "day": day, "count": count}
        try:
            status, body = self._post("reserve", payload)
        except ControlUnavailable:
            return False
        if status != 200 or not isinstance(body.get("accepted"), bool):
            return False
        if body["accepted"]:
            self._reservations()[day].append({"reservation_id": reservation_id, "release_id": None})
        return body["accepted"]

    def release_unused_calls(self, count: int, day: str | None = None) -> None:
        if not isinstance(count, int) or isinstance(count, bool) or count < 0:
            raise ValueError("Nonnegative unused reservation required")
        day = day or date.today().isoformat()
        if count == 0:
            reservations = self._reservations()[day]
            if not reservations:
                raise ControlUnavailable("No matching shared reservation")
            reservations.pop()
            return
        reservations = self._reservations()[day]
        if not reservations:
            raise ControlUnavailable("No matching shared reservation")
        reservation = reservations[-1]
        reservation_id = str(reservation["reservation_id"])
        release_id = reservation["release_id"] or uuid4().hex
        reservation["release_id"] = release_id
        status, _body = self._post("release", {
            "edition_id": self.edition_id, "reservation_id": reservation_id,
            "release_id": release_id, "day": day, "count": count,
        })
        if status != 200:
            raise ControlUnavailable("Shared budget release rejected")
        reservations.pop()

    def consume(self, rules: list[tuple[object, str]]) -> None:
        charges = [{"rule": getattr(rule, "name", ""), "principal": principal} for rule, principal in rules]
        status, body = self._post("consume", {"edition_id": self.edition_id, "charges": charges})
        if status == 429:
            detail = body.get("detail", {})
            raise Limited(str(detail.get("limit", "shared_control")), int(detail.get("retry_after", 1)))
        if status != 200:
            raise ControlUnavailable("Shared abuse control unavailable")
