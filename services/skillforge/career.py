
import json
import re
from io import BytesIO
from typing import Literal
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from .config import COOKIE
from .contribution_projects import PROJECTS, roadmap
from .db import encode, entities, find_attempt, find_scan, now, recent_attempts, transaction, workspace_write
from .github import contribution_activity
from .problem_scoring import best_assessments, developer_index
from .scoring import RUBRIC

router = APIRouter(prefix="/api/career")
ROLES = {
    "Frontend developer": ["JavaScript", "TypeScript", "React", "Accessibility", "Testing", "Performance"],
    "Backend developer": ["APIs", "SQL", "Python", "Testing", "Reliability", "Data structures"],
    "Full-stack developer": ["TypeScript", "React", "APIs", "SQL", "Testing", "Deployment"],
    "Software engineer": ["Data structures", "Algorithms", "System design", "Testing", "Reliability", "Documentation"],
    "Data analyst": ["SQL", "Python", "Statistics", "Communication", "Documentation"],
    "Data engineer": ["SQL", "Python", "Data pipelines", "Testing", "Reliability", "Deployment"],
    "DevOps engineer": ["CI/CD", "Docker", "Deployment", "Reliability", "Testing", "Documentation"],
    "AI/ML engineer": ["Python", "Statistics", "Machine learning", "APIs", "Testing", "Performance"],
}
STATUS = {"proposed": {"approved", "dismissed"}, "approved": {"completed", "dismissed"}}


class Target(BaseModel):
    role: str = Field(max_length=40)
    description: str = Field(default="", max_length=6000)
    hours: int = Field(default=5, ge=1, le=40)


class Evidence(BaseModel):
    kind: Literal["repository", "assessment"]
    reference: str = Field(min_length=1, max_length=36)
    note: str = Field(max_length=400)


class ActionRequest(BaseModel):
    skill: str = Field(min_length=1, max_length=60)


class Transition(BaseModel):
    state: Literal["approved", "dismissed", "completed"]


def workspace(request):
    from .main import owner_of
    return owner_of(request)


def make_profile():
    return {"role": "Software engineer", "description": "", "hours": 5, "evidence": [], "actions": [], "audit": []}


def stored_profile(tx, owner):
    row = tx.run("MATCH (p:SFProfile {owner: $owner}) RETURN properties(p) AS profile", owner=owner).single()
    return json.loads(row["profile"]["data"]) if row else make_profile()


def save_profile(tx, owner, data):
    tx.run("MERGE (p:SFProfile {owner: $owner}) SET p.data = $data",
           owner=owner, data=encode(data)).consume()


def requirements(data):
    role = ROLES.get(data["role"], [])
    description = data["description"]
    known = {skill for skills in ROLES.values() for skill in skills}
    extracted = [skill for skill in sorted(known) if
                 re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", description, re.IGNORECASE)]
    return list(dict.fromkeys(role + extracted))


def audit(data, key, state):
    data["audit"] = [{"action": key, "state": state, "at": now()}, *data["audit"]][:150]


def response_data(data):
    targets = requirements(data)
    complete = {item["skill"] for item in data["actions"] if item["state"] == "completed"}
    return {"profile": data, "roles": list(ROLES), "requirements": targets,
            "planned": [skill for skill in targets if skill in complete],
            "open": [skill for skill in targets if skill not in complete]}


@router.get("")
def career(request: Request):
    owner = workspace(request)
    with transaction() as tx:
        data = stored_profile(tx, owner)
    return response_data(data)


@router.get("/developer-index")
def skills_index(request: Request):
    from .main import current_session
    owner = workspace(request)
    login = (current_session(request) or {}).get("github")
    with transaction() as tx:
        assessed = recent_attempts(tx, owner, 250)
        engineering = None
        repository = None
        if login:
            entries = entities(tx, """
                MATCH (s:SFScan {owner: $owner, state: 'complete'}) WHERE s.repo STARTS WITH $prefix
                RETURN s AS node ORDER BY s.created DESC, s.id DESC LIMIT 100
                """, owner=owner, prefix=login.lower() + "/")
            seen = set()
            for row in entries:
                if row["repo"] in seen:
                    continue
                seen.add(row["repo"])
                quality = row["result"]["quality"]
                if quality["version"] == RUBRIC and quality["rankable"] and quality["score"] is not None:
                    repository, engineering = row["repo"], quality["score"]
                    break
    return {**developer_index(engineering, best_assessments(assessed)), "repository": repository}


def contribution_plan(owner):
    with transaction() as tx:
        profile = stored_profile(tx, owner)
        rows = tx.run("""
            MATCH (s:SFScan {owner: $owner, state: 'complete'})
            WITH s.repo AS repo, max(s.created) AS scanned
            RETURN repo ORDER BY scanned DESC, repo LIMIT 6
            """, owner=owner)
        scans = [{"title": row["repo"], "url": "https://github.com/" + row["repo"],
                  "kind": "repository scan"} for row in rows]
        assessments = len(best_assessments(recent_attempts(tx, owner, 250)))
    progress = profile.get("contribution_progress", {})
    projects = [{**project, "completed": progress.get(project["id"], [])} for project in PROJECTS]
    return {**roadmap(profile, requirements(profile), scans, assessments, projects),
            "selected": profile.get("contribution_project")}


@router.get("/contribution-roadmap")
def contribution_roadmap(request: Request):
    return contribution_plan(workspace(request))


class ProjectProgress(BaseModel):
    project: str = Field(max_length=60)
    task: str | None = Field(default=None, max_length=60)
    completed: bool = False


@router.put("/contribution-roadmap")
def update_contribution_roadmap(body: ProjectProgress, request: Request):
    owner = workspace(request)
    project = next((item for item in PROJECTS if item["id"] == body.project), None)
    if not project or (body.task is not None and body.task not in {task["id"] for task in project["tasks"]}):
        raise HTTPException(422, "Choose an available project and milestone.")
    with workspace_write(owner, request.cookies[COOKIE]) as tx:
        profile = stored_profile(tx, owner)
        profile["contribution_project"] = body.project
        if body.task is not None:
            progress = profile.setdefault("contribution_progress", {})
            completed = set(progress.get(body.project, []))
            if body.completed:
                completed.add(body.task)
            else:
                completed.discard(body.task)
            progress[body.project] = sorted(completed)
        save_profile(tx, owner, profile)
    return contribution_plan(owner)


@router.post("/contribution-roadmap/github")
async def refresh_contribution_roadmap(request: Request):
    from .main import current_session
    owner = workspace(request)
    login = (current_session(request) or {}).get("github")
    if not login:
        raise HTTPException(403, "Connect GitHub before importing public activity.")
    try:
        activity = await contribution_activity(login)
    except (httpx.HTTPError, ValueError) as exc:
        raise HTTPException(502, "GitHub activity is temporarily unavailable.") from exc
    with workspace_write(owner, request.cookies[COOKIE]) as tx:
        profile = stored_profile(tx, owner)
        profile["github_activity"] = {**activity, "at": now()}
        save_profile(tx, owner, profile)
    return contribution_plan(owner)


@router.delete("/contribution-roadmap/github")
def clear_contribution_roadmap(request: Request):
    owner = workspace(request)
    with workspace_write(owner, request.cookies[COOKIE]) as tx:
        profile = stored_profile(tx, owner)
        profile.pop("github_activity", None)
        save_profile(tx, owner, profile)
    return contribution_plan(owner)


@router.put("/target")
def target(body: Target, request: Request):
    owner = workspace(request)
    if body.role not in ROLES:
        raise HTTPException(422, "Choose a supported role.")
    with workspace_write(owner, request.cookies[COOKIE]) as tx:
        data = stored_profile(tx, owner)
        data.update(body.model_dump())
        save_profile(tx, owner, data)
    return response_data(data)


@router.post("/evidence", status_code=201)
def attach(body: Evidence, request: Request):
    owner = workspace(request)
    find_evidence = find_scan if body.kind == "repository" else find_attempt
    with workspace_write(owner, request.cookies[COOKIE]) as tx:
        row = find_evidence(tx, owner, body.reference)
        if not row or not row["result"]:
            raise HTTPException(404, "The evidence is unavailable in this workspace.")
        result = row["result"]
        if body.kind == "repository" and row["state"] == "complete":
            title = row["repo"] + " · " + result["revision"][:7]
            label = "Static repository analysis"
        elif body.kind == "assessment" and not result.get("pending"):
            title = row["problem"].replace("-", " ").capitalize()
            label = f"Evaluator result · {result['passed']}/{result['total']} cases"
        else:
            raise HTTPException(422, "Attach completed analysis or assessment work.")
        data = stored_profile(tx, owner)
        if any((item["kind"], item["reference"]) == (body.kind, body.reference) for item in data["evidence"]):
            raise HTTPException(409, "This result is already linked to your portfolio.")
        if len(data["evidence"]) >= 100:
            raise HTTPException(409, "This portfolio has reached its evidence limit.")
        data["evidence"].insert(0, {
            "id": str(uuid4()), "kind": body.kind, "reference": body.reference, "title": title,
            "label": label, "note": body.note.strip(), "at": now(),
        })
        save_profile(tx, owner, data)
    return response_data(data)


@router.delete("/evidence/{key}")
def remove_evidence(key: str, request: Request):
    owner = workspace(request)
    with workspace_write(owner, request.cookies[COOKIE]) as tx:
        data = stored_profile(tx, owner)
        data["evidence"] = [item for item in data["evidence"] if item["id"] != key]
        save_profile(tx, owner, data)
    return response_data(data)


@router.post("/actions", status_code=201)
def propose(body: ActionRequest, request: Request):
    owner = workspace(request)
    with workspace_write(owner, request.cookies[COOKIE]) as tx:
        data = stored_profile(tx, owner)
        if body.skill not in requirements(data):
            raise HTTPException(422, "Choose a skill from the current role plan.")
        if len(data["actions"]) >= 100 or any(
            item["skill"] == body.skill and item["state"] in {"proposed", "approved", "completed"}
            for item in data["actions"]
        ):
            raise HTTPException(409, "This skill already has a plan or the plan limit was reached.")
        action = {"id": str(uuid4()), "skill": body.skill, "state": "proposed", "created": now()}
        data["actions"].insert(0, action)
        audit(data, action["id"], action["state"])
        save_profile(tx, owner, data)
    return response_data(data)


@router.patch("/actions/{key}")
def transition(key: str, body: Transition, request: Request):
    owner = workspace(request)
    with workspace_write(owner, request.cookies[COOKIE]) as tx:
        data = stored_profile(tx, owner)
        action = next((item for item in data["actions"] if item["id"] == key), None)
        if not action:
            raise HTTPException(404, "Action unavailable.")
        if body.state not in STATUS.get(action["state"], set()):
            raise HTTPException(409, "This action has already moved to a different stage.")
        action["state"] = body.state
        audit(data, key, body.state)
        save_profile(tx, owner, data)
    return response_data(data)


def pdf(lines):
    def escape(text):
        return "".join("\\" + char if char in "\\()" else char for char in text.encode(
            "cp1252", "replace",
        ).decode("cp1252") if ord(char) >= 32)
    pages = [lines[index:index + 43] for index in range(0, len(lines), 43)]
    objects = [b"<< /Type /Catalog /Pages 2 0 R >>", None,
               b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"]
    kids = []
    for page in pages:
        number = len(objects) + 1
        kids.append(f"{number} 0 R")
        content = "BT /F1 10 Tf 15 TL 46 795 Td " + "\n".join(f"({escape(text)}) Tj T*" for text in page) + " ET"
        content = content.encode("cp1252")
        objects.append(f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources "
                       f"<< /Font << /F1 3 0 R >> >> /Contents {number + 1} 0 R >>".encode())
        objects.append(f"<< /Length {len(content)} >>\nstream\n".encode() + content + b"\nendstream")
    objects[1] = f"<< /Type /Pages /Count {len(kids)} /Kids [{' '.join(kids)}] >>".encode()
    output = BytesIO()
    output.write(b"%PDF-1.4\n")
    positions = [0]
    for index, obj in enumerate(objects, 1):
        positions.append(output.tell())
        output.write(f"{index} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = output.tell()
    output.write(f"xref\n0 {len(positions)}\n0000000000 65535 f \n".encode())
    for position in positions[1:]:
        output.write(f"{position:010} 00000 n \n".encode())
    output.write(f"trailer\n<< /Size {len(positions)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return output.getvalue()


@router.get("/report.pdf")
def report(request: Request):
    import textwrap

    owner = workspace(request)
    with transaction() as tx:
        data = stored_profile(tx, owner)
    lines = ["SkillForge | Learning and evidence report", "", data["role"],
             f"Weekly time budget: {data['hours']} hours", "", "Requirements"]
    lines.extend(requirements(data))
    lines += ["", "Portfolio evidence"]
    for item in data["evidence"]:
        for text in (item["title"], item["label"], item["note"]):
            lines.extend(textwrap.wrap(text, width=80))
        lines.append("")
    lines += ["", "Action history"]
    lines.extend(item["skill"] + " - " + item["state"] for item in data["actions"])
    lines += ["", "This report records learning and evidence. It does not certify employment readiness."]
    return Response(pdf(lines), media_type="application/pdf",
                    headers={"Content-Disposition": 'attachment; filename="skillforge-learning-report.pdf"'})
