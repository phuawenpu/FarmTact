import type { Bootstrap, Crop, EvidenceRecord, Run } from './types'
import type { Conversation, Quest, Scenario, ScenarioComparison, ScenarioControls } from './game'
import type { ExplorerDetail, ExplorerSnapshotSummary, ForecastSettings, GeneratorSettings, PublicContext } from './explorer'
import { editionPath } from './edition'

const API = () => editionPath('/api/v1')

export class ApiError extends Error {
  status: number
  detail?: string
  constructor(message: string, status: number, detail?: string) {
    super(message)
    this.status = status
    this.detail = detail
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API()}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...init?.headers,
    },
  })
  if (!response.ok) {
    let detail: string | undefined
    try {
      const payload = (await response.json()) as { detail?: unknown }
      if (typeof payload.detail === 'string') detail = payload.detail
      else if (Array.isArray(payload.detail)) detail = payload.detail.map(item => {
        if (!item || typeof item !== 'object') return 'Check the entered assumptions.'
        const issue = item as { loc?: unknown[]; msg?: unknown }
        const field = (issue.loc || []).filter(part => part !== 'body').join(' · ').replaceAll('_', ' ')
        return `${field ? `${field}: ` : ''}${typeof issue.msg === 'string' ? issue.msg : 'Check this value.'}`
      }).join(' ')
    } catch {
      detail = undefined
    }
    throw new ApiError(detail || `Request failed (${response.status})`, response.status, detail)
  }
  return response.json() as Promise<T>
}

export const api = {
  bootstrap: () => request<Bootstrap>('/bootstrap'),
  crop: async (id: string) => {
    const response = await request<{ crop: Crop; evidence: EvidenceRecord[] }>(`/crops/${encodeURIComponent(id)}/evidence`)
    return { ...response.crop, evidence: response.evidence }
  },
  importSeed: () => request<{ id: string; status: string; version: number }>('/imports', { method: 'POST', body: JSON.stringify({ fixture: 'synthetic_demo' }) }),
  importFarm: (farm: unknown) => request<{ id: string; status: string; version: number }>('/imports', { method: 'POST', body: JSON.stringify({ farm }) }),
  createRun: (council = true) => request<{ id: string; status: string }>('/planning-runs', {
    method: 'POST',
    headers: { 'Idempotency-Key': crypto.randomUUID() },
    body: JSON.stringify({ council }),
  }),
  run: (id: string) => request<Run>(`/planning-runs/${encodeURIComponent(id)}`),
  replan: (id: string) => request<{ id: string; status: string } | Run>(`/planning-runs/${encodeURIComponent(id)}/replan`, {
    method: 'POST',
    headers: { 'Idempotency-Key': crypto.randomUUID() },
    body: JSON.stringify({ disruption: 'crop_delay' }),
  }),
  replay: (id: string) => request<Run>(`/planning-runs/${encodeURIComponent(id)}/replay`),
  demoReplay: () => request<Run>('/demo/replay'),
  eventsUrl: (id: string) => `${API()}/planning-runs/${encodeURIComponent(id)}/events`,
  conversations: async () => (await request<{ conversations: Conversation[] }>('/conversations')).conversations,
  conversation: (id: string) => request<Conversation>(`/conversations/${encodeURIComponent(id)}`),
  conversationReplay: (id: string) => request<Conversation>(`/conversations/${encodeURIComponent(id)}/replay`),
  createConversation: (body: { advisor: string; snapshot_kind: 'farm' | 'scenario'; snapshot_id?: string; selected_bed_id?: string }) => request<{ id: string; status: string; reused?: boolean }>('/conversations', {
    method: 'POST',
    headers: { 'Idempotency-Key': crypto.randomUUID() },
    body: JSON.stringify(body),
  }),
  sendConversationMessage: (id: string, body: { content: string; reply_to?: string }) => request<{ id: string; conversation_id: string; status: string; message_id?: string }>(`/conversations/${encodeURIComponent(id)}/messages`, {
    method: 'POST', headers: { 'Idempotency-Key': crypto.randomUUID() }, body: JSON.stringify(body),
  }),
  inviteAdvisor: (id: string, body: { advisor: string; question: string; reply_to: string }) => request<{ id: string; conversation_id: string; status: string }>(`/conversations/${encodeURIComponent(id)}/invite`, {
    method: 'POST', headers: { 'Idempotency-Key': crypto.randomUUID() }, body: JSON.stringify(body),
  }),
  conveneCouncil: (id: string, body: { question: string; reply_to?: string }) => request<{ id: string; conversation_id: string; status: string }>(`/conversations/${encodeURIComponent(id)}/council`, {
    method: 'POST', headers: { 'Idempotency-Key': crypto.randomUUID() }, body: JSON.stringify(body),
  }),
  scenarios: async () => (await request<{ scenarios: Scenario[] }>('/scenarios')).scenarios,
  scenario: (id: string) => request<Scenario>(`/scenarios/${encodeURIComponent(id)}`),
  createScenario: (body: { name: string; parent_scenario_id?: string; source_conversation_id?: string; explorer_snapshot_id?: string; controls: ScenarioControls; quest_id?: string }) => request<Scenario>('/scenarios', {
    method: 'POST',
    headers: { 'Idempotency-Key': crypto.randomUUID() },
    body: JSON.stringify(body),
  }),
  runScenario: (id: string) => request<Scenario>(`/scenarios/${encodeURIComponent(id)}/run`, {
    method: 'POST',
    headers: { 'Idempotency-Key': crypto.randomUUID() },
    body: JSON.stringify({}),
  }),
  compareScenarios: (ids: string[]) => request<ScenarioComparison>(`/scenarios/compare?ids=${encodeURIComponent(ids.join(','))}`),
  quests: async () => (await request<{ quests: Quest[] }>('/quests')).quests,
  inspectQuest: (questId: string, scenarioId: string) => request<Quest>(`/quests/${encodeURIComponent(questId)}/inspect`, {
    method: 'POST', body: JSON.stringify({ scenario_id: scenarioId }),
  }),
  explorerSnapshots: async () => (await request<{ snapshots: ExplorerSnapshotSummary[] }>('/data-explorer/snapshots')).snapshots,
  explorerSnapshot: (id: string, policy = 'Balanced') => request<ExplorerDetail>(`/data-explorer/snapshots/${encodeURIComponent(id)}?policy=${encodeURIComponent(policy)}`),
  explorerEvaluation: () => request<Record<string, unknown>>('/data-explorer/evaluation'),
  explorerPreview: (generator_settings: GeneratorSettings, forecast_settings: ForecastSettings, signal?: AbortSignal) => request<ExplorerDetail>('/data-explorer/preview', { method: 'POST', signal, body: JSON.stringify({ generator_settings, forecast_settings }) }),
  saveExplorerSnapshot: (name: string, generator_settings: GeneratorSettings, forecast_settings: ForecastSettings) => request<ExplorerDetail>('/data-explorer/snapshots', { method: 'POST', headers: { 'Idempotency-Key': crypto.randomUUID() }, body: JSON.stringify({ name, generator_settings, forecast_settings }) }),
  explorerPublic: () => request<PublicContext>('/data-explorer/public'),
  explorerExportUrl: (params: URLSearchParams) => `${API()}/data-explorer/export?${params.toString()}`,
}
