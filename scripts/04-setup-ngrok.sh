#!/usr/bin/env bash
# =============================================================================
# 04-setup-ngrok.sh — Install ngrok on Raspberry Pi 3 (ARMv7 / ARM64)
# =============================================================================
set -euo pipefail

INSTALL_DIR="/home/pi/raspi-hotspot"

# Detect architecture
ARCH=$(uname -m)
if [[ "$ARCH" == "aarch64" ]]; then
    NGROK_ARCH="arm64"
else
    NGROK_ARCH="arm"
fi

echo "==> Detected architecture: ${ARCH} → using ngrok ${NGROK_ARCH} build"
echo "==> Installing ngrok..."

# Install ngrok via the official apt repository
curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
    | tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
    | tee /etc/apt/sources.list.d/ngrok.list
apt-get update -y
apt-get install -y ngrok

echo ""
echo "==> ngrok installed. Now add your auth token to config/.env:"
echo "    NGROK_AUTHTOKEN=your_token_here"
echo ""
echo "    Get your token at: https://dashboard.ngrok.com/get-started/your-authtoken"
echo ""
echo "==> (Optional) Reserve a free static domain at:"
echo "    https://dashboard.ngrok.com/cloud-edge/domains"
echo "    Then set NGROK_STATIC_DOMAIN=yourname.ngrok-free.app in config/.env"
echo ""
echo "==> The ngrok tunnel is started automatically by the Flask app."
echo "    Tunnel URL is shown in Admin Dashboard → Overview."
