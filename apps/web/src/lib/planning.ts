import type { Farm, Strategy } from "./types";
import type { SimulationWorld } from "./api";
import { mutationRequest, request } from "./api";
import { editionStorageKey } from "./edition";
import type { SceneTransition, StoredExplanation } from "./cards";

export type PlanningStage =
  | "records"
  | "planning"
  | "review"
  | "simulation"
  | "comparison";
export type PlanningJobStatus =
  | "QUEUED"
  | "RUNNING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

export interface FutureDemandAssumption {
  crop_id: string;
  start_date: string;
  end_date: string;
  percent: number;
}
export interface SeasonalAssumption {
  crop_id: string;
  system: "sheltered_hydroponic";
  start_date: string;
  end_date: string;
  yield_percent: number;
  delay_days: number;
  reason: string;
  provenance: "synthetic_assumption";
}
export interface OrderChange {
  operation: "add" | "amend" | "cancel";
  order_id: string;
  crop_id?: string;
  due_date?: string;
  quantity_kg?: number;
  price_sgd_per_kg?: number;
}
export interface PlanningAssumptions {
  future_demand: FutureDemandAssumption[];
  seasonal: SeasonalAssumption[];
  order_changes: OrderChange[];
}
export interface PlanningJob {
  id: string;
  kind: string;
  status: PlanningJobStatus;
  stage: string;
  error?: string | null;
}
export interface PlanningReview {
  status: string;
  findings?: Array<Record<string, unknown>>;
  [key: string]: unknown;
}
export interface AllocationChange {
  operation?: string;
  change?: string;
  bed_id?: string;
  crop_id?: string;
  before?: Record<string, unknown> | null;
  after?: Record<string, unknown> | null;
  [key: string]: unknown;
}
export interface PlanningResult {
  strategies?: Strategy[];
  forecast?: Record<string, unknown> | null;
  retained_strategy?: Strategy | Record<string, unknown> | null;
  comparisons?:
    | Array<Record<string, unknown>>
    | Record<string, Record<string, unknown>>;
  allocation_changes?: AllocationChange[];
  [key: string]: unknown;
}
export interface PlanningSession {
  guidance?: { version: 'integrated-guidance-v1'; revision: number; step: 'inspect' | 'compare' | 'tradeoff' | 'review' | 'recalculate' | 'approve' | 'results'; skipped: boolean };
  id: string;
  revision: number;
  created_at: string;
  updated_at: string;
  status: string;
  stage: PlanningStage;
  farm: Farm;
  input_hash: string;
  result?: PlanningResult | null;
  selected_strategy_id?: string | null;
  review?: PlanningReview | null;
  assumptions?: PlanningAssumptions | null;
  simulation?: SimulationWorld | null;
  job?: PlanningJob | null;
  history?: Array<Record<string, unknown>>;
  data_mode: "synthetic_demo";
  tactical_context?: {
    version: string;
    planning_snapshot: {
      session_id: string;
      result_id?: string | null;
      input_hash: string;
      revision: number;
    };
    scenario: {
      id: string;
      entity_kind: "scenario";
      title: string;
      label: string;
      source: string;
      execution_mode: "simulation";
      inference_triggered: false;
      ask_eligible: boolean;
      ask_disabled_reason?: string | null;
    };
    grow_space?: {
      id: string;
      entity_kind: "grow_space";
      title: string;
      name: string;
      area_m2: number;
      system: string;
      source: string;
      reservation_window: { start_date: string; end_date: string };
      reservation_active: boolean;
      reserve_eligible: boolean;
      reserve_disabled_reason?: string | null;
      ask_eligible: boolean;
      ask_disabled_reason?: string | null;
    } | null;
  };
  [key: string]: unknown;
}

export interface FarmerProposal {
  explanation?: StoredExplanation;
  scene_transition?: SceneTransition;
  approval?: { available: boolean; reason: string | null; strategy_id?: string };
  id: string;
  session_id: string;
  base_revision: number;
  proposal_revision: number;
  status: string;
  selected_strategy_id?: string;
  calculated_metrics: Record<string, number | null>;
  recalculated_metrics?: Record<string, number | null>;
  metric_deltas?: Record<string, number | null>;
  recalculation_job?: { id?: string; status?: string };
  inverse_of_proposal_id?: string;
  inverse_proposal_id?: string;
  undo?: {
    available: boolean;
    reason?: string | null;
    expected_session_revision?: number;
  };
  [key: string]: unknown;
}
export interface FarmerTask {
  id: string;
  proposal_id: string;
  proposal_revision: number;
  action: string;
  due_date: string;
  crop_id?: string;
  batch_id?: string;
  location?: string;
  checklist: string[];
  planned_quantity?: number | null;
  actual_quantity?: number | string | null;
  unit?: string | null;
  status: string;
  event_revision: number;
  recovery?: { required?: boolean; reason?: string };
  [key: string]: unknown;
}
export interface FarmerImport {
  candidate_id: string;
  source_name: string;
  source_kind: string;
  status: string;
  warnings?: string[];
  rows?: Record<string, unknown>[];
  authority?: string;
  planning_eligible?: boolean;
  [key: string]: unknown;
}
export interface FarmerWorkflowState {
  version: string;
  phase: string;
  revision: number;
  inbox: FarmerImport[];
  proposals: FarmerProposal[];
  tasks: FarmerTask[];
  events: Array<Record<string, unknown>>;
  real_operations_enabled: false;
}
export interface FarmerAssumptions {
  tentative_orders: Array<Record<string, unknown>>;
  future_demand: Array<Record<string, unknown>>;
  seasonal: Array<Record<string, unknown>>;
  order_changes: Array<Record<string, unknown>>;
  reservations: Array<{ bed_id: string; start_date: string; end_date: string }>;
  capacity?: {
    nursery_sites?: number;
    labour_hours_per_week?: number;
    cash_sgd?: number;
  };
}

const key = editionStorageKey("planning-session");
export function rememberedPlanningSession() {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}
export function rememberPlanningSession(id: string) {
  try {
    localStorage.setItem(key, id);
  } catch {
    /* persistence is optional */
  }
}

export const planningApi = {
  importFarm: (expected_farm_version:number, source:{farm:unknown}|{fixture:'synthetic_demo'}, name='Imported farm workflow') =>
    mutationRequest<PlanningSession>('/planning-sessions/import', {expected_farm_version, ...source, name}),
  replayResult: (sessionId: string, resultId: string) => request<{session_id:string;result_id:string;result:PlanningResult;replay:true}>(
    `/planning-sessions/${encodeURIComponent(sessionId)}/results/${encodeURIComponent(resultId)}`),
  guidance: (session: PlanningSession, step: NonNullable<PlanningSession['guidance']>['step'], skipped = false) =>
    mutationRequest<PlanningSession>(`/planning-sessions/${encodeURIComponent(session.id)}/guidance`, {
      version: 'integrated-guidance-v1', revision: session.guidance?.revision ?? 0, step, skipped,
    }),
  list: () => request<{ sessions: PlanningSession[] }>("/planning-sessions"),
  create: (name = "Farm production mission", workflow = false) =>
    mutationRequest<PlanningSession>("/planning-sessions", { name, workflow }),
  get: (id: string) =>
    request<PlanningSession>(`/planning-sessions/${encodeURIComponent(id)}`),
  calculate: (id: string, revision: number) =>
    mutationRequest<PlanningSession>(
      `/planning-sessions/${encodeURIComponent(id)}/calculate`,
      { revision },
    ),
  review: (id: string, revision: number) =>
    mutationRequest<PlanningSession>(
      `/planning-sessions/${encodeURIComponent(id)}/review`,
      { revision },
    ),
  disrupt: (id: string, revision: number, assumptions: PlanningAssumptions) =>
    mutationRequest<PlanningSession>(
      `/planning-sessions/${encodeURIComponent(id)}/disrupt`,
      { revision, assumptions },
    ),
  advance: (id: string, revision: number, days: 1 | 7) =>
    mutationRequest<PlanningSession>(
      `/planning-sessions/${encodeURIComponent(id)}/advance`,
      { revision, days },
    ),
  cancel: (id: string, revision: number) =>
    mutationRequest<PlanningSession>(
      `/planning-sessions/${encodeURIComponent(id)}/cancel`,
      { revision },
    ),
};

export const farmerWorkflowApi = {
  state: () => request<FarmerWorkflowState>("/farm-workflow"),
  manualImport: (sourceName: string, rows: Array<Record<string, unknown>>) =>
    mutationRequest<FarmerImport>("/farm-workflow/imports", {
      source_name: sourceName,
      import_kind: "manual",
      rows,
    }),
  upload: (file: File, sourceKind: string) =>
    request<FarmerImport>(
      `/farm-workflow/imports/upload?filename=${encodeURIComponent(file.name)}&source_kind=${encodeURIComponent(sourceKind)}`,
      {
        method: "POST",
        headers: { "Content-Type": file.type || "application/octet-stream" },
        body: file,
      },
    ),
  reviewImport: (
    id: string,
    decision: "confirm" | "reject",
    reviewer = "farmer",
    note?: string,
  ) =>
    mutationRequest<FarmerImport>(
      `/farm-workflow/imports/${encodeURIComponent(id)}/review`,
      { expected_status: "candidate", decision, reviewer, note },
    ),
  createProposal: (
    session: PlanningSession,
    strategyId: string,
    assumptions: FarmerAssumptions,
    sourceCandidateIds: string[] = [],
    sourceConversation?: { conversation_id: string; message_id: string },
  ) =>
    mutationRequest<FarmerProposal>("/farm-workflow/proposals", {
      session_id: session.id,
      base_revision: session.revision,
      changes: [{ kind: "planning_assumptions", assumptions }],
      selected_strategy_id: strategyId,
      source_candidate_ids: sourceCandidateIds,
      source_conversation_id: sourceConversation?.conversation_id,
      source_message_id: sourceConversation?.message_id,
      idempotency_key: crypto.randomUUID(),
    }),
  applyProposal: (proposal: FarmerProposal) =>
    mutationRequest<FarmerProposal>(
      `/farm-workflow/proposals/${encodeURIComponent(proposal.id)}/apply`,
      {
        proposal_id: proposal.id,
        expected_base_revision: proposal.base_revision,
        idempotency_key: crypto.randomUUID(),
      },
    ),
  inverseProposal: (proposal: FarmerProposal) =>
    mutationRequest<FarmerProposal>(
      `/farm-workflow/proposals/${encodeURIComponent(proposal.id)}/inverse`,
      {
        proposal_id: proposal.id,
        proposal_revision: proposal.proposal_revision,
        expected_session_revision: proposal.undo?.expected_session_revision,
        idempotency_key: crypto.randomUUID(),
      },
    ),
  approve: (proposal: FarmerProposal) =>
    mutationRequest<{ proposal: FarmerProposal; tasks: FarmerTask[] }>(
      `/farm-workflow/proposals/${encodeURIComponent(proposal.id)}/approve-actions`,
      {
        proposal_id: proposal.id,
        proposal_revision: proposal.proposal_revision,
        selected_strategy_id: typeof proposal.recalculated_strategy_id === 'string' ? proposal.recalculated_strategy_id : proposal.selected_strategy_id,
        idempotency_key: crypto.randomUUID(),
      },
    ),
  taskResult: (
    task: FarmerTask,
    status: "completed" | "failed",
    actualQuantity: number | null,
    rejectedQuantity: number | null,
    note: string,
    checklistCompleted: string[],
    photoReference: string | null,
  ) =>
    mutationRequest<FarmerTask>(
      `/farm-workflow/tasks/${encodeURIComponent(task.id)}/result`,
      {
        expected_status: task.status,
        result_status: status,
        actual_quantity: actualQuantity,
        rejected_quantity: rejectedQuantity,
        unit: task.unit || undefined,
        photo_reference: photoReference,
        checklist_completed: checklistCompleted,
        note,
      },
    ),
  correctTask: (
    task: FarmerTask,
    field: string,
    correctedValue: unknown,
    reason: string,
  ) =>
    mutationRequest<FarmerTask>(
      `/farm-workflow/tasks/${encodeURIComponent(task.id)}/corrections`,
      {
        expected_event_revision: task.event_revision,
        field,
        corrected_value: correctedValue,
        reason,
        idempotency_key: crypto.randomUUID(),
      },
    ),
  wasteRescue: (body: {
    session_id: string;
    result_id: string;
    strategy_id: string;
    lot_id?: string;
    sale_price_sgd_per_kg: number;
    rescue_price_sgd_per_kg: number;
    rescue_cost_sgd_per_kg: number;
  }) =>
    mutationRequest<{
      as_of: string;
      as_of_basis: string;
      expires_on: string;
      days_remaining: number;
      quantity_kg: number;
      surplus_lots: Array<{lot_id:string;crop_id:string;quantity_kg:number;harvested_date:string;expires_on:string;origin:string}>;
      selected_lot_ids: string[];
      selection_basis: string;
      scenarios: Array<{
        id: string;
        rescued_kg: number;
        projected_margin_sgd: number;
        margin_delta_sgd: number;
      }>;
      basis: string;
      binding: Record<string, string>;
      authorizes_operation: false;
    }>("/farm-workflow/waste-rescue", body),
};
