import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import BeginnerGame from './BeginnerGame'
import { api, ApiError } from '../lib/api'
import { beginnerApi } from '../lib/beginnerApi'
import { defaultBeginnerUtilities, readBeginnerProgress, writeBeginnerProgress,
  type BeginnerCard, type BeginnerJourney, type BeginnerUtilityCard } from '../lib/beginner'
import type { Conversation } from '../lib/game'

// StrictMode can mount twice. Share only the in-flight bootstrap so a first visit
// cannot mint concurrent anonymous sessions with competing cookies.
let bootstrapPending: Promise<unknown> | null = null
function bootstrap() {
  if (!bootstrapPending) bootstrapPending = api.bootstrap().finally(() => { bootstrapPending = null })
  return bootstrapPending
}

function remember(journey: BeginnerJourney) {
  writeBeginnerProgress({ ...readBeginnerProgress(), introSeen: true,
    serverSeasonId: journey.id, serverRevision: journey.revision })
}

function message(error: unknown) {
  if (error instanceof ApiError && error.status === 409)
    return 'Your season changed in another action. The latest decision has been restored; please choose again.'
  return error instanceof Error ? error.message : 'The connection was interrupted. Your saved season is safe. Try again.'
}

const pending = (journey: BeginnerJourney | null) =>
  ['QUEUED', 'RUNNING'].includes(journey?.planning_session?.status || '')

type FarmRecords = {
  farm?: { name?: string; beds?: Array<{ name: string; area_m2: string | number }>;
    orders?: Array<{ crop_id: string; quantity_kg: string | number; due_date: string }>;
    recipes?: Array<{ crop_id: string; nursery_days: number; grow_days: number }> }
}

export default function BeginnerApp({ landing }: { landing: boolean }) {
  const [journey, setJourney] = useState<BeginnerJourney | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [conversation, setConversation] = useState<Conversation | null>(null)
  const [adviserNote, setAdviserNote] = useState('Ask Asha about your current decision. Asking is optional; you can finish the season without it.')
  const lock = useRef(false)
  const initialized = useRef(false)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      await bootstrap()
      const page = await beginnerApi.list()
      const remembered = readBeginnerProgress().serverSeasonId
      const current = page.journeys.find(item => item.id === remembered) || page.journeys[0] || null
      setJourney(current)
      if (current) remember(current)
      else writeBeginnerProgress({ introSeen: false })
      initialized.current = true
      setError(null)
      return current
    } catch (caught) { setError(message(caught)); return null }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { void load() }, [load])

  useEffect(() => {
    if (!journey || !pending(journey)) return
    const id = journey.id
    let cancelled = false
    let timer: ReturnType<typeof setTimeout>
    const poll = async () => {
      try {
        const next = await beginnerApi.get(id)
        if (!cancelled) {
          setJourney(current => current?.id === id ? next : current)
          remember(next)
          setError(null)
        }
      } catch (caught) { if (!cancelled) setError(message(caught)) }
      if (!cancelled) timer = setTimeout(poll, 2000)
    }
    timer = setTimeout(poll, 1000)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [journey?.id, journey?.planning_session?.status])

  useEffect(() => {
    if (!conversation || !['QUEUED', 'RUNNING'].includes(conversation.last_request_status || '')) return
    let cancelled = false
    const timer = setInterval(() => {
      void api.conversation(conversation.id).then(next => {
        if (!cancelled) setConversation(next)
      }).catch(caught => { if (!cancelled) setAdviserNote(message(caught)) })
    }, 2000)
    return () => { cancelled = true; clearInterval(timer) }
  }, [conversation?.id, conversation?.last_request_status])

  useEffect(() => {
    if (!conversation) return
    if (conversation.last_request_error) {
      setAdviserNote(`Asha cannot reply right now. ${conversation.last_request_error} Your season can continue.`)
      return
    }
    const replies = conversation.messages.filter(item => item.speaker === 'advisor')
    const latest = replies[replies.length - 1]
    if (latest) setAdviserNote(latest.validation_status === 'references_verified'
      ? latest.content
      : 'The adviser response could not be verified. Use Explain to review the recorded facts and continue your season.')
    else setAdviserNote('Your question is with Asha. You can continue your season while waiting.')
  }, [conversation])

  const perform = useCallback(async (actionId: string, optionId?: string) => {
    if (!journey || lock.current) return
    lock.current = true; setBusy(true); setError(null)
    try {
      const next = await beginnerApi.action(journey, actionId, optionId)
      setJourney(next); remember(next)
      if (next.id !== journey.id) { setConversation(null); setAdviserNote('Ask Asha about the new season after calculating your plans.') }
    } catch (caught) {
      setError(message(caught))
      if (caught instanceof ApiError && caught.status === 409) {
        const next = await beginnerApi.get(journey.id).catch(() => null)
        if (next) { setJourney(next); remember(next) }
      }
    } finally { lock.current = false; setBusy(false) }
  }, [journey])

  const start = async () => {
    if (lock.current) return
    lock.current = true; setBusy(true); setError(null)
    try {
      if (!initialized.current) {
        await load()
        if (!initialized.current) return
      }
      const next = journey || await beginnerApi.create()
      remember(next); setJourney(next)
      window.location.assign('/play')
    } catch (caught) { setError(message(caught)) }
    finally { lock.current = false; setBusy(false) }
  }

  const ask = async (question: string, card: BeginnerCard) => {
    if (!journey?.planning_session || pending(journey) || lock.current) return
    lock.current = true; setBusy(true)
    try {
      const prefixes: Record<string, string> = { strategy: 'strategy-', order: 'order-', bed: 'constraint-', grow_space: 'constraint-', crop: 'crop-', batch: 'crop-batch-' }
      const entity = card.entity
      const focused = entity && prefixes[entity.kind]
        ? { card_id: `${prefixes[entity.kind]}${entity.id}`, entity_kind: entity.kind, entity_id: entity.id }
        : { card_id: 'agent-asha', entity_kind: 'agent', entity_id: 'asha' }
      const created = await api.createConversation({ advisor: 'asha', snapshot_kind: 'planning',
        snapshot_id: journey.planning_session.id, focus: focused })
      await api.sendConversationMessage(created.id, { content: question })
      setConversation(await api.conversation(created.id))
      setAdviserNote('Your question is with Asha. You can continue your season while waiting.')
    } catch (caught) { setAdviserNote(`Asha cannot reply right now. ${message(caught)} Your season can continue.`) }
    finally { lock.current = false; setBusy(false) }
  }

  const utilities = useMemo(() => {
    const farm = (journey as (BeginnerJourney & FarmRecords) | null)?.farm
    const rows = defaultBeginnerUtilities.map((item): BeginnerUtilityCard => {
      if (item.kind === 'next_step') return { ...item, summary: journey?.next_action
        ? `Your next move: ${journey.next_action.label}. Return to the season to see the decision and its explanation.` : 'Return to your season for the current objective.' }
      if (item.kind === 'journal') return { ...item, summary: journey?.timeline?.length
        ? journey.timeline.slice(-4).map(row => `${row.date || ''} ${row.summary || row.title || row.type || row.action || 'Saved farm event'}`.trim()).join('\n')
        : 'Your season has just begun. Confirmed choices and simulated farm events will appear here.', primaryAction: { id: 'return-to-season', kind: 'continue', label: 'Back to season' } }
      if (item.kind === 'records') return { ...item, summary: farm?.orders?.length
        ? `Teaching records · simulated farm. ${farm.orders.map(order => `${order.quantity_kg} kg of ${order.crop_id.replaceAll('_', ' ')} due ${order.due_date}`).join('. ')}. ${farm.beds?.length || 4} growing beds. These records belong only to this lesson.`
        : 'This lesson uses a separate, fictional four-bed farm. Your other farm records remain unchanged. Order quantities and dates are shown on the season cards.', primaryAction: { id: 'return-to-season', kind: 'continue', label: 'Back to season' } }
      if (item.kind === 'crops') return { ...item, summary: farm?.recipes?.length
        ? farm.recipes.map(recipe => `${recipe.crop_id.replaceAll('_', ' ')}: ${recipe.nursery_days} days in the nursery, then ${recipe.grow_days} days in a bed. This is a teaching recipe, not a prediction for a real farm.`).join('\n')
        : 'Growing takes time. The saved crop recipe determines nursery and growing days; clicking faster cannot make vegetables mature sooner.', primaryAction: { id: 'return-to-season', kind: 'continue', label: 'Back to season' } }
      if (item.kind === 'adviser') return { ...item, summary: adviserNote,
        primaryAction: { id: 'ask-adviser', kind: 'ask', label: 'Prepare a question',
          disabled: !journey?.planning_session || journey.stage === 'START' || pending(journey), disabledReason: 'Calculate your plans before asking about them.' } }
      if (item.kind === 'replay') return { ...item, summary: 'Start another attempt on the same teaching farm. This season and its recorded events stay in your journal.',
        primaryAction: { id: 'replay', kind: 'replay', label: 'Start a new attempt', disabled: pending(journey), disabledReason: pending(journey) ? 'Wait for the current calculation to finish.' : undefined } }
      return item
    })
    if (journey?.stage === 'COMPLETE') rows.splice(1, 0, { id: 'utility-next-challenge', kind: 'next_step', title: 'Two orders, one farm',
      eyebrow: 'Next challenge', summary: 'Try balancing two crops and two customer orders on the same small farm.',
      primaryAction: { id: 'next_challenge', kind: 'continue', label: 'Start the next challenge' } })
    return rows
  }, [journey, adviserNote])

  return <BeginnerGame landing={landing || (!loading && !journey)} journey={journey} loading={loading}
    busy={busy || loading} error={error} hasSavedSeason={Boolean(journey)} utilities={utilities}
    onStart={start} onContinue={start}
    onJourneyAction={request => perform(request.actionId, request.optionId)}
    onUtilityAction={(_utility, action) => perform(action.id)} onAsk={ask} />
}
