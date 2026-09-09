from __future__ import annotations

import json
import math
import tempfile
import unittest
from unittest.mock import patch
from datetime import datetime, timezone
from pathlib import Path

from packages.ingestion import get_public_context, rebuild, refresh
from packages.ingestion.http import HttpResponse
from packages.ingestion.nea import normalize_station_observations
from packages.ingestion.singstat import normalize_trade_volume
from packages.ingestion.storage import SnapshotStore


FIXTURE_NOTICE = "Contract-shape fixture based on official live responses; values are test-only and are not agronomic evidence."


def station_payload(unit: str, value: float) -> dict:
    return {
        "fixture_notice": FIXTURE_NOTICE,
        "code": 0, "errorMsg": "",
        "data": {
            "readingType": "fixture", "readingUnit": unit,
            "stations": [{"id": "S001", "name": "Fixture Station", "location": {"latitude": 1.35, "longitude": 103.8}}],
            "readings": [{"timestamp": "2026-09-08T16:00:00+08:00", "data": [{"stationId": "S001", "value": value}]}],
        },
    }


def forecast_24h_payload() -> dict:
    return {"fixture_notice": FIXTURE_NOTICE, "code": 0, "errorMsg": "", "data": {"records": [{
        "timestamp": "2026-09-08T11:30:00+08:00", "updatedTimestamp": "2026-09-08T11:41:00+08:00",
        "general": {"validPeriod": {"start": "2026-09-08T12:00:00+08:00", "end": "2026-09-09T12:00:00+08:00"},
                    "temperature": {"low": 25, "high": 34}, "relativeHumidity": {"low": 60, "high": 95},
                    "forecast": {"text": "Fixture showers"}},
        "periods": [{"timePeriod": {"start": "2026-09-08T12:00:00+08:00", "end": "2026-09-08T18:00:00+08:00"},
                     "regions": {"north": {"text": "Fixture showers"}}}],
    }]}}


def forecast_4d_payload() -> dict:
    return {"fixture_notice": FIXTURE_NOTICE, "code": 0, "errorMsg": "", "data": {"records": [{
        "timestamp": "2026-09-08T09:25:00+08:00", "updatedTimestamp": "2026-09-08T09:31:00+08:00",
        "forecasts": [{"timestamp": "2026-09-09T00:00:00+08:00", "temperature": {"low": 25, "high": 34},
                       "relativeHumidity": {"low": 60, "high": 95}, "forecast": {"summary": "Fixture storm"}}],
    }]}}


def singstat_payload(rows: list[dict] | None = None) -> dict:
    return {"fixture_notice": FIXTURE_NOTICE, "StatusCode": 200, "Message": "", "Data": {
        "title": "Merchandise Trade Volume by Commodity and Market, Monthly", "frequency": "Monthly",
        "startPeriod": "2020 Jan", "endPeriod": "2026 Jul", "dataLastUpdated": "17/08/2026",
        "isMore": False, "nextCursor": None, "rows": rows or [],
    }}


class FakeTransport:
    def get(self, url: str, query: dict[str, str], timeout: float) -> HttpResponse:
        if url.endswith("/rainfall"):
            payload = station_payload("mm", 1.2)
        elif url.endswith("/air-temperature"):
            payload = station_payload("deg C", 30.5)
        elif url.endswith("/relative-humidity"):
            payload = station_payload("percentage", 78)
        elif url.endswith("/twenty-four-hr-forecast"):
            payload = forecast_24h_payload()
        elif url.endswith("/four-day-outlook"):
            payload = forecast_4d_payload()
        elif query.get("timeFilter") == "2026 Sep":
            payload = singstat_payload()
        else:
            payload = singstat_payload([{
                "hs8Products": "07051900 - OTHER LETTUCE FRESH OR CHILLED (TNE)", "market": "WORLD",
                "tradeType": "IMPORTS", "period": "2026 Jul", "quantity": "856",
            }])
        body = json.dumps(payload, allow_nan=False).encode()
        return HttpResponse(200, body, {"content-type": "application/json", "authorization": "must-not-persist"}, url)


class RainfallFailureTransport(FakeTransport):
    def get(self, url: str, query: dict[str, str], timeout: float) -> HttpResponse:
        if url.endswith("/rainfall"):
            raise TimeoutError("fixture timeout")
        return super().get(url, query, timeout)


class RegistryTests(unittest.TestCase):
    def test_catalogue_and_registry_are_complete_and_cross_referenced(self) -> None:
        catalogue = json.loads(Path("research/crop_catalogue.json").read_text())
        evidence = json.loads(Path("research/evidence_register.json").read_text())
        datasets = json.loads(Path("research/dataset_registry.json").read_text())
        sources = json.loads(Path("research/source_registry.json").read_text())
        self.assertEqual(12, len(catalogue["profiles"]))
        self.assertTrue(all(profile["popularity_rank"] is None for profile in catalogue["profiles"]))
        self.assertEqual(24, len(evidence["documents"]))
        self.assertEqual(23, len(datasets["datasets"]))
        self.assertEqual(63, len(sources["sources"]))
        evidence_ids = {row["evidence_id"] for row in evidence["documents"]}
        self.assertTrue(all(set(profile["evidence_ids"]) <= evidence_ids for profile in catalogue["profiles"]))
        kale = next(profile for profile in catalogue["profiles"] if profile["crop_id"] == "kale")
        self.assertIsNone(kale["taxon_concept"])

    def test_new_tropical_herbs_have_distinct_taxa_and_contextual_evidence(self) -> None:
        catalogue = json.loads(Path("research/crop_catalogue.json").read_text())
        evidence = json.loads(Path("research/evidence_register.json").read_text())
        profiles = {row["crop_id"]: row for row in catalogue["profiles"]}
        existing_ids = {
            "caixin", "pak_choi", "kailan", "bayam", "kangkong", "lettuce",
            "kale", "mustard_greens", "malabar_spinach", "sweet_potato_leaves",
        }
        self.assertTrue(existing_ids <= profiles.keys())
        self.assertEqual("Allium tuberosum Rottler ex Spreng.", profiles["garlic_chives"]["taxon_concept"])
        self.assertEqual("Eryngium foetidum L.", profiles["sawtooth_coriander"]["taxon_concept"])
        self.assertEqual({"Amaryllidaceae", "Apiaceae"}, {
            profiles["garlic_chives"]["family"], profiles["sawtooth_coriander"]["family"],
        })
        documents = {row["evidence_id"]: row for row in evidence["documents"]}
        for crop_id in ("garlic_chives", "sawtooth_coriander"):
            rows = [documents[evidence_id] for evidence_id in profiles[crop_id]["evidence_ids"]]
            self.assertGreaterEqual(len(rows), 2)
            self.assertTrue(all(crop_id in row["crop_ids"] for row in rows))
            self.assertTrue(all(row["doi"] and row["finding"] and row["limit"] for row in rows))
            self.assertTrue(all("local_validation" in row["parameter_use"] or "no_autonomous" in row["parameter_use"] for row in rows))

    def test_specific_sawtooth_product_code_does_not_make_broad_hs_series_crop_specific(self) -> None:
        mappings = json.loads(Path("research/crop_hs_mappings.json").read_text())["mappings"]
        specific = next(row for row in mappings if row.get("product_code") == "HVL0PSC")
        broad = next(row for row in mappings if row["code"] == "07099990" and row.get("crop_id") is None)
        self.assertEqual("sawtooth_coriander", specific["crop_id"])
        self.assertEqual("approved_product_description_match", specific["status"])
        self.assertEqual("unresolved", broad["status"])
        self.assertIn("sawtooth_coriander", broad["candidate_crop_ids"])

    def test_ambiguous_spinach_and_kale_stay_unresolved(self) -> None:
        catalogue = json.loads(Path("research/crop_catalogue.json").read_text())
        queue = {item["input"]: item for item in catalogue["alias_review_queue"]}
        self.assertEqual("unresolved", queue["spinach"]["status"])
        self.assertEqual("unresolved", queue["kale"]["status"])
        mappings = json.loads(Path("research/crop_hs_mappings.json").read_text())["mappings"]
        broad = [row for row in mappings if row["code"] in {"07097000", "07049030", "07099990"} and row.get("crop_id") is None]
        self.assertTrue(all(row["status"] == "unresolved" and row.get("crop_id") is None for row in broad))


class NormalizationTests(unittest.TestCase):
    def test_station_observation_preserves_time_unit_and_provenance(self) -> None:
        rows = normalize_station_observations(station_payload("percentage", 78), source_id="D03",
            snapshot_id="snap-1", retrieved_at="2026-09-08T08:01:00+00:00", variable="relative_humidity", expected_unit="%")
        self.assertEqual("%", rows[0]["unit"])
        self.assertEqual("snap-1", rows[0]["snapshot_id"])
        self.assertFalse(rows[0]["eligible_for_point_in_time_features"])
        self.assertIn("raw_locator", rows[0])

    def test_nonfinite_station_value_is_not_normalized(self) -> None:
        with self.assertRaisesRegex(ValueError, "no valid"):
            normalize_station_observations(station_payload("mm", math.nan), source_id="D01", snapshot_id="snap-1",
                retrieved_at="2026-09-08T08:01:00+00:00", variable="rainfall", expected_unit="mm")

    def test_trade_volume_keeps_provider_unit_and_unknown_availability(self) -> None:
        payload = singstat_payload([
            {"hs8Products": "07051900 - OTHER LETTUCE FRESH OR CHILLED (TNE)", "market": "WORLD", "tradeType": "IMPORTS", "period": "2026 Jul", "quantity": "856"},
            {"hs8Products": "07097000 - SPINACH NEW ZEALAND SPINACH & ORACHE SPINACH FRESH OR CHILLED (TNE)", "market": "WORLD", "tradeType": "IMPORTS", "period": "2026 Jul", "quantity": "NaN"},
        ])
        rows, coverage = normalize_trade_volume(payload, snapshot_id="snap-2", retrieved_at="2026-09-08T08:01:00+00:00")
        self.assertEqual(1, len(rows))
        self.assertEqual("tonne", rows[0]["unit"])
        self.assertIsNone(rows[0]["available_at"])
        self.assertFalse(rows[0]["eligible_for_point_in_time_features"])
        self.assertEqual(1, coverage["invalid_selected_quantities"])

    def test_snapshot_is_content_addressed_and_headers_are_redacted(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = SnapshotStore(Path(directory))
            response = HttpResponse(200, b'{"ok":true}', {"content-type": "application/json", "authorization": "secret"}, "https://example.test")
            first = store.save(source_id="D01", request_url="https://example.test", query={}, retrieved_at="2026-09-08T00:00:00+00:00", response=response, licence_state="verified")
            second = store.save(source_id="D01", request_url="https://example.test", query={}, retrieved_at="2026-09-08T00:01:00+00:00", response=response, licence_state="verified")
            self.assertEqual(first.sha256, second.sha256)
            self.assertNotIn("authorization", first.response_headers)
            self.assertEqual(first.sha256, __import__("hashlib").sha256((Path(directory) / first.relative_path).read_bytes()).hexdigest())


class PublicApiTests(unittest.TestCase):
    def test_refresh_get_and_offline_rebuild(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            current = datetime(2026, 9, 8, 8, 5, tzinfo=timezone.utc)
            context = refresh(data_dir, now=current, transport=FakeTransport())
            self.assertEqual("passed", context.quality["status"])
            self.assertEqual({"D01", "D02", "D03", "D04", "D05", "D06"}, {row["source_id"] for row in context.sources})
            required = {"source_id", "provider", "kind", "status", "source_time", "retrieved_at", "freshness", "unit", "coverage", "snapshot_id", "licence_state"}
            self.assertTrue(all(required <= set(row) for row in context.sources))
            loaded = get_public_context(data_dir)
            self.assertEqual(len(context.weather_observations), len(loaded.weather_observations))
            with patch("packages.ingestion.context._utc_now", return_value=datetime(2026, 9, 9, 8, 5, tzinfo=timezone.utc)):
                aged = get_public_context(data_dir)
            self.assertEqual("stale", next(row for row in aged.sources if row["source_id"] == "D01")["freshness"])
            (data_dir / "normalized" / "weather_observations.jsonl").unlink()
            rebuilt = rebuild(data_dir)
            self.assertEqual("offline_snapshot_rebuild", rebuilt.execution_mode)
            self.assertTrue((data_dir / "normalized" / "weather_observations.jsonl").exists())
            self.assertEqual("passed", rebuilt.quality["status"])

    def test_failure_uses_prior_snapshot_as_explicit_stale_cache(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            data_dir = Path(directory)
            current = datetime(2026, 9, 8, 8, 5, tzinfo=timezone.utc)
            refresh(data_dir, now=current, transport=FakeTransport())
            failed = refresh(data_dir, now=current, transport=RainfallFailureTransport())
            rainfall = next(row for row in failed.sources if row["source_id"] == "D01")
            failure = next(row for row in failed.failures if row.source_id == "D01")
            self.assertEqual("cached_stale", rainfall["status"])
            self.assertEqual("stale", rainfall["freshness"])
            self.assertTrue(failure.cached_context_available)
            self.assertEqual("passed", failed.quality["status"])
            rainfall_snapshot_ids = {row["snapshot_id"] for row in failed.weather_observations if row["source_id"] == "D01"}
            self.assertTrue(rainfall_snapshot_ids <= {snapshot.snapshot_id for snapshot in failed.snapshots})
            lineage = json.loads((data_dir / "manifests" / "lineage.json").read_text())
            lineage_sources = {edge["from"] for edge in lineage["edges"] if edge["to"] == "weather_observations"}
            self.assertTrue(rainfall_snapshot_ids <= lineage_sources)


if __name__ == "__main__":
    unittest.main()
