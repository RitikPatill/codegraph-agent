# CodeGraph Agent

![Status](https://img.shields.io/badge/status-WIP-orange)
![License](https://img.shields.io/badge/license-MIT-blue)
![M1](https://img.shields.io/badge/M1-scaffold-green)
![M2](https://img.shields.io/badge/M2-ingestion-lightgrey)
![M3](https://img.shields.io/badge/M3-graph--core-lightgrey)
![M4](https://img.shields.io/badge/M4-tools-lightgrey)
![M5](https://img.shields.io/badge/M5-agent--loop-lightgrey)
![M6](https://img.shields.io/badge/M6-streaming--ui-lightgrey)
![M7](https://img.shields.io/badge/M7-cytoscape-lightgrey)
![M8](https://img.shields.io/badge/M8-polish-lightgrey)

> M1 scaffold shipped. Backend and frontend boot; graph ingestion, agent loop, and UI are not yet built.

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

## What works — M1

| Area | Detail |
|---|---|
| Backend scaffold | FastAPI app (`src/codegraph/main.py`), managed with `uv` and `pyproject.toml` |
| Health endpoint | `GET /health` returns `{"status": "ok"}`; covered by a pytest smoke test |
| Frontend scaffold | Vite 6 + React 19 + TypeScript; `pnpm dev` starts the dev server on port 5173 |
| Linting / formatting | ruff-format + ruff lint on all backend Python; prettier on frontend TS/JSON/CSS |
| Pre-commit hooks | Both linters run on commit via `.pre-commit-config.yaml` |
| License | MIT |

Everything else listed in the architecture and roadmap sections is planned, not built.

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

The backend and frontend scaffolds run independently. No graph or agent functionality is wired up yet.

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
│       └── main.py            # FastAPI app + /health endpoint
│   └── tests/
│       └── test_health.py
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
