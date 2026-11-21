
"""Start the compiled SkillForge app and API together on the local machine."""

import argparse
import asyncio
import errno
import hashlib
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import tempfile
import webbrowser
from contextlib import contextmanager, suppress
from importlib import import_module
from pathlib import Path
from urllib import request

import uvicorn

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "apps" / "web"
SERVICES = ROOT / "services"
STATE = ROOT / ".skillforge-local"
HOST = "127.0.0.1"
DEFAULT_PORT = 8765
PORT_CHOICES = 20
WINDOWS = os.name == "nt"


def options():
    parser = argparse.ArgumentParser(description="Build and run SkillForge on this computer.")
    parser.add_argument("--port", type=int, help="Require a specific local port instead of choosing a free one.")
    parser.add_argument("--no-browser", action="store_true", help="Print the URL without opening a browser.")
    parser.add_argument("--check", action="store_true", help="Verify startup with a temporary database and stop.")
    parser.add_argument("--reinstall", action="store_true", help="Reinstall the locked web dependencies.")
    args = parser.parse_args()
    if args.port is not None and not 1024 <= args.port <= 65535:
        parser.error("--port must be between 1024 and 65535.")
    return args


@contextmanager
def checkout_lock():
    STATE.mkdir(exist_ok=True)
    with (STATE / "launcher.lock").open("a+b") as lock:
        try:
            if WINDOWS:
                import msvcrt

                lock.seek(0)
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl

                fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("This checkout already has an active launcher. Stop it before starting another.") from exc
        yield


def reserve_port(explicit):
    choices = [explicit] if explicit is not None else range(DEFAULT_PORT, DEFAULT_PORT + PORT_CHOICES)
    for port in choices:
        reservation = socket.socket()
        try:
            if WINDOWS:
                reservation.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
            reservation.bind((HOST, port))
        except OSError as exc:
            reservation.close()
            if exc.errno not in {errno.EADDRINUSE, errno.EACCES, 10048, 10013}:
                raise
        else:
            return reservation
    label = str(explicit) if explicit is not None else f"{DEFAULT_PORT}–{DEFAULT_PORT + PORT_CHOICES - 1}"
    raise RuntimeError(f"Port {label} is in use or unavailable. Choose another with --port 8870.")


def prepare_web(reinstall):
    node = shutil.which("node.exe" if WINDOWS else "node")
    npm = shutil.which("npm.cmd" if WINDOWS else "npm")
    if not node or not npm:
        raise RuntimeError("Node.js and npm must be available on PATH. Use Node.js 22.12 or newer.")
    version = subprocess.check_output([node, "--version"], text=True, timeout=10).strip()
    match = re.fullmatch(r"v(\d+)\.(\d+)\.(\d+)", version)
    if not match or tuple(map(int, match.groups())) < (22, 12, 0):
        raise RuntimeError(f"Node.js 22.12 or newer is required. Found {version!r}.")
    npm_version = subprocess.check_output([npm, "--version"], cwd=WEB, text=True, timeout=15).strip()
    installed = WEB / "node_modules"
    stamp = installed / ".skillforge-install"
    files = [WEB / "package.json", WEB / "package-lock.json"]
    identity = hashlib.sha256(f"{version}\n{npm_version}".encode() + b"".join(path.read_bytes() for path in files)).hexdigest()
    cached = stamp.is_file() and stamp.read_text(encoding="utf-8", errors="replace") == identity
    suffix = ".cmd" if WINDOWS else ""
    tools = [installed / ".bin" / ("vite" + suffix), installed / ".bin" / ("tsc" + suffix),
             installed / ".package-lock.json"]
    if reinstall or not cached or not all(path.is_file() for path in tools):
        print("Installing web dependencies from the lockfile...", flush=True)
        try:
            subprocess.run([npm, "ci", "--include=dev", "--no-audit", "--no-fund"], cwd=WEB, check=True)
        except subprocess.CalledProcessError as exc:
            raise RuntimeError("Web dependencies could not be installed. Check the npm error above and your connection.") from exc
        stamp.write_text(identity, encoding="utf-8")

    print("Building the SkillForge website...", flush=True)
    try:
        subprocess.run([npm, "run", "build"], cwd=WEB, check=True)
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("The website build failed. Review the error above. If dependencies are damaged, retry with --reinstall.") from exc


def ready(origin):
    opener = request.build_opener(request.ProxyHandler({}))
    try:
        with opener.open(origin + "/api/health", timeout=4) as response:
            if json.load(response).get("ok") is not True:
                raise RuntimeError("The SkillForge API did not report a healthy database.")
        with opener.open(origin + "/", timeout=4) as response:
            html = response.read(65_536).decode("utf-8")
        asset = re.search(r'<script\b[^>]+\bsrc="(/assets/[^"]+\.js)"', html)
        if 'id="root"' not in html or not asset:
            raise RuntimeError("SkillForge served an incomplete web build.")
        with opener.open(origin + asset.group(1), timeout=4) as response:
            if not response.read(1):
                raise RuntimeError("SkillForge served an empty web bundle.")
    except (OSError, ValueError) as exc:
        raise RuntimeError("SkillForge did not pass its local startup check. Review the server output above.") from exc


async def serve(reservation, database, args):
    port = reservation.getsockname()[1]
    origin = f"http://{HOST}:{port}"
    callback = origin + "/api/auth/github/callback"
    os.environ.update(
        APP_ENV="development",
        APP_ORIGIN=origin,
        DATABASE_URL="sqlite:///" + database.as_posix(),
        SCAN_WORKER_ENABLED="true",
        GITHUB_OAUTH_CALLBACK_URL=callback,
    )
    sys.path.insert(0, str(SERVICES))
    app = import_module("skillforge.main").app
    engine = import_module("skillforge.db").engine
    server = uvicorn.Server(uvicorn.Config(
        app, host=HOST, port=port, access_log=False, timeout_graceful_shutdown=5,
    ))
    task = asyncio.create_task(server.serve(sockets=[reservation]))
    try:
        loop = asyncio.get_running_loop()
        deadline = loop.time() + 30
        while not server.started and not task.done() and loop.time() < deadline:
            await asyncio.sleep(0.1)
        if not server.started:
            if task.done():
                await task
            raise RuntimeError("The local server could not start. Review the server output above.")
        await asyncio.to_thread(ready, origin)
        print(f"\nSkillForge is ready at {origin}/", flush=True)
        if args.check:
            print("Startup check passed using a temporary database.", flush=True)
            return
        if os.environ.get("GITHUB_CLIENT_ID") and os.environ.get("GITHUB_CLIENT_SECRET"):
            print(f"GitHub OAuth callback for this run: {callback}", flush=True)
        print("Press Ctrl+C to stop. Keep this window open while using SkillForge.", flush=True)
        if not args.no_browser:
            try:
                if not await asyncio.to_thread(webbrowser.open, origin + "/"):
                    print("Open the URL above in your browser.")
            except (OSError, webbrowser.Error):
                print("Open the URL above in your browser.")
        await task
    finally:
        server.should_exit = True
        try:
            if not task.done():
                if not server.started:
                    task.cancel()
                with suppress(asyncio.CancelledError):
                    await task
        finally:
            engine.dispose()


def main():
    args = options()
    try:
        with checkout_lock(), reserve_port(args.port) as reservation:
            port = reservation.getsockname()[1]
            if args.port is None and port != DEFAULT_PORT:
                print(f"Port {DEFAULT_PORT} is occupied or unavailable. Using {port}.")
            prepare_web(args.reinstall)
            if args.check:
                with tempfile.TemporaryDirectory(prefix="check-", dir=STATE) as directory:
                    asyncio.run(serve(reservation, Path(directory) / "skillforge.db", args))
            else:
                asyncio.run(serve(reservation, ROOT / ".skillforge.db", args))
    except KeyboardInterrupt:
        return 0
    except (RuntimeError, OSError, subprocess.SubprocessError) as exc:
        print(f"\n{exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
