# Installation Guide — Raspberry Pi 3 / Pi 2 B

This guide covers two deployment paths:

| Path | Best for |
|------|----------|
| **Docker** (recommended) | Fastest setup, easiest updates, consistent across PC and Pi |
| **Manual** | If you can't install Docker on the Pi, or need full OS-level control |

Dependency files:
- `backend/requirements.txt` = core dependencies (good for local PC dev)
- `backend/requirements-pi.txt` = core + Raspberry Pi GPIO dependencies

---

## Docker Deployment (Recommended)

### Prerequisites

- Docker and Docker Compose installed on the Pi:
  ```bash
  curl -fsSL https://get.docker.com | sh
  sudo usermod -aG docker pi
  # Log out and back in for group change to take effect
  ```
- The project cloned onto the Pi

### 1 — Clone and configure

```bash
git clone https://github.com/benitocalcanho/raspi-hotspot.git
cd raspi-hotspot
```

The `config/.env` file ships with safe defaults — the app starts without editing it.
For a production install, open it and set strong secret keys:

```bash
nano config/.env   # set SECRET_KEY and JWT_SECRET_KEY at minimum
```

Generate secret keys:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 2 — Run (desktop / no GPIO)

```bash
docker compose -f docker-compose.prod.yml up -d
```

### 2 — Run (Raspberry Pi, with GPIO relays)

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml up -d
```

This overlay:
- Installs `network-manager` (nmcli) inside the image
- Mounts the host D-Bus socket (`/var/run/dbus`) so the container's `nmcli` talks directly to the Pi's NetworkManager — this is what makes the **WiFi Networks** tab work from the dashboard
- Sets `ENABLE_GPIO=true` and maps `/dev/gpiomem` for relay hardware access

> **Always use the Pi overlay on a Raspberry Pi.** Using only `docker-compose.prod.yml` disables WiFi management and GPIO.

### 3 — Access the app

- **Local**: `http://<pi-ip>:5000`
- **Users remote**: Via ngrok URL shown in Admin Dashboard
- **Admin remote**: Via Tailscale `http://100.x.x.x:5000` (optional backup)

Log in as `admin` / `admin12345` (or whatever you set in `config/.env`). Change the password immediately, then set all other secrets (ngrok token, iCal URL, SMTP) in the dashboard — no `.env` editing needed after this.

### Useful commands

```bash
# Follow logs
docker compose -f docker-compose.prod.yml logs -f

# Stop the app
docker compose -f docker-compose.prod.yml down

# Update to latest image
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d

# Back up the database
docker cp raspi-hotspot:/app/backend/instance/data/raspi.db ./backup.db

# Restore a backup
docker cp ./backup.db raspi-hotspot:/app/backend/instance/data/raspi.db
```

### Persistent data

Docker named volumes keep your data safe across restarts and image updates:

| Volume | Contents |
|--------|----------|
| `raspi_data` | SQLite database (`instance/data/raspi.db`) |
| `raspi_uploads` | Door images uploaded via the dashboard |

---

## Manual Deployment

This focuses on the core application stack:
- user management
- Google Calendar sync
- admin access over Tailscale
- user access over ngrok

The hotspot setup script is optional and not required for the main deployment path.

## Prerequisites

- Raspberry Pi 3 Model B/B+ OR Raspberry Pi 2 B
- MicroSD card (16 GB minimum, Class 10 recommended)
- Raspberry Pi OS Lite (Bookworm / 64-bit or Bullseye / 32-bit)
- Internet access on the Pi (Ethernet or WiFi)

---

## Step 1 — Flash the OS

1. Download **Raspberry Pi OS Lite** from [raspberrypi.com/software](https://www.raspberrypi.com/software/)
2. Flash with **Raspberry Pi Imager**
3. In Imager's advanced options (**Ctrl+Shift+X**):
   - Set hostname: `raspi-hotspot`
   - Enable SSH
   - Set username: `pi` / your password
4. Boot the Pi and connect via SSH or keyboard

---

## Step 2 — Clone the Project

```bash
cd /home/pi
git clone https://github.com/YOUR_USER/raspi-hotspot.git
cd raspi-hotspot
```

---

## Step 3 — Run the Setup Scripts

Run each script in order:

```bash
# System dependencies, Python venv, directory setup
sudo bash scripts/01-setup-pi.sh

# Install Tailscale (for admin remote access)
sudo bash scripts/03-setup-tailscale.sh
sudo tailscale up   # Follow the authentication link

# Install ngrok (for user remote access)
sudo bash scripts/04-setup-ngrok.sh
```

---

## Step 4 — Configure Environment

```bash
nano /home/pi/raspi-hotspot/config/.env
```

Fill in the minimum required values:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Random 64-char hex string |
| `JWT_SECRET_KEY` | Random 64-char hex string |
| `ADMIN_PASSWORD` | Your admin account password |

All other operational secrets (ngrok token, iCal URL, SMTP, cleaner password) are configured later in the admin dashboard — no `.env` editing needed after first boot.

---

## Step 5 — Build Frontend and Start Services

```bash
sudo bash scripts/05-setup-services.sh
```

This:
- Builds the Vue 3 frontend (`npm run build`)
- Installs systemd service units
- Starts the Flask app

---

## Step 6 — Access the App

After the app starts, access it using one of these paths:
- **Local network**: `http://<pi-ip>:5000`
- **Admin (anywhere)**: Via Tailscale IP `http://100.x.x.x:5000`
- **Users (anywhere)**: Via ngrok URL shown in Admin Dashboard

Log in with the bootstrap admin credentials from `config/.env`, then configure everything else in the dashboard (iCal URL, ngrok, SMTP, guest password settings).

---

## Optional — Hotspot Flow

The hotspot setup is not part of the main app deployment anymore. If you later want to revisit it, the script still exists:

```bash
sudo bash scripts/02-setup-hotspot.sh
```

For Raspberry Pi 2 B, this requires a USB WiFi dongle with AP mode support.

---

## Updating

```bash
cd /home/pi/raspi-hotspot
git pull
source .venv/bin/activate
pip install -r backend/requirements-pi.txt
cd frontend && npm install && npm run build
sudo systemctl restart raspi-app
```

---

## Logs

```bash
# Application logs
journalctl -u raspi-app -f

# Hotspot logs
journalctl -u raspi-hotspot -f

# Access logs
tail -f /home/pi/raspi-hotspot/logs/access.log
```
