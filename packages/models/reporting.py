"""Versioned schemas for generated numerical evidence."""
from __future__ import annotations

from datetime import datetime
from typing import Any,Literal

from pydantic import BaseModel,ConfigDict,Field,model_validator


NUMERICAL_REPORT_SCHEMA_VERSION='farmtact-numerical-evaluation-2.0.0'


class NumericalEvaluationReport(BaseModel):
    model_config=ConfigDict(extra='forbid',strict=True,allow_inf_nan=False,validate_default=True)
    report_schema_version: Literal['farmtact-numerical-evaluation-2.0.0']=NUMERICAL_REPORT_SCHEMA_VERSION
    report_id: str=Field(pattern=r'^[0-9a-f]{64}$')
    generated_at: datetime
    status: Literal['PASS','FAIL']
    mode: Literal['synthetic_demo']='synthetic_demo'
    validation_status: Literal['demo_only']='demo_only'
    evaluation_scope: dict[str,Any]
    dataset_name: str
    fixture_hash: str=Field(pattern=r'^[0-9a-f]{64}$')
    generator_version: str
    generator_settings: dict[str,Any]
    cutoff: datetime
    source_revision: dict[str,Any]
    forecast_version: str
    forecast_contract_version: str
    forecast_settings: dict[str,Any]
    forecast_evaluation: list[dict[str,Any]]
    planner_version: str
    planner_configuration: dict[str,Any]
    strategies: list[dict[str,Any]]
    baseline: list[dict[str,Any]]
    solver_reproducibility: dict[str,Any]
    public_features_used: list[str]=Field(max_length=0)
    promotion_status: Literal['not_eligible_synthetic_only']='not_eligible_synthetic_only'
    limitations: list[str]=Field(min_length=1)

    @model_validator(mode='after')
    def validate_scope_metadata(self):
        required={'cohort','origin_count','horizons','target','synthetic_only'}
        if not required<=self.evaluation_scope.keys() or self.evaluation_scope.get('synthetic_only') is not True:
            raise ValueError('evaluation_scope lacks required synthetic cohort metadata')
        return self
