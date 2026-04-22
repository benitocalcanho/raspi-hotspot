#!/bin/bash
# Switch between development and production modes for Raspi Hotspot

set -e

MODE="$1"

if [[ "$MODE" == "dev" ]]; then
  echo "==> Stopping any background Flask server..."
  pkill -f "python app.py" || true
  echo "==> Starting Flask backend (dev mode)..."
  (cd backend && source .venv/bin/activate && python app.py &)
  echo "==> Starting Vite frontend dev server..."
  (cd frontend && npm run dev)
elif [[ "$MODE" == "prod" ]]; then
  echo "==> Building frontend and restarting Flask backend (prod mode)..."
  ./rebuild_and_restart.sh
else
  echo "Usage: $0 [dev|prod]"
  echo "  dev  - Start Flask and Vite dev servers for development (hot reload)"
  echo "  prod - Build frontend and restart Flask backend for production/ngrok"
  exit 1
fi
