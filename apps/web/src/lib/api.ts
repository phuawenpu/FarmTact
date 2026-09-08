import type { Bootstrap, Crop, EvidenceRecord, Run } from './types'

const API = '/api/v1'

export class ApiError extends Error {
  status: number
  detail?: string
  constructor(message: string, status: number, detail?: string) {
    super(message)
    this.status = status
    this.detail = detail
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API}${path}`, {
    ...init,
    headers: {
      ...(init?.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }),
      ...init?.headers,
    },
  })
  if (!response.ok) {
    let detail: string | undefined
    try {
      const payload = (await response.json()) as { detail?: string }
      detail = payload.detail
    } catch {
      detail = undefined
    }
    throw new ApiError(detail || `Request failed (${response.status})`, response.status, detail)
  }
  return response.json() as Promise<T>
}

export const api = {
  bootstrap: () => request<Bootstrap>('/bootstrap'),
  crop: async (id: string) => {
    const response = await request<{ crop: Crop; evidence: EvidenceRecord[] }>(`/crops/${encodeURIComponent(id)}/evidence`)
    return { ...response.crop, evidence: response.evidence }
  },
  importSeed: () => request<{ id: string; status: string; version: number }>('/imports', { method: 'POST', body: JSON.stringify({ fixture: 'synthetic_demo' }) }),
  importFarm: (farm: unknown) => request<{ id: string; status: string; version: number }>('/imports', { method: 'POST', body: JSON.stringify({ farm }) }),
  createRun: (council = true) => request<{ id: string; status: string }>('/planning-runs', {
    method: 'POST',
    headers: { 'Idempotency-Key': crypto.randomUUID() },
    body: JSON.stringify({ council }),
  }),
  run: (id: string) => request<Run>(`/planning-runs/${encodeURIComponent(id)}`),
  replan: (id: string) => request<{ id: string; status: string } | Run>(`/planning-runs/${encodeURIComponent(id)}/replan`, {
    method: 'POST',
    headers: { 'Idempotency-Key': crypto.randomUUID() },
    body: JSON.stringify({ disruption: 'crop_delay' }),
  }),
  replay: (id: string) => request<Run>(`/planning-runs/${encodeURIComponent(id)}/replay`),
  demoReplay: () => request<Run>('/demo/replay'),
  eventsUrl: (id: string) => `${API}/planning-runs/${encodeURIComponent(id)}/events`,
}
