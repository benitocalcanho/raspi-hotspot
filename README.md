# Raspi Hotspot — Smart Device Platform

A full-stack application for **Raspberry Pi 3** featuring user management, GPIO control,
Google Calendar integration, and dual remote-access layers (Tailscale + ngrok).

## Features

- **First-boot WiFi hotspot** — Pi creates an AP, user connects and configures target WiFi
- **User management** — Admin creates/manages users; role-based access (admin / user)
- **Admin dashboard** — Full system control via Tailscale private network
- **User dashboards** — Isolated per-user views accessible via ngrok public URL
- **Login traceability** — Full audit log of every authentication event
- **GPIO control** — Toggle / read GPIO pins from the web UI
- **Google Calendar sync** — Automatically creates users based on calendar events
- **Remote access**:
  - **Admin**: Tailscale (private, encrypted, works behind CGNAT)
  - **Users**: ngrok free tunnel (HTTPS, accessible from anywhere)

## Architecture

```
                     ┌──────────────────────────────────┐
                     │         Raspberry Pi 3            │
                     │                                   │
  Admin ──Tailscale──▶   Flask API (port 5000)          │
                     │   ├── /api/auth                   │
  User ───ngrok──────▶   ├── /api/admin  (admin only)   │
                     │   ├── /api/user   (per user)      │
                     │   ├── /api/gpio                   │
                     │   ├── /api/wifi   (setup only)    │
                     │   └── /api/calendar               │
                     │                                   │
                     │   Vue 3 SPA (served by Flask)    │
                     │   SQLite Database                 │
                     │   GPIO pins (gpiozero)            │
                     └──────────────────────────────────┘
```

## Project Structure

```
raspi-hotspot/
├── backend/
│   ├── app.py                  # Flask application factory
│   ├── config.py               # Environment-based config
│   ├── requirements.txt        # Python dependencies
│   ├── models/                 # SQLAlchemy ORM models
│   ├── routes/                 # API blueprints
│   ├── services/               # Business logic
│   └── utils/                  # Auth helpers, decorators
├── frontend/                   # Vue 3 SPA
│   ├── src/
│   │   ├── views/              # Login, Admin, User, WiFiSetup
│   │   ├── components/
│   │   ├── router/
│   │   └── stores/             # Pinia state management
│   └── package.json
├── scripts/                    # One-time setup scripts
│   ├── 01-setup-pi.sh
│   ├── 02-setup-hotspot.sh
│   ├── 03-setup-tailscale.sh
│   ├── 04-setup-ngrok.sh
│   └── 05-setup-services.sh
├── config/                     # Config file templates
├── systemd/                    # Systemd service units
├── docs/                       # Documentation
└── tests/                      # Backend tests
```

## Hardware: Raspberry Pi 3

| Component | Detail |
|-----------|--------|
| CPU | ARM Cortex-A53 quad-core 1.2 GHz (32-bit OS) |
| RAM | 1 GB LPDDR2 |
| WiFi | Broadcom BCM43438 (single chip — uses virtual `uap0` AP interface) |
| GPIO | 40-pin header |
| Storage | MicroSD (16 GB minimum recommended) |

> **WiFi note**: Pi 3 has one physical WiFi chip. This project creates a virtual `uap0`
> interface for the hotspot while `wlan0` connects to the target network simultaneously.

## Quick Start

```bash
# 1. Clone and run initial setup
git clone https://github.com/YOUR_USER/raspi-hotspot.git
cd raspi-hotspot
sudo bash scripts/01-setup-pi.sh

# 2. Configure environment
cp config/.env.example config/.env
nano config/.env   # fill in secrets and API keys

# 3. Start the application
sudo systemctl enable --now raspi-app
```

See [docs/INSTALLATION.md](docs/INSTALLATION.md) for full step-by-step instructions.

## Documentation

| Document | Description |
|----------|-------------|
| [docs/INSTALLATION.md](docs/INSTALLATION.md) | Complete install guide |
| [docs/HARDWARE.md](docs/HARDWARE.md) | GPIO wiring and hardware setup |
| [docs/API.md](docs/API.md) | REST API reference |
| [docs/GOOGLE_CALENDAR.md](docs/GOOGLE_CALENDAR.md) | Calendar integration setup |
| [docs/REMOTE_ACCESS.md](docs/REMOTE_ACCESS.md) | Tailscale + ngrok configuration |

## License

MIT
