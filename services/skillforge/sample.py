
SOURCES = {
    "src/dispatch.ts": """import { rankStops } from './planner'
import { estimateArrival } from './eta'
import { createStore } from 'zustand'

export function dispatch(stops: Stop[]) {
  return rankStops(stops).map(estimateArrival)
}
""",
    "src/planner.ts": """import { normalizeZone } from './zones'

export function rankStops(stops: Stop[]) {
  return [...stops].sort((a, b) => normalizeZone(a.zone) - normalizeZone(b.zone))
}
""",
    "src/eta.ts": """import { addMinutes } from 'date-fns'

export function estimateArrival(stop: Stop) {
  // FIXME account for seasonal delays
  return addMinutes(new Date(), stop.minutes)
}
""",
    "src/zones.ts": """export function normalizeZone(zone: string) {
  return Number(zone.replace('Z', ''))
}
""",
    "tests/dispatch.test.ts": """import { dispatch } from '../src/dispatch'
import { expect, test } from 'vitest'

test('returns no stops for an empty route', () => {
  expect(dispatch([])).toEqual([])
})
""",
}
PATHS = set(SOURCES) | {"README.md", "package.json", "package-lock.json"}
SNAPSHOT = {
    "repo": "sample/delivery-routing", "branch": "main", "revision": "sample", "sources": SOURCES,
    "paths": PATHS, "description": "Illustrative delivery route planning service.", "language": "TypeScript",
    "eligible": len(SOURCES), "total_files": len(PATHS), "truncated": False, "history_available": True,
    "history": [
        {"id": "pr-14", "kind": "pr", "label": "PR #14", "title": "Sort routes by zone before dispatch",
         "body": "We sort routes by zone to reduce repeated visits when drivers cross zone boundaries. Supersedes #8.",
         "date": "2026-10-27", "merged": "2026-10-27", "actor": "sample-maintainer",
         "paths": ["src/planner.ts"]},
        {"id": "comment-4", "kind": "comment", "label": "PR #14 discussion", "title": "Dispatcher feedback",
         "body": "During the pilot, drivers crossed the same zone boundary several times per route.",
         "date": "2026-10-26", "actor": "sample-dispatcher", "parent": "pr-14"},
        {"id": "pr-11", "kind": "pr", "label": "PR #11", "title": "Add a test for empty routes",
         "body": "Dispatch returns an empty route when there are no orders.", "date": "2026-10-25",
         "paths": ["tests/dispatch.test.ts"]},
        {"id": "pr-8", "kind": "pr", "label": "PR #8", "title": "Sort routes by estimated arrival",
         "body": "We sort routes by arrival time to reduce late deliveries.", "date": "2026-10-20",
         "merged": "2026-10-20", "actor": "sample-maintainer", "paths": ["src/planner.ts"]},
    ],
}
