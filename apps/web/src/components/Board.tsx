import { ArrowRight, CalendarDays, CheckCircle2, ChevronRight, CircleAlert, Gauge, Layers3, ListTree, Play, RotateCcw, Sparkles, Table2, X } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { Crop, Farm, Run, Strategy } from '../lib/types'
import { editionPath } from '../lib/edition'
import { CropArt, EventIcon, formatDate, formatMoney, humanizeExecutionMode, humanizeSystem, Meter, StatusPill } from './Visuals'

interface BoardProps {
  farm: Farm
  crops: Crop[]
  run: Run | null
  busy: string | null
  executionMode: string
  transientEvent: string | null
  onStart: (council: boolean) => void
  onDemoReplay: () => void
  onReplan: () => void
  onReplay: () => void
}

export function Board({ farm, crops, run, busy, executionMode, transientEvent, onStart, onDemoReplay, onReplan, onReplay }: BoardProps) {
  const accepted = run?.strategies.find(strategy => strategy.id === run.accepted_strategy_id)
  const terminalRun = Boolean(run && ['accepted_for_simulation', 'review_withheld', 'no_feasible_plan', 'failed', 'cancelled', 'stale_input'].includes(run.status.toLowerCase()))
  const compactHero = terminalRun && !run?.shared_demo
  const evidenceStatus = run?.evidence_validation?.status
  const evidenceValidated = typeof evidenceStatus === 'string' && evidenceStatus.toLowerCase() === 'passed'
  const reviewWithheld = run?.status.toLowerCase() === 'review_withheld'
  const [previewId, setPreviewId] = useState<string | null>(null)
  const [sheet, setSheet] = useState<'strategy' | 'timeline' | 'council' | null>(null)
  const [tableView, setTableView] = useState(false)
  const preview = run?.strategies.find(strategy => strategy.id === previewId) || accepted || run?.strategies[0]
  const strategyCards = useMemo(() => run ? [...run.strategies].sort((a, b) => Number(b.id === run.accepted_strategy_id) - Number(a.id === run.accepted_strategy_id)) : [], [run])
  const cropMap = useMemo(() => new Map(crops.map(crop => [crop.id, crop])), [crops])
  const resourcePlan = preview?.metrics

  return (
    <>
      <section className={`hero-card ${compactHero ? 'hero-card--compact' : ''}`}>
        <div className="hero-card__eyebrow"><Sparkles size={15} /> Planning mission</div>
        <div className="hero-card__body">
          <div>
            <p className="kicker">{farm.location} · {farm.horizon_days}-day horizon</p>
            <h1>Turn today’s beds into the next good harvest.</h1>
            <p className="hero-card__copy">Plan for {farm.orders.length} buyer {farm.orders.length === 1 ? 'commitment' : 'commitments'} within the farm’s space, labour and cash limits.</p>
          </div>
          {!run || run.shared_demo || ['failed', 'cancelled'].includes(run.status.toLowerCase()) ? (
            <div className="hero-actions">
              <button className="button button--lime button--hero" onClick={() => onStart(true)} disabled={!!busy}>
                {busy === 'start-council' ? <span className="spinner" /> : <Play size={18} fill="currentColor" />} Plan with DeepSeek council
              </button>
              <button className="button button--cream button--hero" onClick={() => onStart(false)} disabled={!!busy}>
                {busy === 'start-numerical' ? <span className="spinner" /> : <Gauge size={18} />} Plan with numerical tools
              </button>
              {!run && <button className="hero-replay-button" onClick={onDemoReplay} disabled={!!busy}><RotateCcw size={15}/>{busy === 'demo-replay' ? 'Loading replay…' : 'Replay recorded demo'}</button>}
            </div>
          ) : (
            <div className="mission-status">
              <StatusPill status={run.status} />
              <span>Run {run.id.slice(0, 8)}</span>
            </div>
          )}
        </div>
        <div className="hero-orbit" aria-hidden="true"><span>🌱</span><span>🥬</span><span>✓</span></div>
      </section>

      {transientEvent && (
        <div className="event-toast" role="status">
          <EventIcon type={transientEvent} />
          <span>{transientEvent.replaceAll('_', ' ')}</span>
        </div>
      )}

      {run?.shared_demo && (
        <section className="shared-replay-banner">
          <RotateCcw size={19}/><div><strong>Shared recorded demo</strong><p>This is a stored DeepSeek council result in replay mode. It is not current-time agent activity.</p>{run.claims.length === 6 && <small>Archived six-role council from the reference edition.</small>}</div><StatusPill status="replay" />
        </section>
      )}

      {run && (
        <section className="acceptance-banner">
          <span className="acceptance-banner__icon">{reviewWithheld ? <CircleAlert size={21}/> : <CheckCircle2 size={21} />}</span>
          <div>
            <strong>{reviewWithheld ? 'Council evidence review withheld' : accepted ? `${accepted.name} ${run.shared_demo ? 'was ' : ''}selected automatically` : 'Policy checks in progress'}</strong>
            <p>{reviewWithheld ? acceptanceSummary(run, evidenceValidated) : accepted ? acceptanceSummary(run, evidenceValidated) : 'FarmTact is validating candidates. No approval click is required.'}</p>
          </div>
          <span className="mode-chip">{run.execution_mode}</span>
        </section>
      )}

      {run?.disruption && (
        <section className="disruption-banner" aria-label="Simulated disruption">
          <span><CircleAlert size={20} /></span>
          <div><p className="kicker">Simulated event</p><strong>Crop delay applied</strong><p>{disruptionSummary(run.disruption)}</p></div>
          <StatusPill status="synthetic" />
        </section>
      )}

      <section className="section-block">
        <div className="section-heading">
          <div><p className="kicker">{farm.data_mode.replaceAll('_', ' ')}</p><h2>Your growing board</h2></div>
          <button className="text-button" onClick={() => setSheet('timeline')}><CalendarDays size={17} /> Timeline</button>
        </div>
        <div className="board-mode-labels" aria-label="Board data and execution modes">
          <span>{farm.data_mode.replaceAll('_', ' ')}</span><span>{humanizeExecutionMode(run?.execution_mode || executionMode)}</span><span>{run?.shared_demo ? 'shared recorded demo' : 'simulation only'}</span>
        </div>
        <div className="bed-grid">
          {farm.beds.map((bed, index) => {
            const crop = bed.crop_id ? cropMap.get(bed.crop_id) : undefined
            const progress = Math.min(100, Math.max(0, bed.progress * (bed.progress <= 1 ? 100 : 1)))
            return (
              <article className={`bed-card bed-card--${bed.stage}`} key={bed.id} style={{ '--delay': `${index * 45}ms` } as React.CSSProperties}>
                <div className="bed-card__top">
                  <span className="bed-card__number">{String(index + 1).padStart(2, '0')}</span>
                  <StatusPill status={bed.stage} />
                </div>
                <CropArt cropId={bed.crop_id} color={crop?.color} stage={bed.stage} />
                <div className="bed-card__content">
                  <h3>{crop?.label || bed.name}</h3>
                  <p>{crop ? `${bed.name} · ${humanizeSystem(bed.system)}` : `${bed.area_m2} m² ready for a crop`}</p>
                  {bed.stage !== 'empty' && (
                    <>
                      <div className="bed-progress" role="progressbar" aria-label={`${bed.name} growth`} aria-valuenow={progress} aria-valuemin={0} aria-valuemax={100}>
                        <span style={{ width: `${progress}%` }} />
                      </div>
                      <div className="bed-card__dates"><span>{Math.round(progress)}% cycle elapsed</span><span>{bed.harvest_date ? `Harvest ${formatDate(bed.harvest_date)}` : 'Harvest unreported'}</span></div>
                    </>
                  )}
                </div>
              </article>
            )
          })}
        </div>
      </section>

      <section className="section-block">
        <div className="section-heading">
          <div><p className="kicker">Plan candidates</p><h2>Choose a lens</h2></div>
          {run?.strategies.length ? <span className="count-badge">{run.strategies.length} strategies</span> : null}
        </div>
        {run?.strategies.length ? (
          <div className="strategy-strip">
            {strategyCards.map(strategy => {
              const isAccepted = strategy.id === run.accepted_strategy_id
              const isPreview = strategy.id === preview?.id
              return (
                <button key={strategy.id} className={`strategy-card strategy-card--${strategy.name.toLowerCase()} ${isPreview ? 'is-selected' : ''}`} onClick={() => { setPreviewId(strategy.id); setSheet('strategy') }}>
                  <span className="strategy-card__tag">{isAccepted ? <><CheckCircle2 size={14} /> Auto-selected</> : 'Compare'}</span>
                  <span className="strategy-card__name">{strategy.name}</span>
                  <span className="strategy-card__description">{strategy.description}</span>
                  <span className="strategy-card__score"><strong>{Math.round(strategy.metrics.fill_rate * 100)}%</strong><small>demand filled</small></span>
                  <span className="strategy-card__mini"><span>{formatMoney(strategy.metrics.margin_sgd)} margin</span><span>{strategy.metrics.waste_kg.toLocaleString('en-SG')} kg waste</span></span>
                  <span className="strategy-card__open">See the trade-offs <ChevronRight size={16} /></span>
                </button>
              )
            })}
          </div>
        ) : (
          <div className="soft-empty"><Layers3 size={21} /><span>{run ? 'Strategies will appear as the planning run completes.' : 'Start a planning mission to compare Lean, Balanced and Resilient strategies.'}</span></div>
        )}
      </section>

      <section className="board-columns">
        <div className="section-block resource-panel">
          <div className="section-heading"><div><p className="kicker">Plan scope</p><h2>Plan resources</h2></div><Gauge size={20} /></div>
          {resourcePlan ? (
            <div className="meter-stack">
              <div className="resource-stat"><span>New sowing area</span><strong>{resourcePlan.area_m2.toLocaleString('en-SG')} <small>m²</small></strong><p>Summed across the horizon; peak bed occupancy is validated separately.</p></div>
              <Meter label={`Labour over ${farm.horizon_days} days`} value={resourcePlan.labour_hours} max={farm.resources.labour_hours_per_week * Math.ceil(farm.horizon_days / 7)} unit="hr" tone="sky" />
              <Meter label="Cash" value={resourcePlan.cost_sgd} max={farm.resources.cash_sgd} unit="SGD" tone="coral" />
            </div>
          ) : <p className="muted-copy">Plan usage will appear after calculations finish.</p>}
        </div>

        <div className="section-block advisors-panel">
          <div className="section-heading">
            <div><p className="kicker">Specialist council</p><h2>Advisor briefs</h2></div>
            {run?.claims.length ? <button className="text-button" onClick={() => setSheet('council')}>View all</button> : null}
          </div>
          {run?.claims.length ? (
            <div className="advisor-list">
              {run.claims.slice(0, 3).map((claim, index) => (
                <article className="advisor-card" key={`${claim.role}-${index}`}>
                  <div className={`advisor-avatar advisor-avatar--${index % 3}`}>{claim.role.slice(0, 2).toUpperCase()}</div>
                  <div><div className="advisor-card__meta"><strong>{claim.role.replaceAll('_', ' ')}</strong><StatusPill status={claim.status} /></div><p>{claim.statement}</p></div>
                </article>
              ))}
            </div>
          ) : <div className="advisor-roster-empty"><div aria-hidden="true"><span>CR</span><span>DM</span><span>IC</span></div><p>Advisors are waiting on an evidence-grounded run. No simulated conversation is shown as live activity.</p></div>}
        </div>
      </section>

      {run && !run.shared_demo && (
        <section className="action-deck">
          <div><p className="kicker">Scenario tools</p><h2>Test the plan, keep the evidence</h2><p>Replanning labels the crop delay as simulated. Replay uses the stored result with zero new inference.</p></div>
          <div className="action-deck__buttons">
            <button className="button button--cream" onClick={onReplay} disabled={!!busy}><RotateCcw size={17} /> {busy === 'replay' ? 'Loading…' : 'Replay run'}</button>
            <button className="button button--coral" onClick={onReplan} disabled={!!busy}><CircleAlert size={17} /> {busy === 'replan' ? 'Replanning…' : 'Simulate crop delay'}</button>
          </div>
        </section>
      )}

      <BottomSheet open={sheet !== null} title={sheet === 'strategy' ? `${preview?.name || ''} strategy` : sheet === 'timeline' ? 'Harvest timeline' : 'Council findings'} onClose={() => setSheet(null)}>
        {sheet === 'strategy' && preview && <StrategyDetails strategy={preview} accepted={preview.id === run?.accepted_strategy_id} runId={run?.id} sharedDemo={run?.shared_demo} />}
        {sheet === 'timeline' && (
          <Timeline farm={farm} strategy={preview} crops={cropMap} table={tableView} onToggle={() => setTableView(value => !value)} />
        )}
        {sheet === 'council' && <Council run={run} />}
      </BottomSheet>
    </>
  )
}

function acceptanceSummary(run: Run, evidenceValidated: boolean) {
  if (run.status.toLowerCase() === 'review_withheld') return 'Numerical alternatives are available, but council evidence review was withheld. This is not an infeasibility finding.'
  const subject = run.shared_demo ? 'The recorded plan was accepted' : 'Accepted'
  if (evidenceValidated) return `${subject} for simulation after numerical and evidence validation recorded by the council.`
  if (run.council_status === 'not_run') return `${subject} for simulation after numerical validation.`
  return `${subject} for simulation after numerical validation. Council findings remain separately labelled.`
}

function disruptionSummary(disruption: NonNullable<Run['disruption']>) {
  if (typeof disruption === 'string') return disruption.replaceAll('_', ' ')
  const delay = typeof disruption.delay_days === 'number' ? `${disruption.delay_days}-day delay` : 'Timing delay'
  const batch = typeof disruption.batch_id === 'string' ? ` for batch ${disruption.batch_id}` : ''
  return `${delay}${batch}. This observation is synthetic and triggers a new versioned plan.`
}

function StrategyDetails({ strategy, accepted, runId, sharedDemo }: { strategy: Strategy; accepted: boolean; runId?: string; sharedDemo?: boolean }) {
  const metrics = [
    ['Demand filled', `${Math.round(strategy.metrics.fill_rate * 100)}%`],
    ['Margin', formatMoney(strategy.metrics.margin_sgd)],
    ['Expected harvest', `${strategy.metrics.harvest_kg.toLocaleString('en-SG')} kg`],
    ['Shortfall', `${strategy.metrics.shortfall_kg.toLocaleString('en-SG')} kg`],
    ['Waste', `${strategy.metrics.waste_kg.toLocaleString('en-SG')} kg`],
    ['Cost', formatMoney(strategy.metrics.cost_sgd)],
  ]
  return (
    <div className="sheet-stack">
      <div className="sheet-intro"><StatusPill status={strategy.status} /><p>{strategy.description}</p>{accepted && <div className="accepted-note"><CheckCircle2 size={17} /> {sharedDemo ? 'Recorded acceptance for simulation.' : 'Accepted for simulation by development policy.'}</div>}{accepted && runId && !sharedDemo && <a className="button button--forest worklist-link" href={editionPath(`/api/v1/planning-runs/${encodeURIComponent(runId)}/worklist.csv`)} download>Download accepted worklist</a>}</div>
      <div className="metric-grid">{metrics.map(([label, value]) => <div key={label}><span>{label}</span><strong>{value}</strong></div>)}</div>
      {strategy.violations.length > 0 && <div className="warning-box"><CircleAlert size={18} /><div><strong>Constraint warnings</strong>{strategy.violations.map((item, index) => <p key={typeof item === 'string' ? item : `${item.constraint_code}-${index}`}>{formatViolation(item)}</p>)}</div></div>}
      <div><h3 className="subheading">Assumptions</h3>{strategy.assumptions.length ? <ul className="clean-list">{strategy.assumptions.map(item => <li key={item}>{item}</li>)}</ul> : <p className="muted-copy">No assumptions reported.</p>}</div>
    </div>
  )
}

function formatViolation(item: Strategy['violations'][number]) {
  if (typeof item === 'string') return item
  const label = item.constraint_code?.replaceAll('_', ' ') || 'Constraint violation'
  const amounts = item.required !== undefined && item.available !== undefined
    ? `: ${item.required} ${item.unit || ''} required, ${item.available} available`
    : ''
  return `${label}${amounts}`
}

function Timeline({ farm, strategy, crops, table, onToggle }: { farm: Farm; strategy?: Strategy; crops: Map<string, Crop>; table: boolean; onToggle: () => void }) {
  const allocations = strategy?.allocations || []
  return (
    <div className="sheet-stack">
      <button className="view-toggle" onClick={onToggle}>{table ? <ListTree size={17} /> : <Table2 size={17} />}{table ? 'Visual timeline' : 'Accessible table'}</button>
      {!allocations.length ? <p className="muted-copy">No planned allocations are available for this strategy.</p> : table ? (
        <div className="table-scroll"><table><caption>Planned crop stages and harvest dates</caption><thead><tr><th>Bed</th><th>Crop</th><th>Sow</th><th>Transplant</th><th>Harvest</th><th>Expected</th></tr></thead><tbody>{allocations.map(item => <tr key={`${item.bed_id}-${item.crop_id}`}><td>{farm.beds.find(b => b.id === item.bed_id)?.name || item.bed_id}</td><td>{crops.get(item.crop_id)?.label || item.crop_id}</td><td>{formatDate(item.sow_date)}</td><td>{formatDate(item.transplant_date)}</td><td>{formatDate(item.harvest_date)}</td><td>{item.expected_kg} kg</td></tr>)}</tbody></table></div>
      ) : (
        <div className="timeline-list">{allocations.map(item => <article key={`${item.bed_id}-${item.crop_id}`}><CropArt cropId={item.crop_id} color={crops.get(item.crop_id)?.color} compact /><div><strong>{crops.get(item.crop_id)?.label || item.crop_id}</strong><span>{farm.beds.find(b => b.id === item.bed_id)?.name || item.bed_id} · {item.area_m2} m²</span><div className="stage-track"><i className="stage-track__sow"/><i className="stage-track__grow"/><i className="stage-track__harvest"/></div><small>Sow {formatDate(item.sow_date)} <ArrowRight size={12}/> harvest {formatDate(item.harvest_date)}</small></div><b>{item.expected_kg} kg</b></article>)}</div>
      )}
    </div>
  )
}

function Council({ run }: { run: Run | null }) {
  if (!run?.claims.length) return <p className="muted-copy">No council findings were reported.</p>
  return <div className="sheet-stack advisor-list">{run.claims.map((claim, index) => <article className="advisor-card advisor-card--full" key={`${claim.role}-${index}`}><div className={`advisor-avatar advisor-avatar--${index % 3}`}>{claim.role.slice(0, 2).toUpperCase()}</div><div><div className="advisor-card__meta"><strong>{claim.role.replaceAll('_', ' ')}</strong><StatusPill status={claim.status} /></div><p>{claim.statement}</p><small>{claim.evidence_ids.length ? `Evidence: ${claim.evidence_ids.join(', ')}` : 'No evidence references reported'}</small></div></article>)}</div>
}

export function BottomSheet({ open, title, onClose, children }: { open: boolean; title: string; onClose: () => void; children: React.ReactNode }) {
  const closeButton = useRef<HTMLButtonElement>(null)
  useEffect(() => {
    if (!open) return
    closeButton.current?.focus()
    const handleKey = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose() }
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [open, onClose])
  if (!open) return null
  return (
    <div className="sheet-layer" role="presentation" onMouseDown={event => { if (event.target === event.currentTarget) onClose() }}>
      <section className="bottom-sheet" role="dialog" aria-modal="true" aria-label={title}>
        <div className="sheet-handle" />
        <header><h2>{title}</h2><button ref={closeButton} className="icon-button" onClick={onClose} aria-label="Close"><X size={20} /></button></header>
        <div className="bottom-sheet__body">{children}</div>
      </section>
    </div>
  )
}
