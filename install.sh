#!/usr/bin/env bash
# ============================================================
#  install.sh — One-command Invisible Key installer
#
#  Run on your Raspberry Pi (or any Linux machine):
#    curl -fsSL https://raw.githubusercontent.com/benitocalcanho/invisible-key/main/install.sh | bash
#
#  What this script does:
#    1. Installs Docker if not already present
#    2. Downloads docker-compose.prod.yml and .env.example
#    3. Prompts you to fill in optional bootstrap secrets
#    4. Starts the container (pulls the pre-built image — no build needed)
# ============================================================

set -euo pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${GREEN}[invisible-key]${NC} $*"; }
warn()    { echo -e "${YELLOW}[invisible-key]${NC} $*"; }
fatal()   { echo -e "${RED}[invisible-key] ERROR:${NC} $*" >&2; exit 1; }

# ── Config ────────────────────────────────────────────────────────────────────
REPO_RAW="https://raw.githubusercontent.com/benitocalcanho/invisible-key/main"
INSTALL_DIR="${INSTALL_DIR:-$HOME/invisible-key}"

# ── Host detection ───────────────────────────────────────────────────────────
IS_PI=false
if grep -qi "raspberry pi\|bcm27\|bcm28" /proc/cpuinfo 2>/dev/null \
   || [[ -f /sys/firmware/devicetree/base/model ]] && grep -qi "raspberry pi" /sys/firmware/devicetree/base/model 2>/dev/null; then
  IS_PI=true
fi

IS_32BIT_TRIXIE=false
if [[ "$(dpkg --print-architecture 2>/dev/null || true)" == "armhf" ]] \
   && grep -q "VERSION_CODENAME=trixie" /etc/os-release 2>/dev/null; then
  IS_32BIT_TRIXIE=true
fi

# ── Docker check / install ────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  if [[ "$IS_PI" == "true" && "$IS_32BIT_TRIXIE" == "true" ]]; then
    info "Docker not found — installing Raspberry Pi OS packages for 32-bit Trixie …"
    sudo rm -f /etc/apt/sources.list.d/docker.list
    sudo apt update
    sudo apt install -y docker.io docker-compose
    sudo systemctl enable --now docker
  else
    info "Docker not found — installing via get.docker.com …"
    curl -fsSL https://get.docker.com | sh
  fi
  # Add current user to docker group so we don't need sudo for docker commands
  sudo usermod -aG docker "$USER"
  warn "Added $USER to the 'docker' group."
  warn "You may need to log out and back in for this to take effect."
  warn "If docker commands fail, run:  newgrp docker"
else
  info "Docker $(docker --version) already installed."
fi

# ── Docker Compose check ──────────────────────────────────────────────────────
if ! docker compose version &>/dev/null 2>&1; then
  fatal "Docker Compose plugin not found. On Raspberry Pi OS 32-bit Trixie, install it with:\n  sudo apt install -y docker-compose"
fi

# ── Create install directory ──────────────────────────────────────────────────
mkdir -p "$INSTALL_DIR"
cd "$INSTALL_DIR"
info "Installing to $INSTALL_DIR"

# ── Download compose files ────────────────────────────────────────────────────
info "Downloading docker-compose.prod.yml …"
curl -fsSL "$REPO_RAW/docker-compose.prod.yml" -o docker-compose.prod.yml

info "Downloading docker-compose.pi.yml …"
curl -fsSL "$REPO_RAW/docker-compose.pi.yml"   -o docker-compose.pi.yml

info "Downloading .env.example …"
curl -fsSL "$REPO_RAW/.env.example"            -o .env.example

# ── Create .env if not already present ───────────────────────────────────────
if [[ ! -f .env ]]; then
  cp .env.example .env
  warn ".env created from example. You can adjust bootstrap defaults now."
else
  info ".env already exists — skipping copy."
fi

# ── Prompt user to configure secrets ────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  Optional: review .env before starting${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  The app works with defaults, then lets you configure ngrok, iCal, SMTP,"
echo "  users, and passwords from the admin dashboard."
echo ""
echo "  For production, you may change ADMIN_PASSWORD and generate secret keys:"
echo "    python3 -c \"import secrets; print(secrets.token_hex(32))\""
echo ""

read -r -p "Open .env in nano now? [y/N] " answer
answer="${answer:-N}"
if [[ "${answer^^}" == "Y" ]]; then
  ${EDITOR:-nano} .env
fi

# ── Start the container ───────────────────────────────────────────────────────
echo ""
if [[ "$IS_PI" == "true" ]]; then
  info "Raspberry Pi detected — enabling GPIO overlay."
  COMPOSE_CMD="docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml"
else
  warn "Not a Raspberry Pi — running without GPIO overlay."
  COMPOSE_CMD="docker compose -f docker-compose.prod.yml"
fi

info "Pulling image and starting invisible-key …"
$COMPOSE_CMD up -d

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  invisible-key is running!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Open in browser:    http://$(hostname -I | awk '{print $1}'):5000"
echo "  Follow logs:        docker compose -f docker-compose.prod.yml logs -f"
echo "  Stop:               docker compose -f docker-compose.prod.yml down"
echo ""
echo "  Log in with the ADMIN_USERNAME / ADMIN_PASSWORD from .env or defaults"
echo "  Set all remaining secrets (ngrok, iCal, SMTP) in the dashboard."
echo ""
