#!/usr/bin/env bash
# Start the Adhikar Telegram bot
set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Load env vars
set -a
source "$SCRIPT_DIR/.env"
set +a

cd "$SCRIPT_DIR/adhikar_local"
echo "Starting Telegram bot ..."
python bot.py
