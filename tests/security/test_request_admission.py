"""Unauthenticated uploads cannot occupy request-body parsing slots."""
import pytest
from fastapi.testclient import TestClient

from services.api.app import create_app
from services.api.store import Store


@pytest.mark.parametrize("path", ["/api/v1/imports", "/api/v1/scenarios", "/api/v1/conversations"])
def test_unauthenticated_writes_reject_before_consuming_body(path):
    def body():
        raise AssertionError("Unauthenticated request body was consumed")
        yield b"unreachable"

    with TestClient(create_app(Store("sqlite://"), start_worker=False)) as client:
        response = client.post(path, content=body(), headers={"Content-Type": "application/json"})
        assert response.status_code == 401
