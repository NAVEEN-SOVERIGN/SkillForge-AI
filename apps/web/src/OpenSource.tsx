import { ArrowLeft, ArrowRight, ArrowUpRight, GitBranch, GithubLogo } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { api, errorText } from './api'
import './open-source.css'

type Issue = { repo: string; number: number; title: string; summary: string; updated: string | null; url: string }
type Results = { items: Issue[]; partial: boolean; more: boolean }
const languages = ['Python', 'JavaScript', 'TypeScript', 'Java', 'Go', 'Rust', 'C++', 'Ruby']

function issuePreview(markdown: string) {
  return markdown
    .replace(/<!--[^]*?(?:-->|$)/g, ' ')
    .replace(/```[^]*?(?:```|$)/g, ' ')
    .replace(/!\[[^\]]*\]\([^)]*\)/g, '')
    .replace(/\[([^\]]+)\]\([^)]*(?:\)|$)/g, '$1')
    .replace(/^\s{0,3}(?:#{1,6}\s+|>\s*|[-*+]\s+(?:\[[ xX]\]\s*)?)/gm, '')
    .replace(/(\*\*|__|~~|`)([^\n]+?)\1/g, '$2')
    .replace(/\s+/g, ' ')
    .trim()
}

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

  const labelName = label === 'good first issue' ? 'Good first issue' : 'Help wanted'

  return <section className="contributions" aria-labelledby="contributions-title">
    <header className="contributions-intro">
      <h1 id="contributions-title">Open source contributions</h1>
      <p>Find an unassigned GitHub issue in your stack. Explore the code in SkillForge or open the issue to get started.</p>
    </header>

    <div className="contributions-toolbar">
      <label>Language <select value={language} onChange={event => {
        setPage(1); setLanguage(event.target.value)
      }}>{languages.map(value => <option key={value}>{value}</option>)}</select></label>
      <label>Issue label <select value={label} onChange={event => {
        setPage(1); setLabel(event.target.value)
      }}><option value="good first issue">Good first issue</option><option value="help wanted">Help wanted</option></select></label>
    </div>

    <section className="contributions-feed" aria-labelledby="issue-results-heading" aria-busy={!results && !error}>
      <header className="contributions-feed-head">
        <h2 id="issue-results-heading">Open issues</h2>
        <span role="status">{results ? `${results.items.length} on this page` : ''}</span>
      </header>
      {error ? <div className="contributions-state" role="status">
        <p>{error}</p> <button className="button compact" onClick={() => setRetry(retry + 1)}>Retry</button>
      </div> : !results ? <p className="contributions-state" role="status">Loading GitHub issues…</p>
      : <>
        {results.partial && <p className="contributions-state" role="status">GitHub returned partial results.</p>}
        {!results.items.length && <p className="contributions-state">No open issues matched these filters on this page.</p>}
        {results.items.map(issue => {
          const preview = issuePreview(issue.summary)
          return <article className="contribution-issue" key={issue.url}>
            <div className="contribution-issue-copy">
              <div className="contribution-meta"><GitBranch size={15} aria-hidden="true" /><span>{issue.repo}</span><span>#{issue.number}</span></div>
              <h3><a href={issue.url} target="_blank" rel="noreferrer">{issue.title.replaceAll('`', '')} <ArrowUpRight size={15} aria-hidden="true" /></a></h3>
              {preview && <p className="contribution-excerpt">{preview}</p>}
              <div className="contribution-details">
                <span className="contribution-label">{labelName}</span>
                {issue.updated && <time dateTime={issue.updated}>Updated {issue.updated.slice(0, 10)}</time>}
              </div>
            </div>
            <div className="contribution-actions">
              <a className="button" href={issue.url} target="_blank" rel="noreferrer"><GithubLogo size={16} aria-hidden="true" /> View on GitHub</a>
              <button className="text-button" onClick={() => onExplore(issue.repo)}>Explore repository <ArrowRight size={14} aria-hidden="true" /></button>
            </div>
          </article>
        })}
        {(page > 1 || results.more) && <nav className="contributions-pagination" aria-label="Issue pages">
          <button className="button compact" disabled={page === 1} onClick={() => setPage(page - 1)}><ArrowLeft size={14} /> Previous</button>
          <span>Page {page}</span>
          <button className="button compact" disabled={!results.more} onClick={() => setPage(page + 1)}>Next <ArrowRight size={14} /></button>
        </nav>}
      </>}
    </section>
  </section>
}
