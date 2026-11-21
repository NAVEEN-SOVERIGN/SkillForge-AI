import { ArrowUpRight, GitBranch } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { api, errorText } from './api'

type Issue = { repo: string; number: number; title: string; summary: string; updated: string | null; url: string }
type Results = { items: Issue[]; partial: boolean; more: boolean }
const languages = ['Python', 'JavaScript', 'TypeScript', 'Java', 'Go', 'Rust', 'C++', 'Ruby']

export function OpenSource({ onExplore }: { onExplore: (repo: string) => void }) {
  const [language, setLanguage] = useState('Python')
  const [label, setLabel] = useState('good first issue')
  const [page, setPage] = useState(1)
  const [retry, setRetry] = useState(0)
  const [results, setResults] = useState<Results>()
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    setResults(undefined)
    setError('')
    const params = new URLSearchParams({ language, label, page: String(page) })
    void api<Results>('/contributions?' + params).then(value => {
      if (active) setResults(value)
    }).catch(error => {
      if (active) setError(errorText(error))
    })
    return () => { active = false }
  }, [language, label, page, retry])

  return <section className="panel findings">
    <h1>Open source contributions</h1>
    <p>Find an unassigned GitHub issue in your stack. Open it to check the scope and ask maintainers how to get started.</p>
    <div className="score-filters">
      <label className="comparison">Language <select value={language} onChange={event => {
        setPage(1); setLanguage(event.target.value)
      }}>{languages.map(value => <option key={value}>{value}</option>)}</select></label>
      <label className="comparison">Issue label <select value={label} onChange={event => {
        setPage(1); setLabel(event.target.value)
      }}><option value="good first issue">Good first issue</option><option value="help wanted">Help wanted</option></select></label>
    </div>
    {error ? <p role="status">{error} <button className="button compact" onClick={() => setRetry(retry + 1)}>Retry</button></p>
      : !results ? <p role="status">Loading GitHub issues…</p>
      : <>
        {results.partial && <p role="status">GitHub returned partial results.</p>}
        {!results.items.length && <p>No open issues matched these filters on this page.</p>}
        {results.items.map(issue => <article key={issue.url}>
          <GitBranch size={19} />
          <div className="word-wrap">
            <small>{issue.repo} · #{issue.number}{issue.updated && ' · Updated ' + issue.updated.slice(0, 10)}</small>
            <h3><a href={issue.url} target="_blank" rel="noreferrer">{issue.title} <ArrowUpRight size={14} /></a></h3>
            {issue.summary && <p>{issue.summary}</p>}
            <button className="button compact" onClick={() => onExplore(issue.repo)}>Explore repository in SkillForge</button>
          </div>
        </article>)}
        {(page > 1 || results.more) && <div className="score-filters" aria-label="Issue pages">
          <button className="button compact" disabled={page === 1} onClick={() => setPage(page - 1)}>Previous</button>
          <span>Page {page}</span>
          <button className="button compact" disabled={!results.more} onClick={() => setPage(page + 1)}>Next</button>
        </div>}
      </>}
  </section>
}
