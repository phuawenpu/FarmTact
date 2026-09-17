import type { Farm, Strategy } from '../lib/types'
import { RecordFacts } from './ToolCard'

const value = (input: unknown, suffix = '') => typeof input === 'number' && Number.isFinite(input)
  ? `${new Intl.NumberFormat(undefined, {maximumFractionDigits: 1}).format(input)}${suffix}` : 'Not reported'

/** A saved numerical result, never a new calculation or a claim of executed work. */
export default function PlanningReadout({strategy, farm}: {strategy?: Strategy; farm: Farm}) {
  if (!strategy) return <p>Calculate alternatives before inspecting a schedule.</p>
  return <section aria-label="Saved strategy readout">
    <p>Projected across {farm.horizon_days} days, including all demand. These totals are not the outcome of the single example order.</p>
    <dl className="record-facts">
      <div><dt>Delivery covered</dt><dd>{value(typeof strategy.metrics.fill_rate === 'number' ? strategy.metrics.fill_rate * 100 : null, '%')}</dd></div>
      <div><dt>Uncovered demand</dt><dd>{value(strategy.metrics.shortfall_kg, ' kg')}</dd></div>
      <div><dt>Growing cost</dt><dd>{value(strategy.metrics.cost_sgd, ' SGD')}</dd></div>
      <div><dt>Planner margin</dt><dd>{value(strategy.metrics.margin_sgd, ' SGD')}</dd></div>
    </dl>
    <h3>Dated bed allocations</h3>
    {strategy.allocations.length ? <ol className="planning-allocation-list">{strategy.allocations.map((allocation, i) => <li key={allocation.id || `${allocation.bed_id}:${allocation.crop_id}:${allocation.sow_date}:${i}`}>
      <strong>{farm.beds.find(bed => bed.id === allocation.bed_id)?.name || allocation.bed_id} · {allocation.crop_id.replaceAll('_', ' ')}</strong>
      <span>Sow {allocation.sow_date} → transplant {allocation.transplant_date} → harvest {allocation.harvest_date}</span>
      <span>{value(allocation.area_m2, ' m²')} · {value(allocation.expected_kg, ' kg projected')}</span>
    </li>)}</ol> : <p>No dated allocations are reported for this result.</p>}
    {!!strategy.violations?.length && <><h3>Constraint findings</h3><RecordFacts value={strategy.violations}/></>}
    <details><summary>All numerical facts and record identities</summary><RecordFacts value={{metrics: strategy.metrics, allocations: strategy.allocations, violations: strategy.violations}}/></details>
  </section>
}
