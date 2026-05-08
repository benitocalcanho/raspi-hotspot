# REST API Reference

Base URL: `http://<pi-ip>:5000/api`

All protected endpoints require `Authorization: Bearer <access_token>` header.

---

## Authentication (`/api/auth`)

### POST `/auth/login`
```json
{ "username": "john", "password": "secret" }
```
Returns `access_token`, `refresh_token`, and `user` object.

### POST `/auth/refresh`
Header: `Authorization: Bearer <refresh_token>`
Returns new `access_token`.

### POST `/auth/logout`
Logs the event. Client must discard tokens.

### POST `/auth/change-password`
```json
{ "current_password": "old", "new_password": "new_min8chars" }
```

### GET `/auth/me`
Returns the authenticated user's profile.

---

## Admin (`/api/admin`) — admin role required

### GET `/admin/overview`
System summary: user counts, audit event count, ngrok URL, system time.

### GET `/admin/users`
List all users.

### POST `/admin/users`
```json
{ "username": "jane", "password": "pass", "role": "user" }
```
`email` is optional and internally derived if omitted.

### GET `/admin/users/:id`
### PATCH `/admin/users/:id`
```json
{ "is_active": false, "role": "admin" }
```
### DELETE `/admin/users/:id`

### GET `/admin/audit?page=1&per_page=50&user_id=3`
Paginated audit log.

### GET `/admin/ngrok`
Returns `{ "url": "https://...", "active": true }`.

### POST `/admin/ngrok/restart`
Restarts the ngrok tunnel.

### GET `/admin/settings`
Returns the full settings schema and current values.
```json
{
  "schema": { "ICAL_URL": { "label": "...", "section": "ical", "secret": false, "multiline": false }, ... },
  "values": { "ICAL_URL": { "is_set": true, "value": "https://..." }, ... }
}
```

### PATCH `/admin/settings`
Update one or more settings. Empty strings are ignored (keeps existing value).
```json
{
  "ICAL_URL": "https://calendar.google.com/...",
  "CALENDAR_GUEST_PASSWORD_MODE": "from_event",
  "NGROK_AUTHTOKEN": "...",
  "CHECKOUT_TIME": "12:00",
  "CHECKIN_TIME": "14:00"
}
```
If `NGROK_AUTHTOKEN` or `NGROK_STATIC_DOMAIN` is updated, the ngrok tunnel restarts automatically.

---

## User (`/api/user`)

### GET `/user/dashboard`
Returns logged-in user's profile and last 10 login events.

### GET `/user/activity`
Returns last 100 audit events for the authenticated user.

---

## GPIO (`/api/gpio`) — requires `ENABLE_GPIO=true`

### GET `/gpio/pins`
All configured pins.

### POST `/gpio/pins` — admin only
```json
{ "pin_number": 17, "label": "Front Door", "direction": "output" }
```

### GET `/gpio/pins/:pin_number`
Read current state.

### POST `/gpio/pins/:pin_number/toggle`
Toggle output pin state (fires a 5-second relay pulse for output pins).

### DELETE `/gpio/pins/:pin_number` — admin only
Remove pin configuration.

---

## WiFi (`/api/wifi`)

### GET `/wifi/status`
Current wlan0 connection state. No auth required.

### GET `/wifi/scan`
List available WiFi networks (sorted by signal strength). No auth required.

### POST `/wifi/connect`
```json
{ "ssid": "MyNetwork", "passphrase": "wifipassword" }
```
No auth required (used during hotspot setup phase).

### POST `/wifi/hotspot/stop` — admin only
Tear down the uap0 hotspot.

### GET `/wifi/admin/status` — admin only
Current connection status (device, state, active connection name).

### GET `/wifi/admin/scan` — admin only
Scan nearby networks. Returns list of `{ ssid, signal, security }`.

### GET `/wifi/admin/saved` — admin only
List all WiFi profiles saved in NetworkManager.
Returns list of `{ name, active }`.

### POST `/wifi/admin/saved` — admin only
Save credentials for a network without connecting immediately. The Pi will auto-connect when in range.
```json
{ "ssid": "ApartmentWiFi", "passphrase": "password123" }
```
If a profile for that SSID already exists, its credentials are updated.

### DELETE `/wifi/admin/saved/:name` — admin only
Remove a saved WiFi profile from NetworkManager.

### POST `/wifi/admin/saved/:name/connect` — admin only
Activate a saved WiFi profile immediately (network must be in range).

---

## Calendar (`/api/calendar`)

### POST `/calendar/sync` — admin only
Manually trigger iCal sync. Returns `{ "users_created": N }`.
