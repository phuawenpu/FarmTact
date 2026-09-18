import { AlertTriangle, ArrowUpRight, BarChart3, BookOpen, CalendarClock, CheckCircle2, Cloud, Database, FileJson, FlaskConical, Leaf, LockKeyhole, Play, RefreshCw, Search, ShieldCheck, Upload } from 'lucide-react'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import type { Capabilities, Crop, Farm, Run, Source } from '../lib/types'
import { editionPath } from '../lib/edition'
import { CropArt, formatDate, formatMoney, humanizeExecutionMode, StatusPill } from './Visuals'
import { SimulationPanel } from './SimulationPanel'

export function DataRoom({ sources, capabilities }: { sources: Source[]; capabilities: Capabilities }) {
  return (
    <div className="room-page">
      <RoomHero eyebrow="Evidence map" title="Know what the plan knows." copy="Every current-information card shows where it came from, when it was observed and how it was retrieved." icon={<Database size={27} />} />
      <section className="capability-ribbon">
        <div><span className="capability-icon"><ShieldCheck size={19} /></span><span><small>DeepSeek text</small><strong><StatusPill status={capabilities.deepseek.status} /></strong></span></div>
        <div><span className="capability-icon"><Leaf size={19} /></span><span><small>Data mode</small><strong>{capabilities.data_mode.replaceAll('_', ' ')}</strong></span></div>
        <div><span className="capability-icon"><FlaskConical size={19} /></span><span><small>Execution</small><strong>{capabilities.execution_mode}</strong></span></div>
      </section>
      <section className="section-block">
        <div className="section-heading"><div><p className="kicker">Source registry</p><h2>Current information</h2></div><span className="count-badge">{sources.length} sources</span></div>
        {sources.length ? <div className="source-grid">{sources.map(source => <SourceCard source={source} key={source.id} />)}</div> : <div className="soft-empty"><Cloud size={21} /><span>No source records were returned by the API.</span></div>}
      </section>
    </div>
  )
}

function SourceCard({ source }: { source: Source }) {
  const content = (
    <>
      <div className="source-card__top"><span className={`source-mark source-mark--${source.origin}`}><Cloud size={17} /></span><StatusPill status={source.status} /></div>
      <div><p className="kicker">{source.origin === 'public' ? 'public source' : 'synthetic fixture'} · {humanizeExecutionMode(source.execution_mode)}</p><h3>{source.name}</h3><p>{source.summary}</p></div>
      {source.value !== undefined && source.value !== null && <div className="source-value"><strong>{source.value}</strong>{source.unit && <span>{Array.isArray(source.unit) ? source.unit.join(' · ') : source.unit}</span>}</div>}
      <dl className="provenance-list">
        <div><dt>Observed</dt><dd>{formatDate(source.observed_at, true)}</dd></div>
        <div><dt>Retrieved</dt><dd>{formatDate(source.retrieved_at, true)}</dd></div>
        <div><dt>Freshness</dt><dd>{source.freshness}</dd></div>
      </dl>
      {source.url && <span className="source-link">Open source <ArrowUpRight size={14} /></span>}
    </>
  )
  return source.url ? <a className="source-card" href={source.url} target="_blank" rel="noreferrer">{content}</a> : <article className="source-card">{content}</article>
}

export function CropLibrary({ crops, onLoadCrop }: { crops: Crop[]; onLoadCrop: (id: string) => Promise<Crop> }) {
  const [query, setQuery] = useState('')
  const [selected, setSelected] = useState<Crop | null>(null)
  const [loading, setLoading] = useState<string | null>(null)
  const closeButton = useRef<HTMLButtonElement>(null)
  const profileDialog = useRef<HTMLElement>(null)
  const profileTrigger = useRef<HTMLButtonElement | null>(null)
  const profileRequest = useRef(0)
  const closeCrop = useCallback(() => {
    profileRequest.current += 1
    setSelected(null)
    setLoading(null)
    profileTrigger.current?.focus({ preventScroll: true })
  }, [])
  useEffect(() => () => { profileRequest.current += 1 }, [])
  const filtered = useMemo(() => crops.filter(crop => `${crop.label} ${crop.aliases.join(' ')}`.toLowerCase().includes(query.toLowerCase())), [crops, query])

  const openCrop = async (crop: Crop, trigger: HTMLButtonElement) => {
    const request = ++profileRequest.current
    profileTrigger.current = trigger
    setSelected(crop)
    setLoading(crop.id)
    try {
      const profile = await onLoadCrop(crop.id)
      if (profileRequest.current === request) setSelected(profile)
    } catch { /* summary remains usable */ } finally {
      if (profileRequest.current === request) setLoading(null)
    }
  }

  const selectedCropId = selected?.id
  useEffect(() => {
    if (!selectedCropId) return
    closeButton.current?.focus()
    const handleKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') { event.preventDefault(); closeCrop(); return }
      if (event.key !== 'Tab') return
      const controls = Array.from(profileDialog.current?.querySelectorAll<HTMLElement>('button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex="0"]') || []).filter(element => element.getClientRects().length > 0)
      const first = controls[0], last = controls[controls.length - 1]
      if (!first) return
      if (event.shiftKey && (document.activeElement === first || !profileDialog.current?.contains(document.activeElement))) { event.preventDefault(); last.focus() }
      else if (!event.shiftKey && (document.activeElement === last || !profileDialog.current?.contains(document.activeElement))) { event.preventDefault(); first.focus() }
    }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [selectedCropId, closeCrop])

  return (
    <div className="room-page">
      <RoomHero eyebrow="Crop atlas" title="Recipes with receipts." copy="Explore biological lead times, system fit, warnings and the evidence behind each planning parameter." icon={<Leaf size={27} />} />
      <label className="search-field"><Search size={18} /><span className="sr-only">Search crops</span><input value={query} onChange={event => setQuery(event.target.value)} placeholder="Search crop or local alias" /></label>
      <section className="crop-library">
        {filtered.map((crop, index) => (
          <button className="crop-profile-card" onClick={event => void openCrop(crop, event.currentTarget)} key={crop.id} style={{ '--delay': `${index * 35}ms` } as React.CSSProperties}>
            <div className="crop-profile-card__art"><CropArt cropId={crop.id} color={crop.color} /></div>
            <div className="crop-profile-card__body">
              <div><h2>{crop.label}</h2><p>{crop.aliases.length ? crop.aliases.join(' · ') : 'No aliases reported'}</p></div>
              <StatusPill status={crop.recipe?.validation_status || 'profile only'} />
              <dl>
                <div><dt>Harvested part</dt><dd>{crop.harvested_part}</dd></div>
                <div><dt>Cycle</dt><dd>{crop.recipe ? `${crop.recipe.cycle_days} days` : 'Unreported'}</dd></div>
                <div><dt>Evidence</dt><dd>{crop.evidence_ids.length} references</dd></div>
              </dl>
            </div>
          </button>
        ))}
        {!filtered.length && <div className="soft-empty"><Search size={20} /><span>No crops match “{query}”.</span></div>}
      </section>
      {selected && <div className="sheet-layer" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) closeCrop() }}><section ref={profileDialog} className="crop-modal" role="dialog" aria-modal="true" aria-label={`${selected.label} profile`}><button ref={closeButton} className="modal-close" onClick={closeCrop}>Close</button><CropArt cropId={selected.id} color={selected.color} /><p className="illustration-caveat">Illustration shows a representative form; cultivar and SKU may vary. Artwork does not resolve catalogue taxonomy or agronomic uncertainty.</p><p className="kicker">{selected.harvested_part}</p><h2>{selected.label}</h2><p className="crop-aliases">{selected.aliases.join(' · ')}</p>{loading === selected.id ? <p className="muted-copy">Loading evidence profile…</p> : <><h3 className="subheading">Planning recipe</h3>{selected.recipe ? <div className="metric-grid"><div><span>Full cycle</span><strong>{selected.recipe.cycle_days} days</strong></div><div><span>Nursery</span><strong>{selected.recipe.nursery_days} days</strong></div><div><span>Expected yield</span><strong>{selected.recipe.yield_kg_per_m2} kg/m²</strong></div><div><span>Validation</span><strong>{selected.recipe.validation_status.replaceAll('_', ' ')}</strong></div></div> : <p className="muted-copy">No planning recipe is available.</p>}<h3 className="subheading">Cautions</h3>{selected.warnings.length ? <ul className="clean-list warning-list">{selected.warnings.map(item => <li key={item}><AlertTriangle size={15}/>{item}</li>)}</ul> : <p className="muted-copy">No warnings reported.</p>}<h3 className="subheading">Evidence</h3>{selected.evidence?.length ? <div className="evidence-records">{selected.evidence.map(record => <article key={record.evidence_id}><div><span><BookOpen size={13}/>{record.evidence_id}</span>{record.year && <small>{record.year}</small>}</div><strong>{record.title || 'Untitled evidence record'}</strong>{record.finding && <p>{record.finding}</p>}{record.limit && <p className="evidence-limit"><AlertTriangle size={13}/>{record.limit}</p>}{record.source_url && <a href={record.source_url} target="_blank" rel="noreferrer">Open source <ArrowUpRight size={13}/></a>}</article>)}</div> : <div className="evidence-chips">{selected.evidence_ids.map(id => <span key={id}><BookOpen size={13}/>{id}</span>)}</div>}</>}</section></div>}
    </div>
  )
}

export function Outcomes({ run, crops, busy, onReplay }: { run: Run | null; crops: Crop[]; busy: string | null; onReplay: () => void }) {
  const strategy = run?.strategies.find(item => item.id === run.accepted_strategy_id) || run?.strategies[0]
  const maxValue = Math.max(0, ...(strategy?.weekly.flatMap(week => [week.demand_kg, week.harvest_kg, week.delivered_kg]) || []))
  return (
    <div className="room-page">
      <RoomHero eyebrow="Outcome lab" title="Learn from every turn." copy="Compare expected harvest, delivery and shortfall using the stored decision record." icon={<BarChart3 size={27} />} />
      {!run || !strategy ? <div className="state-panel state-panel--empty"><span className="state-panel__icon"><CalendarClock size={24}/></span><div><h2>No plan outcome yet</h2><p>Run a planning mission first. Its weekly results and stored replay will appear here.</p></div></div> : (
        <>
          <section className="outcome-scoreboard">
            <div><span>Expected harvest</span><strong>{strategy.metrics.harvest_kg.toLocaleString('en-SG')}<small> kg</small></strong></div>
            <div><span>Demand filled</span><strong>{Math.round(strategy.metrics.fill_rate * 100)}<small>%</small></strong></div>
            <div><span>Margin</span><strong>{formatMoney(strategy.metrics.margin_sgd)}</strong></div>
            <div><span>Shortfall</span><strong>{strategy.metrics.shortfall_kg.toLocaleString('en-SG')}<small> kg</small></strong></div>
          </section>
          <section className="section-block">
            <div className="section-heading"><div><p className="kicker">Week by week</p><h2>Demand and harvest</h2></div><span className="mode-chip">{run.execution_mode}</span></div>
            {strategy.weekly.length ? <div className="weekly-chart" role="img" aria-label="Weekly demand, harvest and delivery chart">{strategy.weekly.map(week => <div className="week-column" key={week.week}><div className="bars"><i className="bar bar--demand" style={{ height: `${maxValue ? week.demand_kg / maxValue * 100 : 0}%` }} title={`Demand ${week.demand_kg} kg`}/><i className="bar bar--harvest" style={{ height: `${maxValue ? week.harvest_kg / maxValue * 100 : 0}%` }} title={`Harvest ${week.harvest_kg} kg`}/></div><strong>W{week.week}</strong><span>{formatDate(week.date)}</span>{week.shortfall_kg > 0 && <small>{week.shortfall_kg} kg short</small>}</div>)}</div> : <p className="muted-copy">No weekly result series was returned.</p>}
            <div className="chart-legend"><span><i className="legend-dot legend-dot--demand"/> Demand</span><span><i className="legend-dot legend-dot--harvest"/> Harvest</span></div>
          </section>
          <section className="replay-card"><span className="replay-card__icon"><RefreshCw size={22}/></span><div><h2>{run.shared_demo ? 'Shared recorded demo' : 'Stored replay'}</h2><p>{run.shared_demo ? 'This curated replay uses stored council records and makes no current-time model calls.' : 'Review the same result with execution mode replay and zero new model calls.'}</p></div>{run.shared_demo ? <span className="shared-replay-note"><StatusPill status="replay" /> Start your own mission from the Board to enable worklist and replan actions.</span> : <div className="replay-card__actions"><a className="button button--cream" href={editionPath(`/api/v1/planning-runs/${encodeURIComponent(run.id)}/worklist.csv`)} download>Download worklist</a><button className="button button--forest" onClick={onReplay} disabled={!!busy}>{busy === 'replay' ? 'Loading…' : 'Open replay'}</button></div>}</section>
          <SimulationPanel run={run} crops={crops}/>
        </>
      )}
    </div>
  )
}

export function Setup({ farm, busy, onSeed, onImport }: { farm: Farm | null; busy: string | null; onSeed: () => void; onImport: (farm: unknown) => void }) {
  const input = useRef<HTMLInputElement>(null)
  const [fileError, setFileError] = useState<string | null>(null)
  const chooseFile = async (file?: File) => {
    if (!file) return
    try {
      if (file.size > 1_000_000) throw new Error('Choose a JSON file under 1 MB.')
      const parsed: unknown = JSON.parse(await file.text())
      const farmData = typeof parsed === 'object' && parsed !== null && 'farm' in parsed ? (parsed as { farm: unknown }).farm : parsed
      if (!farmData || typeof farmData !== 'object') throw new Error('The file must contain a farm object.')
      setFileError(null)
      onImport(farmData)
    } catch (error) { setFileError(error instanceof Error ? error.message : 'That file could not be read.') } finally { if (input.current) input.current.value = '' }
  }
  return (
    <div className="room-page">
      <RoomHero eyebrow="Farm setup" title="Bring the farm onto the board." copy="Load the versioned synthetic demo or import a validated JSON farm record." icon={<FileJson size={27} />} />
      <section className="setup-choice-grid">
        <article className="setup-choice setup-choice--seed"><span><Play size={23} fill="currentColor"/></span><p className="kicker">One click</p><h2>Seed the demo farm</h2><p>Loads the complete synthetic demonstration through the backend’s validated fixture importer.</p><button className="button button--lime" onClick={onSeed} disabled={!!busy}>{busy === 'seed' ? 'Loading demo…' : 'Load synthetic demo'}</button></article>
        <article className="setup-choice"><span><Upload size={23}/></span><p className="kicker">Private input</p><h2>Import farm JSON</h2><p>The browser parses the file and submits its farm object. Embedded scripts are never executed.</p><input ref={input} className="sr-only" type="file" accept="application/json,.json" onChange={event => chooseFile(event.target.files?.[0])}/><button className="button button--forest" onClick={() => input.current?.click()} disabled={!!busy}>{busy === 'import' ? 'Importing…' : 'Choose JSON file'}</button>{fileError && <p className="field-error" role="alert">{fileError}</p>}</article>
      </section>
      {farm && <section className="section-block"><div className="section-heading"><div><p className="kicker">Connected farm</p><h2>{farm.name}</h2></div><StatusPill status={farm.data_mode}/></div><dl className="farm-facts"><div><dt>Location</dt><dd>{farm.location}</dd></div><div><dt>Growing spaces</dt><dd>{farm.beds.length}</dd></div><div><dt>Orders</dt><dd>{farm.orders.length}</dd></div><div><dt>Version</dt><dd>{farm.version}</dd></div><div><dt>Cutoff</dt><dd>{formatDate(farm.cutoff)}</dd></div><div><dt>Timezone</dt><dd>{farm.timezone}</dd></div></dl><div className="simulation-note"><LockKeyhole size={17}/><span>This development workspace permits simulated work only. It cannot commit real planting, purchases or buyer communication.</span></div></section>}
    </div>
  )
}

function RoomHero({ eyebrow, title, copy, icon }: { eyebrow: string; title: string; copy: string; icon: React.ReactNode }) {
  return <section className="room-hero"><span className="room-hero__icon">{icon}</span><div><p className="kicker">{eyebrow}</p><h1>{title}</h1><p>{copy}</p></div></section>
}
