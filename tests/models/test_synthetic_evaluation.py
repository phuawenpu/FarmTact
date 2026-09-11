from datetime import datetime,time,timedelta,timezone
import json

import pytest
from pydantic import ValidationError

from packages.contracts import content_hash
from packages.fixtures import (
    CropCycleOutcome,
    benchmark_manifest,
    synthetic_crop_cycle_benchmark,
    synthetic_demand_benchmark,
    synthetic_farm,
)
from packages.models import DemandForecastRecord,HarvestForecastRecord,forecast
from packages.models.evaluation import build_synthetic_evaluation
from packages.models.reporting import NumericalEvaluationReport


def test_reference_fixture_hash_is_preserved():
    assert content_hash(synthetic_farm())=='00286779541fa9ed1245ea2aff65d08c1a05241cdc6a399706aa6601fdbc3f76'


def test_demand_generators_are_versioned_deterministic_and_disjoint():
    train=synthetic_demand_benchmark('training');evaluation=synthetic_demand_benchmark('evaluation')
    assert benchmark_manifest(train)==benchmark_manifest(synthetic_demand_benchmark('training'))
    assert train.generator_version!=evaluation.generator_version
    assert {row.farm_id for row in train.records}.isdisjoint(row.farm_id for row in evaluation.records)
    assert {row.buyer_id for row in train.records}.isdisjoint(row.buyer_id for row in evaluation.records)
    assert max(row.due_week for row in train.records)<min(row.due_week for row in evaluation.records)
    assert {row.regime for row in train.records}=={'stable','growth','compression'}
    assert {'demand_surge','demand_drop'}<{row.shock for row in train.records}
    assert any(row.cancelled_kg>0 and row.cancellation_available_at for row in train.records)
    assert train.public_features_used==[]


def test_crop_cycle_outcomes_are_independent_typed_observations():
    train=synthetic_crop_cycle_benchmark('training');evaluation=synthetic_crop_cycle_benchmark('evaluation')
    assert train.generator_version!=evaluation.generator_version
    assert {row.batch_id for row in train.outcomes}.isdisjoint(row.batch_id for row in evaluation.outcomes)
    assert {'operational_delay','quality_loss'}<{row.shock for row in train.outcomes}
    assert all(row.outcome_available_at.date()>row.actual_harvest_date for row in train.outcomes)
    invalid=train.outcomes[0].model_dump()
    invalid['outcome_available_at']=datetime.combine(invalid['actual_harvest_date']-timedelta(days=1),time(),timezone.utc)
    with pytest.raises(ValidationError,match='outcome cannot be available before harvest'):
        CropCycleOutcome.model_validate(invalid)


def test_forecast_has_validated_price_and_harvest_semantics():
    result=forecast(synthetic_farm())
    assert result['forecast_contract_version']=='2.0.0'
    assert all(DemandForecastRecord.model_validate_json(json.dumps(row)) for row in result['demand'])
    assert all(HarvestForecastRecord.model_validate_json(json.dumps(row)) for row in result['harvest'])
    farm=synthetic_farm().model_copy(update={'orders':[]})
    empty=forecast(farm)
    assert {row['price_status'] for row in empty['demand']}=={'unavailable_no_booked_price'}
    assert {row['price_sgd_per_kg'] for row in empty['demand']}=={0}


def test_rolling_origin_report_is_multihorizon_leakage_checked_and_never_promoted():
    report=build_synthetic_evaluation(
        synthetic_demand_benchmark('training'),synthetic_demand_benchmark('evaluation'),
        synthetic_crop_cycle_benchmark('training'),synthetic_crop_cycle_benchmark('evaluation'))
    assert all(report.split_checks.values())
    assert report.demand_evaluation['horizons_weeks']==[1,2,4]
    assert set(report.demand_evaluation['cohorts'])=={'farm','buyer'}
    assert all(check['leakage_violations']==0 for check in report.demand_evaluation['leakage'].values())
    assert report.demand_evaluation['public_features_used']==[]
    assert report.promotion.status=='blocked'
    assert report.promotion.eligible_for_production is False
    assert {gate.gate_id for gate in report.promotion.gates if gate.status=='blocked'} >= {
        'real_farm_temporal_validation','external_farm_validation','operational_monitoring'}


def test_checked_in_numerical_report_uses_versioned_schema_and_preserves_archive():
    current=NumericalEvaluationReport.model_validate_json(open('reports/numerical_evaluation.json').read())
    archived=json.loads(open('reports/v8/archive/numerical_evaluation.pre-v8.json').read())
    assert current.evaluation_scope['synthetic_only'] is True
    assert current.public_features_used==[]
    assert current.promotion_status=='not_eligible_synthetic_only'
    assert archived['fixture_hash']==current.fixture_hash
    assert 'report_schema_version' not in archived
