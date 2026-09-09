import type { Farm, Strategy } from './types'

export type ExplorerTab = 'overview' | 'generator' | 'records' | 'public' | 'experiments'
export type DatasetKey = 'beds' | 'recipes' | 'batches' | 'history' | 'orders' | 'inventory' | 'resources' | 'forecast' | 'allocations' | 'ledger' | 'weekly'
export type Policy = 'Lean' | 'Balanced' | 'Resilient'
export interface GeneratorSettings { history_multiplier: number; history_trend: number; pattern_amplitude: number; orders_multiplier: number; price_multiplier: number }
export interface ForecastSettings { alpha: number }
export interface ExplorerSnapshotSummary { id: string; name: string; kind: string; cutoff: string; content_hash: string; scenario_id?: string; status?: string }
export interface ExplorerField { key: string; label: string; unit?: string | null; description?: string }
export type ExplorerRecord = { id: string; crop_id?: string; date?: string; [key: string]: unknown }
export interface ExplorerDetail {
  id: string; name: string; kind: string; cutoff: string; planning_date: string
  date_extent: { start: string; end: string }; content_hash: string; generator_version: string
  generator_settings: GeneratorSettings | null; forecast_settings: ForecastSettings; forecast_version: string
  provenance: Record<string, unknown>; counts: Record<string, number>; farm: Farm
  records: Record<DatasetKey, ExplorerRecord[]>; fields: Record<DatasetKey, ExplorerField[]>
  forecast: Record<string, unknown>; result: { strategies?: Strategy[]; status?: string; violations?: unknown[]; [key: string]: unknown } | null
  scenario_id?: string; unsaved: boolean
}
export interface PublicSource { id: string; name: string; url?: string; status: string; coverage?: unknown; observed_at?: string; retrieved_at?: string; freshness?: string; quality?: string; licence_state?: string; reuse_restrictions?: string; record_count: number }
export interface PublicRow extends ExplorerRecord { source_id: string; date: string; value: number; unit: string; metric: string; station?: string }
export interface PublicContext { sources: PublicSource[]; datasets: { weather_observations: PublicRow[]; weather_forecasts: PublicRow[]; trade_observations: PublicRow[] } }
export const DEFAULT_GENERATOR: GeneratorSettings = { history_multiplier: 1, history_trend: 0, pattern_amplitude: 1, orders_multiplier: 1, price_multiplier: 1 }
export const DEFAULT_FORECAST: ForecastSettings = { alpha: .35 }
