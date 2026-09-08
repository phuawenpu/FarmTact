from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from .http import HttpResponse
from .models import SnapshotRecord


SAFE_RESPONSE_HEADERS = {"content-type", "date", "etag", "last-modified", "x-request-id"}


class SnapshotStore:
    def __init__(self, data_dir: Path) -> None:
        self.data_dir = data_dir

    def save(
        self,
        *,
        source_id: str,
        request_url: str,
        query: dict[str, str],
        retrieved_at: str,
        response: HttpResponse,
        licence_state: str,
    ) -> SnapshotRecord:
        digest = hashlib.sha256(response.body).hexdigest()
        snapshot_id = f"{source_id.lower()}-{digest[:20]}"
        relative_path = Path("raw") / source_id.lower() / f"{digest}.json"
        output_path = self.data_dir / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        if output_path.exists():
            if hashlib.sha256(output_path.read_bytes()).hexdigest() != digest:
                raise RuntimeError(f"immutable snapshot collision at {output_path}")
        else:
            descriptor = os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(response.body)
        media_type = response.headers.get("content-type", "").split(";", 1)[0] or None
        safe_headers = {
            key: value for key, value in response.headers.items() if key.lower() in SAFE_RESPONSE_HEADERS
        }
        return SnapshotRecord(
            snapshot_id=snapshot_id,
            source_id=source_id,
            request_url=request_url,
            query=dict(sorted(query.items())),
            retrieved_at=retrieved_at,
            http_status=response.status,
            sha256=digest,
            byte_count=len(response.body),
            media_type=media_type,
            relative_path=str(relative_path),
            response_headers=safe_headers,
            licence_state=licence_state,
        )


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(encoded)
    temporary.replace(path)


def write_jsonl_atomic(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, sort_keys=True, ensure_ascii=False) + "\n")
    temporary.replace(path)
