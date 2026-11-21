
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
        {"id": 8, "title": "Sort stops by zone before dispatch",
         "body": "Group nearby deliveries to reduce repeated visits to the same zone.", "date": "2026-10-20"},
        {"id": 11, "title": "Add a test for empty routes",
         "body": "Dispatch returns an empty route when there are no orders.", "date": "2026-10-25"},
    ],
}
