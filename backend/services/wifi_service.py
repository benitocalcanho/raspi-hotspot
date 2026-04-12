"""
WiFi / hotspot management service for Raspberry Pi 3.

Strategy for Pi 3 (single Broadcom WiFi chip):
  - A virtual AP interface 'uap0' is cloned from wlan0.
  - uap0 runs hostapd (access point) + dnsmasq (DHCP).
  - wlan0 connects to the target network via NetworkManager / wpa_supplicant.
  - Both can run simultaneously on the Broadcom BCM43438 chip.

All shell commands are run with subprocess with explicit argument lists
(no shell=True) to prevent command injection.
"""
import subprocess
import json
import re
from pathlib import Path


# ── Helpers ──────────────────────────────────────────────────────────────────

def _run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Run a command safely (no shell=True)."""
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def _validate_ssid(ssid: str) -> str:
    if not ssid or len(ssid) > 32:
        raise ValueError("SSID must be 1–32 characters.")
    return ssid


def _validate_passphrase(passphrase: str) -> str:
    if len(passphrase) < 8 or len(passphrase) > 63:
        raise ValueError("Passphrase must be 8–63 characters.")
    return passphrase


# ── Hotspot control ───────────────────────────────────────────────────────────

def start_hotspot(ssid: str, passphrase: str, hotspot_ip: str) -> dict:
    """
    Bring up the uap0 virtual AP interface with hostapd + dnsmasq.
    Requires root / sudo.
    """
    _validate_ssid(ssid)
    _validate_passphrase(passphrase)

    # 1. Create virtual AP interface if not present
    _run(["sudo", "iw", "dev", "wlan0", "interface", "add", "uap0", "type", "__ap"], check=False)
    _run(["sudo", "ip", "link", "set", "uap0", "up"])
    _run(["sudo", "ip", "addr", "add", f"{hotspot_ip}/24", "dev", "uap0"], check=False)

    # 2. Write a minimal hostapd config to a temp file
    hostapd_conf = (
        f"interface=uap0\n"
        f"driver=nl80211\n"
        f"ssid={ssid}\n"
        f"hw_mode=g\n"
        f"channel=6\n"
        f"wmm_enabled=0\n"
        f"macaddr_acl=0\n"
        f"auth_algs=1\n"
        f"ignore_broadcast_ssid=0\n"
        f"wpa=2\n"
        f"wpa_passphrase={passphrase}\n"
        f"wpa_key_mgmt=WPA-PSK\n"
        f"wpa_pairwise=CCMP\n"
        f"rsn_pairwise=CCMP\n"
    )
    hostapd_conf_path = Path("/tmp/raspi_hostapd.conf")
    hostapd_conf_path.write_text(hostapd_conf)
    hostapd_conf_path.chmod(0o600)

    # 3. Start hostapd (daemonised)
    _run(["sudo", "hostapd", "-B", str(hostapd_conf_path)])

    # 4. Start dnsmasq for this interface only
    _run([
        "sudo", "dnsmasq",
        "--interface=uap0",
        "--bind-interfaces",
        "--dhcp-range=192.168.50.10,192.168.50.50,12h",
        f"--address=/#/{hotspot_ip}",   # Captive-portal redirect
        "--no-daemon", "--pid-file=/tmp/raspi_dnsmasq.pid",
    ], check=False)

    return {"status": "hotspot_started", "ssid": ssid, "ip": hotspot_ip}


def stop_hotspot() -> dict:
    """Tear down the hotspot gracefully."""
    _run(["sudo", "pkill", "-f", "raspi_hostapd.conf"], check=False)
    _run(["sudo", "pkill", "-f", "raspi_dnsmasq.pid"], check=False)
    _run(["sudo", "iw", "dev", "uap0", "del"], check=False)
    return {"status": "hotspot_stopped"}


# ── WiFi scanning / connecting ────────────────────────────────────────────────

def scan_networks() -> list[dict]:
    """
    Scan visible WiFi networks using nmcli.
    Returns a list of dicts: {ssid, signal, security}.
    """
    result = _run([
        "nmcli", "-t", "-f", "SSID,SIGNAL,SECURITY",
        "dev", "wifi", "list", "--rescan", "yes",
    ], check=False)

    networks = []
    seen: set[str] = set()
    for line in result.stdout.strip().splitlines():
        parts = line.split(":")
        if len(parts) >= 3:
            ssid = parts[0].strip()
            if ssid and ssid not in seen:
                seen.add(ssid)
                networks.append({
                    "ssid": ssid,
                    "signal": int(parts[1]) if parts[1].isdigit() else 0,
                    "security": parts[2].strip() or "Open",
                })
    # Sort strongest signal first
    return sorted(networks, key=lambda n: n["signal"], reverse=True)


def connect_to_network(ssid: str, passphrase: str) -> dict:
    """
    Connect wlan0 to a WiFi network via NetworkManager.
    The connection is saved automatically (persistent across reboots).
    """
    _validate_ssid(ssid)
    _validate_passphrase(passphrase)

    result = _run([
        "sudo", "nmcli", "dev", "wifi", "connect", ssid,
        "password", passphrase,
        "ifname", "wlan0",
    ], check=False)

    if result.returncode != 0:
        return {"status": "error", "message": result.stderr.strip()}

    return {"status": "connected", "ssid": ssid}


def get_connection_status() -> dict:
    """Return the current wlan0 connection status."""
    result = _run(["nmcli", "-t", "-f", "DEVICE,STATE,CONNECTION", "dev", "status"], check=False)
    for line in result.stdout.strip().splitlines():
        parts = line.split(":")
        if parts[0] == "wlan0":
            return {
                "device": parts[0],
                "state": parts[1] if len(parts) > 1 else "unknown",
                "connection": parts[2] if len(parts) > 2 else "",
            }
    return {"device": "wlan0", "state": "unknown", "connection": ""}
