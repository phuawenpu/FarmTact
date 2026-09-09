import { AlertCircle, ChevronLeft, ChevronRight, Database, Download, LoaderCircle, Search } from 'lucide-react'
import { useEffect, useMemo, useRef, useState } from 'react'
import { ChartTable, ExplorerChart, type ChartPoint } from './ExplorerChart'

type DatasetKey = 'weather_observations' | 'weather_forecasts' | 'trade_observations'
type PublicSource = {
  id: string; name: string; provider?: string | null; kind?: string | null; url?: string | null
  status: string; upstream_status?: string | null; coverage?: Record<string, unknown>
  observed_at?: string | null; retrieved_at?: string | null; freshness?: string | null
  quality?: string | null; quality_flags?: string[]; licence_state?: string | null
  reuse_restrictions?: string | string[]; export_allowed: boolean; record_count: number
  unit_scope?: string | null; freshness_expectation?: string | null; failure_reason?: string | null
}
type PublicRow = {
  id: string; source_id: string; date: string; metric: string; value: unknown; unit?: string | null
  observed_at?: string | null; retrieved_at?: string | null; station_id?: string | null
  station_name?: string | null; provider_variable?: string | null; interval_minutes?: number | null
  grid_point?: unknown; commodity_code?: string | null; commodity_description?: string | null
  partner?: string | null; trade_flow?: string | null; location_id?: string | null
  export_allowed: boolean; [key: string]: unknown
}
type PublicContext = { sources: PublicSource[]; datasets: Record<DatasetKey, PublicRow[]> }

const DATASETS: Array<[DatasetKey, string]> = [
  ['weather_observations', 'Weather observations'],
  ['weather_forecasts', 'Weather forecasts'],
  ['trade_observations', 'Trade observations'],
]
const label = (value: string) => value.replaceAll('_', ' ').replace(/\b\w/g, letter => letter.toUpperCase())
const display = (value: unknown) => value === null || value === undefined || value === '' ? '—' : typeof value === 'object' ? JSON.stringify(value) : String(value)
const numeric = (value: unknown) => value !== '' && value !== null && value !== undefined && Number.isFinite(Number(value))
const restrictions = (value?: string | string[]) => Array.isArray(value) ? value.join(' ') : value || 'No additional reuse restriction recorded.'

function seriesIdentity(row: PublicRow) {
  return JSON.stringify([
    row.source_id, row.station_id || row.grid_point || row.location_id || '', row.metric, row.unit || '',
    row.interval_minutes || '', row.commodity_code || '', row.partner || '', row.trade_flow || '',
  ])
}

function seriesLabel(row: PublicRow, source?: PublicSource) {
  const place = row.station_name || row.station_id || (row.grid_point ? `grid ${display(row.grid_point)}` : row.location_id)
  const commodity = row.commodity_code ? `${row.commodity_code} · ${row.commodity_description || 'commodity'}` : ''
  const context = [place, commodity, row.partner, row.trade_flow].filter(Boolean).join(' · ')
  const interval = row.interval_minutes ? ` · ${row.interval_minutes} min` : ''
  return `${source?.name || row.source_id} · ${label(row.metric)}${context ? ` · ${context}` : ''} · ${row.unit || 'unitless'}${interval}`
}

async function responseError(response: Response) {
  try { const body = await response.json() as { detail?: string }; return body.detail || `Request failed (${response.status})` }
  catch { return `Request failed (${response.status})` }
}

export function PublicExplorer() {
  const [data, setData] = useState<PublicContext | null>(null)
  const [loading, setLoading] = useState(true), [error, setError] = useState(''), [exporting, setExporting] = useState('')
  const [sourceId, setSourceId] = useState(''), [dataset, setDataset] = useState<DatasetKey>('weather_observations')
  const [query, setQuery] = useState(''), [start, setStart] = useState(''), [end, setEnd] = useState('')
  const [sort, setSort] = useState('date'), [descending, setDescending] = useState(false), [page, setPage] = useState(1)
  const [series, setSeries] = useState(''), [selectedId, setSelectedId] = useState('')
  const inspector = useRef<HTMLDetailsElement>(null)

  useEffect(() => {
    const controller = new AbortController()
    void (async () => {
      try {
        const response = await fetch('/api/v1/data-explorer/public', { credentials: 'same-origin', signal: controller.signal })
        if (!response.ok) throw new Error(await responseError(response))
        const body = await response.json() as PublicContext
        setData(body)
        setSourceId(body.sources.find(source => source.record_count > 0)?.id || body.sources[0]?.id || '')
      } catch (reason) {
        if (!controller.signal.aborted) setError(reason instanceof Error ? reason.message : 'Public context unavailable.')
      } finally { if (!controller.signal.aborted) setLoading(false) }
    })()
    return () => controller.abort()
  }, [])

  const selectedSource = data?.sources.find(source => source.id === sourceId)
  const sourceRows = useMemo(() => (data?.datasets[dataset] || []).filter(row => !sourceId || row.source_id === sourceId), [data, dataset, sourceId])
  const dateExtent = useMemo(() => {
    const dates = sourceRows.map(row => row.date).filter(Boolean).sort()
    return { first: dates[0] || '', last: dates.at(-1) || '' }
  }, [sourceRows])
  useEffect(() => { setStart(dateExtent.first); setEnd(dateExtent.last); setPage(1); setSelectedId('') }, [dataset, sourceId, dateExtent.first, dateExtent.last])

  const filtered = useMemo(() => sourceRows.filter(row =>
    (!start || row.date >= start) && (!end || row.date <= end) &&
    (!query || JSON.stringify(row).toLocaleLowerCase().includes(query.toLocaleLowerCase()))
  ), [sourceRows, start, end, query])
  const fields = useMemo(() => {
    const preferred = ['id', 'source_id', 'date', 'metric', 'value', 'unit', 'station_name', 'station_id', 'location_id', 'commodity_code', 'partner', 'trade_flow', 'observed_at', 'retrieved_at']
    const present = new Set(filtered.flatMap(row => Object.keys(row)))
    return [...preferred.filter(key => present.has(key)), ...[...present].filter(key => !preferred.includes(key))].slice(0, 14)
  }, [filtered])
  useEffect(() => { if (!fields.includes(sort)) setSort(fields.includes('date') ? 'date' : fields[0] || 'id') }, [fields, sort])
  const ordered = useMemo(() => [...filtered].sort((left, right) => {
    const a = left[sort], b = right[sort]
    const comparison = numeric(a) && numeric(b) ? Number(a) - Number(b) : String(a ?? '').localeCompare(String(b ?? ''))
    return comparison * (descending ? -1 : 1)
  }), [filtered, sort, descending])
  const pageSize = 25, pages = Math.max(1, Math.ceil(ordered.length / pageSize))
  const shown = ordered.slice((page - 1) * pageSize, page * pageSize)
  useEffect(() => setPage(1), [query, start, end, sort, descending])

  const observedRows = useMemo(
    () => dataset === 'weather_forecasts' ? [] : filtered.filter(row => numeric(row.value)),
    [dataset, filtered],
  )
  const seriesGroups = useMemo(() => {
    const groups = new Map<string, PublicRow[]>()
    observedRows.forEach(row => groups.set(seriesIdentity(row), [...(groups.get(seriesIdentity(row)) || []), row]))
    return groups
  }, [observedRows])
  useEffect(() => { if (!seriesGroups.has(series)) setSeries(seriesGroups.keys().next().value || '') }, [seriesGroups, series])
  const chartRows = seriesGroups.get(series) || []
  const chartPoints: ChartPoint[] = chartRows.map(row => ({ id: row.id, date: row.date, value: Number(row.value), label: label(row.metric) })).sort((a, b) => a.date.localeCompare(b.date))
  const chartExample = chartRows[0]

  const selectRecord = (id: string) => {
    setSelectedId(id)
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    window.setTimeout(() => inspector.current?.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'nearest' }), 0)
  }
  const selected = ordered.find(row => row.id === selectedId)
  const exportAllowed = filtered.length > 0 && filtered.every(row => row.export_allowed)
  const download = async (format: 'csv' | 'json') => {
    setError(''); setExporting(format)
    try {
      const params = new URLSearchParams({ dataset, format, q: query })
      if (sourceId) params.set('source_id', sourceId)
      if (start) params.set('start', start)
      if (end) params.set('end', end)
      const response = await fetch(`/api/v1/data-explorer/public/export?${params}`, { credentials: 'same-origin' })
      if (!response.ok) throw new Error(await responseError(response))
      const blob = await response.blob(), url = URL.createObjectURL(blob), anchor = document.createElement('a')
      anchor.href = url; anchor.download = `farmtact-public-${dataset}.${format}`; anchor.click(); URL.revokeObjectURL(url)
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Export failed.') }
    finally { setExporting('') }
  }

  if (loading) return <div className="explorer-loading"><LoaderCircle className="spinner-icon" /> Loading cached public sources…</div>
  if (!data) return <p className="explorer-alert" role="alert"><AlertCircle size={17} />{error || 'Public context unavailable.'}</p>

  return <div style={{ display: 'grid', gap: 12 }}>
    <style>{`.public-explorer-controls button,.public-explorer-controls select,.public-explorer-controls input{min-height:44px}.public-source-picker{min-width:min(100%,280px)!important}.public-source-picker select,.public-series-picker select{width:100%;min-width:0;max-width:100%}.public-series-picker{min-width:0}.public-source-summary{overflow-wrap:anywhere}.public-export-note{margin:0;color:#68746b;font-size:.68rem}`}</style>
    <p className="explorer-note"><Database size={16} /> Cached public context stays separate from synthetic farm records. Forecasts can be inspected as records, but are never plotted as observations.</p>
    {error && <p className="explorer-alert" role="alert"><AlertCircle size={17} />{error}</p>}

    <section className="explorer-card records-toolbar public-explorer-controls">
      <label className="public-source-picker"><span>Public source</span><select aria-label="Public source" value={sourceId} onChange={event => setSourceId(event.target.value)}><option value="">All sources</option>{data.sources.map(source => <option key={source.id} value={source.id}>{source.id} · {source.name} · {source.record_count ? `${source.record_count} records` : 'metadata only'}</option>)}</select></label>
      <label><span>Record set</span><select aria-label="Public record set" value={dataset} onChange={event => setDataset(event.target.value as DatasetKey)}>{DATASETS.map(([key, name]) => <option key={key} value={key}>{name}</option>)}</select></label>
      <label className="record-search"><span>Search records</span><div><Search size={16} /><input aria-label="Search public records" value={query} maxLength={100} onChange={event => setQuery(event.target.value)} placeholder="Station, metric, commodity…" /></div></label>
      <label><span>From</span><input aria-label="Public start date" type="date" value={start} min={dateExtent.first} max={end || dateExtent.last} disabled={!dateExtent.first} onChange={event => setStart(event.target.value)} /></label>
      <label><span>To</span><input aria-label="Public end date" type="date" value={end} min={start || dateExtent.first} max={dateExtent.last} disabled={!dateExtent.last} onChange={event => setEnd(event.target.value)} /></label>
    </section>

    {selectedSource && <section className="explorer-card public-source-summary" aria-live="polite"><div className="explorer-section-title"><div><p className="kicker">{selectedSource.id} · {selectedSource.provider || 'Public provider'}</p><h2>{selectedSource.name}</h2></div><span className={`source-status source-status--${selectedSource.status}`}>{selectedSource.status === 'metadata_only' ? 'Metadata only' : selectedSource.status}</span></div><dl className="explorer-dl"><div><dt>Records</dt><dd>{selectedSource.record_count}</dd></div><div><dt>Coverage</dt><dd>{display(selectedSource.coverage)}</dd></div><div><dt>Observed / issued</dt><dd>{selectedSource.observed_at || (selectedSource.record_count ? 'Not supplied by source' : 'No ingested rows')}</dd></div><div><dt>Retrieved</dt><dd>{selectedSource.retrieved_at || 'Not retrieved'}</dd></div><div><dt>Freshness</dt><dd>{selectedSource.freshness || 'unknown'}{selectedSource.freshness_expectation ? ` · expected ${selectedSource.freshness_expectation}` : ''}</dd></div><div><dt>Quality</dt><dd>{selectedSource.quality || 'unrated'}{selectedSource.quality_flags?.length ? ` · ${selectedSource.quality_flags.join(', ')}` : ''}</dd></div><div><dt>Licence</dt><dd>{selectedSource.licence_state || 'unreviewed'}</dd></div><div><dt>Export</dt><dd>{selectedSource.export_allowed ? 'Allowed with source attribution' : 'Disabled'}</dd></div></dl><p>{restrictions(selectedSource.reuse_restrictions)}</p>{selectedSource.failure_reason && <p role="alert">Source status: {selectedSource.failure_reason}</p>}{selectedSource.url && <a href={selectedSource.url} target="_blank" rel="noreferrer">Open original source</a>}</section>}

    <section className="explorer-card explorer-wide"><div className="explorer-section-title"><div><p className="kicker">Numeric observations only</p><h2>Observed series</h2></div><span>{seriesGroups.size} separate series</span></div><label className="public-series-picker" style={{ display: 'grid', gap: 4, fontSize: '.68rem', fontWeight: 800 }}>Measurement series<select aria-label="Public measurement series" value={series} onChange={event => setSeries(event.target.value)} style={{ minHeight: 44 }}><option value="">Select an observed series</option>{[...seriesGroups.entries()].map(([key, rows]) => <option key={key} value={key}>{seriesLabel(rows[0], data.sources.find(source => source.id === rows[0].source_id))}</option>)}</select></label>{chartPoints.length ? <><ExplorerChart points={chartPoints} unit={chartExample?.unit || ''} onSelect={selectRecord} /><ChartTable points={chartPoints} unit={chartExample?.unit || ''} onSelect={selectRecord} /></> : <div className="explorer-empty">This source and date range contain no numeric observations. Forecast records remain available below.</div>}</section>

    <section className="explorer-card records-toolbar public-explorer-controls"><label><span>Sort records</span><select aria-label="Sort public records" value={sort} onChange={event => setSort(event.target.value)}>{fields.map(field => <option key={field} value={field}>{label(field)}</option>)}</select></label><button className="button button--cream" onClick={() => setDescending(value => !value)}>{descending ? 'Descending' : 'Ascending'}</button><button className="button button--forest" disabled={!exportAllowed || Boolean(exporting)} onClick={() => void download('csv')}><Download size={16} />{exporting === 'csv' ? 'Preparing…' : 'CSV'}</button><button className="button button--cream" disabled={!exportAllowed || Boolean(exporting)} onClick={() => void download('json')}><Download size={16} />{exporting === 'json' ? 'Preparing…' : 'JSON'}</button><p className="public-export-note">{!filtered.length ? 'No matching records to export.' : exportAllowed ? 'Export includes source attribution and current filters.' : 'Export disabled because this selection includes unverified redistribution terms.'}</p></section>

    <section className="explorer-card explorer-wide"><div className="explorer-section-title"><div><p className="kicker">{ordered.length} curated records</p><h2>{DATASETS.find(([key]) => key === dataset)?.[1]}</h2></div><span>Source, measurement and unit stay separate</span></div><div className="table-scroll"><table className="records-table"><caption>Filtered {dataset.replaceAll('_', ' ')} records</caption><thead><tr>{fields.map(field => <th key={field}><button onClick={() => { setSort(field); setDescending(sort === field ? !descending : false) }}>{label(field)}</button></th>)}</tr></thead><tbody>{shown.map(row => <tr key={row.id} className={selectedId === row.id ? 'is-selected' : ''} onClick={() => setSelectedId(row.id)}>{fields.map(field => <td key={field}>{display(row[field])}</td>)}</tr>)}</tbody></table></div>{!shown.length && <div className="explorer-empty">{selectedSource?.status === 'metadata_only' ? 'This registry source has metadata only and no ingested rows.' : 'No records match the current filters.'}</div>}<div className="pagination"><button disabled={page <= 1} onClick={() => setPage(value => value - 1)}><ChevronLeft /> Previous</button><span>Page {page} of {pages}</span><button disabled={page >= pages} onClick={() => setPage(value => value + 1)}>Next <ChevronRight /></button></div>{selected && <details ref={inspector} open className="record-inspector"><summary>Selected curated record · {selected.id}</summary><pre>{JSON.stringify(selected, null, 2)}</pre></details>}</section>
  </div>
}
