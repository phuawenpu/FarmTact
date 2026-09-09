export interface NewsRecord {
  id: string
  source_id: string
  title: string
  canonical_url: string
  published_at_raw: string
  published_at: string
  retrieved_at: string
  observed_at?: string | null
  event_start_at?: string | null
  event_end_at?: string | null
  event_date_basis?: string | null
  geography: 'singapore' | 'regional'
  crop_ids: string[]
  topics: string[]
  quality_issues: string[]
  content_hash: string
  temporal_fit: 'recent' | 'historical' | 'future' | 'ongoing'
  retrieval_freshness: string
  relevance: string
}
export interface NewsSource {
  id: string
  name: string
  status: string
  scope: string
  url?: string | null
  terms_url?: string | null
  publisher_kind: string
  reuse_mode: string
  record_count?: number
  rejected_count?: number
  last_attempt_at?: string | null
  last_success_at?: string | null
}
export interface NewsContext {
  status: string
  frozen: boolean
  cutoff?: string
  farm_cutoff?: string
  content_hash?: string
  decision_id?: string
  records: NewsRecord[]
  sources: NewsSource[]
  total: number
  summary: string
  limitations?: string[]
}
