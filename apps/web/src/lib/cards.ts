/** Presentation references never grant authority to mutate a domain entity. */
export type ToolDeck = 'plan' | 'records' | 'knowledge' | 'experiments' | 'history'
/** Read-only navigation hints; domain APIs still validate every saved focus. */
export type KnowledgeTarget = {kind:'crop'|'source'|'advisor';id:string} | {kind:'threads'|'council'|'index'|'crops'|'sources'|'advisers'}
export type ExperimentTarget = 'index'|'scenarios'|'explorer'|'generator'|'rescue'|'research'
export type ResearchTarget = 'overview'|'context'|'discussion'|'proposal'|'calculate'|'challenge'|'results'|'history'|'actual'|'report'
export type HistoryTarget = 'plans'|'discussions'|'simulations'|'events'|'preferences'|'help'
export type PlanTarget = 'objectives'|'strategies'|'assumptions'|'proposals'|'new'
export type RecordsTarget = {view:'setup'|'imports'|'orders'|'beds'|'inventory'|'proposals'|'tasks'|'verify'|'history';entityId?:string}
export interface ToolTarget {
  plan?: PlanTarget
  records?: RecordsTarget
  knowledge?: KnowledgeTarget
  experiments?: ExperimentTarget
  research?: ResearchTarget
  history?: HistoryTarget
}
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
/** A Council review is advisory, frozen to a calculated planning result, and never grants approval authority. */
export interface CouncilReviewBinding {
  sessionId: string
  revision: number
  resultId: string | null
  status: string
  findingCount: number
  providerSubmissionRequired: boolean
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
  council?: CouncilReviewBinding | null
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
