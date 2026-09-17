import type { CardAction, FarmCard } from './cards'

export const cardString = (value: unknown): string | null => typeof value === 'string' && value.length ? value : null
export const cardRevision = (value: unknown): number | null => typeof value === 'number' && Number.isInteger(value) ? value : null
export const cardRecord = (value: unknown): Record<string, unknown> => value && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {}
/** Preserve supplied source references; an absent source stays absent. */
export function cardReferences(...values: unknown[]): string[] {
  return values.flatMap(value => value == null ? [] : Array.isArray(value) ? cardReferences(...value)
    : typeof value === 'string' ? [value] : typeof value === 'object' ? [JSON.stringify(value)] : [])
}
export function toolCardActions(primary: { label: string; disabled?: boolean } | undefined, secondary: { label: string; disabled?: boolean } | undefined, busy: boolean, mutationLabels: string[]): CardAction[] {
  return [{ id: 'back', label: 'Back', eligible: true, authority: 'local_navigation', eligibilitySource: 'local' },
    ...[primary, secondary].flatMap((action, index): CardAction[] => action ? [{ id: index === 0 ? 'primary' : 'secondary', label: action.label,
      eligible: !busy && !action.disabled, authority: mutationLabels.includes(action.label) ? 'server_mutation' : 'local_navigation',
      eligibilitySource: 'local', ...((busy || action.disabled) ? { disabledReason: busy ? 'Waiting for server confirmation.' : 'The current card prerequisites are not met.' } : {}) }] : [])]
}
export function staticToolCard(deck: string, view: string, title: string): FarmCard {
  const id = `${deck}:${view}`
  return { id, entityId: id, entityKind: 'tool', title, provenance: [],
    binding: { sessionId: null, inputHash: null, revision: null, resultId: null },
    boardTargets: [], actions: [], outcomeBasis: null }
}
