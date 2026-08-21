"""Unit tests for codegraph.tools — all in-memory, no API calls."""
from __future__ import annotations

from pathlib import Path

import networkx as nx
import pytest

from codegraph.tools import (
    find_callers,
    find_callees,
    find_definition,
    neighborhood,
    read_source,
    search_symbols,
    shortest_path,
)

# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture()
def tiny_graph() -> nx.DiGraph:
    """
    Two files: main.py and utils.py

    Nodes:
        file:main.py
        func:main.py:main
        func:main.py:helper
        file:utils.py
        func:utils.py:util_a
        class:utils.py:Config

    Edges (kind):
        file:main.py      → func:main.py:main       CONTAINS
        file:main.py      → func:main.py:helper      CONTAINS
        file:utils.py     → func:utils.py:util_a     CONTAINS
        file:utils.py     → class:utils.py:Config    CONTAINS
        func:main.py:main → func:main.py:helper      CALLS
        func:main.py:main → func:utils.py:util_a     CALLS
        file:main.py      → func:utils.py:util_a     IMPORTS
    """
    g = nx.DiGraph()

    # Nodes
    g.add_node("file:main.py", kind="File", name="main.py", file="/repo/main.py", start_line=1, end_line=10)
    g.add_node("func:main.py:main", kind="Function", name="main", file="/repo/main.py", start_line=1, end_line=5)
    g.add_node("func:main.py:helper", kind="Function", name="helper", file="/repo/main.py", start_line=7, end_line=10)
    g.add_node("file:utils.py", kind="File", name="utils.py", file="/repo/utils.py", start_line=1, end_line=20)
    g.add_node("func:utils.py:util_a", kind="Function", name="util_a", file="/repo/utils.py", start_line=1, end_line=8)
    g.add_node("class:utils.py:Config", kind="Class", name="Config", file="/repo/utils.py", start_line=10, end_line=20)

    # Edges
    g.add_edge("file:main.py", "func:main.py:main", kind="CONTAINS")
    g.add_edge("file:main.py", "func:main.py:helper", kind="CONTAINS")
    g.add_edge("file:utils.py", "func:utils.py:util_a", kind="CONTAINS")
    g.add_edge("file:utils.py", "class:utils.py:Config", kind="CONTAINS")
    g.add_edge("func:main.py:main", "func:main.py:helper", kind="CALLS")
    g.add_edge("func:main.py:main", "func:utils.py:util_a", kind="CALLS")
    g.add_edge("file:main.py", "func:utils.py:util_a", kind="IMPORTS")

    return g


# ---------------------------------------------------------------------------
# find_definition
# ---------------------------------------------------------------------------


def test_find_definition_exact(tiny_graph):
    results = find_definition(tiny_graph, "main")
    ids = [r["id"] for r in results]
    assert "func:main.py:main" in ids


def test_find_definition_kind_filter_class(tiny_graph):
    results = find_definition(tiny_graph, "Config", kind="Class")
    assert len(results) == 1
    assert results[0]["id"] == "class:utils.py:Config"


def test_find_definition_kind_filter_function(tiny_graph):
    results = find_definition(tiny_graph, "Config", kind="Function")
    assert results == []


def test_find_definition_no_match(tiny_graph):
    assert find_definition(tiny_graph, "nonexistent") == []


# ---------------------------------------------------------------------------
# find_callers
# ---------------------------------------------------------------------------


def test_find_callers(tiny_graph):
    results = find_callers(tiny_graph, "func:utils.py:util_a")
    ids = [r["id"] for r in results]
    assert "func:main.py:main" in ids
    # IMPORTS edge should NOT appear
    assert "file:main.py" not in ids


def test_find_callers_none(tiny_graph):
    # file:main.py has no CALLS predecessors
    results = find_callers(tiny_graph, "file:main.py")
    assert results == []


# ---------------------------------------------------------------------------
# find_callees
# ---------------------------------------------------------------------------


def test_find_callees(tiny_graph):
    results = find_callees(tiny_graph, "func:main.py:main")
    ids = [r["id"] for r in results]
    assert "func:main.py:helper" in ids
    assert "func:utils.py:util_a" in ids


def test_find_callees_no_calls(tiny_graph):
    # helper calls nothing
    results = find_callees(tiny_graph, "func:main.py:helper")
    assert results == []


# ---------------------------------------------------------------------------
# neighborhood
# ---------------------------------------------------------------------------


def test_neighborhood_depth1(tiny_graph):
    result = neighborhood(tiny_graph, "func:main.py:main", depth=1)
    node_ids = [n["id"] for n in result["nodes"]]
    # centre + direct neighbours via any edge direction
    assert "func:main.py:main" in node_ids
    assert "func:main.py:helper" in node_ids
    assert "func:utils.py:util_a" in node_ids


def test_neighborhood_has_edges(tiny_graph):
    result = neighborhood(tiny_graph, "func:main.py:main", depth=1)
    assert len(result["edges"]) > 0


def test_neighborhood_depth2_larger(tiny_graph):
    d1 = neighborhood(tiny_graph, "file:main.py", depth=1)
    d2 = neighborhood(tiny_graph, "file:main.py", depth=2)
    assert len(d2["nodes"]) >= len(d1["nodes"])


# ---------------------------------------------------------------------------
# shortest_path
# ---------------------------------------------------------------------------


def test_shortest_path_exists(tiny_graph):
    path = shortest_path(tiny_graph, "file:main.py", "func:utils.py:util_a")
    assert len(path) >= 2
    assert path[0] == "file:main.py"
    assert path[-1] == "func:utils.py:util_a"


def test_shortest_path_none(tiny_graph):
    # No directed path from Config back to helper
    path = shortest_path(tiny_graph, "class:utils.py:Config", "func:main.py:helper")
    assert path == []


def test_shortest_path_missing_node(tiny_graph):
    path = shortest_path(tiny_graph, "func:main.py:main", "does:not:exist")
    assert path == []


# ---------------------------------------------------------------------------
# search_symbols
# ---------------------------------------------------------------------------


def test_search_symbols_case_insensitive(tiny_graph):
    results = search_symbols(tiny_graph, "UTIL")
    ids = [r["id"] for r in results]
    assert "func:utils.py:util_a" in ids


def test_search_symbols_kind_filter(tiny_graph):
    results = search_symbols(tiny_graph, "config", kind="Class")
    assert len(results) == 1
    assert results[0]["id"] == "class:utils.py:Config"


def test_search_symbols_kind_filter_no_match(tiny_graph):
    results = search_symbols(tiny_graph, "config", kind="Function")
    assert results == []


def test_search_symbols_no_match(tiny_graph):
    assert search_symbols(tiny_graph, "zzznomatch") == []


# ---------------------------------------------------------------------------
# read_source
# ---------------------------------------------------------------------------


def test_read_source_valid(tmp_path, tiny_graph):
    # Write a real Python file
    src = tmp_path / "main.py"
    src.write_text("def main():\n    pass\n\ndef helper():\n    pass\n", encoding="utf-8")

    # Point node attrs at the temp file
    tiny_graph.nodes["func:main.py:main"]["file"] = str(src)
    tiny_graph.nodes["func:main.py:main"]["start_line"] = 1
    tiny_graph.nodes["func:main.py:main"]["end_line"] = 2

    text = read_source(tiny_graph, "func:main.py:main", tmp_path)
    assert "def main():" in text
    assert "pass" in text


def test_read_source_missing_file(tiny_graph):
    tiny_graph.nodes["func:main.py:main"]["file"] = "/nonexistent/path/main.py"
    result = read_source(tiny_graph, "func:main.py:main", Path("/nonexistent"))
    assert result.startswith("Error:")


def test_read_source_unknown_node(tiny_graph):
    result = read_source(tiny_graph, "func:does:not:exist", Path("/"))
    assert result.startswith("Error:")
