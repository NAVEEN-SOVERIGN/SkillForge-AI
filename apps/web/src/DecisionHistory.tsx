
import { ArrowDown, ArrowUpRight, MagnifyingGlass } from '@phosphor-icons/react'
import { useState } from 'react'
import type { FormEvent } from 'react'
import type { Snapshot } from './api'

type Record = Snapshot['history'][number]
const stopWords = new Set(['the', 'and', 'were', 'was', 'with', 'why', 'how', 'what', 'when', 'did', 'does', 'has', 'have', 'that', 'this', 'for'])
const terms = (value: string) => value.toLowerCase().match(/[a-z0-9_-]{3,50}/g) ?? []
const label = (item: Record) => item.label ?? 'PR #' + item.id

function evidenceFor(question: string, records: Record[]) {
  const query = new Set(terms(question).filter(word => !stopWords.has(word)))
  return records.map(item => {
    const title = new Set(terms(item.title))
    const body = new Set(terms(item.body))
    let points = 0
    for (const word of query) points += title.has(word) ? 3 : body.has(word) ? 1 : 0
    return { item, points }
  }).filter(row => row.points > 0).sort((a, b) => b.points - a.points).slice(0, 4).map(row => row.item)
}

function markdownText(value: string) {
  return value.replace(/[\u0000-\u001f]/g, ' ').replace(/[\\[\]<>#*_]/g, character => '\\' + character).trim()
}

export function DecisionHistory({ snapshot }: { snapshot: Snapshot }) {
  const [query, setQuery] = useState('')
  const [asked, setAsked] = useState('')
  const [through, setThrough] = useState('')
  const displayed = snapshot.history.filter(item => !through || (item.date ?? '').slice(0, 10) <= through)
  const matched = asked ? evidenceFor(asked, displayed) : []
  const highestDate = snapshot.history.find(item => item.date)?.date?.slice(0, 10)

  function ask(event: FormEvent) {
    event.preventDefault()
    setAsked(query.trim())
  }

  function exportDraft() {
    const content = [
      '# Architecture decision draft', '', '## Current question', markdownText(asked), '',
      '## Repository', markdownText(snapshot.repo + ' · ' + snapshot.revision), '', '## Cited context',
      ...matched.flatMap(item => [
        '### ' + markdownText(label(item) + ' · ' + item.title), markdownText(item.body || 'No explanation in this record.'),
        ...(item.url ? [item.url] : []), '',
      ]),
      '## Decision', 'Review evidence and record the decision.', '',
      '## Consequences', 'Record trade-offs after review.',
    ].join('\n')
    const url = URL.createObjectURL(new Blob([content], { type: 'text/markdown;charset=utf-8' }))
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'architecture-decision-draft.md'
    anchor.click()
    window.setTimeout(() => URL.revokeObjectURL(url), 1500)
  }

  function record(item: Record) {
    return <article key={item.id}><span className="eyebrow">{label(item)} {item.date?.slice(0, 10)}</span>
      <h4>{item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.title} <ArrowUpRight size={14} /></a> : item.title}</h4>
      {item.body && <p>{item.body}</p>}
    </article>
  }

  return <section className="panel history-panel">
    <div className="split"><h3>Decision history</h3>{!!snapshot.history.length &&
      <label className="history-date">Show through <input type="date" max={highestDate} value={through}
        onChange={event => setThrough(event.target.value)} /></label>}</div>
    <p>Read pull requests and commits from a bounded history sample.</p>
    {!snapshot.history_available && <p role="status">GitHub history is unavailable for this scan.</p>}
    {snapshot.history_available && !displayed.length && <p>No history records in this date range.</p>}
    {!!snapshot.history.length && <form className="history-search" onSubmit={ask}>
      <label className="search-field"><MagnifyingGlass size={16} /><input aria-label="Ask about repository history" value={query}
        onChange={event => setQuery(event.target.value)} maxLength={200} placeholder="Why are routes sorted by zone?" required /></label>
      <button className="button primary">Find evidence</button>
      {asked && <button type="button" className="text-button" onClick={() => { setAsked(''); setQuery('') }}>Clear question</button>}
    </form>}
    {asked && <section className="history-results" aria-label="Question evidence">
      <div className="split"><h4>Evidence for “{asked}”</h4>
        {!!matched.length && <button className="button compact" onClick={exportDraft}><ArrowDown size={15} /> Export decision draft</button>}</div>
      {matched.length ? <><p>These records match the question. Review their wording before attributing a decision.</p>{matched.map(record)}</>
        : <p>The indexed history does not contain supporting records for this question.</p>}
    </section>}
    <h4>Timeline</h4>
    {displayed.map(record)}
  </section>
}
