import type { Run, Strategy, StrategyMetrics } from './types'

export type AdvisorId = 'ravi' | 'hana' | 'idris' | 'mei' | 'lina' | 'ben' | 'asha'

export interface Advisor {
  id: AdvisorId
  name: string
  role: string
  location: string
  focus: string
  prompt: string
  color: string
  roleId: string
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
  fact_refs?: string[]
  rendered_facts?: RenderedFact[]
  highlight_refs?: string[]
  validation_status?: string
  validation_scope?: string
  interpretation_status?: string
  evidence_status?: string
  relationship?: string
  request_mode?: string
  planner_conclusion?: boolean
  critic_conclusion?: boolean
  proposed_actions?: ProposedAction[]
  replay?: boolean
  [key: string]: unknown
}

export interface RenderedFact {
  reference: string
  kind?: string
  value: unknown
  unit?: string | null
  entity?: { type?: string; id?: string } | null
  period?: { kind?: string; value?: string } | null
  context?: string | null
  snapshot_hash?: string | null
  verification?: string | null
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
  advisor_role?: string | null
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
  last_request_error?: string | null
  tool_results?: Record<string, unknown>
  typed_facts?: Record<string, RenderedFact>
  evidence_context?: Array<{ evidence_id?: string; title?: string; finding?: string; scope?: string; limit?: string; source_url?: string; access_review_status?: string }>
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
  run_key?: string
  attempts?: Array<{ number?: number; status?: string; queued_at?: string; started_at?: string; completed_at?: string; failed_at?: string; cancelled_at?: string; error?: string; [key: string]: unknown }>
  attempt_count?: number
  max_attempts?: number
  cancellation_requested?: boolean
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
  { id: 'ravi', name: 'Ravi', role: 'Demand', roleId: 'demand_analyst', location: 'Orders desk', focus: 'Booked demand, shortages and buyer commitments in kg', prompt: 'Which delivery is most exposed?', color: '#4f8d8c' },
  { id: 'hana', name: 'Hana', role: 'Weather', roleId: 'weather_analyst', location: 'Weather station', focus: 'Public conditions, source time and uncertainty', prompt: 'What conditions should we watch?', color: '#4b80a3' },
  { id: 'idris', name: 'Idris', role: 'Market', roleId: 'market_analyst', location: 'Market stall', focus: 'Market evidence and explicitly connected community signals', prompt: 'What market evidence is available?', color: '#667457' },
  { id: 'mei', name: 'Mei', role: 'Production', roleId: 'production_analyst', location: 'Greenhouse', focus: 'Crop development, yield in kg and biological timing', prompt: 'Why is this bed delayed?', color: '#d98164' },
  { id: 'lina', name: 'Lina', role: 'Supply Chain', roleId: 'supply_chain_analyst', location: 'Packing shed', focus: 'Inventory, harvest arrivals and delivery timing in kg', prompt: 'Where could supply miss delivery?', color: '#c77b54' },
  { id: 'ben', name: 'Ben', role: 'Profit', roleId: 'profit_analyst', location: 'Accounts desk', focus: 'Cash, cost and contribution margin in SGD', prompt: 'What drives the margin?', color: '#b07746' },
  { id: 'asha', name: 'Asha', role: 'Planner', roleId: 'planning_chair', location: 'Council pavilion', focus: 'Validated alternatives, constraints and final synthesis', prompt: 'Compare our best alternatives.', color: '#8a6ea8' },
]

export const QUEST_FALLBACKS: Quest[] = [
  { id: 'late_harvest', title: 'Late harvest', description: 'Delay a selected batch and test its expected yield.', advisor_id: 'mei', status: 'available' },
  { id: 'busy_market', title: 'Busy market', description: 'Change demand for a crop with existing commitments.', advisor_id: 'ravi', status: 'available' },
  { id: 'short_handed_week', title: 'Short-handed week', description: 'Explore what happens when labour changes.', advisor_id: 'ben', status: 'available' },
  { id: 'tight_budget', title: 'Tight budget', description: 'Vary available cash and inspect the trade-offs.', advisor_id: 'asha', status: 'available' },
]

export type SimulationSoundOutcome = 'complete' | 'shortfall' | 'withheld' | 'error'

export function runSoundOutcome(run: Run): SimulationSoundOutcome {
  const status=run.status.toLowerCase()
  if(['failed','cancelled','stale_input'].includes(status))return 'error'
  if(['review_withheld','no_feasible_plan'].includes(status))return 'withheld'
  if(!['completed','accepted_for_simulation'].includes(status))return 'error'
  const strategy=run.strategies.find(item=>item.id===run.accepted_strategy_id)||run.strategies.find(item=>item.name==='Balanced')||run.strategies[0]
  if(Number(strategy?.metrics.shortfall_kg||0)>0)return 'shortfall'
  return 'complete'
}

export function scenarioSoundOutcome(scenario: Scenario): SimulationSoundOutcome {
  if(scenario.status.toLowerCase()!=='completed')return 'error'
  if(String(scenario.simulation_status||'').toLowerCase()==='no_feasible_plan')return 'withheld'
  const strategies=scenario.result?.strategies||[]
  const selected=strategies.find(item=>item.id===scenario.accepted_strategy_id)||strategies.find(item=>item.name==='Balanced')||strategies[0]
  if(Number(selected?.metrics.shortfall_kg||0)>0)return 'shortfall'
  return 'complete'
}
