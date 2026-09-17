/** Presentation references never grant authority to mutate a domain entity. */
export type ToolDeck = 'plan' | 'records' | 'knowledge' | 'experiments' | 'history'
export interface CardBinding {
  sessionId: string
  inputHash: string
  revision: number
  resultId: string | null
}
export interface CardAction {
  id: string
  label: string
  eligible: boolean
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
  outcomeBasis: 'projection' | 'recorded_simulation' | 'farmer_reported'
}
export interface SceneTransition {
  eventId: string
  entityIds: string[]
  effectiveDate: string
  before: Record<string, unknown>
  after: Record<string, unknown>
  factDifferences: Record<string, number | string | null>
}
