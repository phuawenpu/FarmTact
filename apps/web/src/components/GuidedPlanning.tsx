import { AlertTriangle, ArrowRight, CalendarDays, Check, ClipboardList, CloudSun, Leaf, LoaderCircle, PackagePlus, Play, RefreshCw, Scale, Sprout, Users, Warehouse, X } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import type { Crop, Strategy, StrategyMetrics } from '../lib/types'
import { ADVISORS } from '../lib/game'
import { editionPath } from '../lib/edition'
import { planningApi, rememberPlanningSession, rememberedPlanningSession, type OrderChange, type PlanningAssumptions, type PlanningSession } from '../lib/planning'
import { CropArt } from './Visuals'

const terminal = new Set(['COMPLETED', 'FAILED', 'CANCELLED'])
const steps = [
  ['records', 'Review records'], ['planning', 'Calculate schedules'], ['review', 'Council review'], ['simulation', 'Simulate plan'], ['comparison', 'Change & compare'],
] as const

export function GuidedPlanning({ crops, onOpenSetup }: { crops: Crop[]; onOpenSetup: () => void }) {
  const [session, setSession] = useState<PlanningSession | null>(null)
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(''), [error, setError] = useState('')
  const [demandPercent, setDemandPercent] = useState(100), [yieldPercent, setYieldPercent] = useState(100), [delayDays, setDelayDays] = useState(0)
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
  useEffect(()=>{const demand=session?.assumptions?.future_demand?.[0],seasonal=session?.assumptions?.seasonal?.[0],order=session?.assumptions?.order_changes?.[0];if(demand){setDemandPercent(demand.percent);setCropId(demand.crop_id)}if(seasonal){setYieldPercent(seasonal.yield_percent);setDelayDays(seasonal.delay_days);setCropId(seasonal.crop_id)}if(order){setOrderOpen(true);setOrderQty(Number(order.quantity_kg||0));setOrderPrice(Number(order.price_sgd_per_kg||0));setOrderDate(order.due_date||'')}},[session?.id,session?.input_hash])

  useEffect(() => {
    if (!session?.job || terminal.has(session.job.status) || !['QUEUED', 'RUNNING'].includes(session.job.status)) return
    const id = session.id
    const timer = window.setInterval(() => { void planningApi.get(id).then(next => { setSession(next); if (terminal.has(next.job?.status || '')) setBusy('') }).catch(() => {}) }, 2500)
    return () => window.clearInterval(timer)
  }, [session?.id, session?.job?.id, session?.job?.status])

  const mutate = async (label: string, action: (current: PlanningSession) => Promise<PlanningSession>) => {
    if (!session) return
    setBusy(label); setError('')
    try { const next = await action(session); setSession(next); rememberPlanningSession(next.id); if (!['QUEUED', 'RUNNING'].includes(next.job?.status || '')) setBusy('') }
    catch (caught) { setBusy(''); setError(message(caught, `Could not ${label}.`)) }
  }
  const newMission=async()=>{setBusy('start new mission');setError('');try{const next=await planningApi.create();rememberPlanningSession(next.id);setSession(next);setDemandPercent(100);setYieldPercent(100);setDelayDays(0);setOrderOpen(false);setOrderDate('')}catch(caught){setError(message(caught,'Could not start a new mission from the current records.'))}finally{setBusy('')}}
  const date = session?.simulation?.clock_date ? addDays(session.simulation.clock_date, 1) : session?.farm.planning_date || singaporeDate(session?.farm.cutoff) || singaporeToday()
  const endDate = session?.simulation?.end_date || addDays(date, Math.min(session?.farm.horizon_days || 56, 56) - 1)
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

    <FarmRecords session={session} crops={crops} busy={busy} onNewMission={()=>void newMission()} onOpenSetup={onOpenSetup}/>
    <GuidedFarmBoard session={session} crops={crops}/>

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

type GuidedBedState={crop_id?:string;stage?:string;sow_date?:string;transplant_date?:string;harvest_date?:string;expected_kg?:unknown}
function GuidedFarmBoard({ session, crops }: { session: PlanningSession; crops: Crop[] }) {
  const [selectedId,setSelectedId]=useState(session.farm.beds[0]?.id || '')
  const chosen=session.result?.strategies?.find(item=>item.id===session.selected_strategy_id)
  const displayDate=session.farm.planning_date||singaporeDate(session.farm.cutoff)
  const allocations=new Map<string,GuidedBedState>()
  for(const item of [...(chosen?.allocations||[])].filter(value=>value.harvest_date>=displayDate).sort((left,right)=>left.sow_date.localeCompare(right.sow_date)))if(!allocations.has(item.bed_id))allocations.set(item.bed_id,item)
  const simulated=new Map<string,GuidedBedState>((session.simulation?.beds||[]).map(item=>[item.id,item]))
  const raw=session.farm as typeof session.farm&{batches?:Array<{id:string;bed_id:string;recipe_id:string;sow_date:string;transplant_date:string;harvest_date:string;expected_marketable_kg?:number}>;recipes?:Array<{id:string;crop_id:string}>}
  const recipeCrop=new Map((raw.recipes||[]).map(item=>[item.id,item.crop_id]))
  const batches=new Map((raw.batches||[]).map(item=>[item.bed_id,{...item,crop_id:recipeCrop.get(item.recipe_id),expected_kg:item.expected_marketable_kg}]))
  const state=(bedId:string)=>simulated.get(bedId)||allocations.get(bedId)||batches.get(bedId)
  const highlighted=comparisonBedIds(session)
  const selected=session.farm.beds.find(item=>item.id===selectedId), selectedState=selected?state(selected.id):undefined
  return <section className="guided-section guided-farm-board"><header><div><p className="kicker">Farm board · schedule made physical</p><h2>Growing space and planting work</h2><p>{session.stage==='comparison'?'Highlighted beds change when the farm replans.':'Choose a bed to inspect its saved or selected planting schedule.'}</p></div></header><div className="guided-farm-layout"><div className="guided-farm-beds">{session.farm.beds.map(bed=>{const item=state(bed.id),stage=bedVisualStage(item,session.simulation?.clock_date||displayDate),crop=crops.find(value=>value.id===item?.crop_id);return <button key={bed.id} className={`${highlighted.has(bed.id)?'is-affected':''} ${selectedId===bed.id?'is-selected':''}`} onClick={()=>setSelectedId(bed.id)} aria-label={`${bed.name}, ${crop?.label||'available bed'}, ${stage}${highlighted.has(bed.id)?', changed by replanning':''}`}><CropArt cropId={item?.crop_id} color={crop?.color} stage={stage} compact/><span><b>{bed.name}</b><small>{crop?.label||'Available'} · {stage}</small></span>{highlighted.has(bed.id)&&<em>Changed</em>}</button>})}</div><aside aria-live="polite"><p className="kicker">Selected bed</p><h3>{selected?.name||'Choose a bed'}</h3>{selectedState?<><b>{crops.find(item=>item.id===selectedState.crop_id)?.label||selectedState.crop_id}</b><p>Stage: {bedVisualStage(selectedState,session.simulation?.clock_date||displayDate)}<br/>Sow {civil(selectedState.sow_date)}<br/>Transplant {civil(selectedState.transplant_date)}<br/>Harvest {civil(selectedState.harvest_date)}</p>{selectedState.expected_kg!==undefined&&<small>{number(selectedState.expected_kg)} kg expected · synthetic schedule</small>}</>:<p>This growing bed is available in the displayed schedule.</p>}</aside></div></section>
}

function FarmRecords({ session, crops, busy, onNewMission, onOpenSetup }: { session: PlanningSession; crops: Crop[]; busy:string; onNewMission:()=>void; onOpenSetup:()=>void }) {
  const crop = (id?: string) => crops.find(item => item.id === id)?.label || id || 'Unassigned'
  const raw = session.farm as typeof session.farm & { batches?: Array<{id:string;bed_id:string;recipe_id:string;sow_date:string;transplant_date:string;harvest_date:string}>; recipes?: Array<{id:string;crop_id:string}> }
  const recipeCrop = new Map((raw.recipes || []).map(item => [item.id, item.crop_id]))
  const selected = session.result?.strategies?.find(item => item.id === session.selected_strategy_id)
  const planned = new Map((selected?.allocations || []).map(item => [item.bed_id, { crop_id:item.crop_id, stage:'planned', harvest_date:item.harvest_date }]))
  const batches = new Map((raw.batches || []).map(item => [item.bed_id, { crop_id:recipeCrop.get(item.recipe_id), stage:batchStage(item, session.farm.planning_date || singaporeDate(session.farm.cutoff)), harvest_date:item.harvest_date }]))
  const bedState = (id:string) => batches.get(id) || planned.get(id)
  const active = session.farm.beds.filter(bed => Boolean(bedState(bed.id)))
  return <section className="guided-section records-section"><header><div><p className="kicker">1 · Review manual-style records</p><h2>{session.farm.name}</h2><p>{session.farm.location} · planning from {civil(session.farm.planning_date || session.farm.cutoff)}</p></div><div className="records-summary"><span><Warehouse size={18}/><b>{active.length}/{session.farm.beds.length}</b><small>beds occupied</small></span><span><ClipboardList size={18}/><b>{session.farm.orders.length}</b><small>confirmed orders</small></span><span><CalendarDays size={18}/><b>{session.farm.horizon_days} days</b><small>planning horizon</small></span></div></header>
    <div className="record-ledger"><div><h3>Confirmed customer orders</h3>{session.farm.orders.slice(0, 5).map(order => <p key={order.id}><b>{crop(order.crop_id)}</b><span>{number(order.quantity_kg)} kg by {civil(order.due_date)}</span></p>)}{session.farm.orders.length > 5 && <small>+ {session.farm.orders.length - 5} more confirmed records</small>}</div><div><h3>Current growing space</h3>{session.farm.beds.slice(0, 8).map(bed => { const state=bedState(bed.id); return <p key={bed.id}><b>{bed.name}</b><span>{state ? `${crop(state.crop_id)} · ${state.stage}` : 'Available'}</span></p>})}</div></div>
    <p className="demand-disclosure"><b>Expected future demand</b> is calculated separately from these confirmed customer orders. A later scenario can change the residual forecast without rewriting history or bookings.</p>
    <div className="record-actions"><button className="button button--cream" disabled={Boolean(busy)} onClick={onNewMission}><RefreshCw size={16}/> New mission from current records</button><button className="text-button" onClick={onOpenSetup}>Import or update records <ArrowRight size={15}/></button></div>
    <details><summary>Record provenance and limits</summary><p>These project-authored synthetic records demonstrate the planning workflow. Forecast demand is an estimate; confirmed orders remain separate commitments. Results are simulations, not instructions for real farm operations.</p><code>Session {session.id} · input {session.input_hash}</code></details>
  </section>
}

function PlanningResults({ session }: { session: PlanningSession }) {
  const strategies = session.result?.strategies || []
  return <section className="guided-section"><header><div><p className="kicker">2 · Calculate schedules</p><h2>Three feasible priorities</h2><p>Compare fulfillment and waste together. No option is presented as a guaranteed improvement.</p></div></header><div className="guided-strategies">{strategies.map(strategy => <StrategyCard key={strategy.id} strategy={strategy} selected={strategy.id === session.selected_strategy_id}/>)}</div></section>
}
function StrategyCard({ strategy, selected }: { strategy: Strategy; selected: boolean }) { const m = strategy.metrics; return <article className={`guided-strategy ${selected ? 'is-selected' : ''}`}><span>{selected ? 'Selected by policy' : strategy.status.replaceAll('_', ' ')}</span><h3>{strategy.name}</h3><p>{strategy.description}</p><MetricGrid metrics={m}/><details><summary>Planting schedule · {strategy.allocations.length} allocations</summary>{strategy.allocations.slice(0, 6).map((a, i) => <p key={a.id || i}><b>{a.crop_id}</b> · {a.bed_id} · sow {civil(a.sow_date)} · harvest {civil(a.harvest_date)}</p>)}</details></article> }
function MetricGrid({ metrics }: { metrics: StrategyMetrics | Record<string, unknown> }) { const requested=n(metrics,'booked_requested_kg'), delivered=n(metrics,'booked_delivered_kg'), hasBooked='booked_requested_kg' in metrics; const shortfall=hasBooked?Math.max(0,requested-delivered):n(metrics,'shortfall_kg'); const bookedLabel=hasBooked?(requested>0?pct(delivered/requested):'No bookings'):pct(n(metrics,'fill_rate')); return <div className="guided-metrics"><span><b>{bookedLabel}</b><small>{hasBooked?'booked fulfillment':'overall fulfillment'}</small></span><span><b>{number(shortfall)} kg</b><small>{hasBooked?'unmet booked demand':'unmet demand'}</small></span><span><b>{number(n(metrics, 'waste_kg'))} kg</b><small>expired waste</small></span><span><b>{number(n(metrics, 'closing_stock_kg'))} kg</b><small>remaining stock</small></span><span><b>${money(n(metrics, 'margin_sgd'))}</b><small>simulated margin</small></span></div> }

function CouncilCheckpoint({ session, busy, onReview }: { session: PlanningSession; busy: string; onReview: () => void }) {
  const status = session.review?.status || 'NOT_REQUESTED', reviewed = !['NOT_REQUESTED', 'not_requested', ''].includes(status)
  return <section className="guided-section council-checkpoint"><header><div><p className="kicker">3 · Explicit Council checkpoint</p><h2>Ask specialists to explain the tradeoffs</h2><p>Numerical schedules stay available if AI is unavailable. Council findings are advisory and may only cite verified comparison facts.</p></div>{!reviewed && <button className="button button--coral" disabled={Boolean(busy)} onClick={onReview}><Users size={17}/> Review with Council</button>}</header><div className="guided-advisors">{ADVISORS.map(advisor => <span key={advisor.id}><img src={editionPath(`/art/advisors/${advisor.id}.svg`)} alt=""/><b>{advisor.name}</b><small>{advisor.role}</small></span>)}</div>{reviewed && <div className="review-result"><b>Council status: {status.replaceAll('_', ' ').toLowerCase()}</b>{session.review?.findings?.length ? session.review.findings.map((item, index) => {const suggestion=session.result?.strategies?.find(strategy=>strategy.id===item.proposed_strategy_id);return <div key={index}><strong>{String(item.role || 'Council role').replaceAll('_', ' ')}</strong>{suggestion&&<span className="council-suggestion">Advisory suggestion: {suggestion.name}{suggestion.id===session.selected_strategy_id?' · also selected by numerical policy':' · differs from numerical policy selection'}</span>}{Array.isArray(item.rendered_facts) && item.rendered_facts.map((fact, factIndex) => <p key={factIndex}>{String(fact)}</p>)}<p>{String(item.rendered_interpretation || item.statement || item.summary || item.status || 'Recorded finding')}</p></div>}) : <p>The review record is preserved. Numerical comparisons remain authoritative.</p>}</div>}</section>
}

function Simulation({ session, busy, onAdvance }: { session: PlanningSession; busy: string; onAdvance: (days: 1 | 7) => void }) { const sim = session.simulation, chosen=session.result?.strategies?.find(item=>item.id===session.selected_strategy_id), feasible=Boolean(chosen&&chosen.status==='FEASIBLE'&&!chosen.violations.length), remaining=sim?daysBetween(sim.clock_date||addDays(sim.start_date,-1),sim.end_date):session.farm.horizon_days; return <section className="guided-section"><header><div><p className="kicker">4 · Simulate the selected plan</p><h2>{sim ? `Farm clock · ${civil(sim.clock_date)}` : 'See the planting schedule unfold'}</h2><p>Advancing records simulated farm events. It does not perform or authorize real work.</p></div><div className="guided-buttons"><button className="button button--cream" disabled={Boolean(busy)||!feasible||remaining<1} onClick={() => onAdvance(1)}><Play size={16}/> {sim ? '+1 day' : 'Start · 1 day'}</button><button className="button button--forest" disabled={Boolean(busy)||!feasible||remaining<7} onClick={() => onAdvance(7)}><Play size={16}/> {sim ? '+7 days' : 'Start · 1 week'}</button></div></header>{!feasible&&<p className="empty-note">A feasible policy-selected schedule is required before simulation can start.</p>}{sim && <><div className="simulation-totals"><div><Leaf/><span><strong>{number(sim.totals.harvest_kg)} kg</strong><small>harvested</small></span></div><div><Warehouse/><span><strong>{number(sim.totals.delivered_kg)} kg</strong><small>delivered</small></span></div><div><AlertTriangle/><span><strong>{number(sim.totals.disposed_kg)} kg</strong><small>expired waste</small></span></div><div><Scale/><span><strong>${money(sim.cash_sgd)}</strong><small>cash balance</small></span></div></div><div className="guided-bed-strip">{sim.beds.slice(0, 12).map(bed => <span key={bed.id} className={bed.stage}><CropArt cropId={bed.crop_id} stage={bed.stage} compact/><b>{bed.name}</b><small>{bed.stage}</small></span>)}</div></>}</section> }

type DisruptionProps = { crops: Crop[]; cropId: string; setCropId: (s:string)=>void; date:string; endDate:string; demandPercent:number; setDemandPercent:(n:number)=>void; yieldPercent:number; setYieldPercent:(n:number)=>void; delayDays:number; setDelayDays:(n:number)=>void; orderOpen:boolean; setOrderOpen:(b:boolean)=>void; orderQty:number; setOrderQty:(n:number)=>void; orderPrice:number; setOrderPrice:(n:number)=>void; orderDate:string; setOrderDate:(s:string)=>void; busy:string; onRun:()=>void }
function DisruptionForm(p: DisruptionProps) { return <section className="guided-section disruption-form"><header><div><p className="kicker">5 · Introduce a change</p><h2>What changed since the saved plan?</h2><p>Expected demand, confirmed orders and seasonal production assumptions are separate inputs.</p></div></header><div className="assumption-grid"><label>Crop<select value={p.cropId} onChange={e => p.setCropId(e.target.value)}>{p.crops.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}</select></label><label><span>Expected future demand <b>{p.demandPercent}%</b></span><input type="range" min="50" max="150" step="5" value={p.demandPercent} onChange={e => p.setDemandPercent(Number(e.target.value))}/><small>Residual forecast only; history and bookings stay unchanged.</small></label><label><span>Seasonal yield assumption <b>{p.yieldPercent}%</b></span><input type="range" min="50" max="100" step="5" value={p.yieldPercent} onChange={e => p.setYieldPercent(Number(e.target.value))}/><small>Synthetic sensitivity for sheltered hydroponics.</small></label><label><span>Harvest delay <b>{p.delayDays} days</b></span><input type="range" min="0" max="14" value={p.delayDays} onChange={e => p.setDelayDays(Number(e.target.value))}/><small>Applies {civil(p.date)}–{civil(p.endDate)}.</small></label></div><button className="order-toggle" aria-expanded={p.orderOpen} onClick={() => p.setOrderOpen(!p.orderOpen)}><PackagePlus size={18}/><span><b>Add a confirmed customer order</b><small>This is separate from expected future demand.</small></span></button>{p.orderOpen && <div className="order-fields"><label>Due date<input type="date" value={p.orderDate} onChange={e => p.setOrderDate(e.target.value)}/></label><label>Quantity (kg)<input type="number" min="0.1" step="0.1" value={p.orderQty} onChange={e => p.setOrderQty(Number(e.target.value))}/></label><label>Price (SGD/kg)<input type="number" min="0" step="0.1" value={p.orderPrice} onChange={e => p.setOrderPrice(Number(e.target.value))}/></label></div>}<div className="disruption-submit"><CloudSun/><p><b>Fair comparison</b><small>The saved schedule and all replanned strategies will face these exact same changed conditions.</small></p><button className="button button--forest" disabled={Boolean(p.busy) || !p.cropId} onClick={p.onRun}><RefreshCw size={16}/> Compare and replan</button></div></section> }

function Comparison({ session }: { session: PlanningSession }) {
  const entries = comparisonEntries(session)
  const physical = comparisonChanges(session)
  return <section className="guided-section comparison-result"><header><div><p className="kicker">Same-condition comparison</p><h2>Keep the saved schedule or replan?</h2><p>Every arm uses the same changed demand, seasonal assumptions, opening inventory and planning horizon.</p></div></header>{entries.length ? <div className="comparison-grid">{entries.map(([name, metrics], index) => <article key={name} className={index === 0 ? 'is-retained' : ''}><span>{index === 0 ? 'Saved schedule under disruption' : 'Replanned under disruption'}</span><h3>{name}</h3><MetricGrid metrics={metrics}/></article>)}</div> : <p className="empty-note">The comparison completed without a displayable metric summary. Its evidence remains stored in this session.</p>} {!!physical.length && <div className="physical-changes"><h3>What physically changes</h3>{physical.slice(0, 12).map((item, index) => <p key={index}><Sprout size={15}/><b>{item.operation}</b><span>{item.label}</span></p>)}</div>}</section>
}

function comparisonEntries(session: PlanningSession): Array<[string, Record<string, unknown>]> { const raw = session.result?.comparisons; const values: Array<[string, Record<string, unknown>]> = []; if (Array.isArray(raw)) { const first = raw[0]; if (first?.baseline_metrics) values.push(['Saved schedule', first.baseline_metrics as Record<string, unknown>]); raw.forEach((item, i) => values.push([String(item.policy || item.name || item.strategy_name || item.strategy_id || `Option ${i+1}`), ((item.scenario_metrics || item.metrics || item) as Record<string, unknown>)])) } else if (raw) Object.entries(raw).forEach(([name,item]) => values.push([name, ((item.metrics || item) as Record<string, unknown>)])); if (!values.length && session.result?.retained_strategy) { const retained=session.result.retained_strategy as Record<string,unknown>; values.push([String(retained.name || 'Saved schedule'), ((retained.metrics || retained) as Record<string,unknown>)]) } return values }
function comparisonChanges(session: PlanningSession) { const raw = session.result?.comparisons; if (!Array.isArray(raw)) return []; const rows: Array<{operation:string;label:string}> = []; for (const comparison of raw) { const policy=String(comparison.policy || 'Plan'), changes=comparison.allocation_changes as {added?:Array<Record<string,unknown>>;removed?:Array<Record<string,unknown>>;changed?:Array<Record<string,unknown>>} | undefined; changes?.added?.forEach(item=>rows.push({operation:`${policy} adds`,label:`${String(item.crop_id || 'crop')} in ${String(item.bed_id || 'a bed')}`})); changes?.removed?.forEach(item=>rows.push({operation:`${policy} removes`,label:`${String(item.crop_id || 'crop')} from ${String(item.bed_id || 'a bed')}`})); changes?.changed?.forEach(item=>rows.push({operation:`${policy} changes`,label:`allocation ${String(item.allocation_id || '')}`})) } return rows }
function comparisonBedIds(session:PlanningSession){const ids=new Set<string>(),raw=session.result?.comparisons;if(!Array.isArray(raw))return ids;for(const comparison of raw){const changes=comparison.allocation_changes as {added?:Array<Record<string,unknown>>;removed?:Array<Record<string,unknown>>;changed?:Array<{fields?:Record<string,{before?:unknown;after?:unknown}>}>}|undefined;for(const item of [...(changes?.added||[]),...(changes?.removed||[])])if(item.bed_id)ids.add(String(item.bed_id));for(const item of changes?.changed||[]){const bed=item.fields?.bed_id;if(bed?.before)ids.add(String(bed.before));if(bed?.after)ids.add(String(bed.after))}}return ids}
function n(o: Record<string, unknown>, key: string) { const value = Number(o[key] ?? 0); return Number.isFinite(value) ? value : 0 }
function number(value: unknown) { const n = Number(value || 0); return n.toLocaleString('en-SG', { maximumFractionDigits: 2 }) }
function money(value: unknown) { const n = Number(value || 0); return n.toLocaleString('en-SG', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }
function pct(value: number) { return `${(value <= 1 ? value * 100 : value).toFixed(1)}%` }
function civil(value?: string | null) { if (!value) return 'not started'; const date = value.slice(0,10).split('-'); return date.length === 3 ? `${date[2]} ${['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'][Number(date[1])-1]} ${date[0]}` : value }
function addDays(value: string, days: number) { const date = new Date(`${value.slice(0,10)}T00:00:00Z`); date.setUTCDate(date.getUTCDate()+days); return date.toISOString().slice(0,10) }
function singaporeDate(value?: string | null) { if (!value) return ''; const parsed=new Date(value); if (Number.isNaN(parsed.getTime())) return ''; const parts=new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Singapore',year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(parsed); const get=(type:string)=>parts.find(part=>part.type===type)?.value||''; return `${get('year')}-${get('month')}-${get('day')}` }
function singaporeToday() { return singaporeDate(new Date().toISOString()) }
function batchStage(batch:{sow_date:string;transplant_date:string;harvest_date:string}, day:string) { return day<batch.sow_date?'scheduled':day<batch.transplant_date?'nursery':day<=batch.harvest_date?'growing':'harvested' }
function bedVisualStage(item:GuidedBedState|undefined,day:string){if(!item||!item.crop_id)return'empty';if(typeof item.stage==='string')return item.stage;if(day<String(item.sow_date))return'future';if(day<String(item.transplant_date))return'nursery';if(day===String(item.harvest_date))return'ready';if(day<String(item.harvest_date))return'growing';return'harvested'}
function daysBetween(start:string,end:string){return Math.max(0,Math.round((Date.parse(`${end.slice(0,10)}T00:00:00Z`)-Date.parse(`${start.slice(0,10)}T00:00:00Z`))/86400000))}
function message(value: unknown, fallback: string) { return value instanceof Error ? value.message : fallback }
