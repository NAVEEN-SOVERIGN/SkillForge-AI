
import asyncio
import json
import os
import secrets
import time

from fastapi import FastAPI, Header, HTTPException

from .practice_contract import Submission

app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)
TOKEN = os.getenv("JUDGE_TOKEN", "")
RUNTIME = os.getenv("JUDGE_CONTAINER_RUNTIME", "runsc")
IMAGES = {"python": os.getenv("JUDGE_PYTHON_IMAGE", ""), "javascript": os.getenv("JUDGE_JAVASCRIPT_IMAGE", "")}
RUNNER_LIMIT = 32_000
RUNNER_COUNT = asyncio.Semaphore(2)

PYTHON_WRAPPER = """
import json, os, sys, tempfile

data = json.load(sys.stdin)
with open('/tmp/solution.py', 'w', encoding='utf-8') as target:
    target.write(data['source'])
with tempfile.TemporaryFile(dir='/tmp') as case:
    case.write(data['input'].encode('utf-8'))
    case.seek(0)
    os.dup2(case.fileno(), 0)
    os.execv(sys.executable, [sys.executable, '-IBS', '/tmp/solution.py'])
"""

JAVASCRIPT_WRAPPER = """
const { readFileSync, writeFileSync } = require('node:fs');
const { spawnSync } = require('node:child_process');
const data = JSON.parse(readFileSync(0, 'utf8'));
writeFileSync('/tmp/solution.cjs', data.source, 'utf8');
const result = spawnSync(process.execPath, ['/tmp/solution.cjs'], {
  input: data.input, maxBuffer: 32001, stdio: ['pipe', 'pipe', 'ignore'],
});
if (result.error || result.status !== 0) process.exit(1);
process.stdout.write(result.stdout);
"""


class SandboxUnavailable(Exception):
    pass


async def remove_container(name):
    try:
        cleanup = await asyncio.create_subprocess_exec(
            "docker", "rm", "-f", name, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL,
        )
        try:
            await asyncio.wait_for(cleanup.wait(), 4)
        except TimeoutError:
            cleanup.kill()
            await cleanup.wait()
    except FileNotFoundError:
        return


async def run_case(language, source, value):
    image = IMAGES[language]
    if "@sha256:" not in image or not RUNTIME:
        raise SandboxUnavailable
    encoded = json.dumps({"source": source, "input": json.dumps(value, ensure_ascii=False)}, ensure_ascii=False).encode()
    name = "skillforge-" + secrets.token_hex(12)
    runtime = ["python", "-IBS", "-c", PYTHON_WRAPPER] if language == "python" else ["node", "-e", JAVASCRIPT_WRAPPER]
    command = [
        "docker", "run", "--rm", "--interactive", "--name", name, "--pull", "never",
        "--runtime", RUNTIME, "--network", "none", "--read-only", "--cap-drop", "ALL",
        "--security-opt", "no-new-privileges", "--user", "65534:65534", "--memory", "144m",
        "--memory-swap", "144m", "--cpus", "0.65", "--pids-limit", "24", "--log-driver", "none",
        "--ulimit", "fsize=1048576:1048576", "--tmpfs", "/tmp:size=4m,mode=1777,nosuid,nodev,noexec",
        "--entrypoint", runtime[0], image, *runtime[1:],
    ]
    started = time.monotonic()
    try:
        proc = await asyncio.create_subprocess_exec(*command, stdin=asyncio.subprocess.PIPE,
                                                    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.DEVNULL)
    except OSError as exc:
        raise SandboxUnavailable from exc
    status, stdout = "runtime_error", bytearray()
    try:
        async with asyncio.timeout(7):
            proc.stdin.write(encoded)
            await proc.stdin.drain()
            proc.stdin.close()
            while chunk := await proc.stdout.read(8192):
                stdout.extend(chunk)
                if len(stdout) > RUNNER_LIMIT:
                    status = "output_limit"
                    break
            else:
                code = await proc.wait()
                if code == 125:
                    raise SandboxUnavailable
                status = "finished" if code == 0 else "runtime_error"
    except TimeoutError:
        status = "time_limit"
    except (BrokenPipeError, ConnectionResetError):
        if await proc.wait() == 125:
            raise SandboxUnavailable from None
    finally:
        if proc.returncode is None:
            proc.kill()
            await proc.wait()
            await remove_container(name)
    result = None
    if status == "finished":
        try:
            result = json.loads(stdout)
        except (ValueError, RecursionError):
            status = "invalid_output"
    return status, result, round((time.monotonic() - started) * 1000)


def matches(actual, expected):
    if type(expected) is bool or expected is None or isinstance(expected, str):
        return type(actual) is type(expected) and actual == expected
    if isinstance(expected, (int, float)):
        return type(actual) in {int, float} and actual == expected
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(
            matches(left, right) for left, right in zip(actual, expected, strict=True)
        )
    return isinstance(actual, dict) and actual.keys() == expected.keys() and all(
        matches(actual[key], expected[key]) for key in expected
    )


@app.post("/evaluate")
async def evaluate(body: Submission, authorization: str = Header(default="")):
    if not TOKEN or not secrets.compare_digest(authorization.encode(), ("Bearer " + TOKEN).encode()):
        raise HTTPException(401, "Evaluator authorization failed.")
    if RUNNER_COUNT.locked():
        raise HTTPException(429, "The evaluator is busy.")
    from .problems import PROBLEMS
    problem = PROBLEMS.get(body.problem)
    if not problem:
        raise HTTPException(404, "Unknown exercise.")
    cases = [(value, output, "Example") for value, output in problem.examples]
    if not body.examples_only:
        cases += [(value, output, label) for (value, output), label in zip(
            problem.hidden, ("Edge case", "Boundary case", "Large input"), strict=True,
        )]
    rows = []
    async with RUNNER_COUNT:
        try:
            for value, expected, label in cases:
                status, output, duration = await run_case(body.language, body.code, value)
                if status == "finished":
                    status = "passed" if matches(output, expected) else "wrong_answer"
                rows.append({"category": label, "status": status, "duration": duration})
        except SandboxUnavailable as exc:
            raise HTTPException(503, "The isolated evaluator is unavailable.") from exc
    passed = sum(row["status"] == "passed" for row in rows)
    return {"cases": rows, "passed": passed, "total": len(rows)}
