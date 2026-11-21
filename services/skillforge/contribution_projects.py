"""Original contribution briefs and evidence-based planning."""

PROJECTS = (
    {
        "id": "accessible-issue-browser", "title": "Make an issue browser accessible",
        "difficulty": "Starter", "hours": 12, "skills": ["JavaScript", "Accessibility", "Testing"],
        "problem": "Keyboard users lose their place when filters replace an issue list.",
        "deliverable": "A focused patch with keyboard checks and a short before-and-after walkthrough.",
        "tasks": [
            {"id": "baseline", "title": "Map the keyboard journey",
             "acceptance": "Record the focus order and document one reproducible barrier using fixture data."},
            {"id": "patch", "title": "Fix focus and result announcements",
             "acceptance": "Focus stays predictable after filtering and the result count is announced."},
            {"id": "tests", "title": "Verify the fix and prepare a PR",
             "acceptance": "Cover keyboard navigation, empty results and narrow screens. Explain the trade-offs in the PR draft."},
        ],
    },
    {
        "id": "resilient-api-import", "title": "Make an API importer resilient",
        "difficulty": "Intermediate", "hours": 20, "skills": ["APIs", "Python", "Reliability", "Testing"],
        "problem": "A partial response or rate limit leaves a background import in an unclear state.",
        "deliverable": "A retry policy, a tested patch and a short recovery runbook.",
        "tasks": [
            {"id": "contract", "title": "Define retry and failure states",
             "acceptance": "Describe recoverable and terminal outcomes with synthetic provider responses."},
            {"id": "retries", "title": "Handle throttling and repeated delivery",
             "acceptance": "Honor retry hints, cap retries and keep a repeated job from duplicating results."},
            {"id": "runbook", "title": "Test failures and write the runbook",
             "acceptance": "Show fixture tests for throttling and partial results, then document how to retry safely."},
        ],
    },
    {
        "id": "decision-evidence-guide", "title": "Explain a change with repository evidence",
        "difficulty": "Starter", "hours": 10, "skills": ["Documentation", "System design", "Communication"],
        "problem": "A newcomer sees a design choice in the code and cannot tell why it was made.",
        "deliverable": "An architecture decision record with citations and a contributor guide.",
        "tasks": [
            {"id": "sources", "title": "Trace one design choice",
             "acceptance": "Identify the relevant file and link at least two dated history records where available."},
            {"id": "decision", "title": "Write the decision record",
             "acceptance": "Describe the context, trade-offs, open questions and any superseding decision."},
            {"id": "handoff", "title": "Prepare the documentation contribution",
             "acceptance": "Include a source checklist and a PR draft that a maintainer can review independently."},
        ],
    },
)


def roadmap(profile, skills, scans, assessments, projects):
    activity = profile.get("github_activity") or {}
    items = activity.get("items", [])
    projects = sorted(projects, key=lambda item: (
        item["id"] != profile.get("contribution_project"),
        -len(set(item["skills"]).intersection(skills)),
    ))
    active = projects[0]
    steps = []

    def add(title, reason, citation=None, project=None):
        steps.append({"title": title, "reason": reason, "citation": citation, "project": project})

    open_pr = next((item for item in items if item["kind"] == "open pull request" and not item.get("draft")), None)
    draft = next((item for item in items if item["kind"] == "open pull request" and item.get("draft")), None)
    merged = next((item for item in items if item["kind"] == "merged pull request"), None)
    issue = next((item for item in items if item["kind"] == "open issue"), None)
    if open_pr:
        add("Follow up on your open pull request",
            "Check review comments and CI, then document what changed.", open_pr)
    elif draft:
        add("Scope your draft pull request",
            "Write acceptance criteria and add a reproducible check before requesting review.", draft)
    elif merged:
        add("Build on a merged contribution",
            "Record the result and use it to propose a small follow-up to maintainers.", merged)
    elif issue:
        add("Turn an issue into a scoped proposal",
            "List the expected outcome and agree on the scope before implementing it.", issue)

    if task := next((task for task in active["tasks"] if task["id"] not in active["completed"]), None):
        overlap = [skill for skill in active["skills"] if skill in skills]
        reason = task["acceptance"]
        if overlap:
            reason += " Fits your target skills in " + ", ".join(overlap) + "."
        add(task["title"], reason, project=active["id"])
    else:
        add("Prepare a contributor handoff", "Collect your milestone evidence and draft a maintainer-friendly PR.",
            project=active["id"])

    if scans:
        project = scans[0]
        add("Use a repository scan to scope the next change",
            "Open the scan and choose a small improvement with a testable outcome. "
            "A repository scan records analysis activity.", project)
    else:
        add("Choose a repository and read its contributing guide",
            "There are no completed repository scans in this workspace yet.")
    if assessments:
        add("Add a test to your contribution",
            f"You have {assessments} distinct assessed exercises. Apply one relevant technique to a regression test.")
    else:
        add("Practice a scenario relevant to your project",
            "A completed assessment can provide additional evidence for your portfolio.")
    return {"projects": projects, "steps": steps, "activity": activity or None,
            "scans": scans, "assessments": assessments, "hours": profile["hours"]}
