"""Retrieve cited decision paths from the authorized scan's bounded public history."""

import os
import re
from itertools import pairwise
from urllib.parse import quote, urlsplit

import httpx

TERMS = re.compile(r"[a-z0-9_]{3,}", re.IGNORECASE)
STOP = {"the", "and", "for", "are", "was", "were", "has", "have", "why", "how", "what", "when", "did", "does", "this", "that", "with", "from", "about", "code", "file"}
REASON = re.compile(r"\b(?:because|so that|in order to|to (?:avoid|prevent|reduce|ensure|support|fix))\b", re.IGNORECASE)
REVERT = re.compile(r"(?im)^this reverts commit ([a-f0-9]{40})\b|\b(?:reverts?|supersedes|replaces)\s+#(\d+)\b")
REFERENCE = re.compile(r"(?<![\w/])#(\d+)\b")
SETTING = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")
SETTING_CHANGE = re.compile(
    r"\b(?i:set|change|raise|lower|increase|decrease) `?(" + SETTING.pattern
    + r")`? (?:(?i:from) [\w.-]+ )?(?i:to) `?([+-]?[0-9]+(?:\.[0-9]+)?|true|false)\b"
)

PROJECT = """
CREATE (scope:SkillForgeQuestion)
WITH scope
UNWIND $records AS row
CREATE (scope)-[:CONTAINS]->(r:SkillForgeRecord {id: row.id, date: row.date})
FOREACH (actor IN row.actors |
  MERGE (scope)-[:HAS_PERSON]->(p:SkillForgePerson {login: actor})
  CREATE (r)-[:AUTHORED_BY]->(p))
FOREACH (entity IN row.entities |
  MERGE (scope)-[:HAS_ENTITY]->(e:SkillForgeEntity {name: entity})
  CREATE (e)-[:HAS_EVIDENCE]->(r))
WITH DISTINCT scope
CALL (scope) {
  UNWIND $links AS link
  MATCH (scope)-[:CONTAINS]->(a {id: link.source}), (scope)-[:CONTAINS]->(b {id: link.target})
  FOREACH (_ IN CASE WHEN link.kind = 'supersedes' THEN [1] ELSE [] END | CREATE (a)-[:SUPERSEDES {basis: link.basis}]->(b))
  FOREACH (_ IN CASE WHEN link.kind = 'related' THEN [1] ELSE [] END | CREATE (a)-[:REFERENCES]->(b))
  RETURN count(*) AS links
}
MATCH (scope)-[:CONTAINS]->(r)
WHERE r.id IN $seeds OR EXISTS { MATCH (scope)-[:HAS_ENTITY]->(e)-[:HAS_EVIDENCE]->(r)
                                WHERE e.name IN $entities }
OPTIONAL MATCH (r)-[:REFERENCES]-(discussion)
WITH scope, collect(DISTINCT r) + collect(DISTINCT discussion) AS candidates
UNWIND candidates AS r
OPTIONAL MATCH (r)<-[override:SUPERSEDES]-(later)
OPTIONAL MATCH (r)-[:AUTHORED_BY]->(person)
OPTIONAL MATCH (r)<-[:HAS_EVIDENCE]-(entity)
OPTIONAL MATCH (r)-[:REFERENCES]-(discussion)
RETURN r.id, collect(DISTINCT CASE WHEN later IS NOT NULL THEN [later.id, override.basis] END), collect(DISTINCT person.login), collect(DISTINCT entity.name), collect(DISTINCT discussion.id)
"""


def words(text):
    return set(TERMS.findall(text.lower())) - STOP


def contains(text, name):
    return bool(re.search(r"(?<![\w./-])" + re.escape(name) + r"(?![\w./-])", text, re.IGNORECASE))


def project(snapshot, question, path, through):
    records = {str(row["id"]): row for row in snapshot["history"]
               if not through or (row["date"] and row["date"][:10] <= through)}
    nodes = snapshot["graph"]["nodes"]
    entities = {path} if path else set(SETTING.findall(question))
    for node in nodes:
        name = node["label"]
        if (node["kind"] in {"file", "function"} and len(name) >= 4
                and (not path or node["path"] == path) and contains(question, name)):
            entities.add(node["path"])
            if node["kind"] == "function":
                entities.add(name)
    entities.discard(None)
    by_number = {id.split("-", 1)[1]: id for id in records if id.startswith(("issue-", "pr-"))}
    aliases = set(entities)
    rename_pairs = [pair for row in records.values() for pair in row.get("renames", [])]
    for _ in rename_pairs:
        expanded = aliases | {name for pair in rename_pairs if aliases.intersection(pair) for name in pair}
        if expanded == aliases:
            break
        aliases = expanded
    query = words(question)
    projections, links, seeds = [], [], []
    settings = {}
    referenced = {by_number.get(number) for number in REFERENCE.findall(question)}
    for id, row in records.items():
        body = row["title"] + "\n" + row["body"]
        direct = set(row.get("paths", ())) | {name for name in aliases if contains(body, name)}
        if (not path and len(query & words(body)) >= 2) or id in referenced:
            seeds.append(id)
        projections.append({"id": id, "date": row["date"] or "", "entities": sorted(direct),
                            "actors": [row["actor"]] if row.get("actor") else []})
        related = {by_number.get(n) for n in REFERENCE.findall(body)} | {row.get("parent")}
        if row.get("merge_sha"):
            related.add("commit-" + row["merge_sha"])
        for target in sorted((related & records.keys()) - {id}):
            links.append({"source": id, "target": target, "kind": "related"})
        if row.get("kind") not in {"commit", "pr"} or (row["kind"] == "pr" and not row.get("merged")):
            continue
        for sha, number in REVERT.findall(body):
            target = "commit-" + sha if sha else by_number.get(number)
            if target in records and (row["date"] or "") > (records[target]["date"] or ""):
                links.append({"source": id, "target": target, "kind": "supersedes",
                              "basis": "Explicit revert or supersession reference"})
        for name, value in SETTING_CHANGE.findall(row["title"]):
            settings.setdefault(name, []).append((row["date"] or "", id, value))
    explicit = {(link["source"], link["target"]) for link in links if link["kind"] == "supersedes"}
    for name, changes in settings.items():
        for (earlier, target, old), (later, source, new) in pairwise(sorted(changes)):
            old_paths = set(records[target].get("paths", ()))
            new_paths = set(records[source].get("paths", ()))
            if old_paths and new_paths and old_paths.isdisjoint(new_paths):
                continue
            if earlier and later > earlier and new != old and (source, target) not in explicit:
                links.append({"source": source, "target": target, "kind": "supersedes",
                              "basis": f"Later recorded change to {name} from {old} to {new}"})
    return records, {"records": projections, "links": links, "entities": sorted(aliases), "seeds": seeds}


def local_paths(params):
    direct = {row["id"] for row in params["records"]
              if set(row["entities"]).intersection(params["entities"])} | set(params["seeds"])
    candidates = set(direct)
    for link in params["links"]:
        if link["kind"] == "related" and direct.intersection((link["source"], link["target"])):
            candidates.update((link["source"], link["target"]))
    return [[row["id"], [[link["source"], link["basis"]] for link in params["links"]
                         if link["kind"] == "supersedes" and link["target"] == row["id"]],
             row["actors"], row["entities"],
             [link["target"] if link["source"] == row["id"] else link["source"] for link in params["links"]
              if link["kind"] == "related" and row["id"] in (link["source"], link["target"])]]
            for row in params["records"] if row["id"] in candidates]


def neo4j_endpoint():
    configured = os.getenv("NEO4J_QUERY_URL") or os.getenv("NEO4J_URI", "").replace("neo4j+s://", "https://", 1)
    url = urlsplit(configured)
    if url.scheme != "https" or not url.hostname or url.username or url.password or url.query or url.fragment:
        raise ValueError("Invalid Neo4j URL")
    database = quote(os.getenv("NEO4J_DATABASE", "neo4j"), safe="")
    return f"https://{url.netloc}/db/{database}/query/v2/tx"


async def neo4j_paths(params):
    endpoint = neo4j_endpoint()
    auth = (os.getenv("NEO4J_USERNAME") or "neo4j", os.environ["NEO4J_PASSWORD"])
    async with httpx.AsyncClient(auth=auth, timeout=5) as http:
        response = await http.post(endpoint, json={"statement": PROJECT, "parameters": params})
        response.raise_for_status()
        payload = response.json()
        transaction = payload.get("transaction", {}).get("id", "")
        if not re.fullmatch(r"[\w-]+", transaction, re.ASCII):
            raise ValueError("Neo4j did not open a transaction")
        headers = {}
        if affinity := response.headers.get("neo4j-cluster-affinity"):
            headers["neo4j-cluster-affinity"] = affinity
        try:
            if payload.get("errors"):
                raise ValueError("Neo4j query failed")
            return payload["data"]["values"]
        finally:
            try:
                await http.delete(f"{endpoint}/{transaction}", headers=headers)
            except httpx.HTTPError:
                pass  # An uncommitted transaction also expires on the server.


async def explain(snapshot, question, path, through, use_neo4j=False):
    records, params = project(snapshot, question, path, through)
    mode = "local"
    if use_neo4j and os.getenv("NEO4J_PASSWORD") and params["records"]:
        try:
            paths = await neo4j_paths(params)
            mode = "neo4j"
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            paths = local_paths(params)
            mode = "fallback"
    else:
        paths = local_paths(params)
    mapped = []
    query = words(question)
    for id, later, actors, entities, discussions in paths:
        row = records[id]
        overlap = query & words(row["title"] + " " + row["body"])
        linked = sorted(set(entities) & set(params["entities"]))
        reason = next((sentence.strip() for sentence in re.split(r"[\n]|(?<=[.!?])\s+", row["body"])
                       if REASON.search(sentence)), None)
        accepted = row.get("kind") in {"commit", "doc"} or bool(row.get("merged"))
        why = overlap & words(row["title"] + " " + (reason or ""))
        supported = bool(reason and accepted and not later and len(why) >= 2
                         and len(overlap) * 2 >= len(query) and (linked or len(why) >= 3))
        mapped.append({"record": row, "entities": linked, "actors": actors,
                       "supersededBy": [{**records[i], "basis": basis} for i, basis in sorted({tuple(link) for link in later})],
                       "related": [records[i] for i in sorted(set(discussions))],
                       "reason": reason if supported else None, "rank": 3 * len(linked) + len(overlap)})
    mapped.sort(key=lambda item: (bool(item["reason"]), bool(item["supersededBy"]), item["rank"],
                                  item["record"]["date"] or "", str(item["record"]["id"])), reverse=True)
    answer = mapped[0] if mapped and mapped[0]["reason"] else None
    return {"mode": mode, "confidence": ("moderate" if answer["entities"] else "low") if answer else "insufficient",
            "evidence": mapped[:5], "answer": answer["reason"] if answer else None}
