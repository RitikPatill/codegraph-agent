"""Persist and load a NetworkX DiGraph as JSON using node_link format."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import networkx as nx


def save_graph(g: nx.DiGraph, path: str | Path) -> None:
    """Write *g* to *path* as JSON (atomic write via temp file + os.replace)."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    data = nx.node_link_data(g, edges="edges")
    json_str = json.dumps(data, default=str)

    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=path.parent,
        delete=False,
        suffix=".tmp",
        encoding="utf-8",
    ) as tmp:
        tmp.write(json_str)
        tmp_path = tmp.name

    os.replace(tmp_path, path)


def load_graph(path: str | Path) -> nx.DiGraph:
    """Load a graph from JSON written by :func:`save_graph`."""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return nx.node_link_graph(data, edges="edges", directed=True, multigraph=False)
