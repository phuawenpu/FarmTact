import type { Strategy, StrategyMetrics } from './types'

export type AdvisorId = 'mei' | 'ravi' | 'hana' | 'ben' | 'asha' | 'idris'

export interface Advisor {
  id: AdvisorId
  name: string
  role: string
  location: string
  focus: string
  prompt: string
  color: string
}

export interface ConversationMessage {
  id: string
  conversation_id: string
  speaker: string
  content: string
  created_at: string
  reply_to_message_id?: string | null
  reply_to?: string | null
  speaker_id?: string | null
  speaker_name?: string | null
  snapshot_ref?: string | null
  evidence_refs?: string[]
  tool_refs?: string[]
  highlight_refs?: string[]
  validation_status?: string
  validation_scope?: string
  interpretation_status?: string
  relationship?: string
  request_mode?: string
  proposed_actions?: ProposedAction[]
  replay?: boolean
  [key: string]: unknown
}

export interface ProposedAction {
  control: 'delay_days' | 'yield_percent' | 'demand_percent' | 'labour_percent' | 'cash_percent'
  target_id?: string
  value: number
  unit: 'days' | 'percent'
  status: 'hypothesis_only' | 'blocked_unsupported'
}

export interface Conversation {
  id: string
  title?: string
  advisor_ids?: string[]
  advisor_id?: string
  farm_id?: string
  scenario_id?: string | null
  snapshot_ref?: string | { kind?: string; id?: string; hash?: string; version?: string | number; frozen_at?: string } | null
  status?: string
  replay?: boolean
  transcript_mode?: string
  execution_mode?: string
  inference_origin?: string
  messages: ConversationMessage[]
  created_at?: string
  updated_at?: string
  selected_bed_id?: string | null
  last_request_id?: string | null
  last_request_status?: string | null
  [key: string]: unknown
}

export interface ScenarioControls {
  batch_id?: string
  delay_days: number
  yield_percent: number
  demand_crop_id?: string
  demand_percent: number
  labour_percent: number
  cash_percent: number
}

export interface ScenarioComputed {
  strategies?: Strategy[]
  accepted_strategy_id?: string
  metrics?: StrategyMetrics | Record<string, number>
  status?: string
  violations?: unknown[]
  [key: string]: unknown
}

export interface Scenario {
  id: string
  name: string
  parent_scenario_id?: string | null
  quest_id?: string | null
  controls: ScenarioControls
  status: string
  snapshot_ref?: string
  input_hash?: string
  baseline_hash?: string
  source_conversation_id?: string | null
  frozen_snapshot?: Record<string, unknown>
  baseline?: ScenarioComputed
  result?: ScenarioComputed
  affected_bed_ids?: string[]
  affected_deliveries?: Array<{ crop_id?: string; due_date?: string; order_id?: string }>
  simulation_status?: string
  policy_comparisons?: PolicyComparison[]
  warnings?: string[]
  created_at?: string
  updated_at?: string
  [key: string]: unknown
}

export interface PolicyComparison {
  policy: string
  baseline_strategy_id: string
  scenario_strategy_id: string
  baseline_status: string
  scenario_status: string
  baseline_metrics: StrategyMetrics
  scenario_metrics: StrategyMetrics
  deltas: Partial<StrategyMetrics>
  violations: unknown[]
}

export interface ScenarioComparison {
  baseline: ScenarioComputed
  scenarios: Scenario[]
}

export interface Quest {
  id: string
  title: string
  name?: string
  description: string
  advisor_id?: AdvisorId
  status?: string
  badge?: string | null
  completed_scenario_ids?: string[]
  inspected_scenario_ids?: string[]
  inspected_ids?: string[]
  experiment_ids?: string[]
  badges?: string[]
  [key: string]: unknown
}

export const ADVISORS: Advisor[] = [
  { id: 'mei', name: 'Mei', role: 'Crop scientist', location: 'Greenhouse', focus: 'Crop development and biological constraints', prompt: 'Why is this bed delayed?', color: '#d98164' },
  { id: 'ravi', name: 'Ravi', role: 'Demand analyst', location: 'Market stall', focus: 'Orders, shortages and buyer commitments', prompt: 'Which delivery is most exposed?', color: '#4f8d8c' },
  { id: 'hana', name: 'Hana', role: 'Weather scout', location: 'Weather station', focus: 'Public conditions and uncertainty', prompt: 'What conditions should we watch?', color: '#4b80a3' },
  { id: 'ben', name: 'Ben', role: 'Resource analyst', location: 'Tool shed', focus: 'Labour, cash, capacity and margin', prompt: 'Where is the tightest resource?', color: '#b07746' },
  { id: 'asha', name: 'Asha', role: 'Planning chair', location: 'Council pavilion', focus: 'Alternatives and trade-offs', prompt: 'Compare our best alternatives.', color: '#8a6ea8' },
  { id: 'idris', name: 'Idris', role: 'Independent critic', location: 'Evidence desk', focus: 'Challenging unsupported conclusions', prompt: 'Show me the evidence.', color: '#667457' },
]

export const QUEST_FALLBACKS: Quest[] = [
  { id: 'late_harvest', title: 'Late harvest', description: 'Delay a selected batch and test its expected yield.', advisor_id: 'mei', status: 'available' },
  { id: 'busy_market', title: 'Busy market', description: 'Change demand for a crop with existing commitments.', advisor_id: 'ravi', status: 'available' },
  { id: 'short_handed_week', title: 'Short-handed week', description: 'Explore what happens when labour changes.', advisor_id: 'ben', status: 'available' },
  { id: 'tight_budget', title: 'Tight budget', description: 'Vary available cash and inspect the trade-offs.', advisor_id: 'asha', status: 'available' },
]
