
# Running SkillForge

## Local development

Use Node 22.12 or later, Python 3.12 and uv. Install the locked frontend and backend dependencies from their respective directories. Start the API and web app in separate terminals.

From `services`:

```sh
uv sync --locked
uv run --locked uvicorn skillforge.main:app --host 127.0.0.1 --port 8765 --no-access-log
```

From `apps/web`:

```sh
npm ci
npm run dev
```

Open [the local workspace](http://localhost:5173/). The seeded example, public URL import, graph, practice catalog and portfolio plan work without account credentials. The judge needs a separate service. By default the API creates an ignored SQLite database and hosts the scan worker. To serve a compiled web build directly from the API, run `npm run build` and set `APP_ORIGIN=http://127.0.0.1:8765` before starting the API.

For optional integrations, copy `.env.example` to an ignored `.env` at the repo root. From `services`, add `--env-file ../.env` to the `uv run` arguments.

## Staging deployment

1. Build the root Dockerfile. Deploy the API and static web app behind one HTTPS reverse proxy. Set `APP_ORIGIN` to the public URL and use PostgreSQL over TLS. Apply a request size cap, per-IP limits for session creation and imports, and an API timeout longer than the evaluator request timeout.
2. Run `python -m skillforge.migrate` as a one-off schema task with a privileged database role. Run the API and scan worker with a separate role that has table access. The production API verifies the schema revision at startup.
3. Deploy a worker using the same image and `python -m skillforge.worker` as its command. Start with one worker to limit shared GitHub quota. Scale after measuring queue age, throttling and upstream calls. Keep the API's embedded worker disabled.
4. Configure separate GitHub OAuth credentials and the callback `/api/auth/github/callback` using the staging origin. The picker lists public repos owned by the connected account, and the service discards the OAuth token after profile lookup. An optional separate read-only API token raises public scan quotas.
5. Configure the judge on its own isolated Linux worker before enabling assessed submissions. Require private networking or authenticated TLS for the API-to-judge link. Keep cloud credentials, data volumes and database routes away from the evaluator host. Pre-pull vetted Python and Node images by digest and install an isolated container runtime such as gVisor. Use `python -m uvicorn skillforge.judge:app` on the judge host, with the Docker CLI available and a high-entropy service token. Pin its images with `JUDGE_PYTHON_IMAGE` and `JUDGE_JAVASCRIPT_IMAGE`. Point the web API at the judge using `JUDGE_URL` and the same `JUDGE_TOKEN`. Keep the judge service off public ingress.
6. If enabling optional Gemini findings, configure a supported model and a server-side key. A scan sends its bounded source excerpts only when the user opts in. The provisional score remains based on the static checks.
7. Verify GitHub OAuth, live scans, source references, durable recovery, PostgreSQL restore, provider timeouts, and the evaluator's limits and isolation before public rollout. Use separate staging data and values. Rebuild from an earlier image to roll back code only when the running schema supports it.

## Current release boundary

The implementation covers public GitHub import and opt-in connected selection, bounded static structure analysis for JavaScript, TypeScript and Python, provisional scoring, practice, and portfolio planning. Dynamic dispatch and provider history outside the sample are outside graph coverage. The editor drafts stay in tab memory.

The current database stores graph metadata in the scan snapshot. Neo4j projection, private repository access, Google and email sign-in, resume extraction, the full legacy career simulation suite, and legacy data migrations remain follow-up work. Keep the inherited inventory as a roadmap and confirm environment and provider choices before enabling those features.

## Operational checks

Use `GET /api/health` for API liveness and current database connectivity. Monitor the oldest queued scan, failed scans by rate limits or provider outages, evaluator availability, and PostgreSQL backups. Keep access-log redaction at the reverse proxy and exclude HTTP bodies, cookies, credentials, and callback query values from logs.
