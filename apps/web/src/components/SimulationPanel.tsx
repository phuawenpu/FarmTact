import { CalendarClock, CheckCircle2, FastForward, History, PackageOpen, RefreshCw, Sprout, WalletCards } from 'lucide-react'
import { useCallback, useEffect, useMemo, useState } from 'react'
import { api, type SimulationEvent, type SimulationWorld } from '../lib/api'
import type { Crop, Run } from '../lib/types'
import { CropArt, formatDate, formatMoney, StatusPill } from './Visuals'

function daysBetween(start: string, end: string) { return Math.round((Date.parse(`${end}T00:00:00Z`) - Date.parse(`${start}T00:00:00Z`)) / 86400000) }
function number(value: unknown) { const parsed = Number(value); return Number.isFinite(parsed) ? parsed : 0 }

export function SimulationPanel({ run, crops }: { run: Run | null; crops: Crop[] }) {
  const [world, setWorld] = useState<SimulationWorld | null>(null)
  const [events, setEvents] = useState<SimulationEvent[]>([])
  const [loading, setLoading] = useState(true), [busy, setBusy] = useState(''), [error, setError] = useState('')
  const cropMap = useMemo(() => new Map(crops.map(crop => [crop.id, crop])), [crops])

  const refresh = useCallback(async (id: string) => {
    const [next, log] = await Promise.all([api.simulation(id), api.simulationEvents(id)])
    setWorld(next); setEvents(log.events)
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true); setError(''); setWorld(null); setEvents([])
    void (async () => {
      try {
        if (!run || run.shared_demo) return
        const summaries = await api.simulations(), match = summaries.find(item => item.run_id === run.id)
        if (match && !cancelled) await refresh(match.id)
      } catch (reason) { if (!cancelled) setError(reason instanceof Error ? reason.message : 'Recorded simulation could not be loaded.') }
      finally { if (!cancelled) setLoading(false) }
    })()
    return () => { cancelled = true }
  }, [run?.id, run?.shared_demo, refresh])

  const mutate = async (kind: 'create' | 'day' | 'week' | 'replan') => {
    if (!run) return
    setBusy(kind); setError('')
    try {
      const next = kind === 'create' ? await api.createSimulation(run.id)
        : kind === 'replan' ? await api.replanSimulation(world!.id, world!.revision)
          : await api.advanceSimulation(world!.id, world!.revision, kind === 'week' ? 7 : 1)
      setWorld(next); await refresh(next.id)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'The recorded simulation action failed.') }
    finally { setBusy('') }
  }

  const accepted = run?.status.toLowerCase() === 'accepted_for_simulation' && Boolean(run.accepted_strategy_id)
  const remaining = world ? daysBetween(world.clock_date || new Date(Date.parse(`${world.start_date}T00:00:00Z`) - 86400000).toISOString().slice(0, 10), world.end_date) : 0
  const canAdvance = Boolean(world && world.status !== 'COMPLETED' && remaining > 0)
  const canReplan = Boolean(world?.clock_date && remaining >= 7 && world.status !== 'COMPLETED')
  const inventoryKg = world?.inventory.reduce((sum, lot) => sum + number(lot.quantity_kg), 0) || 0
  const recent = [...events].reverse().slice(0, 12)

  return <section className="section-block simulation-panel" aria-labelledby="recorded-simulation-title">
    <div className="section-heading"><div><p className="kicker">Recorded synthetic execution</p><h2 id="recorded-simulation-title">Walk the accepted plan forward</h2></div>{world && <StatusPill status={world.status} />}</div>
    <p className="simulation-disclosure"><History size={17}/> This clock changes only when an advance action is recorded. The farm-map date slider is a static plan preview and never creates these events.</p>
    {loading ? <p className="muted-copy">Looking for a recorded simulation…</p> : !world ? <div className="simulation-start">
      <div><strong>{accepted ? 'Ready to create an isolated simulation' : 'An accepted current mission is required'}</strong><p>{run?.shared_demo ? 'Shared replay cannot own a simulation. Start a current farm mission first.' : accepted ? 'This copies the accepted strategy into a tenant-owned synthetic world. No real task or provider call occurs.' : 'Run the current farm mission through acceptance, then return here.'}</p></div>
      <button className="button button--forest" disabled={!accepted || !!busy || Boolean(run?.shared_demo)} onClick={() => void mutate('create')}><Sprout size={17}/>{busy === 'create' ? 'Creating…' : 'Create recorded simulation'}</button>
    </div> : <>
      <div className="simulation-clock">
        <div><CalendarClock size={22}/><span><small>Recorded through</small><strong>{world.clock_date ? formatDate(world.clock_date) : 'Not started'}</strong><em>{remaining} days remain</em></span></div>
        <div className="simulation-actions"><button className="button button--cream" disabled={!canAdvance || !!busy} onClick={() => void mutate('day')}><FastForward size={16}/>{busy === 'day' ? 'Recording…' : 'Advance 1 day'}</button><button className="button button--forest" disabled={!canAdvance || remaining < 7 || !!busy} onClick={() => void mutate('week')}><FastForward size={16}/>{busy === 'week' ? 'Recording…' : 'Advance 7 days'}</button><button className="button button--cream" disabled={!canReplan || !!busy} onClick={() => void mutate('replan')}><RefreshCw size={16}/>{busy === 'replan' ? 'Replanning…' : 'Replan remaining days'}</button></div>
      </div>
      <div className="simulation-totals">
        <div><PackageOpen/><span>Inventory<strong>{inventoryKg.toLocaleString('en-SG', { maximumFractionDigits: 2 })} kg</strong></span></div>
        <div><CheckCircle2/><span>Delivered<strong>{world.totals.delivered_kg.toLocaleString('en-SG')} kg</strong></span></div>
        <div><Sprout/><span>Harvested<strong>{world.totals.harvest_kg.toLocaleString('en-SG')} kg</strong></span></div>
        <div><WalletCards/><span>Cash<strong>{formatMoney(world.cash_sgd)}</strong><small>{formatMoney(world.revenue_sgd)} revenue · {formatMoney(world.cost_sgd)} cost</small></span></div>
      </div>
      <div className="simulation-layout">
        <div><h3>Bed state at the recorded clock</h3><div className="simulation-beds">{world.beds.map(bed => <article key={bed.id} className={`simulation-bed simulation-bed--${bed.stage}`}><CropArt cropId={bed.crop_id} color={bed.crop_id ? cropMap.get(bed.crop_id)?.color : undefined} stage={bed.stage} compact/><span><strong>{bed.name}</strong><small>{bed.crop_id ? cropMap.get(bed.crop_id)?.label || bed.crop_id.replaceAll('_', ' ') : 'Open bed'}</small><StatusPill status={bed.stage}/></span></article>)}</div></div>
        <div><h3>Recorded tasks and events</h3>{recent.length ? <ol className="simulation-events">{recent.map(event => <li key={event.sequence}><span>{event.sequence}</span><div><strong>{event.type.replaceAll('_', ' ')}</strong><small>{formatDate(event.date)} · {event.task ? `${event.task.replaceAll('_', ' ')} · ` : ''}{event.crop_id?.replaceAll('_', ' ') || 'synthetic ledger'}</small></div></li>)}</ol> : <p className="muted-copy">Creation is recorded first. Advance the clock to record tasks, deliveries, costs and closing inventory.</p>}</div>
      </div>
      <p className="simulation-footnote">Engine {world.engine_version} · revision {world.revision} · {world.plan_history.length} recorded replans · inference triggered: no · real operations: disabled</p>
    </>}
    {error && <p className="field-error" role="alert">{error}</p>}
  </section>
}
