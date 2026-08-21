"""Pure graph query functions — no Anthropic dependency.

Each function accepts a NetworkX DiGraph and returns plain dicts/lists
suitable for JSON serialisation into Anthropic tool_result blocks.
"""
from __future__ import annotations

from pathlib import Path

import networkx as nx

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_MAX_SOURCE_LINES = 200


def _node_info(graph: nx.DiGraph, node_id: str) -> dict:
    """Return serialisable dict for a single graph node."""
    data = graph.nodes[node_id]
    return {
        "id": node_id,
        "kind": data.get("kind"),
        "name": data.get("name"),
        "file": str(data.get("file", "")),
        "start_line": data.get("start_line"),
        "end_line": data.get("end_line"),
    }


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------


def find_definition(
    graph: nx.DiGraph,
    symbol_name: str,
    kind: str | None = None,
) -> list[dict]:
    """All nodes whose 'name' attribute matches symbol_name (case-sensitive).

    Optional kind filter: 'File' | 'Class' | 'Function' | 'Method'.
    """
    results = []
    for node_id, data in graph.nodes(data=True):
        if data.get("name") != symbol_name:
            continue
        if kind is not None and data.get("kind") != kind:
            continue
        results.append(_node_info(graph, node_id))
    return results


def find_callers(graph: nx.DiGraph, symbol_id: str) -> list[dict]:
    """Nodes that have a CALLS edge pointing TO symbol_id (predecessors)."""
    if symbol_id not in graph:
        return []
    results = []
    for pred in graph.predecessors(symbol_id):
        edge_data = graph.edges[pred, symbol_id]
        if edge_data.get("kind") == "CALLS":
            results.append(_node_info(graph, pred))
    return results


def find_callees(graph: nx.DiGraph, symbol_id: str) -> list[dict]:
    """Nodes that symbol_id CALLS (successors via CALLS edges)."""
    if symbol_id not in graph:
        return []
    results = []
    for succ in graph.successors(symbol_id):
        edge_data = graph.edges[symbol_id, succ]
        if edge_data.get("kind") == "CALLS":
            results.append(_node_info(graph, succ))
    return results


def neighborhood(graph: nx.DiGraph, symbol_id: str, depth: int = 1) -> dict:
    """Ego-subgraph of radius=depth around symbol_id.

    Returns {"nodes": [...], "edges": [...]}.
    Depth is capped at 3 to avoid huge payloads.
    """
    depth = min(depth, 3)
    if symbol_id not in graph:
        return {"nodes": [], "edges": []}

    ego = nx.ego_graph(graph, symbol_id, radius=depth, undirected=False)

    nodes = [_node_info(graph, n) for n in ego.nodes() if n in graph]
    edges = [
        {"source": u, "target": v, "kind": data.get("kind")}
        for u, v, data in ego.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges}


def shortest_path(graph: nx.DiGraph, source_id: str, target_id: str) -> list[str]:
    """nx.shortest_path between two node IDs. Returns [] if no path exists."""
    try:
        return nx.shortest_path(graph, source_id, target_id)
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []


def search_symbols(
    graph: nx.DiGraph,
    query: str,
    kind: str | None = None,
) -> list[dict]:
    """Substring search (case-insensitive) on node 'name'. Optional kind filter."""
    query_lower = query.lower()
    results = []
    for node_id, data in graph.nodes(data=True):
        name = data.get("name", "")
        if query_lower not in name.lower():
            continue
        if kind is not None and data.get("kind") != kind:
            continue
        results.append(_node_info(graph, node_id))
    return results


def read_source(graph: nx.DiGraph, symbol_id: str, repo_root: Path) -> str:
    """Read the source lines for a symbol using its file/start_line/end_line attrs.

    Returns the raw source text, or an error string if the file is unreadable.
    Output is capped at _MAX_SOURCE_LINES lines.
    """
    if symbol_id not in graph:
        return f"Error: node '{symbol_id}' not found in graph"

    data = graph.nodes[symbol_id]
    file_attr = data.get("file", "")
    start_line: int = data.get("start_line") or 1
    end_line: int = data.get("end_line") or start_line

    # file attr is absolute; fall back to joining with repo_root if relative
    file_path = Path(file_attr)
    if not file_path.is_absolute():
        file_path = repo_root / file_path

    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return f"Error: cannot read '{file_path}': {exc}"

    # 1-indexed → 0-indexed slice
    selected = lines[start_line - 1 : end_line]
    truncated = False
    if len(selected) > _MAX_SOURCE_LINES:
        selected = selected[:_MAX_SOURCE_LINES]
        truncated = True

    text = "\n".join(selected)
    if truncated:
        text += f"\n... (truncated at {_MAX_SOURCE_LINES} lines)"
    return text
