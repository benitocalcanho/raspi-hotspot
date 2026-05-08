"""
WiFi / hotspot management service.

Supported setups:
    - Raspberry Pi 3 onboard WiFi (prefers virtual AP interface uap0)
    - Raspberry Pi 2 + USB WiFi dongle (falls back to physical AP interface)

All shell commands are run with subprocess with explicit argument lists
(no shell=True) to prevent command injection.
"""
from __future__ import annotations

import subprocess
import os
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


def _wifi_interface() -> str:
    """Best-effort detection of the current WiFi interface name."""
    forced_iface = os.getenv("WIFI_IFACE", "").strip()
    if forced_iface:
        link = _run(["ip", "link", "show", forced_iface], check=False)
        if link.returncode == 0:
            return forced_iface

    # Prefer active WiFi interfaces known by NetworkManager.
    result = _run(["nmcli", "-t", "-f", "DEVICE,TYPE,STATE", "dev", "status"], check=False)
    wifi_lines = []
    for line in result.stdout.strip().splitlines():
        parts = line.split(":")
        if len(parts) >= 3 and parts[1] == "wifi":
            wifi_lines.append(parts)

    for parts in wifi_lines:
        if parts[2] == "connected":
            return parts[0]
    if wifi_lines:
        return wifi_lines[0][0]

    # Fallback to iw output if nmcli data is unavailable.
    iw_result = _run(["iw", "dev"], check=False)
    for raw in iw_result.stdout.strip().splitlines():
        line = raw.strip()
        if line.startswith("Interface "):
            return line.split()[1]

    return "wlan0"


def _ap_supported() -> bool:
    result = _run(["iw", "list"], check=False)
    for raw in result.stdout.splitlines():
        if raw.strip() == "* AP":
            return True
    return False


# ── Hotspot control ───────────────────────────────────────────────────────────

def start_hotspot(ssid: str, passphrase: str, hotspot_ip: str) -> dict:
    """
    Bring up the uap0 virtual AP interface with hostapd + dnsmasq.
    Requires root / sudo.
    """
    _validate_ssid(ssid)
    _validate_passphrase(passphrase)

    if not _ap_supported():
        raise RuntimeError("This WiFi adapter does not support AP mode.")

    wifi_iface = _wifi_interface()
    ap_iface = wifi_iface

    # Prefer Pi 3 style: virtual AP interface. Fallback to physical interface.
    add_virtual = _run(
        ["sudo", "iw", "dev", wifi_iface, "interface", "add", "uap0", "type", "__ap"],
        check=False,
    )
    if add_virtual.returncode == 0:
        ap_iface = "uap0"
    else:
        _run(["sudo", "nmcli", "dev", "disconnect", wifi_iface], check=False)

    _run(["sudo", "ip", "link", "set", ap_iface, "up"])
    _run(["sudo", "ip", "addr", "flush", "dev", ap_iface], check=False)
    _run(["sudo", "ip", "addr", "add", f"{hotspot_ip}/24", "dev", ap_iface], check=False)

    # 2. Write a minimal hostapd config to a temp file
    hostapd_conf = (
        f"interface={ap_iface}\n"
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
    subprocess.Popen([
        "sudo", "dnsmasq",
        f"--interface={ap_iface}",
        "--bind-interfaces",
        "--dhcp-range=192.168.50.10,192.168.50.50,12h",
        f"--address=/#/{hotspot_ip}",
        "--pid-file=/tmp/raspi_dnsmasq.pid",
        "--keep-in-foreground",
    ])

    return {
        "status": "hotspot_started",
        "ssid": ssid,
        "ip": hotspot_ip,
        "wifi_iface": wifi_iface,
        "ap_iface": ap_iface,
    }


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


def save_network_profile(ssid: str, passphrase: str) -> dict:
    """
    Save WiFi credentials to NetworkManager without connecting immediately.
    NetworkManager will auto-connect when the network comes into range.
    If a profile for this SSID already exists it is updated in place.
    """
    _validate_ssid(ssid)
    _validate_passphrase(passphrase)

    try:
        # Check whether a profile with this SSID already exists
        check = _run(["nmcli", "-t", "-f", "NAME", "con", "show"], check=False)
        existing_names = [l.strip() for l in check.stdout.strip().splitlines()]
    except FileNotFoundError:
        raise ValueError("nmcli is not available on this system. This feature requires NetworkManager (Raspberry Pi OS).")

    try:
        if ssid in existing_names:
            result = _run([
                "nmcli", "connection", "modify", ssid,
                "wifi-sec.key-mgmt", "wpa-psk",
                "wifi-sec.psk", passphrase,
            ], check=False)
        else:
            result = _run([
                "nmcli", "connection", "add",
                "type", "wifi",
                "con-name", ssid,
                "ssid", ssid,
                "wifi-sec.key-mgmt", "wpa-psk",
                "wifi-sec.psk", passphrase,
            ], check=False)
    except FileNotFoundError:
        raise ValueError("nmcli is not available on this system. This feature requires NetworkManager (Raspberry Pi OS).")

    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or f"Could not save profile for '{ssid}'")

    return {"status": "saved", "ssid": ssid}


def connect_to_network(ssid: str, passphrase: str) -> dict:
    """
    Connect wlan0 to a WiFi network via NetworkManager.
    The connection is saved automatically (persistent across reboots).
    """
    _validate_ssid(ssid)
    _validate_passphrase(passphrase)

    wifi_iface = _wifi_interface()

    result = _run([
        "sudo", "nmcli", "dev", "wifi", "connect", ssid,
        "password", passphrase,
        "ifname", wifi_iface,
    ], check=False)

    if result.returncode != 0:
        return {"status": "error", "message": result.stderr.strip()}

    return {"status": "connected", "ssid": ssid, "device": wifi_iface}


def get_connection_status() -> dict:
    """Return the current WiFi connection status."""
    wifi_iface = _wifi_interface()
    result = _run(["nmcli", "-t", "-f", "DEVICE,STATE,CONNECTION", "dev", "status"], check=False)
    for line in result.stdout.strip().splitlines():
        parts = line.split(":")
        if parts[0] == wifi_iface:
            return {
                "device": parts[0],
                "state": parts[1] if len(parts) > 1 else "unknown",
                "connection": parts[2] if len(parts) > 2 else "",
            }
    return {"device": wifi_iface, "state": "unknown", "connection": ""}


# ── Saved network management (admin dashboard) ────────────────────────────────

def list_saved_networks() -> list[dict]:
    """List WiFi connection profiles saved in NetworkManager."""
    result = _run(
        ["nmcli", "-t", "-f", "NAME,TYPE,ACTIVE", "con", "show"],
        check=False,
    )
    saved = []
    for line in result.stdout.strip().splitlines():
        parts = line.split(":")
        if len(parts) >= 2 and parts[1] in ("wifi", "802-11-wireless"):
            saved.append({
                "name": parts[0],
                "active": parts[2].strip().lower() == "yes" if len(parts) > 2 else False,
            })
    return saved


def delete_saved_network(name: str) -> dict:
    """Delete a saved WiFi connection profile from NetworkManager."""
    result = _run(["nmcli", "connection", "delete", name], check=False)
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or f"Could not delete '{name}'")
    return {"status": "deleted", "name": name}


def connect_saved_network(name: str) -> dict:
    """Activate a previously saved WiFi connection profile."""
    result = _run(["nmcli", "connection", "up", name], check=False)
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or f"Could not connect to '{name}'")
    return {"status": "connected", "name": name}
