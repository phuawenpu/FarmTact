import type { Conversation, ConversationMessage, RenderedFact } from '../lib/game'

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

function isRenderedFact(value: unknown): value is RenderedFact {
  return !!value && typeof value === 'object' && typeof (value as RenderedFact).reference === 'string' && 'value' in value
}

function factValueText(fact: RenderedFact): string {
  const { reference, value, unit, kind } = fact
  if (value === null || value === undefined) return 'Unavailable in this frozen snapshot'
  if (kind === 'date' || typeof value === 'string' && /^\d{4}-\d{2}-\d{2}/.test(value)) return valueText(reference, value)
  const number = typeof value === 'number' ? value : typeof value === 'string' && /^-?\d+(\.\d+)?$/.test(value) ? Number(value) : null
  if (number !== null && Number.isFinite(number)) {
    const delta = reference.includes('.deltas.')
    const prefix = delta && number > 0 ? '+' : ''
    if (unit === 'ratio') return `${prefix}${(number * 100).toLocaleString('en-SG', { maximumFractionDigits: 2 })}${delta ? ' percentage points' : '%'}`
    if (unit === 'SGD') return `${prefix}${new Intl.NumberFormat('en-SG', { style: 'currency', currency: 'SGD', maximumFractionDigits: 2 }).format(number)}`
    const unitLabel: Record<string, string> = { kg: ' kg', m2: ' m²', hours: ' hr', hour: ' hr', days: ' days', day: ' days', sites: ' sites', percent: '%' }
    return `${prefix}${number.toLocaleString('en-SG', { maximumFractionDigits: 3 })}${unit ? unitLabel[unit] ?? ` ${unit}` : ''}`
  }
  if (typeof value === 'boolean') return value ? 'Yes' : 'No'
  if (typeof value === 'object') return JSON.stringify(value)
  return String(value).replaceAll('_', ' ')
}

function unsupportedStatus(validationStatus?: string, evidenceStatus?: string) {
  return /unsupported|blocked|rejected|invalid/.test(`${validationStatus || ''} ${evidenceStatus || ''}`.toLowerCase())
}

/** Displays only server-rendered facts or their canonical frozen-catalogue fallback. */
export function FrozenFactEvidence({ factRefs = [], renderedFacts = [], catalogue = {}, policyLabels = {}, validationStatus, evidenceStatus }: {
  factRefs?: string[]
  renderedFacts?: RenderedFact[]
  catalogue?: Record<string, RenderedFact>
  policyLabels?: Record<string, string>
  validationStatus?: string
  evidenceStatus?: string
}) {
  const rendered = new Map(renderedFacts.filter(isRenderedFact).map(fact => [fact.reference, fact]))
  const refs = [...new Set([...factRefs.filter(ref => typeof ref === 'string'), ...rendered.keys()])]
  if (!refs.length) return null
  const unsupported = unsupportedStatus(validationStatus, evidenceStatus)
  return <details className={`typed-fact-references${unsupported ? ' typed-fact-references--unsupported' : ''}`} open style={{ marginTop: 8, minWidth: 0 }}>
    <summary style={{ minHeight: 44, display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '.8rem', fontWeight: 800 }}>
      {unsupported ? 'Selected frozen values · response not validated' : 'Code-rendered frozen values'}
    </summary>
    <dl style={{ margin: 0, display: 'grid', gap: 8, minWidth: 0 }}>
      {refs.map(ref => {
        const fromRendered = rendered.get(ref)
        const fromCatalogue = isRenderedFact(catalogue[ref]) && catalogue[ref].reference === ref ? catalogue[ref] : undefined
        const fact = fromRendered || fromCatalogue
        return <div key={ref} data-fact-reference={ref} style={{ minWidth: 0, padding: 10, border: `1px solid ${unsupported ? '#d99b8e' : '#cbd8ba'}`, borderRadius: 10, background: unsupported ? '#fff1ed' : '#edf1e4', overflowWrap: 'anywhere' }}>
          <dt style={{ fontSize: '.74rem', lineHeight: 1.5, fontWeight: 750 }}>{[policyLabels[ref], title(ref)].filter(Boolean).join(' · ')}</dt>
          {fact ? <>
            <dd style={{ margin: '6px 0 0', fontSize: '.9rem', lineHeight: 1.5, fontWeight: 750 }}>{factValueText(fact)}</dd>
            <dd style={{ margin: '3px 0 0', fontSize: '.66rem', lineHeight: 1.45, color: '#536057' }}>
              {[fact.entity?.type ? `${words(fact.entity.type)} record` : '', fact.period?.kind ? `${words(fact.period.kind)} ${fact.period.value || ''}` : '', fact.context ? `${words(fact.context)} context` : ''].filter(Boolean).join(' · ')}
            </dd>
            <dd style={{ margin: '3px 0 0', fontSize: '.66rem', lineHeight: 1.45, color: unsupported ? '#913d32' : '#39523e' }}>
              {unsupported ? 'Frozen server value; this response did not pass the evidence gate.' : fact.verification === 'code_rendered_frozen_value' ? 'Value rendered by code from the frozen snapshot.' : fromRendered ? 'Value supplied in the server-rendered fact record.' : 'Value recovered from the canonical frozen fact catalogue.'}
            </dd>
          </> : <dd role="note" style={{ margin: '6px 0 0', fontSize: '.78rem', lineHeight: 1.5, color: '#913d32', fontWeight: 750 }}>Referenced fact is missing from this frozen snapshot.</dd>}
          <details style={{ marginTop: 4, fontSize: '.66rem' }}><summary style={{ cursor: 'pointer', minHeight: 28, display: 'flex', alignItems: 'center' }}>Canonical reference</summary><code style={{ display: 'block', whiteSpace: 'normal', overflowWrap: 'anywhere' }}>{ref}</code>{fact?.entity?.id && <span style={{ display: 'block', marginTop: 3 }}>Entity ID: {fact.entity.id}</span>}</details>
        </div>
      })}
    </dl>
    <p style={{ fontSize: '.7rem', lineHeight: 1.5, marginBottom: 0 }}>Values come from server records, never from the adviser’s prose. Their presence does not verify the interpretation.</p>
  </details>
}

export function QualitativeContextReferences({ refs = [], toolResults = {} }: { refs?: string[]; toolResults?: Record<string, unknown> }) {
  if (!refs.length) return null
  return <details className="tool-references" style={{ marginTop: 8 }}>
    <summary style={{ minHeight: 44, display: 'flex', alignItems: 'center', cursor: 'pointer', fontSize: '.8rem', fontWeight: 700 }}>Qualitative context references</summary>
    <p style={{ marginTop: 0, fontSize: '.7rem', lineHeight: 1.5 }}>These records provide frozen context. They are separate from code-rendered values and do not verify the adviser’s prose.</p>
    <dl style={{ margin: 0, display: 'grid', gap: 8 }}>
      {refs.map(ref => <div key={ref} style={{ minWidth: 0, padding: 10, borderRadius: 10, background: '#f3eddf', overflowWrap: 'anywhere' }}>
        <dt><code style={{ whiteSpace: 'normal', overflowWrap: 'anywhere' }}>{ref}</code></dt>
        <dd style={{ margin: '4px 0 0', fontSize: '.78rem', lineHeight: 1.5 }}>{toolResults[ref] === undefined ? 'Referenced context is missing from this frozen snapshot.' : valueText(ref, toolResults[ref])}</dd>
      </div>)}
    </dl>
  </details>
}

/** Quantities and labels come from frozen backend references, never advisor prose. */
export function AdvisorEvidence({ message, conversation }: { message: ConversationMessage; conversation: Conversation }) {
  const tools = conversation.tool_results || {}
  const evidence = Array.isArray(conversation.evidence_context) ? conversation.evidence_context as Evidence[] : []
  return <div className="advisor-evidence">
    <FrozenFactEvidence factRefs={message.fact_refs} renderedFacts={message.rendered_facts} catalogue={conversation.typed_facts} validationStatus={message.validation_status} evidenceStatus={message.evidence_status as string | undefined}/>
    <QualitativeContextReferences refs={message.tool_refs} toolResults={tools}/>
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
