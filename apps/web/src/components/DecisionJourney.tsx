import { AlertTriangle, ArrowRight, CalendarDays, CheckCircle2, Database, FlaskConical, LoaderCircle } from 'lucide-react'
import { useState } from 'react'
import type { ExplorerDetail, ExplorerRecord } from '../lib/explorer'
import { api } from '../lib/api'
import type { PolicyComparison, Scenario } from '../lib/game'
import { ADVISORS } from '../lib/game'
import { editionStorageKey } from '../lib/edition'

export interface DecisionMission {
  snapshotId: string
  snapshotKind: string
  snapshotHash: string
  cropId: string
  date: string
  bookedKg: number
  eligibleHarvestKg: number
  usableInventoryKg: number
  provisionalGapKg: number
  forecastId: string
  weeklyForecastKg: number
  evidenceIds: string[]
  planningDate: string
  earliestNewHarvest?: string
  recipeDays?: number
}
const MISSION_STORAGE_VERSION='dated-order-mission-v1'

const number = (value: unknown) => Number.isFinite(Number(value)) ? Number(value) : 0
const dateOf = (row: ExplorerRecord) => String(row.date || row.harvest_date || row.due_date || '')
const pretty = (value: string) => new Intl.DateTimeFormat('en-SG', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(new Date(`${value}T00:00:00Z`))
const kg = (value: number) => value.toLocaleString('en-SG', { maximumFractionDigits: 1 })
const addDays = (date: string, days: number) => { const value = new Date(`${date}T00:00:00Z`); value.setUTCDate(value.getUTCDate() + days); return value.toISOString().slice(0, 10) }
const ids = (value: unknown) => Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string') : []

/** A screening gap only: prior harvest allocation and storage losses are not modelled here. */
export function deriveDecisionMission(detail: ExplorerDetail): DecisionMission | null {
  const groups=new Map<string,ExplorerRecord[]>()
  for(const order of detail.records.orders||[]){const date=String(order.due_date||order.date||'');if(!order.crop_id||date<detail.planning_date)continue;const key=`${order.crop_id}|${date}`;groups.set(key,[...(groups.get(key)||[]),order])}
  const candidates = [...groups.entries()].map(([key,orders]) => {
    const [cropId,date]=key.split('|')
    const recipes = new Map((detail.records.recipes||[]).map(recipe=>[String(recipe.id),recipe]))
    const batches = (detail.records.batches || []).filter(batch => {
      if(batch.crop_id!==cropId||dateOf(batch)>date)return false
      const recipe=recipes.get(String(batch.recipe_id)),shelfDays=number(recipe?.shelf_life_days)
      return dateOf(batch)&&addDays(dateOf(batch),shelfDays)>=date
    })
    const inventory = (detail.records.inventory || []).filter(lot => lot.crop_id === cropId && (!lot.harvested_date || String(lot.harvested_date) <= date) && (!lot.expires_date || String(lot.expires_date) >= date))
    const eligibleHarvestKg = batches.reduce((sum, batch) => sum + number(batch.expected_marketable_kg ?? batch.expected_kg), 0)
    const usableInventoryKg = inventory.reduce((sum, lot) => sum + number(lot.quantity_kg), 0)
    const bookedKg=orders.reduce((sum,order)=>sum+Math.max(0,number(order.quantity_kg)-number(order.cancelled_kg)),0)
    const provisionalGapKg = Math.max(0, bookedKg - eligibleHarvestKg - usableInventoryKg)
    const forecast=(detail.records.forecast||[]).find(row=>row.crop_id===cropId&&dateOf(row)<=date&&addDays(dateOf(row),6)>=date)
    const recipe = (detail.records.recipes || []).find(item => item.crop_id === cropId)
    const declaredStages = number(recipe?.nursery_days) + number(recipe?.grow_days)
    const recipeDays = declaredStages || number(recipe?.cycle_days || recipe?.total_cycle_days || recipe?.days_to_harvest) || undefined
    return {
      snapshotId: detail.id, snapshotKind:detail.kind, snapshotHash: detail.content_hash, cropId, date, bookedKg, eligibleHarvestKg, usableInventoryKg,
      provisionalGapKg, forecastId: forecast?.id||'', weeklyForecastKg:number(forecast?.expected_kg), planningDate: detail.planning_date, recipeDays,
      earliestNewHarvest: recipeDays ? addDays(detail.planning_date, recipeDays) : undefined,
      evidenceIds: [...new Set([...orders.map(item=>item.id),...(forecast?[forecast.id,...ids(forecast.history_record_ids),...ids(forecast.order_record_ids)]:[]), ...batches.map(item => item.id), ...inventory.map(item => item.id)])],
    }
  }).filter(item => item.provisionalGapKg > 0)
  return candidates.sort((a, b) => a.date.localeCompare(b.date) || b.provisionalGapKg - a.provisionalGapKg)[0] || null
}

export function loadDecisionMission(): DecisionMission | null {
  try {
    const stored=JSON.parse(window.sessionStorage.getItem(editionStorageKey('decision-mission'))||'null') as {version?:unknown;mission?:unknown}|null
    return stored?.version===MISSION_STORAGE_VERSION&&validMission(stored.mission)?stored.mission:null
  } catch { return null }
}
export function saveDecisionMission(mission: DecisionMission | null) {
  try { if (mission&&validMission(mission)) window.sessionStorage.setItem(editionStorageKey('decision-mission'), JSON.stringify({version:MISSION_STORAGE_VERSION,mission})); else window.sessionStorage.removeItem(editionStorageKey('decision-mission')) } catch { /* Session storage is optional. */ }
}

function validMission(value:unknown):value is DecisionMission{
  if(!value||typeof value!=='object')return false
  const item=value as Record<string,unknown>,strings=['snapshotId','snapshotKind','snapshotHash','cropId','date','forecastId','planningDate'],numbers=['bookedKg','eligibleHarvestKg','usableInventoryKg','provisionalGapKg','weeklyForecastKg']
  if(strings.some(key=>typeof item[key]!=='string'||!item[key]))return false
  if(!/^\d{4}-\d{2}-\d{2}$/.test(String(item.date))||!/^\d{4}-\d{2}-\d{2}$/.test(String(item.planningDate)))return false
  if(numbers.some(key=>typeof item[key]!=='number'||!Number.isFinite(item[key])||Number(item[key])<0))return false
  if(!Array.isArray(item.evidenceIds)||item.evidenceIds.some(id=>typeof id!=='string'||!id))return false
  if(item.recipeDays!==undefined&&(typeof item.recipeDays!=='number'||!Number.isFinite(item.recipeDays)||item.recipeDays<=0))return false
  if(item.earliestNewHarvest!==undefined&&(typeof item.earliestNewHarvest!=='string'||!/^\d{4}-\d{2}-\d{2}$/.test(item.earliestNewHarvest)))return false
  return true
}

export function DecisionMissionCard({ mission, action, actionLabel = 'Test this mission', compact = false }: { mission: DecisionMission; action?: () => void; actionLabel?: string; compact?: boolean }) {
  const maturityMiss = Boolean(mission.earliestNewHarvest && mission.earliestNewHarvest > mission.date)
  const [records,setRecords]=useState<ExplorerRecord[]|null>(null),[recordError,setRecordError]=useState(''),[recordBusy,setRecordBusy]=useState(false)
  const inspect=async()=>{setRecordBusy(true);setRecordError('');try{const detail=await api.explorerSnapshot(mission.snapshotId);const linked=Object.values(detail.records).flat().filter(record=>mission.evidenceIds.includes(record.id));setRecords(linked)}catch(error){setRecordError(error instanceof Error?error.message:'Linked records are unavailable.')}finally{setRecordBusy(false)}}
  return <section className={`decision-mission ${compact ? 'decision-mission--compact' : ''}`} aria-label="Current planning mission">
    <div className="decision-mission__heading"><span><AlertTriangle size={18}/></span><div><p className="kicker">Recommended mission · provisional supply gap</p><h2>Can we cover {label(mission.cropId)} due {pretty(mission.date)}?</h2></div></div>
    <div className="decision-mission__numbers"><span><b>{kg(mission.bookedKg)} kg</b> booked for this date</span><span><b>{kg(mission.eligibleHarvestKg)} kg</b> harvest eligible by shelf life</span><span><b>{kg(mission.usableInventoryKg)} kg</b> inventory valid on due date</span><span className="is-gap"><b>{kg(mission.provisionalGapKg)} kg</b> gap to investigate</span></div>
    <p>This screening comparison uses dated booked orders. It does not allocate an eligible harvest or inventory lot across earlier orders; the numerical planner decides actual shortfall. {mission.forecastId?`The containing week’s statistical forecast is ${kg(mission.weeklyForecastKg)} kg and remains context, not this order’s due quantity.`:''}</p>
    {maturityMiss && <p className="decision-mission__timing"><CalendarDays size={15}/> A new sowing using the declared {mission.recipeDays}-day recipe would mature around {pretty(mission.earliestNewHarvest!)}—after this delivery.</p>}
    <div className="decision-mission__meta"><button className="text-button" aria-expanded={records!==null} onClick={()=>records===null?void inspect():setRecords(null)} disabled={recordBusy}>{recordBusy?<LoaderCircle className="spinner-icon" size={14}/>:<Database size={14}/>} Inspect {mission.evidenceIds.length} linked input records</button><span>Snapshot {mission.snapshotHash.slice(0, 10)}</span>{action && <button className="button button--coral" onClick={action}><FlaskConical size={16}/>{actionLabel}<ArrowRight size={15}/></button>}</div>
    {recordError&&<p className="panel-error" role="alert">{recordError}</p>}
    {records&&<div className="decision-mission__records"><p>Only records contributing to this screen are shown. Expand a row for its curated fields.</p>{records.length?records.map(record=><details key={record.id}><summary>{String(record.id)} · {String(record.crop_id||record.date||record.due_date||'farm-wide')}</summary><pre>{JSON.stringify(record,null,2)}</pre></details>):<p>No linked records were returned for this owned snapshot.</p>}</div>}
  </section>
}

type Perspective = { advisorId: typeof ADVISORS[number]['id']; stance: 'supports' | 'warns' | 'blocks' | 'unknown'; statement: string; evidence: string; facts: string[] }

function change(value: number | undefined, subject: string, unit: string) { return typeof value !== 'number' ? `${subject} was not calculated` : value===0?`${subject} is unchanged`:`${subject} ${value>0?'increases':'decreases'} by ${Math.abs(value).toLocaleString('en-SG',{maximumFractionDigits:1})}${unit}` }
function constraintFact(value:unknown){if(typeof value==='string')return value.replaceAll('_',' ');if(!value||typeof value!=='object')return 'Constraint issue';const item=value as Record<string,unknown>,label=String(item.constraint_code||item.message||'Constraint issue').replaceAll('_',' '),entity=item.entity_id?` for ${String(item.entity_id).replaceAll('_',' ')}`:'',amount=item.required!==undefined&&item.available!==undefined?`: ${String(item.required)} ${String(item.unit||'')} required; ${String(item.available)} ${String(item.unit||'')} available`:'';return `${label}${entity}${amount}`}

export function NumericalPerspectives({ scenario, policy, mission }: { scenario: Scenario; policy: string; mission?: DecisionMission | null }) {
  const row = scenario.policy_comparisons?.find(item => item.policy === policy) as PolicyComparison | undefined
  if (!row) return null
  const d = row.deltas || {}, controls = scenario.controls, violations = row.violations || []
  const maturityMiss = Boolean(mission?.earliestNewHarvest && mission.earliestNewHarvest > mission.date)
  const perspectives: Perspective[] = [
    { advisorId: 'ravi', stance: Number(row.scenario_metrics?.shortfall_kg || 0) > 0 ? 'warns' : 'supports', statement: `Demand is ${controls.demand_percent}% of the frozen baseline; ${change(d.shortfall_kg,'unfilled demand',' kg')}.`, evidence: row.scenario_strategy_id, facts:[`Demand control: ${controls.demand_percent}%`,`Scenario shortfall: ${Number(row.scenario_metrics?.shortfall_kg||0).toFixed(1)} kg`,`Shortfall change: ${Number(d.shortfall_kg||0).toFixed(1)} kg`] },
    { advisorId: 'hana', stance: 'unknown', statement: 'No weather control changed in this numerical branch, so no weather or yield adjustment is claimed.', evidence: scenario.input_hash || 'frozen input', facts:['Weather input: none','Yield response attributed to weather: none'] },
    { advisorId: 'idris', stance: controls.demand_percent !== 100 ? 'warns' : 'unknown', statement: `The ${controls.demand_percent}% demand value is a player assumption, not observed market sentiment or a connected social feed.`, evidence: `control:demand_percent:${controls.demand_percent}`, facts:[`Player-set demand: ${controls.demand_percent}%`,'Observed sentiment records: none'] },
    { advisorId: 'mei', stance: maturityMiss ? 'blocks' : controls.delay_days > 0 || controls.yield_percent < 100 ? 'warns' : 'supports', statement: maturityMiss ? `This specific new-sowing option matures after the selected delivery under the declared ${mission?.recipeDays}-day recipe; the recorded solver result remains separately inspectable.` : `Harvest delay is ${controls.delay_days} days and expected yield is ${controls.yield_percent}% of baseline.`, evidence: mission?.forecastId || String(controls.batch_id || 'selected batch'), facts:[`Harvest delay: ${controls.delay_days} days`,`Yield control: ${controls.yield_percent}%`,...(mission?.earliestNewHarvest?[`Earliest new harvest: ${mission.earliestNewHarvest}`]:[])] },
    { advisorId: 'lina', stance: (scenario.affected_deliveries?.length || 0) > 0 ? 'warns' : 'supports', statement: `${scenario.affected_deliveries?.length || 0} deliveries and ${scenario.affected_bed_ids?.length || 0} beds need inspection in the computed branch.`, evidence: scenario.id, facts:[`Deliveries to inspect: ${scenario.affected_deliveries?.length||0}`,`Affected beds: ${scenario.affected_bed_ids?.length||0}`] },
    { advisorId: 'ben', stance: Number(d.margin_sgd || 0) < 0 ? 'warns' : 'supports', statement: `${change(d.margin_sgd,'Contribution margin',' SGD')}; ${change(d.cost_sgd,'total cost',' SGD')}.`, evidence: row.scenario_strategy_id, facts:[`Margin delta: ${Number(d.margin_sgd||0).toFixed(1)} SGD`,`Cost delta: ${Number(d.cost_sgd||0).toFixed(1)} SGD`] },
    { advisorId: 'asha', stance: row.scenario_status === 'FEASIBLE' && violations.length === 0 ? 'supports' : 'blocks', statement: row.scenario_status === 'FEASIBLE' && violations.length === 0 ? `${policy} passes the recorded numerical constraints; compare service, waste, labour and margin before using this simulation.` : `${policy} has ${violations.length} recorded constraint issue${violations.length === 1 ? '' : 's'} and is not a feasible recommendation.`, evidence: `${row.scenario_strategy_id} · ${scenario.input_hash?.slice(0, 10) || 'frozen'}`, facts:[`Solver status: ${row.scenario_status}`,`Recorded violations: ${violations.length}`,...violations.slice(0,3).map(constraintFact)] },
  ]
  return <section className="numerical-perspectives" aria-label={`Computed numerical perspectives for ${policy}`}>
    <header><div><p className="kicker">Computed perspectives · numerical, no inference</p><h3>Seven views of the trade-off</h3></div><span>These are deterministic templates over frozen results, not agent messages. They may agree, disagree or lack an input.</span></header>
    <div>{perspectives.map(item => { const advisor = ADVISORS.find(value => value.id === item.advisorId)!; return <article key={item.advisorId} className={`perspective-card perspective-card--${item.stance}`}><span className="perspective-card__stance">{item.stance}</span><h4>{advisor.name} · {advisor.role}</h4><p>{item.statement}</p><details><summary>Evidence used</summary><ul>{item.facts.map(fact=><li key={fact}>{fact}</li>)}</ul><small>Frozen record: {item.evidence}</small></details></article> })}</div>
    <p className="numerical-perspectives__action"><CheckCircle2 size={15}/> For an actual paid council interpretation, open Asha and deliberately send a question or choose Convene council.</p>
  </section>
}

function label(value: string) { return value.replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase()) }
