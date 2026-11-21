
import { ArrowRight, CheckCircle, Code, FloppyDisk, Play, XCircle } from '@phosphor-icons/react'
import { useEffect, useState } from 'react'
import { api, errorText } from './api'

type Language = 'python' | 'javascript'
type Problem = {
  id: string; title: string; difficulty: string; story: string; contract: string
  examples: { input: unknown; output: unknown }[]; version: string; languages: Language[]
}
type Result = {
  passed: number; total: number; language: Language; examples_only: boolean; topic?: string; walkthrough?: string
  cases: { category: string; status: string; duration: number }[]
  assessment?: { points: number; measured: number; max: number; normalized: number
    criteria: { id: string; name: string; points: number | null; max: number }[] }
}
type Recommendation = { next: { problem: string; difficulty: string } | null }
type Attempt = Result & { id: string; problem: string; created: number }
const starters: Record<Language, string> = {
  python: 'import json\nimport sys\n\n\ndef solve(data):\n    # Return the result for this exercise.\n    pass\n\n\nprint(json.dumps(solve(json.load(sys.stdin))))\n',
  javascript: "const fs = require('node:fs');\n\nfunction solve(data) {\n  // Return the result for this exercise.\n}\n\nconst input = JSON.parse(fs.readFileSync(0, 'utf8'));\nconsole.log(JSON.stringify(solve(input)));\n",
}
const feedback: Record<string, string> = {
  passed: 'Passed', wrong_answer: 'Wrong answer', invalid_output: 'Expected JSON output',
  runtime_error: 'Runtime error', time_limit: 'Time limit', output_limit: 'Output limit',
}

export function Practice({ enabled, initialProblem }: { enabled: boolean; initialProblem: string | null }) {
  const [catalog, setCatalog] = useState<Problem[]>([])
  const [attempts, setAttempts] = useState<Attempt[]>([])
  const [selected, setSelected] = useState(initialProblem)
  const [language, setLanguage] = useState<Language>('python')
  const [drafts, setDrafts] = useState<Record<string, string>>({})
  const [result, setResult] = useState<Result | null>(null)
  const [problemHistory, setProblemHistory] = useState<Result | null>(null)
  const [busy, setBusy] = useState<'example' | 'submission' | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [recommendation, setRecommendation] = useState<Recommendation['next']>(null)

  useEffect(() => {
    let alive = true
    void api<Problem[]>('/practice/problems').then(items => {
      if (alive) {
        setCatalog(items)
        setSelected(current => current ?? items[0]?.id ?? null)
      }
    }).catch(error => { if (alive) setError(errorText(error)) }).finally(() => { if (alive) setLoading(false) })
    void api<Attempt[]>('/practice/attempts').then(items => { if (alive) setAttempts(items) })
      .catch(error => { if (alive) setError(errorText(error)) })
    void api<Recommendation>('/practice/recommendation').then(data => { if (alive) setRecommendation(data.next) })
      .catch(() => undefined)
    return () => { alive = false }
  }, [])

  const problem = catalog.find(item => item.id === selected)
  const draftKey = selected + ':' + language
  const code = drafts[draftKey] ?? starters[language]
  const currentAttempts = attempts.filter(item => item.problem === selected)

  async function run(examplesOnly: boolean) {
    if (!problem || !code.trim() || busy) return
    setBusy(examplesOnly ? 'example' : 'submission')
    setError('')
    setResult(null)
    setProblemHistory(null)
    try {
      const next = await api<Result>('/practice/submit', 'POST', {
        problem: problem.id, language, code, examples_only: examplesOnly,
      })
      setResult(next)
      if (!examplesOnly) {
        const [history, nextProblem] = await Promise.all([
          api<Attempt[]>('/practice/attempts'), api<Recommendation>('/practice/recommendation'),
        ])
        setAttempts(history)
        setRecommendation(nextProblem.next)
      }
    } catch (error) { setError(errorText(error)) }
    finally { setBusy(null) }
  }

  function select(id: string) {
    setSelected(id); setResult(null); setError(''); setProblemHistory(null)
  }

  const output = problemHistory ?? result
  return <section className="ranking-page practice">
    <p className="eyebrow"><span className="accent-square" /> Applied practice</p>
    <h1>Coding tests<span>.</span></h1>
    <p>Work through everyday engineering problems using data structures and algorithms.</p>
    {error && <p className="notice" role="alert">{error}</p>}
    {loading && <div className="status-panel" role="status">Loading exercises…</div>}
    {!loading && <div className="practice-grid">
      <aside className="library practice-library"><h2>Exercise catalog</h2>
        {recommendation && recommendation.problem !== selected && <button className="button compact" disabled={!!busy}
          onClick={() => select(recommendation.problem)}>Recommended next · {recommendation.difficulty}</button>}
        {catalog.map(item => <button disabled={!!busy} key={item.id} className={'library-item' + (selected === item.id ? ' active' : '')}
          onClick={() => select(item.id)}><Code size={17} /><span><strong>{item.title}</strong><small>{item.difficulty}</small></span></button>)}
      </aside>
      {problem && <div className="practice-detail">
        <section className="panel challenge">
          <p className="eyebrow">{problem.difficulty} · v{problem.version}</p><h2>{problem.title}</h2>
          <p>{problem.story}</p>
          <h3>Input and output</h3><p>{problem.contract}</p>
          <p className="subtle">Read one JSON value from standard input. Print one JSON value to standard output.</p>
          {problem.examples.map((item, index) => <div className="example-grid" key={index}>
            <div><h4>Example input</h4><pre>{JSON.stringify(item.input, null, 2)}</pre></div>
            <div><h4>Expected output</h4><pre>{JSON.stringify(item.output, null, 2)}</pre></div>
          </div>)}
        </section>
        <section className="panel challenge">
          <div className="split"><h3>Solution editor</h3><label className="select-field">Language
            <select value={language} disabled={!!busy} onChange={event => { setLanguage(event.target.value as Language); setResult(null); setProblemHistory(null) }}>
              {problem.languages.map(item => <option value={item} key={item}>{item === 'python' ? 'Python' : 'JavaScript'}</option>)}
            </select></label></div>
          <textarea className="solution" value={code} spellCheck={false} autoCapitalize="off" autoCorrect="off" aria-label="Solution source code"
            maxLength={24000} onChange={event => setDrafts(current => ({ ...current, [draftKey]: event.target.value }))} />
          <div className="inline-buttons">
            <button className="button" onClick={() => void run(true)} disabled={!enabled || !!busy || !code.trim()}><Play size={16} /> Run examples</button>
            <button className="button primary" onClick={() => void run(false)} disabled={!enabled || !!busy || !code.trim()}><ArrowRight size={16} /> Submit solution</button>
            <button className="text-button" disabled={!!busy} onClick={() => setDrafts(current => ({ ...current, [draftKey]: starters[language] }))}>Reset starter</button>
          </div>
          {busy && <p className="subtle" role="status">Evaluating {busy === 'example' ? 'examples' : 'your submission'}…</p>}
          {!enabled && <p className="subtle" role="status">The exercise catalog is available. Code execution requires a connected isolated evaluator.</p>}
        </section>
        {output && <section className="panel challenge results" aria-live="polite">
          <div className="split"><h3>{output.examples_only ? 'Example run' : 'Submission result'}</h3>
            <strong>{output.passed}/{output.total} passed</strong></div>
          {output.cases.map((item, index) => <div className="case-row" key={index}>
            {item.status === 'passed' ? <CheckCircle size={18} /> : <XCircle size={18} />}
            <strong>{item.category}</strong><span>{feedback[item.status] ?? 'Unable to evaluate'}</span></div>)}
          {output.assessment && <>
            <h4>Points breakdown</h4>
            <p>{output.assessment.points}/{output.assessment.measured} measured points · {output.assessment.max - output.assessment.measured} unmeasured</p>
            {output.assessment.criteria.map(item => <div className="split action-row" key={item.id}>
              <span>{item.name}</span><strong>{item.points == null ? 'Unmeasured' : item.points + '/' + item.max}</strong>
            </div>)}
            <p className="subtle">The efficiency points measure a large test within the time budget. Explanation needs qualitative review.</p>
          </>}
          {output.topic && <><h4>{output.topic}</h4><p>{output.walkthrough}</p></>}
        </section>}
        {!!currentAttempts.length && <section className="panel rankings"><h2>Submission history</h2>
          {currentAttempts.map(item => <button key={item.id} onClick={() => setProblemHistory(item)}>
            <FloppyDisk size={15} /><strong>{new Date(item.created * 1000).toLocaleString()}</strong>
            <span>{item.language}</span><strong>{item.passed}/{item.total} passed</strong><ArrowRight size={15} /></button>)}</section>}
      </div>}
    </div>}
  </section>
}
