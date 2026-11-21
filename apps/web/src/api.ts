
export type Session = { login: string | null; oauth: boolean; ai: boolean; judge: boolean }
export type Node = { id: string; label: string; kind: string; path: string | null; line: number | null }
export type Edge = { source: string; target: string; kind: string; path: string; line: number | null }
export type Citation = { title: string; detail: string; path: string | null; line: number | null; url: string | null }
export type Finding = Citation & { dimension: string; points: number; max: number; state: 'met' | 'review' }
export type Coverage = { analyzed: number; eligible: number; percent: number; total: number; truncated: boolean }
export type ScoreSummary = { score: number | null; rankable: boolean; cohort: string | null; version: string; coverage: Coverage }
export type Quality = ScoreSummary & { dimensions: { name: string; points: number; max: number }[]; findings: Finding[] }
export type Snapshot = {
  repo: string; branch: string; revision: string; description: string; language: string | null; sample: boolean
  graph: { nodes: Node[]; edges: Edge[]; unresolved: number; limited: boolean }
  quality: Quality
  history: { id: number; title: string; body: string; date: string; url?: string }[]
  history_available: boolean
  preview_paths: string[]
  review?: { mode: 'reviewed' | 'unavailable'; model?: string; findings: Citation[] }
}
export type Scan = {
  id: string; repo: string; state: 'queued' | 'running' | 'complete' | 'failed'; created: number; updated: number
  revision?: string; summary?: ScoreSummary; result?: Snapshot | { error: string; retryAt?: number }
}
export type Repository = { name: string; description: string | null; language: string | null }
export type Source = { path: string; source: string; url: string | null }

export async function api<T>(path: string, method = 'GET', body?: unknown): Promise<T> {
  const result = await fetch('/api' + path, {
    method, credentials: 'same-origin',
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!result.ok) {
    const error = await result.json().catch(() => ({}))
    throw new Error(typeof error.detail === 'string' ? error.detail : 'The request could not be completed.')
  }
  return result.status === 204 ? undefined as T : result.json()
}

export const pending = (scan: Scan) => scan.state === 'queued' || scan.state === 'running'
export const errorText = (error: unknown) => error instanceof Error ? error.message : 'Something went wrong.'
