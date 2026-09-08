from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from scripts.generate_web_contracts import TARGET, render_typescript
from services.api.app import create_app
from services.api.store import Store
from services.api.view_contracts import Bootstrap, Run


ROOT = Path(__file__).resolve().parents[2]


def test_bootstrap_response_matches_shared_view_contract() -> None:
    with TestClient(create_app(store=Store("sqlite://"), start_worker=False)) as client:
        response = client.get("/api/v1/bootstrap")
        response.raise_for_status()
        payload = response.json()

    validated = Bootstrap.model_validate(payload)
    assert validated.model_dump(mode="json", exclude_unset=True) == payload
    assert all(source.snapshot_id for source in validated.sources if source.status == "validated")


def test_recorded_replay_matches_shared_view_contract_and_keeps_provenance() -> None:
    payload = json.loads((ROOT / "data/fixtures/deepseek_demo_replay.json").read_text())
    validated = Run.model_validate(payload)
    round_trip = validated.model_dump(mode="json", exclude_unset=True)

    assert round_trip == payload
    assert validated.execution_mode == "replay"
    assert validated.shared_demo is True
    assert validated.source_snapshot
    assert all(source.snapshot_id for source in validated.source_snapshot)
    assert validated.inference_origin == "recorded_deepseek"


def test_generated_web_contract_is_current_and_deterministic() -> None:
    first = render_typescript()
    second = render_typescript()
    assert first == second
    assert TARGET.read_text() == first
    assert "$ref" not in first
    assert "anyOf" not in first
    assert "export type BedStage = 'empty' | 'nursery' | 'growing' | 'ready'" in first
    assert "violations: Array<string | ConstraintViolation>" in first
