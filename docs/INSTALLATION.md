# Installation Guide — Raspberry Pi 3 / Pi 2 B

This guide focuses on the core application stack:
- user management
- Google Calendar sync
- admin access over Tailscale
- user access over ngrok

The hotspot setup script is optional and not required for the main deployment path.

Dependency files:
- `backend/requirements.txt` = core dependencies (good for local PC dev)
- `backend/requirements-pi.txt` = core + Raspberry Pi GPIO dependencies

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

Fill in all required values:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Random 64-char hex string |
| `JWT_SECRET_KEY` | Random 64-char hex string |
| `ADMIN_PASSWORD` | Your admin account password |
| `NGROK_AUTHTOKEN` | From ngrok dashboard |
| `NGROK_STATIC_DOMAIN` | Optional: your free static domain |
| `GOOGLE_CREDENTIALS_FILE` | Path to OAuth2 JSON |

Generate secret keys:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

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

Log in with the bootstrap admin credentials from `config/.env`, then:
- create users manually in the admin dashboard, or
- configure Google Calendar sync and trigger a sync

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
