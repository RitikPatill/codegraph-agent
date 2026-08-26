#!/usr/bin/env bash
# record_demo.sh — Boot backend + frontend, run scripted demo query, capture screenshot.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# 1. Guard: ANTHROPIC_API_KEY must be set
if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "ERROR: ANTHROPIC_API_KEY is not set. Export it before running this script." >&2
  exit 1
fi

# Register trap before launching background jobs so cleanup always runs
BACKEND_PID=""
FRONTEND_PID=""
cleanup() {
  echo ""
  echo "Cleaning up background processes..."
  [ -n "$BACKEND_PID" ] && kill "$BACKEND_PID" 2>/dev/null || true
  [ -n "$FRONTEND_PID" ] && kill "$FRONTEND_PID" 2>/dev/null || true
}
trap 'cleanup' EXIT INT TERM

# 2. Start backend from inside backend/ so relative paths in main.py resolve correctly
echo "Starting backend..."
(cd "$REPO_ROOT/backend" && uv run uvicorn codegraph.main:app --port 8000) &
BACKEND_PID=$!

# 3. Poll GET /health until graph_loaded==true (max 30 retries, 1s sleep)
echo "Waiting for backend to be ready..."
MAX_RETRIES=30
n=0
until curl -sf http://localhost:8000/health | python -c "import sys,json; d=json.load(sys.stdin); sys.exit(0 if d.get('graph_loaded') else 1)" 2>/dev/null; do
  n=$((n + 1))
  if [ "$n" -ge "$MAX_RETRIES" ]; then
    echo "ERROR: Backend did not become ready after ${MAX_RETRIES}s" >&2
    exit 1
  fi
  sleep 1
done
echo "Backend ready (graph loaded)."

# 4. Start frontend
echo "Starting frontend..."
(cd "$REPO_ROOT/frontend" && pnpm dev --host 0.0.0.0 --port 5173) &
FRONTEND_PID=$!

# 5. Wait for Vite to compile
echo "Waiting for frontend to compile..."
sleep 5

# 6. Run scripted demo query
echo "Running demo query..."
cd "$REPO_ROOT"
uv run --project backend python scripts/demo_query.py

# 7. Capture screenshot (graceful: skip if playwright not installed)
mkdir -p "$REPO_ROOT/docs"
echo "Capturing screenshot..."
uv run --project backend python scripts/capture_screenshot.py

# 8. Write docs/demo.gif placeholder if it doesn't exist
if [ ! -f "$REPO_ROOT/docs/demo.gif" ]; then
  echo "Writing docs/demo.gif placeholder..."
  python -c "
import pathlib
# Minimal valid GIF89a 1x1 transparent
data = bytes([0x47,0x49,0x46,0x38,0x39,0x61,0x01,0x00,0x01,0x00,
              0x80,0x00,0x00,0xFF,0xFF,0xFF,0x00,0x00,0x00,0x21,
              0xF9,0x04,0x01,0x00,0x00,0x00,0x00,0x2C,0x00,0x00,
              0x00,0x00,0x01,0x00,0x01,0x00,0x00,0x02,0x02,0x44,
              0x01,0x00,0x3B])
pathlib.Path('docs/demo.gif').write_bytes(data)
print('docs/demo.gif placeholder written.')
"
fi

echo ""
echo "Done!"
echo "Screenshot saved: docs/screenshot.png"
echo "Demo GIF:         docs/demo.gif"
