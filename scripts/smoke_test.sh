#!/usr/bin/env bash
# smoke_test.sh — Quick sanity check: health endpoint + demo query.
# Requires a running backend (start with: cd backend && uv run uvicorn codegraph.main:app --port 8000)
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "=== Smoke test: GET /health ==="
HEALTH=$(curl -sf http://localhost:8000/health)
echo "$HEALTH"
echo "$HEALTH" | python -c "
import sys, json
d = json.load(sys.stdin)
if not d.get('graph_loaded'):
    print('FAIL: graph_loaded is not true', file=sys.stderr)
    sys.exit(1)
print('PASS: graph_loaded == true')
"

echo ""
echo "=== Smoke test: demo_query.py ==="
cd "$REPO_ROOT"
uv run --project backend python scripts/demo_query.py
echo "PASS: demo_query.py exited 0"

echo ""
echo "All smoke tests passed."
