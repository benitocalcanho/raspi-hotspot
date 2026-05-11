#!/bin/bash
# Rebuild frontend and restart Flask backend for ngrok users

set -e

cd "$(dirname "$0")"

cd frontend
npm run build
cd ../backend
pkill -f "python app.py" || true
if [ -x ".venv/bin/python" ]; then
	nohup .venv/bin/python app.py > flask.log 2>&1 &
else
	nohup python3 app.py > flask.log 2>&1 &
fi
echo "Frontend rebuilt and Flask restarted."
