# Installation Guide — Raspberry Pi 3

## Prerequisites

- Raspberry Pi 3 Model B or B+
- MicroSD card (16 GB minimum, Class 10 recommended)
- Raspberry Pi OS Lite (Bookworm / 64-bit or Bullseye / 32-bit)
- Internet access (Ethernet or USB WiFi dongle) for the initial install

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

# Configure the virtual AP interface (uap0) for first-boot hotspot
sudo bash scripts/02-setup-hotspot.sh

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
- Starts the hotspot and Flask app

---

## Step 6 — First Boot Access

1. On your phone or laptop, connect to WiFi: **RaspiSetup** (password: `raspisetup123`)
2. Open browser: `http://192.168.50.1:5000`
3. Go to **WiFi Setup** — scan and connect to your home WiFi
4. The Pi connects and saves credentials persistently

After connecting, access the app:
- **Local network**: `http://raspi-hotspot.local:5000`
- **Admin (anywhere)**: Via Tailscale IP `http://100.x.x.x:5000`
- **Users (anywhere)**: Via ngrok URL shown in Admin Dashboard

---

## Updating

```bash
cd /home/pi/raspi-hotspot
git pull
source .venv/bin/activate
pip install -r backend/requirements.txt
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
