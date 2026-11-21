
import asyncio
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException, Request

from .config import COOKIE, JUDGE_TOKEN, JUDGE_URL
from .db import encode, now, recent_attempts, transaction, workspace_write
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
    with transaction() as tx:
        rows = recent_attempts(tx, owner, 100)
    return [
        {"id": row["id"], "problem": row["problem"], "created": row["created"], **row["result"]}
        for row in rows if not row["result"].get("pending")
    ]


@router.get("/recommendation")
def recommendation(request: Request):
    from .main import owner_of
    owner = owner_of(request)
    with transaction() as tx:
        rows = recent_attempts(tx, owner, 250)
    return {"next": next_problem(best_assessments(rows), PROBLEMS)}


def reserve_attempt(owner, token, key, problem):
    timestamp = now()
    with workspace_write(owner, token) as tx:
        recent = recent_attempts(tx, owner, 12, after=timestamp - 300)
        if len(recent) >= 9 or any(row["result"].get("pending") and row["created"] > timestamp - 90
                                   for row in recent):
            raise HTTPException(429, "Wait for the current evaluation or try again shortly.")
        tx.run("""
            CREATE (:SFAttempt {id: $id, owner: $owner, problem: $problem, created: $now, result: $result})
            """, id=key, owner=owner, problem=problem, now=timestamp, result=encode({"pending": True})).consume()


def finish_attempt(owner, key, result=None):
    with transaction(write=True) as tx:
        if result is None:
            tx.run("MATCH (a:SFAttempt {id: $id, owner: $owner}) DELETE a", id=key, owner=owner).consume()
        else:
            tx.run("MATCH (a:SFAttempt {id: $id, owner: $owner}) SET a.result = $result",
                   id=key, owner=owner, result=encode(result)).consume()


@router.post("/submit")
async def submit(body: Submission, request: Request):
    from .main import owner_of
    owner = await asyncio.to_thread(owner_of, request)
    problem = PROBLEMS.get(body.problem)
    if not problem:
        raise HTTPException(404, "Exercise unavailable.")
    if not JUDGE_URL or not JUDGE_TOKEN:
        raise HTTPException(503, "Code submissions require a configured isolated evaluator.")
    key = str(uuid4())
    await asyncio.to_thread(reserve_attempt, owner, request.cookies[COOKIE], key, body.problem)
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
        await asyncio.to_thread(finish_attempt, owner, key, None if body.examples_only else result)
        return result
    except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
        await asyncio.to_thread(finish_attempt, owner, key)
        raise HTTPException(503, "The isolated evaluator is busy or unavailable. Try again shortly.") from exc
