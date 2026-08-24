"""FastAPI application for CodeGraph Agent.

Routes
------
GET  /health   — liveness check with graph stats
POST /ingest   — walk a repo and load its graph into app state
GET  /graph    — return all nodes and edges for the UI
WS   /chat     — stream tool_call / tool_result / text_delta / done events
"""
from __future__ import annotations

import asyncio
import queue
import threading
from contextlib import asynccontextmanager
from pathlib import Path

import networkx as nx
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from codegraph.graph import build_graph, load_graph, save_graph
from codegraph.ingest import ingest_repo

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent
# backend/src/codegraph/ -> backend/sample_repo/
_BACKEND_DIR = _HERE.parent.parent  # backend/
_SAMPLE_REPO = _BACKEND_DIR / "sample_repo"
_KG_CACHE_DIR = _BACKEND_DIR / ".kg_cache"


# ---------------------------------------------------------------------------
# Startup / lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(application: FastAPI):
    _preindex(application)
    yield


def _preindex(application: FastAPI) -> None:
    """Synchronously ingest the bundled sample_repo on startup.

    Uses cached JSON if available so repeated restarts are instant.
    """
    cache_path = _KG_CACHE_DIR / "graph_sample_repo.json"

    if cache_path.exists():
        try:
            g = load_graph(cache_path)
            application.state.graph = g
            application.state.repo_root = _SAMPLE_REPO
            return
        except Exception:
            pass  # corrupt cache → re-ingest below

    if not _SAMPLE_REPO.is_dir():
        # Sample repo missing — start without a graph (non-fatal)
        application.state.graph = None
        application.state.repo_root = None
        return

    symbols = ingest_repo(_SAMPLE_REPO)
    g = build_graph(symbols, _SAMPLE_REPO)
    save_graph(g, cache_path)
    application.state.graph = g
    application.state.repo_root = _SAMPLE_REPO


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(title="CodeGraph Agent", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# HTTP routes
# ---------------------------------------------------------------------------


@app.get("/health")
def health(request: Request) -> dict:
    g: nx.DiGraph | None = getattr(request.app.state, "graph", None)
    return {
        "status": "ok",
        "graph_loaded": g is not None,
        "nodes": g.number_of_nodes() if g is not None else 0,
        "edges": g.number_of_edges() if g is not None else 0,
    }


class IngestRequest(BaseModel):
    repo_path: str


@app.post("/ingest")
def ingest(req: IngestRequest, request: Request) -> dict:
    repo = Path(req.repo_path).resolve()
    if not repo.is_dir():
        raise HTTPException(status_code=400, detail=f"Not a directory: {req.repo_path}")

    symbols = ingest_repo(repo)
    g = build_graph(symbols, repo)

    cache_path = _KG_CACHE_DIR / f"graph_{repo.name}.json"
    save_graph(g, cache_path)

    request.app.state.graph = g
    request.app.state.repo_root = repo

    return {
        "status": "ok",
        "repo": str(repo),
        "nodes": g.number_of_nodes(),
        "edges": g.number_of_edges(),
    }


@app.get("/graph")
def graph_data(request: Request) -> dict:
    g: nx.DiGraph | None = getattr(request.app.state, "graph", None)
    if g is None:
        raise HTTPException(status_code=404, detail="No graph loaded. Call POST /ingest first.")

    # TODO M6: consider pagination or delta updates for large repos
    nodes = [
        {
            "id": node_id,
            "kind": data.get("kind"),
            "name": data.get("name"),
            "file": str(data.get("file", "")),
            "start_line": data.get("start_line"),
            "end_line": data.get("end_line"),
        }
        for node_id, data in g.nodes(data=True)
    ]
    edges = [
        {"source": u, "target": v, "kind": data.get("kind")}
        for u, v, data in g.edges(data=True)
    ]
    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# WebSocket /chat
# ---------------------------------------------------------------------------


@app.websocket("/chat")
async def chat(ws: WebSocket) -> None:
    await ws.accept()
    try:
        payload = await ws.receive_json()
    except WebSocketDisconnect:
        return

    question = payload.get("question", "").strip() if isinstance(payload, dict) else ""
    if not question:
        await ws.send_json({"type": "error", "message": "Missing or empty 'question' field."})
        await ws.close()
        return

    g: nx.DiGraph | None = getattr(ws.app.state, "graph", None)
    repo_root: Path | None = getattr(ws.app.state, "repo_root", None)
    if g is None or repo_root is None:
        await ws.send_json({"type": "error", "message": "No graph loaded. Call POST /ingest first."})
        await ws.close()
        return

    # Lazy import to avoid crashing startup when ANTHROPIC_API_KEY is absent
    try:
        from .agent import run_agent  # noqa: PLC0415
    except RuntimeError as exc:
        await ws.send_json({"type": "error", "message": str(exc)})
        await ws.close()
        return

    event_queue: queue.Queue[dict | None] = queue.Queue()

    def _worker() -> None:
        try:
            for event in run_agent(question, g, repo_root):
                event_queue.put(event)
        except Exception as exc:  # noqa: BLE001
            event_queue.put({"type": "error", "message": str(exc)})
        finally:
            event_queue.put(None)  # sentinel

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    loop = asyncio.get_event_loop()
    try:
        while True:
            event = await loop.run_in_executor(None, event_queue.get)
            if event is None:
                break
            await ws.send_json(event)
        await ws.send_json({"type": "done"})
    except WebSocketDisconnect:
        pass
