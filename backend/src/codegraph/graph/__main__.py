"""CLI entry point: python -m codegraph.graph <kg_json_path>

Prints node/edge counts broken down by type, then samples the first 5 nodes
and 5 edges from the persisted graph file.

Usage:
    python -m codegraph.graph path/to/kg.json
"""
import sys
from collections import Counter
from pathlib import Path

from .persistence import load_graph


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python -m codegraph.graph <kg_json_path>", file=sys.stderr)
        sys.exit(1)

    kg_path = Path(sys.argv[1])
    if not kg_path.exists():
        print(f"Error: {kg_path} does not exist", file=sys.stderr)
        sys.exit(1)

    g = load_graph(kg_path)

    node_kinds: Counter[str] = Counter(
        data.get("kind", "unknown") for _, data in g.nodes(data=True)
    )
    edge_kinds: Counter[str] = Counter(
        data.get("kind", "unknown") for _, _, data in g.edges(data=True)
    )

    node_detail = ", ".join(f"{k}: {v}" for k, v in sorted(node_kinds.items()))
    edge_detail = ", ".join(f"{k}: {v}" for k, v in sorted(edge_kinds.items()))

    print(f"Nodes: {g.number_of_nodes()}  ({node_detail})")
    print(f"Edges: {g.number_of_edges()}  ({edge_detail})")

    print("\nSample nodes (first 5):")
    for i, (nid, data) in enumerate(g.nodes(data=True)):
        if i >= 5:
            break
        kind = data.get("kind", "?")
        name = data.get("name", "?")
        start = data.get("start_line", "?")
        end = data.get("end_line", "?")
        print(f"  {nid}  [{kind}]  {name}  lines {start}-{end}")

    print("\nSample edges (first 5):")
    for i, (src, dst, data) in enumerate(g.edges(data=True)):
        if i >= 5:
            break
        ek = data.get("kind", "?")
        print(f"  {src} --{ek}--> {dst}")


if __name__ == "__main__":
    main()
