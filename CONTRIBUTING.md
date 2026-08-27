# Contributing

## Prerequisites

- Python ≥ 3.11
- [`uv`](https://github.com/astral-sh/uv) (Python package manager)
- Node ≥ 18
- `pnpm`
- `git`

## Dev setup

```bash
git clone https://github.com/ritik-1302/codegraph-agent.git
cd codegraph-agent

# Backend
cd backend
uv sync --extra dev

# Frontend
cd ../frontend
pnpm install

# API key (required for /chat)
export ANTHROPIC_API_KEY=sk-ant-...
```

## Running tests

```bash
# Backend — 51 pytest tests
cd backend
uv run pytest

# Frontend — add tests to src/__tests__/ as the UI grows
cd frontend
# pnpm test  (no frontend tests yet)
```

## Linting

```bash
# Backend
cd backend
uv run ruff check src tests
uv run ruff format --check src tests

# Frontend
cd frontend
pnpm exec prettier --check "src/**/*.{ts,tsx}"
```

## Pre-commit hooks

```bash
pre-commit install
```

After this, ruff and prettier run automatically on every `git commit`. Fix any reported issues before pushing.

## Branch and PR workflow

1. Create a feature branch: `git checkout -b feat/my-feature`
2. Make focused, atomic commits.
3. Open a PR against `main`.
4. PRs are squash-merged — keep the PR title in Conventional Commits format (`feat:`, `fix:`, `docs:`, etc.).

## Adding a new graph tool

1. **`backend/src/codegraph/tools.py`** — add a new function. Follow the existing signature pattern: `def my_tool(g: nx.DiGraph, ...) -> dict`. Return a dict with at least `"nodes"` (list of node-attr dicts) and `"touched_nodes"` (list of node IDs).
2. **`backend/src/codegraph/agent.py`** — add a schema entry to `TOOL_SCHEMAS` (name, description, input_schema).
3. **`backend/src/codegraph/agent.py`** — add a dispatch branch in `_dispatch(tool_name, tool_input, graph, repo_root)`.
4. **`backend/tests/test_tools.py`** — add at least two tests: one for the happy path, one for a missing/invalid node ID.

## Adding a language parser

1. Install the tree-sitter grammar: `uv add tree-sitter-<lang>` (e.g. `tree-sitter-go`).
2. **`backend/src/codegraph/ingest/parsers.py`** — add `parse_<lang>(path: Path) -> list[Symbol]`. Model it on `parse_python` or `parse_typescript`. Extract at minimum: file, class, function/method nodes with line spans.
3. **`backend/src/codegraph/ingest/walker.py`** — register the new extension(s) in the `EXTENSIONS` set (e.g. `".go"`), and add a branch in `_parse_file` that calls your new parser.
4. Add a fixture file (e.g. `backend/tests/fixtures/sample_repo/sample.go`) and extend `test_ingest.py` to assert the new symbols are extracted correctly.
