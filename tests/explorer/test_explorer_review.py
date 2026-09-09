"""Adversarial review cases retained until explorer integrity checks reject them."""

from copy import deepcopy

from fastapi.testclient import TestClient
from sqlalchemy import select, update

from services.api.app import create_app
from services.api.data_explorer import snapshots
from services.api.store import Store


def test_saved_snapshot_rejects_payload_that_no_longer_matches_content_hash():
    store = Store("sqlite://")
    with TestClient(create_app(store, start_worker=False)) as client:
        client.get("/api/v1/bootstrap")
        tenant = store.authenticate(client.cookies.get("farmtact_session"))
        saved = client.post(
            "/api/v1/data-explorer/snapshots",
            json={},
            headers={"Idempotency-Key": "integrity-review"},
        ).json()

        with store.connection() as connection:
            row = connection.execute(
                select(snapshots).where(snapshots.c.tenant_id == tenant)
            ).mappings().one()
        altered = deepcopy(row["payload"])
        altered["input_snapshot"]["history"][0]["ordered_kg"] = "999999"
        with store.connection(write=True) as connection:
            connection.execute(
                update(snapshots)
                .where(snapshots.c.tenant_id == tenant, snapshots.c.id == row["id"])
                .values(payload=altered)
            )

        response = client.get(f"/api/v1/data-explorer/snapshots/{saved['id']}")
        assert response.status_code == 409
        replay = client.post(
            "/api/v1/data-explorer/snapshots",
            json={},
            headers={"Idempotency-Key": "integrity-review"},
        )
        assert replay.status_code == 409
        scenario = client.post(
            "/api/v1/scenarios",
            json={"explorer_snapshot_id": saved["id"]},
            headers={"Idempotency-Key": "corrupt-source"},
        )
        assert scenario.status_code == 409


def test_saved_snapshot_rejects_forecast_that_no_longer_matches_forecast_hash():
    store = Store("sqlite://")
    with TestClient(create_app(store, start_worker=False)) as client:
        client.get("/api/v1/bootstrap")
        tenant = store.authenticate(client.cookies.get("farmtact_session"))
        saved = client.post(
            "/api/v1/data-explorer/snapshots",
            json={"forecast_settings": {"alpha": 0.8}},
            headers={"Idempotency-Key": "forecast-integrity-review"},
        ).json()

        with store.connection() as connection:
            row = connection.execute(
                select(snapshots).where(snapshots.c.tenant_id == tenant)
            ).mappings().one()
        altered = deepcopy(row["payload"])
        altered["forecast"]["demand"][0]["expected_kg"] += 1
        with store.connection(write=True) as connection:
            connection.execute(
                update(snapshots)
                .where(snapshots.c.tenant_id == tenant, snapshots.c.id == row["id"])
                .values(payload=altered)
            )

        assert client.get(f"/api/v1/data-explorer/snapshots/{saved['id']}").status_code == 409


def test_saved_snapshot_rejects_removed_integrity_metadata():
    store = Store("sqlite://")
    with TestClient(create_app(store, start_worker=False)) as client:
        client.get("/api/v1/bootstrap")
        tenant = store.authenticate(client.cookies.get("farmtact_session"))
        saved = client.post(
            "/api/v1/data-explorer/snapshots",
            json={},
            headers={"Idempotency-Key": "metadata-integrity-review"},
        ).json()

        with store.connection() as connection:
            row = connection.execute(
                select(snapshots).where(snapshots.c.tenant_id == tenant)
            ).mappings().one()
        altered = deepcopy(row["payload"])
        altered["forecast"]["demand"][0]["expected_kg"] += 1
        for key in (
            "forecast_hash",
            "reference_snapshot",
            "reference_forecast_settings",
            "reference_forecast_version",
            "reference_content_hash",
            "reference_generator_settings",
            "reference_generator_version",
        ):
            altered.pop(key, None)
        with store.connection(write=True) as connection:
            connection.execute(
                update(snapshots)
                .where(snapshots.c.tenant_id == tenant, snapshots.c.id == row["id"])
                .values(payload=altered)
            )

        assert client.get(f"/api/v1/data-explorer/snapshots/{saved['id']}").status_code == 409
