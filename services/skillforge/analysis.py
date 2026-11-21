
import ast
import posixpath
import re
from dataclasses import dataclass, field

import tree_sitter_javascript
import tree_sitter_typescript
from tree_sitter import Language, Parser

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
    scopes: list = field(default_factory=list)
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
                result.scopes.append((node.name, node.lineno, node.end_lineno or node.lineno))
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
                result.scopes.append((name, line(target), target.end_point.row + 1))
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


def script_target(base, paths):
    stem = posixpath.splitext(base)[0]
    return next((item for item in [base, *(stem + ext for ext in EXTENSIONS),
                 *(base + "/index" + ext for ext in EXTENSIONS)] if item in paths), None)


def alias_target(spec, path, paths, aliases):
    configs = sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True)
    for config, options in configs:
        folder = posixpath.dirname(config)
        if folder and not path.startswith(folder + "/"):
            continue
        for key, replacements in options["paths"].items():
            if not isinstance(replacements, list) or len(key) > 150 or key.count("*") > 1:
                continue
            pattern = re.escape(key).replace(r"\*", "(.*)")
            match = re.fullmatch(pattern, spec)
            if not match:
                continue
            capture = match.group(1) if match.lastindex else ""
            for replacement in replacements[:8]:
                if not isinstance(replacement, str) or len(replacement) > 200:
                    continue
                candidate = posixpath.normpath(posixpath.join(folder, options["base"], replacement.replace("*", capture)))
                if target := script_target(candidate, paths):
                    return target, "file"
            return spec, "unresolved"
    return None


def resolve(spec, path, paths, aliases):
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
        target = script_target(base, paths)
        return (target, "file") if target else (spec, "unresolved")
    if alias := alias_target(spec, path, paths, aliases):
        return alias
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
            dest, kind = resolve(spec, path, snapshot["paths"], snapshot.get("aliases", {}))
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
                caller = next((function for function, start, end in current.scopes if start <= line <= end), None)
                edge(path, dest, "calls across files · inferred", path, line)
                edge(path + "::" + caller if caller else path, dest + "::" + symbol, "calls · inferred", path, line)
            else:
                unresolved += 1
    return {
        "nodes": list(nodes.values()), "edges": list(edges.values()), "unresolved": unresolved, "limited": omitted,
    }, parsed
