import { ArrowRight, CheckCircle2, History, Sprout } from 'lucide-react'
import { useEffect, useState } from 'react'

export type ReleaseChange = { title: string; description: string; feedback_ids: string[]; status: 'implemented' | 'verified' | 'open'; evidence: string[] }
export type ReleaseEdition = { id: string; title: string; published_at: string; summary: string; changes: ReleaseChange[]; source_commit: string; source_url: string; compare_url: string; image_digest: string; review_url: string; play_url: string; status: 'published' }
export type Releases = { latest: string; editions: ReleaseEdition[] }

export function useReleases() {
  const [data, setData] = useState<Releases | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { const controller = new AbortController(); void fetch('/api/releases', { signal: controller.signal }).then(async response => {
    if (!response.ok) throw Error('Release history is unavailable.')
    setData(await response.json())
  }).catch(error => { if (!controller.signal.aborted) setError(error instanceof Error ? error.message : 'Release history is unavailable.') }); return () => controller.abort() }, [])
  return { data, error }
}

export function EditionSwitcher({ editionId }: { editionId: string }) {
  const { data } = useReleases()
  return <div className="edition-switcher"><label><span>Edition &amp; evolution</span><select aria-label="Choose FarmTact edition" value={editionId} onChange={event => window.location.assign(`/${event.target.value}/`)}>{data?.editions.map(edition => <option key={edition.id} value={edition.id}>{edition.id.toUpperCase()} · {edition.title}</option>) || <option value={editionId}>{editionId.toUpperCase()}</option>}</select></label><p>Each edition has its own farm and progress.</p><a href={`/${editionId}/changes`}>Changes and evidence</a></div>
}

export function EditionChooser() {
  const { data, error } = useReleases()
  return <main className="edition-page"><header className="edition-hero"><span className="brand__mark"><Sprout size={28}/></span><p className="kicker">FarmTact editions</p><h1>Choose your strategy room</h1><p>Play the preserved original or explore the latest evolution. Every edition remains available with its own review evidence.</p></header>
    {error && <p className="error-banner" role="alert">{error}</p>}{!data && !error && <p role="status">Loading editions…</p>}
    <section className="edition-grid" aria-label="Published editions">{data?.editions.map(edition => <article className={edition.id === data.latest ? 'edition-card is-latest' : 'edition-card'} key={edition.id}><div><span className="edition-badge">{edition.id === data.latest ? 'Latest edition' : 'Preserved edition'}</span><h2>{edition.title}</h2><p>{edition.summary}</p><small>Published {new Date(edition.published_at).toLocaleDateString('en-SG', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })}</small></div><div className="edition-actions"><a className="button button--forest" href={edition.play_url}>Play {edition.id.toUpperCase()} <ArrowRight size={17}/></a><a className="button button--cream" href={`/${edition.id}/changes`}><History size={17}/> See changes</a></div></article>)}</section>
  </main>
}

export function ChangesPage({ editionId }: { editionId: string }) {
  const { data, error } = useReleases(); const edition = data?.editions.find(item => item.id === editionId)
  return <main className="edition-page changes-page"><a className="review-back" href="/">← All editions</a>{error && <p className="error-banner" role="alert">{error}</p>}{!data && !error && <p role="status">Loading release notes…</p>}{data && !edition && <p role="alert">This edition has not been published.</p>}{edition && <><header className="edition-hero"><p className="kicker">{edition.id} · published evolution</p><h1>{edition.title}</h1><p>{edition.summary}</p><div className="edition-actions"><a className="button button--forest" href={edition.play_url}>Play this edition</a><a className="button button--cream" href={edition.review_url}>Read edition reviews</a>{edition.source_url&&<a className="button button--cream" href={edition.source_url} target="_blank" rel="noreferrer">Git source</a>}{edition.compare_url&&<a className="button button--cream" href={edition.compare_url} target="_blank" rel="noreferrer">Compare changes</a>}</div></header><section className="changes-list"><h2>What changed</h2>{edition.changes.map((change, index) => <article key={`${change.title}-${index}`}><span className={`change-status change-status--${change.status}`}><CheckCircle2 size={15}/>{change.status}</span><h3>{change.title}</h3><p>{change.description}</p>{change.feedback_ids.length > 0 && <small>Responds to {change.feedback_ids.map((id,i)=><span key={id}>{i?', ':''}<a href={`${edition.review_url}#${id.split('-')[0]}`}>{id}</a></span>)}</small>}{change.evidence.length > 0 && <details><summary>Release evidence</summary><ul>{change.evidence.map(item => <li key={item}>{/^https?:\/\//.test(item)?<a href={item} target="_blank" rel="noreferrer">{item}</a>:item}</li>)}</ul></details>}</article>)}</section></>}</main>
}
