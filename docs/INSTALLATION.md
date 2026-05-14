# Installation Guide

This is the canonical install guide for Raspi Hotspot. Use Docker unless you have a specific reason to manage Python, Node, and systemd manually.

Calendar schedule times are deployment-local. The app detects the host/container timezone at runtime; set `APP_TIMEZONE` only when a host needs an explicit IANA timezone override such as `Europe/Lisbon`.

## Recommended Path

| Target | Command |
|---|---|
| Desktop or server without GPIO | `docker compose -f docker-compose.prod.yml up -d` |
| Raspberry Pi with relays, reed sensor, or WiFi management | `docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml up -d` |

## Prepare The Raspberry Pi

Use **Raspberry Pi Imager** to flash the SD card. This is the most reliable way to make the Pi headless and reachable before the app is installed.

Recommended Imager choices:

| Imager step | Selection |
|---|---|
| Device | Your Raspberry Pi model |
| OS | Raspberry Pi OS Lite, preferably 64-bit |
| Storage | The microSD card for the Pi |

Before writing the card, open **OS Customisation** and set:

| Setting | Recommended value |
|---|---|
| Hostname | `hotspot` or another memorable name |
| Username/password | Create the normal Pi login, for example user `pi` with a strong password |
| Wireless LAN | Set the WiFi SSID, password, and WiFi country |
| Locale | Set timezone, keyboard layout, and language |
| SSH | Enable SSH, preferably with your SSH public key; password SSH is acceptable for first install |
| Raspberry Pi Connect | Enable/link it if Imager offers the option |

Raspberry Pi Connect is useful as the recovery/admin shell path when you are away from the local network. It can replace Tailscale for simple remote SSH-style maintenance. It does **not** replace ngrok for guest/admin web access to the app.

After writing the card, boot the Pi and wait a minute or two for first-boot setup to finish. Then connect using one of:

```bash
ssh pi@hotspot.local
ssh pi@<pi-ip>
```

or open Raspberry Pi Connect in a browser and use the remote shell.

For headless Raspberry Pi OS Lite installs, enable user lingering so Raspberry Pi Connect can remain available after a reboot before you manually log in:

```bash
loginctl enable-linger
```

On a Raspberry Pi, always include `docker-compose.pi.yml`. The Pi overlay:
- sets `ENABLE_GPIO=true`
- uses the real `gpiozero` driver
- maps `/dev/gpiomem` for GPIO access
- mounts `/var/run/dbus` so the container can talk to the host NetworkManager for WiFi management

Do not add `privileged: true` for normal GPIO use. `/dev/gpiomem` is enough for the relay and reed sensor paths used by this app.

## Prerequisites

- Raspberry Pi OS Lite, prepared with WiFi and SSH through Raspberry Pi Imager, or another Linux host with Docker
- Docker and Docker Compose
- Network access to pull the image from GitHub Container Registry
- For GPIO hardware: Raspberry Pi with `/dev/gpiomem`

Install Docker on Raspberry Pi:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker pi
sudo reboot
```

After reboot, verify:

```bash
docker --version
docker compose version
```

## Install

Clone the repository:

```bash
git clone https://github.com/benitocalcanho/raspi-hotspot.git
cd raspi-hotspot
```

Start on Raspberry Pi:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml up -d
```

Start on desktop or non-GPIO server:

```bash
docker compose -f docker-compose.prod.yml up -d
```

Check status:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml ps
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml logs --tail=200 app
```

## First Login

Open:

```text
http://<pi-ip>:5000
```

Default credentials:

```text
admin / admin12345
```

Change the admin password immediately.

## Configure In The Dashboard

After first login, configure operational settings in the admin dashboard instead of editing `.env`:

| Setting | Dashboard area |
|---|---|
| Admin/users/cleaner accounts | Users / Calendar Sync |
| iCal URL | Calendar Sync |
| Guest password mode | Calendar Sync |
| Check-in / check-out times | Calendar Sync |
| ngrok token and static domain | ngrok Tunnel |
| SMTP notifications | Email |
| Saved WiFi networks | WiFi Networks |
| Door photos | Door Images |

Only bootstrap secrets belong in environment variables:

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Flask signing secret |
| `JWT_SECRET_KEY` | JWT signing secret |
| `ADMIN_USERNAME` | Initial admin username |
| `ADMIN_PASSWORD` | Initial admin password |
| `APP_TIMEZONE` | Optional timezone override |

## Persistent Data

Docker named volumes keep runtime data across container updates:

| Volume | Contents |
|---|---|
| `raspi_data` | SQLite database at `/app/backend/instance/data/raspi.db` |
| `raspi_uploads` | Door images uploaded through the dashboard |

Back up the database:

```bash
docker cp raspi-hotspot:/app/backend/instance/data/raspi.db ./backup.db
```

Restore a database backup:

```bash
docker cp ./backup.db raspi-hotspot:/app/backend/instance/data/raspi.db
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml restart app
```

## Updates

For repeatable Raspberry Pi updates, use [DEPLOY_PI.md](DEPLOY_PI.md).

Short version:

```bash
git pull --ff-only
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml pull app
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml up -d --force-recreate app
```

## Logs

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml logs -f app
```

## Optional Manual Install

The Docker image is the supported path. The old setup scripts are still present for manual/systemd installs, but they are secondary:

```bash
sudo bash scripts/01-setup-pi.sh
sudo bash scripts/04-setup-ngrok.sh
sudo bash scripts/05-setup-services.sh
```

Use this path only when Docker is not available or when you intentionally want OS-level control.

## Optional Hotspot Script

The hotspot setup is not part of the main deployment path. If you later need a first-boot hotspot flow:

```bash
sudo bash scripts/02-setup-hotspot.sh
```

Raspberry Pi 2 B generally needs a USB WiFi adapter with AP mode support.
