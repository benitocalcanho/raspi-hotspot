# Remote Access — ngrok + Tailscale

## Architecture

| Channel | Who | How |
|---------|-----|-----|
| **ngrok** | Admin + all users | Primary HTTPS public tunnel; URL shown in dashboard |
| **Tailscale** | Admin (optional backup) | Private VPN for SSH/admin access when ngrok is unavailable |

ngrok is the primary path for all remote access. Tailscale is recommended as a backup for SSH and admin dashboard access to the host machine only.

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
http://100.x.x.x:5000
```

Tailscale is not required to access the admin dashboard — it is accessible via ngrok.
Use Tailscale as a fallback for direct host access (SSH, recovery) when ngrok is unavailable.

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
3. (Recommended) Reserve a free static domain: Dashboard → Cloud Edge → Domains → New Domain
4. Paste your token (and optionally the static domain) in:
   **Admin Dashboard → ngrok Tunnel** tab → Save

The tunnel starts automatically and restarts on save. No app restart needed.

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
