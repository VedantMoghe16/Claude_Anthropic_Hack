#!/usr/bin/env bash
# Start the Adhikar React frontend (dev server)
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR/WEBSITE/frontend"
echo "Starting frontend on http://localhost:5173 ..."
npm run dev
