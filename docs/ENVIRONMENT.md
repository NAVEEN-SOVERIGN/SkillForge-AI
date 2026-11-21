# Environment and credential handoff

Use an ignored local environment file or the staging secret store for live integrations. The seeded workspace and public URL import can run without credentials. Use separate staging and production secrets and exact OAuth callback URLs for the new host. Review [.env.example](../.env.example) for the implemented settings and [operations](OPERATIONS.md) for startup commands. The inventory below includes deferred integration settings from the two reference applications.

| Settings | Integration |
| --- | --- |
| `NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE` | The decision-context pilot uses the HTTPS Neo4j Query API. Set `NEO4J_URI` to the Aura `neo4j+s://` connection URI or override the origin with `NEO4J_QUERY_URL`. The account needs transaction write access for a projection that is rolled back after traversal. Use an isolated staging database with its own credentials. Without Neo4j settings, the app uses its local graph. |
| `SESSION_SECRET`, `SECURE_SESSION_COOKIE`, `SESSION_COOKIE_SAMESITE`, `ALLOWED_ORIGINS`, `FRONTEND_URL` | Preserve these names where practical. Use a fresh secret per environment, HTTPS secure cookies in hosted environments, `lax` as default, and an exact public origin. |
| `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `GITHUB_OAUTH_CALLBACK_URL` | Keep account sign-in. Register the new staging and production callbacks per provider app. |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`, `GOOGLE_OAUTH_CALLBACK_URL` | Keep Google sign-in. Register the new callback and verify approved origins. |
| `GITHUB_API_TOKEN` | Optional server-side read-only quota credential for public indexing, independent of OAuth sign-in. Use this Hackfront name in the integrated service and map upstream's `GITHUB_TOKEN` when running its reference build. |
| `BREVO_API_KEY`, `BREVO_FROM` | Optional HTTPS email provider. Confirm sender, capabilities and mail delivery in staging. Prefer the configured HTTPS provider when both mail paths are present. |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM` | Optional SMTP provider. Check host egress and auth before enabling email. |
| `GITHUB_API_TIMEOUT_SECONDS`, `MAX_INDEXED_FILES`, `MAX_SOURCE_FILES`, `MAX_SOURCE_BYTES`, `MAX_SOURCE_TOTAL_BYTES` | Non-secret import settings. Keep validation bounds and conservative defaults. |
| `DATABASE_URL` | New PostgreSQL secret for account, career, evidence and queue storage. Separate migration and runtime access in production. |
| GitHub picker and optional private access | Define the configured connection scopes and callback in milestone 2. If private access is approved later, use a scoped GitHub App and store its signing key and webhook secret in the deployer's secret store. |
| Assessment evaluator | Define the service settings in milestone 3. Keep evaluator dispatch credentials and assessment data in the control plane with per-job inputs supplied to the isolated runtime. |
| `GEMINI_API_KEY`, `GEMINI_MODEL`, `AI_PROVIDER` | Optional SkillForge server-side provider settings. Use deterministic AI in fixture runs and when unavailable. Confirm supported models when staging is configured. Browser BYOK uses tab memory and requires no server env value. |
| `JWT_SECRET`, `SKILLFORGE_DB_FILE`, `CLIENT_ORIGIN`, `VITE_API_BASE_URL` | Legacy SkillForge settings. Review their behavior during the baseline. The planned driver, session stack, PostgreSQL persistence and relative same-origin API replace these application settings. |

Only non-secret frontend settings may use `VITE_*`. Add a validated placeholder template alongside the runtime implementation. Never commit a live `.env` or include environment values in diagnostic output.
