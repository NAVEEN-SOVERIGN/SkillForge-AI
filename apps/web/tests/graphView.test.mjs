
import assert from 'node:assert/strict'
import test from 'node:test'
import { folderOverview, neighborhood, PAGE_SIZE, parentScope, ROOT_FILES, searchNodes } from '../src/graphView.ts'

const file = (path) => ({ id: path, label: path.split('/').at(-1), path, kind: 'file', line: 1 })
const imports = (source, target) => ({ source, target, kind: 'imports file', path: source, line: 1 })

test('large repositories open by folder and page file-level views', () => {
  const nodes = [
    file('index.ts'),
    ...Array.from({ length: 80 }, (_, index) => file('app/module-' + index + '.ts')),
    ...Array.from({ length: 65 }, (_, index) => file('tests/test-' + index + '.ts')),
  ]
  const edges = nodes.slice(1, 81).map((node, index) => imports(node.id, 'tests/test-' + index % 65 + '.ts'))
  const root = folderOverview(nodes, edges, '', 0, 'all')
  assert.deepEqual(root.nodes.map(node => node.id).sort(), [ROOT_FILES, 'app/', 'tests/'])
  assert.deepEqual(root.edges, [{ source: 'app/', target: 'tests/', kind: 'imports', count: 80 }])
  assert.equal(root.nodes.find(node => node.id === 'app/').count, 80)
  const expanded = folderOverview(nodes, edges, 'app/', 0, 'all')
  const next = folderOverview(nodes, edges, 'app/', 1, 'all')
  assert.equal(expanded.nodes.length, PAGE_SIZE)
  assert.equal(expanded.total, 80)
  assert.equal(new Set([...expanded.nodes, ...next.nodes].map(node => node.id)).size, 2 * PAGE_SIZE)
  assert.equal(parentScope('app/components/'), 'app/')
  assert.equal(parentScope(ROOT_FILES), '')
  assert.equal(searchNodes(nodes, 'test-52.ts', 'file')[0].id, 'tests/test-52.ts')
})

test('focus draws a bounded neighborhood and preserves all inspectable connections', () => {
  const selected = file('service.ts')
  const nodes = [selected, ...Array.from({ length: 25 }, (_, index) => file('caller-' + index + '.ts'))]
  const edges = nodes.slice(1).flatMap(node => [
    imports(node.id, selected.id),
    { ...imports(node.id, selected.id), kind: 'calls across files · inferred', line: 4 },
  ])
  const all = new Map(nodes.map(node => [node.id, node]))
  const result = neighborhood(selected, edges, all, 'all')
  assert.equal(result.nodes.length, 5)
  assert.equal(result.edges.length, 4)
  assert.equal(result.relevant.length, 50)
  assert.equal(result.hidden, 21)
  assert.equal(neighborhood(selected, edges, all, 'calls').relevant.length, 25)
})
