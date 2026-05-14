
# Raspi Hotspot — Airbnb Guest Access System

A plug-and-play **Raspberry Pi** web app for short-term rental hosts. Guests connect to your local network and get a simple phone-friendly page to unlock building and apartment doors. The admin dashboard manages users, configures all operational secrets via a GUI, and syncs guest accounts automatically from a private iCal URL — no API credentials or .env editing required after install.

## Features

- **Guest dashboard** — Full-screen door cards with photo backgrounds; one-tap unlock buttons (GPIO relay, 5 s pulse)
- **Automatic guest accounts** — Syncs from a private iCal URL; guest account is active for the full duration of the calendar event and deleted once the event ends
- **Calendar-free fallback** — Manual user creation still works
- **Role-based access** — `admin` / `user` / `cleaner` / `guest`
- **Admin dashboard** — User management, audit log, calendar sync, schedule settings, WiFi network management, door image uploads, door sensor log
- **Settings GUI** — Paste all secrets (iCal URL, ngrok token, SMTP, etc.) in the browser — no SSH or .env editing needed after initial setup
- **Audit log** — Every login, creation, and deletion recorded with IP and device info
- **GPIO relay control** — Unlock door buttons trigger configurable GPIO pins for 5 seconds
- **Door sensor log** — Optional reed switch on GPIO23 records open/closed state changes
- **Remote access** — Admin dashboard via ngrok public URL (primary); Tailscale as backup for admin access if ngrok is unavailable

## How It Works

1. Admin pastes the private iCal URL in **Settings** (no Google API needed)
2. Every day at the configured check-in time (default 14:00), the app fetches today's calendar events — the first word of the event title becomes the guest's username
3. The guest logs in on their phone and sees two door cards; tapping a button fires a GPIO relay
4. Each day at check-out time (default 12:00), the app re-checks the calendar — if the event still spans today (multi-day stay) the guest account is kept; once the event ends, the guest account is deleted and the cleaner account is created or reactivated so they can clean between stays

## Architecture

```
                     ┌──────────────────────────────────────┐
                     │           Raspberry Pi               │
                     │                                      │
  Admin ────ngrok────▶  Flask API (port 5000)              │
                     │  ├── /api/auth                       │
  Guest ────ngrok────▶  ├── /api/admin   (admin only)      │
                     │  ├── /api/user    (all roles)        │
  Admin ─Tailscale──▶  ├── /api/uploads (door images)      │
  (backup SSH)       │  ├── /api/wifi    (WiFi management)  │
                     │  ├── /api/gpio    (relay control)    │
                     │  ├── /api/calendar (iCal sync)       │
                     │  └── /api/door    (reed sensor log)  │
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
│   ├── config.py               # Non-sensitive defaults; all secrets in DB
│   ├── requirements.txt        # Core Python dependencies
│   ├── requirements-pi.txt     # Core + Raspberry Pi GPIO dependencies
│   ├── uploads/                # Door images uploaded via admin dashboard
│   ├── models/
│   │   ├── user.py             # User model (role, created_by, is_active, valid_until)
│   │   ├── setting.py          # DB-backed key/value store for runtime settings
│   │   ├── audit_log.py        # Login/event audit trail
│   │   └── door_log.py         # Reed sensor open/closed events
│   ├── routes/
│   │   ├── auth.py             # Login, logout, /me — case-insensitive
│   │   ├── admin.py            # User CRUD, settings PATCH, scheduler restart
│   │   ├── user.py             # Dashboard endpoint (all roles)
│   │   ├── uploads.py          # Door image upload + serve
│   │   ├── calendar_sync.py    # Manual sync trigger
│   │   ├── wifi.py             # WiFi status + admin WiFi management
│   │   ├── gpio.py             # GPIO pin control (guarded by ENABLE_GPIO)
│   │   └── door.py             # Door sensor status/log endpoints
│   ├── services/
│   │   ├── calendar_service.py # iCal fetch, guest create/delete, APScheduler
│   │   ├── gpio_service.py     # gpiozero abstraction with mock fallback
│   │   ├── audit_service.py    # Log creation helpers
│   │   ├── wifi_service.py     # nmcli wrappers (connect, save, list, delete)
│   │   └── reed_sensor_service.py # gpiozero reed switch monitoring
│   └── utils/
│       └── decorators.py       # require_roles
├── frontend/
│   ├── src/
│   │   ├── App.vue             # Root — NavBar hidden for guests
│   │   ├── api.js              # Axios instance + JWT interceptor
│   │   ├── views/
│   │   │   ├── Login.vue
│   │   │   ├── GuestDashboard.vue   # Two door cards, full-screen, mobile-first
│   │   │   ├── AdminDashboard.vue   # Tabs: Users, Audit, Calendar, ngrok, Email, WiFi, Doors, Door Log
│   │   │   ├── CleanerDashboard.vue
│   │   │   └── UserDashboard.vue
│   │   ├── components/
│   │   │   ├── NavBar.vue
│   │   │   ├── SettingsPanel.vue    # All admin settings sections
│   │   │   ├── WifiManager.vue      # Saved networks + add/remove
│   │   │   ├── UserTable.vue
│   │   │   ├── AuditLog.vue
│   │   │   ├── GpioPanel.vue
│   │   │   ├── DoorLog.vue
│   │   │   └── ButtonHistoryTable.vue
│   │   ├── router/index.js          # Role-gated routes
│   │   └── stores/auth.js           # Pinia auth store
│   ├── dist/                        # Built SPA (served by Flask)
│   └── vite.config.js
├── scripts/                    # One-time Raspberry Pi setup scripts
├── systemd/                    # Systemd service units
└── config/
    └── .env                    # Used by local/manual development compose
```

## Quick Install on Raspberry Pi

**Option A — Docker (recommended)**

No build tools, Node.js, or Python needed on the Pi.

```bash
git clone https://github.com/benitocalcanho/raspi-hotspot.git
cd raspi-hotspot

# Desktop / no GPIO:
docker compose -f docker-compose.prod.yml up -d

# Raspberry Pi (GPIO relays, reed sensor, WiFi management):
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml up -d
```

Log in at `http://<pi-ip>:5000` with `admin` / `admin12345`. Change the password, then configure everything else in the dashboard.

**Option B — Manual Install (no Docker)**

```bash
git clone https://github.com/benitocalcanho/raspi-hotspot.git
cd raspi-hotspot
sudo bash scripts/01-setup-pi.sh
```

See [docs/INSTALLATION.md](docs/INSTALLATION.md) for the canonical install guide.

For repeatable update workflows on Raspberry Pi, see [docs/DEPLOY_PI.md](docs/DEPLOY_PI.md).

## Environment Variables

Only bootstrap variables belong in environment variables. Everything else is set in the dashboard.

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | `raspi-hotspot-default-secret-key-change-me` | Flask/JWT secret — **change in production** |
| `JWT_SECRET_KEY` | `raspi-hotspot-default-jwt-key-change-me` | JWT signing key — **change in production** |
| `ADMIN_USERNAME` | `admin` | Bootstrap admin username |
| `ADMIN_PASSWORD` | `admin12345` | Bootstrap admin password |
| `APP_TIMEZONE` | auto-detected | Optional IANA timezone override |

## Calendar Guest Sync


The scheduler runs two cron jobs daily:

| Time | Action |
|---|---|
| `CHECKOUT_TIME` (12:00) | Re-checks iCal. If no event is active today, deletes calendar-created guest accounts and activates/creates cleaner. If an event is still active, guest is kept and cleaner stays deactivated. |
| `CHECKIN_TIME` (14:00) | Fetches iCal URL, finds events active today, creates or updates guest account and deactivates cleaner. |

Timezone behavior (plug-and-play):
- Scheduler and date checks run in deployment-local timezone detected at runtime.
- Optional override is available via `APP_TIMEZONE` (IANA name, e.g. `Europe/Lisbon`).
- If no override is set, runtime uses container/system timezone (`TZ`, `/etc/timezone`, `/etc/localtime`) and falls back to UTC only if detection fails.


The **first word** of the calendar event title becomes the username (lowercased). Passwords are set from the dashboard setting. Login is case-insensitive. **No email field is required for user creation.**

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
| GPIO17 | Building door relay (5 s pulse) |
| GPIO27 | Apartment door relay (5 s pulse) |
| GPIO23 | Reed switch door sensor |

These GPIO rows are created automatically on startup. End users only need to wire the Raspberry Pi according to the pinout.

On Raspberry Pi, use the Pi compose overlay to set `ENABLE_GPIO=true`, map GPIO devices, and use real `gpiozero` hardware access.

See [docs/HARDWARE.md](docs/HARDWARE.md) for wiring diagrams.

## License

MIT
