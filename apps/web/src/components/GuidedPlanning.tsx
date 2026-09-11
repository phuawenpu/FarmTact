import { AlertTriangle, ArrowRight, CalendarDays, Check, ClipboardList, CloudSun, Leaf, LoaderCircle, PackagePlus, Play, RefreshCw, Scale, Sprout, Users, Warehouse, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { Crop, Strategy, StrategyMetrics } from '../lib/types'
import { ADVISORS } from '../lib/game'
import { editionPath } from '../lib/edition'
import { planningApi, rememberPlanningSession, rememberedPlanningSession, type OrderChange, type PlanningAssumptions, type PlanningSession } from '../lib/planning'

const terminal = new Set(['COMPLETED', 'FAILED', 'CANCELLED'])
const steps = [
  ['records', 'Review records'], ['planning', 'Calculate schedules'], ['review', 'Council review'], ['simulation', 'Simulate plan'], ['comparison', 'Change & compare'],
] as const

export function GuidedPlanning({ crops }: { crops: Crop[] }) {
  const [session, setSession] = useState<PlanningSession | null>(null)
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(''), [error, setError] = useState('')
  const [demandPercent, setDemandPercent] = useState(115), [yieldPercent, setYieldPercent] = useState(90), [delayDays, setDelayDays] = useState(3)
  const [cropId, setCropId] = useState(''), [orderOpen, setOrderOpen] = useState(false)
  const [orderQty, setOrderQty] = useState(20), [orderPrice, setOrderPrice] = useState(8), [orderDate, setOrderDate] = useState('')
  const cropOptions = useMemo(() => crops.filter(item => item.recipe), [crops])
  const selectedCrop = cropId || cropOptions[0]?.id || ''

  const load = useCallback(async () => {
    setLoading(true); setError('')
    try {
      const remembered = rememberedPlanningSession()
      let value: PlanningSession | undefined
      if (remembered) try { value = await planningApi.get(remembered) } catch { /* fall through to latest */ }
      if (!value) { const page = await planningApi.list(); value = page.sessions[0] }
      if (!value) value = await planningApi.create()
      rememberPlanningSession(value.id); setSession(value)
    } catch (caught) { setError(message(caught, 'The guided planning mission could not be opened.')) }
    finally { setLoading(false) }
  }, [])
  useEffect(() => { void load() }, [load])

  useEffect(() => {
    if (!session?.job || terminal.has(session.job.status) || !['QUEUED', 'RUNNING'].includes(session.job.status)) return
    const id = session.id
    const timer = window.setInterval(() => { void planningApi.get(id).then(next => { setSession(next); if (terminal.has(next.job?.status || '')) setBusy('') }).catch(() => {}) }, 1200)
    return () => window.clearInterval(timer)
  }, [session?.id, session?.job?.id, session?.job?.status])

  const mutate = async (label: string, action: (current: PlanningSession) => Promise<PlanningSession>) => {
    if (!session) return
    setBusy(label); setError('')
    try { const next = await action(session); setSession(next); rememberPlanningSession(next.id); if (!['QUEUED', 'RUNNING'].includes(next.job?.status || '')) setBusy('') }
    catch (caught) { setBusy(''); setError(message(caught, `Could not ${label}.`)) }
  }
  const date = session?.farm.planning_date || session?.farm.cutoff?.slice(0, 10) || new Date().toISOString().slice(0, 10)
  const endDate = addDays(date, Math.min(session?.farm.horizon_days || 56, 56) - 1)
  const dueDate = orderDate || addDays(date, 21)
  const makeAssumptions = (): PlanningAssumptions => ({
    future_demand: [{ crop_id: selectedCrop, start_date: date, end_date: endDate, percent: Math.min(demandPercent, 150) }],
    seasonal: [{ crop_id: selectedCrop, system: 'sheltered_hydroponic', start_date: date, end_date: endDate, yield_percent: yieldPercent, delay_days: delayDays, reason: 'Test how a seasonal production disruption changes the saved schedule.', provenance: 'synthetic_assumption' }],
    order_changes: orderOpen ? [{ operation: 'add', order_id: `guided-${session?.id || 'session'}-${session?.revision || 0}`, crop_id: selectedCrop, due_date: dueDate, quantity_kg: orderQty, price_sgd_per_kg: orderPrice } satisfies OrderChange] : [],
  })
  const currentStep = Math.max(0, steps.findIndex(([id]) => id === session?.stage))

  if (loading) return <section className="guided-loading"><LoaderCircle className="spin"/><h1>Opening the production planning mission</h1><p>Loading the saved farm records and latest session.</p></section>
  if (!session) return <section className="guided-loading"><AlertTriangle/><h1>Planning mission unavailable</h1><p>{error}</p><button className="button button--forest" onClick={() => void load()}>Try again</button></section>
  const running = ['QUEUED', 'RUNNING'].includes(session.job?.status || '')

  return <div className="guided-planning">
    <header className="guided-hero">
      <div><p className="kicker">Farm production planning · synthetic demonstration</p><h1>Plan the next crop cycle</h1><p>Balance customer demand, crop timing, growing space and seasonal conditions—then see how the farm changes.</p></div>
      <span className="guided-data-badge"><Sprout size={17}/> Simulated farm · no real operations</span>
    </header>
    <nav className="guided-steps" aria-label="Planning mission progress">
      {steps.map(([id, label], index) => <span key={id} className={index === currentStep ? 'is-current' : index < currentStep ? 'is-done' : ''}><b>{index < currentStep ? <Check size={14}/> : index + 1}</b><small>{label}</small></span>)}
    </nav>
    {error && <div className="guided-error" role="alert"><AlertTriangle size={18}/><span>{error}</span><button onClick={() => setError('')} aria-label="Dismiss error"><X size={16}/></button></div>}
    {running && <div className="guided-running" role="status"><LoaderCircle className="spin"/><span><b>{session.job?.stage?.replaceAll('_', ' ') || 'Calculating'}</b><small>Your farm remains available while the numerical worker runs.</small></span><button className="text-button" onClick={() => void mutate('cancel calculation', value => planningApi.cancel(value.id, value.revision))}>Cancel</button></div>}

    <FarmRecords session={session} crops={crops}/>

    {session.result?.strategies?.length ? <PlanningResults session={session} /> : <section className="guided-action-card">
      <span><Scale size={22}/></span><div><p className="kicker">Same inputs, three priorities</p><h2>Calculate feasible planting schedules</h2><p>Lean, Balanced and Resilient schedules will use these records, growth cycles and available beds. Numerical calculation does not use AI.</p></div>
      <button className="button button--forest" disabled={Boolean(busy)} onClick={() => void mutate('calculate schedules', value => planningApi.calculate(value.id, value.revision))}>Calculate schedules <ArrowRight size={17}/></button>
    </section>}

    {!!session.result?.strategies?.length && <CouncilCheckpoint session={session} busy={busy} onReview={() => void mutate('request Council review', value => planningApi.review(value.id, value.revision))}/>} 
    {!!session.result?.strategies?.length && <Simulation session={session} busy={busy} onAdvance={days => void mutate(`advance ${days} days`, value => planningApi.advance(value.id, value.revision, days))}/>} 
    {!!session.result?.strategies?.length && <DisruptionForm crops={cropOptions} cropId={selectedCrop} setCropId={setCropId} date={date} endDate={endDate} demandPercent={demandPercent} setDemandPercent={setDemandPercent} yieldPercent={yieldPercent} setYieldPercent={setYieldPercent} delayDays={delayDays} setDelayDays={setDelayDays} orderOpen={orderOpen} setOrderOpen={setOrderOpen} orderQty={orderQty} setOrderQty={setOrderQty} orderPrice={orderPrice} setOrderPrice={setOrderPrice} orderDate={dueDate} setOrderDate={setOrderDate} busy={busy} onRun={() => void mutate('compare disruption', value => planningApi.disrupt(value.id, value.revision, makeAssumptions()))}/>} 
    {session.stage === 'comparison' && <Comparison session={session}/>} 
  </div>
}

function FarmRecords({ session, crops }: { session: PlanningSession; crops: Crop[] }) {
  const crop = (id?: string) => crops.find(item => item.id === id)?.label || id || 'Unassigned'
  const active = session.farm.beds.filter(bed => bed.stage !== 'empty')
  return <section className="guided-section records-section"><header><div><p className="kicker">1 · Review manual-style records</p><h2>{session.farm.name}</h2><p>{session.farm.location} · planning from {civil(session.farm.planning_date || session.farm.cutoff)}</p></div><div className="records-summary"><span><Warehouse size={18}/><b>{active.length}/{session.farm.beds.length}</b><small>beds occupied</small></span><span><ClipboardList size={18}/><b>{session.farm.orders.length}</b><small>confirmed orders</small></span><span><CalendarDays size={18}/><b>{session.farm.horizon_days} days</b><small>planning horizon</small></span></div></header>
    <div className="record-ledger"><div><h3>Confirmed customer orders</h3>{session.farm.orders.slice(0, 5).map(order => <p key={order.id}><b>{crop(order.crop_id)}</b><span>{number(order.quantity_kg)} kg by {civil(order.due_date)}</span></p>)}{session.farm.orders.length > 5 && <small>+ {session.farm.orders.length - 5} more confirmed records</small>}</div><div><h3>Current growing space</h3>{session.farm.beds.slice(0, 8).map(bed => <p key={bed.id}><b>{bed.name}</b><span>{bed.stage === 'empty' ? 'Available' : `${crop(bed.crop_id)} · ${bed.stage}`}</span></p>)}</div></div>
    <p className="demand-disclosure"><b>Expected future demand</b> is calculated separately from these confirmed customer orders. A later scenario can change the residual forecast without rewriting history or bookings.</p>
    <details><summary>Record provenance and limits</summary><p>These project-authored synthetic records demonstrate the planning workflow. Forecast demand is an estimate; confirmed orders remain separate commitments. Results are simulations, not instructions for real farm operations.</p><code>Session {session.id} · input {session.input_hash}</code></details>
  </section>
}

function PlanningResults({ session }: { session: PlanningSession }) {
  const strategies = session.result?.strategies || []
  return <section className="guided-section"><header><div><p className="kicker">2 · Calculate schedules</p><h2>Three feasible priorities</h2><p>Compare fulfillment and waste together. No option is presented as a guaranteed improvement.</p></div></header><div className="guided-strategies">{strategies.map(strategy => <StrategyCard key={strategy.id} strategy={strategy} selected={strategy.id === session.selected_strategy_id}/>)}</div></section>
}
function StrategyCard({ strategy, selected }: { strategy: Strategy; selected: boolean }) { const m = strategy.metrics; return <article className={`guided-strategy ${selected ? 'is-selected' : ''}`}><span>{selected ? 'Selected by policy' : strategy.status.replaceAll('_', ' ')}</span><h3>{strategy.name}</h3><p>{strategy.description}</p><MetricGrid metrics={m}/><details><summary>Planting schedule · {strategy.allocations.length} allocations</summary>{strategy.allocations.slice(0, 6).map((a, i) => <p key={a.id || i}><b>{a.crop_id}</b> · {a.bed_id} · sow {civil(a.sow_date)} · harvest {civil(a.harvest_date)}</p>)}</details></article> }
function MetricGrid({ metrics }: { metrics: StrategyMetrics | Record<string, unknown> }) { const shortfall = 'booked_shortfall_kg' in metrics ? n(metrics, 'booked_shortfall_kg') : n(metrics, 'shortfall_kg'); return <div className="guided-metrics"><span><b>{pct(n(metrics, 'fill_rate'))}</b><small>booked fulfillment</small></span><span><b>{number(shortfall)} kg</b><small>unmet demand</small></span><span><b>{number(n(metrics, 'waste_kg'))} kg</b><small>expired waste</small></span><span><b>{number(n(metrics, 'closing_stock_kg'))} kg</b><small>remaining stock</small></span><span><b>${money(n(metrics, 'margin_sgd'))}</b><small>simulated margin</small></span></div> }

function CouncilCheckpoint({ session, busy, onReview }: { session: PlanningSession; busy: string; onReview: () => void }) {
  const status = session.review?.status || 'NOT_REQUESTED', reviewed = !['NOT_REQUESTED', 'not_requested', ''].includes(status)
  return <section className="guided-section council-checkpoint"><header><div><p className="kicker">3 · Explicit Council checkpoint</p><h2>Ask specialists to explain the tradeoffs</h2><p>Numerical schedules stay available if AI is unavailable. Council findings are advisory and may only cite verified comparison facts.</p></div>{!reviewed && <button className="button button--coral" disabled={Boolean(busy)} onClick={onReview}><Users size={17}/> Review with Council</button>}</header><div className="guided-advisors">{ADVISORS.map(advisor => <span key={advisor.id}><img src={editionPath(`/art/advisors/${advisor.id}.svg`)} alt=""/><b>{advisor.name}</b><small>{advisor.role}</small></span>)}</div>{reviewed && <div className="review-result"><b>Council status: {status.replaceAll('_', ' ').toLowerCase()}</b>{session.review?.findings?.length ? session.review.findings.map((item, index) => <div key={index}><strong>{String(item.role || 'Council role').replaceAll('_', ' ')}</strong>{Array.isArray(item.rendered_facts) && item.rendered_facts.map((fact, factIndex) => <p key={factIndex}>{String(fact)}</p>)}<p>{String(item.rendered_interpretation || item.statement || item.summary || item.status || 'Recorded finding')}</p></div>) : <p>The review record is preserved. Numerical comparisons remain authoritative.</p>}</div>}</section>
}

function Simulation({ session, busy, onAdvance }: { session: PlanningSession; busy: string; onAdvance: (days: 1 | 7) => void }) { const sim = session.simulation; return <section className="guided-section"><header><div><p className="kicker">4 · Simulate the selected plan</p><h2>{sim ? `Farm clock · ${civil(sim.clock_date)}` : 'See the planting schedule unfold'}</h2><p>Advancing records simulated farm events. It does not perform or authorize real work.</p></div><div className="guided-buttons"><button className="button button--cream" disabled={Boolean(busy)} onClick={() => onAdvance(1)}><Play size={16}/> {sim ? '+1 day' : 'Start · 1 day'}</button><button className="button button--forest" disabled={Boolean(busy)} onClick={() => onAdvance(7)}><Play size={16}/> {sim ? '+7 days' : 'Start · 1 week'}</button></div></header>{sim && <><div className="simulation-totals"><div><Leaf/><span><strong>{number(sim.totals.harvest_kg)} kg</strong><small>harvested</small></span></div><div><Warehouse/><span><strong>{number(sim.totals.delivered_kg)} kg</strong><small>delivered</small></span></div><div><AlertTriangle/><span><strong>{number(sim.totals.disposed_kg)} kg</strong><small>expired waste</small></span></div><div><Scale/><span><strong>${money(sim.cash_sgd)}</strong><small>cash balance</small></span></div></div><div className="guided-bed-strip">{sim.beds.slice(0, 12).map(bed => <span key={bed.id} className={bed.stage}><img src={bed.crop_id ? editionPath(`/art/crops/${bed.crop_id}-growing.svg`) : editionPath('/art/empty-bed.svg')} alt="" onError={e => { e.currentTarget.style.display = 'none' }}/><b>{bed.name}</b><small>{bed.stage}</small></span>)}</div></>}</section> }

type DisruptionProps = { crops: Crop[]; cropId: string; setCropId: (s:string)=>void; date:string; endDate:string; demandPercent:number; setDemandPercent:(n:number)=>void; yieldPercent:number; setYieldPercent:(n:number)=>void; delayDays:number; setDelayDays:(n:number)=>void; orderOpen:boolean; setOrderOpen:(b:boolean)=>void; orderQty:number; setOrderQty:(n:number)=>void; orderPrice:number; setOrderPrice:(n:number)=>void; orderDate:string; setOrderDate:(s:string)=>void; busy:string; onRun:()=>void }
function DisruptionForm(p: DisruptionProps) { return <section className="guided-section disruption-form"><header><div><p className="kicker">5 · Introduce a change</p><h2>What changed since the saved plan?</h2><p>Expected demand, confirmed orders and seasonal production assumptions are separate inputs.</p></div></header><div className="assumption-grid"><label>Crop<select value={p.cropId} onChange={e => p.setCropId(e.target.value)}>{p.crops.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}</select></label><label><span>Expected future demand <b>{p.demandPercent}%</b></span><input type="range" min="50" max="150" step="5" value={p.demandPercent} onChange={e => p.setDemandPercent(Number(e.target.value))}/><small>Residual forecast only; history and bookings stay unchanged.</small></label><label><span>Seasonal yield assumption <b>{p.yieldPercent}%</b></span><input type="range" min="50" max="100" step="5" value={p.yieldPercent} onChange={e => p.setYieldPercent(Number(e.target.value))}/><small>Synthetic sensitivity for sheltered hydroponics.</small></label><label><span>Harvest delay <b>{p.delayDays} days</b></span><input type="range" min="0" max="14" value={p.delayDays} onChange={e => p.setDelayDays(Number(e.target.value))}/><small>Applies {civil(p.date)}–{civil(p.endDate)}.</small></label></div><button className="order-toggle" aria-expanded={p.orderOpen} onClick={() => p.setOrderOpen(!p.orderOpen)}><PackagePlus size={18}/><span><b>Add a confirmed customer order</b><small>This is separate from expected future demand.</small></span></button>{p.orderOpen && <div className="order-fields"><label>Due date<input type="date" value={p.orderDate} onChange={e => p.setOrderDate(e.target.value)}/></label><label>Quantity (kg)<input type="number" min="0.1" step="0.1" value={p.orderQty} onChange={e => p.setOrderQty(Number(e.target.value))}/></label><label>Price (SGD/kg)<input type="number" min="0" step="0.1" value={p.orderPrice} onChange={e => p.setOrderPrice(Number(e.target.value))}/></label></div>}<div className="disruption-submit"><CloudSun/><p><b>Fair comparison</b><small>The saved schedule and all replanned strategies will face these exact same changed conditions.</small></p><button className="button button--forest" disabled={Boolean(p.busy) || !p.cropId} onClick={p.onRun}><RefreshCw size={16}/> Compare and replan</button></div></section> }

function Comparison({ session }: { session: PlanningSession }) {
  const entries = comparisonEntries(session)
  const physical = comparisonChanges(session)
  return <section className="guided-section comparison-result"><header><div><p className="kicker">Same-condition comparison</p><h2>Keep the saved schedule or replan?</h2><p>Every arm uses the same changed demand, seasonal assumptions, opening inventory and planning horizon.</p></div></header>{entries.length ? <div className="comparison-grid">{entries.map(([name, metrics], index) => <article key={name} className={index === 0 ? 'is-retained' : ''}><span>{index === 0 ? 'Saved schedule under disruption' : 'Replanned under disruption'}</span><h3>{name}</h3><MetricGrid metrics={metrics}/></article>)}</div> : <p className="empty-note">The comparison completed without a displayable metric summary. Its evidence remains stored in this session.</p>} {!!physical.length && <div className="physical-changes"><h3>What physically changes</h3>{physical.slice(0, 12).map((item, index) => <p key={index}><Sprout size={15}/><b>{item.operation}</b><span>{item.label}</span></p>)}</div>}</section>
}

function comparisonEntries(session: PlanningSession): Array<[string, Record<string, unknown>]> { const raw = session.result?.comparisons; const values: Array<[string, Record<string, unknown>]> = []; if (Array.isArray(raw)) { const first = raw[0]; if (first?.baseline_metrics) values.push(['Saved schedule', first.baseline_metrics as Record<string, unknown>]); raw.forEach((item, i) => values.push([String(item.policy || item.name || item.strategy_name || item.strategy_id || `Option ${i+1}`), ((item.scenario_metrics || item.metrics || item) as Record<string, unknown>)])) } else if (raw) Object.entries(raw).forEach(([name,item]) => values.push([name, ((item.metrics || item) as Record<string, unknown>)])); if (!values.length && session.result?.retained_strategy) { const retained=session.result.retained_strategy as Record<string,unknown>; values.push([String(retained.name || 'Saved schedule'), ((retained.metrics || retained) as Record<string,unknown>)]) } return values }
function comparisonChanges(session: PlanningSession) { const raw = session.result?.comparisons; if (!Array.isArray(raw)) return []; const rows: Array<{operation:string;label:string}> = []; for (const comparison of raw) { const policy=String(comparison.policy || 'Plan'), changes=comparison.allocation_changes as {added?:Array<Record<string,unknown>>;removed?:Array<Record<string,unknown>>;changed?:Array<Record<string,unknown>>} | undefined; changes?.added?.forEach(item=>rows.push({operation:`${policy} adds`,label:`${String(item.crop_id || 'crop')} in ${String(item.bed_id || 'a bed')}`})); changes?.removed?.forEach(item=>rows.push({operation:`${policy} removes`,label:`${String(item.crop_id || 'crop')} from ${String(item.bed_id || 'a bed')}`})); changes?.changed?.forEach(item=>rows.push({operation:`${policy} changes`,label:`allocation ${String(item.allocation_id || '')}`})) } return rows }
function n(o: Record<string, unknown>, key: string) { const value = Number(o[key] ?? 0); return Number.isFinite(value) ? value : 0 }
function number(value: unknown) { const n = Number(value || 0); return n.toLocaleString('en-SG', { maximumFractionDigits: 2 }) }
function money(value: unknown) { const n = Number(value || 0); return n.toLocaleString('en-SG', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function pct(value: number) { return `${(value <= 1 ? value * 100 : value).toFixed(1)}%` }
function civil(value?: string | null) { if (!value) return 'not started'; const date = value.slice(0,10).split('-'); return date.length === 3 ? `${date[2]} ${['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][Number(date[1])-1]} ${date[0]}` : value }
function addDays(value: string, days: number) { const date = new Date(`${value.slice(0,10)}T00:00:00Z`); date.setUTCDate(date.getUTCDate()+days); return date.toISOString().slice(0,10) }
function message(value: unknown, fallback: string) { return value instanceof Error ? value.message : fallback }
