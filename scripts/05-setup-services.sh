#!/usr/bin/env bash
# =============================================================================
# 05-setup-services.sh — Install systemd units and build the frontend
# =============================================================================
set -euo pipefail

INSTALL_DIR="/home/pi/raspi-hotspot"

echo "==> Building Vue 3 frontend..."
cd "${INSTALL_DIR}/frontend"
sudo -u pi npm install
sudo -u pi npm run build
echo "  Frontend built → frontend/dist/"

echo "==> Installing systemd service units..."
cp "${INSTALL_DIR}/systemd/"*.service /etc/systemd/system/
systemctl daemon-reload

echo "==> Enabling services..."
systemctl enable raspi-app.service

echo "==> Starting services..."
systemctl start raspi-app.service

echo ""
echo "==> All services are running. Status:"
systemctl status raspi-app.service --no-pager -l || true
echo ""
echo "==> Setup complete!"
echo "    App URL on local network: http://<pi-ip>:5000"
echo "    Admin access: use your Tailscale IP on port 5000"
echo "    User access: use the ngrok URL shown in the admin dashboard"
echo ""
echo "    Optional hotspot setup remains available via scripts/02-setup-hotspot.sh"
