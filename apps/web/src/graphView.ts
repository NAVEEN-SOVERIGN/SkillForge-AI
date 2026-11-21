
import type { Edge, Node } from './api'

export const PAGE_SIZE = 12
export const NEIGHBORS_PER_SIDE = 4
export const ROOT_FILES = '@root-files'
const PACKAGES = '@packages'
const UNRESOLVED = '@unresolved'

export type OverviewNode = Node & { count?: number }
export type AggregateEdge = { source: string; target: string; kind: 'imports' | 'calls'; count: number }

function area(id: string, label: string, kind: string): OverviewNode {
  return { id, label, kind, path: null, line: null }
}

export function folderOverview(nodes: Node[], edges: Edge[], scope: string, page: number, filter: string) {
  const entries = new Map<string, OverviewNode>()
  const buckets = new Map<string, string>()
  const paths = new Map(nodes.filter(node => node.kind === 'file').map(node => [node.path, node]))
  function group(node: Node): string | undefined {
    if (!node.path) {
      if (scope) return
      if (node.kind === 'package') return PACKAGES
      if (node.kind === 'unresolved') return UNRESOLVED
      return
    }
    if (scope === ROOT_FILES) return node.path.includes('/') ? undefined : node.path
    if (scope && !node.path.startsWith(scope)) return
    const relative = node.path.slice(scope.length)
    const slash = relative.indexOf('/')
    if (slash >= 0) return scope + relative.slice(0, slash + 1)
    return scope ? node.path : ROOT_FILES
  }
  for (const node of nodes) {
    const id = group(node)
    if (!id) continue
    buckets.set(node.id, id)
    if (!entries.has(id)) {
      if (id === ROOT_FILES) entries.set(id, area(id, 'Root files', 'folder'))
      else if (id === PACKAGES) entries.set(id, area(id, 'External packages', 'package'))
      else if (id === UNRESOLVED) entries.set(id, area(id, 'Unresolved imports', 'unresolved'))
      else if (id.endsWith('/')) entries.set(id, area(id, id.slice(0, -1).split('/').at(-1)!, 'folder'))
      else if (paths.has(id)) entries.set(id, paths.get(id)!)
      else entries.set(id, area(id, id.split('/').at(-1)!, 'file'))
    }
    if ((node.kind === 'file' && id !== node.id) || id === PACKAGES || id === UNRESOLVED) {
      const entry = entries.get(id)!
      entries.set(id, { ...entry, count: (entry.count ?? 0) + 1 })
    }
  }
  const ordered = [...entries.values()].sort((a, b) =>
    Number(b.kind === 'folder') - Number(a.kind === 'folder') || a.label.localeCompare(b.label))
  const shown = ordered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)
  const ids = new Set(shown.map(node => node.id))
  const counts = new Map<string, AggregateEdge>()
  for (const edge of edges) {
    const kind = edge.kind.startsWith('imports') ? 'imports' : edge.kind.startsWith('calls across files') ? 'calls' : null
    if (!kind || (filter !== 'all' && kind !== filter)) continue
    const source = buckets.get(edge.source), target = buckets.get(edge.target)
    if (!source || !target || source === target || !ids.has(source) || !ids.has(target)) continue
    const key = JSON.stringify([source, target, kind])
    counts.set(key, { source, target, kind, count: (counts.get(key)?.count ?? 0) + 1 })
  }
  const links = [...counts.values()].sort((a, b) => b.count - a.count)
  return { nodes: shown, edges: links.slice(0, PAGE_SIZE), total: ordered.length, hidden: Math.max(0, links.length - PAGE_SIZE) }
}

export function neighborhood(node: Node, edges: Edge[], allNodes: Map<string, Node>, filter: string) {
  const relevant = edges.filter(edge => (edge.target === node.id || edge.source === node.id) &&
    (filter === 'all' || edge.kind.startsWith(filter)))
  const incoming: string[] = [], outgoing: string[] = []
  for (const edge of relevant) {
    const enters = edge.target === node.id
    const other = enters ? edge.source : edge.target
    const group = enters ? incoming : outgoing
    if (other !== node.id && allNodes.has(other) && !group.includes(other)) group.push(other)
  }
  const shownIn = incoming.slice(0, NEIGHBORS_PER_SIDE)
  const shownOut = outgoing.filter(id => !shownIn.includes(id)).slice(0, NEIGHBORS_PER_SIDE)
  const ids = new Set([node.id, ...shownIn, ...shownOut])
  const visible = new Set<string>()
  const shownEdges = relevant.filter(edge => {
    if (!ids.has(edge.source) || !ids.has(edge.target) || edge.source === edge.target) return false
    const key = JSON.stringify([edge.source, edge.target])
    if (visible.has(key)) return false
    visible.add(key)
    return true
  })
  return { incoming: shownIn, outgoing: shownOut, relevant, edges: shownEdges,
    nodes: [...ids].flatMap(id => allNodes.get(id) ?? []),
    hidden: new Set([...incoming, ...outgoing]).size - ids.size + 1 }
}

export function parentScope(scope: string) {
  return scope === ROOT_FILES ? '' : scope.slice(0, -1).split('/').slice(0, -1).map(part => part + '/').join('')
}

export function searchNodes(nodes: Node[], query: string, kind: string) {
  const needle = query.toLowerCase().trim()
  const matches = nodes.filter(node => (kind === 'all' || node.kind === kind) &&
    (node.label + ' ' + (node.path ?? '') + ' ' + node.id).toLowerCase().includes(needle))
  return matches.sort((a, b) => Number(b.label.toLowerCase() === needle) - Number(a.label.toLowerCase() === needle) ||
    a.label.localeCompare(b.label))
}
