import { ArrowDown, ArrowLeft, ArrowRight, ArrowUp, Hand, BookOpen, CalendarDays, ClipboardList, Crosshair, FlaskConical, List, Minus, Plus, RotateCcw, SlidersHorizontal, Users, Wrench } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { Allocation, Bed, Crop, Farm, Run } from '../lib/types'
import { ADVISORS, advisorPublicLabel, type Advisor, type AdvisorId, type ProposedAction, type Scenario } from '../lib/game'
import { AccessibleFarmView, BedDetailPanel, ConversationPanel, QuestJournal, ScenarioLab } from './GamePanels'
import { DecisionMissionCard, type DecisionMission } from './DecisionJourney'
import { NewsPanel } from './NewsPanel'
import { editionPath } from '../lib/edition'

type Panel = 'bed' | 'conversation' | 'quests' | 'scenarios' | 'list' | null

interface WorldProps {
  farm: Farm
  crops: Crop[]
  run: Run | null
  mission?: DecisionMission | null
  executionMode: string
  onOpenTools: () => void
  onOpenCrops: () => void
  onOpenOutcomes: () => void
  guidedPlanAvailable?: boolean
  onReturnToGuidedPlan?: () => void
}

const advisorPositions: Record<AdvisorId, { x: number; y: number }> = {
  mei: { x: 792, y: 214 }, ravi: { x: 848, y: 493 }, hana: { x: 166, y: 185 },
  ben: { x: 160, y: 494 }, asha: { x: 667, y: 552 }, idris: { x: 535, y: 625 }, lina: { x: 925, y: 635 },
}
const advisorById = (id: AdvisorId) => ADVISORS.find(advisor => advisor.id === id)!

export function World({ farm, crops, run, mission, executionMode, onOpenTools, onOpenCrops, onOpenOutcomes, guidedPlanAvailable, onReturnToGuidedPlan }: WorldProps) {
  const [panel, setPanel] = useState<Panel>(null)
  const [selectedBedId, setSelectedBedId] = useState<string | null>(farm.beds[0]?.id || null)
  const [selectedAdvisor, setSelectedAdvisor] = useState<Advisor>(advisorById('mei'))
  const [previewDay, setPreviewDay] = useState(0)
  const [zoom, setZoom] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [moveMode, setMoveMode] = useState(false)
  const [dragging, setDragging] = useState(false)
  const suppressClick = useRef(false)
  const [scenarioAffected, setScenarioAffected] = useState<string[]>([])
  const [advisorReferenced, setAdvisorReferenced] = useState<string[]>([])
  const [scenarioContext, setScenarioContext] = useState<Scenario | null>(null)
  const [proposedAction, setProposedAction] = useState<{ action: ProposedAction; conversationId: string } | null>(null)
  const [questContext, setQuestContext] = useState<string | null>(null)
  const pointer = useRef<{ id: number; x: number; y: number; originX: number; originY: number; moved: boolean } | null>(null)
  const viewportRef = useRef<HTMLDivElement>(null)
  const cropMap = useMemo(() => new Map(crops.map(crop => [crop.id, crop])), [crops])
  const selectedBed = farm.beds.find(bed => bed.id === selectedBedId) || null
  const previewDate = addDays(farm.planning_date || singaporeCivilDate(farm.cutoff), previewDay)
  const currentRun = run && !run.shared_demo && String(run.input_version) === String(farm.version) ? run : null
  const accepted = currentRun?.strategies.find(strategy => strategy.id === currentRun.accepted_strategy_id)
  const allocationsByBed = useMemo(() => {
    const grouped = new Map<string, Allocation[]>()
    for (const allocation of accepted?.allocations || []) grouped.set(allocation.bed_id, [...(grouped.get(allocation.bed_id) || []), allocation])
    return grouped
  }, [accepted])
  const affected = new Set<string>([...scenarioAffected, ...advisorReferenced, ...(Array.isArray(run?.disruption && typeof run.disruption === 'object' ? run.disruption.affected_bed_ids : null)
    ? (run?.disruption as { affected_bed_ids: string[] }).affected_bed_ids : [])])

  const openAdvisor = (advisor: Advisor) => { setSelectedAdvisor(advisor); setPanel('conversation') }
  const recenter = () => { setZoom(1); setPan({ x: 0, y: 0 }) }
  const highlightReferences = (refs: string[]) => {
    const referenced = new Set(refs)
    const deliveryCrops = new Set(farm.orders.filter(order => referenced.has(`delivery:${order.id}`)).map(order => order.crop_id))
    const beds = farm.beds.filter(bed => referenced.has(`bed:${bed.id}`) || (bed.batch_id && referenced.has(`batch:${bed.batch_id}`)) || (bed.crop_id && deliveryCrops.has(bed.crop_id)))
    setAdvisorReferenced(beds.map(bed => bed.id))
    if (beds[0]) {
      setSelectedBedId(beds[0].id)
      const position = bedPosition(farm.beds.indexOf(beds[0]))
      setZoom(1); setPan({ x: 520 - position.x, y: 330 - position.y })
    }
    setPanel(null)
  }
  const boundedPan = (x: number, y: number) => {
    const rect = viewportRef.current?.getBoundingClientRect()
    const maxX = Math.max(0, (1040 * zoom - (rect?.width || 360)) / 2 + 48)
    const maxY = Math.max(0, (720 * zoom - (rect?.height || 430)) / 2 + 48)
    return { x: clamp(x, -maxX, maxX), y: clamp(y, -maxY, maxY) }
  }
  const nudge = (x: number, y: number) => setPan(old => boundedPan(old.x + x, old.y + y))
  const finishDrag = () => { pointer.current = null; setDragging(false) }
  useEffect(() => { setPan(old => boundedPan(old.x, old.y)) }, [zoom])


  return (
    <div className="world-page">
      <section className="world-heading" aria-labelledby="farm-world-title">
        <div><p className="kicker">{farm.location} · synthetic simulation</p><h1 id="farm-world-title">{farm.name}</h1><p>Tap a bed or visit an advisor to explore the plan.</p></div>
        <div className="world-heading__actions">
          <button className="world-chip" onClick={() => { setSelectedAdvisor(advisorById('asha')); setScenarioContext(null); setPanel('conversation') }}><Users size={17}/><span>Talk to advisors</span></button>
          <button className="world-chip" onClick={() => setPanel('quests')}><ClipboardList size={17}/><span>Quest journal</span></button>
          <button className="world-chip" onClick={() => { setQuestContext(null); setProposedAction(null); setPanel('scenarios') }}><FlaskConical size={17}/><span>Scenario lab</span></button>
          <button className="world-chip" onClick={onOpenCrops}><BookOpen size={17}/><span>Crop almanac</span></button>
        </div>
      </section>
      <aside className="room-context" aria-label="Room scope"><div><strong>Farm snapshot and main mission</strong><span>The map reads the connected farm version. Its plan count can differ from the separate current guided plan.</span></div>{guidedPlanAvailable && onReturnToGuidedPlan && <button className="button button--cream" onClick={onReturnToGuidedPlan}>Return to current guided plan</button>}</aside>

      {mission&&<DecisionMissionCard mission={mission} action={()=>{setQuestContext('busy_market');setProposedAction(null);setPanel('scenarios')}}/>}
      <NewsPanel/>

      <section className="farm-world-shell" aria-label="Interactive farm world">
        <div className="resource-hud" aria-label="Farm resources">
          <span><b>{farm.beds.filter(bed => bed.stage !== 'empty').length}</b><small>active beds</small></span>
          <span><b>{farm.resources.labour_hours_per_week}</b><small>labour hr/wk</small></span>
          <span><b>${Math.round(farm.resources.cash_sgd).toLocaleString('en-SG')}</b><small>available cash</small></span>
          <button onClick={onOpenOutcomes}><b>{run?.strategies.length || 0}</b><small>plan options</small></button>
        </div>

        <div className="map-navigation">
          <button className="world-chip" aria-pressed={moveMode} onClick={() => { finishDrag(); setMoveMode(value => !value) }}><Hand size={18}/>{moveMode ? 'Done moving · scroll page' : 'Move farm'}</button>
          <p id="map-instructions">{moveMode ? 'Drag anywhere on the farm. Tap a bed to inspect. Choose Done moving to scroll the page.' : 'Swipe to scroll the page. Choose Move farm to drag the map, or use the arrow controls. Mouse users can drag directly.'}</p>
        </div>
        <div
          ref={viewportRef}
          className={`farm-world-viewport ${moveMode ? 'is-move-mode' : ''} ${dragging ? 'is-dragging' : ''}`}
          tabIndex={0} role="group" aria-label="Farm map" aria-describedby="map-instructions"
          onKeyDown={event => {
            if (event.target !== event.currentTarget) return
            const directions: Record<string, [number, number]> = { ArrowLeft: [90, 0], ArrowRight: [-90, 0], ArrowUp: [0, 90], ArrowDown: [0, -90] }
            if (directions[event.key]) { event.preventDefault(); nudge(...directions[event.key]) }
            if (event.key === 'Home') { event.preventDefault(); recenter() }
            if (event.key === 'Escape') { finishDrag(); setMoveMode(false) }
          }}
          onClickCapture={event => { if (suppressClick.current && event.detail > 0) { event.preventDefault(); event.stopPropagation(); suppressClick.current = false } }}
          onPointerDown={event => {
            if (!event.isPrimary || event.button !== 0) return
            suppressClick.current = false
            if ((event.target as Element).closest('.world-controls')) return
            if (event.pointerType !== 'mouse' && !moveMode) return
            pointer.current = { id: event.pointerId, x: event.clientX, y: event.clientY, originX: pan.x, originY: pan.y, moved: false }
          }}
          onPointerMove={event => {
            const gesture = pointer.current
            if (!gesture || gesture.id !== event.pointerId) return
            const dx = event.clientX - gesture.x, dy = event.clientY - gesture.y
            if (!gesture.moved && Math.hypot(dx, dy) < 8) return
            if (!gesture.moved) { gesture.moved = true; setDragging(true); event.currentTarget.setPointerCapture(event.pointerId) }
            suppressClick.current = true
            setPan(boundedPan(gesture.originX + dx, gesture.originY + dy))
          }}
          onPointerUp={event => { if (pointer.current?.id === event.pointerId) { finishDrag(); if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId) } }}
          onPointerCancel={finishDrag}
          onDragStart={event => event.preventDefault()}
          onLostPointerCapture={finishDrag}
        >
          <div className="farm-world-canvas" style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})` }}>
            <FarmLandscape />
            <button className="world-facility" style={{ left: 742, top: 148 }} onClick={() => openAdvisor(advisorById('mei'))}>Visit greenhouse</button>
            <button className="world-facility" style={{ left: 430, top: 112 }} onClick={() => setPanel('list')}>View nursery schedule</button>
            <button className="world-facility" style={{ left: 855, top: 407 }} onClick={() => openAdvisor(advisorById('idris'))}>Visit market stall</button>
            <button className="world-facility" style={{ left: 174, top: 386 }} onClick={() => openAdvisor(advisorById('ben'))}>Visit accounts desk</button>
            <button className="world-facility" style={{ left: 668, top: 444 }} onClick={() => openAdvisor(advisorById('asha'))}>Enter council pavilion</button>
            <button className="world-facility" style={{ left: 869, top: 585 }} onClick={onOpenOutcomes}>Open packing schedule</button>
            <button className="world-facility" style={{ left: 934, top: 684 }} onClick={() => openAdvisor(advisorById('lina'))}>Visit packing shed</button>
            <button className="world-facility" style={{ left: 733, top: 651 }} onClick={() => openAdvisor(advisorById('idris'))}>Open market evidence</button>
            <button className="world-facility" style={{ left: 155, top: 101 }} onClick={() => openAdvisor(advisorById('hana'))}>Check weather station</button>
            {farm.beds.map((bed, index) => {
              const position = bedPosition(index)
              const state = previewBed(bed, previewDate, allocationsByBed.get(bed.id), farm.recipe_calendar)
              const crop = state.cropId ? cropMap.get(state.cropId) : undefined
              const cropImage = state.cropId && state.stage !== 'empty' ? editionPath(`/art/crops/${state.cropId}-${assetStage(state.stage)}.svg`) : null
              return (
                <button
                  key={bed.id}
                  className={`world-bed world-bed--${state.stage} ${bed.id === selectedBedId ? 'is-selected' : ''} ${affected.has(bed.id) ? 'is-affected' : ''}`}
                  style={{ left: position.x, top: position.y, zIndex: 20 + Math.round(position.y) }}
                  onClick={() => { setSelectedBedId(bed.id); setPanel('bed') }}
                  aria-label={`${bed.name}, ${crop?.label || 'empty'}, ${state.stage}, ${state.nextAction}`}
                >
                  <span className="world-bed__soil" />
                  {cropImage && <img src={cropImage} alt="" draggable={false}/>} 
                  <span className="world-bed__label"><b>{bed.name}</b><small>{crop?.label || 'Open bed'}</small></span>
                  {affected.has(bed.id) && <span className="world-bed__alert" aria-label={advisorReferenced.includes(bed.id) ? "Referenced by advisor" : "Affected by scenario"}>!</span>}
                </button>
              )
            })}
            {ADVISORS.map(advisor => {
              const position = advisorPositions[advisor.id]
              const hasNotice = Boolean(run?.claims.some(claim => roleMatchesAdvisor(claim.role, advisor.id)))
              return (
                <button key={advisor.id} className={`world-advisor world-advisor--${advisor.id}`} style={{ left: position.x, top: position.y, zIndex: 80 + position.y }} onClick={() => openAdvisor(advisor)} aria-label={`Talk to ${advisorPublicLabel(advisor)} at ${advisor.location}`}>
                  {hasNotice && <span className="world-advisor__notice">!</span>}
                  <span className="world-advisor__bubble">{advisor.prompt}</span>
                  <img src={editionPath(`/art/advisors/${advisor.id}.svg`)} alt="" draggable={false}/>
                  <span className="world-advisor__name"><b>{advisorPublicLabel(advisor)}</b></span>
                </button>
              )
            })}
          </div>

          <div className="world-controls" aria-label="Map controls">
            <button onClick={() => nudge(90, 0)} aria-label="View farm left"><ArrowLeft size={18}/></button>
            <button onClick={() => nudge(-90, 0)} aria-label="View farm right"><ArrowRight size={18}/></button>
            <button onClick={() => nudge(0, 90)} aria-label="View farm up"><ArrowUp size={18}/></button>
            <button onClick={() => nudge(0, -90)} aria-label="View farm down"><ArrowDown size={18}/></button>
            <button onClick={() => setZoom(value => clamp(value + .15, .7, 1.55))} aria-label="Zoom in"><Plus size={18}/></button>
            <button onClick={() => setZoom(value => clamp(value - .15, .7, 1.55))} aria-label="Zoom out"><Minus size={18}/></button>
            <button onClick={recenter} aria-label="Recenter farm"><Crosshair size={18}/></button>
            {moveMode&&<button onClick={()=>{finishDrag();setMoveMode(false)}} aria-label="Exit map movement">Done</button>}
          </div>
          <p className="world-pan-hint"><SlidersHorizontal size={14}/> Tap to inspect · arrows to explore</p>
        </div>

        <div className="date-preview">
          <div><CalendarDays size={18}/><span><small>Plan preview</small><strong>{formatPreviewDate(previewDate)}</strong></span></div>
          <div className="preview-day-controls"><button aria-label="Previous preview day" disabled={previewDay===0} onClick={()=>setPreviewDay(day=>Math.max(0,day-1))}><Minus size={17}/></button><input aria-label="Preview simulation date" type="range" min="0" max={Math.max(0,farm.horizon_days-1)} value={previewDay} onChange={event=>setPreviewDay(Number(event.target.value))}/><button aria-label="Next preview day" disabled={previewDay===Math.max(0,farm.horizon_days-1)} onClick={()=>setPreviewDay(day=>Math.min(Math.max(0,farm.horizon_days-1),day+1))}><Plus size={17}/></button></div>
          <button onClick={() => setPreviewDay(0)} disabled={previewDay === 0}><RotateCcw size={15}/> Today</button>
          <p>Preview only — this does not advance time or create observations.</p>
        </div>
      </section>

      <section className="world-shortcuts" aria-label="Farm shortcuts">
        <button onClick={() => setPanel('list')}><List size={19}/><span><b>Accessible farm list</b><small>All 16 beds and next actions</small></span></button>
        <button onClick={() => { setSelectedAdvisor(advisorById('asha')); setPanel('conversation') }}><Users size={19}/><span><b>Advisor shortcuts</b><small>Talk, invite or convene council</small></span></button>
        <button onClick={onOpenTools}><Wrench size={19}/><span><b>Planning tools</b><small>Strategies, timeline and resources</small></span></button>
      </section>

      <BedDetailPanel open={panel === 'bed'} bed={selectedBed} crop={selectedBed?.crop_id ? cropMap.get(selectedBed.crop_id) : undefined} farm={farm} run={run} previewDate={previewDate} allocations={selectedBed ? allocationsByBed.get(selectedBed.id) : undefined} onClose={() => setPanel(null)} onExperiment={() => { setQuestContext(null); setProposedAction(null); setPanel('scenarios') }} onAsk={() => { setSelectedAdvisor(advisorById('mei')); setScenarioContext(null); setPanel('conversation') }}/>
      <ConversationPanel open={panel === 'conversation'} advisor={selectedAdvisor} advisors={ADVISORS} farm={farm} run={run} selectedBed={selectedBed} scenario={scenarioContext} onHighlight={highlightReferences} onSelectAdvisor={setSelectedAdvisor} onClose={() => setPanel(null)} onOpenScenario={(action, conversationId) => { setProposedAction(action && conversationId ? { action, conversationId } : null); setPanel('scenarios') }}/>
      <QuestJournal open={panel === 'quests'} farm={farm} onClose={() => setPanel(null)} onStartQuest={quest => { setQuestContext(quest.id); setPanel('scenarios') }}/>
      <ScenarioLab open={panel === 'scenarios'} farm={farm} crops={crops} selectedBed={selectedBed} mission={mission} initialQuestId={questContext} proposedAction={proposedAction} onClose={() => setPanel(null)} onHighlight={ids => { setScenarioAffected(ids); if (ids[0]) setSelectedBedId(ids[0]) }} onInterpret={scenario => { setScenarioContext(scenario); setSelectedAdvisor(advisorById('asha')); setPanel('conversation') }}/>
      <AccessibleFarmView open={panel === 'list'} farm={farm} crops={cropMap} previewDate={previewDate} allocations={allocationsByBed} onSelect={bed => { setSelectedBedId(bed.id); setPanel('bed') }} onClose={() => setPanel(null)}/>
    </div>
  )
}

function FarmLandscape() {
  return (
    <svg className="farm-landscape" viewBox="0 0 1040 720" aria-hidden="true">
      <defs>
        <linearGradient id="worldGrass" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#b8cc78"/><stop offset=".55" stopColor="#8fb465"/><stop offset="1" stopColor="#779b58"/></linearGradient>
        <linearGradient id="worldPath" x1="0" y1="0" x2="0" y2="1"><stop stopColor="#eed7a5"/><stop offset="1" stopColor="#d2ae76"/></linearGradient>
        <filter id="softWorldShadow"><feDropShadow dx="0" dy="7" stdDeviation="7" floodColor="#294424" floodOpacity=".23"/></filter>
        <pattern id="grassMarks" width="26" height="22" patternUnits="userSpaceOnUse"><path d="M4 18l3-7m0 7 3-5M19 7l2-4" stroke="#5e874f" strokeWidth="1.4" opacity=".25"/></pattern>
      </defs>
      <path d="M88 250 500 30l464 255-36 310-424 106L73 500Z" fill="url(#worldGrass)" filter="url(#softWorldShadow)"/>
      <path d="M88 250 500 30l464 255-36 310-424 106L73 500Z" fill="url(#grassMarks)"/>
      <path d="M113 290 482 96l405 220-26 55-372-198-351 181Z" fill="url(#worldPath)" opacity=".9"/>
      <path d="M465 150 520 122 903 330 874 382Z" fill="#cfad79" opacity=".8"/>
      <path d="M246 536 482 410 814 590 735 631 482 493 307 583Z" fill="url(#worldPath)"/>
      <g className="world-building" filter="url(#softWorldShadow)"><path d="M708 115 811 168 744 210 638 155Z" fill="#d9efe0" stroke="#fff" strokeWidth="5"/><path d="M638 155v94l106 55v-94Z" fill="#9fcbb9"/><path d="M744 210v94l67-42v-94Z" fill="#74ad9d"/><path d="m669 171 30 15v83l-30-16Zm46 23 17 9v83l-17-9Z" fill="#eaf8ee" opacity=".72"/><text x="720" y="120">GREENHOUSE</text></g>
      <g className="world-building" filter="url(#softWorldShadow)"><path d="m804 399 89 46-67 41-91-48Z" fill="#ec8f55"/><path d="m735 438 91 48v69l-91-47Z" fill="#b8653f"/><path d="m826 486 67-41v70l-67 40Z" fill="#8e513b"/><path d="m721 426 107-60 84 43-106 59Z" fill="#f3c067"/><text x="800" y="380">MARKET</text></g>
      <g className="world-building" filter="url(#softWorldShadow)"><path d="m410 92 75 39-56 34-76-40Z" fill="#f0d29b"/><path d="m354 125 75 40v55l-75-39Z" fill="#b97d55"/><path d="m429 165 56-34v55l-56 34Z" fill="#916143"/><text x="377" y="92">NURSERY</text></g>
      <g className="world-building" filter="url(#softWorldShadow)"><path d="m84 426 112-60 88 47-112 62Z" fill="#789785"/><path d="m104 419 67 36v97l-67-36Z" fill="#9d7251"/><path d="m171 455 91-50v96l-91 51Z" fill="#72543f"/><path d="m82 407 93-51 108 57-22 13-86-46-72 39Z" fill="#446553"/><text x="115" y="365">TOOL SHED</text></g>
      <g className="world-building" filter="url(#softWorldShadow)"><path d="M590 520h154l46 26-124 68-125-68Z" fill="#e9d7aa"/><path d="M604 519h128l-13-89H617Z" fill="#fff1c5"/><path d="m616 430 53-42 64 42Z" fill="#e68167"/><path d="M647 451h52v69h-52Z" fill="#9c6a4d"/><text x="620" y="400">COUNCIL</text></g>
      <g className="world-building" filter="url(#softWorldShadow)"><path d="m844 570 80 42-60 36-82-43Z" fill="#dbb47b"/><path d="m783 605 81 43v48l-81-42Z" fill="#95684d"/><path d="m864 648 60-36v48l-60 36Z" fill="#704f3e"/><text x="808" y="570">PACKING SHED</text></g>
      <g className="world-building" filter="url(#softWorldShadow)"><path d="m734 648 60 31-45 27-61-32Z" fill="#ece2bd"/><path d="m688 674 61 32v28l-61-31Z" fill="#9c7457"/><text x="672" y="646">EVIDENCE DESK</text></g>
      <g className="weather-station"><path d="M157 107v84m-31-63h65m-33-19 30 18-30 17-30-17Z" stroke="#f6f0d9" strokeWidth="6" strokeLinecap="round"/><circle cx="157" cy="105" r="8" fill="#e87e61"/><text x="96" y="91">WEATHER</text></g>
      <g className="world-tree" fill="#47784d"><circle cx="96" cy="255" r="30"/><circle cx="125" cy="246" r="27"/><circle cx="111" cy="222" r="25"/><path d="M109 248v62" stroke="#78583e" strokeWidth="12"/></g>
      <g className="world-tree" fill="#47784d"><circle cx="913" cy="265" r="29"/><circle cx="940" cy="285" r="25"/><circle cx="931" cy="250" r="24"/><path d="M929 278v65" stroke="#78583e" strokeWidth="12"/></g>
      <g className="world-pond"><ellipse cx="380" cy="618" rx="103" ry="43" fill="#73afae"/><ellipse cx="380" cy="611" rx="91" ry="31" fill="#9fd0c4"/><path d="m323 613 21-7m52 12 29-9m16 13 22-4" stroke="#e7f1d5" strokeWidth="4" strokeLinecap="round"/></g>
    </svg>
  )
}

function bedPosition(index: number) {
  const row = Math.floor(index / 4)
  const column = index % 4
  return { x: 328 + column * 108 - row * 56, y: 235 + row * 67 + column * 31 }
}

export function previewBed(bed: Bed, date: Date, allocations: Allocation[] = [], recipeCalendar: Farm['recipe_calendar'] = null) {
  const scheduled = allocations.find(item => date >= parseDate(item.sow_date) && date < nextAvailable(item, recipeCalendar)) || allocations.find(item => date < parseDate(item.sow_date))
  if (scheduled) {
    const sow = parseDate(scheduled.sow_date), transplant = parseDate(scheduled.transplant_date), harvest = parseDate(scheduled.harvest_date)
    const sanitationEnd = sanitationEndDate(scheduled, recipeCalendar)
    if (date < sow) return { stage: 'empty' as const, progress: 0, cropId: scheduled.crop_id, nextAction: `Sow ${scheduled.crop_id.replaceAll('_', ' ')} on ${formatPreviewDate(sow)}` }
    const progress = clamp((date.getTime() - sow.getTime()) / Math.max(1, harvest.getTime() - sow.getTime()) * 100, 0, 100)
    if (date < transplant) return { stage: 'nursery' as const, progress, cropId: scheduled.crop_id, nextAction: `Transplant on ${formatPreviewDate(transplant)}` }
    if (date < harvest) return { stage: 'growing' as const, progress, cropId: scheduled.crop_id, nextAction: `Inspect growth · harvest ${formatPreviewDate(harvest)}` }
    if (date.getTime() === harvest.getTime()) return { stage: 'ready' as const, progress: 100, cropId: scheduled.crop_id, nextAction: `Harvest ${scheduled.crop_id.replaceAll('_', ' ')}` }
    if (date <= sanitationEnd) return { stage: 'sanitation' as const, progress: 100, cropId: undefined, nextAction: `Sanitation through ${formatPreviewDate(sanitationEnd)}` }
    return { stage: 'empty' as const, progress: 100, cropId: undefined, nextAction: 'Bed available' }
  }
  if (!bed.crop_id || bed.stage === 'empty') return { stage: 'empty' as const, progress: 0, cropId: undefined, nextAction: 'Choose a crop' }
  const sow = bed.sow_date ? parseDate(bed.sow_date) : null
  const transplant = bed.transplant_date ? parseDate(bed.transplant_date) : null
  const harvest = bed.harvest_date ? parseDate(bed.harvest_date) : null
  const sanitationEnd = typeof bed.sanitation_end_date === 'string' ? parseDate(bed.sanitation_end_date) : harvest
  if (harvest && date.getTime() === harvest.getTime()) return { stage: 'ready' as const, progress: 100, cropId: bed.crop_id, nextAction: `Harvest ${bed.crop_id.replaceAll('_', ' ')}` }
  if (harvest && date > harvest && sanitationEnd && date <= sanitationEnd) return { stage: 'sanitation' as const, progress: 100, cropId: undefined, nextAction: `Sanitation through ${formatPreviewDate(sanitationEnd)}` }
  if (harvest && date > harvest) return { stage: 'empty' as const, progress: 100, cropId: undefined, nextAction: 'Bed available after sanitation' }
  if (sow && date < sow) return { stage: 'empty' as const, progress: 0, cropId: bed.crop_id, nextAction: `Sow on ${formatPreviewDate(sow)}` }
  if (sow && harvest) {
    const progress = clamp((date.getTime() - sow.getTime()) / (harvest.getTime() - sow.getTime()) * 100, 0, 100)
    return { stage: transplant && date < transplant ? 'nursery' as const : 'growing' as const, progress, cropId: bed.crop_id, nextAction: transplant && date < transplant ? `Transplant on ${formatPreviewDate(transplant)}` : `Inspect growth · harvest ${formatPreviewDate(harvest)}` }
  }
  return { stage: bed.stage, progress: bed.progress * (bed.progress <= 1 ? 100 : 1), cropId: bed.crop_id, nextAction: 'Inspect crop status' }
}

function assetStage(stage: Bed['stage']) { return stage === 'nursery' ? 'seedling' : stage === 'ready' ? 'ready' : 'growing' }
function addDays(iso: string, days: number) { const date = new Date(`${iso.slice(0, 10)}T00:00:00Z`); date.setUTCDate(date.getUTCDate() + days); return date }
function parseDate(iso: string) { return new Date(`${iso.slice(0, 10)}T00:00:00Z`) }
function sanitationEndDate(allocation: Allocation, calendar: Farm['recipe_calendar']) {
  if (typeof allocation.sanitation_end_date === 'string') return parseDate(allocation.sanitation_end_date)
  const recipe = allocation.recipe_id ? calendar?.[allocation.recipe_id] : undefined
  const days = Number(recipe?.sanitation_days)
  return addDays(allocation.harvest_date, Number.isFinite(days) && days >= 0 ? days : 0)
}
function nextAvailable(allocation: Allocation, calendar: Farm['recipe_calendar']) {
  if (typeof allocation.next_available_date === 'string') return parseDate(allocation.next_available_date)
  const end = sanitationEndDate(allocation, calendar)
  end.setUTCDate(end.getUTCDate() + 1)
  return end
}
function singaporeCivilDate(iso: string) {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso.slice(0, 10)
  const parts = new Intl.DateTimeFormat('en-CA', { timeZone: 'Asia/Singapore', year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(date)
  const value = Object.fromEntries(parts.map(part => [part.type, part.value]))
  return `${value.year}-${value.month}-${value.day}`
}
export function formatPreviewDate(date: Date) { return new Intl.DateTimeFormat('en-SG', { day: 'numeric', month: 'short', timeZone: 'UTC' }).format(date) }
function clamp(value: number, min: number, max: number) { return Math.max(min, Math.min(max, value)) }
function roleMatchesAdvisor(role: string, advisor: AdvisorId) {
  const roleMap: Record<AdvisorId, string[]> = { mei: ['production', 'crop', 'scientist'], ravi: ['demand'], hana: ['weather'], ben: ['profit', 'resource'], asha: ['chair', 'planner'], idris: ['market'], lina: ['supply_chain', 'supply chain'] }
  return roleMap[advisor].some(part => role.toLowerCase().includes(part))
}
