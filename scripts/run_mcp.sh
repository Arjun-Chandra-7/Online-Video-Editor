#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="$PROJECT_DIR/backend${PYTHONPATH:+:$PYTHONPATH}"

if [[ -x "$PROJECT_DIR/.venv/bin/python" ]]; then
  exec "$PROJECT_DIR/.venv/bin/python" "$PROJECT_DIR/backend/mcp_server.py"
fi

exec python3 "$PROJECT_DIR/backend/mcp_server.py"
