#!/usr/bin/env bash
set -euo pipefail

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )/.." && pwd )"
cd "$DIR"

echo "=========================================================="
echo "  🚀 Starting Viralist AI Video Editor (Dual Engine + MCP)"
echo "=========================================================="

# Check if frontend is built
if [ ! -f "frontend/dist/index.html" ]; then
    echo "📦 Building frontend for the first time..."
    npm --prefix frontend ci
    npm --prefix frontend run build
fi

echo "⚡ Starting Backend API & MCP Server on http://localhost:8080"
export PYTHONPATH="$DIR/backend${PYTHONPATH:+:$PYTHONPATH}"
if [[ -x "$DIR/.venv/bin/python" ]]; then
    exec "$DIR/.venv/bin/python" backend/main.py
fi
exec python3 backend/main.py
