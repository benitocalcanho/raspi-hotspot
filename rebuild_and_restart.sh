#!/bin/bash
# Rebuild frontend and restart Flask backend for ngrok users

set -e

cd "$(dirname "$0")"

cd frontend
npm run build
cd ../backend
pkill -f "python app.py" || true
nohup python app.py > flask.log 2>&1 &
echo "Frontend rebuilt and Flask restarted."
