import { AlertTriangle, Check, Clock3, CloudOff, LoaderCircle, Sprout } from 'lucide-react'
import type { ReactNode } from 'react'

export function CropArt({ cropId, color = '#93c64b', stage = 'growing', compact = false }: {
  cropId?: string
  color?: string
  stage?: string
  compact?: boolean
}) {
  if (!cropId || stage === 'empty') {
    return (
      <div className={`crop-art crop-art--empty ${compact ? 'crop-art--compact' : ''}`} aria-hidden="true">
        <svg viewBox="0 0 120 100"><path d="M14 72c23-12 69-14 92 0v18H14z" fill="#886545"/><path d="M25 79h70M37 72v18M61 70v20M84 72v18" stroke="#b99567" strokeWidth="2"/></svg>
      </div>
    )
  }
  const seed = [...cropId].reduce((total, char) => total + char.charCodeAt(0), 0)
  const leafCount = stage === 'nursery' ? 3 : stage === 'ready' ? 9 : 6
  const stems = Array.from({ length: leafCount }, (_, index) => {
    const angle = -68 + (136 / Math.max(leafCount - 1, 1)) * index
    const length = 31 + ((seed + index * 7) % 19)
    return { angle, length, width: 11 + ((seed + index * 3) % 8) }
  })
  return (
    <div className={`crop-art ${compact ? 'crop-art--compact' : ''}`} aria-hidden="true">
      <svg viewBox="0 0 120 100">
        <ellipse cx="60" cy="88" rx="35" ry="7" fill="#142f24" opacity=".16" />
        {stems.map(({ angle, length, width }, index) => (
          <g key={index} transform={`translate(60 82) rotate(${angle})`}>
            <path d={`M0 0 Q 2 -${length / 2} 0 -${length}`} stroke="#397345" strokeWidth="3" fill="none" />
            <ellipse cx="0" cy={-length} rx={width} ry={width * 1.55} fill={color} transform={`rotate(${index % 2 ? 18 : -18})`} />
            <path d={`M0 -${length + width}v${width * 1.8}`} stroke="#f2f5bc" strokeWidth="1.4" opacity=".65" />
          </g>
        ))}
        <circle cx="60" cy="78" r={stage === 'ready' ? 17 : 12} fill={color} />
        <path d="M29 87c16-4 45-5 62 0" stroke="#8e6948" strokeWidth="5" strokeLinecap="round" />
      </svg>
    </div>
  )
}

export function StatusPill({ status, children }: { status: string; children?: ReactNode }) {
  const normalized = status.toLowerCase().replaceAll('_', '-')
  const kind = /ready|accepted|complete|available|fresh|live|ok|connected|validated|verified/.test(normalized)
    ? 'good'
    : /fail|blocked|error|stale|violation/.test(normalized)
      ? 'danger'
      : /running|pending|loading|validating|queued/.test(normalized)
        ? 'active'
        : 'neutral'
  return <span className={`status-pill status-pill--${kind}`}><span className="status-dot" />{children || status.replaceAll('_', ' ')}</span>
}

export function StatePanel({ kind, title, detail, action }: {
  kind: 'loading' | 'empty' | 'error'
  title: string
  detail: string
  action?: ReactNode
}) {
  const Icon = kind === 'loading' ? LoaderCircle : kind === 'error' ? CloudOff : Sprout
  return (
    <section className={`state-panel state-panel--${kind}`} role={kind === 'error' ? 'alert' : 'status'}>
      <span className="state-panel__icon"><Icon size={24} /></span>
      <div><h2>{title}</h2><p>{detail}</p>{action}</div>
    </section>
  )
}

export function Meter({ label, value, max, unit, tone = 'lime' }: {
  label: string
  value: number
  max: number
  unit: string
  tone?: 'lime' | 'coral' | 'sky'
}) {
  const percentage = max > 0 ? Math.min(100, Math.max(0, (value / max) * 100)) : 0
  return (
    <div className="meter">
      <div className="meter__label"><span>{label}</span><strong>{value.toLocaleString('en-SG')} <small>{unit}</small></strong></div>
      <div className="meter__track" role="meter" aria-label={label} aria-valuemin={0} aria-valuemax={max} aria-valuenow={value}>
        <span className={`meter__fill meter__fill--${tone}`} style={{ width: `${percentage}%` }} />
      </div>
    </div>
  )
}

export function EventIcon({ type }: { type: string }) {
  if (/failed|rejected|warning|invalidated/.test(type)) return <AlertTriangle size={16} />
  if (/completed|accepted|ready/.test(type)) return <Check size={16} />
  return <Clock3 size={16} />
}

export function formatDate(value?: string | null, withTime = false) {
  if (!value) return 'Not reported'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat('en-SG', {
    day: 'numeric', month: 'short', year: withTime ? undefined : 'numeric',
    hour: withTime ? '2-digit' : undefined, minute: withTime ? '2-digit' : undefined,
    timeZone: 'Asia/Singapore',
  }).format(date)
}

export function formatMoney(value: number) {
  return new Intl.NumberFormat('en-SG', { style: 'currency', currency: 'SGD', maximumFractionDigits: 0 }).format(value)
}

export function humanizeSystem(value: string) {
  const labels: Record<string, string> = {
    sheltered_hydroponic: 'Sheltered hydroponic',
    open_field: 'Open field',
    indoor_vertical: 'Indoor vertical',
  }
  return labels[value] || sentenceCase(value)
}

export function humanizeExecutionMode(value: string) {
  const labels: Record<string, string> = {
    offline_snapshot_rebuild: 'Cached snapshot',
    cached_snapshot: 'Cached snapshot',
    public_refresh: 'Public refresh',
    live_public_refresh: 'Public refresh',
    replay: 'Replay',
    test: 'Test',
  }
  return labels[value] || sentenceCase(value)
}

function sentenceCase(value: string) {
  const words = value.replaceAll('_', ' ').trim()
  return words ? words[0].toUpperCase() + words.slice(1) : 'Unreported'
}
