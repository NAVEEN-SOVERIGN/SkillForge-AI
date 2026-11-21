
import { ArrowsOutSimple, ArrowUpRight, FunnelSimple, MagnifyingGlass, Minus, Plus, X } from '@phosphor-icons/react'
import cytoscape, { type Core } from 'cytoscape'
import { useEffect, useMemo, useRef, useState } from 'react'
import type { Edge, Node, Snapshot, Source } from './api'
import { api, errorText } from './api'

const colors: Record<string, string> = {
  file: '#226a59', folder: '#8d744b', function: '#4b58ad', package: '#a35b45', unresolved: '#777778',
}
const types = ['file', 'function', 'package', 'folder', 'unresolved']

export function CodeGraph({ snapshot, scanId }: { snapshot: Snapshot; scanId: string | null }) {
  const container = useRef<HTMLDivElement>(null)
  const graph = useRef<Core | null>(null)
  const [selected, setSelected] = useState<Node | null>(null)
  const [preview, setPreview] = useState<Source | null>(null)
  const [highlight, setHighlight] = useState<number | null>(null)
  const [draft, setDraft] = useState<string | null>(null)
  const [previewError, setPreviewError] = useState('')
  const [loading, setLoading] = useState(false)
  const [query, setQuery] = useState('')
  const [kind, setKind] = useState('all')
  const [mode, setMode] = useState('files')
  const [showList, setShowList] = useState(false)
  const previewSeq = useRef(0)

  useEffect(() => {
    if (!container.current) return
    const cy = cytoscape({
      container: container.current, elements: [], minZoom: 0.05, maxZoom: 2,
      wheelSensitivity: 0.2, autoungrabify: false,
      style: [
        { selector: 'node', style: {
          'background-color': 'data(color)', label: 'data(label)', color: '#252e29',
          'font-size': 11, 'font-family': 'system-ui', 'text-valign': 'bottom',
          'text-margin-y': 6, 'text-max-width': '145px', 'text-wrap': 'ellipsis',
          width: 20, height: 20, 'border-width': 1, 'border-color': '#ffffff',
        } },
        { selector: 'node[kind = "folder"]', style: { shape: 'round-rectangle', width: 27, height: 16 } },
        { selector: 'node[kind = "package"]', style: { shape: 'hexagon' } },
        { selector: 'node:selected', style: { 'border-width': 4, 'border-color': '#a7c85f', width: 26, height: 26 } },
        { selector: 'node.match', style: { 'border-width': 4, 'border-color': '#f7b259' } },
        { selector: 'node.dim', style: { opacity: 0.35 } },
        { selector: 'edge', style: {
          width: 1.3, 'curve-style': 'bezier', 'line-color': '#b4c0b6',
          'target-arrow-color': '#758f80', 'target-arrow-shape': 'triangle', 'arrow-scale': 0.85,
        } },
        { selector: 'edge[kind ^= "calls"]', style: {
          'line-color': '#7b84c6', 'target-arrow-color': '#5765b0', 'line-style': 'dashed',
        } },
      ],
    })
    cy.on('tap', 'node', event => {
      setSelected(event.target.data('payload') as Node)
      setDraft(null)
    })
    graph.current = cy
    return () => { graph.current = null; cy.destroy() }
  }, [])

  const allNodes = useMemo(() => new Map(snapshot.graph.nodes.map(node => [node.id, node])), [snapshot])
  const connections = selected
    ? snapshot.graph.edges.filter(edge => edge.target === selected.id || edge.source === selected.id)
    : []

  const visibleNodes = useMemo(() => {
    const specific = mode === 'all' || kind === 'function' || query.trim()
    let nodes = snapshot.graph.nodes.filter(node => specific || node.kind !== 'function')
    if (kind !== 'all') {
      const wanted = new Set(nodes.filter(node => node.kind === kind).map(node => node.id))
      for (const edge of snapshot.graph.edges) {
        if (allNodes.get(edge.source)?.kind === kind || allNodes.get(edge.target)?.kind === kind) {
          wanted.add(edge.source)
          wanted.add(edge.target)
        }
      }
      nodes = nodes.filter(node => wanted.has(node.id))
    }
    return nodes
  }, [snapshot, mode, kind, allNodes, query])

  useEffect(() => {
    const cy = graph.current
    if (!cy) return
    const visible = new Set(visibleNodes.map(node => node.id))
    cy.batch(() => {
      cy.elements().remove()
      cy.add(visibleNodes.map(node => ({
        data: { id: node.id, label: node.label, kind: node.kind, color: colors[node.kind], payload: node },
      })))
      cy.add(snapshot.graph.edges.filter(edge => visible.has(edge.source) && visible.has(edge.target)).map((edge, index) => ({
        data: { id: 'edge-' + index, source: edge.source, target: edge.target, kind: edge.kind },
      })))
    })
    if (cy.nodes().length) {
      cy.layout({ name: cy.nodes().length > 100 ? 'grid' : 'breadthfirst', directed: true, padding: 55, spacingFactor: 1.2 }).run()
      if (cy.zoom() > 1.15) cy.zoom(1.15)
      cy.center()
    }
  }, [snapshot, visibleNodes])

  useEffect(() => {
    const cy = graph.current
    if (!cy) return
    const needle = query.trim().toLowerCase()
    cy.nodes().forEach(node => {
      const item = node.data('payload') as Node
      const match = !!needle && (item.label + ' ' + (item.path ?? '')).toLowerCase().includes(needle)
      node.toggleClass('match', match)
      node.toggleClass('dim', !!needle && !match)
    })
  }, [query, visibleNodes])

  useEffect(() => {
    if (selected) graph.current?.getElementById(selected.id).select()
  }, [selected, visibleNodes])

  async function showSource(path: string, line: number | null) {
    const sequence = ++previewSeq.current
    setPreviewError('')
    setHighlight(line)
    setLoading(true)
    setDraft(null)
    setPreview(null)
    try {
      const next = await api<Source>((scanId ? '/scans/' + scanId : '/sample') + '/source?path=' + encodeURIComponent(path))
      if (previewSeq.current === sequence) setPreview(next)
    } catch (error) {
      if (previewSeq.current === sequence) setPreviewError(errorText(error))
    } finally {
      if (previewSeq.current === sequence) setLoading(false)
    }
  }

  function selectNode(node: Node) {
    setSelected(node)
    setShowList(false)
    if (node.path && snapshot.preview_paths.includes(node.path)) void showSource(node.path, node.line)
  }

  function zoom(scale: number) {
    const cy = graph.current
    if (cy) cy.zoom({ level: cy.zoom() * scale, renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 } })
  }

  const list = visibleNodes.filter(node => (node.label + ' ' + (node.path ?? '')).toLowerCase().includes(query.toLowerCase()))
  const link = (edge: Edge) => {
    const incoming = edge.target === selected?.id
    const target = allNodes.get(incoming ? edge.source : edge.target)
    return <div className="edge-row" key={[edge.source, edge.target, edge.kind].join('|')}>
      <button className="text-button" onClick={() => target && selectNode(target)}>{target?.label ?? 'Unknown'}</button>
      <span>{incoming ? '←' : '→'} {edge.kind}</span>
      {edge.line && snapshot.preview_paths.includes(edge.path) &&
        <button className="icon-button tiny" onClick={() => void showSource(edge.path, edge.line)}
          aria-label={'Open connection source line ' + edge.line}><ArrowUpRight size={14} /></button>}
    </div>
  }

  return <section className="graph-card" aria-label="Interactive code structure">
    <div className="graph-toolbar">
      <label className="search-field"><MagnifyingGlass size={16} /><input value={query} onChange={event => {
        setQuery(event.target.value)
        if (event.target.value) setShowList(true)
      }} placeholder="Find a file or function" aria-label="Find a file or function" /></label>
      <label className="select-field"><FunnelSimple size={16} /><select aria-label="Filter graph node type" value={kind}
        onChange={event => setKind(event.target.value)}><option value="all">All types</option>
        {types.map(type => <option key={type} value={type}>{type.charAt(0).toUpperCase() + type.slice(1)}</option>)}</select></label>
      <button className="button compact" onClick={() => setMode(mode === 'files' ? 'all' : 'files')} aria-pressed={mode === 'all'}>
        {mode === 'all' ? 'Hide functions' : 'Show functions'}
      </button>
      <button className="button compact graph-list-button" onClick={() => setShowList(!showList)} aria-expanded={showList}>
        {showList ? 'Hide list' : 'Node list'}
      </button>
    </div>
    <div className={'graph-grid' + (selected ? ' selected' : '')}>
      <div className="map">
        <div className="canvas" aria-hidden="true" ref={container} />
        {!visibleNodes.length && <p className="canvas-empty">No graph nodes available for this selection.</p>}
        {showList && <div className="node-list" aria-label="Graph nodes">
          {list.length ? list.map(node => <button key={node.id} onClick={() => selectNode(node)}>
            <span className="color-dot" style={{ background: colors[node.kind] }} />{node.label}<small>{node.path ?? node.kind}</small>
          </button>) : <p>No matching nodes.</p>}
        </div>}
        <div className="zoom-controls">
          <button className="icon-button" aria-label="Zoom in" onClick={() => zoom(1.3)}><Plus size={17} /></button>
          <button className="icon-button" aria-label="Zoom out" onClick={() => zoom(0.77)}><Minus size={17} /></button>
          <button className="icon-button" aria-label="Fit graph" onClick={() => graph.current?.fit(undefined, 55)}><ArrowsOutSimple size={17} /></button>
        </div>
      </div>
      {selected && <aside className="node-inspector" aria-label="Graph node details">
        <div className="split"><span className="eyebrow">{selected.kind}</span>
          <button className="icon-button" aria-label="Close node details" onClick={() => { setSelected(null); graph.current?.nodes().unselect() }}><X size={16} /></button>
        </div>
        <h3>{selected.label}</h3>
        <p className="mono word-wrap">{selected.path}</p>
        {selected.path && snapshot.preview_paths.includes(selected.path) && <button className="button compact"
          onClick={() => void showSource(selected.path!, selected.line)}>Open source</button>}
        <h4>Connections</h4>
        {connections.length ? connections.map(link) : <p>No indexed connections.</p>}
      </aside>}
    </div>
    <div className="legend">{types.map(type => <span key={type}><i style={{ background: colors[type] }} />{type}</span>)}
      <span>{snapshot.graph.unresolved} unresolved{snapshot.graph.limited ? ' · node limit reached' : ''}</span>
    </div>
    {(preview || loading || previewError) && <section className="preview">
      <div className="split"><div><h3>{preview?.path ?? 'Source preview'}</h3>
        {preview?.url && <a href={preview.url} target="_blank" rel="noreferrer">Open pinned file on GitHub <ArrowUpRight size={14} /></a>}</div>
        <div className="inline-buttons">{preview && <button className="button compact" onClick={() => setDraft(draft === null ? preview.source : null)}>
          {draft === null ? 'Open scratch draft' : 'Discard draft'}</button>}
          <button className="icon-button" aria-label="Close preview" onClick={() => {
            previewSeq.current++; setPreview(null); setLoading(false); setDraft(null); setPreviewError('')
          }}><X size={16} /></button></div>
      </div>
      {loading && <p>Fetching pinned source…</p>}{previewError && <p role="alert">{previewError}</p>}
      {draft !== null ? <label className="draft-field">Local scratch draft<textarea value={draft}
        aria-label="Local scratch draft" onChange={event => setDraft(event.target.value)} spellCheck={false} /></label>
        : preview && <pre>{preview.source.split('\n').map((line, index) => <span key={index} className={highlight === index + 1 ? 'highlight-line' : ''}>
          <i>{index + 1}</i>{line || ' '}
        </span>)}</pre>}
    </section>}
  </section>
}
