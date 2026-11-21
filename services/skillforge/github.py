
import asyncio
import json
import re
from urllib.parse import quote, urlsplit

import httpx

from .config import GITHUB_TOKEN

NAME = re.compile(r"[A-Za-z0-9_.-]{1,100}")
SHA = re.compile(r"[a-f0-9]{40}")
MAX_FILES = 72
FILE_BYTES = 64_000
MAX_TREE_BYTES = 8_000_000
EXCLUDED = {"node_modules", "vendor", "dist", "build", ".venv", "__pycache__", "generated"}
SOURCE_EXTENSIONS = {".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs", ".mts", ".cts"}


class GitHubError(Exception):
    def __init__(self, message, retry_at=None):
        super().__init__(message)
        self.retry_at = retry_at


def repo_name(value):
    value = value.strip()
    if value.lower().startswith("github.com/"):
        value = "https://" + value
    if "://" in value:
        try:
            url = urlsplit(value)
            if url.scheme != "https" or url.netloc.lower() != "github.com" or url.query or url.fragment:
                raise ValueError
            value = url.path.strip("/")
        except ValueError as exc:
            raise GitHubError("Enter a public GitHub URL such as https://github.com/owner/repo.") from exc
    parts = value.removesuffix(".git").split("/")
    if len(parts) != 2 or any(not NAME.fullmatch(part) or part in {".", ".."} for part in parts):
        raise GitHubError("Enter a GitHub repository in owner/repo format.")
    return "/".join(parts).lower()


def headers(token=GITHUB_TOKEN):
    result = {"Accept": "application/vnd.github+json", "User-Agent": "SkillForge"}
    if token:
        result["Authorization"] = "Bearer " + token
    return result


def client():
    return httpx.AsyncClient(timeout=12, follow_redirects=False, limits=httpx.Limits(max_connections=8))


def check_response(response):
    if response.status_code == 429 or (
        response.status_code == 403
        and (response.headers.get("x-ratelimit-remaining") == "0" or response.headers.get("retry-after"))
    ):
        reset = response.headers.get("x-ratelimit-reset", "")
        raise GitHubError("GitHub is throttling requests. Try again after the rate limit resets.",
                          int(reset) if reset.isdecimal() else None)
    if response.status_code in (403, 404):
        raise GitHubError("This public GitHub resource could not be accessed.")
    if response.status_code != 200:
        raise GitHubError("GitHub could not complete the request. Try again shortly.")


async def api(http, path, params=None, token=GITHUB_TOKEN, limit=MAX_TREE_BYTES):
    async with http.stream("GET", "https://api.github.com" + path, params=params, headers=headers(token)) as response:
        check_response(response)
        content = bytearray()
        async for chunk in response.aiter_bytes(16384):
            content.extend(chunk)
            if len(content) > limit:
                raise GitHubError("GitHub returned more metadata than this workspace can analyze.")
    return json.loads(content)


def source_path(path):
    if not path or len(path) > 400 or any(part in {"", ".", ".."} for part in path.split("/")):
        return False
    if any(part in EXCLUDED for part in path.split("/")[:-1]):
        return False
    name = path.rsplit("/", 1)[-1].lower()
    return not name.endswith((".min.js", ".d.ts")) and any(name.endswith(ext) for ext in SOURCE_EXTENSIONS)


def test_path(path):
    parts = path.lower().split("/")
    return any(part in {"tests", "test", "__tests__", "spec"} for part in parts[:-1]) or (
        parts[-1].startswith("test_") or any(part in parts[-1] for part in (".test.", ".spec.", "_test.py"))
    )


def source_href(repo, revision, path, line=None):
    return f"https://github.com/{repo}/blob/{revision}/{quote(path, safe='/')}" + (f"#L{line}" if line else "")


async def read_source(http, repo, revision, path):
    target = f"https://raw.githubusercontent.com/{repo}/{revision}/{quote(path, safe='/')}"
    async with http.stream("GET", target, headers={"User-Agent": "SkillForge"}) as response:
        check_response(response)
        body = bytearray()
        async for chunk in response.aiter_bytes(16384):
            body.extend(chunk)
            if len(body) > FILE_BYTES:
                raise GitHubError("This file exceeds the preview size limit.")
    if b"\0" in body:
        raise GitHubError("Binary source previews are unavailable.")
    return body.decode("utf-8", errors="replace")


async def get_snapshot(repo):
    async with client() as http:
        info = await api(http, "/repos/" + repo, limit=128_000)
        if info.get("private") or info.get("visibility") != "public":
            raise GitHubError("This workspace accepts public GitHub repositories.")
        branch = info["default_branch"]
        commit = await api(http, f"/repos/{repo}/commits/{quote(branch, safe='')}", limit=1_500_000)
        revision = commit["sha"]
        tree_sha = commit["commit"]["tree"]["sha"]
        if not SHA.fullmatch(revision) or not SHA.fullmatch(tree_sha):
            raise GitHubError("GitHub returned an unsupported revision.")
        tree = await api(http, f"/repos/{repo}/git/trees/{tree_sha}", {"recursive": "1"})
        files = [
            entry for entry in tree["tree"]
            if entry.get("type") == "blob" and entry.get("mode") in {"100644", "100755"}
        ]
        paths = {entry["path"] for entry in files}
        eligible = [entry for entry in files if source_path(entry["path"])]
        small = sorted(
            (entry for entry in eligible if 0 < entry.get("size", 0) <= FILE_BYTES),
            key=lambda entry: (not test_path(entry["path"]), entry["path"].count("/"), entry["path"]),
        )
        semaphore = asyncio.Semaphore(4)

        async def fetch(entry):
            async with semaphore:
                try:
                    return entry["path"], await read_source(http, repo, revision, entry["path"])
                except (GitHubError, httpx.HTTPError):
                    return entry["path"], None

        sources = {
            path: data for path, data in await asyncio.gather(*(fetch(entry) for entry in small[:MAX_FILES]))
            if data is not None
        }
        context_names = {"readme", "readme.md", "readme.rst", "package.json", "pyproject.toml", "requirements.txt"}
        context_files = sorted(
            (entry for entry in files if entry["path"].rsplit("/", 1)[-1].lower() in context_names
             and 0 < entry.get("size", 0) <= FILE_BYTES),
            key=lambda entry: (entry["path"].count("/"), entry["path"]),
        )[:6]
        metadata_files = {
            path: data for path, data in await asyncio.gather(*(fetch(entry) for entry in context_files))
            if data is not None
        }
        configs = sorted(path for path in paths if path.rsplit("/", 1)[-1] == "tsconfig.json")[:4]
        aliases = {}
        for path in configs:
            try:
                raw_config = await read_source(http, repo, revision, path)
                compiler = json.loads(raw_config).get("compilerOptions", {})
                base = compiler.get("baseUrl", ".")
                path_map = compiler.get("paths", {})
                if isinstance(base, str) and isinstance(path_map, dict):
                    aliases[path] = {"base": base, "paths": path_map}
            except (GitHubError, httpx.HTTPError, ValueError, AttributeError):
                continue
        history = []
        history_available = False
        try:
            pulls = await api(http, f"/repos/{repo}/pulls", {"state": "all", "per_page": 12}, limit=1_200_000)
            history = [
                {"id": "pr-" + str(item["number"]), "label": "PR #" + str(item["number"]),
                 "title": item["title"][:240], "body": (item.get("body") or "")[:700],
                 "date": item.get("updated_at"), "url": f"https://github.com/{repo}/pull/{item['number']}"}
                for item in pulls
            ]
            history_available = True
        except (GitHubError, httpx.HTTPError, ValueError, KeyError):
            pass
        try:
            commits = await api(http, f"/repos/{repo}/commits", {"sha": revision, "per_page": 8}, limit=600_000)
            for item in commits:
                if not SHA.fullmatch(item["sha"]):
                    continue
                title, _, message = item["commit"]["message"].partition("\n")
                history.append({"id": "commit-" + item["sha"], "label": "Commit " + item["sha"][:7],
                                "title": title[:240], "body": message.strip()[:700],
                                "date": item["commit"]["committer"]["date"],
                                "url": f"https://github.com/{repo}/commit/{item['sha']}"})
            history_available = True
        except (GitHubError, httpx.HTTPError, ValueError, KeyError, TypeError):
            pass

    return {
        "repo": repo, "branch": branch, "revision": revision, "description": (info.get("description") or "")[:300],
        "language": info.get("language"), "paths": paths, "sources": sources, "eligible": len(eligible),
        "total_files": len(files), "truncated": bool(tree.get("truncated")),
        "history": sorted(history, key=lambda item: item["date"] or "", reverse=True),
        "history_available": history_available, "aliases": aliases, "metadata_files": metadata_files,
    }


async def public_repositories(login, page):
    if not NAME.fullmatch(login):
        return []
    async with client() as http:
        payload = await api(http, "/users/" + login + "/repos",
                            {"per_page": 30, "page": page, "sort": "updated", "type": "owner"}, limit=600_000)
    return [
        {"name": item["full_name"], "description": item.get("description"), "language": item.get("language")}
        for item in payload if item.get("private") is False
    ]
