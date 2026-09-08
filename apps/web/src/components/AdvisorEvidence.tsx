import type { Conversation, ConversationMessage } from '../lib/game'

type Evidence = { evidence_id?: string; title?: string; finding?: string; scope?: string; limit?: string; source_url?: string; access_review_status?: string }
const labels: Record<string, string> = {
  fill_rate: 'Demand filled', margin_sgd: 'Contribution margin', waste_kg: 'Waste', shortfall_kg: 'Unfilled demand',
  harvest_kg: 'Marketable harvest', cost_sgd: 'Total cost', labour_hours: 'Labour over the horizon',
  labour_hours_per_week: 'Weekly labour allowance', cash_sgd: 'Available cash', area_m2: 'Growing area',
  expected_marketable_kg: 'Expected marketable harvest', nursery_sites: 'Nursery capacity',
  harvest_date: 'Scheduled harvest', transplant_date: 'Scheduled transplant', sow_date: 'Scheduled sowing',
  due_date: 'Delivery due', quantity_kg: 'Ordered quantity', price_sgd_per_kg: 'Price per kg',
  delay_days: 'Harvest delay', yield_percent: 'Expected yield assumption', demand_percent: 'Demand assumption',
  labour_percent: 'Labour assumption', cash_percent: 'Cash assumption', biological_lead_days: 'Biological lead time',
  nursery_days: 'Nursery duration', grow_days: 'Growing duration', constraints: 'Hard constraints', violations: 'Hard constraints',
}
function words(text: string) { return text.replaceAll('_', ' ').replaceAll('.', ' · ').replaceAll(':', ' · ') }
function title(ref: string) {
  const field = ref.split('.').at(-1) || ref
  const name = labels[field] || words(field)
  const policy = ref.match(/(?:^|[.:])(lean|balanced|resilient)(?:\.|$)/i)?.[1]
  const side = /deltas/.test(ref) ? 'Change from baseline' : /baseline/.test(ref) ? 'Baseline' : /scenario_metrics|scenario:result/.test(ref) ? 'Experiment' : ''
  const entity = !policy && /^(bed|batch|delivery|recipe|source):/.test(ref) ? words(ref.split('.')[0]) : ''
  return [policy ? policy[0].toUpperCase() + policy.slice(1) : '', side, entity, name].filter(Boolean).join(' · ')
}
function valueText(ref: string, value: unknown): string {
  const field = ref.split('.').at(-1) || ref
  if (value === null || value === undefined) return 'Unavailable in this frozen snapshot'
  if (typeof value === 'string' && /^\d{4}-\d{2}-\d{2}/.test(value)) {
    const date = new Date(value.length === 10 ? `${value}T00:00:00Z` : value)
    if (!Number.isNaN(date.getTime())) return new Intl.DateTimeFormat('en-SG', { day: 'numeric', month: 'short', year: 'numeric', timeZone: value.length === 10 ? 'UTC' : 'Asia/Singapore', ...(value.length > 10 ? { hour: '2-digit' as const, minute: '2-digit' as const } : {}) }).format(date)
  }
  const number = typeof value === 'number' ? value : typeof value === 'string' && /^-?\d+(\.\d+)?$/.test(value) ? Number(value) : null
  if (number !== null && Number.isFinite(number)) {
    const delta = ref.includes('.deltas.')
    const prefix = delta && number > 0 ? '+' : ''
    if (/fill_rate/.test(field)) return `${prefix}${(number * 100).toLocaleString('en-SG', { maximumFractionDigits: 2 })}${delta ? ' percentage points' : '%'}`
    if (field.includes('sgd')) return `${prefix}${new Intl.NumberFormat('en-SG', { style: 'currency', currency: 'SGD', maximumFractionDigits: 2 }).format(number)}${field.endsWith('per_kg') ? '/kg' : ''}`
    const unit = field.endsWith('_kg') ? ' kg' : field.endsWith('_m2') ? ' m²' : field.includes('hours') ? ' hr' : field.includes('days') ? ' days' : field.endsWith('_percent') ? '%' : field.includes('sites') ? ' sites' : ''
    return `${prefix}${number.toLocaleString('en-SG', { maximumFractionDigits: 3 })}${unit}`
  }
  if (Array.isArray(value)) {
    if (!value.length) return /constraints|violations/.test(ref) ? 'No hard constraint violations' : 'None recorded'
    return value.map(item => {
      if (item && typeof item === 'object' && 'constraint_code' in item) {
        const v = item as Record<string, unknown>
        return `${words(String(v.constraint_code))}: requires ${String(v.required)} ${String(v.unit)}, available ${String(v.available)}`
      }
      return typeof item === 'string' ? item : 'Recorded contextual result'
    }).join('; ')
  }
  if (typeof value === 'object') return Object.entries(value as Record<string, unknown>).filter(([, v]) => v !== null && v !== undefined).map(([key, v]) => `${labels[key] || words(key)}: ${typeof v === 'object' ? 'recorded details' : String(v)}`).join(' · ')
  return String(value).replaceAll('_', ' ')
}
function sourceURL(value?: string) { try { const url = new URL(value || ''); return ['https:', 'http:'].includes(url.protocol) ? url.href : undefined } catch { return undefined } }

/** Quantities and labels come from frozen backend references, never advisor prose. */
export function AdvisorEvidence({ message, conversation }: { message: ConversationMessage; conversation: Conversation }) {
  const tools = conversation.tool_results && typeof conversation.tool_results === 'object' ? conversation.tool_results as Record<string, unknown> : {}
  const evidence = Array.isArray(conversation.evidence_context) ? conversation.evidence_context as Evidence[] : []
  const refs = message.tool_refs || []
  return <div className="advisor-evidence">
    {!!refs.length && <details className="tool-references" open>
      <summary style={{ minHeight: 44, display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '.8rem', fontWeight: 700 }}>Facts from this frozen snapshot</summary>
      <dl style={{ margin: 0, display: 'grid', gap: 8 }}>
        {refs.map(ref => <div key={ref} style={{ padding: 10, borderRadius: 10, background: '#edf1e4', overflowWrap: 'anywhere' }}>
          <dt style={{ fontSize: '.74rem', lineHeight: 1.5 }}>{title(ref)}</dt>
          <dd style={{ margin: '4px 0 0', fontSize: '.85rem', lineHeight: 1.5, fontWeight: 650 }}>{valueText(ref, tools[ref])}</dd>
        </div>)}
      </dl>
      <p style={{ fontSize: '.7rem', lineHeight: 1.5, marginBottom: 0 }}>Farm and experiment figures are synthetic. Public-source values retain their source context.</p>
    </details>}
    {(message.evidence_refs || []).map(ref => {
      const item = evidence.find(entry => entry.evidence_id === ref)
      const url = sourceURL(item?.source_url)
      return <details key={ref} className="evidence-citation" style={{ fontSize: '.8rem', lineHeight: 1.6, marginTop: 8 }}>
        <summary style={{ minHeight: 44, cursor: 'pointer', paddingBlock: 10 }}>{ref} · {item?.title || 'Evidence and applicability'}</summary>
        {item ? <div style={{ padding: 10, background: '#f3eddf', borderRadius: 10 }}>
          {item.finding && <p>{item.finding}</p>}
          {item.scope && <p><strong>Scope:</strong> {item.scope}</p>}
          {item.limit && <p><strong>Limit:</strong> {item.limit}</p>}
          <p>A citation does not establish that the advisor’s interpretation applies to this farm.</p>
          {url && <a href={url} target="_blank" rel="noreferrer" style={{ display: 'inline-flex', minHeight: 44, alignItems: 'center' }}>Read source ↗</a>}
        </div> : <p>This reference was not supplied in the frozen evidence context.</p>}
      </details>
    })}
  </div>
}
