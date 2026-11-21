# Code Context — 3-minute Hackathon Demo

## Before the demo

- Start the frontend and API, then open the Code Context page.
- Confirm GitHub API access. Public unauthenticated GitHub requests are rate limited; rehearse once and keep the fallback repository ready.
- Set `GEMINI_API_KEY` on the server to enable evidence-constrained answer and ADR prose rewriting. Without it, answers use deterministic evidence fallback and ADRs use an exact-source template.
- For persistent relationship traversal, configure `NEO4J_QUERY_URL`, `NEO4J_USERNAME`, and `NEO4J_PASSWORD`. Verify graph sync before presenting; without AuraDB, explain that graph retrieval is session-local.
- Keep a public, judge-chosen repository in mind, but do not promise its history contains a rationale.

## Three-minute run of show

### 0:00–0:25 — Start with the Kubernetes sample

Click **Run the sample walkthrough**. The app loads the real public `kubernetes/kubernetes` repository and asks the sample eviction-controller question. Point to the source citations, author/date fields, and conservative confidence. If the available records do not state why, the app must say the rationale is not established.

### 0:25–0:50 — Scrub the Decision Time Machine

Move the time slider. Show the selected retrieved record and what matching records surfaced later. Clarify that the timeline contains only sources retrieved for this question; a later record alone does not prove that an earlier decision was reversed.

### 0:50–1:40 — Run the Guardrail examples

Open **Before you merge** and click **Try a file with strong history**. The preset is selected from actual PR records and changed-file paths in the connected repository; it is not a fabricated finding. Expand the per-file row, inspect the source link, then use **Copy as PR comment** and show the Markdown preview.

Click **Try an unknown file**. It selects a real file from the repository tree that has no linked record in the retrieved history (and checks AuraDB too when indexed). Show **Unknown, history missing** and say plainly: unknown means history is missing, not that the change is safe. If the sample has no explicit-rationale PR or no unlinked file, the app reports that it could not find that live preset instead of inventing one.

Click **Try a change that re-adds removed code** to demonstrate the Déjà Vu Detector. It selects removed lines from an actual retrieved Kubernetes PR patch, then builds a clearly labeled constructed diff that adds those exact lines back. This constructed example is not a real PR. Show the “Possible repeat” card, confidence, highlighted textual match, and linked historical PR. Matching is textual; review the linked history to confirm intent. If no eligible patch is present in the retrieved sample, the preset reports that it could not construct the example.

### 1:35–2:05 — Export the evidence as an ADR

Generate an ADR from the answer’s retrieved sources. Show the Title, Status, Date, Context, Decision, Consequences, Evidence Links, Related People, and Related Incidents. Any unsupported section says **Not found in repository history**. Download the `.md` file or copy it. Point out whether the ADR used **Gemini evidence rewrite** or **Deterministic evidence template**.

### 2:05–3:00 — Let a judge choose a public repository

Connect the judge’s public GitHub repository, ask a question about a specific behavior or path, inspect the answer and source, then run a diff or PR through the Guardrail. Make no claim of safety when the graph has no matching files. If evidence is absent, use that abstention as the result.

## What the prototype does and does not prove

- The Guardrail compares exact changed paths with loaded evidence and, if AuraDB is indexed, graph results. It analyzes at most 50 files per run and reports the analyzed count.
- Déjà Vu checks actual added/removed patch lines against at most 10 retrieved historical PR patches per changed file. It normalizes whitespace, skips trivial lines, and requires two consecutive meaningful lines or one long line. Strong means three or more consecutive lines; Moderate means two lines or one long line. This is a textual match, not proof of intent or a bug. A no-match result explicitly does not mean safe.
- A file row is incident-linked only when a retrieved incident record shares that exact file or is explicitly connected to a shared-path record. Other linked records are shown as history. No link means **Unknown**, never safe.
- The timeline shows a small, ranked evidence set, not a full reconstruction of the repository at every date.
- ADR template mode quotes retrieved source text and marks unsupported sections. Gemini mode is instructed to rewrite only from the supplied sources and attaches source links; review it before treating the ADR as authoritative.
- The demo loads a bounded slice of public commits, pull requests, issues, and design records. It does not see private repositories, external incident systems, or history omitted by GitHub/API limits.
- Gemini improves prose but does not create evidence. The deterministic mode is the expected fallback when the key is absent or generation fails.
