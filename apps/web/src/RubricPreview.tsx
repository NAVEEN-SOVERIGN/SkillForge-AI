
import { ArrowRight, ArrowUpRight } from '@phosphor-icons/react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import { errorText, type Criterion, type Snapshot } from './api'

const RELEVANCE = {
  applicable: 'Applicable', not_applicable: 'Not applicable', uncertain: 'Uncertain',
}

export function RubricCriteria({ criteria, expected = [], onToggle }: {
  criteria: Criterion[]; expected?: string[]; onToggle?: (id: string) => void
}) {
  return <div className="criterion-list">
    {criteria.map(item => <article key={item.id} className="criterion">
      <div><h4>{item.name}</h4><p>{item.reason}</p>
        {item.evidence?.path && (item.evidence.url
          ? <a href={item.evidence.url} target="_blank" rel="noreferrer">{item.evidence.path}:{item.evidence.line} <ArrowUpRight size={13} /></a>
          : <small>{item.evidence.path}:{item.evidence.line}</small>)}
        {onToggle && item.relevance === 'not_applicable' && <label className="checkbox">
          <input type="checkbox" checked={expected.includes(item.id)} onChange={() => onToggle(item.id)} />
          This capability is expected for this project
        </label>}
      </div>
      <div><strong>{RELEVANCE[item.relevance]}</strong>
        {item.relevance !== 'not_applicable' && <small>Weight {item.proposedWeight}</small>}</div>
    </article>)}
  </div>
}

export function RubricPreview({ snapshot, onApprove }: {
  snapshot: Snapshot; onApprove: (expected: string[], note: string) => Promise<void>
}) {
  const [expected, setExpected] = useState<string[]>([])
  const [note, setNote] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try { await onApprove(expected, note) }
    catch (failure) { setError(errorText(failure)); setBusy(false) }
  }

  return <form className="panel rubric-preview" onSubmit={submit}>
    <p className="eyebrow">Rubric review</p>
    <h3>{snapshot.quality.archetype}</h3>
    <p>Review which criteria apply before publishing the engineering score. Project expectations you flag will be marked uncertain pending source evidence.</p>
    {!!snapshot.quality.features?.length && <div className="history-results">
      <h4>Detected features</h4>
      {snapshot.quality.features.map(item => <div key={item.name}>{item.name}{item.evidence?.url && <> · <a
        href={item.evidence.url} target="_blank" rel="noreferrer">{item.evidence.path}:{item.evidence.line}</a></>}</div>)}
    </div>}
    {!!snapshot.review?.context?.length && <div className="history-results">
      <h4>AI observations with matching static signals</h4>
      {snapshot.review.context.map(item => <div key={item.title + item.line}>
        <strong>{item.title}</strong> · {item.detail} {item.url && <a href={item.url} target="_blank" rel="noreferrer">Source</a>}
      </div>)}
    </div>}
    <RubricCriteria criteria={snapshot.quality.criteria ?? []} expected={expected} onToggle={id => setExpected(current =>
      current.includes(id) ? current.filter(value => value !== id) : [...current, id])} />
    <label className="rubric-note">Challenge a relevance decision <textarea rows={3} value={note} onChange={event => setNote(event.target.value)}
      placeholder="Describe the capability or point to the relevant source." maxLength={600} /></label>
    {(expected.length > 0 || note.trim()) && <p className="subtle">A challenged rubric publishes an unranked score.</p>}
    {error && <p className="notice" role="alert">{error}</p>}
    <button className="button primary" disabled={busy}>{busy ? 'Publishing…' : 'Publish score'} <ArrowRight size={16} /></button>
  </form>
}
