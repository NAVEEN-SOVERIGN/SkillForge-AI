
from .analysis import JS, parse_js, parse_python
from .scoring import half_up

VERSION = "scenario-scoring-v1"
WEIGHTS = {
    "correctness": ("Functional correctness", 40),
    "efficiency": ("Efficiency signal", 20),
    "edge": ("Edge cases", 15),
    "quality": ("Static code quality", 10),
    "explanation": ("Problem-solving explanation", 15),
}
CATEGORIES = {
    "Example": "correctness", "Functional": "correctness",
    "Edge case": "edge", "Boundary case": "edge", "Large input": "efficiency",
}
LEVELS = ("Foundations", "Intermediate", "Advanced")


def assess_submission(cases, language, source):
    groups = {key: [] for key in WEIGHTS}
    for row in cases:
        if row["category"] in CATEGORIES:
            groups[CATEGORIES[row["category"]]].append(row["status"] == "passed")
    parsed = parse_python(source) if language == "python" else parse_js(source, JS)
    quality = half_up(10 * sum((parsed.syntax_ok, len(source.splitlines()) <= 150 and
                               all(len(line) <= 140 for line in source.splitlines()))), 2)
    values = {
        key: half_up(WEIGHTS[key][1] * sum(results), len(results)) if results else None
        for key, results in groups.items()
    }
    values["quality"] = quality
    # A machine-checked submission supplies no validated evidence of the learner's reasoning.
    values["explanation"] = None
    breakdown = [{"id": key, "name": name, "points": values[key], "max": maximum}
                 for key, (name, maximum) in WEIGHTS.items()]
    total = sum(item["points"] for item in breakdown if item["points"] is not None)
    measured = sum(item["max"] for item in breakdown if item["points"] is not None)
    return {"version": VERSION, "points": total, "measured": measured, "max": 100,
            "normalized": half_up(1000 * total, measured), "criteria": breakdown}


def best_assessments(rows):
    best = {}
    for row in rows:
        assessment = row["result"].get("assessment")
        if not assessment or assessment.get("version") != VERSION:
            continue
        previous = best.get(row["problem"])
        if not previous or assessment["normalized"] > previous["normalized"]:
            best[row["problem"]] = assessment
    return best


def next_problem(best, catalog):
    passed_by_level = {
        level: [key for key, score in best.items() if key in catalog and catalog[key].difficulty == level
                and score["normalized"] >= 800]
        for level in LEVELS
    }
    level = next((level for level in LEVELS if len(passed_by_level[level]) < 3), LEVELS[-1])
    eligible = [problem for problem in catalog.values() if problem.difficulty == level
                and problem.id not in passed_by_level[level]]
    unseen = next((item for item in eligible if item.id not in best), None)
    candidate = unseen or (eligible[0] if eligible else None)
    return {"problem": candidate.id, "difficulty": level} if candidate else None


def developer_index(engineering, assessments):
    problem_solving = half_up(sum(entry["normalized"] for entry in assessments.values()), len(assessments)) \
        if assessments else None
    overall = half_up(60 * engineering + 40 * problem_solving, 100) \
        if engineering is not None and problem_solving is not None else None
    return {"engineering": engineering, "problemSolving": problem_solving, "index": overall,
            "problems": len(assessments),
            "provisional": overall is None or len(assessments) < 3 or any(
                item["measured"] != item["max"] for item in assessments.values()
            )}
