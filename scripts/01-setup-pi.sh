#!/usr/bin/env bash
# =============================================================================
# 01-setup-pi.sh — Initial Raspberry Pi 3 / Pi 2 B system preparation
# Run once as root / sudo bash scripts/01-setup-pi.sh
# =============================================================================
set -euo pipefail

INSTALL_DIR="/home/pi/invisible-key"
PYTHON_MIN="3.9"

echo "==> Updating system packages..."
apt-get update -y
apt-get upgrade -y

echo "==> Installing system dependencies..."
apt-get install -y \
    python3 python3-pip python3-venv \
    git curl wget \
    hostapd dnsmasq \
    network-manager \
    nodejs npm \
    iw wireless-tools

echo "==> Enabling NetworkManager and disabling dhcpcd conflict..."
systemctl enable --now NetworkManager
systemctl disable dhcpcd 2>/dev/null || true

echo "==> Creating application directory..."
mkdir -p "${INSTALL_DIR}"
chown pi:pi "${INSTALL_DIR}"

echo "==> Setting up Python virtual environment..."
sudo -u pi python3 -m venv "${INSTALL_DIR}/.venv"
sudo -u pi "${INSTALL_DIR}/.venv/bin/pip" install --upgrade pip

echo "==> Installing Python dependencies..."
sudo -u pi "${INSTALL_DIR}/.venv/bin/pip" install -r "${INSTALL_DIR}/backend/requirements-pi.txt"

echo "==> Creating data directory for SQLite..."
mkdir -p "${INSTALL_DIR}/backend/data"
chown -R pi:pi "${INSTALL_DIR}/backend/data"

echo "==> Copying config from template (if not already present)..."
if [ ! -f "${INSTALL_DIR}/config/.env" ]; then
    cp "${INSTALL_DIR}/config/.env.example" "${INSTALL_DIR}/config/.env"
    echo "  !! EDIT ${INSTALL_DIR}/config/.env before starting the app !!"
fi

echo ""
echo "==> Step 1 complete. Next steps:"
echo "    1. Edit config/.env with your settings"
echo "    2. Run scripts/02-setup-hotspot.sh"
echo "    3. Run scripts/03-setup-tailscale.sh"
echo "    4. Run scripts/04-setup-ngrok.sh"
echo "    5. Run scripts/05-setup-services.sh"
