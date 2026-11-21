# API and worker instructions

- Scope objects to the authenticated account or temporary workspace at the query boundary. Validate origin and session on mutations. Revoke access immediately on account deletion and reconcile cleanup across PostgreSQL and Neo4j with durable jobs.
- Use bounded GitHub requests and source reads. Confirm host after redirects, stream files, reserve quota before import, handle reset headers and avoid unmeasured history fan-out. Store graph metadata and durable citation pointers. Fetch full source on demand.
- Make migrations, retries and job completion idempotent. Use leases and transactions for ownership-sensitive transitions, approval and evidence deduplication. Simulations are read-only against current readiness state.
- Treat repository and provider content as untrusted. Validate model output and citation allowlists. Version the rubric and analyzers. Compute scoring and eligibility server-side with reproducible fixture checks. Keep unresolved call sites and coverage limits explicit.
- Analyze imported code statically. Route standalone coding test submissions to the isolated no-network evaluator with resource caps and structured output. Expose only the current test input to the running submission. Keep the test corpus and answers in the evaluator control plane, and prevent hidden-case content from reaching the browser through feedback or captured output.
- Validate environment settings at startup, use secret redaction and report dependency health without credentials. Test concurrency, retry, isolation and deletion for the behavior changed.
