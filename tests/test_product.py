
import os
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

TEMP = tempfile.TemporaryDirectory()
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(TEMP.name) / "suite.db")
os.environ["APP_ENV"] = "test"
os.environ["SCAN_WORKER_ENABLED"] = "false"
os.environ["JUDGE_URL"] = ""
os.environ["JUDGE_TOKEN"] = ""

from skillforge import config
from skillforge.db import engine
from skillforge.judge import matches
from skillforge.main import app
from skillforge.sample import SNAPSHOT
from skillforge.scanning import compile_snapshot

ORIGIN = {"Origin": config.ORIGIN}


def tearDownModule():
    engine.dispose()
    TEMP.cleanup()


class GraphAndScoreTests(unittest.TestCase):
    def test_static_sample_has_function_and_package_edges(self):
        payload = compile_snapshot(SNAPSHOT)
        edges = {(row["source"], row["target"], row["kind"]) for row in payload["graph"]["edges"]}
        self.assertIn(("src/dispatch.ts", "package:zustand", "imports package"), edges)
        self.assertIn(("src/dispatch.ts::dispatch", "src/planner.ts::rankStops", "calls · inferred"), edges)
        self.assertTrue(payload["quality"]["rankable"])
        self.assertEqual(payload["quality"], compile_snapshot(SNAPSHOT)["quality"])

    def test_alias_edges_are_pinned_to_the_import_and_call_sites(self):
        sources = {"src/app.ts": "import { greet as hello } from '@/greet';\nexport function run(){hello();}\n",
                   "src/greet.ts": "export function greet() { return 'hi' }\n"}
        snapshot = {**SNAPSHOT, "sources": sources, "paths": set(sources), "eligible": 2,
                    "aliases": {"tsconfig.json": {"base": ".", "paths": {"@/*": ["src/*"]}}}}
        payload = compile_snapshot(snapshot)
        edges = {(row["kind"], row["source"], row["target"], row["line"]) for row in payload["graph"]["edges"]}
        self.assertIn(("imports file", "src/app.ts", "src/greet.ts", 1), edges)
        self.assertIn(("calls · inferred", "src/app.ts::run", "src/greet.ts::greet", 2), edges)
        self.assertFalse(compile_snapshot({**snapshot, "eligible": 20})["quality"]["rankable"])

    def test_boolean_answers_cannot_be_replaced_with_integers(self):
        self.assertTrue(matches([True, 4.0], [True, 4]))
        self.assertFalse(matches([1, 4], [True, 4]))


class WorkspaceTests(unittest.TestCase):
    def test_queue_is_origin_and_owner_scoped(self):
        with TestClient(app) as owner, TestClient(app) as other:
            owner.get("/api/session").raise_for_status()
            other.get("/api/session").raise_for_status()
            self.assertEqual(owner.post("/api/scans", json={"repository": "owner/repo"}).status_code, 403)
            self.assertEqual(owner.post("/api/scans", json={"repository": "https://example.org/a/b"},
                                        headers=ORIGIN).status_code, 422)
            payload = {"repository": "github.com/owner/repo"}
            job = owner.post("/api/scans", json=payload, headers=ORIGIN)
            self.assertEqual(job.status_code, 202)
            key = job.json()["id"]
            self.assertEqual(owner.post("/api/scans", json=payload, headers=ORIGIN).json()["id"], key)
            self.assertEqual(other.get("/api/scans/" + key).status_code, 404)
            self.assertEqual(other.get("/api/scans").json(), [])
            owner.delete("/api/account", headers=ORIGIN).raise_for_status()
            self.assertEqual(owner.get("/api/scans/" + key).status_code, 404)

    def test_public_catalog_does_not_disclose_hidden_cases(self):
        with TestClient(app) as client:
            catalog = client.get("/api/practice/problems").json()
            self.assertEqual(len(catalog), 12)
            self.assertTrue(all("hidden" not in item and "walkthrough" not in item for item in catalog))
            client.get("/api/session").raise_for_status()
            denied = client.post("/api/practice/submit", headers=ORIGIN, json={
                "problem": "warehouse-reconciliation", "language": "python", "code": "print('{}')",
            })
            self.assertEqual(denied.status_code, 503)
            self.assertEqual(client.get("/api/practice/attempts").json(), [])

    def test_actions_require_explicit_approval_and_export(self):
        with TestClient(app) as client:
            client.get("/api/session").raise_for_status()
            client.put("/api/career/target", headers=ORIGIN, json={
                "role": "Frontend developer", "hours": 7, "description": "We prefer Python and testing.",
            }).raise_for_status()
            proposed = client.post("/api/career/actions", headers=ORIGIN, json={"skill": "Python"}).json()
            key = proposed["profile"]["actions"][0]["id"]
            route = "/api/career/actions/" + key
            self.assertEqual(client.patch(route, headers=ORIGIN, json={"state": "completed"}).status_code, 409)
            client.patch(route, headers=ORIGIN, json={"state": "approved"}).raise_for_status()
            completed = client.patch(route, headers=ORIGIN, json={"state": "completed"}).json()
            self.assertIn("Python", completed["planned"])
            self.assertTrue(client.get("/api/career/report.pdf").content.startswith(b"%PDF-1.4"))
