"""API integration tests for M5 FastAPI backend.

Uses starlette.testclient.TestClient (sync, no asyncio required).
The full agent round-trip (WebSocket /chat with real Claude call) is
intentionally skipped to avoid requiring ANTHROPIC_API_KEY in CI.
"""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from codegraph.main import app

# Path to the existing test fixture repo (no dependency on sample_repo/)
_FIXTURE_REPO = Path(__file__).parent / "fixtures" / "sample_repo"


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_ok():
    """GET /health always returns 200 with status=='ok'."""
    with TestClient(app) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_health_graph_loaded():
    """After lifespan startup, the sample_repo graph should be pre-loaded."""
    with TestClient(app) as client:
        resp = client.get("/health")
    data = resp.json()
    assert data["graph_loaded"] is True
    assert data["nodes"] > 0
    assert data["edges"] >= 0


# ---------------------------------------------------------------------------
# /ingest
# ---------------------------------------------------------------------------


def test_ingest_valid_path():
    """POST /ingest with a real directory returns nodes and edges counts."""
    with TestClient(app) as client:
        resp = client.post("/ingest", json={"repo_path": str(_FIXTURE_REPO)})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["nodes"] > 0
    assert data["edges"] >= 0


def test_ingest_invalid_path():
    """POST /ingest with a non-existent path returns 400."""
    with TestClient(app) as client:
        resp = client.post("/ingest", json={"repo_path": "/nonexistent_path_xyz_123"})
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# /graph
# ---------------------------------------------------------------------------


def test_graph_after_ingest():
    """GET /graph returns non-empty nodes and edges after ingest."""
    with TestClient(app) as client:
        client.post("/ingest", json={"repo_path": str(_FIXTURE_REPO)})
        resp = client.get("/graph")
    assert resp.status_code == 200
    data = resp.json()
    assert "nodes" in data and "edges" in data
    assert len(data["nodes"]) > 0


def test_graph_no_graph_404():
    """GET /graph when app.state.graph is None returns 404."""
    with TestClient(app) as client:
        saved = app.state.graph
        try:
            app.state.graph = None
            resp = client.get("/graph")
        finally:
            app.state.graph = saved
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# WebSocket /chat
# ---------------------------------------------------------------------------


def test_ws_no_graph():
    """WebSocket /chat when state.graph is None returns an error event."""
    with TestClient(app) as client:
        # Force state to None after lifespan loads the graph
        app.state.graph = None
        app.state.repo_root = None
        with client.websocket_connect("/chat") as ws:
            ws.send_json({"question": "What calls Depends?"})
            msg = ws.receive_json()
    assert msg["type"] == "error"


def test_ws_missing_question():
    """WebSocket /chat with an empty payload returns an error event."""
    with TestClient(app) as client:
        with client.websocket_connect("/chat") as ws:
            ws.send_json({})
            msg = ws.receive_json()
    assert msg["type"] == "error"
