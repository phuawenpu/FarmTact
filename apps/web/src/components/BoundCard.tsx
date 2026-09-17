import { forwardRef, type HTMLAttributes, type ReactNode } from 'react'
import type { FarmCard } from '../lib/cards'

type Props = Omit<HTMLAttributes<HTMLElement>, 'title'> & {
  card: FarmCard
  children: ReactNode
}

/** Publishes a card's authority and frozen binding without adding controls or navigation. */
const BoundCard = forwardRef<HTMLElement, Props>(function BoundCard({ card, children, ...props }, ref) {
  const binding = card.binding
  return <article ref={ref}
    {...props}
    data-card-id={card.id}
    data-entity-id={card.entityId}
    data-entity-kind={card.entityKind}
    data-session-id={binding.sessionId ?? undefined}
    data-input-hash={binding.inputHash ?? undefined}
    data-session-revision={binding.revision ?? undefined}
    data-result-id={binding.resultId ?? undefined}
    data-snapshot-id={binding.snapshotId ?? undefined}
    data-provenance={JSON.stringify(card.provenance)}
    data-board-targets={JSON.stringify(card.boardTargets)}
    data-outcome-basis={card.outcomeBasis ?? undefined}
    data-card-actions={JSON.stringify(card.actions)}
    data-action-authority={JSON.stringify(Object.fromEntries(card.actions.map((action) => [action.id, action.authority])))}
    data-action-eligibility={JSON.stringify(Object.fromEntries(card.actions.map((action) => [action.id, { eligible: action.eligible, source: action.eligibilitySource, reason: action.disabledReason ?? null }] )))}
  >{children}</article>
})

export default BoundCard
