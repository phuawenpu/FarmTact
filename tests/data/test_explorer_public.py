from __future__ import annotations

import unittest
from unittest.mock import patch

from packages.ingestion.models import PublicContext
from services.api.explorer_public import public_explorer


NOW = "2026-09-08T08:05:00+00:00"


def context(*, status: str = "validated", freshness: str = "fresh") -> PublicContext:
    return PublicContext(
        schema_version="1.0.0", built_at=NOW, execution_mode="cached",
        sources=[{
            "source_id": "D01", "status": status, "source_time": "2026-09-08T16:00:00+08:00",
            "retrieved_at": NOW, "freshness": freshness, "freshness_age_minutes": 5,
            "coverage": {"row_count": 2, "station_count": 1}, "snapshot_id": "snap-1",
        }, {
            "source_id": "D06", "status": "validated", "source_time": None,
            "retrieved_at": NOW, "freshness": "unknown", "freshness_age_minutes": None,
            "coverage": {"row_count": 1}, "snapshot_id": "snap-6",
        }],
        weather_observations=[{
            "observation_id": "obs-a", "source_id": "D01", "snapshot_id": "snap-1",
            "station_id": "S1", "station_name": "Station", "latitude": 1.3, "longitude": 103.8,
            "variable": "rainfall", "value": 1.5, "unit": "mm", "interval_minutes": 5,
            "observed_at": "2026-09-08T16:00:00+08:00", "available_at": "2026-09-08T16:00:00+08:00",
            "availability_status": "uncertain", "eligible_for_point_in_time_features": False,
            "retrieved_at": NOW, "quality_flags": ["automated_station"],
        }, {
            "observation_id": "obs-b", "source_id": "D01", "snapshot_id": "snap-1",
            "station_id": "S1", "station_name": "Station", "latitude": 1.3, "longitude": 103.8,
            "variable": "air_temperature", "value": 30, "unit": "degC", "interval_minutes": 5,
            "observed_at": "2026-09-08T16:00:00+08:00", "available_at": "2026-09-08T16:00:00+08:00",
            "availability_status": "uncertain", "eligible_for_point_in_time_features": False,
            "retrieved_at": NOW, "quality_flags": [],
        }],
        trade_observations=[{
            "trade_observation_id": "trade-a", "source_id": "D06", "snapshot_id": "snap-6",
            "period_start": "2026-07-01", "period": "2026 Jul", "measure": "trade_volume",
            "value": "67", "unit": "tonne", "raw_unit": "TNE", "observed_at": "2026-07-01T00:00:00+08:00",
            "retrieved_at": NOW, "available_at": None, "availability_status": "unknown_release",
            "eligible_for_point_in_time_features": False, "reporter": "Singapore", "partner": "WORLD",
            "trade_flow": "IMPORTS", "commodity_code": "07049020", "commodity_description": "MUSTARD",
            "flags": [],
        }],
    )


class PublicExplorerTests(unittest.TestCase):
    @patch("services.api.explorer_public.get_public_context")
    def test_curates_cached_rows_without_collapsing_measurements(self, get_context) -> None:
        get_context.return_value = context()
        result = public_explorer()
        rows = result["datasets"]["weather_observations"]
        self.assertEqual({"obs-a", "obs-b"}, {row["id"] for row in rows})
        self.assertEqual({("rainfall", "mm"), ("air_temperature", "degC")},
                         {(row["metric"], row["unit"]) for row in rows})
        self.assertEqual([], result["datasets"]["weather_forecasts"])
        self.assertEqual(NOW, rows[0]["retrieved_at"])
        get_context.assert_called_once()

    @patch("services.api.explorer_public.get_public_context")
    def test_stale_cache_and_registry_only_sources_are_explicit(self, get_context) -> None:
        get_context.return_value = context(status="cached_stale", freshness="stale")
        result = public_explorer()
        rainfall = next(source for source in result["sources"] if source["id"] == "D01")
        registry_only = next(source for source in result["sources"] if source["id"] == "D07")
        self.assertEqual("cached_stale", rainfall["status"])
        self.assertEqual("stale", rainfall["freshness"])
        self.assertIn("cached_stale", rainfall["quality_flags"])
        self.assertEqual("metadata_only", registry_only["status"])
        self.assertEqual(0, registry_only["record_count"])
        self.assertIsNone(registry_only["retrieved_at"])

    @patch("services.api.explorer_public.get_public_context")
    def test_missing_cache_still_returns_complete_registry(self, get_context) -> None:
        get_context.return_value = PublicContext(schema_version="1", built_at=NOW, execution_mode="unavailable")
        result = public_explorer()
        self.assertEqual(23, len(result["sources"]))
        self.assertTrue(all(source["status"] == "metadata_only" for source in result["sources"]))
        self.assertEqual({name: [] for name in ("weather_observations", "weather_forecasts", "trade_observations")},
                         result["datasets"])

    @patch("services.api.explorer_public.get_public_context")
    def test_licence_policy_protects_source_and_row_exports(self, get_context) -> None:
        get_context.return_value = context()
        result = public_explorer()
        rainfall = next(source for source in result["sources"] if source["id"] == "D01")
        trade = next(source for source in result["sources"] if source["id"] == "D06")
        self.assertTrue(rainfall["export_allowed"])
        self.assertTrue(all(row["export_allowed"] for row in result["datasets"]["weather_observations"]))
        self.assertFalse(trade["export_allowed"])
        self.assertTrue(trade["reuse_restrictions"])
        self.assertFalse(result["datasets"]["trade_observations"][0]["export_allowed"])
        self.assertEqual("not_verified_for_redistribution",
                         result["datasets"]["trade_observations"][0]["licence_state"])
        self.assertTrue(result["datasets"]["trade_observations"][0]["reuse_restrictions"])


if __name__ == "__main__":
    unittest.main()
