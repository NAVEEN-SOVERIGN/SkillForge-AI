# Product requirements

## Product and users

SkillForge Integrated helps students, developers, and working professionals evaluate their GitHub projects, understand where the code needs work, and practice the underlying skills through coding assessments based on real-world scenarios. Users can turn a documented improvement or an assessment result into portfolio evidence and connect it to a target role.

## Primary journey

1. Paste a GitHub repository URL or connect GitHub and pick one or more repositories. Review what the app can access and start an analysis.
2. Review the project rubric, then open a 1,000-point scorecard and rankings for comparable repositories. Inspect the criteria, cited findings, amount of code analyzed, limitations, and fixes with the largest expected impact. Re-score a new commit and compare it with the previous revision.
3. Open the code structure graph to see how files communicate through imports and calls. Select a file or function to inspect incoming and outgoing connections and jump to the linked source. Open decision history when it explains a connection or quality finding. Practice the underlying skill through a scenario such as reconciling stock updates or calculating peak support coverage from overlapping shifts.
4. Submit code against a clear input/output contract. See sample test feedback, hidden test categories, execution limits, and an explanation after submission. Review your results alongside the repository scorecard.
5. Optionally set a target role or paste a job description, attach evaluated evidence to your portfolio, review suggested actions, and export a career-readiness report.

## Requirements and acceptance

| ID | Capability | Acceptance criteria |
| --- | --- | --- |
| R1 | Identity and settings | GitHub, Google, and verified email sign-in work in staging. Email supports sign-up verification, optional sign-in verification, password and profile changes, and deletion with reauthentication. A deletion revokes sessions immediately and durably schedules cleanup of career data and saved indexes; repeat requests are handled safely. A sample session uses its own data. |
| R2 | Career baseline | Role catalog, onboarding, profile, resume extraction with user review, JD extraction, opportunity matching, gap analysis, roadmaps, weekly scheduling and activities share one account and skill vocabulary. Unsupported extracted requirements are labeled for review. |
| R3 | Repository workspace and code structure graph | Import with notice and consent. Show revision, date, coverage, job state, and retry time on throttling. Make the interactive code structure graph the default repository view. Show folders, files, functions, and external packages as distinct node types. Use directed, labeled edges for file imports, package imports and cross-file function calls. Keep decision history available as a secondary graph view. Include a source reader and local scratch editor. Signed-in users can explicitly save, reopen, re-index, and delete. Temporary workspaces expire. |
| R4 | Evidence assistant and decision review | Rank relevant history and source records including commits, PRs, reviews, issues, discussions, ADRs, and symbols where available. Each answer has inspectable sources or abstains. Code alone can support claims about behavior. Claims about intent require historical evidence. Explicit supersession links show both records and the relationship basis. Timeline playback filters evidence by date. A read-only PR review shows cited historical decisions and possible textual repeats, with explicit unknowns. Users can copy the review or export a sourced ADR draft. Before a hosted AI request, show which repository data will be sent and obtain consent. |
| R5 | Projects and proof | Combine Project Forge, projects and milestones, Portfolio Intelligence, Resume Truth, proof challenges and assessments. Capture the repo revision, artifact, citation, asserted contribution and checks. Repository presence and AI review alone grant no verified skill credit. Static checks are labeled with their actual method. Answer keys and grading remain server-side. |
| R6 | Readiness and evidence | One ledger links requirements, skills, proof and recommendations. Category, source, limitations, evaluation date, deduplication key and scoring version are visible where applicable. Dashboard, opportunity views, skill radar and PDF agree for the same snapshot. The score displays weighted coverage, assessment and project components and the applied policy. |
| R7 | Actions and practice | Opportunity gaps and portfolio findings can propose a challenge or governed action. Approval, dismissal and completion have explicit, audited transitions. The tracker, coaching, interview practice, readiness sprint and career simulations reuse account data with scenario assumptions and outcomes visible. Simulated changes never mutate the current baseline. |
| R8 | Trust and operations | A non-owner cannot view, modify, export, or delete another workspace's data. Source previews are bounded and transmitted on demand. Provider keys stay out of telemetry. GitHub throttling and failed AI calls surface recoverable states. Reports and core planning remain usable during citation assistant, mail, or graph-provider outages where their dependencies allow. |
| R9 | GitHub picker and scoring jobs | Support pasted public GitHub URLs and an opt-in GitHub connection that lists eligible repositories. Show the selected branch and evaluated commit SHA. Queue scoring with deduplication and visible progress. Disconnect stops new access. Scope supported repository access to the user's explicit selection. |
| R10 | Code quality ranking | Score each eligible commit on a versioned, project-aware 1,000-point rubric. Preview applicable, excluded and uncertain criteria, then publish measured scores, weights, commit-pinned evidence, confidence and coverage. Compare compatible project, stack and measured-rubric cohorts. Tie equal scores and label insufficient coverage as unranked. Compare repeat scans at the same commit and changes over time. |
| R11 | Scenario-based coding tests | Provide a curated catalog of real-life tasks that exercise data structures and algorithms, with sample cases, hidden edge and performance cases, language choice, submission history, and feedback. Judge with versioned problem data and publish problem topic and walkthrough after completion. Suggest relevant practice from repo findings where the connection is specific. |

## Code quality scoring

[Adaptive scoring](SCORING.md) defines project context detection, criteria review, normalization, grade thresholds, coverage, confidence and ranking rules.

## Coding assessment design

Start with a proposed pilot of 12 tasks across arrays and hash maps, sorting and intervals, heaps, graph traversal, and dynamic programming. Separate the story from the test contract and specify constraints so learners can select the right approach. Include starter code, accessible examples, deterministic hidden tests, and resource bounds. Record the problem version, language, runtime, pass count and feedback. Keep hidden inputs and reference solutions server-side. Keep assessment results separate from repository quality scores and let eligible assessment evidence contribute to career readiness under its own rules.

## Code structure graph acceptance

- Start with a folder and file overview. Expand to functions and dependencies on demand. Search by path or symbol, filter by edge and node type, and select a node to see its callers, callees, imports and dependents where resolved. Each edge shows its direction and links to the import statement or call site in the evaluated commit.
- Proposed initial support is JavaScript, TypeScript and Python. Resolve supported aliases, relative imports and imported symbols from source and project metadata. Mark unresolved or ambiguous calls explicitly. Dynamic dispatch, reflection, runtime data and external API activity require their own evidence. Partial scans show what was analyzed and where graph coverage ends.
- Verify against fixtures with a local file import, an external package, an aliased import, a cross-file call and an ambiguous dynamic call. The graph exposes each resolved connection in both directions of navigation. A keyboard-accessible list and detail view presents the same relationships. Repo findings deep-link to the relevant graph node when the scan resolved it.

## Product boundaries

- Launch with public GitHub repositories and individual workspaces. Enable private GitHub selection only after a separate scoped GitHub App integration, privacy review, revocation checks and default-off external AI transfer pass staging. Team administration, paid plans and other hosts are outside this release.
- Imported repositories and editor drafts are analyzed statically. Run scenario-test submissions only in a dedicated short-lived evaluator with no network access, secrets, or access to workspace stores. Existing static proof challenges retain their original evaluation path and labels.
- Readiness measures recorded evidence against a versioned target. It carries no hiring prediction. A repository file or contribution claim is weak evidence until evaluated against a rubric.
- An uploaded resume and AI transfer have distinct notices and consent events. Users can review extracted fields before saving and discard the source upload after extraction by default.

## Proposed beta measures

- Measure first scored repo, findings opened, re-scores after a new commit, and first completed test. Track the funnel through event names and opaque IDs without collecting resume text, source contents or prompts in analytics.
- Initial pilot targets are at least 80% of ten moderated participants completing repo import, interpreting their lowest dimension and submitting a test without help. Compare rubric results with independent reviewer ratings before opening the pilot.
- Release acceptance requires all R1–R11 scenarios to pass in staging, including ranking integrity, judge isolation, provider outages, account cleanup and workspace isolation. See the [build plan](BUILD_PLAN.md) for operational gates.
