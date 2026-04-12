# Google Calendar Integration

## How It Works

The Pi periodically polls your Google Calendar for events whose title matches a special
format, and automatically creates user accounts from them.

**Event title format:**
```
CREATE_USER | username | email@example.com | TemporaryPassword123!
```

The keyword `CREATE_USER` is configurable via `CALENDAR_USER_CREATION_KEYWORD` in `.env`.

---

## Setup: Google Cloud Project

### 1. Create a Google Cloud Project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Create a new project (e.g. `raspi-hotspot`)

### 2. Enable the Google Calendar API

1. Navigate to **APIs & Services → Library**
2. Search for `Google Calendar API`
3. Click **Enable**

### 3. Create OAuth 2.0 Credentials

1. Go to **APIs & Services → Credentials**
2. Click **Create Credentials → OAuth client ID**
3. Application type: **Desktop app**
4. Download the JSON file
5. Copy it to your Pi:

```bash
scp ~/Downloads/credentials.json pi@raspi-hotspot.local:~/raspi-hotspot/config/
```

### 4. Configure `.env`

```env
GOOGLE_CREDENTIALS_FILE=/home/pi/raspi-hotspot/config/credentials.json
GOOGLE_TOKEN_FILE=/home/pi/raspi-hotspot/config/token.json
GOOGLE_CALENDAR_ID=primary
CALENDAR_USER_CREATION_KEYWORD=CREATE_USER
CALENDAR_SYNC_INTERVAL=300
```

### 5. Authorize on First Run

The first time the calendar sync runs, you need to authorize it:

```bash
cd /home/pi/raspi-hotspot/backend
source ../.venv/bin/activate
python3 -c "from services.calendar_service import sync_calendar; from app import create_app; sync_calendar(create_app())"
```

A browser will open (or a URL printed). Log in with the Google account that owns the
calendar. This saves `token.json` — no re-authorization needed after this.

---

## Usage Example

Add this event to Google Calendar:

| Field | Value |
|-------|-------|
| Title | `CREATE_USER \| johndoe \| john@company.com \| Welcome2024!` |
| Date | Any future date |

Within `CALENDAR_SYNC_INTERVAL` seconds (default 5 minutes), the Pi will:
1. Detect the event
2. Create `johndoe` account with the given email and password
3. Log the creation in the audit trail
4. Skip the event on future syncs (tracked by calendar event ID)

---

## Manual Sync

Admin Dashboard → Calendar Sync → **Sync Now**

Or via API:
```bash
curl -X POST http://100.x.x.x:5000/api/calendar/sync \
  -H "Authorization: Bearer <admin_jwt>"
```
