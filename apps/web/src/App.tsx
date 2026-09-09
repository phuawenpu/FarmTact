import { Activity, Database, FlaskConical, Leaf, Map, Menu, MoreHorizontal, Plus, Settings2, Sprout, Wrench, X } from 'lucide-react'
import { useCallback, useEffect, useRef, useState } from 'react'
import { Board } from './components/Board'
import { CropLibrary, Outcomes, Setup } from './components/Rooms'
import { DataExplorer } from './components/DataExplorer'
import { StatePanel, StatusPill } from './components/Visuals'
import { World } from './components/World'
import { api } from './lib/api'
import type { AppView, Bootstrap, Crop, Run } from './lib/types'

const navItems: Array<{ id: AppView; label: string; icon: typeof Map }> = [
  { id: 'world', label: 'Farm', icon: Map },
  { id: 'board', label: 'Farm tools', icon: Wrench },
  { id: 'crops', label: 'Crops', icon: Leaf },
  { id: 'data', label: 'Data', icon: Database },
  { id: 'outcomes', label: 'Outcomes', icon: FlaskConical },
  { id: 'setup', label: 'Setup', icon: Settings2 },
]

export default function App() {
  const [view, setView] = useState<AppView>('world')
  const [bootstrap, setBootstrap] = useState<Bootstrap | null>(null)
  const [run, setRun] = useState<Run | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState<string | null>(null)
  const [transientEvent, setTransientEvent] = useState<string | null>(null)
  const [moreOpen, setMoreOpen] = useState(false)
  const eventTimer = useRef<number | undefined>(undefined)

  const loadBootstrap = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await api.bootstrap()
      setBootstrap(data)
      setRun(data.latest_run)
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'FarmTact could not load the farm workspace.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { void loadBootstrap() }, [loadBootstrap])
  useEffect(() => { window.scrollTo({ top: 0, behavior: 'auto' }) }, [view])

  const fetchRun = useCallback(async (id: string) => {
    try {
      let nextRun = await api.run(id)
      let followedReplacement = false
      for (let depth = 0; nextRun.superseded_by && nextRun.superseded_by !== nextRun.id && depth < 5; depth += 1) {
        nextRun = await api.run(nextRun.superseded_by)
        followedReplacement = true
      }
      if (followedReplacement) {
        const workspace = await api.bootstrap()
        setBootstrap(workspace)
        if (workspace.latest_run?.id === nextRun.id) nextRun = workspace.latest_run
      }
      setRun(nextRun)
      return nextRun
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'The planning run could not be refreshed.')
      return null
    }
  }, [])

  useEffect(() => {
    if (run?.superseded_by && run.superseded_by !== run.id) void fetchRun(run.superseded_by)
  }, [run?.id, run?.superseded_by, fetchRun])

  useEffect(() => {
    if (!run?.id || ['completed', 'failed', 'cancelled', 'accepted_for_simulation', 'no_feasible_plan', 'stale_input'].includes(run.status.toLowerCase())) return
    const id = run.id
    const source = new EventSource(api.eventsUrl(id))
    source.onmessage = event => {
      try {
        const payload = JSON.parse(event.data) as { event_type?: string }
        if (payload.event_type) {
          setTransientEvent(payload.event_type)
          window.clearTimeout(eventTimer.current)
          eventTimer.current = window.setTimeout(() => setTransientEvent(null), 3500)
          if (/strategy_ready|accepted_for_simulation|run_completed|run_failed/.test(payload.event_type)) void fetchRun(id)
        }
      } catch { /* malformed stream events are ignored and polling remains active */ }
    }
    source.onerror = () => source.close()
    const poll = window.setInterval(() => { void fetchRun(id) }, 2500)
    return () => { source.close(); window.clearInterval(poll) }
  }, [run?.id, run?.status, fetchRun])

  useEffect(() => () => window.clearTimeout(eventTimer.current), [])

  const startRun = async (council: boolean) => {
    setBusy(council ? 'start-council' : 'start-numerical'); setError(null)
    try {
      const created = await api.createRun(council)
      setRun(current => current?.id === created.id ? current : {
        id: created.id, status: created.status, input_version: '', created_at: new Date().toISOString(),
        execution_mode: bootstrap?.capabilities.execution_mode || 'test', data_mode: bootstrap?.capabilities.data_mode || '',
        council_status: council ? 'queued' : 'not_run', strategies: [], claims: [], events: [], warnings: [],
      })
      await fetchRun(created.id)
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'The planning mission could not start.') }
    finally { setBusy(null) }
  }

  const demoReplay = async () => {
    setBusy('demo-replay'); setError(null)
    try { setRun(await api.demoReplay()); setView('board'); window.scrollTo({ top: 0, behavior: 'auto' }) }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'The recorded demo could not be loaded.') }
    finally { setBusy(null) }
  }

  const replan = async () => {
    if (!run) return
    setBusy('replan'); setError(null)
    try {
      const result = await api.replan(run.id)
      const workspace = await api.bootstrap()
      setBootstrap(workspace)
      if ('strategies' in result) setRun(result)
      else await fetchRun(result.id)
    } catch (caught) { setError(caught instanceof Error ? caught.message : 'The disruption could not be applied.') }
    finally { setBusy(null) }
  }

  const replay = async () => {
    if (!run) return
    setBusy('replay'); setError(null)
    try { setRun(await api.replay(run.id)); setView('outcomes'); window.scrollTo({ top: 0, behavior: 'auto' }) }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'The stored replay could not be loaded.') }
    finally { setBusy(null) }
  }

  const seed = async () => {
    setBusy('seed'); setError(null)
    try { await api.importSeed(); await loadBootstrap(); setView('world') }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'The synthetic demo could not be imported.') }
    finally { setBusy(null) }
  }

  const importFarm = async (farm: unknown) => {
    setBusy('import'); setError(null)
    try { await api.importFarm(farm); await loadBootstrap(); setView('world') }
    catch (caught) { setError(caught instanceof Error ? caught.message : 'The farm record could not be imported.') }
    finally { setBusy(null) }
  }

  const loadCrop = (id: string): Promise<Crop> => api.crop(id)

  return (
    <div className="app-shell">
      <aside className="side-rail">
        <Brand />
        <nav aria-label="FarmTact rooms">
          {navItems.map(({ id, label, icon: Icon }) => <button key={id} className={view === id ? 'is-active' : ''} onClick={() => setView(id)}><Icon size={20}/><span>{label}</span></button>)}
        </nav>
        <div className="side-rail__mode"><span>Workspace</span><strong>{bootstrap?.capabilities.data_mode?.replaceAll('_', ' ') || 'Unavailable'}</strong></div>
      </aside>

      <div className="app-content">
        <header className="topbar">
          <div className="topbar__mobile-brand"><Brand /></div>
          <div className="farm-identity">
            <span className="farm-identity__icon"><Sprout size={20}/></span>
            <span><small>Active farm</small><strong>{bootstrap?.farm.name || 'Farm not loaded'}</strong></span>
          </div>
          <div className="topbar__status">
            {run && <StatusPill status={run.status} />}
            <button className="icon-button" onClick={() => setView('setup')} aria-label="Add or import farm"><Plus size={20}/></button>
            <button className="icon-button topbar__more" onClick={() => setMoreOpen(value => !value)} aria-label="Workspace status"><MoreHorizontal size={20}/></button>
          </div>
          {moreOpen && <div className="topbar-popover"><button aria-label="Close" onClick={() => setMoreOpen(false)}><X size={16}/></button><span>Data mode</span><strong>{bootstrap?.capabilities.data_mode || 'unavailable'}</strong><span>Execution</span><strong>{bootstrap?.capabilities.execution_mode || 'unavailable'}</strong></div>}
        </header>

        <main>
          {error && <div className="error-banner" role="alert"><Activity size={18}/><span>{error}</span><button onClick={() => setError(null)}>Dismiss</button></div>}
          {loading ? <StatePanel kind="loading" title="Opening the strategy room" detail="Loading the farm, evidence registry and latest planning run." /> : !bootstrap ? (
            <StatePanel kind="error" title="The farm workspace is unavailable" detail="The API did not return a usable bootstrap response." action={<button className="button button--forest" onClick={loadBootstrap}>Try again</button>} />
          ) : (
            <>
              {view === 'world' && <World farm={bootstrap.farm} crops={bootstrap.crops} run={run} executionMode={bootstrap.capabilities.execution_mode} onOpenTools={() => setView('board')} onOpenCrops={() => setView('crops')} onOpenOutcomes={() => setView('outcomes')} />}
              {view === 'board' && <Board farm={bootstrap.farm} crops={bootstrap.crops} run={run} busy={busy} executionMode={bootstrap.capabilities.execution_mode} transientEvent={transientEvent} onStart={startRun} onDemoReplay={demoReplay} onReplan={replan} onReplay={replay} />}
              {view === 'crops' && <CropLibrary crops={bootstrap.crops} onLoadCrop={loadCrop} />}
              {view === 'data' && <DataExplorer bootstrap={bootstrap} />}
              {view === 'outcomes' && <Outcomes run={run} busy={busy} onReplay={replay} />}
              {view === 'setup' && <Setup farm={bootstrap.farm} busy={busy} onSeed={seed} onImport={importFarm} />}
            </>
          )}
        </main>
      </div>

      <nav className="thumb-nav" aria-label="FarmTact rooms">
        {navItems.map(({ id, label, icon: Icon }) => <button key={id} className={view === id ? 'is-active' : ''} onClick={() => setView(id)}><span><Icon size={19}/></span><small>{id === 'board' ? 'Tools' : label}</small></button>)}
      </nav>
    </div>
  )
}

function Brand() {
  return <div className="brand"><span className="brand__mark"><Sprout size={22}/></span><span><strong>FarmTact</strong><small>Strategy Room</small></span></div>
}
