
import { lazy, StrictMode, Suspense, useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { createRoot } from 'react-dom/client'
import {
  ArrowDownRight, ArrowRight, ArrowUpRight, ChartBar, CheckCircle, Code, GitBranch, GithubLogo,
  Briefcase, Graph, ListChecks, Plus, Sparkle, Trash, X,
} from '@phosphor-icons/react'
import { api, errorText, pending } from './api'
import type { Repository, Scan, Session, Snapshot } from './api'
import { Practice } from './Practice'
import { Career } from './Career'
import './styles.css'

const CodeGraph = lazy(() => import('./Graph').then(module => ({ default: module.CodeGraph })))

type View = 'workspace' | 'rankings' | 'practice' | 'career'
type Tab = 'graph' | 'quality' | 'history'

function App() {
  const [view, setView] = useState<View>('workspace')
  const [tab, setTab] = useState<Tab>('graph')
  const [session, setSession] = useState<Session | null>(null)
  const [scans, setScans] = useState<Scan[]>([])
  const [active, setActive] = useState<string | null>(null)
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null)
  const [repo, setRepo] = useState('')
  const [consent, setConsent] = useState(false)
  const [notice, setNotice] = useState('')
  const [loadError, setLoadError] = useState('')
  const [busy, setBusy] = useState(false)
  const [picker, setPicker] = useState(false)
  const [repositories, setRepositories] = useState<Repository[]>([])
  const [pickerPage, setPickerPage] = useState(1)
  const [pickerStatus, setPickerStatus] = useState('')
  const [settings, setSettings] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState(false)
  const [previous, setPrevious] = useState<Scan | undefined>()
  const [practiceFocus, setPracticeFocus] = useState<string | null>(null)

  useEffect(() => {
    let alive = true
    void (async () => {
      try {
        const account = await api<Session>('/session')
        const results = await api<Scan[]>('/scans')
        if (alive) { setSession(account); setScans(results) }
      } catch (error) { if (alive) setNotice(errorText(error)) }
    })()
    const auth = new URLSearchParams(location.search).get('auth')
    if (auth) {
      history.replaceState(null, '', '/')
      if (auth !== 'connected') setNotice(auth === 'unavailable' ? 'GitHub sign-in is unavailable.' : 'GitHub could not connect. Please try again.')
    }
    return () => { alive = false }
  }, [])

  const shouldPoll = scans.some(pending)
  useEffect(() => {
    if (!shouldPoll) return
    let alive = true
    let timer: number
    async function attempt() {
      try {
        const next = await api<Scan[]>('/scans')
        if (alive) setScans(next)
        if (!next.some(pending)) return
      } catch (error) {
        if (alive) setNotice(errorText(error))
      }
      if (alive) timer = window.setTimeout(() => void attempt(), 1900)
    }
    timer = window.setTimeout(() => void attempt(), 1000)
    return () => { alive = false; window.clearTimeout(timer) }
  }, [shouldPoll])

  const selectedRow = scans.find(item => item.id === active)
  const selectedState = selectedRow?.state
  useEffect(() => {
    let alive = true
    setSnapshot(null)
    setLoadError('')
    if (active && selectedState !== 'complete') return
    const run = active
      ? api<Scan>('/scans/' + active).then(scan => scan.result as Snapshot)
      : api<Snapshot>('/sample')
    void run.then(result => { if (alive) setSnapshot(result) })
      .catch(error => { if (alive) setLoadError(errorText(error)) })
    return () => { alive = false }
  }, [active, selectedState])

  useEffect(() => {
    if (!picker) return
    let alive = true
    setPickerStatus('Loading repositories…')
    void api<Repository[]>('/github/repos?page=' + pickerPage).then(next => {
      if (alive) { setRepositories(next); setPickerStatus('') }
    }).catch(error => { if (alive) setPickerStatus(errorText(error)) })
    return () => { alive = false }
  }, [picker, pickerPage])

  async function start(event: FormEvent) {
    event.preventDefault()
    setNotice('')
    setBusy(true)
    try {
      const scan = await api<Scan>('/scans', 'POST', { repository: repo, ai: consent })
      setScans(current => [scan, ...current.filter(row => row.id !== scan.id)])
      openScan(scan.id)
      setRepo('')
      setConsent(false)
    } catch (error) { setNotice(errorText(error)) }
    finally { setBusy(false) }
  }

  function openScan(id: string | null, nextTab: Tab = 'graph') {
    setActive(id); setView('workspace'); setTab(nextTab); setPrevious(undefined)
  }

  async function removeScan(id: string) {
    try {
      await api('/scans/' + id, 'DELETE')
      setScans(current => current.filter(row => row.id !== id))
      if (active === id) openScan(null)
    } catch (error) { setNotice(errorText(error)) }
  }

  async function accountAction(remove: boolean) {
    setNotice('')
    try {
      await api(remove ? '/account' : '/auth/logout', remove ? 'DELETE' : 'POST')
      setSession(await api<Session>('/session'))
      setScans([])
      openScan(null)
      setSettings(false)
      setDeleteConfirm(false)
    } catch (error) { setNotice(errorText(error)) }
  }

  const summary = selectedRow?.result && 'error' in selectedRow.result ? selectedRow.result : null
  const comparable = scans.filter(row => row.id !== active && row.repo === snapshot?.repo && row.summary?.rankable
    && snapshot?.quality.rankable && row.summary.version === snapshot?.quality.version && row.summary.cohort === snapshot?.quality.cohort)

  return <>
    <header className="topbar">
      <div className="top-inner">
        <button className="brand" onClick={() => openScan(null)}><span className="brand-mark"><GitBranch size={21} weight="bold" /></span><span>SkillForge</span></button>
        <nav aria-label="Main navigation">
          <button className={view === 'workspace' ? 'nav-active' : ''} onClick={() => setView('workspace')}><Graph size={18} /> Workspace</button>
          <button className={view === 'rankings' ? 'nav-active' : ''} onClick={() => setView('rankings')}><ChartBar size={18} /> Rankings</button>
          <button className={view === 'practice' ? 'nav-active' : ''} onClick={() => { setPracticeFocus(null); setView('practice') }}><Code size={18} /> Practice</button>
          <button className={view === 'career' ? 'nav-active' : ''} onClick={() => setView('career')}><Briefcase size={18} /> Career</button>
        </nav>
        <button className="top-account" onClick={() => setSettings(!settings)} aria-expanded={settings}>
          <GithubLogo size={18} /><span>{session?.login ?? 'Account'}</span>
        </button>
      </div>
    </header>
    <main className="shell">
      {settings && <section className="settings-panel" aria-label="Account settings">
        <div className="split"><h2>Account</h2><button className="icon-button" onClick={() => setSettings(false)} aria-label="Close account settings"><X size={17} /></button></div>
        <p>{session?.login ? 'Connected as ' + session.login : 'You’re using a temporary workspace.'}</p>
        {session?.login ? <button className="button" onClick={() => void accountAction(false)}>Disconnect GitHub</button>
          : session?.oauth && <a className="button" href="/api/auth/github">Connect GitHub</a>}
        <div className="danger-zone">
          {deleteConfirm ? <><p>Delete your scans, practice results, and workspace data?</p><button className="button danger" onClick={() => void accountAction(true)}>Confirm deletion</button>
            <button className="button" onClick={() => setDeleteConfirm(false)}>Cancel</button></>
            : <button className="button danger" onClick={() => setDeleteConfirm(true)}>Delete workspace data</button>}
        </div>
      </section>}
      {notice && <div className="notice" role="alert">{notice}<button className="icon-button" onClick={() => setNotice('')} aria-label="Dismiss notice"><X size={16} /></button></div>}
      {view === 'workspace' ? <>
        <section className="hero">
          <div className="hero-copy">
            <p className="eyebrow"><span className="accent-square" /> Repository workspace</p>
            <h1>See how your<br className="desktop-break" /> code fits together<span>.</span></h1>
            <p>Map imports and calls, review common engineering practices, and see what to improve in your GitHub projects.</p>
          </div>
          <form className="import-panel" onSubmit={start}>
            <div className="import-title"><span className="up-arrow"><ArrowDownRight size={21} weight="bold" /></span><h2>Analyze a repository</h2></div>
            <label htmlFor="repository">Public GitHub URL</label>
            <div className="input-line"><GithubLogo size={19} /><input id="repository" autoComplete="off" value={repo} maxLength={280}
              onChange={event => setRepo(event.target.value)} placeholder="github.com/owner/repository" required /></div>
            {session?.ai && <label className="checkbox"><input type="checkbox" checked={consent} onChange={event => setConsent(event.target.checked)} />
              <span>Send up to six public source excerpts to Gemini for optional review.</span></label>}
            <div className="import-actions">
              <button className="button primary" disabled={busy || !session}>{busy ? 'Queuing…' : 'Analyze repo'} <ArrowRight size={17} /></button>
              {session?.oauth && !session.login && <a href="/api/auth/github" className="text-button">Connect GitHub</a>}
              {session?.login && <button type="button" className="text-button" onClick={() => { setPickerPage(1); setPicker(true) }}>Choose from GitHub</button>}
              <button type="button" className="text-button" onClick={() => openScan(null)}>Explore example</button>
            </div>
          </form>
        </section>
        <div className="workspace-grid">
          <aside className="library">
            <div className="split"><h2>Repositories</h2><button className="icon-button" aria-label="Focus repository import" onClick={() => document.getElementById('repository')?.focus()}><Plus size={17} /></button></div>
            <button className={'library-item' + (!active ? ' active' : '')} onClick={() => openScan(null)}>
              <GitBranch size={17} /><span><strong>delivery-routing</strong><small>Example workspace</small></span>
            </button>
            {scans.map(scan => <div className={'library-row' + (scan.id === active ? ' active' : '')} key={scan.id}>
              <button className="library-item" onClick={() => openScan(scan.id)}>
                <GitBranch size={17} /><span><strong>{scan.repo}</strong><small>{pending(scan) ? scan.state : scan.state === 'failed' ? 'Needs attention'
                  : (scan.revision?.slice(0, 7) ?? 'Complete') + (scan.summary?.score != null ? ' · ' + scan.summary.score + '/100' : '')}</small></span>
              </button>
              {!pending(scan) && <button className="icon-button tiny remove-scan" onClick={() => {
                if (window.confirm('Remove this scan from your workspace?')) void removeScan(scan.id)
              }} aria-label={'Remove scan for ' + scan.repo}><Trash size={14} /></button>}
            </div>)}
          </aside>
          <section className="detail" aria-label="Selected repository">
            <div className="detail-heading">
              <div><p className="eyebrow">{snapshot?.sample ? 'Example repository' : 'Repository analysis'}</p>
                <h2>{snapshot?.repo ?? selectedRow?.repo ?? 'Repository analysis'}</h2>
                {snapshot && <p>{snapshot.description || 'Analyze the structure and quality of this revision.'}</p>}</div>
              {snapshot && <div className="revision"><GitBranch size={16} /> {snapshot.branch}<span>{snapshot.revision.slice(0, 7)}</span></div>}
            </div>
            {!snapshot && !loadError && !summary && <div className="status-panel" role="status">{selectedState === 'queued' ? 'Waiting for an analysis worker…'
              : selectedState === 'running' ? 'Reading source and building the graph…' : 'Loading repository…'}</div>}
            {loadError && <div className="status-panel" role="alert">{loadError}</div>}
            {summary && <div className="status-panel" role="alert"><p>{summary.error}</p>
              {summary.retryAt && <p>Try after {new Date(summary.retryAt * 1000).toLocaleTimeString()}.</p>}
              <button className="button" onClick={() => { setRepo(selectedRow!.repo); document.getElementById('repository')?.focus() }}>Prepare another scan</button></div>}
            {snapshot && <>
              <div className="tabbar" aria-label="Repository views">
                <button className={tab === 'graph' ? 'current' : ''} onClick={() => setTab('graph')}><Graph size={17} /> Code graph</button>
                <button className={tab === 'quality' ? 'current' : ''} onClick={() => setTab('quality')}><ListChecks size={17} /> Quality score</button>
                <button className={tab === 'history' ? 'current' : ''} onClick={() => setTab('history')}><GitBranch size={17} /> Decision history</button>
              </div>
              {tab === 'graph' && <Suspense fallback={<p className="status-panel" role="status">Loading code graph…</p>}>
                <CodeGraph key={snapshot.repo + snapshot.revision} snapshot={snapshot} scanId={active} />
              </Suspense>}
              {tab === 'quality' && <Scorecard snapshot={snapshot} comparable={comparable} previous={previous} onCompare={setPrevious}
                onPractice={id => { setPracticeFocus(id); setView('practice'); window.scrollTo(0, 0) }} />}
              {tab === 'history' && <History snapshot={snapshot} />}
            </>}
          </section>
        </div>
      </> : view === 'rankings' ? <Rankings scans={scans} onOpen={id => openScan(id, 'quality')} onWorkspace={() => setView('workspace')} />
        : view === 'practice' ? <Practice enabled={!!session?.judge} initialProblem={practiceFocus} /> : <Career scans={scans} />}
    </main>
    <footer><span>SkillForge</span><span>Repository analysis and applied practice</span></footer>
    {picker && <div className="modal-backdrop"><section className="modal" role="dialog" aria-modal="true" aria-label="Choose a GitHub repository">
      <div className="split"><h2>Choose a public repository</h2><button className="icon-button" autoFocus onClick={() => setPicker(false)} aria-label="Close picker"><X size={18} /></button></div>
      {pickerStatus ? <p role="status">{pickerStatus}</p> : <div className="picker-list">
        {repositories.length ? repositories.map(item => <button key={item.name} onClick={() => { setRepo(item.name); setPicker(false); document.getElementById('repository')?.focus() }}>
          <GithubLogo size={17} /><span><strong>{item.name}</strong><small>{item.description ?? item.language ?? 'Public repository'}</small></span><ArrowRight size={16} />
        </button>) : <p>No public repositories on this page.</p>}
      </div>}
      <div className="split"><button className="button compact" disabled={pickerPage === 1 || !!pickerStatus} onClick={() => setPickerPage(pickerPage - 1)}>Previous</button>
        <span>Page {pickerPage}</span><button className="button compact" disabled={repositories.length < 30 || pickerPage >= 10 || !!pickerStatus}
          onClick={() => setPickerPage(pickerPage + 1)}>Next</button></div>
    </section></div>}
  </>
}

function History({ snapshot }: { snapshot: Snapshot }) {
  return <section className="panel history-panel">
    <h3>Recent pull request history</h3>
    <p>This view uses a bounded history sample. Pull request text can provide context for a decision.</p>
    {!snapshot.history_available && <p role="status">GitHub history is unavailable for this scan.</p>}
    {snapshot.history_available && !snapshot.history.length && <p>No pull requests were found in the sample.</p>}
    {snapshot.history.map(item => <article key={item.id}><span className="eyebrow">PR #{item.id} {item.date?.slice(0, 10)}</span>
      <h4>{item.url ? <a href={item.url} target="_blank" rel="noreferrer">{item.title} <ArrowUpRight size={14} /></a> : item.title}</h4><p>{item.body}</p>
    </article>)}
  </section>
}

function Scorecard({ snapshot, previous, comparable, onCompare, onPractice }: {
  snapshot: Snapshot; previous?: Scan; comparable: Scan[]; onCompare: (scan?: Scan) => void; onPractice: (id: string) => void
}) {
  const quality = snapshot.quality
  const delta = previous?.summary?.score != null && quality.score != null ? quality.score - previous.summary.score : null
  return <div className="report">
    <section className="score-overview panel">
      <div><p className="eyebrow">Provisional quality score</p><p className="score-number">{quality.score ?? '—'}<span> / 100</span></p>
        <p>{quality.coverage.analyzed} of {quality.coverage.eligible} eligible files analyzed · {quality.coverage.percent}% coverage</p>
        <p>{quality.rankable ? quality.cohort + ' cohort' : 'Unranked due to insufficient coverage'} · {quality.version}</p>
        {!!comparable.length && <label className="comparison">Compare with <select value={previous?.id ?? ''} onChange={event => onCompare(comparable.find(scan => scan.id === event.target.value))}>
          <option value="">Select revision</option>{comparable.map(scan => <option key={scan.id} value={scan.id}>{scan.revision?.slice(0, 7)} · {new Date(scan.created * 1000).toLocaleDateString()}</option>)}
        </select>{delta !== null && <strong>{delta > 0 ? '+' : ''}{delta} points</strong>}</label>}
      </div>
      <div className="dimensions">{quality.dimensions.map(dimension => <div key={dimension.name}>
        <div className="split"><span>{dimension.name}</span><strong>{dimension.max ? dimension.points + '/' + dimension.max : 'N/A'}</strong></div>
        <progress value={dimension.points} max={dimension.max || 1} aria-label={dimension.name} />
      </div>)}</div>
    </section>
    <section className="panel findings">
      <h3>Evidence and next steps</h3>
      <p>These checks look for common engineering signals in the sampled revision.</p>
      {[...quality.findings].sort((a, b) => Number(a.state === 'met') - Number(b.state === 'met') || b.max - a.max).map(finding =>
        <article key={finding.title}><div className="finding-icon">{finding.state === 'met' ? <CheckCircle size={22} /> : <Code size={22} />}</div>
          <div><h4>{finding.title}</h4><p>{finding.detail}</p>{finding.path && <small className="mono">{finding.url && !snapshot.sample
            ? <a href={finding.url} target="_blank" rel="noreferrer">{finding.path}:{finding.line} <ArrowUpRight size={13} /></a>
            : finding.path + ':' + finding.line}</small>}
            {finding.state === 'review' && finding.dimension === 'Performance hygiene' && <button className="text-button"
              onClick={() => onPractice('load-monitor')}>Practice efficient processing</button>}
            {finding.state === 'review' && finding.title === 'Test files are present' && <button className="text-button"
              onClick={() => onPractice('support-coverage')}>Practice boundary cases</button>}</div>
          <span className={'finding-pts ' + finding.state}>{finding.points}/{finding.max}</span></article>)}
    </section>
    {snapshot.review && <section className="panel findings">
      <h3><Sparkle size={20} /> Optional Gemini review</h3>
      {snapshot.review.mode === 'unavailable' && <p>Gemini was unavailable. The static quality report is ready.</p>}
      {snapshot.review.mode === 'reviewed' && !snapshot.review.findings.length && <p>No cited additional findings returned.</p>}
      {snapshot.review.findings.map((item, index) => <article key={index}>
        <div className="finding-icon"><Sparkle size={20} /></div><div><h4>{item.title}</h4><p>{item.detail}</p>
          {item.url && <a href={item.url} target="_blank" rel="noreferrer">{item.path}:{item.line} <ArrowUpRight size={14} /></a>}</div></article>)}
    </section>}
  </div>
}

function Rankings({ scans, onOpen, onWorkspace }: { scans: Scan[]; onOpen: (id: string) => void; onWorkspace: () => void }) {
  const latest = [...new Map([...scans].reverse().filter(row => row.state === 'complete').map(row => [row.repo, row])).values()]
  const ranked = latest.filter(row => row.summary?.rankable && row.summary.score !== null)
  const groups = Map.groupBy(ranked, row => (row.summary?.cohort ?? 'Unknown') + ' · ' + row.summary?.version)
  const unranked = latest.filter(row => !row.summary?.rankable)
  return <section className="ranking-page">
    <p className="eyebrow"><span className="accent-square" /> Repository quality</p>
    <h1>Repository rankings<span>.</span></h1>
    <p>Compare the latest completed scan per repository within the same language cohort and scoring version.</p>
    {!latest.length && <div className="status-panel"><p>Analyze a public repository to start your rankings.</p><button className="button primary" onClick={onWorkspace}>Open workspace <ArrowRight size={16} /></button></div>}
    {[...groups].map(([name, rows]) => <section className="panel rankings" key={name}><h2>{name}</h2>
      {rows.sort((a, b) => (b.summary?.score ?? 0) - (a.summary?.score ?? 0)).map((row, index, ordered) =>
        <button key={row.id} onClick={() => onOpen(row.id)}><span>{ordered.findIndex(item => item.summary?.score === row.summary?.score) + 1 || index + 1}</span>
          <strong>{row.repo}</strong><span>{row.summary?.coverage.percent}% coverage</span><strong>{row.summary?.score}/100</strong><ArrowUpRight size={17} /></button>)}
    </section>)}
    {!!unranked.length && <section className="panel rankings"><h2>Unranked</h2>{unranked.map(row => <button key={row.id} onClick={() => onOpen(row.id)}>
      <span>—</span><strong>{row.repo}</strong><span>{row.summary?.coverage.percent}% coverage</span><span>Partial</span><ArrowUpRight size={17} /></button>)}</section>}
  </section>
}

createRoot(document.getElementById('root')!).render(<StrictMode><App /></StrictMode>)
