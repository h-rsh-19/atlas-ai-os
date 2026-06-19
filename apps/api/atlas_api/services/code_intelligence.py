from __future__ import annotations

import ast
import importlib.util
import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from uuid import uuid4

from atlas_api.schemas import (
    CodeGraph,
    CodeGraphEdge,
    CodeGraphNode,
    CodeRiskItem,
    CodeRiskReport,
    CodeSymbol,
    RepoFile,
    RepoProject,
)

SOURCE_LANGUAGES = {"Python", "TypeScript", "JavaScript", "Go", "Rust", "Java"}
TEST_MARKERS = ("test", "spec")
TODO_PATTERN = re.compile(r"\b(TODO|FIXME|HACK)\b", re.IGNORECASE)
JS_IMPORT_PATTERN = re.compile(
    r"(?:import\s+(?:.+?\s+from\s+)?|export\s+.+?\s+from\s+|require\()\s*['\"]([^'\"]+)['\"]",
    re.MULTILINE,
)
JS_FUNCTION_PATTERN = re.compile(
    r"(?P<export>export\s+)?(?:(?:async\s+)?function\s+"
    r"(?P<fn>[A-Za-z_$][\w$]*)|(?:const|let|var)\s+"
    r"(?P<const>[A-Za-z_$][\w$]*)\s*=\s*(?:async\s*)?\([^)]*\)\s*=>)",
    re.MULTILINE,
)
JS_CLASS_PATTERN = re.compile(r"(?P<export>export\s+)?class\s+(?P<name>[A-Za-z_$][\w$]*)")
JS_ROUTE_PATTERN = re.compile(r"export\s+(?:async\s+)?function\s+(GET|POST|PUT|PATCH|DELETE)")


@dataclass
class ParsedFile:
    path: str
    language: str | None
    size_bytes: int
    lines: list[str]
    imports: list[str] = field(default_factory=list)
    symbols: list[dict[str, object]] = field(default_factory=list)
    calls: list[tuple[str, str]] = field(default_factory=list)


def analyze_repository(project: RepoProject) -> tuple[list[CodeSymbol], CodeGraph, CodeRiskReport]:
    generated_at = datetime.now(UTC)
    parsed_files = [_parse_file(file) for file in project.file_tree if _is_source_or_doc(file)]
    symbols = _build_symbols(project.id, parsed_files, generated_at)
    graph = _build_graph(project, parsed_files, symbols, generated_at)
    risk_report = _build_risk_report(project, parsed_files, graph, generated_at)
    return symbols, graph, risk_report


def parser_provider() -> str:
    providers = ["python-ast", "typescript/javascript-heuristics"]
    if importlib.util.find_spec("tree_sitter"):
        providers.append("tree-sitter-runtime-detected")
    if importlib.util.find_spec("networkx"):
        providers.append("networkx-runtime-detected")
    else:
        providers.append("local-graph-algorithms")
    return " + ".join(providers)


def _parse_file(file: RepoFile) -> ParsedFile:
    lines = (file.preview or "").splitlines()
    parsed = ParsedFile(
        path=file.path,
        language=file.language,
        size_bytes=file.size_bytes,
        lines=lines,
    )
    if file.language == "Python":
        _parse_python(parsed, file.preview or "")
    elif file.language in {"TypeScript", "JavaScript"}:
        _parse_javascript_like(parsed, file.preview or "")
    elif file.language in {"Markdown", "JSON", "TOML", "YAML"}:
        parsed.imports.extend(_extract_dependency_mentions(parsed.path, file.preview or ""))
    return parsed


def _parse_python(parsed: ParsedFile, content: str) -> None:
    try:
        tree = ast.parse(content)
    except SyntaxError:
        parsed.symbols.append(
            {
                "name": Path(parsed.path).stem,
                "kind": "module",
                "line_start": 1,
                "line_end": max(1, len(parsed.lines)),
                "signature": None,
                "evidence": _line(parsed.lines, 1),
                "metadata": {"parse_error": "syntax_error"},
            }
        )
        return

    parent_stack: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            parsed.imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = "." * node.level + (node.module or "")
            parsed.imports.append(module)
        elif isinstance(node, ast.ClassDef):
            parsed.symbols.append(_python_symbol(parsed, node, "class"))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "route" if _has_route_decorator(node) else "function"
            parsed.symbols.append(_python_symbol(parsed, node, kind))

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            parent_stack.append(node.name)
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    call_name = _python_call_name(child)
                    if call_name:
                        parsed.calls.append((node.name, call_name))
            parent_stack.pop()


def _python_symbol(
    parsed: ParsedFile,
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef,
    kind: str,
) -> dict[str, object]:
    end_line = getattr(node, "end_lineno", node.lineno)
    signature = None
    decorators = [_decorator_name(item) for item in getattr(node, "decorator_list", [])]
    route_info = _route_decorator_info(getattr(node, "decorator_list", []))
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        args = [arg.arg for arg in node.args.args]
        signature = f"{node.name}({', '.join(args)})"
    return {
        "name": node.name,
        "kind": kind,
        "line_start": node.lineno,
        "line_end": end_line,
        "signature": signature,
        "evidence": _line(parsed.lines, node.lineno),
        "metadata": {
            "decorators": decorators,
            **route_info,
        },
    }


def _parse_javascript_like(parsed: ParsedFile, content: str) -> None:
    parsed.imports.extend(match.group(1) for match in JS_IMPORT_PATTERN.finditer(content))

    for match in JS_CLASS_PATTERN.finditer(content):
        line = _line_number(content, match.start())
        parsed.symbols.append(
            {
                "name": match.group("name"),
                "kind": "class",
                "line_start": line,
                "line_end": line,
                "signature": f"class {match.group('name')}",
                "evidence": _line(parsed.lines, line),
                "metadata": {"exported": bool(match.group("export"))},
            }
        )

    for match in JS_FUNCTION_PATTERN.finditer(content):
        name = str(match.group("fn") or match.group("const"))
        line = _line_number(content, match.start())
        kind = "component" if name[:1].isupper() else "function"
        parsed.symbols.append(
            {
                "name": name,
                "kind": kind,
                "line_start": line,
                "line_end": line,
                "signature": _line(parsed.lines, line).strip()[:160],
                "evidence": _line(parsed.lines, line),
                "metadata": {"exported": bool(match.group("export"))},
            }
        )

    for match in JS_ROUTE_PATTERN.finditer(content):
        line = _line_number(content, match.start())
        parsed.symbols.append(
            {
                "name": match.group(1),
                "kind": "route",
                "line_start": line,
                "line_end": line,
                "signature": f"{match.group(1)} {parsed.path}",
                "evidence": _line(parsed.lines, line),
                "metadata": {
                    "http_method": match.group(1),
                    "route_path": _next_route_from_path(parsed.path),
                },
            }
        )

    known_calls = re.findall(r"\b([A-Za-z_$][\w$]*)\s*\(", content)
    for symbol in parsed.symbols:
        for call in known_calls[:80]:
            if call != symbol["name"]:
                parsed.calls.append((str(symbol["name"]), call))


def _build_symbols(
    project_id: str,
    parsed_files: list[ParsedFile],
    generated_at: datetime,
) -> list[CodeSymbol]:
    symbols: list[CodeSymbol] = []
    for parsed in parsed_files:
        for symbol in parsed.symbols:
            symbols.append(
                CodeSymbol(
                    id=f"sym_{uuid4().hex[:16]}",
                    project_id=project_id,
                    name=str(symbol["name"]),
                    kind=str(symbol["kind"]),
                    file_path=parsed.path,
                    language=parsed.language,
                    line_start=int(symbol["line_start"]),
                    line_end=int(symbol["line_end"]),
                    signature=symbol.get("signature") if symbol.get("signature") else None,
                    evidence=str(symbol.get("evidence") or ""),
                    metadata=dict(symbol.get("metadata") or {}),
                    created_at=generated_at,
                )
            )
    return symbols


def _build_graph(
    project: RepoProject,
    parsed_files: list[ParsedFile],
    symbols: list[CodeSymbol],
    generated_at: datetime,
) -> CodeGraph:
    nodes: dict[str, CodeGraphNode] = {}
    edges: dict[str, CodeGraphEdge] = {}
    project_paths = {file.path for file in project.file_tree}
    symbol_by_name = defaultdict(list)
    for symbol in symbols:
        symbol_by_name[symbol.name].append(symbol)

    for parsed in parsed_files:
        file_node_id = _file_node_id(parsed.path)
        nodes[file_node_id] = CodeGraphNode(
            id=file_node_id,
            label=parsed.path,
            kind="file",
            file_path=parsed.path,
            metadata={"language": parsed.language, "size_bytes": parsed.size_bytes},
        )
        for imported in parsed.imports:
            target_path = _resolve_import_path(parsed.path, imported, project_paths)
            target_id = _file_node_id(target_path) if target_path else f"module:{imported}"
            nodes.setdefault(
                target_id,
                CodeGraphNode(
                    id=target_id,
                    label=target_path or imported,
                    kind="file" if target_path else "external_module",
                    file_path=target_path,
                    metadata={"imported_by": parsed.path},
                ),
            )
            _add_edge(edges, file_node_id, target_id, "imports", imported)

    for symbol in symbols:
        symbol_id = _symbol_node_id(symbol)
        nodes[symbol_id] = CodeGraphNode(
            id=symbol_id,
            label=symbol.name,
            kind=symbol.kind,
            file_path=symbol.file_path,
            metadata={
                "line_start": symbol.line_start,
                "line_end": symbol.line_end,
                "language": symbol.language,
            },
        )
        _add_edge(edges, _file_node_id(symbol.file_path), symbol_id, "contains", symbol.evidence)

    for parsed in parsed_files:
        for caller_name, callee_name in parsed.calls:
            caller = next(
                (
                    item
                    for item in symbols
                    if item.name == caller_name and item.file_path == parsed.path
                ),
                None,
            )
            callees = symbol_by_name.get(callee_name, [])
            if caller and callees:
                _add_edge(
                    edges,
                    _symbol_node_id(caller),
                    _symbol_node_id(callees[0]),
                    "calls",
                    f"{caller_name} calls {callee_name}",
                )

    relation_counts = Counter(edge.relation for edge in edges.values())
    route_map = _route_map(symbols)
    test_coverage = _test_coverage_map(parsed_files)
    dependency_hotspots = _dependency_hotspots(nodes, edges)
    refactor_priorities = _refactor_priorities(parsed_files, symbols, edges)
    return CodeGraph(
        project_id=project.id,
        generated_at=generated_at,
        parser_provider=parser_provider(),
        nodes=list(nodes.values()),
        edges=list(edges.values()),
        metrics={
            "files": len(parsed_files),
            "symbols": len(symbols),
            "relations": dict(relation_counts),
            "external_modules": sum(1 for node in nodes.values() if node.kind == "external_module"),
            "route_map": route_map,
            "test_coverage": test_coverage,
            "dependency_hotspots": dependency_hotspots,
            "refactor_priorities": refactor_priorities,
        },
    )


def _build_risk_report(
    project: RepoProject,
    parsed_files: list[ParsedFile],
    graph: CodeGraph,
    generated_at: datetime,
) -> CodeRiskReport:
    risks: list[CodeRiskItem] = []
    source_files = [item for item in parsed_files if item.language in SOURCE_LANGUAGES]
    test_paths = {item.path for item in parsed_files if _looks_like_test(item.path)}

    if not project.readme or len(project.readme.strip()) < 120:
        risks.append(
            _risk(
                project.id,
                "documentation",
                "medium",
                "README is weak or missing",
                "The repository needs stronger onboarding and project narrative evidence.",
                "README content is missing or under 120 characters.",
                file_path="README.md" if project.readme else None,
            )
        )

    for parsed in source_files:
        line_count = max(1, len(parsed.lines))
        symbol_count = len(parsed.symbols)
        if parsed.size_bytes > 20_000 or line_count > 300:
            risks.append(
                _risk(
                    project.id,
                    "large_file",
                    "high" if line_count > 600 else "medium",
                    f"Large file: {parsed.path}",
                    f"{parsed.path} has {line_count} lines and {parsed.size_bytes} bytes.",
                    f"{parsed.path}:{line_count}",
                    file_path=parsed.path,
                    line=line_count,
                    metadata={"lines": line_count, "size_bytes": parsed.size_bytes},
                )
            )
        if symbol_count > 14:
            risks.append(
                _risk(
                    project.id,
                    "complex_file",
                    "medium",
                    f"Many symbols in {parsed.path}",
                    f"{parsed.path} defines {symbol_count} functions/classes/routes.",
                    f"{parsed.path} has {symbol_count} extracted symbols.",
                    file_path=parsed.path,
                    metadata={"symbol_count": symbol_count},
                )
            )
        for index, line in enumerate(parsed.lines, start=1):
            if TODO_PATTERN.search(line):
                risks.append(
                    _risk(
                        project.id,
                        "todo_hotspot",
                        "low",
                        f"TODO/FIXME in {parsed.path}",
                        "A TODO-style marker should be triaged before release.",
                        line.strip(),
                        file_path=parsed.path,
                        line=index,
                    )
                )
        if not _has_test_counterpart(parsed.path, test_paths):
            risks.append(
                _risk(
                    project.id,
                    "missing_tests",
                    "medium",
                    f"Missing test signal for {parsed.path}",
                    "No nearby test/spec file was found for this source file.",
                    parsed.path,
                    file_path=parsed.path,
                )
            )

    inbound = Counter(edge.target for edge in graph.edges if edge.relation == "imports")
    for target, count in inbound.items():
        if count >= 4:
            node = next((item for item in graph.nodes if item.id == target), None)
            risks.append(
                _risk(
                    project.id,
                    "dependency_hotspot",
                    "medium",
                    f"Dependency hotspot: {node.label if node else target}",
                    f"{count} files import this module/file.",
                    node.file_path or target if node else target,
                    file_path=node.file_path if node else None,
                    metadata={"inbound_imports": count},
                )
            )

    for cycle in _find_file_cycles(graph):
        risks.append(
            _risk(
                project.id,
                "circular_dependency",
                "high",
                "Circular file dependency",
                "A cycle exists in file imports and should be broken with a boundary module.",
                " -> ".join(cycle),
                metadata={"cycle": cycle},
            )
        )

    duplicate_groups = _duplicate_module_names(source_files)
    for name, paths in duplicate_groups.items():
        risks.append(
            _risk(
                project.id,
                "duplicated_looking_modules",
                "low",
                f"Duplicated-looking module names: {name}",
                (
                    "Multiple files share a similar module name and may hide "
                    "duplicated responsibility."
                ),
                ", ".join(paths),
                metadata={"paths": paths},
            )
        )

    for priority in graph.metrics.get("refactor_priorities", [])[:3]:
        if isinstance(priority, dict) and float(priority.get("score", 0)) >= 18:
            risks.append(
                _risk(
                    project.id,
                    "refactor_priority",
                    "medium",
                    f"Refactor priority: {priority.get('file_path')}",
                    (
                        "This file combines size, symbol count, TODOs, import pressure, "
                        "and test gap signals."
                    ),
                    str(priority.get("reason", "Composite deterministic score.")),
                    file_path=str(priority.get("file_path")),
                    metadata=priority,
                )
            )

    summary = (
        f"Analyzed {len(parsed_files)} files, {graph.metrics.get('symbols', 0)} symbols, "
        f"and found {len(risks)} deterministic risks."
    )
    return CodeRiskReport(
        project_id=project.id,
        generated_at=generated_at,
        summary=summary,
        risks=risks,
        metrics={
            "source_files": len(source_files),
            "risks": len(risks),
            "high_risks": sum(1 for risk in risks if risk.severity == "high"),
            "medium_risks": sum(1 for risk in risks if risk.severity == "medium"),
            "low_risks": sum(1 for risk in risks if risk.severity == "low"),
            "route_count": len(graph.metrics.get("route_map", [])),
            "test_coverage": graph.metrics.get("test_coverage", {}),
            "top_dependency_hotspots": graph.metrics.get("dependency_hotspots", [])[:5],
            "top_refactor_priorities": graph.metrics.get("refactor_priorities", [])[:5],
        },
    )


def _route_map(symbols: list[CodeSymbol]) -> list[dict[str, object]]:
    routes: list[dict[str, object]] = []
    for symbol in symbols:
        if symbol.kind != "route":
            continue
        method = symbol.metadata.get("http_method") or "ROUTE"
        routes.append(
            {
                "method": str(method).upper(),
                "path": str(symbol.metadata.get("route_path") or "/"),
                "handler": symbol.name,
                "file_path": symbol.file_path,
                "line": symbol.line_start,
            }
        )
    return sorted(routes, key=lambda item: (str(item["file_path"]), str(item["path"])))


def _test_coverage_map(parsed_files: list[ParsedFile]) -> dict[str, object]:
    source_files = [
        item
        for item in parsed_files
        if item.language in SOURCE_LANGUAGES and not _looks_like_test(item.path)
    ]
    test_paths = {item.path for item in parsed_files if _looks_like_test(item.path)}
    uncovered = [
        item.path for item in source_files if not _has_test_counterpart(item.path, test_paths)
    ]
    covered = [item.path for item in source_files if item.path not in uncovered]
    ratio = round(len(covered) / len(source_files), 2) if source_files else 1.0
    return {
        "source_files": len(source_files),
        "test_files": len(test_paths),
        "covered_files": len(covered),
        "uncovered_files": uncovered[:20],
        "coverage_ratio": ratio,
    }


def _dependency_hotspots(
    nodes: dict[str, CodeGraphNode],
    edges: dict[str, CodeGraphEdge],
) -> list[dict[str, object]]:
    inbound = Counter(edge.target for edge in edges.values() if edge.relation == "imports")
    ranked: list[dict[str, object]] = []
    for target, count in inbound.most_common(12):
        node = nodes.get(target)
        ranked.append(
            {
                "id": target,
                "label": node.label if node else target,
                "kind": node.kind if node else "unknown",
                "file_path": node.file_path if node else None,
                "inbound_imports": count,
            }
        )
    return ranked


def _refactor_priorities(
    parsed_files: list[ParsedFile],
    symbols: list[CodeSymbol],
    edges: dict[str, CodeGraphEdge],
) -> list[dict[str, object]]:
    symbols_by_file = Counter(symbol.file_path for symbol in symbols)
    inbound_by_file = Counter(
        edge.target.replace("file:", "", 1)
        for edge in edges.values()
        if edge.relation == "imports" and edge.target.startswith("file:")
    )
    test_paths = {item.path for item in parsed_files if _looks_like_test(item.path)}
    priorities: list[dict[str, object]] = []
    for parsed in parsed_files:
        if parsed.language not in SOURCE_LANGUAGES or _looks_like_test(parsed.path):
            continue
        lines = len(parsed.lines)
        todos = sum(1 for line in parsed.lines if TODO_PATTERN.search(line))
        symbol_count = symbols_by_file[parsed.path]
        inbound = inbound_by_file[parsed.path]
        missing_test = not _has_test_counterpart(parsed.path, test_paths)
        score = round(
            min(
                100,
                (lines / 40)
                + (symbol_count * 3)
                + (todos * 7)
                + (inbound * 5)
                + (12 if missing_test else 0),
            ),
            1,
        )
        if score <= 0:
            continue
        reasons = [
            f"{lines} lines",
            f"{symbol_count} symbols",
            f"{inbound} inbound imports",
        ]
        if todos:
            reasons.append(f"{todos} TODO/FIXME markers")
        if missing_test:
            reasons.append("missing nearby test")
        priorities.append(
            {
                "file_path": parsed.path,
                "score": score,
                "reason": ", ".join(reasons),
            }
        )
    return sorted(priorities, key=lambda item: float(item["score"]), reverse=True)[:12]


def _is_source_or_doc(file: RepoFile) -> bool:
    return bool(file.preview) and file.kind == "file" and bool(
        file.language in SOURCE_LANGUAGES or file.language
    )


def _line(lines: list[str], number: int) -> str:
    if 1 <= number <= len(lines):
        return lines[number - 1].strip()
    return ""


def _line_number(content: str, offset: int) -> int:
    return content.count("\n", 0, offset) + 1


def _has_route_decorator(node: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    return bool(_route_decorator_info(node.decorator_list))


def _route_decorator_info(decorators: list[ast.expr]) -> dict[str, str]:
    for decorator in decorators:
        name = _decorator_name(decorator)
        method = name.split(".")[-1]
        if not (name.startswith(("app.", "router.")) and method in _http_methods()):
            continue
        route_path = ""
        if isinstance(decorator, ast.Call) and decorator.args:
            first_arg = decorator.args[0]
            if isinstance(first_arg, ast.Constant) and isinstance(first_arg.value, str):
                route_path = first_arg.value
        return {"http_method": method.upper(), "route_path": route_path or "/"}
    return {}


def _decorator_name(node: ast.AST) -> str:
    if isinstance(node, ast.Call):
        return _decorator_name(node.func)
    if isinstance(node, ast.Attribute):
        return f"{_decorator_name(node.value)}.{node.attr}"
    if isinstance(node, ast.Name):
        return node.id
    return ast.unparse(node) if hasattr(ast, "unparse") else "decorator"


def _python_call_name(node: ast.Call) -> str | None:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return None


def _http_methods() -> set[str]:
    return {"get", "post", "put", "patch", "delete", "options", "head"}


def _next_route_from_path(path: str) -> str:
    route = path
    for prefix in ("app/", "src/app/"):
        if prefix in route:
            route = route.split(prefix, 1)[1]
            break
    route = re.sub(r"/route\.(ts|tsx|js|jsx)$", "", route)
    route = re.sub(r"/page\.(ts|tsx|js|jsx)$", "", route)
    route = re.sub(r"\[(.*?)\]", r":\1", route)
    return "/" + route.strip("/")


def _extract_dependency_mentions(path: str, content: str) -> list[str]:
    if path.endswith("package.json"):
        return re.findall(r'"([^"]+)":\s*"[^"]+"', content)[:80]
    if path.endswith("pyproject.toml"):
        return re.findall(r'"([A-Za-z0-9_.-]+)[<>=~!]', content)[:80]
    return []


def _resolve_import_path(
    current_path: str,
    imported: str,
    project_paths: set[str],
) -> str | None:
    if not imported.startswith("."):
        module_path = imported.replace(".", "/") + ".py"
        matches = [path for path in project_paths if path.endswith(module_path)]
        return matches[0] if matches else None

    base = PurePosixPath(current_path).parent
    target = (base / imported).as_posix()
    normalized = str(PurePosixPath(target))
    candidates = [
        normalized,
        f"{normalized}.py",
        f"{normalized}.ts",
        f"{normalized}.tsx",
        f"{normalized}.js",
        f"{normalized}.jsx",
        f"{normalized}/index.ts",
        f"{normalized}/index.tsx",
    ]
    for candidate in candidates:
        if candidate in project_paths:
            return candidate
    return None


def _file_node_id(path: str) -> str:
    return f"file:{path}"


def _symbol_node_id(symbol: CodeSymbol) -> str:
    return f"symbol:{symbol.file_path}:{symbol.name}:{symbol.line_start}"


def _add_edge(
    edges: dict[str, CodeGraphEdge],
    source: str,
    target: str,
    relation: str,
    evidence: str | None,
) -> None:
    if source == target:
        return
    edge_id = f"{source}->{relation}->{target}"
    edges.setdefault(
        edge_id,
        CodeGraphEdge(
            id=edge_id,
            source=source,
            target=target,
            relation=relation,
            evidence=evidence,
        ),
    )


def _risk(
    project_id: str,
    category: str,
    severity: str,
    title: str,
    detail: str,
    evidence: str,
    *,
    file_path: str | None = None,
    line: int | None = None,
    metadata: dict[str, object] | None = None,
) -> CodeRiskItem:
    return CodeRiskItem(
        id=f"risk_{uuid4().hex[:16]}",
        project_id=project_id,
        category=category,
        severity=severity,
        title=title,
        detail=detail,
        evidence=evidence,
        file_path=file_path,
        line=line,
        metadata=metadata or {},
    )


def _looks_like_test(path: str) -> bool:
    lower = path.lower()
    return any(marker in PurePosixPath(lower).name for marker in TEST_MARKERS)


def _has_test_counterpart(path: str, test_paths: set[str]) -> bool:
    stem = PurePosixPath(path).stem.lower()
    if _looks_like_test(path):
        return True
    return any(stem in PurePosixPath(test).stem.lower() for test in test_paths)


def _find_file_cycles(graph: CodeGraph) -> list[list[str]]:
    adjacency: dict[str, list[str]] = defaultdict(list)
    file_labels = {node.id: node.label for node in graph.nodes if node.kind == "file"}
    for edge in graph.edges:
        if edge.relation == "imports" and edge.source in file_labels and edge.target in file_labels:
            adjacency[edge.source].append(edge.target)

    cycles: list[list[str]] = []
    visiting: list[str] = []
    seen: set[str] = set()

    def visit(node: str) -> None:
        if node in visiting:
            index = visiting.index(node)
            cycles.append([file_labels[item] for item in visiting[index:]] + [file_labels[node]])
            return
        if node in seen:
            return
        visiting.append(node)
        for target in adjacency.get(node, []):
            visit(target)
        visiting.pop()
        seen.add(node)

    for node in adjacency:
        visit(node)
    return cycles[:8]


def _duplicate_module_names(files: list[ParsedFile]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for file in files:
        name = re.sub(r"[^a-z0-9]", "", PurePosixPath(file.path).stem.lower())
        if name and name not in {"index", "main", "__init__"}:
            groups[name].append(file.path)
    return {name: paths for name, paths in groups.items() if len(paths) > 1}
