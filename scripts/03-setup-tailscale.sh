#!/usr/bin/env bash
# =============================================================================
# 03-setup-tailscale.sh — Install and authenticate Tailscale on Pi 3 (ARMv7)
# =============================================================================
set -euo pipefail

echo "==> Installing Tailscale..."
curl -fsSL https://tailscale.com/install.sh | sh

echo "==> Enabling Tailscale service..."
systemctl enable --now tailscaled

echo ""
echo "==> To authenticate, run:"
echo "    sudo tailscale up"
echo ""
echo "    This opens a browser link. After authentication:"
echo "    - Your Pi gets a stable Tailscale IP (100.x.x.x)"
echo "    - The admin dashboard is accessible from any Tailscale device"
echo "    - Works behind CGNAT with no port forwarding needed"
echo ""
echo "==> Optional: enable subnet routing (exposes local LAN via Tailscale)"
echo "    sudo tailscale up --advertise-routes=192.168.1.0/24 --accept-dns=false"
