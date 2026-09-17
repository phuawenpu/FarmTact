"""Unauthenticated uploads cannot occupy request-body parsing slots."""
import pytest
from fastapi.testclient import TestClient

from services.api.app import create_app
from services.api.store import Store


@pytest.mark.parametrize("path", ["/api/v1/imports", "/api/v1/scenarios", "/api/v1/conversations", "/api/v1/farm-workflow/imports/upload", "/api/v1/farm-workflow/proposals", "/api/v1/farm-workflow/proposals/example/inverse"])
def test_unauthenticated_writes_reject_before_consuming_body(path):
    def body():
        raise AssertionError("Unauthenticated request body was consumed")
        yield b"unreachable"

    with TestClient(create_app(Store("sqlite://"), start_worker=False)) as client:
        response = client.post(path, content=body(), headers={"Content-Type": "application/json"})
        assert response.status_code == 401


def test_document_extraction_attempts_share_ai_burst_limits():
    with TestClient(create_app(Store('sqlite://'),start_worker=False)) as client:
        client.get('/api/v1/bootstrap')
        for _ in range(6):
            result=client.post('/api/v1/farm-workflow/imports/upload?filename=bad.pdf&source_kind=invalid',content=b'bad')
            assert result.status_code==422
        response=client.post('/api/v1/farm-workflow/imports/upload?filename=bad.pdf&source_kind=document_extraction',content=b'bad')
        assert response.status_code==429


def test_v13_mutations_have_session_rate_limit_before_route_work():
    store = Store("sqlite://")
    with TestClient(create_app(store, start_worker=False)) as client:
        client.get("/api/v1/bootstrap")
        path = "/api/v1/farm-workflow/proposals/missing/inverse"
        body = {"proposal_id": "missing", "proposal_revision": 2,
                "expected_session_revision": 4, "idempotency_key": "missing"}
        for _ in range(45):
            response = client.post(path, json=body)
            assert response.status_code != 429
        limited = client.post(path, json=body)
        assert limited.status_code == 429
        assert limited.json()["limit"] == "write_session"
        assert int(limited.headers["retry-after"]) >= 1
