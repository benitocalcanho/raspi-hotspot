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
systemctl enable raspi-hotspot.service
systemctl enable raspi-app.service

echo "==> Starting services..."
systemctl start raspi-hotspot.service
sleep 3
systemctl start raspi-app.service

echo ""
echo "==> All services are running. Status:"
systemctl status raspi-hotspot.service --no-pager -l || true
systemctl status raspi-app.service --no-pager -l || true
echo ""
echo "==> Setup complete!"
echo "    Hotspot SSID: $(grep HOTSPOT_SSID ${INSTALL_DIR}/config/.env | cut -d= -f2)"
echo "    After connecting to the hotspot, open: http://192.168.50.1:5000"
