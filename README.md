# CodeGraph Agent

![Status](https://img.shields.io/badge/status-WIP-orange)
![License](https://img.shields.io/badge/license-MIT-blue)
![M1](https://img.shields.io/badge/M1-scaffold-green)
![M2](https://img.shields.io/badge/M2-ingestion-green)
![M3](https://img.shields.io/badge/M3-graph--core-lightgrey)
![M4](https://img.shields.io/badge/M4-tools-lightgrey)
![M5](https://img.shields.io/badge/M5-agent--loop-lightgrey)
![M6](https://img.shields.io/badge/M6-streaming--ui-lightgrey)
![M7](https://img.shields.io/badge/M7-cytoscape-lightgrey)
![M8](https://img.shields.io/badge/M8-polish-lightgrey)

> M2 ingestion shipped. Tree-sitter parses Python and JS/TS into typed `Symbol` objects; `ingest_repo()` walks a directory. Graph building, agent loop, and UI are not yet built.

---

## Problem statement

Vector-RAG treats code as prose and loses what actually matters: **structure**. A senior engineer asking *"what breaks if I change `handle_request`?"* needs call edges, inheritance chains, and import graphs — not cosine-similar docstrings.

CodeGraph Agent builds a **structural knowledge graph** of a repository's symbols and exposes that graph as tools to a Claude-powered agent. Instead of a fixed retrieval pipeline, the agent plans multi-hop traversals:

```
find_callers(handle_request)
  → neighborhood(each caller, depth=1)
  → rank by blast radius
```

The result is an answer that cites exact files and functions, with a live graph visualization showing which nodes the agent touched.

---

## What works — M2

| Area | Detail |
|---|---|
| Backend scaffold | FastAPI app (`src/codegraph/main.py`), managed with `uv` and `pyproject.toml` |
| Health endpoint | `GET /health` returns `{"status": "ok"}`; covered by a pytest smoke test |
| Frontend scaffold | Vite 6 + React 19 + TypeScript; `pnpm dev` starts the dev server on port 5173 |
| Linting / formatting | ruff-format + ruff lint on all backend Python; prettier on frontend TS/JSON/CSS |
| Pre-commit hooks | Both linters run on commit via `.pre-commit-config.yaml` |
| **Code ingestion** | `codegraph.ingest` walks a repo with `pathlib`, parses `.py` / `.ts` / `.js` files using `tree-sitter`, and emits typed `Symbol` dataclasses (`File`, `Class`, `Function`, `Method`) with file path and 1-indexed line spans |
| **Ingest CLI** | `python -m codegraph.ingest <path>` prints a JSON array of all symbols |
| **Tests** | 10 pytest tests against fixture files covering Python and TS parsing, line spans, hidden-dir skipping, and `ingest_repo()` |
| License | MIT |

Agent loop, graph building, and UI are not yet built.

---

## Planned architecture

```mermaid
flowchart LR
    U[User / Browser] -->|WS| API[FastAPI]
    API --> Agent[Claude Agent Loop]
    Agent -->|tool_use| Tools[Graph Query Tools]
    Tools --> KG[(NetworkX KG)]
    Ingest[tree-sitter Ingest] --> KG
    Repo[Local Repo] --> Ingest
    API -->|stream trace + node ids| U
    U -.->|Cytoscape highlights| U
```

**Node types:** `File`, `Module`, `Class`, `Function`, `Method`

**Edge types:** `IMPORTS`, `DEFINES`, `CALLS`, `INHERITS`, `CONTAINS`

**Agent tools (planned):** `find_definition`, `find_callers`, `find_callees`, `neighborhood`, `shortest_path`, `search_symbols`, `read_source`

---

## Quickstart

Code ingestion is functional. Graph building, agent loop, and UI are not yet built.

```bash
# Backend
cd backend
uv sync
uv run uvicorn codegraph.main:app --reload
# → http://localhost:8000/health

# Frontend (separate terminal)
cd frontend
pnpm install
pnpm dev
# → http://localhost:5173
```

```bash
# Run backend tests
cd backend
uv run pytest
```

```bash
# Ingest a repo and print symbols as JSON
cd backend
uv run python -m codegraph.ingest /path/to/any/repo
```

Docker Compose is a stub — Dockerfiles are not yet written:

```bash
docker compose up  # not functional yet
```

---

## Repository layout

```
codegraph-agent/
├── backend/                   # Python / FastAPI
│   ├── pyproject.toml         # uv-managed; ruff + pytest configured
│   └── src/codegraph/
│       ├── __init__.py
│       ├── main.py            # FastAPI app + /health endpoint
│       └── ingest/            # M2: tree-sitter ingestion
│           ├── __init__.py    # exports ingest_repo()
│           ├── __main__.py    # CLI: python -m codegraph.ingest <path>
│           ├── models.py      # Symbol dataclass
│           ├── parsers.py     # parse_python(), parse_typescript()
│           └── walker.py      # ingest_repo() directory walker
│   └── tests/
│       ├── test_health.py
│       ├── test_ingest.py     # 10 tests for M2
│       └── fixtures/
│           └── sample_repo/   # sample.py + utils.ts + .hidden/
├── frontend/                  # Vite + React + TypeScript
│   ├── package.json
│   ├── vite.config.ts
│   ├── tsconfig.json
│   └── src/
│       ├── main.tsx
│       └── App.tsx
├── docker-compose.yml         # stub
├── .pre-commit-config.yaml
├── .gitignore
└── README.md
```

---

## Why this is portfolio-strong

- **KG-as-tool** is a rare, senior-signal pattern — most people default to vector RAG
- Live graph animation makes results screenshot-able and GIF-able
- Every layer (parser → graph → tool → agent loop → streaming UI) is a distinct engineering artifact reviewers can inspect
- Runs locally on the Anthropic free tier

---

## License

MIT © 2026 Ritik
