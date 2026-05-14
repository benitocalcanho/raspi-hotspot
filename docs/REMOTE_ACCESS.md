# Remote Access — ngrok + Raspberry Pi Connect

## Shared Behavior Note

Remote access configuration is host-specific, but calendar scheduling remains deployment-local timezone based.
Avoid maintainer-specific timezone assumptions in remote operations and support flows.

## Architecture

| Channel | Who | How |
|---------|-----|-----|
| **ngrok** | Admin + all users | Primary HTTPS public tunnel; URL shown in dashboard |
| **Raspberry Pi Connect** | Admin | Browser-based remote shell for host maintenance/recovery |
| **Tailscale** | Admin (optional) | Private VPN for direct SSH/private IP access |

ngrok is the primary path for app access. Raspberry Pi Connect is the recommended simple fallback for remote shell access to the host machine. Tailscale remains optional if you want a private VPN.

---

## Raspberry Pi Connect (Admin Shell)

Raspberry Pi Connect provides remote shell access through a browser and works without router port forwarding. It is a good replacement for Tailscale when you only need occasional admin/recovery shell access to the Pi.

Set it up during Raspberry Pi Imager if the option is available:

1. Choose Raspberry Pi OS Lite.
2. Open OS Customisation.
3. Configure hostname, user/password, WiFi, locale, and SSH.
4. Enable/link Raspberry Pi Connect.

On headless Raspberry Pi OS Lite, enable user lingering so Connect can remain reachable after reboot before an interactive login:

```bash
loginctl enable-linger
```

Use Raspberry Pi Connect for:
- checking Docker logs
- pulling app updates
- restarting the container
- fixing WiFi/ngrok/app settings when you are not on the local network

Raspberry Pi Connect does not expose the web app to guests. Keep ngrok for guest/admin web access.

---

## Tailscale (Optional Admin Access)

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
Use Tailscale only when you want private-network style access instead of Raspberry Pi Connect's browser shell.

### Tailscale Access Controls (Optional ACL)

In your [Tailscale admin console](https://login.tailscale.com/admin/acls), you can
restrict which devices can reach the Pi:

```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["autogroup:owner"],
      "dst": ["tag:invisible-key:5000"]
    }
  ],
  "tagOwners": {
    "tag:invisible-key": ["autogroup:owner"]
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

ngrok, Raspberry Pi Connect, and Tailscale work without router configuration:
- no port forwarding required
- no public IP required
- suitable for mobile networks and CGNAT ISPs
