# Calendar Integration (iCal)

## How It Works

The app polls a private iCal URL daily to manage guest accounts automatically.
No Google API credentials, no OAuth, no JSON files — just a URL you paste once in the dashboard.

**Supported providers:** Google Calendar, Apple Calendar, Outlook/Office 365, Fastmail, and any calendar that exports a private iCal feed.

---

## Setup

### 1 — Get your private iCal URL

**Google Calendar:**
1. Open [calendar.google.com](https://calendar.google.com)
2. Click the three-dot menu next to the calendar → **Settings and sharing**
3. Scroll to **Secret address in iCal format**
4. Copy the URL (starts with `https://calendar.google.com/calendar/ical/...`)

**Apple Calendar (iCloud):**
1. Go to [icloud.com/calendar](https://icloud.com/calendar)
2. Click the share icon next to the calendar → enable **Public Calendar**
3. Copy the webcal:// URL and change `webcal://` to `https://`

**Outlook / Office 365:**
1. Open Outlook → Calendar → right-click the calendar → **Share** → **Publish to web**
2. Copy the ICS link

---

### 2 — Paste the URL in the dashboard

Admin Dashboard -> **Calendar Sync** tab -> **Google Calendar (iCal)** section -> paste URL -> **Save**.

No restart required. The next scheduled sync will use the new URL.

---

## Calendar Event Format

The **first word** of the event title becomes the guest's username (lowercased, special characters replaced with `_`).

**Guest password** is set by the dashboard setting under **Guest Password**:

| Mode | Behaviour |
|------|-----------|
| **Fixed password** | All guests get the same password configured in the dashboard |
| **Last word of event title** | The last word of the title is used as the password — useful for using the last 4 digits of the guest's phone number |

**Example event titles:**

| Title | Username | Password (last-word mode) |
|-------|----------|--------------------------|
| `Alice 0612` | `alice` | `0612` |
| `Smith family vacation 8523` | `smith` | `8523` |
| `john` | `john` | — (use fixed password mode) |

---

## Sync Schedule

Two cron jobs run daily (times configurable in dashboard):

| Time | Action |
|------|--------|
| `CHECKOUT_TIME` (default 12:00) | Re-checks the calendar. **If no ongoing multi-day event started before today:** deletes all calendar-created guest accounts, then creates/reactivates the cleaner account. A new event that starts today does **not** activate yet. **If an event started before today and still spans today:** guest account is kept, cleaner stays deactivated. |
| `CHECKIN_TIME` (default 14:00) | Fetches iCal, finds the event eligible for guest access (`DTSTART < today`, or `DTSTART == today` and local time is at/after check-in), creates or updates the guest account, deactivates the cleaner account. |

An event is **active today** when: `DTSTART ≤ today < DTEND` (iCal DTEND is exclusive).

### Timezone Behavior

- Scheduler and `today` calculations use deployment-local timezone detected at runtime.
- Optional override: set `APP_TIMEZONE` (IANA timezone name) to force a specific timezone.
- If unset, runtime detection uses `TZ`, then `/etc/timezone` or `/etc/localtime`, and falls back to UTC only if no valid timezone is found.
- In Docker deployments, mount host timezone files so container runtime matches host timezone.

---

## Cleaner Account Lifecycle

The cleaner account is toggled automatically so the cleaner can access the property only between guest stays:

1. **Guest checks out** (checkout job runs, no active event today) — cleaner account is created (if missing) or activated. The cleaner can now log in and access the door buttons.
2. **New guest checks in** (check-in job runs at/after check-in time and an eligible event is found) — cleaner account is deactivated. Guest account is created or updated. The cleaner loses access while a guest is in the property.
3. **Multi-day stay** — if the checkout job runs while the event still covers today, the guest account is untouched and the cleaner remains deactivated for the full duration.

The cleaner username and password are configured in **Calendar Sync -> Cleaner Account**.

---

## Manual Sync

Admin Dashboard -> **Calendar Sync** tab -> **Sync Now**.

After syncing, the dashboard shows a summary of exactly what happened:
- Guest created or kept (with event title and expiry date)
- Guests deleted on checkout
- Cleaner account created, activated, or deactivated
- iCal URL not configured or fetch error (with the error message)

Useful after adding a new event, extending a stay, or changing the iCal URL.

---

## Changing Schedule Times

Admin Dashboard -> **Calendar Sync** tab -> **Guest Schedule** section -> update times -> **Save** -> **Apply Schedule Changes**.

Changes take effect immediately without restarting the app.

Or via API:

```bash
curl -X POST http://100.x.x.x:5000/api/calendar/sync \
  -H "Authorization: Bearer <admin_jwt>"
```
