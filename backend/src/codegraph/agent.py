"""Claude tool-use agent loop for CodeGraph.

Drives a multi-turn Anthropic messages.create loop until the model emits a
final text block, yielding structured events for each step.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Iterator

import networkx as nx

from codegraph import tools as _tools

# ---------------------------------------------------------------------------
# Validate API key at import time
# ---------------------------------------------------------------------------

if not os.environ.get("ANTHROPIC_API_KEY"):
    raise RuntimeError(
        "ANTHROPIC_API_KEY is not set. "
        "Export the environment variable before importing codegraph.agent."
    )

import anthropic  # noqa: E402  (import after key check)

_client = anthropic.Anthropic()

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

_SYSTEM = (
    "You are a code architecture assistant. You have access to a structural "
    "knowledge graph of a software repository.\n"
    "Use the provided tools to traverse the graph and answer questions about "
    "code structure, dependencies, and impact.\n"
    "Always cite specific node IDs (e.g. func:utils.py:parse_config) in your "
    "final answer."
)

# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "find_definition",
        "description": (
            "Find nodes whose 'name' attribute exactly matches symbol_name. "
            "Use this to locate where a class, function, or method is defined. "
            "Optional kind filter: 'File' | 'Class' | 'Function' | 'Method'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol_name": {
                    "type": "string",
                    "description": "Exact (case-sensitive) name to look up.",
                },
                "kind": {
                    "type": "string",
                    "enum": ["File", "Class", "Function", "Method"],
                    "description": "Optional node kind filter.",
                },
            },
            "required": ["symbol_name"],
        },
    },
    {
        "name": "find_callers",
        "description": (
            "Return all nodes that call the given symbol (predecessors via CALLS edges). "
            "Requires the full node ID, e.g. 'func:utils.py:parse_config'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol_id": {
                    "type": "string",
                    "description": "Full node ID of the callee.",
                },
            },
            "required": ["symbol_id"],
        },
    },
    {
        "name": "find_callees",
        "description": (
            "Return all nodes that the given symbol calls (successors via CALLS edges). "
            "Requires the full node ID."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol_id": {
                    "type": "string",
                    "description": "Full node ID of the caller.",
                },
            },
            "required": ["symbol_id"],
        },
    },
    {
        "name": "neighborhood",
        "description": (
            "Return the ego-subgraph (all nodes and edges within `depth` hops) "
            "around a given node. Good for understanding local context. "
            "depth is capped at 3."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol_id": {
                    "type": "string",
                    "description": "Full node ID of the centre node.",
                },
                "depth": {
                    "type": "integer",
                    "description": "Number of hops (1–3). Default 1.",
                    "default": 1,
                },
            },
            "required": ["symbol_id"],
        },
    },
    {
        "name": "shortest_path",
        "description": (
            "Find the shortest directed path between two nodes. "
            "Returns an ordered list of node IDs, or [] if no path exists."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "source_id": {
                    "type": "string",
                    "description": "Starting node ID.",
                },
                "target_id": {
                    "type": "string",
                    "description": "Ending node ID.",
                },
            },
            "required": ["source_id", "target_id"],
        },
    },
    {
        "name": "search_symbols",
        "description": (
            "Substring search (case-insensitive) across all node names. "
            "Use this to find symbols when you only know part of the name. "
            "Optional kind filter."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Substring to search for (case-insensitive).",
                },
                "kind": {
                    "type": "string",
                    "enum": ["File", "Class", "Function", "Method"],
                    "description": "Optional node kind filter.",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_source",
        "description": (
            "Read the raw source code for a symbol using its stored file path "
            "and line range. Returns the source text (capped at 200 lines)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "symbol_id": {
                    "type": "string",
                    "description": "Full node ID of the symbol to read.",
                },
            },
            "required": ["symbol_id"],
        },
    },
]

# ---------------------------------------------------------------------------
# Internal dispatch
# ---------------------------------------------------------------------------


def _dispatch(
    name: str,
    args: dict,
    graph: nx.DiGraph,
    repo_root: Path,
) -> list | dict | str:
    """Call the appropriate tool function and return its raw result."""
    if name == "find_definition":
        return _tools.find_definition(graph, args["symbol_name"], args.get("kind"))
    if name == "find_callers":
        return _tools.find_callers(graph, args["symbol_id"])
    if name == "find_callees":
        return _tools.find_callees(graph, args["symbol_id"])
    if name == "neighborhood":
        return _tools.neighborhood(graph, args["symbol_id"], args.get("depth", 1))
    if name == "shortest_path":
        return _tools.shortest_path(graph, args["source_id"], args["target_id"])
    if name == "search_symbols":
        return _tools.search_symbols(graph, args["query"], args.get("kind"))
    if name == "read_source":
        return _tools.read_source(graph, args["symbol_id"], repo_root)
    return {"error": f"Unknown tool: {name}"}


def _extract_touched_nodes(result: list | dict | str) -> list[str]:
    """Extract node IDs from a tool result (dicts with an 'id' key)."""
    ids: list[str] = []
    if isinstance(result, list):
        for item in result:
            if isinstance(item, dict) and "id" in item:
                ids.append(item["id"])
    elif isinstance(result, dict):
        nodes = result.get("nodes", [])
        if isinstance(nodes, list):
            for item in nodes:
                if isinstance(item, dict) and "id" in item:
                    ids.append(item["id"])
        # shortest_path returns a plain list of strings — handled above
    return ids


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_agent(
    question: str,
    graph: nx.DiGraph,
    repo_root: Path,
    *,
    model: str = "claude-opus-4-6",
    max_tokens: int = 4096,
    system: str | None = None,
) -> Iterator[dict]:
    """Drive the Claude tool-use loop until the model emits a final text block.

    Yields event dicts:
      {"type": "tool_call",   "name": str, "args": dict, "touched_nodes": list[str]}
      {"type": "tool_result", "name": str, "result": str | list | dict}
      {"type": "text_delta",  "text": str}
    """
    system_prompt = system or _SYSTEM
    messages: list[dict] = [{"role": "user", "content": question}]

    while True:
        response = _client.messages.create(
            model=model,
            tools=TOOL_SCHEMAS,
            messages=messages,
            max_tokens=max_tokens,
            system=system_prompt,
        )

        tool_results: list[dict] = []

        for block in response.content:
            if block.type == "text":
                yield {"type": "text_delta", "text": block.text}

            elif block.type == "tool_use":
                result = _dispatch(block.name, block.input, graph, repo_root)
                touched = _extract_touched_nodes(result)

                # If result is a plain list of strings (shortest_path), those ARE the IDs
                if isinstance(result, list) and all(isinstance(x, str) for x in result):
                    touched = result

                yield {
                    "type": "tool_call",
                    "name": block.name,
                    "args": block.input,
                    "touched_nodes": touched,
                }
                yield {
                    "type": "tool_result",
                    "name": block.name,
                    "result": result,
                }

                tool_results.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, default=str),
                    }
                )

        if response.stop_reason == "end_turn":
            break

        # Append assistant turn and tool results, then loop
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})
