"""Shared, serializable contracts for FarmTact's public API views.

These models describe the response shapes consumed by the web application.  View
models allow additional fields deliberately: public run/source records carry
provenance and audit details that must survive validation even when the browser
does not yet render them.
"""
from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


OMIT_NULL = {"x-typescript-omit-null": True}


class ViewModel(BaseModel):
    model_config = ConfigDict(extra="allow", allow_inf_nan=False)


class BedStage(StrEnum):
    empty = "empty"
    nursery = "nursery"
    growing = "growing"
    ready = "ready"


class StrategyName(StrEnum):
    lean = "Lean"
    balanced = "Balanced"
    resilient = "Resilient"


class SourceOrigin(StrEnum):
    public = "public"
    synthetic = "synthetic"


class Bed(ViewModel):
    id: str
    name: str
    area_m2: float
    system: str
    crop_id: str | None = Field(default=None, json_schema_extra=OMIT_NULL)
    stage: BedStage
    sow_date: str | None = Field(default=None, json_schema_extra=OMIT_NULL)
    harvest_date: str | None = Field(default=None, json_schema_extra=OMIT_NULL)
    progress: float


class FarmResources(ViewModel):
    area_m2: float
    nursery_sites: int
    labour_hours_per_week: float
    cash_sgd: float


class FarmOrder(ViewModel):
    id: str
    crop_id: str
    due_date: str
    quantity_kg: float
    price_sgd_per_kg: float


class Farm(ViewModel):
    id: str
    name: str
    location: str
    timezone: str
    data_mode: str
    cutoff: str
    horizon_days: int
    beds: list[Bed]
    resources: FarmResources
    orders: list[FarmOrder]
    version: int | str


class CropRecipe(ViewModel):
    cycle_days: int
    nursery_days: int
    yield_kg_per_m2: float
    validation_status: str


class EvidenceRecord(ViewModel):
    evidence_id: str
    title: str | None = None
    year: int | None = None
    finding: str | None = None
    limit: str | None = None
    scope: str | None = None
    licence_state: str | None = None
    access_review_status: str | None = None
    source_url: str | None = None


class Crop(ViewModel):
    id: str
    label: str
    aliases: list[str]
    color: str | None = Field(default=None, json_schema_extra=OMIT_NULL)
    harvested_part: str
    evidence_ids: list[str]
    warnings: list[str]
    recipe: CropRecipe | None
    evidence: list[EvidenceRecord] | None = None
    popularity_rank: int | None = None
    taxonomy_status: str | None = None


class Source(ViewModel):
    id: str
    name: str
    status: str
    observed_at: str | None
    retrieved_at: str
    available_at: str | None = None
    freshness: str
    origin: SourceOrigin
    execution_mode: str
    summary: str
    unit: str | list[str] | None = None
    value: str | float | None = None
    url: str | None = None
    snapshot_id: str | None = None
    coverage: dict[str, Any] | None = None
    licence_state: str | None = None
    availability_status: str | None = None


class DeepSeekCapability(ViewModel):
    status: str
    models: list[str]
    reason: str | None = None
    overall_trial_status: str | None = None


class VisionCapability(ViewModel):
    status: str


class Capabilities(ViewModel):
    deepseek: DeepSeekCapability
    vision: VisionCapability
    data_mode: str
    execution_mode: str


class StrategyMetrics(ViewModel):
    fill_rate: float
    margin_sgd: float
    waste_kg: float
    harvest_kg: float
    shortfall_kg: float
    cost_sgd: float
    labour_hours: float
    area_m2: float
    closing_stock_kg: float | None = None
    opening_stock_kg: float | None = None
    revenue_sgd: float | None = None


class Allocation(ViewModel):
    bed_id: str
    crop_id: str
    sow_date: str
    transplant_date: str
    harvest_date: str
    area_m2: float
    expected_kg: float
    id: str | None = Field(default=None, json_schema_extra=OMIT_NULL)
    recipe_id: str | None = Field(default=None, json_schema_extra=OMIT_NULL)
    executed: bool | None = Field(default=None, json_schema_extra=OMIT_NULL)


class WeeklyResult(ViewModel):
    week: int
    date: str
    demand_kg: float
    harvest_kg: float
    delivered_kg: float
    shortfall_kg: float


class ConstraintViolation(ViewModel):
    constraint_code: str | None = None
    entity_id: str | None = None
    period: str | None = None
    required: float | None = None
    available: float | None = None
    unit: str | None = None
    severity: str | None = None
    repair_options: list[str] | None = None


class Strategy(ViewModel):
    id: str
    name: StrategyName
    status: str
    description: str
    metrics: StrategyMetrics
    allocations: list[Allocation]
    weekly: list[WeeklyResult]
    violations: list[str | ConstraintViolation]
    assumptions: list[str]
    policy_parameters: dict[str, Any] | None = None
    cost_breakdown: dict[str, Any] | None = None
    ledger: list[dict[str, Any]] | None = None
    scenario_results: list[dict[str, Any]] | None = None
    scenario_set_id: str | None = None
    scenario_seed: int | None = None
    solver: dict[str, Any] | None = None
    input_hash: str | None = None
    model_version: str | None = None
    calculation_version: str | None = None
    risk: dict[str, Any] | None = None


class Claim(ViewModel):
    role: str
    claim_type: str
    statement: str
    evidence_ids: list[str]
    tool_result_refs: list[str]
    status: str
    recommendation: str | None = None
    run_id: str | None = None
    snapshot_id: str | None = None
    rejection_reasons: list[str] | None = None


class RunEvent(ViewModel):
    sequence: int
    event_type: str
    occurred_at: str
    body: Any
    run_id: str | None = None
    schema_version: str | None = None


class Run(ViewModel):
    id: str
    status: str
    input_version: int | str
    created_at: str
    execution_mode: str
    data_mode: str
    council_status: str
    strategies: list[Strategy]
    claims: list[Claim]
    events: list[RunEvent]
    warnings: list[str]
    accepted_strategy_id: str | None = Field(default=None, json_schema_extra=OMIT_NULL)
    parent_run_id: str | None = None
    disruption: str | dict[str, Any] | None = None
    shared_demo: bool | None = Field(default=None, json_schema_extra=OMIT_NULL)
    superseded_by: str | None = Field(default=None, json_schema_extra=OMIT_NULL)
    input_hash: str | None = None
    source_snapshot: list[Source] | None = None
    evidence_version: str | None = None
    development_phase: str | None = None
    decision_policy: str | None = None
    council_requested: bool | None = None
    with_vision: bool | None = None
    completed_at: str | None = None
    original_execution_mode: str | None = None
    inference_origin: str | None = None
    replay_of: str | None = None
    acceptance_stale: bool | None = None
    forecast: dict[str, Any] | None = None
    scenario_set: list[dict[str, Any]] | None = None
    scenario_set_id: str | None = None
    visual_observation: dict[str, Any] | None = None
    inference_budget: dict[str, Any] | None = None
    inference_audit: list[dict[str, Any]] | None = None
    acceptance: dict[str, Any] | None = None
    simulated_outcome: dict[str, Any] | None = None


class Bootstrap(ViewModel):
    farm: Farm
    crops: list[Crop]
    sources: list[Source]
    capabilities: Capabilities
    latest_run: Run | None


WEB_MODELS = (
    Bed,
    FarmResources,
    FarmOrder,
    Farm,
    CropRecipe,
    EvidenceRecord,
    Crop,
    Source,
    DeepSeekCapability,
    VisionCapability,
    Capabilities,
    StrategyMetrics,
    Allocation,
    WeeklyResult,
    ConstraintViolation,
    Strategy,
    Claim,
    RunEvent,
    Run,
    Bootstrap,
)
