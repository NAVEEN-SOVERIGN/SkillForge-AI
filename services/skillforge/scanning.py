
import asyncio
import logging
import secrets

from sqlalchemy import select, update

from .analysis import quality, structure
from .db import engine, expire_guests, now, scans
from .github import GitHubError, get_snapshot, source_href

logger = logging.getLogger(__name__)
LEASE_SECONDS = 360


def compile_snapshot(snapshot):
    graph, parsed = structure(snapshot)
    return {
        "repo": snapshot["repo"], "branch": snapshot["branch"], "revision": snapshot["revision"],
        "description": snapshot["description"], "language": snapshot["language"], "graph": graph,
        "quality": quality(snapshot, parsed), "history": snapshot["history"],
        "history_available": snapshot["history_available"], "preview_paths": sorted(snapshot["sources"]),
        "sample": snapshot["revision"] == "sample",
    }


def claim():
    with engine.begin() as connection:
        connection.execute(update(scans).where(
            scans.c.state == "running", scans.c.updated < now() - LEASE_SECONDS,
        ).values(state="queued", lease=None, updated=now()))
        candidate = connection.execute(select(scans).where(
            scans.c.state == "queued",
        ).order_by(scans.c.created).limit(1)).mappings().first()
        if not candidate:
            return None
        lease = secrets.token_hex(24)
        changed = connection.execute(update(scans).where(
            scans.c.id == candidate["id"], scans.c.state == "queued",
        ).values(state="running", lease=lease, updated=now()))
        return (dict(candidate), lease) if changed.rowcount == 1 else None


def finish(scan_id, lease, state, result):
    with engine.begin() as connection:
        connection.execute(update(scans).where(
            scans.c.id == scan_id, scans.c.lease == lease, scans.c.state == "running",
        ).values(state=state, result=result, lease=None, updated=now()))


async def run_scans():
    last_cleanup = 0
    while True:
        try:
            if now() - last_cleanup > 60:
                await asyncio.to_thread(expire_guests)
                last_cleanup = now()
            claimed = await asyncio.to_thread(claim)
            if claimed:
                await perform(*claimed)
                continue
        except Exception as exc:  # noqa: BLE001 - Keep the queue alive and omit untrusted exception content.
            logger.error("Scan worker iteration failed (%s).", type(exc).__name__)
        await asyncio.sleep(1.25)


async def perform(scan, lease):
    try:
        async with asyncio.timeout(240):
            snapshot = await get_snapshot(scan["repo"])
            payload = await asyncio.to_thread(compile_snapshot, snapshot)
            if scan["options"].get("ai"):
                from .review import review
                payload["review"] = await review(snapshot, payload["quality"])
        await asyncio.to_thread(finish, scan["id"], lease, "complete", payload)
    except GitHubError as exc:
        await asyncio.to_thread(finish, scan["id"], lease, "failed", {"error": str(exc), "retryAt": exc.retry_at})
    except Exception as exc:  # noqa: BLE001 - Finish the job without exposing provider or repository content.
        logger.warning("Repository scan did not complete (%s).", type(exc).__name__)
        await asyncio.to_thread(finish, scan["id"], lease, "failed", {"error": "Analysis was interrupted. Try again."})


def source_for(result, path, line=None):
    if result.get("sample"):
        return None
    return source_href(result["repo"], result["revision"], path, line)
