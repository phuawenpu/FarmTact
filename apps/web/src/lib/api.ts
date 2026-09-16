import type { Bootstrap, Crop, EvidenceRecord, Run } from "./types";
import type {
  Conversation,
  Quest,
  Scenario,
  ScenarioComparison,
  ScenarioControls,
} from "./game";
import type {
  ExplorerDetail,
  ExplorerSnapshotSummary,
  ForecastSettings,
  GeneratorSettings,
  PublicContext,
} from "./explorer";
import { editionPath, editionStorageKey } from "./edition";
import type { NewsContext } from "./news";

export interface MarketSignals {
  crop_id?: string | null;
  source?: string | { id?: string; name?: string };
  status: string;
  observation_count?: number;
  observations?: unknown[];
  connected_social_feeds?: boolean;
  feeds?: unknown[];
  sources?: Array<string | { id?: string; name?: string }>;
  summary?: string;
  provenance?: string | string[];
  limitations?: string[];
}

export interface SimulationBed {
  id: string;
  name: string;
  area_m2: number;
  stage: string;
  progress: number;
  crop_id?: string;
  allocation_id?: string;
  sow_date?: string;
  transplant_date?: string;
  harvest_date?: string;
  nursery_allocations?: string[];
  sanitation_end_date?: string;
  next_available_date?: string;
  next_transition?: string;
}
export interface SimulationWorld {
  id: string;
  engine_version: string;
  revision: number;
  status: string;
  run_id: string;
  clock_date: string | null;
  start_date: string;
  end_date: string;
  days_executed: number;
  strategy_id: string;
  strategy_name: string;
  event_sequence: number;
  beds: SimulationBed[];
  inventory: Array<{
    id?: string;
    crop_id?: string;
    quantity_kg?: string | number;
    expires_date?: string;
  }>;
  totals: {
    harvest_kg: number;
    delivered_kg: number;
    disposed_kg: number;
    demand_kg: number;
  };
  cash_sgd: number;
  revenue_sgd: number;
  cost_sgd: number;
  plan_history: Array<Record<string, unknown>>;
  simulation_only: true;
  inference_triggered: false;
  real_operations_enabled: false;
  outcome_basis: string;
  [key: string]: unknown;
}
export interface SimulationEvent {
  sequence: number;
  type: string;
  date: string;
  recorded_at: string;
  origin: string;
  task?: string;
  task_id?: string;
  allocation_id?: string;
  bed_id?: string;
  crop_id?: string;
  ledger?: Record<string, unknown>;
  [key: string]: unknown;
}

const API = () => editionPath("/api/v1");

export class ApiError extends Error {
  status: number;
  detail?: string;
  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.status = status;
    this.detail = detail;
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API()}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData
        ? {}
        : { "Content-Type": "application/json" }),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    let detail: string | undefined;
    try {
      const payload = (await response.json()) as { detail?: unknown };
      if (typeof payload.detail === "string") detail = payload.detail;
      else if (Array.isArray(payload.detail))
        detail = payload.detail
          .map((item) => {
            if (!item || typeof item !== "object")
              return "Check the entered assumptions.";
            const issue = item as { loc?: unknown[]; msg?: unknown };
            const field = (issue.loc || [])
              .filter((part) => part !== "body")
              .join(" · ")
              .replaceAll("_", " ");
            return `${field ? `${field}: ` : ""}${typeof issue.msg === "string" ? issue.msg : "Check this value."}`;
          })
          .join(" ");
    } catch {
      detail = undefined;
    }
    throw new ApiError(
      detail || `Request failed (${response.status})`,
      response.status,
      detail,
    );
  }
  return response.json() as Promise<T>;
}

type PendingMutation = { key: string; created_at: string };

function pendingMutations(): Record<string, PendingMutation> {
  try {
    return JSON.parse(
      sessionStorage.getItem(editionStorageKey("pending-mutations")) || "{}",
    ) as Record<string, PendingMutation>;
  } catch {
    return {};
  }
}

function savePending(values: Record<string, PendingMutation>) {
  try {
    sessionStorage.setItem(
      editionStorageKey("pending-mutations"),
      JSON.stringify(values),
    );
  } catch {
    /* storage may be disabled */
  }
}

function mutationIdentity(method: string, path: string, body: string) {
  return JSON.stringify([method.toUpperCase(), path, body]);
}

/** Reuse a mutation key after reload when the prior network/5xx outcome is uncertain. */
export async function mutationRequest<T>(
  path: string,
  body: unknown,
  init: Omit<RequestInit, "method" | "body"> & { method?: string } = {},
  requiredKey?: string,
): Promise<T> {
  const method = init.method || "POST",
    encoded = JSON.stringify(body);
  const identity = mutationIdentity(method, path, encoded),
    pending = pendingMutations();
  const operation = pending[identity] || {
    key: requiredKey || crypto.randomUUID(),
    created_at: new Date().toISOString(),
  };
  pending[identity] = operation;
  savePending(pending);
  try {
    const result = await request<T>(path, {
      ...init,
      method,
      body: encoded,
      headers: { ...init.headers, "Idempotency-Key": operation.key },
    });
    const current = pendingMutations();
    delete current[identity];
    savePending(current);
    return result;
  } catch (error) {
    if (
      error instanceof ApiError &&
      error.status >= 400 &&
      error.status < 500 &&
      ![408, 425, 429].includes(error.status)
    ) {
      const current = pendingMutations();
      delete current[identity];
      savePending(current);
    }
    throw error;
  }
}

export const api = {
  news: (query: URLSearchParams = new URLSearchParams()) =>
    request<NewsContext>(`/news?${query}`),
  bootstrap: () => request<Bootstrap>("/bootstrap"),
  crop: async (id: string) => {
    const response = await request<{ crop: Crop; evidence: EvidenceRecord[] }>(
      `/crops/${encodeURIComponent(id)}/evidence`,
    );
    return { ...response.crop, evidence: response.evidence };
  },
  importSeed: () =>
    mutationRequest<{ id: string; status: string; version: number }>(
      "/imports",
      { fixture: "synthetic_demo" },
    ),
  importFarm: (farm: unknown) =>
    mutationRequest<{ id: string; status: string; version: number }>(
      "/imports",
      { farm },
    ),
  createRun: (council = true) =>
    mutationRequest<{ id: string; status: string }>("/planning-runs", {
      council,
    }),
  run: (id: string) => request<Run>(`/planning-runs/${encodeURIComponent(id)}`),
  replan: (id: string) =>
    mutationRequest<{ id: string; status: string } | Run>(
      `/planning-runs/${encodeURIComponent(id)}/replan`,
      { disruption: "crop_delay" },
    ),
  replay: (id: string) =>
    request<Run>(`/planning-runs/${encodeURIComponent(id)}/replay`),
  demoReplay: () => request<Run>("/demo/replay"),
  eventsUrl: (id: string) =>
    `${API()}/planning-runs/${encodeURIComponent(id)}/events`,
  conversations: async () =>
    (await request<{ conversations: Conversation[] }>("/conversations"))
      .conversations,
  conversation: (id: string) =>
    request<Conversation>(`/conversations/${encodeURIComponent(id)}`),
  conversationReplay: (id: string) =>
    request<Conversation>(`/conversations/${encodeURIComponent(id)}/replay`),
  createConversation: (body: {
    advisor: string;
    snapshot_kind: "farm" | "scenario" | "planning";
    snapshot_id?: string;
    selected_bed_id?: string;
  }) =>
    mutationRequest<{ id: string; status: string; reused?: boolean }>(
      "/conversations",
      body,
    ),
  sendConversationMessage: (
    id: string,
    body: { content: string; reply_to?: string },
  ) =>
    mutationRequest<{
      id: string;
      conversation_id: string;
      status: string;
      message_id?: string;
    }>(`/conversations/${encodeURIComponent(id)}/messages`, body),
  inviteAdvisor: (
    id: string,
    body: { advisor: string; question: string; reply_to: string },
  ) =>
    mutationRequest<{ id: string; conversation_id: string; status: string }>(
      `/conversations/${encodeURIComponent(id)}/invite`,
      body,
    ),
  conveneCouncil: (id: string, body: { question: string; reply_to?: string }) =>
    mutationRequest<{ id: string; conversation_id: string; status: string }>(
      `/conversations/${encodeURIComponent(id)}/council`,
      body,
    ),
  scenarioPage: (limit = 12, before?: string) =>
    request<{ scenarios: Scenario[] }>(
      `/scenarios?limit=${limit}${before ? `&before=${encodeURIComponent(before)}` : ""}`,
    ),
  scenarios: async () =>
    (await request<{ scenarios: Scenario[] }>("/scenarios?limit=30")).scenarios,
  scenario: (id: string) =>
    request<Scenario>(`/scenarios/${encodeURIComponent(id)}`),
  createScenario: (body: {
    name: string;
    parent_scenario_id?: string;
    source_conversation_id?: string;
    explorer_snapshot_id?: string;
    controls: ScenarioControls;
    quest_id?: string;
  }) => mutationRequest<Scenario>("/scenarios", body),
  runScenario: (id: string) =>
    mutationRequest<Scenario>(`/scenarios/${encodeURIComponent(id)}/run`, {}),
  retryScenario: (id: string, originalRunKey: string) =>
    mutationRequest<Scenario>(
      `/scenarios/${encodeURIComponent(id)}/retry`,
      {},
      {},
      originalRunKey,
    ),
  cancelScenario: (id: string) =>
    mutationRequest<Scenario>(
      `/scenarios/${encodeURIComponent(id)}/cancel`,
      {},
    ),
  compareScenarios: (ids: string[]) =>
    request<ScenarioComparison>(
      `/scenarios/compare?ids=${encodeURIComponent(ids.join(","))}`,
    ),
  quests: async () => (await request<{ quests: Quest[] }>("/quests")).quests,
  inspectQuest: (questId: string, scenarioId: string) =>
    mutationRequest<Quest>(`/quests/${encodeURIComponent(questId)}/inspect`, {
      scenario_id: scenarioId,
    }),
  explorerSnapshots: async () =>
    (
      await request<{ snapshots: ExplorerSnapshotSummary[] }>(
        "/data-explorer/snapshots",
      )
    ).snapshots,
  explorerSnapshot: (id: string, policy = "Balanced") =>
    request<ExplorerDetail>(
      `/data-explorer/snapshots/${encodeURIComponent(id)}?policy=${encodeURIComponent(policy)}`,
    ),
  explorerEvaluation: () =>
    request<Record<string, unknown>>("/data-explorer/evaluation"),
  explorerPreview: (
    generator_settings: GeneratorSettings,
    forecast_settings: ForecastSettings,
    signal?: AbortSignal,
  ) =>
    request<ExplorerDetail>("/data-explorer/preview", {
      method: "POST",
      signal,
      body: JSON.stringify({ generator_settings, forecast_settings }),
    }),
  saveExplorerSnapshot: (
    name: string,
    generator_settings: GeneratorSettings,
    forecast_settings: ForecastSettings,
  ) =>
    mutationRequest<ExplorerDetail>("/data-explorer/snapshots", {
      name,
      generator_settings,
      forecast_settings,
    }),
  explorerPublic: () => request<PublicContext>("/data-explorer/public"),
  marketSignals: (crop?: string) =>
    request<MarketSignals>(
      `/market-signals${crop ? `?crop=${encodeURIComponent(crop)}` : ""}`,
    ),
  explorerExportUrl: (params: URLSearchParams) =>
    `${API()}/data-explorer/export?${params.toString()}`,
  simulations: async () =>
    (
      await request<{
        simulations: Array<{
          id: string;
          revision: number;
          status: string;
          run_id: string;
          clock_date: string | null;
          days_executed: number;
        }>;
      }>("/simulations")
    ).simulations,
  simulation: (id: string) =>
    request<SimulationWorld>(`/simulations/${encodeURIComponent(id)}`),
  simulationEvents: (id: string) =>
    request<{
      events: SimulationEvent[];
      event_sequence: number;
      next_cursor?: number | null;
    }>(`/simulations/${encodeURIComponent(id)}/events?after=0&limit=200`),
  createSimulation: (runId: string) =>
    mutationRequest<SimulationWorld>("/simulations", { run_id: runId }),
  advanceSimulation: (id: string, revision: number, days: 1 | 7) =>
    mutationRequest<SimulationWorld>(
      `/simulations/${encodeURIComponent(id)}/advance`,
      { revision, days },
    ),
  replanSimulation: (id: string, revision: number) =>
    mutationRequest<SimulationWorld>(
      `/simulations/${encodeURIComponent(id)}/replan`,
      { revision },
    ),
};
