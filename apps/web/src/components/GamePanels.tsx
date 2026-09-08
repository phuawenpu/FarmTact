import { ArrowRight, Award, BadgeCheck, Bot, Check, ChevronRight, CircleAlert, FlaskConical, GitBranch, LoaderCircle, MessageCircle, Play, RotateCcw, Send, Sparkles, Users, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import type { Advisor, Conversation, ConversationMessage, ProposedAction, Quest, Scenario, ScenarioComparison, ScenarioControls } from '../lib/game'
import { QUEST_FALLBACKS } from '../lib/game'
import { api } from '../lib/api'
import type { Bed, Crop, Farm, Run, StrategyMetrics } from '../lib/types'
import { formatPreviewDate, previewBed } from './World'
import { AdvisorEvidence } from './AdvisorEvidence'

interface PanelShellProps { open: boolean; title: string; eyebrow?: string; wide?: boolean; onClose: () => void; children: React.ReactNode }

function PanelShell({ open, title, eyebrow, wide, onClose, children }: PanelShellProps) {
  const closeRef = useRef<HTMLButtonElement>(null)
  const panelRef = useRef<HTMLElement>(null)
  const closeHandler = useRef(onClose)
  closeHandler.current = onClose
  useEffect(() => {
    if (!open) return
    const previous = document.activeElement instanceof HTMLElement ? document.activeElement : null
    closeRef.current?.focus()
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') closeHandler.current()
      if (event.key !== 'Tab' || !panelRef.current) return
      const focusable = [...panelRef.current.querySelectorAll<HTMLElement>('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),textarea:not(:disabled),[tabindex]:not([tabindex="-1"])')]
      if (!focusable.length) return
      const first = focusable[0], last = focusable[focusable.length - 1]
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus() }
    }
    window.addEventListener('keydown', onKey)
    return () => { window.removeEventListener('keydown', onKey); previous?.focus() }
  }, [open])
  if (!open) return null
  return <div className="game-panel-layer" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
    <section ref={panelRef} className={`game-panel ${wide ? 'game-panel--wide' : ''}`} role="dialog" aria-modal="true" aria-label={title}>
      <header><div>{eyebrow && <p className="kicker">{eyebrow}</p>}<h2>{title}</h2></div><button ref={closeRef} className="icon-button" onClick={onClose} aria-label="Close"><X size={20}/></button></header>
      <div className="game-panel__body">{children}</div>
    </section>
  </div>
}

export function BedDetailPanel({ open, bed, crop, farm, run, previewDate, allocations, onClose, onExperiment, onAsk }: { open: boolean; bed: Bed | null; crop?: Crop; farm: Farm; run: Run | null; previewDate: Date; allocations?: import('../lib/types').Allocation[]; onClose: () => void; onExperiment: () => void; onAsk: () => void }) {
  if (!bed) return null
  const preview = previewBed(bed, previewDate, allocations)
  const harvestDate = allocations?.[0]?.harvest_date || bed.harvest_date
  const earlierDeliveries = bed.crop_id && harvestDate ? farm.orders.filter(order => order.crop_id === bed.crop_id && order.due_date < harvestDate) : []
  const runMatchesFarm = Boolean(run && !run.shared_demo && String(run.input_version) === String(farm.version))
  const accepted = runMatchesFarm ? run?.strategies.find(strategy => strategy.id === run.accepted_strategy_id) : undefined
  const bedIssues = accepted?.violations.filter(value => typeof value !== 'string' && value.entity_id === bed.id) || []
  return <PanelShell open={open} title={bed.name} eyebrow="Growing bed" onClose={onClose}>
    <div className="bed-inspector">
      <div className="bed-inspector__hero">
        {preview.cropId && preview.stage !== 'empty' ? <img src={`/art/crops/${preview.cropId}-${preview.stage === 'nursery' ? 'seedling' : preview.stage === 'ready' ? 'ready' : 'growing'}.svg`} alt={`${crop?.label || preview.cropId}, ${preview.stage}`}/> : <span>Open soil</span>}
      </div>
      <div className="bed-inspector__title"><div><p className="kicker">{preview.stage}</p><h3>{crop?.label || 'Unplanted bed'}</h3></div><strong>{Math.round(preview.progress)}%</strong></div>
      <div className="bed-progress" role="progressbar" aria-label={`${bed.name} growth preview`} aria-valuenow={Math.round(preview.progress)} aria-valuemin={0} aria-valuemax={100}><span style={{ width: `${preview.progress}%` }}/></div>
      <dl className="bed-facts"><div><dt>Preview date</dt><dd>{formatPreviewDate(previewDate)}</dd></div><div><dt>Next action</dt><dd>{preview.nextAction}</dd></div><div><dt>System</dt><dd>{bed.system.replaceAll('_', ' ')}</dd></div><div><dt>Area</dt><dd>{bed.area_m2} m²</dd></div></dl>
      {(earlierDeliveries.length > 0 || bedIssues.length > 0) && <div className="bed-issues"><strong><CircleAlert size={15}/> Planning issues to inspect</strong>{earlierDeliveries.map(order => <p key={order.id}>Delivery {order.id} is due {order.due_date} before this bed’s scheduled harvest. This bed cannot supply it; other beds or inventory may.</p>)}{bedIssues.map((issue,index) => <p key={index}>{formatConstraint(issue)}</p>)}</div>}
      {run && !runMatchesFarm && <p className="panel-note">The visible plan belongs to a different or recorded snapshot, so its constraint findings are not attached to this bed.</p>}
      <p className="preview-note">This is a schedule preview from recorded dates. It does not claim that growth was observed.</p>
      <div className="panel-actions"><button className="button button--forest" onClick={onAsk}><MessageCircle size={17}/> Ask Mei</button><button className="button button--coral" onClick={onExperiment}><FlaskConical size={17}/> Try a change</button></div>
    </div>
  </PanelShell>
}

export function ConversationPanel({ open, advisor, advisors, farm, run, selectedBed, scenario, onSelectAdvisor, onClose, onOpenScenario }: { open: boolean; advisor: Advisor; advisors: Advisor[]; farm: Farm; run: Run | null; selectedBed: Bed | null; scenario: Scenario | null; onSelectAdvisor: (advisor: Advisor) => void; onClose: () => void; onOpenScenario: (action?: ProposedAction, conversationId?: string) => void }) {
  const [conversation, setConversation] = useState<Conversation | null>(null)
  const [loading, setLoading] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [content, setContent] = useState('')
  const [invitee, setInvitee] = useState(advisors.find(item => item.id !== advisor.id)?.id || 'idris')
  const [replyTo, setReplyTo] = useState<string | null>(null)
  const [savedConversations, setSavedConversations] = useState<Conversation[]>([])
  const transcriptRef = useRef<HTMLDivElement>(null)
  const conversationGeneration = useRef(0)

  const refresh = useCallback(async (id: string, generation = conversationGeneration.current) => { const value = await api.conversation(id); if (generation === conversationGeneration.current) setConversation(value); return value }, [])

  useEffect(() => {
    if (!open) return
    const generation = ++conversationGeneration.current
    let cancelled = false
    setLoading(true); setBusy(false); setError(null); setConversation(null); setReplyTo(null)
    void (async () => {
      try {
        const available = await api.conversations()
        if (!cancelled) setSavedConversations(available.filter(item => item.advisor_id === advisor.id || item.advisor_ids?.includes(advisor.id)))
        const expectedSnapshotId = scenario?.id || `${farm.id}:v${farm.version}`
        let match = available.find(item => (item.advisor_id === advisor.id || item.advisor_ids?.includes(advisor.id)) && snapshotId(item) === expectedSnapshotId && (item.selected_bed_id || null) === (selectedBed?.id || null))
        if (!match) {
          const created = await api.createConversation({ advisor: advisor.id, snapshot_kind: scenario ? 'scenario' : 'farm', snapshot_id: scenario?.id || farm.id, selected_bed_id: selectedBed?.id })
          match = await api.conversation(created.id)
        } else match = await api.conversation(match.id)
        if (!cancelled) {
          setConversation(match)
          if (requestActive(match.last_request_status)) { setBusy(true); await pollForMessages(match.id, match.messages.length, generation); setBusy(false) }
        }
      } catch (caught) { if (!cancelled) setError(messageFor(caught, 'Conversation history is unavailable.')) }
      finally { if (!cancelled) setLoading(false) }
    })()
    return () => { cancelled = true; if (conversationGeneration.current === generation) conversationGeneration.current += 1 }
  }, [open, advisor.id, farm.id, farm.version, run?.id, scenario?.id, selectedBed?.id])

  useEffect(() => { transcriptRef.current?.scrollTo({ top: transcriptRef.current.scrollHeight, behavior: 'smooth' }) }, [conversation?.messages.length])

  const pollForMessages = async (id: string, _previous: number, generation = conversationGeneration.current) => {
    for (let attempt = 0; attempt < 330; attempt += 1) {
      await new Promise(resolve => window.setTimeout(resolve, 900))
      if (generation !== conversationGeneration.current) return false
      const next = await refresh(id, generation)
      if (!requestActive(next.last_request_status)) return true
    }
    if (generation === conversationGeneration.current) setError('The response is still running. It is saved and will resume when this discussion reopens.')
    return false
  }

  const send = async (prompt = content) => {
    if (!conversation || !prompt.trim() || busy) return
    const generation = conversationGeneration.current
    setBusy(true); setError(null)
    try {
      const before = conversation.messages.length
      await api.sendConversationMessage(conversation.id, { content: prompt.trim(), ...(replyTo ? { reply_to: replyTo } : {}) })
      if (generation !== conversationGeneration.current) return
      setContent(''); setReplyTo(null)
      await refresh(conversation.id, generation)
      await pollForMessages(conversation.id, before, generation)
    } catch (caught) { if (generation === conversationGeneration.current) setError(messageFor(caught, 'The message could not be sent.')) }
    finally { if (generation === conversationGeneration.current) setBusy(false) }
  }

  const invite = async () => {
    const selected = replyTo ? conversation?.messages.find(message => message.id === replyTo && message.speaker === 'advisor') : undefined
    const target = selected || [...(conversation?.messages || [])].reverse().find(message => message.speaker === 'advisor')
    if (!conversation || !target || busy) return
    const generation = conversationGeneration.current
    setBusy(true); setError(null)
    try { const before = conversation.messages.length; await api.inviteAdvisor(conversation.id, { advisor: invitee, question: `Please respond to this point: ${target.content}`, reply_to: target.id }); if (generation !== conversationGeneration.current) return; setReplyTo(null); await pollForMessages(conversation.id, before, generation) }
    catch (caught) { if (generation === conversationGeneration.current) setError(messageFor(caught, 'The advisor invitation could not be sent.')) }
    finally { if (generation === conversationGeneration.current) setBusy(false) }
  }

  const council = async () => {
    if (!conversation || busy) return
    const generation = conversationGeneration.current
    setBusy(true); setError(null)
    try { const before = conversation.messages.length; await api.conveneCouncil(conversation.id, { question: content.trim() || `What should we learn from ${selectedBed?.name || 'this farm snapshot'}?`, ...(replyTo ? { reply_to: replyTo } : {}) }); if (generation !== conversationGeneration.current) return; setContent(''); await pollForMessages(conversation.id, before, generation) }
    catch (caught) { if (generation === conversationGeneration.current) setError(messageFor(caught, 'The council could not be convened.')) }
    finally { if (generation === conversationGeneration.current) setBusy(false) }
  }

  const replay = async () => {
    if (!conversation) return
    const generation = conversationGeneration.current
    setLoading(true)
    try { const replayed = await api.conversationReplay(conversation.id); if (generation === conversationGeneration.current) setConversation(replayed) }
    catch (caught) { if (generation === conversationGeneration.current) setError(messageFor(caught, 'The recorded conversation could not be replayed.')) }
    finally { if (generation === conversationGeneration.current) setLoading(false) }
  }

  return <PanelShell open={open} title={`${advisor.name} · ${advisor.role}`} eyebrow={advisor.location} onClose={onClose}>
    <div className="conversation-shell">
      <div className="advisor-profile">
        <img src={`/art/advisors/${advisor.id}.svg`} alt={`Portrait of ${advisor.name}`}/><div><strong>{advisor.focus}</strong><p>Current context: {scenario ? `${scenario.name} · frozen branch ${scenario.id.slice(0, 8)}` : selectedBed ? `${selectedBed.name} · ${selectedBed.crop_id?.replaceAll('_', ' ') || 'open bed'}` : farm.name}</p></div>
      </div>
      <div className="advisor-switcher" aria-label="Advisor shortcuts">{advisors.map(item => <button key={item.id} className={item.id === advisor.id ? 'is-active' : ''} onClick={() => onSelectAdvisor(item)} aria-label={`Talk to ${item.name}`}><img src={`/art/advisors/${item.id}.svg`} alt=""/><span>{item.name}</span></button>)}</div>
      {!!savedConversations.length && <label className="saved-discussions"><span>Saved discussions</span><select value={conversation?.id || ''} onChange={event => { setLoading(true); void refresh(event.target.value).finally(() => setLoading(false)) }}><option value="" disabled>Select a frozen record</option>{savedConversations.map(item => <option key={item.id} value={item.id}>{item.advisor_id || 'advisor'} · {snapshotId(item) || 'frozen snapshot'}{item.selected_bed_id ? ` · ${item.selected_bed_id}` : ''}</option>)}</select></label>}
      {conversation && snapshotId(conversation) !== (scenario?.id || `${farm.id}:v${farm.version}`) && <div className="replay-label"><RotateCcw size={15}/><span>Saved frozen discussion · {snapshotId(conversation)}. This is not the current farm snapshot.</span></div>}
      {conversation?.transcript_mode === 'replay' && <div className="replay-label"><RotateCcw size={15}/><span>Recorded replay · opening and replaying use no new inference.</span></div>}
      {conversation?.last_request_status && ['INTERRUPTED','PARTIAL','FAILED','BLOCKED'].includes(conversation.last_request_status.toUpperCase()) && <div className="partial-conversation" role="status"><CircleAlert size={15}/><span><strong>Saved partial discussion · {conversation.last_request_status.toLowerCase()}</strong>Your existing messages are preserved. You can retry the question safely from this snapshot.</span></div>}
      {conversation?.messages.some(message => message.request_mode === 'council' || ['agreement','disagreement','challenge','synthesis','conclusion'].includes(message.relationship || '')) && <div className="council-stage" aria-label="Council speakers">{advisors.map(item => <span key={item.id}><img src={`/art/advisors/${item.id}.svg`} alt=""/><small>{item.name}</small></span>)}<b>Recorded council · expand messages below</b></div>}
      <div className="prompt-row" aria-label="Suggested questions">
        {[advisor.prompt, 'Show me the evidence.', 'What could I change?'].map(prompt => <button key={prompt} onClick={() => void send(prompt)} disabled={busy || loading}>{prompt}</button>)}
      </div>
      <div className="conversation-transcript" ref={transcriptRef} aria-live="polite">
        {loading && !conversation ? <div className="panel-loading"><LoaderCircle className="spinner-icon"/> Opening recorded messages…</div> : null}
        {!loading && conversation && !conversation.messages.length ? <div className="conversation-empty"><MessageCircle size={27}/><strong>Start with a farm question</strong><p>Advice stays attached to this frozen snapshot.</p></div> : null}
        {conversation?.messages.map(message => <MessageCard key={message.id} message={message} messages={conversation.messages} conversation={conversation} replying={replyTo === message.id} onReply={() => setReplyTo(message.id)} onOpenScenario={action => onOpenScenario(action, conversation.id)}/>) }
        {busy && <div className="thinking-row"><span className="thinking-dots"><i/><i/><i/></span>Waiting for a bounded response…</div>}
      </div>
      {error && <p className="panel-error" role="alert"><CircleAlert size={15}/>{error}</p>}
      {replyTo && <button className="reply-banner" onClick={() => setReplyTo(null)}>Replying to a specific message <X size={14}/></button>}
      <form className="conversation-composer" onSubmit={event => { event.preventDefault(); void send() }}>
        <label className="sr-only" htmlFor="advisor-message">Message {advisor.name}</label><input id="advisor-message" value={content} onChange={event => setContent(event.target.value)} placeholder={`Ask ${advisor.name} about this snapshot…`} maxLength={1000}/><button type="submit" aria-label="Send message" disabled={!content.trim() || busy}><Send size={18}/></button>
      </form>
      <div className="conversation-actions">
        <label><span>Invite</span><select value={invitee} onChange={event => setInvitee(event.target.value as typeof invitee)}>{advisors.filter(item => item.id !== advisor.id).map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label>
        <button onClick={() => void invite()} disabled={busy || !conversation?.messages.length}><Bot size={16}/> Invite advisor</button>
        <button onClick={() => void council()} disabled={busy || !conversation}><Users size={16}/> Convene council</button>
        <button onClick={() => void replay()} disabled={!conversation || busy}><RotateCcw size={16}/> Replay</button>
      </div>
    </div>
  </PanelShell>
}

function MessageCard({ message, messages, conversation, replying, onReply, onOpenScenario }: { message: ConversationMessage; messages: ConversationMessage[]; conversation: Conversation; replying: boolean; onReply: () => void; onOpenScenario: (action: ProposedAction) => void }) {
  const author = message.speaker === 'user' ? 'You' : message.speaker_name || message.speaker_id || message.speaker
  const unsupported = message.validation_status === 'unsupported' || message.validation_status === 'blocked_unsupported'
  const replied = message.reply_to ? messages.find(item => item.id === message.reply_to) : undefined
  return <article className={`message-card message-card--${message.speaker} ${replying ? 'is-replying' : ''}`}>
    {message.reply_to && <span className="message-relationship"><ArrowRight size={12}/> replies to {replied?.speaker_name || replied?.speaker_id || 'earlier message'}{replied ? `: “${replied.content.slice(0, 48)}${replied.content.length > 48 ? '…' : ''}”` : ''}</span>}
    <header><strong>{author}</strong><span className={`validation-chip ${unsupported ? 'validation-chip--bad' : ''}`}>{message.validation_status === 'references_verified' ? 'References checked · advisor interpretation' : message.validation_status || 'recorded'}</span></header>
    <p>{message.content}</p>
    <AdvisorEvidence message={message} conversation={conversation}/>
    {!!message.proposed_actions?.length && <div className="proposed-actions"><strong>Supported experiment</strong>{message.proposed_actions.map((action, index) => <button key={`${action.control}-${index}`} onClick={() => onOpenScenario(action)} disabled={action.status === 'blocked_unsupported'}><FlaskConical size={14}/>{action.control.replaceAll('_', ' ')} = {action.value}{action.unit === 'percent' ? '%' : ' days'} <ChevronRight size={14}/></button>)}</div>}
    {unsupported && <p className="unsupported-note"><CircleAlert size={13}/> Unsupported advice cannot authorize a change.</p>}
    {message.validation_status === 'references_verified' && <p className="interpretation-note">Citations and proposed controls were checked. The advisor’s interpretation remains unverified.</p>}
    <button className="message-reply" onClick={onReply}>Reply to this point</button>
  </article>
}

export function QuestJournal({ open, farm, onClose, onStartQuest }: { open: boolean; farm: Farm; onClose: () => void; onStartQuest: (quest: Quest) => void }) {
  const [quests, setQuests] = useState<Quest[]>(QUEST_FALLBACKS)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => { if (open) void api.quests().then(values => setQuests(mergeQuests(values))).catch(caught => setError(messageFor(caught, 'Saved progress is temporarily unavailable.'))) }, [open])
  return <PanelShell open={open} title="Quest journal" eyebrow={`${farm.name} · repeatable challenges`} onClose={onClose}>
    <div className="quest-intro"><Award size={25}/><div><strong>Experiment to earn discovery badges</strong><p>Infeasible outcomes still count when you inspect the trade-offs.</p></div></div>
    {error && <p className="panel-note">{error} You can still review the four challenges.</p>}
    <div className="quest-list">{quests.map((quest, index) => {
      const completed = (quest.experiment_ids?.length || quest.completed_scenario_ids?.length || 0) > 0
      const inspected = (quest.inspected_ids?.length || quest.inspected_scenario_ids?.length || 0) > 0
      return <article key={quest.id} className={completed ? 'is-complete' : ''}><span className="quest-number">{completed ? <Check size={18}/> : index + 1}</span><div><p className="kicker">{completed ? 'Experiment complete' : 'Available now'}</p><h3>{quest.name || quest.title}</h3><p>{quest.description}</p><div className="quest-badges">{completed && <span><BadgeCheck size={14}/> Experimenter</span>}{inspected && <span><Sparkles size={14}/> Trade-off finder</span>}</div></div><button className="button button--forest" onClick={() => onStartQuest(quest)}>{completed ? 'Try again' : 'Start quest'}<ChevronRight size={16}/></button></article>
    })}</div>
  </PanelShell>
}

export function ScenarioLab({ open, farm, crops, selectedBed, initialQuestId, proposedAction, onClose, onHighlight, onInterpret }: { open: boolean; farm: Farm; crops: Crop[]; selectedBed: Bed | null; initialQuestId: string | null; proposedAction: { action: ProposedAction; conversationId: string } | null; onClose: () => void; onHighlight: (bedIds: string[]) => void; onInterpret: (scenario: Scenario) => void }) {
  const [scenarios, setScenarios] = useState<Scenario[]>([])
  const [quests, setQuests] = useState<Quest[]>(QUEST_FALLBACKS)
  const [questId, setQuestId] = useState('sandbox')
  const [parentId, setParentId] = useState('')
  const [controls, setControls] = useState<ScenarioControls>(() => sandboxControls(selectedBed, farm.orders[0]?.crop_id))
  const [selectedIds, setSelectedIds] = useState<string[]>([])
  const [comparison, setComparison] = useState<ScenarioComparison | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [phase, setPhase] = useState<'brief' | 'assumptions' | 'result'>('brief')

  const load = useCallback(async () => {
    const [savedScenarios, savedQuests] = await Promise.all([api.scenarios(), api.quests()])
    setScenarios(savedScenarios); setQuests(mergeQuests(savedQuests))
    return savedScenarios
  }, [])
  useEffect(() => {
    if (!open) return
    let cancelled = false
    void load().then(async saved => {
      const pending = saved.find(item => requestActive(item.status))
      if (!pending || cancelled) return
      setBusy(true); setSelectedIds([pending.id])
      let resumed = pending
      for (let attempt = 0; !scenarioTerminal(resumed.status) && attempt < 300 && !cancelled; attempt += 1) { await new Promise(resolve => window.setTimeout(resolve, 500)); resumed = await api.scenario(resumed.id) }
      if (!cancelled) { setScenarios(items => [resumed, ...items.filter(item => item.id !== resumed.id)]); setBusy(false); if (scenarioTerminal(resumed.status)) { setPhase('result'); onHighlight(resumed.affected_bed_ids || []) } }
    }).catch(caught => { if (!cancelled) setError(messageFor(caught, 'Saved scenario branches are unavailable.')) })
    return () => { cancelled = true }
  }, [open, load])
  useEffect(() => { setControls(questId === 'sandbox' ? sandboxControls(selectedBed, farm.orders[0]?.crop_id) : questControls(questId, selectedBed, farm.orders[0]?.crop_id)) }, [selectedBed?.id])
  useEffect(() => {
    if (!open) return
    if (initialQuestId) { setQuestId(initialQuestId); setControls(questControls(initialQuestId, selectedBed, farm.orders[0]?.crop_id)); setPhase('brief') }
    else if (!proposedAction) { setQuestId('sandbox'); setControls(sandboxControls(selectedBed, farm.orders[0]?.crop_id)); setPhase('brief') }
  }, [open, initialQuestId])
  useEffect(() => {
    if (!open || !proposedAction) return
    const { action } = proposedAction
    setControls(previous => ({ ...previous, [action.control]: action.value, ...(action.control === 'delay_days' || action.control === 'yield_percent' ? { batch_id: action.target_id || previous.batch_id } : {}), ...(action.control === 'demand_percent' ? { demand_crop_id: action.target_id || previous.demand_crop_id } : {}) }))
    setQuestId('sandbox'); setParentId(''); setPhase('assumptions')
  }, [open, proposedAction])

  const quest = quests.find(item => item.id === questId) || { id: 'sandbox', title: 'Open sandbox', name: 'Open sandbox', description: 'Change any supported farm assumption without a quest badge.', advisor_id: 'asha' as const }
  const run = async () => {
    setBusy(true); setError(null); setComparison(null)
    try {
      let scenario = await api.createScenario({ name: `${quest.name || quest.title} · ${new Date().toLocaleDateString('en-SG')}`, controls, ...(questId !== 'sandbox' ? { quest_id: questId } : {}), ...(proposedAction ? { source_conversation_id: proposedAction.conversationId } : parentId ? { parent_scenario_id: parentId } : {}) })
      scenario = await api.runScenario(scenario.id)
      for (let attempt = 0; !scenarioTerminal(scenario.status) && attempt < 300; attempt += 1) { await new Promise(resolve => window.setTimeout(resolve, 500)); scenario = await api.scenario(scenario.id) }
      setScenarios(values => [scenario, ...values.filter(item => item.id !== scenario.id)])
      setSelectedIds([scenario.id])
      if (!scenarioTerminal(scenario.status)) throw new Error('The numerical job is still running. It remains saved and will resume when this lab reopens.')
      setPhase('result'); onHighlight(scenario.affected_bed_ids || [])
    } catch (caught) { setError(messageFor(caught, 'The experiment could not run.')) }
    finally { setBusy(false) }
  }

  const compare = async () => {
    if (!selectedIds.length) return
    setBusy(true); setError(null)
    try { setComparison(await api.compareScenarios(selectedIds.slice(0, 3))); setPhase('result') }
    catch (caught) { setError(messageFor(caught, 'These branches could not be compared.')) }
    finally { setBusy(false) }
  }

  const inspect = async (scenario: Scenario) => {
    if (!scenario.quest_id) return
    setBusy(true); setError(null)
    try { await api.inspectQuest(scenario.quest_id, scenario.id); setQuests(mergeQuests(await api.quests())) }
    catch (caught) { setError(messageFor(caught, 'Quest inspection could not be saved.')) }
    finally { setBusy(false) }
  }

  return <PanelShell open={open} title="Scenario lab" eyebrow="Frozen-input numerical experiments" wide onClose={onClose}>
    <div className="scenario-layout">
      <aside className="scenario-brief">
        <div className="scenario-steps" aria-label="Experiment steps"><button className={phase === 'brief' ? 'is-active' : ''} onClick={() => setPhase('brief')}>1 <span>Briefing</span></button><button className={phase === 'assumptions' ? 'is-active' : ''} onClick={() => setPhase('assumptions')}>2 <span>Assumptions</span></button><button className={phase === 'result' ? 'is-active' : ''} onClick={() => setPhase('result')}>3 <span>Compare</span></button></div>
        <label>Challenge<select value={questId} onChange={event => { setQuestId(event.target.value); setControls(event.target.value === 'sandbox' ? sandboxControls(selectedBed, farm.orders[0]?.crop_id) : questControls(event.target.value, selectedBed, farm.orders[0]?.crop_id)); setPhase('brief') }}><option value="sandbox">Open sandbox</option>{quests.map(item => <option key={item.id} value={item.id}>{item.name || item.title}</option>)}</select></label>
        <div className="brief-card"><img src={`/art/advisors/${quest.advisor_id || 'asha'}.svg`} alt=""/><div><p className="kicker">Advisor briefing</p><h3>{quest.name || quest.title}</h3><p>{quest.description}</p></div></div>
        <p className="preview-note">Every experiment creates a branch from frozen farm inputs. The main farm and its latest run remain unchanged.{proposedAction ? ' This branch is linked to the exact conversation snapshot.' : ''}</p>
      </aside>
      <div className="scenario-workbench">
        {phase !== 'result' ? <>
          <div className="scenario-heading"><div><p className="kicker">Editable assumptions</p><h3>What changes in this branch?</h3></div><span>Numerical · no inference</span></div>
          <div className="scenario-controls">
            <RangeControl label="Harvest delay" value={controls.delay_days} min={0} max={14} suffix="days" onChange={value => setControls(current => ({ ...current, delay_days: value }))}/>
            <RangeControl label="Expected yield" value={controls.yield_percent} min={50} max={100} suffix="%" onChange={value => setControls(current => ({ ...current, yield_percent: value }))}/>
            <RangeControl label="Market demand" value={controls.demand_percent} min={50} max={150} suffix="%" onChange={value => setControls(current => ({ ...current, demand_percent: value }))}/>
            <RangeControl label="Available labour" value={controls.labour_percent} min={50} max={150} suffix="%" onChange={value => setControls(current => ({ ...current, labour_percent: value }))}/>
            <RangeControl label="Available cash" value={controls.cash_percent} min={50} max={150} suffix="%" onChange={value => setControls(current => ({ ...current, cash_percent: value }))}/>
          </div>
          <div className="scenario-targets"><label>Selected batch<select value={controls.batch_id || ''} onChange={event => setControls(current => ({ ...current, batch_id: event.target.value }))}>{farm.beds.filter(bed => bed.crop_id).map((bed, index) => <option key={bed.id} value={batchId(bed, index)}>{bed.name} · {bed.crop_id?.replaceAll('_', ' ')}</option>)}</select></label><label>Demand crop<select value={controls.demand_crop_id || ''} onChange={event => setControls(current => ({ ...current, demand_crop_id: event.target.value }))}>{crops.filter(crop => farm.orders.some(order => order.crop_id === crop.id)).map(crop => <option key={crop.id} value={crop.id}>{crop.label}</option>)}</select></label><label>Continue branch<select value={parentId} onChange={event => setParentId(event.target.value)}><option value="">Main farm baseline</option>{scenarios.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}</select></label></div>
          {parentId && <p className="panel-note">Assumptions are relative to this branch; comparison retains the original farm baseline.</p>}
          {error && <p className="panel-error" role="alert"><CircleAlert size={15}/>{error}</p>}
          <div className="panel-actions"><button className="button button--forest" onClick={() => setPhase('assumptions')}>Review assumptions</button><button className="button button--coral" onClick={() => void run()} disabled={busy}>{busy ? <LoaderCircle className="spinner-icon"/> : <Play size={17}/>} Run experiment</button></div>
        </> : <ScenarioResults scenarios={scenarios} quests={quests} selectedIds={selectedIds} setSelectedIds={setSelectedIds} comparison={comparison} onCompare={() => void compare()} onInspect={scenario => void inspect(scenario)} onInterpret={onInterpret} busy={busy} error={error}/>} 
      </div>
    </div>
  </PanelShell>
}

function ScenarioResults({ scenarios, quests, selectedIds, setSelectedIds, comparison, onCompare, onInspect, onInterpret, busy, error }: { scenarios: Scenario[]; quests: Quest[]; selectedIds: string[]; setSelectedIds: React.Dispatch<React.SetStateAction<string[]>>; comparison: ScenarioComparison | null; onCompare: () => void; onInspect: (scenario: Scenario) => void; onInterpret: (scenario: Scenario) => void; busy: boolean; error: string | null }) {
  const displayed = comparison?.scenarios || scenarios.filter(item => selectedIds.includes(item.id))
  const [policy, setPolicy] = useState('Balanced')
  return <div className="scenario-results"><div className="scenario-heading"><div><p className="kicker">Before and after</p><h3>Inspect the trade-offs</h3></div><span><BadgeCheck size={14}/> Learning counts even when infeasible</span></div>
    {!scenarios.length ? <div className="conversation-empty"><GitBranch size={28}/><strong>No branches yet</strong><p>Run an experiment to create one.</p></div> : <div className="branch-picker"><p>Select up to three branches</p>{scenarios.map(item => { const selected = selectedIds.includes(item.id); return <label key={item.id}><input type="checkbox" checked={selected} disabled={!selected && selectedIds.length >= 3} onChange={() => setSelectedIds(ids => selected ? ids.filter(id => id !== item.id) : [...ids, item.id])}/><span><b>{item.name}</b><small>{scenarioStatusLabel(item)}</small></span></label>})}</div>}
    <button className="button button--forest compare-button" onClick={onCompare} disabled={busy || !selectedIds.length}>{busy ? <LoaderCircle className="spinner-icon"/> : <GitBranch size={17}/>} Compare selected</button>
    {error && <p className="panel-error" role="alert"><CircleAlert size={15}/>{error}</p>}
    {!!displayed.length && <div className="policy-picker" aria-label="Planning policy"><span>Compare the same policy</span>{['Lean','Balanced','Resilient'].map(name => <button key={name} className={policy === name ? 'is-active' : ''} onClick={() => setPolicy(name)}>{name}</button>)}</div>}
    {!!displayed.length && <div className="comparison-table-wrap"><table className="comparison-table"><caption>{policy} policy · baseline, branch outcome and computed change</caption><thead><tr><th>Outcome</th><th>Baseline</th>{displayed.map(item => <th key={item.id}>{item.name}<small> outcome · Δ</small></th>)}</tr></thead><tbody>{['fill_rate','margin_sgd','waste_kg','shortfall_kg','labour_hours','cost_sgd'].map(metric => <tr key={metric}><th>{metric.replaceAll('_', ' ')}</th><td>{policyMetric(displayed[0], policy, metric, 'baseline')}</td>{displayed.map(item => <td key={item.id} className={item.simulation_status === 'NO_FEASIBLE_PLAN' ? 'is-warning' : ''}>{policyMetric(item, policy, metric, 'scenario')} <small className="metric-delta">{formatDelta(item.policy_comparisons?.find(row => row.policy === policy)?.deltas?.[metric as keyof StrategyMetrics], metric)}</small></td>)}</tr>)}</tbody></table></div>}
    {!!displayed.length && <div className="branch-cards">{displayed.map(item => { const row = item.policy_comparisons?.find(value => value.policy === policy); const inspected = quests.find(quest => quest.id === item.quest_id)?.inspected_ids?.includes(item.id); const completed = item.status === 'COMPLETED'; return <article key={item.id}><p className="kicker">{scenarioStatusLabel(item)}</p><h3>{item.name}</h3><p>{controlSummary(item.controls)}</p><small>Snapshot {item.input_hash?.slice(0, 10) || 'recorded'} · baseline {item.baseline_hash?.slice(0, 10) || 'recorded'}</small>{item.affected_bed_ids?.length ? <span>{item.affected_bed_ids.length} affected {item.affected_bed_ids.length === 1 ? 'bed' : 'beds'} · {item.affected_deliveries?.length || 0} deliveries</span> : null}{item.affected_deliveries?.length ? <details><summary>Affected deliveries</summary>{item.affected_deliveries.map(delivery => <p key={delivery.order_id}>{delivery.order_id} · {delivery.crop_id?.replaceAll('_', ' ')} · due {delivery.due_date}</p>)}</details> : null}{completed && row?.violations?.length ? <details><summary>{row.violations.length} constraint {row.violations.length === 1 ? 'issue' : 'issues'}</summary>{row.violations.map((violation,index) => <p key={index}>{formatConstraint(violation)}</p>)}</details> : completed ? <span><Check size={12}/> No {policy} constraint issues</span> : <span>Results unavailable until this job completes.</span>}{completed && item.quest_id && <button className={inspected ? 'is-inspected' : ''} onClick={() => onInspect(item)} disabled={Boolean(inspected) || busy}>{inspected ? <><BadgeCheck size={14}/> Trade-off badge earned</> : <><Award size={14}/> Mark trade-offs inspected</>}</button>}{completed && <button onClick={() => onInterpret(item)}><MessageCircle size={14}/> Ask an advisor about this branch</button>}</article>})}</div>}
  </div>
}

function RangeControl({ label, value, min, max, suffix, onChange }: { label: string; value: number; min: number; max: number; suffix: string; onChange: (value: number) => void }) {
  return <label className="range-control"><span><b>{label}</b><output>{value}{suffix === 'days' ? ` ${value === 1 ? 'day' : 'days'}` : suffix}</output></span><input aria-label={label} type="range" min={min} max={max} value={value} onChange={event => onChange(Number(event.target.value))}/><small>{min}{suffix === '%' ? '%' : ''}<i/>{max}{suffix === '%' ? '%' : ''}</small></label>
}

export function AccessibleFarmView({ open, farm, crops, previewDate, allocations, onSelect, onClose }: { open: boolean; farm: Farm; crops: Map<string, Crop>; previewDate: Date; allocations: Map<string, import('../lib/types').Allocation[]>; onSelect: (bed: Bed) => void; onClose: () => void }) {
  return <PanelShell open={open} title="Farm list" eyebrow={`Schedule preview · ${formatPreviewDate(previewDate)}`} wide onClose={onClose}><div className="accessible-world-table"><p className="preview-note">Keyboard-friendly alternative to the farm scene. Previewed stages use scheduled dates and do not create observations.</p><table><caption>All {farm.beds.length} growing beds</caption><thead><tr><th>Bed</th><th>Crop</th><th>Stage</th><th>Progress</th><th>Next action</th><th/></tr></thead><tbody>{farm.beds.map(bed => { const state = previewBed(bed, previewDate, allocations.get(bed.id)); return <tr key={bed.id}><th>{bed.name}</th><td>{state.cropId ? crops.get(state.cropId)?.label || state.cropId : 'Open bed'}</td><td>{state.stage}</td><td>{Math.round(state.progress)}%</td><td>{state.nextAction}</td><td><button onClick={() => onSelect(bed)}>Inspect</button></td></tr> })}</tbody></table></div></PanelShell>
}

function sandboxControls(bed: Bed | null, fallbackCrop?: string): ScenarioControls { return { batch_id: bed ? batchId(bed, 0) : 'batch-01', delay_days: 0, yield_percent: 100, demand_crop_id: bed?.crop_id || fallbackCrop, demand_percent: 100, labour_percent: 100, cash_percent: 100 } }
function questControls(questId: string, bed: Bed | null, fallbackCrop?: string): ScenarioControls {
  const controls: ScenarioControls = { batch_id: bed ? batchId(bed, 0) : 'batch-01', delay_days: 0, yield_percent: 100, demand_crop_id: bed?.crop_id || fallbackCrop, demand_percent: 100, labour_percent: 100, cash_percent: 100 }
  if (questId === 'late_harvest') { controls.delay_days = 3; controls.yield_percent = 90 }
  if (questId === 'busy_market') controls.demand_percent = 125
  if (questId === 'short_handed_week') controls.labour_percent = 70
  if (questId === 'tight_budget') controls.cash_percent = 65
  return controls
}
function batchId(bed: Bed, index: number) { return typeof bed.batch_id === 'string' ? bed.batch_id : bed.id.startsWith('bed-') ? bed.id.replace('bed-', 'batch-') : `batch-${String(index + 1).padStart(2, '0')}` }
function scenarioTerminal(status: string) { return ['completed','feasible','infeasible','failed','no_feasible_plan'].some(value => status.toLowerCase().includes(value)) }
function mergeQuests(values: Quest[]) { return QUEST_FALLBACKS.map(fallback => ({ ...fallback, ...(values.find(value => value.id === fallback.id) || {}) })) }
function messageFor(caught: unknown, fallback: string) { return caught instanceof Error ? caught.message : fallback }
function controlSummary(controls: ScenarioControls) { return `${controls.delay_days}d delay · ${controls.yield_percent}% yield · ${controls.demand_percent}% demand · ${controls.labour_percent}% labour · ${controls.cash_percent}% cash` }
function policyMetric(scenario: Scenario, policy: string, metric: string, side: 'baseline' | 'scenario') {
  const row = scenario.policy_comparisons?.find(item => item.policy === policy)
  const value = row?.[side === 'baseline' ? 'baseline_metrics' : 'scenario_metrics']?.[metric as keyof StrategyMetrics]
  if (typeof value !== 'number') return '—'
  return formatMetric(value, metric)
}
function formatMetric(value: number, metric: string) {
  if (metric === 'fill_rate') return `${(value * (value <= 1 ? 100 : 1)).toLocaleString('en-SG', { minimumFractionDigits: 1, maximumFractionDigits: 2 })}%`
  if (metric.includes('sgd')) return `$${Math.round(value).toLocaleString('en-SG')}`
  return `${value.toLocaleString('en-SG', { maximumFractionDigits: 2 })}${metric.includes('kg') ? ' kg' : metric.includes('hours') ? ' hr' : ''}`
}
function formatDelta(value: unknown, metric: string) { if (typeof value !== 'number') return 'Δ —'; if (metric === 'fill_rate') return `Δ ${value > 0 ? '+' : ''}${(value * 100).toLocaleString('en-SG', { maximumFractionDigits: 2 })} percentage points`; return `Δ ${value > 0 ? '+' : ''}${formatMetric(value, metric)}` }
function formatConstraint(value: unknown) {
  if (typeof value === 'string') return value.replaceAll('_', ' ')
  if (!value || typeof value !== 'object') return 'Constraint issue'
  const item = value as Record<string, unknown>
  const label = String(item.constraint_code || item.message || 'Constraint issue').replaceAll('_', ' ')
  const entity = item.entity_id ? ` for ${String(item.entity_id).replaceAll('_', ' ')}` : ''
  const quantities = item.required !== undefined && item.available !== undefined ? `: ${String(item.required)} ${String(item.unit || '')} required; ${String(item.available)} ${String(item.unit || '')} available` : ''
  return `${label}${entity}${quantities}`
}
function snapshotId(conversation: Conversation) { return typeof conversation.snapshot_ref === 'object' ? conversation.snapshot_ref?.id : conversation.snapshot_ref }
function requestActive(status?: string | null) { return ['QUEUED','RUNNING'].includes(String(status || '').toUpperCase()) }
function scenarioStatusLabel(scenario: Scenario) { if (scenario.simulation_status === 'NO_FEASIBLE_PLAN') return 'Infeasible result'; if (scenario.simulation_status === 'ACCEPTED_FOR_SIMULATION') return 'Feasible branch · simulation only'; if (scenario.status === 'COMPLETED') return 'Experiment complete'; return scenario.status.replaceAll('_', ' ').toLowerCase() }
