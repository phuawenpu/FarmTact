/** Presentation references never grant authority to mutate a domain entity. */
export type ToolDeck = 'plan' | 'records' | 'knowledge' | 'experiments' | 'history'
export interface CardBinding {
  sessionId: string | null
  inputHash: string | null
  revision: number | null
  resultId: string | null
  snapshotId?: string | null
}
export interface CardAction {
  id: string
  label: string
  eligible: boolean
  authority: 'local_navigation' | 'server_mutation'
  eligibilitySource: 'local' | 'server'
  disabledReason?: string
}
export interface FarmCard {
  id: string
  entityId: string
  entityKind: string
  title: string
  provenance: string[]
  binding: CardBinding
  boardTargets: string[]
  actions: CardAction[]
  outcomeBasis: 'projection' | 'recorded_simulation' | 'farmer_reported' | null
}
export interface SceneTransition {
  event_id: string
  entity_ids: string[]
  effective_date: string | null
  before: Record<string, unknown>
  after: Record<string, unknown>
  fact_differences: Record<string, number | string | null>
  outcome_basis: 'projection' | 'recorded_simulation'
  inference_triggered?: false
}
export interface StoredExplanation {
  version: 'integrated-explanation-v1'
  outcome_basis: 'projection'
  what_changed: Array<Record<string, unknown>>
  why: string
  tradeoff: Record<string, number | null>
  evidence: {
    before_result_id?: string
    after_result_id?: string
    before_strategy_id?: string
    after_strategy_id?: string
  }
  affected_bed_ids: string[]
  allocation_changes: Array<{
    id: string
    before: Record<string, unknown> | null
    after: Record<string, unknown> | null
  }>
  next_action: string
  inference_triggered: false
}
