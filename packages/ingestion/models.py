from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SnapshotRecord:
    snapshot_id: str
    source_id: str
    request_url: str
    query: dict[str, str]
    retrieved_at: str
    http_status: int
    sha256: str
    byte_count: int
    media_type: str | None
    relative_path: str
    response_headers: dict[str, str]
    licence_state: str


@dataclass(frozen=True)
class SourceFailure:
    source_id: str
    state: str
    occurred_at: str
    reason: str
    retryable: bool
    cached_context_available: bool = False


@dataclass
class PublicContext:
    schema_version: str
    built_at: str
    execution_mode: str
    sources: list[dict[str, Any]] = field(default_factory=list)
    snapshots: list[SnapshotRecord] = field(default_factory=list)
    weather_observations: list[dict[str, Any]] = field(default_factory=list)
    weather_forecasts: list[dict[str, Any]] = field(default_factory=list)
    trade_observations: list[dict[str, Any]] = field(default_factory=list)
    failures: list[SourceFailure] = field(default_factory=list)
    freshness: list[dict[str, Any]] = field(default_factory=list)
    quality: dict[str, Any] = field(default_factory=dict)

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)
