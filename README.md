
# Raspi Hotspot — Airbnb Guest Access System

A plug-and-play **Raspberry Pi** web app for short-term rental hosts. Guests connect to your local network and get a simple phone-friendly page to unlock building and apartment doors. The admin dashboard manages users, configures all operational secrets via a GUI, and syncs guest accounts automatically from a private iCal URL — no API credentials or .env editing required after install.

## Features

- **Guest dashboard** — Full-screen door cards with photo backgrounds; one-tap unlock buttons (GPIO relay, 5 s pulse)
- **Automatic guest accounts** — Syncs from a private iCal URL; guest created at check-in time, deleted at check-out
- **Calendar-free fallback** — Manual user creation still works
- **Role-based access** — `admin` / `user` / `cleaner` / `guest`
- **Admin dashboard** — User management, audit log, calendar sync, schedule settings, door image uploads
- **Settings GUI** — Paste all secrets (iCal URL, ngrok token, WiFi, SMTP, etc.) in the browser — no SSH or .env editing needed after initial setup
- **Audit log** — Every login, creation, and deletion recorded with IP and device info
- **GPIO relay control** — Unlock door buttons trigger configurable GPIO pins for 5 seconds
- **Remote access** — Admin dashboard via ngrok public URL (primary); Tailscale as backup for admin access if ngrok is unavailable

## How It Works

1. Admin pastes the private iCal URL in **Settings** (no Google API needed)
2. Every day at the configured check-in time (default 14:00), the app fetches today's calendar events — the first word of the event title becomes the guest's username
3. The guest logs in on their phone and sees two door cards; tapping a button fires a GPIO relay
4. At check-out time (default 12:00 the next day), the guest account is deleted automatically

## Architecture

```
                     ┌──────────────────────────────────────┐
                     │           Raspberry Pi               │
                     │                                      │
  Admin ──Tailscale──▶  Flask API (port 5000)              │
                     │  ├── /api/auth                       │
  Guest ────ngrok────▶  ├── /api/admin   (admin only)      │
                     │  ├── /api/user    (all roles)        │
                     │  ├── /api/uploads (door images)      │
                     │  ├── /api/gpio    (relay control)    │
                     │  └── /api/calendar (iCal sync)       │
                     │                                      │
                     │  Vue 3 SPA (served by Flask)         │
                     │  SQLite Database                     │
                     │  APScheduler (2 daily cron jobs)     │
                     │  GPIO pins via gpiozero              │
                     └──────────────────────────────────────┘
```

## Project Structure

```
raspi-hotspot/
├── backend/
│   ├── app.py                  # Flask application factory + SPA serving
│   ├── config.py               # Only non-sensitive defaults; all secrets in DB
│   ├── requirements.txt        # Python dependencies
│   ├── uploads/                # Door images uploaded via admin dashboard
│   ├── models/
│   │   ├── user.py             # User model (role, created_by, is_active)
│   │   ├── setting.py          # DB-backed key/value store for all runtime secrets
│   │   └── audit_log.py        # Login/event audit trail
│   ├── routes/
│   │   ├── auth.py             # Login, logout, /me — case-insensitive
│   │   ├── admin.py            # User CRUD, settings PATCH, scheduler restart (all settings from DB)
│   │   ├── user.py             # Dashboard endpoint (all roles)
│   │   ├── uploads.py          # Door image upload + serve
│   │   ├── calendar_sync.py    # Manual sync trigger
│   │   ├── wifi.py             # WiFi status
│   │   └── gpio.py             # GPIO pin toggle (optional, guarded by ENABLE_GPIO)
│   ├── services/
│   │   ├── calendar_service.py # iCal fetch, guest create/delete, APScheduler
│   │   ├── gpio_service.py     # gpiozero abstraction with mock fallback
│   │   ├── audit_service.py    # Log creation helpers
│   │   └── wifi_service.py     # nmcli wrappers
│   └── utils/
│       └── decorators.py       # require_roles, tailscale_required
├── frontend/
│   ├── src/
│   │   ├── App.vue             # Root — NavBar hidden for guests
│   │   ├── api.js              # Axios instance + JWT interceptor
│   │   ├── views/
│   │   │   ├── Login.vue
│   │   │   ├── GuestDashboard.vue   # Two door cards, full-screen, mobile-first
│   │   │   ├── AdminDashboard.vue   # Tabs: Users, Audit, Calendar, Settings, Door Images
│   │   │   ├── CleanerDashboard.vue
│   │   │   └── UserDashboard.vue
│   │   ├── components/
│   │   │   ├── NavBar.vue
│   │   │   ├── SettingsPanel.vue    # iCal URL, schedule times, ngrok token
│   │   │   ├── UserTable.vue
│   │   │   └── AuditLog.vue
│   │   ├── router/index.js          # Role-gated routes
│   │   └── stores/auth.js           # Pinia auth store
│   ├── dist/                        # Built SPA (served by Flask)
│   └── vite.config.js
├── scripts/                    # One-time Raspberry Pi setup scripts
├── systemd/                    # Systemd service units
└── tests/                      # Backend tests
```

## Quick Install on Raspberry Pi

You can deploy this project on a fresh Raspberry Pi in minutes:

```bash
git clone https://github.com/YOUR_USER/raspi-hotspot.git
cd raspi-hotspot
sudo bash scripts/01-setup-pi.sh
```

This script will:
- Update your system and install all dependencies (Python, Node.js, hostapd, etc.)
- Set up a Python virtual environment
- Install backend and frontend dependencies
- Prepare the data directory

After running the script, open a browser to your Pi's IP (or ngrok URL) and log in as admin. **All secrets and settings are configured via the dashboard — no file editing or SSH required after install.**

For advanced setup (hotspot, Tailscale, ngrok, systemd), see the scripts in the `scripts/` folder and follow the step-by-step comments in each script.

---

### Prerequisites

- Raspberry Pi (any model with network access)
- A private iCal URL (from your calendar provider; Google, Apple, Outlook, etc.)

### 1 — Install dependencies

```bash
git clone https://github.com/YOUR_USER/raspi-hotspot.git
cd raspi-hotspot

# Backend
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd ../frontend
npm install
npm run build
```

### 2 — Run

```bash
cd backend
source .venv/bin/activate
python app.py
```

Open **http://<pi-ip>:5000** — log in as admin (default credentials: admin / admin12345).

### 3 — Configure all settings in the browser

Log in as admin → **Settings** tab → paste your iCal URL, ngrok token, WiFi, SMTP, and any other secrets. All operational settings are stored in the database and take effect immediately. No .env or SSH needed after install.

## Environment Variables

All operational secrets (iCal URL, ngrok, WiFi, SMTP, etc.) are now managed via the dashboard and stored in the database. The only environment variables you may need are for initial admin bootstrap or development:

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | random on each start | Flask/JWT secret — **set a fixed value in production** |
| `ADMIN_USERNAME` | `admin` | Initial admin username (used only if no admin exists) |
| `ADMIN_PASSWORD` | `admin12345` | Initial admin password (used only if no admin exists) |

After first login, set all other secrets in the dashboard. No .env editing required for normal operation.

## Calendar Guest Sync

The scheduler runs two cron jobs daily:

| Time | Action |
|---|---|
| `CHECKOUT_TIME` (12:00) | Deletes all `guest` accounts created by the calendar |
| `CHECKIN_TIME` (14:00) | Fetches iCal URL, finds today's events, creates guest account |

The **first word** of the calendar event title becomes the username (lowercased). Passwords are set from the dashboard setting. Login is case-insensitive.

To trigger sync manually: Admin dashboard → **Calendar Sync** tab → **Sync Now**.

To change times or passwords without restarting: update **Settings** in the dashboard.

## Door Images

Upload photos from **Admin Dashboard → Door Images** tab. Images are stored in `backend/uploads/` and served at `/api/uploads/<filename>`. Guests see them as full-screen card backgrounds immediately after upload.

## Remote Access

| User  | Method         | URL                                 |
|-------|----------------|-------------------------------------|
| Admin | ngrok (primary)| `https://<your-domain>.ngrok.io`    |
| Admin | Tailscale (backup) | `http://<tailscale-ip>:5000`     |
| Guests| ngrok          | `https://<your-domain>.ngrok.io`    |

**Admin dashboard is always accessible via ngrok.** Tailscale is recommended as a backup for admin access to the host machine in case ngrok disconnects or is unavailable. No physical access to the Raspberry Pi is required after deployment.

Set ngrok settings in the dashboard. Run `scripts/04-setup-ngrok.sh` for systemd autostart.

## Development

```bash
# Terminal 1 — Flask with hot reload
cd backend && source .venv/bin/activate && python app.py

# Terminal 2 — Vite dev server (hot reload on port 5173, proxies API to 5000)
cd frontend && npm run dev
```

Open `http://localhost:5173` for live development. Use an incognito window to test the guest view simultaneously.

After frontend changes for production:
```bash
cd frontend && npm run build
```

## Hardware — GPIO Wiring

| GPIO Pin | Function |
|---|---|
| Configurable | Building door relay (5 s pulse) |
| Configurable | Apartment door relay (5 s pulse) |

Set `ENABLE_GPIO=true` to activate relay routes. On non-Pi hardware the service falls back to mock mode automatically.

See [docs/HARDWARE.md](docs/HARDWARE.md) for wiring diagrams.

## License

MIT

