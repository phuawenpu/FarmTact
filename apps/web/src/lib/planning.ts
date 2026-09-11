import type { Farm, Strategy } from './types'
import type { SimulationWorld } from './api'
import { mutationRequest, request } from './api'
import { editionStorageKey } from './edition'

export type PlanningStage = 'records' | 'planning' | 'review' | 'simulation' | 'comparison'
export type PlanningJobStatus = 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'

export interface FutureDemandAssumption { crop_id: string; start_date: string; end_date: string; percent: number }
export interface SeasonalAssumption { crop_id: string; system: 'sheltered_hydroponic'; start_date: string; end_date: string; yield_percent: number; delay_days: number; reason: string; provenance: 'synthetic_assumption' }
export interface OrderChange { operation: 'add' | 'amend' | 'cancel'; order_id: string; crop_id?: string; due_date?: string; quantity_kg?: number; price_sgd_per_kg?: number }
export interface PlanningAssumptions { future_demand: FutureDemandAssumption[]; seasonal: SeasonalAssumption[]; order_changes: OrderChange[] }
export interface PlanningJob { id: string; kind: string; status: PlanningJobStatus; stage: string; error?: string | null }
export interface PlanningReview { status: string; findings?: Array<Record<string, unknown>>; [key: string]: unknown }
export interface AllocationChange { operation?: string; change?: string; bed_id?: string; crop_id?: string; before?: Record<string, unknown> | null; after?: Record<string, unknown> | null; [key: string]: unknown }
export interface PlanningResult {
  strategies?: Strategy[]
  forecast?: Record<string, unknown> | null
  retained_strategy?: Strategy | Record<string, unknown> | null
  comparisons?: Array<Record<string, unknown>> | Record<string, Record<string, unknown>>
  allocation_changes?: AllocationChange[]
  [key: string]: unknown
}
export interface PlanningSession {
  id: string; revision: number; created_at: string; updated_at: string; status: string; stage: PlanningStage
  farm: Farm; input_hash: string; result?: PlanningResult | null; selected_strategy_id?: string | null
  review?: PlanningReview | null; assumptions?: PlanningAssumptions | null; simulation?: SimulationWorld | null
  job?: PlanningJob | null; history?: Array<Record<string, unknown>>; data_mode: 'synthetic_demo'; [key: string]: unknown
}

const key = editionStorageKey('planning-session')
export function rememberedPlanningSession() { try { return localStorage.getItem(key) } catch { return null } }
export function rememberPlanningSession(id: string) { try { localStorage.setItem(key, id) } catch { /* persistence is optional */ } }

export const planningApi = {
  list: () => request<{ sessions: PlanningSession[] }>('/planning-sessions'),
  create: () => mutationRequest<PlanningSession>('/planning-sessions', {}),
  get: (id: string) => request<PlanningSession>(`/planning-sessions/${encodeURIComponent(id)}`),
  calculate: (id: string, revision: number) => mutationRequest<PlanningSession>(`/planning-sessions/${encodeURIComponent(id)}/calculate`, { revision }),
  review: (id: string, revision: number) => mutationRequest<PlanningSession>(`/planning-sessions/${encodeURIComponent(id)}/review`, { revision }),
  disrupt: (id: string, revision: number, assumptions: PlanningAssumptions) => mutationRequest<PlanningSession>(`/planning-sessions/${encodeURIComponent(id)}/disrupt`, { revision, assumptions }),
  advance: (id: string, revision: number, days: 1 | 7) => mutationRequest<PlanningSession>(`/planning-sessions/${encodeURIComponent(id)}/advance`, { revision, days }),
  cancel: (id: string, revision: number) => mutationRequest<PlanningSession>(`/planning-sessions/${encodeURIComponent(id)}/cancel`, { revision }),
}
