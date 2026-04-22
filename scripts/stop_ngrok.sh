#!/bin/bash
# Kill all running ngrok tunnels and processes (for static domain reuse)

set -e

# Kill any running ngrok processes
pkill -f ngrok || true

# Optionally, use ngrok CLI to stop tunnels (if ngrok is running as a service or in the background)
if command -v ngrok &>/dev/null; then
  ngrok tunnels list | awk '/online/ {print $1}' | while read -r tunnel; do
    ngrok tunnels stop "$tunnel" || true
  done
fi

echo "All ngrok tunnels and processes stopped. You can now restart your app safely."
