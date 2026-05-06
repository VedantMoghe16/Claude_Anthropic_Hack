#!/usr/bin/env bash
# Start the Adhikar FastAPI backend
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load env vars so uvicorn subprocess inherits them
set -a
source "$SCRIPT_DIR/.env"
set +a

cd "$SCRIPT_DIR/WEBSITE/backend"
echo "Starting backend on http://127.0.0.1:8000 ..."
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
