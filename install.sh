#!/usr/bin/env bash
# ============================================================
#  install.sh — One-command Raspi Hotspot installer
#
#  Run on your Raspberry Pi (or any Linux machine):
#    curl -fsSL https://raw.githubusercontent.com/benitocalcanho/raspi-hotspot/main/install.sh | bash
#
#  What this script does:
#    1. Installs Docker if not already present
#    2. Downloads docker-compose.prod.yml and config/.env.example
#    3. Prompts you to fill in the required secrets
#    4. Starts the container (pulls the pre-built image — no build needed)
# ============================================================

set -euo pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BOLD='\033[1m'; NC='\033[0m'
info()    { echo -e "${GREEN}[raspi-hotspot]${NC} $*"; }
warn()    { echo -e "${YELLOW}[raspi-hotspot]${NC} $*"; }
fatal()   { echo -e "${RED}[raspi-hotspot] ERROR:${NC} $*" >&2; exit 1; }

# ── Config ────────────────────────────────────────────────────────────────────
REPO_RAW="https://raw.githubusercontent.com/benitocalcanho/raspi-hotspot/main"
INSTALL_DIR="${INSTALL_DIR:-$HOME/raspi-hotspot}"

# ── Docker check / install ────────────────────────────────────────────────────
if ! command -v docker &>/dev/null; then
  info "Docker not found — installing via get.docker.com …"
  curl -fsSL https://get.docker.com | sh
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
  fatal "Docker Compose plugin not found. Please update Docker or install manually:\n  https://docs.docker.com/compose/install/"
fi

# ── Create install directory ──────────────────────────────────────────────────
mkdir -p "$INSTALL_DIR/config"
cd "$INSTALL_DIR"
info "Installing to $INSTALL_DIR"

# ── Download compose files ────────────────────────────────────────────────────
info "Downloading docker-compose.prod.yml …"
curl -fsSL "$REPO_RAW/docker-compose.prod.yml" -o docker-compose.prod.yml

info "Downloading docker-compose.pi.yml …"
curl -fsSL "$REPO_RAW/docker-compose.pi.yml"   -o docker-compose.pi.yml

info "Downloading config/.env.example …"
curl -fsSL "$REPO_RAW/config/.env.example"     -o config/.env.example

# ── Create config/.env if not already present ────────────────────────────────
if [[ ! -f config/.env ]]; then
  cp config/.env.example config/.env
  warn "config/.env created from example. Please fill in the required values now."
else
  info "config/.env already exists — skipping copy."
fi

# ── Prompt user to configure secrets ────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BOLD}  Required: edit config/.env before starting${NC}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  At minimum, set these three values:"
echo ""
echo "    SECRET_KEY       — random hex string (see below)"
echo "    JWT_SECRET_KEY   — random hex string (see below)"
echo "    ADMIN_PASSWORD   — your admin password"
echo ""
echo "  Generate secret keys:"
echo "    python3 -c \"import secrets; print(secrets.token_hex(32))\""
echo ""
echo "  All other secrets (ngrok, iCal, SMTP) can be set later in the dashboard."
echo ""

read -r -p "Open config/.env in nano now? [Y/n] " answer
answer="${answer:-Y}"
if [[ "${answer^^}" == "Y" ]]; then
  ${EDITOR:-nano} config/.env
fi

# ── Detect Raspberry Pi ───────────────────────────────────────────────────────
IS_PI=false
if grep -qi "raspberry pi\|bcm27\|bcm28" /proc/cpuinfo 2>/dev/null \
   || [[ -f /sys/firmware/devicetree/base/model ]] && grep -qi "raspberry pi" /sys/firmware/devicetree/base/model 2>/dev/null; then
  IS_PI=true
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

info "Pulling image and starting raspi-hotspot …"
$COMPOSE_CMD up -d

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  raspi-hotspot is running!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  Open in browser:    http://$(hostname -I | awk '{print $1}'):5000"
echo "  Follow logs:        docker compose -f docker-compose.prod.yml logs -f"
echo "  Stop:               docker compose -f docker-compose.prod.yml down"
echo ""
echo "  Log in with the ADMIN_USERNAME / ADMIN_PASSWORD from config/.env"
echo "  Set all remaining secrets (ngrok, iCal, SMTP) in the dashboard."
echo ""
