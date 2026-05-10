# Raspberry Pi 3 B+ — Step-by-Step Installation Log

This document tracks the exact steps taken to install the app on a Raspberry Pi 3 B+.
It serves as a repeatable reference for future installs.

---

## Hardware

- Raspberry Pi 3 Model B+
- MicroSD card (Class 10 recommended, **16 GB+**; 8 GB is too small with Pi OS Full)
- Power supply (5V / 2.5A minimum)

---

## Step 1 — Flash the OS

**Tool:** Raspberry Pi Imager

**OS:** **Raspberry Pi OS Lite (64-bit)** — headless, no desktop

> ⚠️ Do **not** use the Full (desktop) version on an 8 GB card — it fills ~6 GB and leaves no room for Docker images.
> Lite uses ~1.5 GB, leaving ~4.5 GB free.

**Imager advanced options configured:**
- WiFi SSID and password
- Raspberry Connect enabled
- SSH enabled
- Hostname: _(default or custom)_
- Username: `pi` (or custom)

Flash to SD card, insert into Pi, power on.

**Result:** Pi connected to WiFi. Accessible via Raspberry Connect and SSH. ✅

---

## Step 2 — Initial OS Setup

```bash
sudo apt update && sudo apt upgrade -y
```

> ℹ️ Pi OS Lite expands the filesystem automatically on first boot. No manual step needed.

**Result:** ✅ (automatic)

---

## Step 3 — Prevent Sleep / Suspend

The Pi must never sleep — it runs 24/7 as a server.

```bash
# Disable screen blanking (console)
sudo raspi-config nonint do_blanking 1

# Disable system suspend/sleep/hibernate
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target

# Don't wait for network on boot (faster startup, avoids boot hang)
sudo systemctl disable NetworkManager-wait-online.service
```

**Result:** ✅

---

## Step 4 — Install Docker

Created a directory for Docker-related files:
```bash
mkdir ~/docker
cd ~/docker
```

Installed Docker using the official Debian script:
```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker pi   # replace 'pi' with your username if different
```

Log out and back in (or reboot) for the group change to take effect:
```bash
sudo reboot
```

Verify:
```bash
docker --version
docker compose version
```

**Result:** Docker 29.4.3, Docker Compose v5.1.3 ✅

---

## Step 5 — Clone the Project

```bash
cd ~/docker
git clone https://github.com/benitocalcanho/raspi-hotspot.git
cd raspi-hotspot
```

**Result:** ✅

---

## Step 6 — Start the App

On the Pi, always use the Pi overlay (`docker-compose.pi.yml`). This enables:
- GPIO relay control (`/dev/gpiomem`)
- WiFi management from the dashboard (mounts host D-Bus socket so the container's `nmcli` talks to the Pi's NetworkManager)

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml up -d
```

This automatically pulls `ghcr.io/benitocalcanho/raspi-hotspot:latest` (linux/arm64 for 64-bit OS).
No build step required.

Check it's running:
```bash
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs -f
```

**Result:** _(pending)_

---

## Step 7 — Access the App

Find the Pi's IP address:
```bash
hostname -I
```

Open in a browser on any device on the same network:
```
http://<pi-ip>:5000
```

Default login: `admin` / `admin12345`

**Change the admin password immediately.**

**Result:** _(pending)_

---

## Step 8 — Configure in the Dashboard

All secrets are configured via the Admin Dashboard — no SSH or `.env` editing needed:

| Setting | Where |
|---------|-------|
| ngrok authtoken + static domain | Settings → ngrok Tunnel |
| iCal URL | Calendar Sync → Google Calendar (iCal) |
| Guest password mode | Calendar Sync → Guest Password |
| Check-in / check-out times | Calendar Sync → Guest Schedule |
| Cleaner username + password | Calendar Sync → Cleaner Account |
| SMTP email | Email tab |
| Door images | Door Images tab |

**Result:** _(pending)_

---

## Step 9 — (Optional) GPIO Relay Control

If you have relay hardware connected to the Pi GPIO pins, stop the container and restart with the Pi overlay:

```bash
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml up -d
```

This enables `gpiozero` and maps `/dev/gpiomem` into the container.

Configure GPIO pin numbers in Admin Dashboard → GPIO.

**Result:** _(pending)_

---

## Useful Commands

```bash
# View logs
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml logs -f

# Stop
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml down

# Update to latest image
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml up -d

# Back up the database
docker cp raspi-hotspot:/app/backend/instance/data/raspi.db ./backup.db

# Restore a backup
docker cp ./backup.db raspi-hotspot:/app/backend/instance/data/raspi.db
```

---

## Notes / Issues Encountered

_(Add any issues and solutions here as the install progresses)_
