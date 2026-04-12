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

## Admin (`/api/admin`) — Tailscale only

### GET `/admin/overview`
System summary: user counts, audit event count, ngrok URL.

### GET `/admin/users`
List all users.

### POST `/admin/users`
```json
{ "username": "jane", "email": "jane@x.com", "password": "pass", "role": "user" }
```

### GET `/admin/users/:id`
### PATCH `/admin/users/:id`
```json
{ "is_active": false, "role": "admin", "email": "new@x.com" }
```
### DELETE `/admin/users/:id`

### GET `/admin/audit?page=1&per_page=50&user_id=3`
Paginated audit log.

### GET `/admin/ngrok`
Returns `{ "url": "https://...", "active": true }`.

### POST `/admin/ngrok/restart`
Restarts the ngrok tunnel.

---

## User (`/api/user`)

### GET `/user/dashboard`
Returns logged-in user's profile and last 10 login events.

### GET `/user/activity`
Returns last 100 audit events for the authenticated user.

---

## GPIO (`/api/gpio`)

### GET `/gpio/pins`
All configured pins.

### POST `/gpio/pins` — admin + Tailscale
```json
{ "pin_number": 17, "label": "LED", "direction": "output" }
```

### GET `/gpio/pins/:pin_number`
Read current state.

### POST `/gpio/pins/:pin_number/toggle`
Toggle output pin state.

### DELETE `/gpio/pins/:pin_number` — admin + Tailscale
Remove pin configuration.

---

## WiFi (`/api/wifi`)

### GET `/wifi/status`
Current wlan0 connection state.

### GET `/wifi/scan`
List available WiFi networks (sorted by signal strength). No auth required.

### POST `/wifi/connect`
```json
{ "ssid": "MyNetwork", "passphrase": "wifipassword" }
```
No auth required (used during hotspot setup phase).

### POST `/wifi/hotspot/stop` — admin + Tailscale
Tear down the uap0 hotspot.

---

## Calendar (`/api/calendar`)

### POST `/calendar/sync` — admin + Tailscale
Manually trigger Google Calendar sync. Returns `{ "users_created": N }`.
