"""Build a NetworkX directed graph from a flat list of Symbol objects.

Node IDs:
    file:<rel_path>                       – File
    class:<rel_path>:<ClassName>          – Class
    func:<rel_path>:<FuncName>            – Function
    method:<rel_path>:<ClassName>.<Name>  – Method

Edge kinds:
    CONTAINS  File  → Class | Function | Method
    DEFINES   Class → Method
    IMPORTS   File  → Class | Function  (Python only, best-effort)
    CALLS     Function | Method → Function | Method  (intra-file regex heuristic)
    INHERITS  Class → Class  (Python only)
"""
from __future__ import annotations

import re
from pathlib import Path

import networkx as nx
import tree_sitter_python
from tree_sitter import Language, Parser

from codegraph.ingest.models import Symbol

_PY_LANGUAGE = Language(tree_sitter_python.language())


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def build_graph(symbols: list[Symbol], repo_root: str | Path) -> nx.DiGraph:
    """Build a directed knowledge graph from *symbols* rooted at *repo_root*."""
    repo_root = Path(repo_root).resolve()
    g = nx.DiGraph()

    _add_nodes(g, symbols, repo_root)
    _add_contains_edges(g, symbols, repo_root)
    _add_defines_edges(g, symbols, repo_root)
    _add_import_edges(g, symbols, repo_root)
    _add_call_edges(g, symbols, repo_root)
    _add_inherit_edges(g, symbols, repo_root)

    return g


# ---------------------------------------------------------------------------
# Node / edge helpers
# ---------------------------------------------------------------------------


def _rel_path_str(abs_file: str, repo_root: Path) -> str:
    """Return forward-slash relative path string for *abs_file* under *repo_root*."""
    try:
        rel = Path(abs_file).relative_to(repo_root)
        return str(rel).replace("\\", "/")
    except ValueError:
        return Path(abs_file).name


def _node_id(symbol: Symbol, repo_root: Path) -> str:
    rel = _rel_path_str(symbol.file, repo_root)
    if symbol.kind == "File":
        return f"file:{rel}"
    if symbol.kind == "Class":
        return f"class:{rel}:{symbol.name}"
    if symbol.kind == "Function":
        return f"func:{rel}:{symbol.name}"
    if symbol.kind == "Method":
        parent = symbol.parent or ""
        return f"method:{rel}:{parent}.{symbol.name}"
    raise ValueError(f"Unknown symbol kind: {symbol.kind!r}")


# ---------------------------------------------------------------------------
# Step 1 – nodes
# ---------------------------------------------------------------------------


def _add_nodes(g: nx.DiGraph, symbols: list[Symbol], repo_root: Path) -> None:
    for sym in symbols:
        nid = _node_id(sym, repo_root)
        g.add_node(
            nid,
            kind=sym.kind,
            name=sym.name,
            file=sym.file,
            start_line=sym.start_line,
            end_line=sym.end_line,
        )


# ---------------------------------------------------------------------------
# Step 2 – CONTAINS edges  (File → Class | Function | Method)
# ---------------------------------------------------------------------------


def _add_contains_edges(g: nx.DiGraph, symbols: list[Symbol], repo_root: Path) -> None:
    for sym in symbols:
        if sym.kind == "File":
            continue
        rel = _rel_path_str(sym.file, repo_root)
        file_nid = f"file:{rel}"
        sym_nid = _node_id(sym, repo_root)
        if g.has_node(file_nid) and g.has_node(sym_nid):
            g.add_edge(file_nid, sym_nid, kind="CONTAINS")


# ---------------------------------------------------------------------------
# Step 3 – DEFINES edges  (Class → Method)
# ---------------------------------------------------------------------------


def _add_defines_edges(g: nx.DiGraph, symbols: list[Symbol], repo_root: Path) -> None:
    for sym in symbols:
        if sym.kind != "Method" or not sym.parent:
            continue
        rel = _rel_path_str(sym.file, repo_root)
        class_nid = f"class:{rel}:{sym.parent}"
        method_nid = _node_id(sym, repo_root)
        if g.has_node(class_nid) and g.has_node(method_nid):
            g.add_edge(class_nid, method_nid, kind="DEFINES")


# ---------------------------------------------------------------------------
# Step 4 – IMPORTS edges  (Python only, best-effort)
# ---------------------------------------------------------------------------


def _add_import_edges(g: nx.DiGraph, symbols: list[Symbol], repo_root: Path) -> None:
    # name → list of node IDs for all class/function nodes in this repo
    name_to_nids: dict[str, list[str]] = {}
    for sym in symbols:
        if sym.kind in ("Class", "Function"):
            nid = _node_id(sym, repo_root)
            name_to_nids.setdefault(sym.name, []).append(nid)

    parser = Parser(_PY_LANGUAGE)
    for sym in symbols:
        if sym.kind != "File" or not sym.name.endswith(".py"):
            continue
        file_path = Path(sym.file)
        if not file_path.exists():
            continue

        source = file_path.read_bytes()
        tree = parser.parse(source)
        rel = _rel_path_str(sym.file, repo_root)
        file_nid = f"file:{rel}"

        for name in _extract_import_names(tree.root_node):
            for target_nid in name_to_nids.get(name, []):
                if g.has_node(file_nid) and g.has_node(target_nid):
                    g.add_edge(file_nid, target_nid, kind="IMPORTS")


def _extract_import_names(node) -> list[str]:
    """Recursively collect symbol names referenced by import statements."""
    names: list[str] = []

    if node.type in ("import_statement", "import_from_statement"):
        for child in node.children:
            if child.type == "dotted_name":
                text = child.text.decode("utf-8", errors="replace")
                names.append(text.split(".")[-1])
            elif child.type == "identifier":
                names.append(child.text.decode("utf-8", errors="replace"))
            elif child.type == "aliased_import":
                alias = child.child_by_field_name("alias")
                if alias:
                    names.append(alias.text.decode("utf-8", errors="replace"))
                else:
                    name_field = child.child_by_field_name("name")
                    if name_field:
                        text = name_field.text.decode("utf-8", errors="replace")
                        names.append(text.split(".")[-1])
        return names  # don't recurse further into import nodes

    for child in node.children:
        names.extend(_extract_import_names(child))
    return names


# ---------------------------------------------------------------------------
# Step 5 – CALLS edges  (intra-file regex heuristic)
# ---------------------------------------------------------------------------


def _add_call_edges(g: nx.DiGraph, symbols: list[Symbol], repo_root: Path) -> None:
    """Add CALLS edges between callables in the same file using regex line-scan.

    Only checks symbols within the same file to avoid O(n²) cross-repo false
    positives. This is intentionally approximate; M4 tools do not require
    perfect call edges.
    """
    # Group callable symbols by file
    by_file: dict[str, list[Symbol]] = {}
    for sym in symbols:
        if sym.kind in ("Function", "Method"):
            by_file.setdefault(sym.file, []).append(sym)

    for abs_file, callables in by_file.items():
        file_path = Path(abs_file)
        if not file_path.exists():
            continue
        try:
            lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue

        for caller in callables:
            caller_nid = _node_id(caller, repo_root)
            body = lines[caller.start_line - 1 : caller.end_line]

            for callee in callables:
                if callee.name == caller.name:
                    continue
                pattern = re.compile(r"\b" + re.escape(callee.name) + r"\b")
                if any(pattern.search(line) for line in body):
                    callee_nid = _node_id(callee, repo_root)
                    if g.has_node(caller_nid) and g.has_node(callee_nid):
                        g.add_edge(caller_nid, callee_nid, kind="CALLS")


# ---------------------------------------------------------------------------
# Step 6 – INHERITS edges  (Python only)
# ---------------------------------------------------------------------------


def _add_inherit_edges(g: nx.DiGraph, symbols: list[Symbol], repo_root: Path) -> None:
    # Build name → node_id map for all class nodes
    class_by_name: dict[str, str] = {}
    for sym in symbols:
        if sym.kind == "Class":
            class_by_name[sym.name] = _node_id(sym, repo_root)

    parser = Parser(_PY_LANGUAGE)
    for sym in symbols:
        if sym.kind != "File" or not sym.name.endswith(".py"):
            continue
        file_path = Path(sym.file)
        if not file_path.exists():
            continue

        source = file_path.read_bytes()
        tree = parser.parse(source)
        rel = _rel_path_str(sym.file, repo_root)

        _walk_inherit(tree.root_node, rel, class_by_name, g)


def _walk_inherit(
    node,
    rel: str,
    class_by_name: dict[str, str],
    g: nx.DiGraph,
) -> None:
    if node.type == "class_definition":
        name_node = node.child_by_field_name("name")
        if name_node:
            class_name = name_node.text.decode("utf-8", errors="replace")
            child_nid = f"class:{rel}:{class_name}"
            superclasses = node.child_by_field_name("superclasses")
            if superclasses:
                for arg in superclasses.children:
                    if arg.type == "identifier":
                        base_name = arg.text.decode("utf-8", errors="replace")
                        base_nid = class_by_name.get(base_name)
                        if base_nid and g.has_node(child_nid) and g.has_node(base_nid):
                            g.add_edge(child_nid, base_nid, kind="INHERITS")

    for child in node.children:
        _walk_inherit(child, rel, class_by_name, g)
