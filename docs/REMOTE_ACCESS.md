# Remote Access — Tailscale + ngrok

## Architecture

| Channel | Who | How |
|---------|-----|-----|
| **Tailscale** | Admin only | Private encrypted mesh VPN, works behind CGNAT |
| **ngrok** | Regular users | Free HTTPS public tunnel to the Flask app |

---

## Tailscale (Admin Access)

### What is Tailscale?
Tailscale is a zero-config VPN built on WireGuard. It assigns your Pi a stable private
IP in the `100.x.x.x` range that is only reachable by devices in your Tailscale account.
No port forwarding or DDNS required — works behind CGNAT.

### Setup

```bash
# Already installed by scripts/03-setup-tailscale.sh
# Authenticate:
sudo tailscale up
# Follow the URL printed to a browser on any device in your Tailscale account.

# Check your Pi's Tailscale IP:
tailscale ip -4
```

### Accessing the Admin Dashboard

From **any device** in your Tailscale network:
```
http://100.x.x.x:5000/admin
```

The backend enforces that all `/api/admin/*` requests originate from the Tailscale subnet
(`100.64.0.0/10`). Requests from any other IP are rejected with HTTP 403, even with a valid
admin JWT.

### Tailscale Access Controls (Optional ACL)

In your [Tailscale admin console](https://login.tailscale.com/admin/acls), you can
restrict which devices can reach the Pi:

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["autogroup:owner"],
      "dst": ["tag:raspi:5000"]
    }
  ],
  "tagOwners": {
    "tag:raspi": ["autogroup:owner"]
  }
}
```

---

## ngrok (User Access)

### What is ngrok?
ngrok creates an HTTPS tunnel from the public internet to your Flask app running locally
on the Pi. The free tier provides one tunnel with a stable URL (if you reserve a static
domain).

### Setup

1. Create a free account at [ngrok.com](https://ngrok.com)
2. Get your auth token: Dashboard → Getting Started → Your Authtoken
3. Add to `config/.env`:
   ```
   NGROK_AUTHTOKEN=your_token_here
   ```

4. (Recommended) Reserve a free static domain:
   - Dashboard → Cloud Edge → Domains → New Domain
   - Then set:
   ```
   NGROK_STATIC_DOMAIN=yourname.ngrok-free.app
   ```

### How it works

When the Flask app starts, it automatically:
1. Authenticates with ngrok using your token
2. Opens an HTTPS tunnel to `localhost:5000`
3. The public URL is shown in **Admin Dashboard → Overview**

Users access:
```
https://yourname.ngrok-free.app/login
```
They log in with their credentials and see only their own dashboard.

### Sharing URLs with Users

Send each user their access URL. Since JWT authentication is required,
even if someone guesses the URL they cannot access data without valid credentials.

### ngrok Free Tier Limits

| Feature | Free Tier |
|---------|-----------|
| Tunnels | 1 simultaneous |
| Static domain | 1 free domain |
| Bandwidth | 1 GB/month |
| Connections | Unlimited |

This is sufficient for a Raspberry Pi project with a small number of users.

---

## CGNAT Compatibility

Both Tailscale and ngrok work without any router configuration:
- Neither requires port forwarding
- Neither requires a public IP
- Both work from mobile networks and behind CGNAT ISPs
