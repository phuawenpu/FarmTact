import { useEffect, useState } from 'react'
import { CalendarDays, ExternalLink, Newspaper } from 'lucide-react'
import { api } from '../lib/api'
import type { NewsContext } from '../lib/news'
import './news.css'

function date(value?: string | null) {
  return value ? new Intl.DateTimeFormat('en-SG', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'Asia/Singapore' }).format(new Date(value)) : 'Not supplied'
}

export function NewsPanel({ scenarioId, runId }: { scenarioId?: string; runId?: string }) {
  const [loaded, setData] = useState<NewsContext | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [geography, setGeography] = useState('all')
  const [period, setPeriod] = useState('all')
  const [crop, setCrop] = useState('')
  const [retry, setRetry] = useState(0)
  const frozen = Boolean(scenarioId || runId)
  useEffect(() => {
    let current = true
    setLoading(true); setError('')
    const query = new URLSearchParams(frozen ? (scenarioId ? { scenario_id: scenarioId } : { run_id: runId! }) : { geography, period, ...(crop ? { crop } : {}) })
    api.news(query).then(result => { if (current) setData(result) }).catch(() => { if (current) setError('News is unavailable. Your saved farm and numerical experiments remain available.') }).finally(() => { if (current) setLoading(false) })
    return () => { current = false }
  }, [scenarioId, runId, frozen, geography, period, crop, retry])
  const data = loaded && (frozen ? loaded.decision_id === (scenarioId || runId) : !loaded.frozen) ? loaded : null
  return <section aria-busy={loading} className="news-panel" aria-label={frozen ? 'Frozen News evidence' : 'News scout'}>
    <header><span className="news-icon"><Newspaper size={21}/></span><div><p className="kicker">News scout · supporting the council</p><h2>{frozen ? 'What this decision knew' : 'Beyond the farm gate'}</h2></div></header>
    <p>Reported news can help you choose a question to test. It does not change your orders, crop yields or prices.</p>
    {loading && <p role="status">Reading cached headlines…</p>}
    {error && <p role="alert">{error} <button onClick={() => setRetry(value => value + 1)}>Try again</button></p>}
    {data && <>
      <p className="news-clock">{frozen ? 'Evidence frozen' : 'News available'}: {date(data.cutoff)} SGT.<br/>Farm planning date: {date(data.farm_cutoff)} SGT. These are separate clocks.</p>
      <details className="news-browser">
        <summary><strong>{frozen ? 'Inspect frozen sources' : 'Browse headlines and sources'}</strong><span>{data.total} matching record{data.total === 1 ? '' : 's'}</span></summary>
        {!frozen && <div className="news-filters">
          <label>Region<select value={geography} onChange={event => setGeography(event.target.value)}><option value="all">Singapore + region</option><option value="singapore">Singapore</option><option value="regional">Regional</option></select></label>
          <label>Time<select value={period} onChange={event => setPeriod(event.target.value)}><option value="all">All available dates</option><option value="recent">Published in last 7 days</option><option value="future">Announced future events</option><option value="historical">Older publications</option></select></label>
          <label>Crop in headline<select value={crop} onChange={event => setCrop(event.target.value)}><option value="">All crops + general context</option>{['caixin', 'pak_choi', 'kailan', 'lettuce', 'bayam', 'kangkong', 'kale', 'mustard_greens', 'malabar_spinach', 'sweet_potato_leaves'].map(id => <option key={id} value={id}>{id.replaceAll('_', ' ')}</option>)}</select></label>
        </div>}
        {data.records.length === 0 && <p className="news-empty" role="status">{data.status === 'not_recorded' ? data.summary : period === 'future' ? 'No matching source records provide explicit future event dates. Publication dates have not been used as event dates.' : 'No matching dated records are available. General regional headlines may not name these crops.'}</p>}
        <div className="news-records">{data.records.map(record => {
          const source = data.sources.find(item => item.id === record.source_id)
          return <article key={record.id}>
            <p className="kicker">{source?.name || record.source_id} · {record.geography}</p>
            <h3><a href={record.canonical_url} target="_blank" rel="noreferrer">{record.title} <ExternalLink size={14} aria-label="opens source"/></a></h3>
            <p className="news-context-tag">{record.temporal_fit === 'recent' ? 'Recent publication' : record.temporal_fit === 'future' ? 'Announced future event' : record.temporal_fit === 'ongoing' ? 'Ongoing dated event' : 'Older publication'} · {record.relevance === 'crop_headline_match' ? 'Headline crop match' : 'General context'}</p>
            <dl><div><dt>Published</dt><dd>{date(record.published_at)}</dd></div><div><dt>Retrieved</dt><dd>{date(record.retrieved_at)} · {record.retrieval_freshness === 'fresh' ? 'fresh cache' : 'stale cache'}</dd></div>
              <div><dt><CalendarDays size={13}/> Event starts</dt><dd>{date(record.event_start_at)}</dd></div>{record.event_end_at && <div><dt>Event ends</dt><dd>{date(record.event_end_at)}</dd></div>}</dl>
            <details><summary>Evidence and limits</summary><p>{source?.scope}</p><p>All displayed times use Singapore time. Source date: {record.published_at_raw}.</p>{record.quality_issues.map(issue => <p key={issue}>{issue.replaceAll('_', ' ')}</p>)}<p>Record: <code>{record.id}</code></p><p>Content fingerprint: <code>{record.content_hash}</code></p></details>
          </article>
        })}</div>
        {data.total > data.records.length && <p>Showing {data.records.length} of {data.total}. Narrow the filters for a closer look.</p>}
        <details className="news-source-list"><summary>Source coverage and access</summary>{data.sources.map(source => <article key={source.id}><strong>{source.name}</strong><p>{source.status.replaceAll('_', ' ')} · {source.record_count || 0} collected records · {source.reuse_mode.replaceAll('_', ' ')}</p><p>{source.scope}</p>{source.last_attempt_at && <p>Last checked: {date(source.last_attempt_at)} SGT</p>}{source.url && <a href={source.url} target="_blank" rel="noreferrer">Open source <ExternalLink size={13}/></a>}</article>)}</details>
      </details>
      <p className="news-footnote">Cached public metadata · no inference while browsing. {frozen ? 'Advisor requests use this saved evidence.' : 'Starting an experiment freezes the available evidence; later headlines do not rewrite it.'}</p>
    </>}
  </section>
}
