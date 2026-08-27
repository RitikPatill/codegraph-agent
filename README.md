# CodeGraph Agent

> An agent that answers architectural questions about any codebase by planning traversals over a live code knowledge graph, with a visual reasoning UI.

<!-- TODO: replace with a 5-10 second demo gif. Record with ScreenToGif on
     Windows or peek on macOS. Save to docs/demo.gif and update path here. -->
![demo](docs/demo.gif)

## What it is

CodeGraph Agent ingests a Python or TypeScript repository, parses it with `tree-sitter`, and builds a structural knowledge graph of its symbols — files, classes, functions, methods — connected by `CALLS`, `IMPORTS`, `INHERITS`, `DEFINES`, and `CONTAINS` edges stored in a NetworkX graph. That graph is then exposed as a set of typed tools to a Claude-powered agent loop.

When you ask a natural-language question ("what would break if I removed `Depends()`?", "which classes inherit from `BaseModel`?", "what is the call chain from `create_app` to the database?"), the agent plans a sequence of graph queries — chaining `search_symbols → find_callers → neighborhood` as needed — and streams each step back to the browser. A Cytoscape.js panel animates the nodes the agent is currently touching, so you can watch the reasoning unfold in real time alongside the chat transcript.

## Quickstart

```bash
git clone https://github.com/ritik-1302/codegraph-agent.git
cd codegraph-agent

# Backend — requires Python 3.11+, uv (https://docs.astral.sh/uv/)
cd backend
uv sync
export ANTHROPIC_API_KEY=sk-ant-...
uv run uvicorn codegraph.main:app --reload
# Starts on http://localhost:8000
# The sample repo is indexed automatically on startup

# Frontend — in a second terminal, requires Node + pnpm
cd ../frontend
pnpm install
pnpm dev
# Opens http://localhost:5173
```

## Usage

Open `http://localhost:5173`. The left pane is the chat interface; the right pane shows the full knowledge graph of the pre-indexed sample repo.

Type a question and press Enter. The agent streams each tool call as a collapsible card — tool name, arguments, and result — while the affected graph nodes pulse in the right pane. When the agent finishes, the final answer appears inline with `[node:function:handle_request]` references that scroll and zoom the graph to the cited symbol.

To index a different repository, POST to the ingest endpoint:

```bash
curl -s -X POST http://localhost:8000/ingest \
  -H 'Content-Type: application/json' \
  -d '{"repo_path": "/absolute/path/to/samples/fastapi-slice"}'
```

Two sample repositories live in `samples/` — `fastapi-slice` (Python) and `ts-utils` (TypeScript) — and work without any external dependencies.

## Architecture

```
Browser ──WS──► FastAPI ──► Agent Loop ──tool_use──► Graph Query Tools
                                                            │
                                                     NetworkX KG
                                                            ▲
                                              tree-sitter Ingest ◄── Local Repo

FastAPI streams {type, name, args, touched_nodes} frames back to the browser.
Cytoscape.js animates touched_nodes; chat panel appends each tool call card.
```

**Node types:** `File` `Module` `Class` `Function` `Method`

**Edge types:** `IMPORTS` `DEFINES` `CALLS` `INHERITS` `CONTAINS`

**Agent tools:** `find_definition` · `find_callers` · `find_callees` · `neighborhood` · `shortest_path` · `search_symbols` · `read_source`

## Project structure

```
codegraph-agent/
├── backend/                # Python 3.11 · FastAPI · NetworkX · tree-sitter
│   ├── src/codegraph/
│   │   ├── ingest/         # tree-sitter parsers for Python and TypeScript
│   │   ├── graph/          # graph builder and JSON persistence
│   │   ├── tools.py        # 7 pure graph query functions
│   │   └── agent.py        # Claude tool-use loop, streaming generator
│   ├── sample_repo/        # bundled demo repo indexed on startup
│   └── tests/              # 51 tests across ingest, graph, tools, and API
├── frontend/               # Vite · React 19 · TypeScript · Cytoscape.js
│   └── src/
│       ├── hooks/          # useChat — WebSocket lifecycle and message state
│       └── components/     # ChatPanel, GraphPanel, ToolCallCard
├── samples/
│   ├── fastapi-slice/      # self-contained Python sample for demo queries
│   └── ts-utils/           # self-contained TypeScript sample for demo queries
├── scripts/                # demo_query.py, smoke_test.sh, capture_screenshot.py
├── docs/                   # demo.gif, screenshot.png
├── record_demo.sh          # boots stack, runs demo query, captures artifacts
├── ARCHITECTURE.md         # layer-by-layer technical deep-dive
└── CONTRIBUTING.md         # dev setup, lint/test commands, extension checklists
```

## Roadmap

- [ ] Add Go, Rust, and Java via additional tree-sitter grammars
- [ ] Optional embedding layer for semantic fallback in `search_symbols`
- [ ] VS Code extension with inline "who calls this?" code lens
- [ ] Incremental re-index on file change via `watchdog` to avoid full re-ingest
- [ ] Subgraph export to PlantUML or Graphviz `.dot` from any traversal result

## License

MIT — see LICENSE.

---

Built autonomously by [autodev](https://github.com/RitikPatill/autodev),
a multi-agent orchestrator I designed. Each commit in this repo was
authored by me; the implementation work was performed by Sonnet under
the orchestrator's control. Read the orchestrator's README to see how.
