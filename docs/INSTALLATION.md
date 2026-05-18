# Installation Guide

This is the canonical install guide for Invisible Key. Use Docker unless you have a specific reason to manage Python, Node, and systemd manually.

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
| OS | Raspberry Pi OS Lite |
| Storage | The microSD card for the Pi |

OS architecture:

| Raspberry Pi | Recommended OS |
|---|---|
| Raspberry Pi 2 B / older 32-bit-only boards | Raspberry Pi OS Lite 32-bit |
| Raspberry Pi 3, 4, 5 | Raspberry Pi OS Lite 64-bit |

For Raspberry Pi 2 B, also read [INSTALL_PI2B.md](INSTALL_PI2B.md). It uses the same Docker deployment, but the OS and expectations are different because the board is 32-bit and has no onboard WiFi.

Before writing the card, open **OS Customisation** and set:

| Setting | Recommended value |
|---|---|
| Hostname | `invisible-key` or another memorable name |
| Username/password | Create the normal Pi login, for example user `pi` with a strong password |
| Wireless LAN | Set the WiFi SSID, password, and WiFi country |
| Locale | Set timezone, keyboard layout, and language |
| SSH | Enable SSH, preferably with your SSH public key; password SSH is acceptable for first install |
| Raspberry Pi Connect | Enable/link it if Imager offers the option |

Raspberry Pi Connect is useful as the recovery/admin shell path when you are away from the local network. It can replace Tailscale for simple remote SSH-style maintenance. It does **not** replace ngrok for guest/admin web access to the app.

If the Pi will connect through a WiFi repeater/range extender, especially with a USB WiFi adapter, disable WiFi MAC randomization after first login. See the WiFi note in [INSTALL_PI2B.md](INSTALL_PI2B.md). Repeaters can use MAC proxying, and local SSH/app access may fail even while ping works unless the WiFi profile is stable.

After writing the card, boot the Pi and wait a minute or two for first-boot setup to finish. Then connect using one of:

```bash
ssh pi@invisible-key.local
ssh pi@<pi-ip>
```

or open Raspberry Pi Connect in a browser and use the remote shell.

## First Boot Setup

Start from a clean Raspberry Pi OS Lite shell. The Lite image is intentionally minimal, so install basic tools before cloning the app:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git curl ca-certificates
```

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
- Network access to pull the image from GitHub Container Registry
- For GPIO hardware: Raspberry Pi with `/dev/gpiomem`

Install Docker on Raspberry Pi 3/4/5 with Raspberry Pi OS 64-bit:

```bash
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker "$USER"
sudo reboot
```

On Raspberry Pi 2 B with Raspberry Pi OS Lite 32-bit Trixie, use [INSTALL_PI2B.md](INSTALL_PI2B.md) instead. Docker's upstream Raspbian repository may not provide a `trixie` release for that board, so the Pi 2 B guide installs `docker.io` and `docker-compose` from Raspberry Pi OS packages.

After reboot, verify:

```bash
docker --version
docker compose version
```

## Install

Clone the repository:

```bash
git clone https://github.com/benitocalcanho/invisible-key.git
cd invisible-key
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
| `invisible_key_data` | SQLite database at `/app/backend/instance/data/invisible_key.db` |
| `invisible_key_uploads` | Door images uploaded through the dashboard |

Back up the database:

```bash
docker cp invisible-key:/app/backend/instance/data/invisible_key.db ./backup.db
```

Restore a database backup:

```bash
docker cp ./backup.db invisible-key:/app/backend/instance/data/invisible_key.db
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

The Docker Compose files cap container logs with Docker's `json-file` log driver:

```yaml
max-size: "5m"
max-file: "3"
```

This keeps recent debugging history while limiting the app container log to about 15 MB.

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
