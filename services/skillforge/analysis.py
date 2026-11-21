
import ast
import posixpath
import re
from collections import Counter
from dataclasses import dataclass, field

import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Parser

from .github import source_href, test_path

JS = Language(tree_sitter_javascript.language())
TS = Language(tree_sitter_typescript.language_typescript())
TSX = Language(tree_sitter_typescript.language_tsx())
EXTENSIONS = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts")
MAX_NODES = 850
MAX_EDGES = 1800


@dataclass
class Parsed:
    imports: list = field(default_factory=list)
    definitions: dict = field(default_factory=dict)
    calls: list = field(default_factory=list)
    exported: dict = field(default_factory=dict)
    syntax_ok: bool = True


def parse_python(code):
    result = Parsed()
    try:
        module = ast.parse(code)
    except (SyntaxError, ValueError, RecursionError):
        result.syntax_ok = False
        return result

    for node in module.body:
        match node:
            case ast.FunctionDef() | ast.AsyncFunctionDef():
                result.definitions[node.name] = node.lineno
                result.exported[node.name] = node.name
            case ast.Import():
                for item in node.names:
                    alias = item.asname or item.name.split(".")[0]
                    result.imports.append((item.name, alias, "*", node.lineno))
            case ast.ImportFrom():
                for item in node.names:
                    result.imports.append(("." * node.level + (node.module or ""),
                                           item.asname or item.name, item.name, node.lineno))
    for node in ast.walk(module):
        if isinstance(node, ast.Call):
            match node.func:
                case ast.Name(id=name):
                    result.calls.append((name, None, node.lineno))
                case ast.Attribute(value=ast.Name(id=name), attr=attr):
                    result.calls.append((name, attr, node.lineno))
    return result


def parse_js(code, language):
    result = Parsed()
    source = code.encode()
    tree = Parser(language).parse(source)
    result.syntax_ok = not tree.root_node.has_error

    def value(node):
        return source[node.start_byte:node.end_byte].decode(errors="replace") if node else ""

    def line(node):
        return node.start_point.row + 1

    for statement in tree.root_node.named_children:
        if statement.type == "import_statement":
            spec = value(statement.child_by_field_name("source"))[1:-1]
            if not spec:
                continue
            clause = next((child for child in statement.named_children if child.type == "import_clause"), None)
            result.imports.append((spec, None, None, line(statement)))
            if clause:
                for child in clause.named_children:
                    if child.type == "identifier":
                        result.imports.append((spec, value(child), "default", line(statement)))
                    elif child.type == "namespace_import":
                        result.imports.append((spec, value(child.named_children[-1]), "*", line(statement)))
                    elif child.type == "named_imports":
                        for item in child.named_children:
                            original = value(item.child_by_field_name("name"))
                            alias = value(item.child_by_field_name("alias")) or original
                            result.imports.append((spec, alias, original, line(statement)))
            continue

        root = statement
        exported = statement.type == "export_statement"
        if exported:
            root = statement.child_by_field_name("declaration") or statement
            clause = next((child for child in statement.named_children if child.type == "export_clause"), None)
            if clause and not statement.child_by_field_name("source"):
                for item in clause.named_children:
                    name = value(item.child_by_field_name("name"))
                    alias = value(item.child_by_field_name("alias")) or name
                    if name:
                        result.exported[alias] = name
        targets = [root] if root.type in {"function_declaration", "generator_function_declaration"} else []
        if root.type in {"lexical_declaration", "variable_declaration"}:
            targets = [
                item for item in root.named_children if (fn := item.child_by_field_name("value"))
                and fn.type in {"arrow_function", "function_expression", "generator_function"}
                and item.child_by_field_name("name").type == "identifier"
            ]
        for target in targets:
            name = value(target.child_by_field_name("name"))
            if name:
                result.definitions[name] = line(target)
                if exported:
                    is_default = any(child.type == "default" for child in statement.children)
                    result.exported["default" if is_default else name] = name

    queue = [tree.root_node]
    while queue and len(result.calls) < 2500:
        node = queue.pop()
        if node.type == "call_expression":
            fn = node.child_by_field_name("function")
            arguments = node.child_by_field_name("arguments")
            if value(fn) == "require" and arguments and arguments.named_child_count == 1:
                arg = arguments.named_children[0]
                if arg.type == "string":
                    result.imports.append((value(arg)[1:-1], None, None, line(node)))
            if fn and fn.type == "identifier":
                result.calls.append((value(fn), None, line(node)))
            if fn and fn.type == "member_expression":
                obj = fn.child_by_field_name("object")
                prop = fn.child_by_field_name("property")
                if obj and obj.type == "identifier" and prop:
                    result.calls.append((value(obj), value(prop), line(node)))
        queue.extend(reversed(node.named_children))
    return result


def resolve(spec, path, paths):
    folder = posixpath.dirname(path)
    if path.endswith(".py"):
        levels = len(spec) - len(spec.lstrip("."))
        module = spec[levels:].replace(".", "/")
        if levels:
            base = posixpath.normpath(posixpath.join(folder, *([".."] * (levels - 1)), module))
            candidates = [base]
        else:
            candidates = [module, "src/" + module]
        for candidate in candidates:
            for item in (candidate + ".py", posixpath.join(candidate, "__init__.py")):
                if item in paths:
                    return item, "file"
        return (spec, "unresolved") if levels else (spec.split(".")[0], "package")

    if spec.startswith("."):
        base = posixpath.normpath(posixpath.join(folder, spec))
        stem = posixpath.splitext(base)[0]
        for item in [base, *(stem + ext for ext in EXTENSIONS), *(base + "/index" + ext for ext in EXTENSIONS)]:
            if item in paths:
                return item, "file"
        return spec, "unresolved"
    if spec.startswith(("@/", "#", "/")):
        return spec, "unresolved"
    parts = spec.split("/")
    return "/".join(parts[:2]) if spec.startswith("@") else parts[0], "package"


def structure(snapshot):
    sources = snapshot["sources"]
    parsed = {
        path: parse_python(code) if path.endswith(".py") else parse_js(
            code, TSX if path.endswith(".tsx") else TS if path.endswith((".ts", ".mts", ".cts")) else JS,
        )
        for path, code in sources.items()
    }
    nodes, edges = {}, {}
    unresolved = 0
    omitted = False

    def node(identifier, label, kind, path=None, line=None):
        nonlocal omitted
        if identifier not in nodes:
            if len(nodes) >= MAX_NODES:
                omitted = True
                return
            nodes[identifier] = {"id": identifier, "label": label, "kind": kind, "path": path, "line": line}

    def edge(source, target, kind, path, line=None):
        nonlocal omitted
        key = (source, target, kind)
        if source not in nodes or target not in nodes or key in edges:
            return
        if len(edges) >= MAX_EDGES:
            omitted = True
            return
        edges[key] = {"source": source, "target": target, "kind": kind, "path": path, "line": line}

    for path, current in parsed.items():
        node(path, path.rsplit("/", 1)[-1], "file", path)
        parts = path.split("/")
        for index in range(len(parts) - 1):
            folder = "/".join(parts[:index + 1]) + "/"
            node(folder, parts[index], "folder")
            if index:
                edge("/".join(parts[:index]) + "/", folder, "contains", path)
        if len(parts) > 1:
            edge("/".join(parts[:-1]) + "/", path, "contains", path)
        for name, line in current.definitions.items():
            identifier = path + "::" + name
            node(identifier, name, "function", path, line)
            edge(path, identifier, "defines", path, line)

    for path, current in parsed.items():
        bindings = {}
        for spec, local, name, line in current.imports:
            dest, kind = resolve(spec, path, snapshot["paths"])
            if kind == "unresolved":
                identifier = "unresolved:" + spec
                unresolved += 1
            else:
                identifier = dest if kind == "file" else "package:" + dest
            node(identifier, dest.rsplit("/", 1)[-1] if kind == "file" else dest, kind,
                 dest if kind == "file" else None)
            edge(path, identifier, "imports " + kind, path, line)
            if local:
                bindings[local] = (dest, kind, name)
        for root, member, line in current.calls:
            if root not in bindings:
                continue
            dest, kind, imported = bindings[root]
            if kind != "file":
                continue
            other = parsed.get(dest)
            name = member if imported == "*" else imported if member is None else None
            symbol = other.exported.get(name) if other else None
            if symbol and symbol in other.definitions:
                edge(path, dest + "::" + symbol, "calls · inferred", path, line)
            else:
                unresolved += 1
    return {
        "nodes": list(nodes.values()), "edges": list(edges.values()), "unresolved": unresolved, "limited": omitted,
    }, parsed


RUBRIC = "common-practices-v1"
DIMENSIONS = {
    "Reliability": 25, "Maintainability": 25, "Testing and CI": 20,
    "Dependency hygiene": 15, "Performance hygiene": 10, "Documentation": 5,
}


def quality(snapshot, parsed):
    paths = snapshot["paths"]
    sources = snapshot["sources"]
    tests = [path for path in paths if test_path(path)]
    ci = sorted(path for path in paths if path.startswith(".github/workflows/") and path.endswith((".yaml", ".yml")))
    readmes = sorted(path for path in paths if path.lower() in {"readme", "readme.md", "readme.rst"})
    projects = sorted(path for path in paths if path.rsplit("/", 1)[-1] in {
        "package.json", "pyproject.toml", "requirements.txt", "Pipfile",
    })
    locks = sorted(path for path in paths if path.rsplit("/", 1)[-1] in {
        "package-lock.json", "pnpm-lock.yaml", "yarn.lock", "bun.lock", "uv.lock", "poetry.lock", "Pipfile.lock",
    })
    invalid = [(path, 1) for path, item in parsed.items() if not item.syntax_ok]
    long = [(path, 1) for path, code in sources.items() if len(code.splitlines()) > 450]
    todo = [
        (path, number) for path, code in sources.items()
        for number, line in enumerate(code.splitlines(), 1)
        if re.search(r"^\s*(?:#|//)\s*(?:FIXME|HACK)\b", line)
    ]
    sync = [
        (path, number) for path, code in sources.items() if not test_path(path) and not path.endswith(".py")
        for number, line in enumerate(code.splitlines(), 1)
        if re.search(r"\b(?:readFileSync|writeFileSync|execFileSync)\s*\(", line)
    ]
    findings = []

    def check(dimension, title, weight, passed, detail, evidence=None):
        path, line = evidence or (None, None)
        findings.append({
            "dimension": dimension, "title": title, "points": weight if passed else 0, "max": weight,
            "state": "met" if passed else "review", "detail": detail, "path": path, "line": line,
            "url": source_href(snapshot["repo"], snapshot["revision"], path, line) if path else None,
        })

    check("Reliability", "Supported source parses", 25, not invalid,
          "Parser signal across the sample. Review parse errors before inferring a broken build.", next(iter(invalid), None))
    check("Maintainability", "File size stays manageable", 15, not long,
          "Review sampled files over 450 lines for focused modules.", next(iter(long), None))
    check("Maintainability", "Maintenance markers", 10, not todo,
          "Review explicit FIXME or HACK markers in sampled source.", next(iter(todo), None))
    check("Testing and CI", "Test files are present", 12, bool(tests),
          "File naming shows test presence. Assertion quality and test results require separate evidence.",
          (sorted(tests)[0], 1) if tests else None)
    check("Testing and CI", "GitHub Actions configuration", 8, bool(ci),
          "Looks for a checked-in workflow. A file alone does not establish that CI passes.", (ci[0], 1) if ci else None)
    check("Dependency hygiene", "Dependency manifest", 5, bool(projects),
          "Check for declared project dependencies.", (projects[0], 1) if projects else None)
    check("Dependency hygiene", "Dependency lockfile", 10, bool(locks),
          "Check for a lockfile supporting reproducible installs.", (locks[0], 1) if locks else None)
    if any(not path.endswith(".py") for path in sources):
        check("Performance hygiene", "Blocking JavaScript I/O", 10, not sync,
              "Review synchronous file or process calls in server hot paths and scripts.", next(iter(sync), None))
    check("Documentation", "Root README", 5, bool(readmes),
          "Check for a root entry point for setup and usage documentation.", (readmes[0], 1) if readmes else None)
    counts = Counter("Python" if path.endswith(".py") else "JavaScript / TypeScript" for path in sources)
    cohort = "Mixed" if len(counts) > 1 else next(iter(counts), None)
    percent = min(100, round(100 * len(sources) / max(1, snapshot["eligible"])))
    dimensions = [
        {"name": name, "points": sum(item["points"] for item in findings if item["dimension"] == name),
         "max": sum(item["max"] for item in findings if item["dimension"] == name)}
        for name in DIMENSIONS
    ]
    maximum = sum(item["max"] for item in findings)
    rankable = bool(sources and percent >= 75 and not snapshot["truncated"])
    return {
        "version": RUBRIC, "score": round(100 * sum(item["points"] for item in findings) / maximum) if sources else None,
        "rankable": rankable, "cohort": cohort, "dimensions": dimensions, "findings": findings,
        "coverage": {"analyzed": len(sources), "eligible": snapshot["eligible"], "percent": percent,
                     "total": snapshot["total_files"], "truncated": snapshot["truncated"]},
    }
