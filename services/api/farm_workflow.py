"""V12 farmer workflow persistence and deterministic action accounting.

This module coordinates the existing guided planning session.  It does not run a
planner: ``apply_proposal`` delegates recalculation to an injected queue hook.
All reads and writes require a tenant and every mutation uses optimistic revision
checks plus tenant-scoped idempotency receipts.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timezone
from decimal import Decimal
from functools import wraps
import hashlib
import json
import secrets
from typing import Any, Callable, Protocol

from fastapi import HTTPException, Request
from fastapi.responses import Response
from pydantic import Field
from sqlalchemy import LargeBinary, Column, ForeignKey, ForeignKeyConstraint, Integer, JSON, String, Table, UniqueConstraint, func, select, update

from packages.contracts import Farm, Strict, content_hash
from packages.ingestion.financial import FinancialDataConnector, FinancialImport
from packages.workflow_contracts import ApplyProposalRequest, ApproveActionsRequest, CorrectionRequest, ReviewImportRequest, TaskResultRequest
from services.api.store import metadata, now


VERSION = "farmer-workflow-v1"
IMPORTS = Table("farm_workflow_imports", metadata,
    Column("id", String, primary_key=True), Column("tenant_id", String, ForeignKey("tenants.id"), nullable=False),
    Column("status", String, nullable=False), Column("payload", JSON, nullable=False), UniqueConstraint("id", "tenant_id"))
PROPOSALS = Table("farm_workflow_proposals", metadata,
    Column("id", String, primary_key=True), Column("tenant_id", String, ForeignKey("tenants.id"), nullable=False),
    Column("session_id", String, nullable=False), Column("status", String, nullable=False), Column("payload", JSON, nullable=False),
    UniqueConstraint("id", "tenant_id"), ForeignKeyConstraint(["session_id", "tenant_id"], ["guided_planning_sessions.id", "guided_planning_sessions.tenant_id"]))
TASKS = Table("farm_workflow_tasks", metadata,
    Column("id", String, primary_key=True), Column("tenant_id", String, ForeignKey("tenants.id"), nullable=False),
    Column("session_id", String, nullable=False), Column("proposal_id", String, nullable=False), Column("status", String, nullable=False),
    Column("payload", JSON, nullable=False), UniqueConstraint("id", "tenant_id"),
    ForeignKeyConstraint(["proposal_id", "tenant_id"], ["farm_workflow_proposals.id", "farm_workflow_proposals.tenant_id"]))
EVENTS = Table("farm_workflow_events", metadata,
    Column("id", Integer, primary_key=True), Column("tenant_id", String, ForeignKey("tenants.id"), nullable=False),
    Column("subject_id", String, nullable=False), Column("sequence", Integer, nullable=False), Column("payload", JSON, nullable=False),
    UniqueConstraint("tenant_id", "subject_id", "sequence"))
RECEIPTS = Table("farm_workflow_receipts", metadata,
    Column("tenant_id", String, ForeignKey("tenants.id"), primary_key=True), Column("key", String, primary_key=True),
    Column("request_hash", String, nullable=False), Column("payload", JSON, nullable=False))
SOURCE_BLOBS = Table("farm_workflow_source_blobs", metadata,
    Column("candidate_id", String, primary_key=True), Column("tenant_id", String, ForeignKey("tenants.id"), nullable=False),
    Column("filename", String, nullable=False), Column("media_type", String, nullable=False),
    Column("sha256", String, nullable=False), Column("payload", LargeBinary, nullable=False),
    UniqueConstraint("candidate_id", "tenant_id"))

_SOURCE_MEDIA = {"text/csv", "application/pdf", "image/png", "image/jpeg",
                 "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


def save_source_blob(store, tenant: str, candidate_id: str, *, raw: bytes, filename: str, media_type: str) -> None:
    if not raw or len(raw) > 8 * 1024 * 1024: raise ValueError("Source file is empty or exceeds 8 MiB")
    normalized = media_type.split(";", 1)[0].lower()
    if normalized not in _SOURCE_MEDIA: raise ValueError("Unsupported source media type")
    safe_name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1].replace('"', "").replace("\r", "").replace("\n", "")
    if not safe_name or safe_name in {".", ".."} or len(safe_name) > 200: raise ValueError("Invalid source filename")
    digest = hashlib.sha256(raw).hexdigest()
    with store.connection(write=True) as c:
        old = c.execute(select(SOURCE_BLOBS).where(SOURCE_BLOBS.c.candidate_id == candidate_id,
            SOURCE_BLOBS.c.tenant_id == tenant)).mappings().first()
        if old:
            if old["sha256"] != digest: raise ValueError("Source candidate blob collision")
            return
        c.execute(SOURCE_BLOBS.insert().values(candidate_id=candidate_id, tenant_id=tenant, filename=safe_name,
            media_type=normalized, sha256=digest, payload=raw))


class PlanningAdapter(Protocol):
    def get_session(self, store: Any, tenant_id: str, session_id: str) -> dict[str, Any] | None: ...
    def get_result(self, store: Any, tenant_id: str, result_id: str | None) -> dict[str, Any] | None: ...
    def queue_recalculation(self, store: Any, tenant_id: str, session: dict[str, Any], changes: list[dict[str, Any]]) -> dict[str, Any]: ...
    def approve_result(self, store: Any, tenant_id: str, session: dict[str, Any], proposal: dict[str, Any],
                       result: dict[str, Any], strategy_id: str) -> dict[str, Any]: ...


def _atomic_mutation(function):
    @wraps(function)
    def wrapped(store, tenant, *args, **kwargs):
        with store.transaction(tenant):
            return function(store, tenant, *args, **kwargs)
    return wrapped


save_source_blob = _atomic_mutation(save_source_blob)


def _json(value: Any) -> Any:
    if isinstance(value, (date, datetime, Decimal)):
        return str(value)
    if hasattr(value, "__dict__"):
        return {key: _json(item) for key, item in value.__dict__.items()}
    if isinstance(value, tuple): return [_json(item) for item in value]
    if isinstance(value, list): return [_json(item) for item in value]
    if isinstance(value, dict): return {key: _json(item) for key, item in value.items()}
    return value


def _request_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(_json(value), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def reconcile_financial_rows(rows: list[dict[str, Any]], *, reviewed_rows: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    revenue = Decimal(0); expense = Decimal(0); quantities: dict[str, Decimal] = {}; seen = set(); duplicates = []
    corrections = 0; resolved_corrections = []
    reviewed_references = {str(row.get("reference") or "") for row in (reviewed_rows or []) if row.get("reference")}
    incoming_correction_references: set[str] = set()
    targets: dict[str, list[dict[str, Any]]] = {}
    for source in [*(reviewed_rows or []), *rows]:
        reference = str(source.get("reference") or "")
        if reference and source.get("kind") != "correction":
            targets.setdefault(reference, []).append(source)
    for row in rows:
        reference = str(row.get("reference") or "")
        kind = row.get("kind")
        if kind != "correction" and reference and reference in seen:
            duplicates.append(reference); continue
        if reference: seen.add(reference)
        amount = Decimal(str(row.get("amount_sgd", row.get("amount", 0))))
        if not amount.is_finite(): raise ValueError("Financial amounts must be finite")
        if kind == "sale": revenue += amount
        elif kind == "expense": expense += amount
        elif kind == "correction":
            corrections += 1
            if not reference:
                raise ValueError("Correction reference is required")
            if reference in reviewed_references or reference in incoming_correction_references:
                raise ValueError(f"Correction reference is already used: {reference}")
            incoming_correction_references.add(reference)
            target_reference = str(row.get("corrects_reference") or "")
            if not target_reference:
                raise ValueError("Correction target reference is required")
            matches = targets.get(target_reference, [])
            if not matches:
                raise ValueError(f"Unknown correction target reference: {target_reference}")
            if len(matches) != 1:
                raise ValueError(f"Ambiguous correction target reference: {target_reference}")
            target_kind = matches[0].get("kind")
            if target_kind == "sale": revenue += amount
            elif target_kind == "expense": expense += amount
            else: raise ValueError(f"Correction target is not a sale or expense: {target_reference}")
            provenance = matches[0].get("provenance") or {}
            resolved_corrections.append({
                "reference": reference, "corrects_reference": target_reference,
                "target_kind": target_kind, "signed_delta_sgd": str(amount),
                "target_source_sha256": provenance.get("source_sha256"),
                "target_row_number": matches[0].get("row_number", provenance.get("row_number")),
            })
        quantity = row.get("quantity")
        unit = row.get("unit")
        if quantity is not None and unit:
            quantity_value = Decimal(str(quantity))
            if not quantity_value.is_finite(): raise ValueError("Financial quantities must be finite")
            quantities[unit] = quantities.get(unit, Decimal(0)) + quantity_value
    return {"source_row_count": len(rows), "counted_row_count": len(rows) - len(duplicates),
            "duplicate_references": sorted(set(duplicates)), "correction_row_count": corrections,
            "correction_semantics": "target_category_signed_delta", "revenue_sgd": str(revenue), "expense_sgd": str(expense),
            "net_sgd": str(revenue - expense), "quantity_by_unit": {key: str(value) for key, value in sorted(quantities.items())},
            "resolved_corrections": resolved_corrections}


def _receipt(store, tenant: str, key: str, request: Any, create: Callable[[], dict[str, Any]]) -> tuple[dict[str, Any], bool]:
    if not key or len(key) > 200:
        raise ValueError("A bounded idempotency key is required")
    digest = _request_hash(request)
    with store.transaction(tenant) as c:
        old = c.execute(select(RECEIPTS).where(RECEIPTS.c.tenant_id == tenant, RECEIPTS.c.key == key).with_for_update()).mappings().first()
        if old:
            if old["request_hash"] != digest:
                raise ValueError("Idempotency key reused with changed inputs")
            return deepcopy(old["payload"]), False
        response = create()
        c.execute(RECEIPTS.insert().values(tenant_id=tenant, key=key, request_hash=digest, payload=response))
    return response, True


def append_event(store, tenant: str, subject_id: str, event_type: str, body: dict[str, Any]) -> dict[str, Any]:
    with store.transaction(tenant) as c:
        seq = (c.execute(select(EVENTS.c.sequence).where(EVENTS.c.tenant_id == tenant, EVENTS.c.subject_id == subject_id)
                         .order_by(EVENTS.c.sequence.desc()).limit(1)).scalar_one_or_none() or 0) + 1
        event = {"sequence": seq, "subject_id": subject_id, "event_type": event_type,
                 "occurred_at": now(), "version": VERSION, "body": _json(body)}
        c.execute(EVENTS.insert().values(tenant_id=tenant, subject_id=subject_id, sequence=seq, payload=event))
    return event


@_atomic_mutation
def save_import(store, tenant: str, candidate: FinancialImport | dict[str, Any], *, source_kind: str = "accounting_export") -> dict[str, Any]:
    payload = _json(candidate)
    payload.setdefault("candidate_id", payload.get("id"))
    payload.setdefault("source_sha256", payload.get("sha256"))
    if payload.get("tenant_id") != tenant:
        raise ValueError("Import tenant mismatch")
    payload["source_kind"] = source_kind
    payload.setdefault("authority", "review_candidate")
    if source_kind == "photo_observation":
        payload["authority"] = "observation_only"
        payload["yield_authority"] = False
    with store.transaction(tenant) as c:
        existing = c.execute(select(IMPORTS.c.payload).where(IMPORTS.c.id == payload["candidate_id"], IMPORTS.c.tenant_id == tenant)).scalar_one_or_none()
        if existing:
            if (existing.get("source_sha256") or existing.get("sha256")) != (payload.get("source_sha256") or payload.get("sha256")):
                raise ValueError("Import candidate identity collision")
            return existing
        count = c.execute(select(func.count()).select_from(IMPORTS).where(IMPORTS.c.tenant_id == tenant)).scalar_one()
        if count >= 100:
            raise ValueError("Farm Data Inbox limit reached")
        if source_kind != "photo_observation":
            reviewed = c.execute(select(IMPORTS.c.payload).where(
                IMPORTS.c.tenant_id == tenant, IMPORTS.c.status == "confirmed"
            )).scalars().all()
            reviewed_rows = [item for record in reviewed for item in record.get("rows", [])]
            payload["reconciliation"] = reconcile_financial_rows(
                payload.get("rows", []), reviewed_rows=reviewed_rows
            )
        c.execute(IMPORTS.insert().values(id=payload["candidate_id"], tenant_id=tenant,
                                          status=payload["status"], payload=payload))
    append_event(store, tenant, payload["candidate_id"], "import_candidate_created", {"source_kind": source_kind, "sha256": payload.get("source_sha256")})
    return payload


@_atomic_mutation
def review_import(store, tenant: str, candidate_id: str, *, decision: str, reviewer: str,
                  expected_status: str = "candidate", note: str | None = None) -> dict[str, Any]:
    if decision not in {"confirm", "reject"} or not reviewer.strip():
        raise ValueError("Explicit confirm/reject decision and reviewer are required")
    with store.connection(write=True) as c:
        row = c.execute(select(IMPORTS).where(IMPORTS.c.id == candidate_id, IMPORTS.c.tenant_id == tenant).with_for_update()).mappings().first()
        if not row: raise ValueError("Import candidate not found")
        if row["status"] != expected_status: raise ValueError("Import review state changed")
        payload = deepcopy(row["payload"])
        reviewed = c.execute(select(IMPORTS.c.payload).where(
            IMPORTS.c.tenant_id == tenant, IMPORTS.c.status == "confirmed", IMPORTS.c.id != candidate_id
        )).scalars().all()
        if decision == "confirm" and payload.get("source_kind") != "photo_observation":
            payload["reconciliation"] = reconcile_financial_rows(
                payload.get("rows", []),
                reviewed_rows=[item for record in reviewed for item in record.get("rows", [])],
            )
        payload.update(status="confirmed" if decision == "confirm" else "rejected", reviewed_at=now(), reviewed_by=reviewer, review_note=note)
        # Observation-only sources remain non-authoritative after review.
        unsupported = {warning.split(":", 1)[1] for warning in payload.get("warnings", [])
                       if isinstance(warning, str) and warning.startswith("unsupported_crop:")}
        confirmed = payload["status"] == "confirmed"
        payload["planning_eligible"] = confirmed and payload.get("authority") != "observation_only" and not unsupported
        payload["planning_eligibility"] = (
            "rejected" if not confirmed else "observation_only" if payload.get("authority") == "observation_only"
            else "accounting_only_unsupported_crop" if unsupported else "eligible"
        )
        payload["row_eligibility"] = [{
            "row_number": item.get("row_number"),
            "accounting_eligible": confirmed and payload.get("authority") != "observation_only",
            "planning_eligible": payload["planning_eligible"] or (
                confirmed and payload.get("authority") != "observation_only" and item.get("crop_id") not in unsupported
            ),
        } for item in payload.get("rows", [])]
        c.execute(update(IMPORTS).where(IMPORTS.c.id == candidate_id, IMPORTS.c.tenant_id == tenant)
                  .values(status=payload["status"], payload=payload))
    append_event(store, tenant, candidate_id, "import_reviewed", {"decision": decision, "reviewer": reviewer})
    return payload


def calculated_metrics(result: dict[str, Any], strategy_id: str | None = None) -> dict[str, float]:
    strategies = result.get("strategies", [])
    selected = next((row for row in strategies if row.get("id") == strategy_id), strategies[0] if strategies else {})
    metrics = selected.get("metrics", {})
    requested = Decimal(str(metrics.get("booked_requested_kg", 0)))
    delivered = Decimal(str(metrics.get("booked_delivered_kg", 0)))
    expiry = Decimal(str(metrics.get("waste_kg", metrics.get("expired_kg", 0))))
    rescued = Decimal(str(metrics.get("waste_rescue_kg", 0)))
    # Closing stock comes from the planner's FIFO accounting and includes opening
    # inventory/consumption.  Do not reconstruct it as harvest minus demand.
    surplus = None if metrics.get("closing_stock_kg") is None else float(Decimal(str(metrics["closing_stock_kg"])))
    rejected = None if metrics.get("rejected_kg") is None else float(Decimal(str(metrics["rejected_kg"])))
    return {
        "coverage_kg": float(min(delivered, requested)), "surplus_kg": surplus,
        "expiry_kg": float(expiry), "rejection_kg": rejected,
        "margin_sgd": float(Decimal(str(metrics.get("margin_sgd", 0)))), "waste_rescue_kg": float(rescued),
    }


@_atomic_mutation
def create_proposal(store, tenant: str, *, adapter: PlanningAdapter, session_id: str, base_revision: int,
                    changes: list[dict[str, Any]], idempotency_key: str, selected_strategy_id: str | None = None,
                    source_candidate_ids: list[str] | None = None,
                    source_conversation_id: str | None = None, source_message_id: str | None = None) -> dict[str, Any]:
    request = {"session_id": session_id, "base_revision": base_revision, "changes": changes,
               "selected_strategy_id": selected_strategy_id, "source_candidate_ids": source_candidate_ids or [],
               "source_conversation_id": source_conversation_id, "source_message_id": source_message_id}
    def create():
        session = adapter.get_session(store, tenant, session_id)
        if not session: raise ValueError("Planning session not found")
        if session["revision"] != base_revision: raise ValueError("Planning revision changed")
        result = adapter.get_result(store, tenant, session.get("result_id"))
        if not result: raise ValueError("Calculate the planning session before proposing changes")
        discussion = None
        if source_conversation_id or source_message_id:
            if not source_conversation_id or not source_message_id:
                raise ValueError("Discussion provenance requires both conversation and message")
            from services.api.conversation_store import ConversationStore
            persistence = ConversationStore(store)
            conversation = persistence.get_conversation(tenant, source_conversation_id)
            message = persistence.get_message(tenant, source_conversation_id, source_message_id)
            if not conversation or not message: raise ValueError("Discussion source not found")
            frozen = conversation.get("snapshot_ref", {})
            if frozen.get("kind") != "planning" or frozen.get("id") != session_id + ":" + session["result_id"]:
                raise ValueError("Discussion planning result changed; ask against the current result")
            if message.get("speaker") != "advisor" or message.get("validation_status") != "references_verified":
                raise ValueError("Only a validated advisory message can support a proposal")
            discussion = {"conversation_id": source_conversation_id, "message_id": source_message_id,
                          "snapshot_ref": deepcopy(frozen), "message_hash": content_hash(message),
                          "proposed_actions": deepcopy(message.get("proposed_actions", [])),
                          "translation": "farmer_reviewed_assumptions", "reviewed_changes_hash": content_hash(changes),
                          "authority": "reviewed_advisory_context"}
        sources = []
        with store.connection() as c:
            for candidate_id in source_candidate_ids or []:
                candidate = c.execute(select(IMPORTS.c.payload).where(IMPORTS.c.id == candidate_id, IMPORTS.c.tenant_id == tenant)).scalar_one_or_none()
                if not candidate: raise ValueError("Import candidate not found")
                if candidate.get("status") != "confirmed" or not candidate.get("planning_eligible"):
                    raise ValueError("Only confirmed planning-eligible records can support a proposal")
                sources.append({"candidate_id": candidate_id, "source_sha256": candidate.get("source_sha256") or candidate.get("sha256"),
                                "source_kind": candidate.get("source_kind"), "provenance": candidate.get("provenance", {})})
        proposal = {"id": secrets.token_hex(16), "tenant_id": tenant, "session_id": session_id,
            "base_revision": base_revision, "proposal_revision": 1, "status": "draft", "changes": deepcopy(changes),
            "session_input_hash": session.get("input_hash"), "result_id": session.get("result_id"),
            "result_hash": content_hash(result), "calculated_metrics": calculated_metrics(result, session.get("selected_strategy_id")),
            "selected_strategy_id": selected_strategy_id or session.get("selected_strategy_id"),
            "source_candidates": sources,
            "source_conversation": discussion,
            "created_at": now(), "updated_at": now(), "version": VERSION}
        with store.connection(write=True) as c:
            c.execute(PROPOSALS.insert().values(id=proposal["id"], tenant_id=tenant, session_id=session_id, status="draft", payload=proposal))
        append_event(store, tenant, proposal["id"], "proposal_created", {"base_revision": base_revision, "result_hash": proposal["result_hash"]})
        return proposal
    return _receipt(store, tenant, idempotency_key, request, create)[0]


@_atomic_mutation
def apply_proposal(store, tenant: str, proposal_id: str, *, adapter: PlanningAdapter,
                   expected_base_revision: int, idempotency_key: str) -> dict[str, Any]:
    request = {"proposal_id": proposal_id, "expected_base_revision": expected_base_revision}
    def create():
        with store.connection() as c:
            proposal = c.execute(select(PROPOSALS.c.payload).where(PROPOSALS.c.id == proposal_id, PROPOSALS.c.tenant_id == tenant)).scalar_one_or_none()
        if not proposal: raise ValueError("Proposal not found")
        if proposal["status"] != "draft": raise ValueError("Only a draft proposal can be applied")
        if proposal["base_revision"] != expected_base_revision: raise ValueError("Proposal base revision changed")
        session = adapter.get_session(store, tenant, proposal["session_id"])
        if not session or session["revision"] != expected_base_revision: raise ValueError("Planning revision changed; refresh proposal")
        job = adapter.queue_recalculation(store, tenant, session, deepcopy(proposal["changes"]))
        proposal.update(status="applied", proposal_revision=proposal["proposal_revision"] + 1,
                        applied_session_revision=session["revision"], applied_input_hash=session.get("input_hash"),
                        recalculation_job=job, updated_at=now())
        with store.connection(write=True) as c:
            c.execute(update(PROPOSALS).where(PROPOSALS.c.id == proposal_id, PROPOSALS.c.tenant_id == tenant).values(status="applied", payload=proposal))
        append_event(store, tenant, proposal_id, "proposal_applied_recalculation_queued", {"job_id": job.get("id"), "proposal_revision": proposal["proposal_revision"]})
        return proposal
    return _receipt(store, tenant, idempotency_key, request, create)[0]


def _tasks_from_result(tenant: str, proposal: dict[str, Any], result: dict[str, Any], strategy_id: str | None) -> list[dict[str, Any]]:
    strategies = result.get("strategies", [])
    strategy = next((row for row in strategies if row.get("id") == strategy_id), strategies[0] if strategies else None)
    if not strategy or strategy.get("status", "FEASIBLE") != "FEASIBLE" or strategy.get("violations"):
        raise ValueError("A feasible calculated strategy is required before action approval")
    recipes = {row.get("id"): row for row in result.get("input_snapshot", {}).get("recipes", [])}
    snapshot = result.get("input_snapshot", {})
    planning_day = Farm.model_validate(snapshot).planning_date if snapshot.get("cutoff") and snapshot.get("beds") else None
    tasks = []
    for allocation in strategy.get("allocations", []):
        batch = allocation.get("id")
        for action, field, checklist in (("sow", "sow_date", ["Confirm seed lot", "Record sowing"]),
                                         ("transplant", "transplant_date", ["Confirm bed availability", "Record transplant"]),
                                         ("harvest", "harvest_date", ["Weigh accepted crop", "Record rejected crop"])):
            if not allocation.get(field): continue
            due = date.fromisoformat(str(allocation[field])[:10])
            # An allocation may carry historical executed stages so the planner can
            # preserve biology and lot origin. Those stages are evidence, not new work.
            if planning_day is not None and due < planning_day: continue
            # Stable across replans for the same session/allocation/action. This
            # lets approval retain reported work rather than manufacture it anew.
            task_id = "task-" + hashlib.sha256(f"{tenant}:{proposal['session_id']}:{batch}:{action}".encode()).hexdigest()[:24]
            if action == "harvest":
                planned_quantity, unit = allocation.get("expected_kg"), "kg"
            else:
                recipe = recipes.get(allocation.get("recipe_id"), {})
                density = recipe.get("density_per_m2")
                planned_quantity = (float(allocation.get("area_m2", 0)) * float(density)) if density is not None else None
                unit = "plants" if planned_quantity is not None else None
            tasks.append({"id": task_id, "tenant_id": tenant, "session_id": proposal["session_id"], "proposal_id": proposal["id"],
                "proposal_revision": proposal["proposal_revision"], "action": action, "due_date": allocation[field],
                "crop_id": allocation.get("crop_id"), "batch_id": batch, "location": allocation.get("bed_id"),
                "biological_dates": {name: allocation.get(name) for name in ("sow_date", "transplant_date", "harvest_date")},
                "checklist": checklist, "photo_required": False, "planned_quantity": planned_quantity,
                "actual_quantity": None, "unit": unit, "status": "pending", "event_revision": 0,
                "created_at": now(), "updated_at": now(), "real_operations_enabled": False})
    for delivery in strategy.get("order_allocations", []):
        if delivery.get("demand_kind") != "booked" or not delivery.get("delivered_kg"): continue
        identity = f"{delivery.get('order_id')}:{delivery.get('date')}:{delivery.get('crop_id')}"
        task_id = "task-" + hashlib.sha256(f"{tenant}:{proposal['session_id']}:delivery:{identity}".encode()).hexdigest()[:24]
        tasks.append({"id": task_id, "tenant_id": tenant, "session_id": proposal["session_id"], "proposal_id": proposal["id"],
            "proposal_revision": proposal["proposal_revision"], "action": "delivery", "due_date": delivery["date"],
            "crop_id": delivery.get("crop_id"), "batch_id": None, "order_id": delivery.get("order_id"),
            "lot_id": delivery.get("lot_allocations", [{}])[0].get("lot_id") if delivery.get("lot_allocations") else None,
            "lot_allocations": deepcopy(delivery.get("lot_allocations", [])), "location": "dispatch",
            "checklist": ["Confirm order and crop", "Record accepted and rejected weights"], "photo_required": False,
            "planned_quantity": delivery["delivered_kg"], "actual_quantity": None, "rejected_quantity": None,
            "unit": "kg", "status": "pending", "event_revision": 0, "created_at": now(), "updated_at": now(),
            "real_operations_enabled": False})
    return tasks


@_atomic_mutation
def approve_and_create_actions(store, tenant: str, proposal_id: str, *, adapter: PlanningAdapter,
                               proposal_revision: int, idempotency_key: str, selected_strategy_id: str | None = None) -> dict[str, Any]:
    request = {"proposal_id": proposal_id, "proposal_revision": proposal_revision, "selected_strategy_id": selected_strategy_id}
    def create():
        with store.connection() as c:
            proposal = c.execute(select(PROPOSALS.c.payload).where(PROPOSALS.c.id == proposal_id, PROPOSALS.c.tenant_id == tenant)).scalar_one_or_none()
        if not proposal: raise ValueError("Proposal not found")
        if proposal["status"] != "applied" or proposal["proposal_revision"] != proposal_revision:
            raise ValueError("Only the current applied proposal revision can create actions")
        session = adapter.get_session(store, tenant, proposal["session_id"])
        result = adapter.get_result(store, tenant, session.get("result_id") if session else None)
        if not session or not result: raise ValueError("Recalculation has not completed")
        queued_id = proposal.get("recalculation_job", {}).get("id")
        if not queued_id or session.get("result_id") != queued_id or session.get("status") != "COMPLETED":
            raise ValueError("The bound recalculation has not completed")
        if session.get("revision", -1) <= proposal.get("applied_session_revision", -1):
            raise ValueError("Planning revision does not include the recalculation result")
        strategy_id = selected_strategy_id or proposal.get("selected_strategy_id") or session.get("selected_strategy_id")
        tasks = _tasks_from_result(tenant, proposal, result, strategy_id)
        if hasattr(adapter, "approve_result"):
            session = adapter.approve_result(store, tenant, session, proposal, result, strategy_id)
        with store.transaction(tenant) as c:
            existing = {row["id"]: row for row in c.execute(select(TASKS.c.payload).where(TASKS.c.tenant_id == tenant, TASKS.c.session_id == proposal["session_id"])).scalars()}
            active_ids = {task["id"] for task in tasks}
            for old in existing.values():
                if old["id"] not in active_ids and old.get("event_revision", 0) > 0:
                    old.update(superseded_by_proposal_id=proposal_id, recovery_proposal_id=proposal_id, updated_at=now())
                    c.execute(update(TASKS).where(TASKS.c.id == old["id"], TASKS.c.tenant_id == tenant).values(payload=old))
                elif old["id"] not in active_ids and old["status"] in {"pending", "in_progress", "recovery_required"}:
                    old.update(status="cancelled", updated_at=now(), superseded_by_proposal_id=proposal_id)
                    c.execute(update(TASKS).where(TASKS.c.id == old["id"], TASKS.c.tenant_id == tenant).values(status="cancelled", payload=old))
            for task in tasks:
                old = existing.get(task["id"])
                if old and old.get("event_revision", 0) > 0:
                    old.update(recovery_proposal_id=proposal_id, updated_at=now())
                    task.clear(); task.update(old)
                elif old:
                    task.update(event_revision=old.get("event_revision", 0))
                    c.execute(update(TASKS).where(TASKS.c.id == task["id"], TASKS.c.tenant_id == tenant).values(proposal_id=proposal_id, status=task["status"], payload=task))
                else:
                    c.execute(TASKS.insert().values(id=task["id"], tenant_id=tenant, session_id=task["session_id"], proposal_id=proposal_id, status="pending", payload=task))
            proposal.update(status="approved", approved_at=now(), approved_result_id=session.get("result_id"), approved_result_hash=content_hash(result), updated_at=now())
            c.execute(update(PROPOSALS).where(PROPOSALS.c.id == proposal_id, PROPOSALS.c.tenant_id == tenant).values(status="approved", payload=proposal))
        append_event(store, tenant, proposal_id, "actions_created", {"proposal_revision": proposal_revision, "task_ids": [t["id"] for t in tasks]})
        return {"proposal": proposal, "tasks": tasks}
    return _receipt(store, tenant, idempotency_key, request, create)[0]


def _validate_and_derive_reported_task(task: dict[str, Any]) -> None:
    """Validate the complete reported state and derive recovery consistently."""
    quantity = Decimal(str(task["actual_quantity"])) if task.get("actual_quantity") is not None else None
    rejected = Decimal(str(task["rejected_quantity"])) if task.get("rejected_quantity") is not None else None
    planned = Decimal(str(task["planned_quantity"])) if task.get("planned_quantity") is not None else None
    for value in (quantity, rejected):
        if value is not None and (not value.is_finite() or value < 0):
            raise ValueError("Reported quantities must be finite and nonnegative")
    if quantity is not None and not task.get("unit"):
        raise ValueError("Actual quantity requires the task quantity unit")
    outcome = task.get("reported_result_status")
    if outcome is None:
        legacy_recovery = task.get("recovery") or {}
        legacy_reasons = set(legacy_recovery.get("reasons") or [])
        # Newer recovery payloads distinguish a completed-but-short/rejected
        # report from a failed attempt. Older ambiguous payloads remain failed.
        recovered_completion = bool(legacy_reasons.intersection({"quantity_below_plan", "rejected_quantity_reported"}))
        outcome = "completed" if task.get("status") == "completed" or recovered_completion else "failed"
    if outcome == "completed":
        if task.get("action") == "harvest" and quantity is None:
            raise ValueError("Completed harvest requires an actual quantity")
        if task.get("action") == "delivery" and (quantity is None or rejected is None):
            raise ValueError("Completed delivery requires accepted and rejected quantities")
        if set(task.get("checklist_completed") or []) != set(task.get("checklist") or []):
            raise ValueError("Complete every checklist item")
    if task.get("action") == "delivery" and quantity is not None and rejected is not None and planned is not None:
        if quantity + rejected > planned:
            raise ValueError("Accepted plus rejected delivery quantity exceeds its allocated lots")
    short = quantity is not None and planned is not None and quantity < planned
    recovery = outcome == "failed" or short or bool(rejected)
    task["status"] = "recovery_required" if recovery else "completed"
    reasons = (["task_failed"] if outcome == "failed" else []) + (["quantity_below_plan"] if short else []) + (["rejected_quantity_reported"] if rejected else [])
    task["forecast_feedback"] = {
        "planned_quantity": str(planned) if planned is not None else None,
        "actual_quantity": str(quantity) if quantity is not None else None,
        "delta_quantity": str(quantity - planned) if quantity is not None and planned is not None else None,
        "unit": task.get("unit"), "basis": "farmer_reported_unverified",
    }
    task["recovery"] = ({"required": True, "reasons": reasons, "preserve_completed_work": True}
                        if recovery else {"required": False})


@_atomic_mutation
def record_task_result(store, tenant: str, task_id: str, *, expected_status: str, result_status: str,
                       actual_quantity: Any = None, unit: str | None = None, photo_reference: str | None = None,
                       checklist_completed: list[str] | None = None, note: str | None = None,
                       rejected_quantity: Any = None) -> dict[str, Any]:
    if result_status not in {"completed", "failed"}: raise ValueError("Invalid task result status")
    if expected_status not in {"pending", "in_progress", "recovery_required"}:
        raise ValueError("Only unfinished tasks accept a new result")
    with store.transaction(tenant) as c:
        row = c.execute(select(TASKS).where(TASKS.c.id == task_id, TASKS.c.tenant_id == tenant).with_for_update()).mappings().first()
        if not row: raise ValueError("Task not found")
        if row["status"] != expected_status: raise ValueError("Task status changed")
        task = deepcopy(row["payload"]); quantity = None if actual_quantity is None else Decimal(str(actual_quantity))
        rejected = None if rejected_quantity is None else Decimal(str(rejected_quantity))
        if quantity is not None and (not quantity.is_finite() or quantity < 0): raise ValueError("Actual quantity must be finite and nonnegative")
        if rejected is not None and (not rejected.is_finite() or rejected < 0): raise ValueError("Rejected quantity must be finite and nonnegative")
        if quantity is not None and unit != task.get("unit"): raise ValueError("Actual quantity unit must match task unit")
        completed = checklist_completed or []
        if photo_reference:
            photo = c.execute(select(IMPORTS.c.payload).where(IMPORTS.c.id == photo_reference, IMPORTS.c.tenant_id == tenant)).scalar_one_or_none()
            if not photo or photo.get("source_kind") != "photo_observation" or photo.get("status") != "confirmed":
                raise ValueError("Photo reference must name an owned reviewed photo observation")
        task.update(reported_result_status=result_status,
                    actual_quantity=str(quantity) if quantity is not None else None,
                    rejected_quantity=str(rejected) if rejected is not None else None,
                    result_note=note, photo_reference=photo_reference, checklist_completed=completed,
                    event_revision=task["event_revision"] + 1, updated_at=now())
        _validate_and_derive_reported_task(task)
        c.execute(update(TASKS).where(TASKS.c.id == task_id, TASKS.c.tenant_id == tenant).values(status=task["status"], payload=task))
        append_event(store, tenant, task_id, "task_result_recorded", {"status": task["status"], "actual_quantity": task["actual_quantity"],
            "rejected_quantity": task.get("rejected_quantity"), "order_id": task.get("order_id"), "lot_id": task.get("lot_id"),
            "unit": task.get("unit"), "event_revision": task["event_revision"]})
        from services.api.planning_sessions import refresh_reported_forecast
        refresh_reported_forecast(store, tenant, task["session_id"])
    return task


@_atomic_mutation
def correct_task_result(store, tenant: str, task_id: str, *, expected_event_revision: int, field: str,
                        corrected_value: Any, reason: str, idempotency_key: str) -> dict[str, Any]:
    aliases = {"note": "result_note", "result_status": "status"}
    field = aliases.get(field, field)
    allowed = {"actual_quantity", "rejected_quantity", "unit", "result_note", "photo_reference", "status"}
    if field not in allowed or not reason.strip(): raise ValueError("Auditable correction field and reason are required")
    request = {"task_id": task_id, "expected_event_revision": expected_event_revision, "field": field, "value": corrected_value, "reason": reason}
    def create():
        with store.transaction(tenant) as c:
            row = c.execute(select(TASKS).where(TASKS.c.id == task_id, TASKS.c.tenant_id == tenant).with_for_update()).mappings().first()
            if not row: raise ValueError("Task not found")
            task = deepcopy(row["payload"])
            if task.get("event_revision", 0) < 1 or row["status"] in {"pending", "in_progress", "cancelled"}:
                raise ValueError("Only a previously reported task result can be corrected")
            if task["event_revision"] != expected_event_revision: raise ValueError("Task event revision changed")
            previous = task.get(field)
            normalized = corrected_value
            if field in {"actual_quantity", "rejected_quantity"}:
                value = Decimal(str(corrected_value))
                if not value.is_finite() or value < 0: raise ValueError("Actual quantity must be finite and nonnegative")
                normalized = str(value)
            elif field == "unit" and corrected_value not in {"kg", "plants", "trays", "items"}:
                raise ValueError("Unsupported quantity unit")
            elif field == "unit" and task.get("unit") is not None and corrected_value != task.get("unit"):
                raise ValueError("A correction cannot change the task quantity dimension")
            elif field == "status" and corrected_value not in {"completed", "recovery_required", "failed"}:
                raise ValueError("Unsupported corrected task status")
            if field == "photo_reference" and corrected_value:
                photo = c.execute(select(IMPORTS.c.payload).where(IMPORTS.c.id == corrected_value,
                    IMPORTS.c.tenant_id == tenant)).scalar_one_or_none()
                if not photo or photo.get("source_kind") != "photo_observation" or photo.get("status") != "confirmed":
                    raise ValueError("Photo reference must name an owned reviewed photo observation")
            task[field] = normalized
            if field == "status":
                task["reported_result_status"] = "failed" if corrected_value in {"failed", "recovery_required"} else "completed"
            _validate_and_derive_reported_task(task)
            task.update(event_revision=expected_event_revision + 1, updated_at=now())
            c.execute(update(TASKS).where(TASKS.c.id == task_id, TASKS.c.tenant_id == tenant).values(status=task["status"], payload=task))
            append_event(store, tenant, task_id, "task_result_corrected", {"field": field, "previous": previous, "corrected": task[field], "reason": reason, "event_revision": task["event_revision"]})
            from services.api.planning_sessions import refresh_reported_forecast
            refresh_reported_forecast(store, tenant, task["session_id"])
        return task
    return _receipt(store, tenant, idempotency_key, request, create)[0]


def workflow_state(store, tenant: str) -> dict[str, Any]:
    with store.connection() as c:
        imports = list(c.execute(select(IMPORTS.c.payload).where(IMPORTS.c.tenant_id == tenant)).scalars())
        proposals = list(c.execute(select(PROPOSALS.c.payload).where(PROPOSALS.c.tenant_id == tenant)).scalars())
        tasks = list(c.execute(select(TASKS.c.payload).where(TASKS.c.tenant_id == tenant)).scalars())
        events = list(c.execute(select(EVENTS.c.payload).where(EVENTS.c.tenant_id == tenant).order_by(EVENTS.c.id)).scalars())
    phase = "inbox_review" if any(x["status"] == "candidate" for x in imports) else "planning"
    if proposals: phase = "decision"
    if any(x["status"] == "approved" for x in proposals): phase = "acting"
    if tasks and all(x["status"] == "completed" for x in tasks): phase = "verification"
    if any(x["status"] == "recovery_required" for x in tasks): phase = "replanning"
    return {"version": VERSION, "phase": phase, "revision": len(events), "inbox": imports,
            "proposals": proposals, "tasks": tasks, "events": events, "real_operations_enabled": False}


def waste_rescue_scenarios(*, quantity_kg: Any, expires_on: date, today: date,
                           sale_price_sgd_per_kg: Any, rescue_price_sgd_per_kg: Any = 0,
                           rescue_cost_sgd_per_kg: Any = 0) -> dict[str, Any]:
    quantity = Decimal(str(quantity_kg)); sale = Decimal(str(sale_price_sgd_per_kg))
    rescue = Decimal(str(rescue_price_sgd_per_kg)); cost = Decimal(str(rescue_cost_sgd_per_kg))
    if any(not value.is_finite() or value < 0 for value in (quantity, sale, rescue, cost)):
        raise ValueError("Waste Rescue values must be finite and nonnegative")
    days = (expires_on - today).days
    if days < 0: raise ValueError("Expired stock requires disposal accounting, not a future rescue scenario")
    baseline_margin = quantity * sale
    rescue_margin = quantity * (rescue - cost)
    return {"version": "waste-rescue-v1", "as_of": str(today), "expires_on": str(expires_on), "days_remaining": days,
            "quantity_kg": float(quantity), "scenarios": [
                {"id": "sell_as_planned", "rescued_kg": 0.0, "projected_margin_sgd": float(baseline_margin), "margin_delta_sgd": 0.0},
                {"id": "rescue_channel", "rescued_kg": float(quantity), "projected_margin_sgd": float(rescue_margin),
                 "margin_delta_sgd": float(rescue_margin - baseline_margin)},
                {"id": "allow_expiry", "rescued_kg": 0.0, "projected_margin_sgd": 0.0,
                 "margin_delta_sgd": float(-baseline_margin)},
            ], "basis": "local_scenario_comparison", "authorizes_operation": False}


class ManualImportRequest(Strict):
    source_name: str = Field(min_length=1, max_length=200)
    import_kind: str = Field(default="manual", pattern="^(manual|correction)$")
    rows: list[dict[str, Any]] = Field(min_length=1, max_length=1000)


class CreateProposalRequest(Strict):
    session_id: str = Field(min_length=1, max_length=100)
    base_revision: int = Field(ge=0, strict=True)
    changes: list[dict[str, Any]] = Field(min_length=1, max_length=64)
    selected_strategy_id: str | None = Field(default=None, max_length=100)
    source_candidate_ids: list[str] = Field(default_factory=list, max_length=32)
    source_conversation_id: str | None = Field(default=None, min_length=1, max_length=100)
    source_message_id: str | None = Field(default=None, min_length=1, max_length=100)
    idempotency_key: str = Field(min_length=1, max_length=128)


class WasteRescueRequest(Strict):
    session_id: str = Field(min_length=1, max_length=100)
    result_id: str = Field(min_length=1, max_length=100)
    strategy_id: str = Field(min_length=1, max_length=100)
    lot_id: str | None = Field(default=None, max_length=100)
    sale_price_sgd_per_kg: Decimal = Field(default=0, ge=0, le=10000)
    rescue_price_sgd_per_kg: Decimal = Field(default=0, ge=0, le=10000)
    rescue_cost_sgd_per_kg: Decimal = Field(default=0, ge=0, le=10000)


def _http_error(exc: ValueError):
    message = str(exc)
    code = 404 if "not found" in message.lower() else 409 if any(word in message.lower() for word in ("changed", "reused", "completed", "current", "unfinished")) else 422
    raise HTTPException(code, message) from None


def register(app, tenant):
    """Register the complete tenant-scoped V12 workflow HTTP boundary."""
    from services.api import planning_sessions

    class Adapter:
        get_session = staticmethod(planning_sessions.get_session)
        get_result = staticmethod(planning_sessions.get_result)
        def queue_recalculation(self, store, tenant_id, session, changes):
            if not hasattr(planning_sessions, "queue_recalculation"):
                raise ValueError("Workflow recalculation adapter unavailable")
            return planning_sessions.queue_recalculation(store, tenant_id, session, changes)
        def approve_result(self, store, tenant_id, session, proposal, result, strategy_id):
            if not hasattr(planning_sessions, "approve_result"):
                raise ValueError("Workflow approval adapter unavailable")
            return planning_sessions.approve_result(store, tenant_id, session, proposal, result, strategy_id)
    adapter = Adapter()

    @app.get("/api/v1/farm-workflow")
    def state(request: Request): return workflow_state(app.state.store, tenant(request))

    @app.post("/api/v1/farm-workflow/imports", status_code=201)
    def manual(body: ManualImportRequest, request: Request):
        t = tenant(request)
        try:
            candidate = FinancialDataConnector().from_rows(tenant_id=t, source_name=body.source_name, rows=body.rows,
                                                            import_kind=body.import_kind)
            return save_import(app.state.store, t, candidate, source_kind=body.import_kind)
        except ValueError as exc: _http_error(exc)

    @app.post("/api/v1/farm-workflow/imports/upload", status_code=201)
    async def upload(request: Request, filename: str, source_kind: str = "document_extraction"):
        t = tenant(request); raw = await request.body()
        try:
            digest = hashlib.sha256(raw).hexdigest()
            with app.state.store.connection() as c:
                prior = [row for row in c.execute(select(IMPORTS.c.payload).where(IMPORTS.c.tenant_id == t)).scalars()
                         if (row.get("source_sha256") or row.get("sha256")) == digest and row.get("source_kind") == source_kind]
            if prior:
                save_source_blob(app.state.store, t, prior[0]["candidate_id"], raw=raw, filename=filename,
                                 media_type=request.headers.get("content-type", "application/octet-stream"))
                return prior[0]
            if source_kind in {"accounting_export"}:
                candidate = FinancialDataConnector().parse(tenant_id=t, source_name=filename, payload=raw,
                    media_type=request.headers.get("content-type", "application/octet-stream"))
                with app.state.store.transaction(t):
                    saved = save_import(app.state.store, t, candidate, source_kind=source_kind)
                    save_source_blob(app.state.store, t, saved["candidate_id"], raw=raw, filename=filename,
                                     media_type=request.headers.get("content-type", "application/octet-stream"))
                return saved
            from services.api.document_extraction import extract_document
            from starlette.concurrency import run_in_threadpool
            extracted = await run_in_threadpool(extract_document, app.state.store, t, raw, filename, source_kind)
            digest = extracted["provenance"]["source_sha256"]
            if source_kind == "document_extraction":
                candidate = FinancialDataConnector().from_rows(tenant_id=t, source_name=filename, rows=extracted["rows"],
                    import_kind="accounting_export", source_sha256=digest, media_type=request.headers.get("content-type", "application/octet-stream"))
                payload = _json(candidate); payload["warnings"] = extracted["warnings"]; payload["provenance"] = extracted["provenance"]
            else:
                observation_id = "obs-" + hashlib.sha256(f"{t}:{digest}".encode()).hexdigest()[:24]
                payload = {"id": observation_id, "candidate_id": observation_id, "tenant_id": t,
                    "source_name": filename, "sha256": digest, "source_sha256": digest, "created_at": now(), "status": "candidate",
                    "rows": extracted["rows"], "warnings": extracted["warnings"], "provenance": extracted["provenance"]}
            with app.state.store.transaction(t):
                saved = save_import(app.state.store, t, payload, source_kind=source_kind)
                save_source_blob(app.state.store, t, saved["candidate_id"], raw=raw, filename=filename,
                                 media_type=request.headers.get("content-type", "application/octet-stream"))
            return saved
        except ValueError as exc: _http_error(exc)
        except HTTPException: raise
        except Exception as exc:
            from runtime.deepseek_gateway import DeepSeekPolicyError
            if isinstance(exc, DeepSeekPolicyError):
                raise HTTPException(422, "Uploaded document or image could not be decoded within the extraction policy") from None
            raise

    def source_response(candidate_id: str, request: Request, *, download: bool):
        if not candidate_id or len(candidate_id) > 100 or any(value in candidate_id for value in ("/", "\\", "..")):
            raise HTTPException(404, "Candidate source not found")
        t = tenant(request)
        with app.state.store.connection() as c:
            row = c.execute(select(SOURCE_BLOBS).where(SOURCE_BLOBS.c.candidate_id == candidate_id,
                SOURCE_BLOBS.c.tenant_id == t)).mappings().first()
        if not row: raise HTTPException(404, "Candidate source not found")
        disposition = "attachment" if download else "inline"
        return Response(content=row["payload"], media_type=row["media_type"], headers={
            "Content-Disposition": f'{disposition}; filename="{row["filename"]}"',
            "X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-store",
            "Content-Security-Policy": "sandbox; default-src 'none'",
            "ETag": f'"{row["sha256"]}"',
        })

    @app.get("/api/v1/farm-workflow/imports/{candidate_id}/source")
    def preview_source(candidate_id: str, request: Request): return source_response(candidate_id, request, download=False)

    @app.get("/api/v1/farm-workflow/imports/{candidate_id}/source/download")
    def download_source(candidate_id: str, request: Request): return source_response(candidate_id, request, download=True)

    @app.post("/api/v1/farm-workflow/imports/{candidate_id}/review")
    def review(candidate_id: str, body: ReviewImportRequest, request: Request):
        try: return review_import(app.state.store, tenant(request), candidate_id, **body.model_dump(exclude_none=True))
        except ValueError as exc: _http_error(exc)

    @app.post("/api/v1/farm-workflow/proposals", status_code=201)
    def proposal(body: CreateProposalRequest, request: Request):
        try: return create_proposal(app.state.store, tenant(request), adapter=adapter, **body.model_dump())
        except ValueError as exc: _http_error(exc)

    @app.post("/api/v1/farm-workflow/proposals/{proposal_id}/apply", status_code=202)
    def apply(proposal_id: str, body: ApplyProposalRequest, request: Request):
        if body.proposal_id != proposal_id: raise HTTPException(422, "Proposal path/body mismatch")
        try: return apply_proposal(app.state.store, tenant(request), proposal_id, adapter=adapter,
                                   expected_base_revision=body.expected_base_revision, idempotency_key=body.idempotency_key)
        except ValueError as exc: _http_error(exc)

    @app.post("/api/v1/farm-workflow/proposals/{proposal_id}/approve-actions")
    def approve(proposal_id: str, body: ApproveActionsRequest, request: Request):
        if body.proposal_id != proposal_id: raise HTTPException(422, "Proposal path/body mismatch")
        try:
            return approve_and_create_actions(app.state.store, tenant(request), proposal_id, adapter=adapter,
                proposal_revision=body.proposal_revision, idempotency_key=body.idempotency_key,
                selected_strategy_id=body.selected_strategy_id)
        except ValueError as exc: _http_error(exc)

    @app.post("/api/v1/farm-workflow/tasks/{task_id}/result")
    def result(task_id: str, body: TaskResultRequest, request: Request):
        try: return record_task_result(app.state.store, tenant(request), task_id, **body.model_dump())
        except ValueError as exc: _http_error(exc)

    @app.post("/api/v1/farm-workflow/tasks/{task_id}/corrections")
    def correction(task_id: str, body: CorrectionRequest, request: Request):
        try: return correct_task_result(app.state.store, tenant(request), task_id, **body.model_dump())
        except ValueError as exc: _http_error(exc)

    @app.post("/api/v1/farm-workflow/waste-rescue")
    def rescue(body: WasteRescueRequest, request: Request):
        t = tenant(request)
        try:
            session = planning_sessions.get_session(app.state.store, t, body.session_id)
            if not session or body.result_id not in {session.get("result_id"), session.get("approved_result_id")}:
                raise ValueError("Bound planning session/result not found")
            result = planning_sessions.get_result(app.state.store, t, body.result_id)
            strategy = next((row for row in (result or {}).get("strategies", []) if row.get("id") == body.strategy_id), None)
            if not strategy: raise ValueError("Bound strategy not found")
            snapshots = strategy.get("inventory_snapshots", [])
            if not snapshots: raise ValueError("Frozen strategy has no dated terminal inventory snapshot")
            terminal = snapshots[-1]
            as_of = date.fromisoformat(terminal["date"])
            lots = [{"lot_id": row["id"], "crop_id": row.get("crop_id"), "quantity_kg": row["quantity_kg"],
                     "harvested_date": row.get("harvested_date"), "expires_on": row["expires_date"],
                     "origin": row.get("origin")} for row in terminal.get("closing_lots", []) if Decimal(str(row.get("quantity_kg", 0))) > 0]
            if not lots: raise ValueError("Frozen strategy has no terminal surplus lots")
            if body.lot_id:
                lot = next((row for row in lots if row["lot_id"] == body.lot_id), None)
                if not lot: raise ValueError("Bound surplus lot not found")
                selected_lots = [lot]; selection_basis = "selected_exact_terminal_lot"
            else:
                selected_lots = lots
                selection_basis = "all_terminal_lots_aggregated_using_earliest_actual_expiry"
            quantity = sum((Decimal(str(row["quantity_kg"])) for row in selected_lots), Decimal(0))
            expires = min(date.fromisoformat(row["expires_on"]) for row in selected_lots)
            comparison = waste_rescue_scenarios(quantity_kg=quantity, expires_on=expires, today=as_of,
                sale_price_sgd_per_kg=body.sale_price_sgd_per_kg, rescue_price_sgd_per_kg=body.rescue_price_sgd_per_kg,
                rescue_cost_sgd_per_kg=body.rescue_cost_sgd_per_kg)
            comparison["binding"] = {"session_id": body.session_id, "result_id": body.result_id,
                "strategy_id": body.strategy_id, "lot_id": body.lot_id, "result_hash": content_hash(result),
                "derived_quantity_kg": float(quantity)}
            comparison["surplus_lots"] = lots
            comparison["selected_lot_ids"] = [row["lot_id"] for row in selected_lots]
            comparison["selection_basis"] = selection_basis
            comparison["as_of_basis"] = "frozen_terminal_inventory_snapshot_at_horizon_close"
            comparison["basis"] = "hypothetical_local_comparison_of_frozen_projected_terminal_stock"
            return comparison
        except ValueError as exc: _http_error(exc)
