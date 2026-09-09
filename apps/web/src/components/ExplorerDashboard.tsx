import type { DatasetKey, ExplorerDetail, ExplorerRecord, Policy } from '../lib/explorer'
import { ChartTable, ExplorerChart, type ChartPoint } from './ExplorerChart'

const numeric = (value: unknown): value is number | string => value !== null && value !== '' && Number.isFinite(Number(value))
const title = (value: string) => value.replaceAll('_',' ').replace(/\b\w/g, letter => letter.toUpperCase())
const dated = (record: ExplorerRecord) => String(record.date || record.harvest_date || record.due_date || '')
const inRange = (record: ExplorerRecord, start: string, end: string) => (!start || !dated(record) || dated(record) >= start) && (!end || !dated(record) || dated(record) <= end)
const forCrop = (record: ExplorerRecord, crop: string) => !crop || record.crop_id === crop
const amount = (value: unknown) => Number(value).toLocaleString('en-SG', { maximumFractionDigits: 2 })

function Empty({ children }: { children: string }) {
  return <div className="explorer-empty">{children}</div>
}

function TimePanel({ kicker, heading, explanation, points, unit, planningDate, dataset, onOpen }: { kicker: string; heading: string; explanation: string; points: ChartPoint[]; unit: string; planningDate: string; dataset: DatasetKey; onOpen: (dataset: DatasetKey,id: string) => void }) {
  return <section className="explorer-card explorer-wide">
    <p className="kicker">{kicker}</p><h2>{heading}</h2><p>{explanation}</p>
    {points.length ? <><ExplorerChart points={points} unit={unit} planningDate={planningDate} onSelect={id => onOpen(dataset,id)}/><ChartTable points={points} unit={unit} onSelect={id => onOpen(dataset,id)}/></> : <Empty>No linked numeric records match the selected crop and date range.</Empty>}
  </section>
}

function ResourcePanel({ detail, crop, start, end, onOpen }: { detail: ExplorerDetail; crop: string; start: string; end: string; onOpen: (dataset: DatasetKey,id: string) => void }) {
  const rows = (detail.records.weekly || []).filter(row => inRange(row,start,end))
  if (crop) return <section className="explorer-card explorer-wide"><p className="kicker">Whole-farm capacity</p><h2>Labour and nursery reservations</h2><Empty>Resource reservations are farm-wide and cannot be attributed safely to the selected crop. Choose All crops to view them.</Empty></section>
  const labour = rows.flatMap<ChartPoint>(row => numeric(row.labour_hours) && numeric(row.labour_capacity_hours) ? [
    { id: `labour|reserved|${row.id}`, date: dated(row), value: Number(row.labour_hours), label: 'Reserved labour', series: 'Reserved labour', future: dated(row) >= detail.planning_date },
    { id: `labour|capacity|${row.id}`, date: dated(row), value: Number(row.labour_capacity_hours), label: 'Weekly labour capacity', series: 'Weekly labour capacity', future: dated(row) >= detail.planning_date },
  ] : [])
  const nursery = rows.flatMap<ChartPoint>(row => numeric(row.nursery_peak_sites) && numeric(row.nursery_capacity_sites) ? [
    { id: `nursery|reserved|${row.id}`, date: dated(row), value: Number(row.nursery_peak_sites), label: 'Peak reserved nursery sites', series: 'Peak reserved nursery sites', future: dated(row) >= detail.planning_date },
    { id: `nursery|capacity|${row.id}`, date: dated(row), value: Number(row.nursery_capacity_sites), label: 'Nursery site capacity', series: 'Nursery site capacity', future: dated(row) >= detail.planning_date },
  ] : [])
  const sourceId = (id: string) => id.split('|').slice(2).join('|')
  return <section className="explorer-card explorer-wide"><p className="kicker">Whole-farm resource model</p><h2>Reserved capacity by week</h2><p>Reservations and declared limits for this frozen snapshot. These are planning quantities, not measured use.</p>
    {rows.length ? <div className="explorer-grid"><div><h3>Labour</h3><ExplorerChart points={labour} unit="hours" planningDate={detail.planning_date} onSelect={id=>onOpen('weekly',sourceId(id))}/><ChartTable points={labour} unit="hours" onSelect={id=>onOpen('weekly',sourceId(id))}/></div><div><h3>Nursery</h3><ExplorerChart points={nursery} unit="sites" planningDate={detail.planning_date} onSelect={id=>onOpen('weekly',sourceId(id))}/><ChartTable points={nursery} unit="sites" onSelect={id=>onOpen('weekly',sourceId(id))}/></div></div> : <Empty>{`Run the numerical strategies to calculate weekly reservations. Declared capacity is ${amount(detail.farm.resources.labour_hours_per_week)} labour hours per week and ${amount(detail.farm.resources.nursery_sites)} nursery sites.`}</Empty>}
  </section>
}

function FinancialPanel({ detail, crop, policy }: { detail: ExplorerDetail; crop: string; policy: Policy }) {
  const strategies = detail.result?.strategies || []
  if (crop) return <section className="explorer-card explorer-wide"><p className="kicker">Whole-farm simulation</p><h2>Cost and margin comparison</h2><Empty>Financial results are whole-farm simulated totals and cannot be attributed safely to the selected crop. Choose All crops to view them.</Empty></section>
  if (!strategies.length) return <section className="explorer-card explorer-wide"><p className="kicker">Whole-farm simulation</p><h2>Cost and margin comparison</h2><Empty>Run the numerical strategies for this snapshot to calculate costs and simulated margins.</Empty></section>
  const ceiling = Math.max(1,...strategies.flatMap(strategy => [Math.abs(Number(strategy.metrics.cost_sgd)),Math.abs(Number(strategy.metrics.margin_sgd))]))
  return <section className="explorer-card explorer-wide"><p className="kicker">Whole-farm simulated outcome</p><h2>Cost and margin by strategy</h2><p>Computed across the frozen snapshot’s full planning horizon; the date filter does not subset these totals. Bars share one SGD scale; negative margins remain labelled in the table. {policy} is the selected policy.</p>
    <div role="img" aria-label="Comparison of simulated whole-farm cost and margin in Singapore dollars">{strategies.map(strategy => <div key={strategy.id} style={{ marginBlock: 12 }}><strong>{strategy.name}{strategy.name===policy?' · selected':''}</strong><div aria-hidden="true" style={{ display:'grid', gap:4, marginTop:5 }}><span style={{ display:'block', width:`${Math.abs(Number(strategy.metrics.cost_sgd))/ceiling*100}%`, minWidth:2, height:12, borderRadius:6, background:'#b46148' }}/><span style={{ display:'block', width:`${Math.abs(Number(strategy.metrics.margin_sgd))/ceiling*100}%`, minWidth:2, height:12, borderRadius:6, background:Number(strategy.metrics.margin_sgd)>=0?'#315f42':'#8f3946' }}/></div></div>)}</div>
    <div className="table-scroll"><table><caption>Equivalent simulated financial results and recorded cost components</caption><thead><tr><th>Strategy</th><th>Total cost</th><th>Simulated margin</th><th>Inputs</th><th>Labour</th><th>Packing</th><th>Disposal</th></tr></thead><tbody>{strategies.map(strategy => {const costs=strategy.cost_breakdown||{};return <tr key={strategy.id}><th>{strategy.name}{strategy.name===policy?' (selected)':''}</th><td>{amount(strategy.metrics.cost_sgd)} SGD</td><td>{amount(strategy.metrics.margin_sgd)} SGD</td><td>{numeric(costs.inputs_sgd)?`${amount(costs.inputs_sgd)} SGD`:'—'}</td><td>{numeric(costs.labour_sgd)?`${amount(costs.labour_sgd)} SGD`:'—'}</td><td>{numeric(costs.packing_sgd)?`${amount(costs.packing_sgd)} SGD`:'—'}</td><td>{numeric(costs.disposal_sgd)?`${amount(costs.disposal_sgd)} SGD`:'—'}</td></tr>})}</tbody></table></div>
  </section>
}

export function ExplorerDashboard({ detail, crop, start, end, policy, onOpen }: { detail: ExplorerDetail; crop: string; start: string; end: string; policy: Policy; onOpen: (dataset: DatasetKey,id: string) => void }) {
  const batches = (detail.records.batches || []).filter(row => forCrop(row,crop) && inRange(row,start,end))
  const harvestPoints = batches.flatMap<ChartPoint>(row => numeric(row.expected_marketable_kg) && dated(row) ? [{ id:row.id,date:dated(row),value:Number(row.expected_marketable_kg),label:`${row.crop_id ? title(String(row.crop_id)) : 'Crop'} scheduled harvest`,series:`${row.crop_id ? title(String(row.crop_id)) : 'Crop'} scheduled harvest`,future:dated(row)>=detail.planning_date }] : [])

  const demand = (detail.records.forecast || []).filter(row => forCrop(row,crop) && inRange(row,start,end))
  const demandPoints = demand.flatMap<ChartPoint>(row => {
    if (!dated(row)) return []
    const result: ChartPoint[]=[]
    if (numeric(row.expected_kg)) result.push({id:`forecast|expected|${row.id}`,date:dated(row),value:Number(row.expected_kg),label:`${row.crop_id ? title(String(row.crop_id)) : 'Crop'} total demand due`,series:`${row.crop_id ? title(String(row.crop_id)) : 'Crop'} total demand due`,future:dated(row)>=detail.planning_date})
    if (numeric(row.confirmed_kg)) result.push({id:`forecast|confirmed|${row.id}`,date:dated(row),value:Number(row.confirmed_kg),label:`${row.crop_id ? title(String(row.crop_id)) : 'Crop'} confirmed demand due`,series:`${row.crop_id ? title(String(row.crop_id)) : 'Crop'} confirmed demand due`,future:dated(row)>=detail.planning_date})
    return result
  })
  const allocationRows = detail.records.allocations || []
  const supplyDataset: DatasetKey = allocationRows.length ? 'allocations' : 'batches'
  const supplyRows = (allocationRows.length ? allocationRows : batches).filter(row => forCrop(row,crop) && inRange(row,start,end))
  const supplyPoints = supplyRows.flatMap<ChartPoint>(row => {
    const value = numeric(row.expected_kg) ? row.expected_kg : row.expected_marketable_kg
    return numeric(value) && dated(row) ? [{id:row.id,date:dated(row),value:Number(value),label:`${row.crop_id ? title(String(row.crop_id)) : 'Crop'} supply arrival`,series:`${row.crop_id ? title(String(row.crop_id)) : 'Crop'} supply arrival`,future:dated(row)>=detail.planning_date}] : []
  })

  return <>
    <TimePanel kicker="Declared crop schedule" heading="Scheduled harvest arrivals" explanation="Expected fresh marketable kilograms become available only on each recorded harvest date." points={harvestPoints} unit="kg" planningDate={detail.planning_date} dataset="batches" onOpen={onOpen}/>
    <section className="explorer-card explorer-wide"><p className="kicker">Due demand and dated supply</p><h2>Supply arrivals versus demand due</h2><p>Each quantity stays on its own arrival or due date. This comparison does not claim that later supply fulfils earlier demand.</p>
      {demandPoints.length || supplyPoints.length ? <div className="explorer-grid"><div><h3>Demand due</h3>{demandPoints.length?<><ExplorerChart points={demandPoints} unit="kg" planningDate={detail.planning_date} onSelect={id=>onOpen('forecast',id.split('|').slice(2).join('|'))}/><ChartTable points={demandPoints} unit="kg" onSelect={id=>onOpen('forecast',id.split('|').slice(2).join('|'))}/></>:<Empty>No forecast demand matches these filters.</Empty>}</div><div><h3>Scheduled supply arrivals</h3>{supplyPoints.length?<><ExplorerChart points={supplyPoints} unit="kg" planningDate={detail.planning_date} onSelect={id=>onOpen(supplyDataset,id)}/><ChartTable points={supplyPoints} unit="kg" onSelect={id=>onOpen(supplyDataset,id)}/></>:<Empty>No scheduled supply matches these filters.</Empty>}</div></div> : <Empty>No due demand or scheduled supply matches the selected crop and date range.</Empty>}
    </section>
    <ResourcePanel detail={detail} crop={crop} start={start} end={end} onOpen={onOpen}/>
    <FinancialPanel detail={detail} crop={crop} policy={policy}/>
  </>
}
