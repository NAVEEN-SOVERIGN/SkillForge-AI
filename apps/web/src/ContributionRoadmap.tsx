import { useEffect, useRef, useState } from 'react'
import { ArrowUpRight } from '@phosphor-icons/react'
import { api, errorText } from './api'
import type { Session } from './api'

type Citation = { title: string; url: string; kind: string; date?: string }
type Project = {
  id: string; title: string; difficulty: string; hours: number; skills: string[]
  problem: string; deliverable: string; completed: string[]
  tasks: { id: string; title: string; acceptance: string }[]
}
type Plan = {
  projects: Project[]; selected: string | null; hours: number; assessments: number; scans: Citation[]
  activity: { items: Citation[]; partial: boolean; at: number } | null
  steps: { title: string; reason: string; citation: Citation | null; project: string | null }[]
}
const endpoint = '/career/contribution-roadmap'

export function ContributionRoadmap({ session, refreshKey, focusOnMount, onDiscover, onPractice }: {
  session: Session | null; refreshKey: string; focusOnMount: boolean; onDiscover: () => void; onPractice: () => void
}) {
  const [plan, setPlan] = useState<Plan>()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [retry, setRetry] = useState(0)
  const [status, setStatus] = useState('')
  const heading = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    if (focusOnMount) heading.current?.focus()
  }, [focusOnMount])

  useEffect(() => {
    let active = true
    void api<Plan>(endpoint).then(next => {
      if (active) { setPlan(next); setError('') }
    }).catch(failure => { if (active) setError(errorText(failure)) })
    return () => { active = false }
  }, [refreshKey, retry])

  async function update(path: string, method: string, data?: unknown) {
    setBusy(true); setError(''); setStatus('')
    try {
      setPlan(await api<Plan>(endpoint + path, method, data))
      setStatus(method === 'POST' ? 'Public GitHub activity updated.'
        : method === 'DELETE' ? 'Imported GitHub activity removed.' : 'Project progress saved.')
    } catch (failure) { setError(errorText(failure)) }
    finally { setBusy(false) }
  }

  return <section className="panel contribution-roadmap" aria-labelledby="contribution-roadmap-title">
    <h2 id="contribution-roadmap-title" ref={heading} tabIndex={-1}>Contribution roadmap</h2>
    <p>Work through GSoC-style practice projects and use your contribution history to choose the next step.</p>
    {error && <p className="notice" role="alert">{error} <button className="button compact" onClick={() => setRetry(retry + 1)}>Retry loading</button></p>}
    {status && <p role="status">{status}</p>}
    {!plan && !error && <p role="status">Loading contribution roadmap…</p>}
    {plan && <>
      <div className="contribution-plan-grid">
        <section aria-labelledby="roadmap-steps-title">
          <h3 id="roadmap-steps-title">Next steps</h3>
          <ol className="roadmap-steps">{plan.steps.map(step => <li key={step.title}>
            <strong>{step.project ? <a href={'#project-' + step.project} onClick={() => {
              const project = document.getElementById('project-' + step.project)
              if (project instanceof HTMLDetailsElement) project.open = true
            }}>{step.title}</a> : step.title}</strong>
            <p>{step.reason}</p>
            {step.citation && <small>{step.citation.kind} · <a href={step.citation.url} target="_blank" rel="noreferrer">
              {step.citation.title} <ArrowUpRight size={13} />
            </a></small>}
          </li>)}</ol>
          <div className="inline-buttons">
            <button className="button compact" onClick={onDiscover}>Browse open issues</button>
            <button className="button compact" onClick={onPractice}>Open practice scenarios</button>
          </div>
        </section>
        <section className="roadmap-evidence" aria-labelledby="roadmap-evidence-title">
          <h3 id="roadmap-evidence-title">Roadmap evidence</h3>
          <p>{plan.scans.length} recent scanned {plan.scans.length === 1 ? 'repository' : 'repositories'} · {plan.assessments} assessed scenarios</p>
          {plan.activity ? <>
            <p>GitHub activity imported {new Date(plan.activity.at * 1000).toLocaleDateString()}.</p>
            {plan.activity.partial && <p>GitHub activity is a bounded sample.</p>}
            <details><summary>{plan.activity.items.length} public pull requests and issues</summary>
              <ul>{plan.activity.items.map(item => <li key={item.url}>
                <a href={item.url} target="_blank" rel="noreferrer">{item.title}</a>
                <small>{item.kind} · {item.date?.slice(0, 10)}</small>
              </li>)}</ul>
            </details>
          </> : <p>Import your public GitHub pull requests and issues to include them in this plan.</p>}
          {session?.login ? <div className="inline-buttons">
            <button className="button compact" disabled={busy} onClick={() => void update('/github', 'POST')}>
              {plan.activity ? 'Refresh GitHub activity' : 'Import GitHub activity'}
            </button>
            {plan.activity && <button className="text-button" disabled={busy} onClick={() => void update('/github', 'DELETE')}>Remove imported activity</button>}
          </div> : session?.oauth ? <a className="button compact" href="/api/auth/github">Connect GitHub</a>
            : <p>GitHub sign-in is unavailable in this environment.</p>}
          {session?.login && <small>SkillForge saves public titles, links, and activity dates in your workspace.</small>}
        </section>
      </div>
      <h3 id="contribution-projects">Project briefs</h3>
      <p>Independent practice projects inspired by GSoC. Milestone checkmarks are self-reported.</p>
      {plan.projects.map(project => <details className="roadmap-project" id={'project-' + project.id} key={project.id}>
        <summary><strong>{project.title}</strong>
          <small>{project.difficulty} · {project.hours} hours · {project.completed.length}/{project.tasks.length} milestones</small>
        </summary>
        <p>{project.problem}</p>
        <p><strong>Deliverable</strong> {project.deliverable}</p>
        <p>{project.skills.join(' · ')} · About {Math.ceil(project.hours / plan.hours)} weeks at your pace</p>
        <button className="button compact" disabled={busy || plan.selected === project.id} onClick={() =>
          void update('', 'PUT', { project: project.id })}>{plan.selected === project.id ? 'Selected project' : 'Choose project'}</button>
        <ol>{project.tasks.map(task => <li key={task.id}>
          <label><input type="checkbox" disabled={busy} checked={project.completed.includes(task.id)} onChange={event =>
            void update('', 'PUT', { project: project.id, task: task.id, completed: event.target.checked })} />
            <span><strong>{task.title}</strong><small>{task.acceptance}</small></span>
          </label>
        </li>)}</ol>
      </details>)}
    </>}
  </section>
}
