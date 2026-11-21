
import { ArrowDown, Check, LinkSimple, Plus, Trash } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { api, errorText } from './api'
import type { Scan, Session } from './api'
import { ContributionRoadmap } from './ContributionRoadmap'

type Action = { id: string; skill: string; state: 'proposed' | 'approved' | 'completed' | 'dismissed' }
type Entry = { id: string; title: string; kind: string; label: string; note: string }
type CareerData = {
  roles: string[]; requirements: string[]; planned: string[]; open: string[]
  profile: { role: string; description: string; hours: number; evidence: Entry[]; actions: Action[]
    audit: { action: string; state: string; at: number }[] }
}
type Attempt = { id: string; problem: string; passed: number; total: number; created: number }
type Scores = { engineering: number | null; problemSolving: number | null; index: number | null
  problems: number; provisional: boolean; repository: string | null }

export function Career({ scans, session, focusRoadmap, onDiscover, onPractice }: {
  scans: Scan[]; session: Session | null; focusRoadmap: boolean; onDiscover: () => void; onPractice: () => void
}) {
  const [data, setData] = useState<CareerData | null>(null)
  const [attempts, setAttempts] = useState<Attempt[]>([])
  const [target, setTarget] = useState({ role: '', description: '', hours: 5 })
  const [reference, setReference] = useState('')
  const [note, setNote] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [status, setStatus] = useState('')
  const [scores, setScores] = useState<Scores | null>(null)

  useEffect(() => {
    let alive = true
    void Promise.all([api<CareerData>('/career'), api<Attempt[]>('/practice/attempts')]).then(([next, history]) => {
      if (!alive) return
      setData(next)
      setTarget({ role: next.profile.role, description: next.profile.description, hours: next.profile.hours })
      setAttempts(history)
    }).catch(failure => { if (alive) setError(errorText(failure)) })
    void api<Scores>('/career/developer-index').then(result => { if (alive) setScores(result) }).catch(() => undefined)
    return () => { alive = false }
  }, [])

  async function update(path: string, method: string, body: unknown, message: string) {
    setBusy(true); setError(''); setStatus('')
    try {
      setData(await api<CareerData>('/career' + path, method, body))
      setStatus(message)
      return true
    } catch (failure) {
      setError(errorText(failure))
      return false
    } finally { setBusy(false) }
  }

  async function attach(event: FormEvent) {
    event.preventDefault()
    const [kind, id] = reference.split(':')
    if (id && await update('/evidence', 'POST', { kind, reference: id, note }, 'Evidence added.')) {
      setReference('')
      setNote('')
    }
  }

  const active = new Set(data?.profile.actions.filter(item => item.state !== 'dismissed').map(item => item.skill))
  const completedScans = scans.filter(scan => scan.state === 'complete')
  return <section className="ranking-page career">
    <p className="eyebrow"><span className="accent-square" /> Portfolio and planning</p>
    <h1>Career plan<span>.</span></h1>
    <p>Set a role, track learning actions, and attach repository and assessment results to your portfolio.</p>
    {error && <p className="notice" role="alert">{error}</p>}
    {status && <p className="career-status" role="status"><Check size={16} /> {status}</p>}
    {!data && !error && <p className="status-panel" role="status">Loading career plan…</p>}
    {scores && <section className="panel developer-index" aria-label="Developer index">
      <div className="split"><h2>Developer Index</h2>{scores.provisional && <span className="eyebrow">Provisional</span>}</div>
      <div className="index-scores">{[
        ['Engineering', scores.engineering, scores.repository ?? 'Eligible score from a repo owned by your connected GitHub account'],
        ['Problem solving', scores.problemSolving, scores.problems + ' distinct assessed exercises'],
        ['Combined index', scores.index, '60% engineering and 40% problem solving'],
      ].map(([name, score, detail]) => <article key={name}><h3>{name}</h3><strong>{score ?? '—'}{score != null && <small> / 1,000</small>}</strong><p>{detail}</p></article>)}</div>
    </section>}
    {data && <>
      <div className="career-grid">
        <form className="panel form-stack" onSubmit={event => {
          event.preventDefault(); void update('/target', 'PUT', target, 'Target saved.')
        }}>
          <h2>Target role</h2>
          <label>Role<select value={target.role} onChange={event => setTarget({ ...target, role: event.target.value })}>
            {data.roles.map(role => <option key={role}>{role}</option>)}</select></label>
          <label>Study hours per week<input type="number" min={1} max={40} value={target.hours}
            onChange={event => setTarget({ ...target, hours: event.target.valueAsNumber })} required /></label>
          <label>Job description <small>Optional</small><textarea rows={4} maxLength={6000} value={target.description}
            onChange={event => setTarget({ ...target, description: event.target.value })} /></label>
          <button className="button primary" disabled={busy}>Save target</button>
        </form>
        <section className="panel" aria-label="Role requirements"><h2>Learning priorities</h2>
          <p>{data.planned.length} of {data.requirements.length} role skills have a completed learning action.</p>
          <div className="skill-list">{data.requirements.map(skill => <div className="split" key={skill}>
            <span>{skill}</span>
            {active.has(skill) ? <span className="eyebrow">{data.planned.includes(skill) ? 'Complete' : 'In plan'}</span> :
              <button className="button compact" disabled={busy} onClick={() => void update('/actions', 'POST', { skill }, 'Action proposed.')}><Plus size={14} /> Propose action</button>}
          </div>)}</div>
        </section>
      </div>
      <ContributionRoadmap session={session} focusOnMount={focusRoadmap} onDiscover={onDiscover} onPractice={onPractice}
        refreshKey={JSON.stringify([data.profile.role, data.profile.description, data.profile.hours,
          session?.login, completedScans.map(scan => scan.id)])} />
      <section className="panel plan-actions">
        <h2>Actions</h2>
        {!data.profile.actions.length && <p>Propose an action from the learning priorities.</p>}
        {data.profile.actions.map(item => <article key={item.id} className="split action-row">
          <div><h3>{item.skill}</h3><p className="eyebrow">{item.state}</p></div>
          <div className="inline-buttons">
            {item.state === 'proposed' && <button className="button compact primary" disabled={busy}
              onClick={() => void update('/actions/' + item.id, 'PATCH', { state: 'approved' }, 'Action approved.')}>Approve</button>}
            {item.state === 'approved' && <button className="button compact primary" disabled={busy}
              onClick={() => void update('/actions/' + item.id, 'PATCH', { state: 'completed' }, 'Action completed.')}>Complete</button>}
            {(item.state === 'proposed' || item.state === 'approved') && <button className="button compact" disabled={busy}
              onClick={() => void update('/actions/' + item.id, 'PATCH', { state: 'dismissed' }, 'Action dismissed.')}>Dismiss</button>}
          </div>
        </article>)}
        {!!data.profile.audit.length && <details><summary>Action history</summary><ul>
          {data.profile.audit.map((item, index) => <li key={index}>{data.profile.actions.find(action => action.id === item.action)?.skill}
            {' · '}{item.state}{' · '}{new Date(item.at * 1000).toLocaleString()}</li>)}</ul></details>}
      </section>
      <div className="career-grid">
        <form className="panel form-stack" onSubmit={attach}>
          <h2>Add portfolio evidence</h2>
          <label>Completed result<select value={reference} onChange={event => setReference(event.target.value)} required>
            <option value="">Choose a result</option>
            {completedScans.map(item => <option key={item.id} value={'repository:' + item.id}>{item.repo} · {item.revision?.slice(0, 7)}</option>)}
            {attempts.map(item => <option key={item.id} value={'assessment:' + item.id}>{item.problem.replaceAll('-', ' ')} · {item.passed}/{item.total}</option>)}
          </select></label>
          <label>What did you contribute?<textarea rows={4} maxLength={400} value={note} onChange={event => setNote(event.target.value)} /></label>
          <button className="button primary" disabled={busy || !reference}><LinkSimple size={16} /> Attach evidence</button>
        </form>
        <section className="panel">
          <div className="split"><h2>Portfolio evidence</h2><a className="button compact" href="/api/career/report.pdf"><ArrowDown size={14} /> Download PDF</a></div>
          {!data.profile.evidence.length && <p>Completed scans and coding tests can be linked here.</p>}
          {data.profile.evidence.map(item => <article key={item.id} className="evidence-row">
            <div className="split"><h3>{item.title}</h3><button className="icon-button" disabled={busy} aria-label={'Remove ' + item.title}
              onClick={() => void update('/evidence/' + item.id, 'DELETE', undefined, 'Evidence removed.')}><Trash size={15} /></button></div>
            <p className="eyebrow">{item.label}</p>{item.note && <p>{item.note}</p>}
          </article>)}
        </section>
      </div>
    </>}
  </section>
}
