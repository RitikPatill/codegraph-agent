"""Tests for the M3 knowledge-graph builder.

All tests use real tree-sitter parsing.  The two tests that need custom
fixtures (CALLS, INHERITS) create small temp files via pytest's tmp_path.
"""
from pathlib import Path

import pytest

from codegraph.graph import build_graph, load_graph, save_graph
from codegraph.ingest.walker import ingest_repo

FIXTURES = Path(__file__).parent / "fixtures" / "sample_repo"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _graph():
    symbols = ingest_repo(FIXTURES)
    return build_graph(symbols, FIXTURES)


# ---------------------------------------------------------------------------
# Node creation
# ---------------------------------------------------------------------------


def test_file_nodes_created():
    g = _graph()
    node_ids = set(g.nodes)
    assert "file:sample.py" in node_ids
    assert "file:utils.ts" in node_ids


def test_class_nodes_created():
    g = _graph()
    assert "class:sample.py:Greeter" in g.nodes
    data = g.nodes["class:sample.py:Greeter"]
    assert data["kind"] == "Class"
    assert data["name"] == "Greeter"


def test_method_nodes_created():
    g = _graph()
    # sample.py has class Greeter with method hello
    assert "method:sample.py:Greeter.hello" in g.nodes
    data = g.nodes["method:sample.py:Greeter.hello"]
    assert data["kind"] == "Method"
    assert data["name"] == "hello"


def test_function_nodes_created():
    g = _graph()
    assert "func:sample.py:standalone" in g.nodes
    data = g.nodes["func:sample.py:standalone"]
    assert data["kind"] == "Function"


# ---------------------------------------------------------------------------
# CONTAINS edges
# ---------------------------------------------------------------------------


def test_contains_edge_file_to_class():
    g = _graph()
    assert g.has_edge("file:sample.py", "class:sample.py:Greeter")
    assert g.edges["file:sample.py", "class:sample.py:Greeter"]["kind"] == "CONTAINS"


# ---------------------------------------------------------------------------
# DEFINES edges
# ---------------------------------------------------------------------------


def test_defines_edge_class_to_method():
    g = _graph()
    assert g.has_edge("class:sample.py:Greeter", "method:sample.py:Greeter.hello")
    assert (
        g.edges["class:sample.py:Greeter", "method:sample.py:Greeter.hello"]["kind"]
        == "DEFINES"
    )


# ---------------------------------------------------------------------------
# Persistence round-trip
# ---------------------------------------------------------------------------


def test_persist_round_trip(tmp_path):
    g = _graph()
    out = tmp_path / "kg.json"
    save_graph(g, out)
    g2 = load_graph(out)
    assert g2.number_of_nodes() == g.number_of_nodes()
    assert g2.number_of_edges() == g.number_of_edges()


def test_persist_attrs_preserved(tmp_path):
    g = _graph()
    out = tmp_path / "kg.json"
    save_graph(g, out)
    g2 = load_graph(out)

    data = g2.nodes["class:sample.py:Greeter"]
    assert data["kind"] == "Class"
    assert data["name"] == "Greeter"
    assert data["start_line"] == 1


# ---------------------------------------------------------------------------
# CALLS edges  (inline temp file)
# ---------------------------------------------------------------------------


def test_call_edge_intra_file(tmp_path):
    (tmp_path / "call_test.py").write_text(
        "def funcA():\n    funcB()\n\ndef funcB():\n    pass\n",
        encoding="utf-8",
    )
    symbols = ingest_repo(tmp_path)
    g = build_graph(symbols, tmp_path)

    caller_id = "func:call_test.py:funcA"
    callee_id = "func:call_test.py:funcB"
    assert g.has_node(caller_id), f"Node {caller_id!r} missing"
    assert g.has_node(callee_id), f"Node {callee_id!r} missing"
    assert g.has_edge(caller_id, callee_id), "Expected CALLS edge from funcA to funcB"
    assert g.edges[caller_id, callee_id]["kind"] == "CALLS"


# ---------------------------------------------------------------------------
# INHERITS edges  (inline temp file)
# ---------------------------------------------------------------------------


def test_inherits_edge(tmp_path):
    (tmp_path / "inherit_test.py").write_text(
        "class Base:\n    pass\n\nclass Child(Base):\n    pass\n",
        encoding="utf-8",
    )
    symbols = ingest_repo(tmp_path)
    g = build_graph(symbols, tmp_path)

    child_id = "class:inherit_test.py:Child"
    base_id = "class:inherit_test.py:Base"
    assert g.has_node(child_id), f"Node {child_id!r} missing"
    assert g.has_node(base_id), f"Node {base_id!r} missing"
    assert g.has_edge(child_id, base_id), "Expected INHERITS edge from Child to Base"
    assert g.edges[child_id, base_id]["kind"] == "INHERITS"
