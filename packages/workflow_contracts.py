"""Versioned V12 sandbox workflow boundaries; no contract authorizes real operations."""
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal
from pydantic import AwareDatetime, Field
from packages.contracts import Strict

WORKFLOW_VERSION = 'farmer-workflow-v1'
COUNCIL_ROLES = (
    'Demand Planner', 'Crop Planner', 'Weather & Risk Monitor',
    'Market & Price Analyst', 'Capacity & Cost Analyst', 'Farm Planner', 'Plan Reviewer',
)

class FarmImportCandidate(Strict):
    id: str
    tenant_id: str
    source_kind: Literal['accounting_export','manual','correction','document_extraction','photo_observation']
    source_name: str = Field(min_length=1,max_length=200)
    sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    created_at: AwareDatetime
    status: Literal['candidate','confirmed','rejected'] = 'candidate'
    rows: list[dict[str, Any]] = Field(default_factory=list,max_length=1000)
    provenance: dict[str, Any] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list,max_length=1000)

class ReviewImportRequest(Strict):
    expected_status: Literal['candidate'] = 'candidate'
    decision: Literal['confirm','reject']
    reviewer: str = Field(default='sandbox_user',min_length=1,max_length=100)
    note: str | None = Field(default=None,max_length=1000)

class WorkflowProposal(Strict):
    id: str
    session_id: str
    tenant_id: str
    base_revision: int = Field(ge=0)
    proposal_revision: int = Field(ge=1)
    status: Literal['draft','applied','superseded','approved'] = 'draft'
    changes: list[dict[str,Any]] = Field(default_factory=list,max_length=64)
    calculated_metrics: dict[str,Any] = Field(default_factory=dict)
    created_at: AwareDatetime

class ApplyProposalRequest(Strict):
    proposal_id: str = Field(min_length=1,max_length=100)
    expected_base_revision: int = Field(ge=0,strict=True)
    idempotency_key: str = Field(min_length=1,max_length=128)

class ApproveActionsRequest(Strict):
    proposal_id: str = Field(min_length=1,max_length=100)
    proposal_revision: int = Field(ge=1,strict=True)
    selected_strategy_id: str | None = Field(default=None,min_length=1,max_length=100)
    idempotency_key: str = Field(min_length=1,max_length=128)

TaskStatus = Literal['pending','in_progress','completed','failed','cancelled','recovery_required']
class FarmActionTask(Strict):
    id: str
    tenant_id: str
    session_id: str
    proposal_id: str
    proposal_revision: int = Field(ge=1)
    due_date: date
    crop_id: str | None = None
    batch_id: str | None = None
    location: str | None = None
    checklist: list[str] = Field(default_factory=list,max_length=30)
    photo_required: bool = False
    planned_quantity: Decimal | None = Field(default=None,ge=0,le=1000000,allow_inf_nan=False)
    actual_quantity: Decimal | None = Field(default=None,ge=0,le=1000000,allow_inf_nan=False)
    unit: Literal['kg','plants','trays','items'] | None = None
    status: TaskStatus = 'pending'
    created_at: AwareDatetime
    updated_at: AwareDatetime

class TaskResultRequest(Strict):
    expected_status: TaskStatus
    actual_quantity: Decimal | None = Field(default=None,ge=0,le=1000000,allow_inf_nan=False)
    rejected_quantity: Decimal | None = Field(default=None,ge=0,le=1000000,allow_inf_nan=False)
    unit: Literal['kg','plants','trays','items'] | None = None
    photo_reference: str | None = Field(default=None,max_length=100)
    checklist_completed: list[str] = Field(default_factory=list,max_length=30)
    result_status: Literal['completed','failed']
    note: str | None = Field(default=None,max_length=1000)

class CorrectionRequest(Strict):
    expected_event_revision: int = Field(ge=1,strict=True)
    field: Literal['actual_quantity','rejected_quantity','unit','note','result_status']
    corrected_value: Any
    reason: str = Field(min_length=1,max_length=1000)
    idempotency_key: str = Field(min_length=1,max_length=128)
