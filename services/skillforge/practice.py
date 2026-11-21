
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import delete, insert, select, update

from .config import JUDGE_TOKEN, JUDGE_URL
from .db import attempts, digest, engine, now, sessions
from .practice_contract import Submission
from .problem_scoring import assess_submission, best_assessments, next_problem
from .problems import PROBLEM_VERSION, PROBLEMS

router = APIRouter(prefix="/api/practice")


@router.get("/problems")
def catalog():
    return [problem.public() for problem in PROBLEMS.values()]


@router.get("/attempts")
def history(request: Request):
    from .main import owner_of
    owner = owner_of(request)
    with engine.connect() as connection:
        rows = connection.execute(select(attempts).where(
            attempts.c.owner == owner,
        ).order_by(attempts.c.created.desc()).limit(100)).mappings().all()
    return [
        {"id": row["id"], "problem": row["problem"], "created": row["created"], **row["result"]}
        for row in rows if not row["result"].get("pending")
    ]


@router.get("/recommendation")
def recommendation(request: Request):
    from .main import owner_of
    owner = owner_of(request)
    with engine.connect() as connection:
        rows = connection.execute(select(attempts.c.result, attempts.c.problem).where(
            attempts.c.owner == owner,
        ).order_by(attempts.c.created.desc()).limit(250)).mappings().all()
    return {"next": next_problem(best_assessments(rows), PROBLEMS)}


@router.post("/submit")
async def submit(body: Submission, request: Request):
    from .config import COOKIE
    from .main import owner_of
    owner = owner_of(request)
    problem = PROBLEMS.get(body.problem)
    if not problem:
        raise HTTPException(404, "Exercise unavailable.")
    if not JUDGE_URL or not JUDGE_TOKEN:
        raise HTTPException(503, "Code submissions require a configured isolated evaluator.")
    key = str(uuid4())
    with engine.begin() as connection:
        connection.execute(select(sessions.c.token).where(
            sessions.c.token == digest(request.cookies[COOKIE]),
        ).with_for_update()).first()
        recent = connection.execute(select(attempts.c.result, attempts.c.created).where(
            attempts.c.owner == owner, attempts.c.created > now() - 300,
        ).limit(12)).mappings().all()
        if len(recent) >= 9 or any(row["result"].get("pending") and row["created"] > now() - 90 for row in recent):
            raise HTTPException(429, "Wait for the current evaluation or try again shortly.")
        connection.execute(insert(attempts).values(
            id=key, owner=owner, problem=body.problem, created=now(), result={"pending": True},
        ))
    try:
        async with httpx.AsyncClient(timeout=65, follow_redirects=False) as http:
            response = await http.post(JUDGE_URL + "/evaluate", json=body.model_dump(),
                                       headers={"Authorization": "Bearer " + JUDGE_TOKEN})
            response.raise_for_status()
            data = response.json()
        if data.get("version") != PROBLEM_VERSION:
            raise ValueError("Evaluator version differs from the public catalog.")
        expected_categories = ["Example"] * len(problem.examples)
        if not body.examples_only:
            expected_categories += ["Functional", "Edge case", "Boundary case", "Large input"]
        cases = data["cases"]
        if ([row["category"] for row in cases] != expected_categories or
                any(row["status"] not in {"passed", "wrong_answer", "time_limit", "runtime_error", "invalid_output",
                                          "output_limit"} for row in cases)):
            raise ValueError("Invalid evaluation response.")
        cases = [{"category": row["category"], "status": row["status"], "duration": max(0, int(row["duration"]))}
                 for row in cases]
        result = {"passed": sum(row["status"] == "passed" for row in cases), "total": len(cases), "cases": cases,
                  "language": body.language, "examples_only": body.examples_only, "version": PROBLEM_VERSION}
        if not body.examples_only:
            result.update({"topic": problem.topic, "walkthrough": problem.walkthrough,
                           "assessment": assess_submission(cases, body.language, body.code)})
        with engine.begin() as connection:
            if body.examples_only:
                connection.execute(delete(attempts).where(attempts.c.id == key, attempts.c.owner == owner))
            else:
                connection.execute(update(attempts).where(attempts.c.id == key, attempts.c.owner == owner)
                                   .values(result=result))
        return result
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        with engine.begin() as connection:
            connection.execute(delete(attempts).where(attempts.c.id == key, attempts.c.owner == owner))
        raise HTTPException(503, "The isolated evaluator is busy or unavailable. Try again shortly.") from exc
