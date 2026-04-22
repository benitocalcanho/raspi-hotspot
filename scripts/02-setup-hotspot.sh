#!/usr/bin/env bash
# =============================================================================
# 02-setup-hotspot.sh — Prepares first-boot hotspot mode.
# Supports:
#   - Raspberry Pi 3 onboard WiFi (virtual AP interface uap0)
#   - Raspberry Pi 2 + AP-capable USB WiFi dongle
# =============================================================================
set -euo pipefail

INSTALL_DIR="/home/pi/raspi-hotspot"

# Load env values
source "${INSTALL_DIR}/config/.env"

SSID="${HOTSPOT_SSID:-RaspiSetup}"
HOST_IP="${HOTSPOT_IP:-192.168.50.1}"

detect_wifi_iface() {
    if [[ -n "${WIFI_IFACE:-}" ]] && ip link show "${WIFI_IFACE}" >/dev/null 2>&1; then
        echo "${WIFI_IFACE}"
        return 0
    fi

    local iface
    iface="$(nmcli -t -f DEVICE,TYPE dev status | awk -F: '$2=="wifi" {print $1; exit}')"
    if [[ -n "${iface}" ]]; then
        echo "${iface}"
        return 0
    fi

    iface="$(iw dev | awk '$1=="Interface" {print $2; exit}')"
    if [[ -n "${iface}" ]]; then
        echo "${iface}"
        return 0
    fi

    return 1
}

echo "==> Checking WiFi interface..."
WIFI_IFACE_DETECTED="$(detect_wifi_iface || true)"
if [[ -z "${WIFI_IFACE_DETECTED}" ]]; then
    echo "ERROR: No WiFi interface found. Plug in your USB WiFi dongle first."
    exit 1
fi
echo "    WiFi interface: ${WIFI_IFACE_DETECTED}"

echo "==> Checking AP mode support..."
if ! iw list | grep -qE '^[[:space:]]*\*[[:space:]]+AP$'; then
    echo "ERROR: This WiFi adapter does not advertise AP mode support."
    echo "       Use a dongle/chipset that supports hostapd AP mode."
    exit 1
fi

echo "==> Writing NetworkManager rule for virtual AP interface (uap0)..."
cat > /etc/NetworkManager/conf.d/99-unmanaged-uap0.conf <<EOF
[keyfile]
unmanaged-devices=interface-name:uap0
EOF

echo "==> Creating hotspot startup script /usr/local/bin/raspi-hotspot-up..."
cat > /usr/local/bin/raspi-hotspot-up <<'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail

source /home/pi/raspi-hotspot/config/.env || true

detect_wifi_iface() {
    if [[ -n "${WIFI_IFACE:-}" ]] && ip link show "${WIFI_IFACE}" >/dev/null 2>&1; then
        echo "${WIFI_IFACE}"
        return 0
    fi

    local iface
    iface="$(nmcli -t -f DEVICE,TYPE dev status | awk -F: '$2=="wifi" {print $1; exit}')"
    if [[ -n "${iface}" ]]; then
        echo "${iface}"
        return 0
    fi

    iface="$(iw dev | awk '$1=="Interface" {print $2; exit}')"
    if [[ -n "${iface}" ]]; then
        echo "${iface}"
        return 0
    fi

    return 1
}

if ! iw list | grep -qE '^[[:space:]]*\*[[:space:]]+AP$'; then
    echo "Hotspot startup failed: adapter does not support AP mode."
    exit 1
fi

WIFI_IFACE_DETECTED="$(detect_wifi_iface || true)"
if [[ -z "${WIFI_IFACE_DETECTED}" ]]; then
    echo "Hotspot startup failed: no WiFi interface found."
    exit 1
fi

AP_IFACE="${WIFI_IFACE_DETECTED}"
AP_IS_VIRTUAL=0

# Prefer a virtual AP interface (Pi 3 style). If unsupported, fallback to the
# physical interface (common on Pi 2 USB dongles).
if iw dev "${WIFI_IFACE_DETECTED}" interface add uap0 type __ap 2>/dev/null; then
    AP_IFACE="uap0"
    AP_IS_VIRTUAL=1
fi

# If AP runs on the same physical interface, disconnect client mode first.
if [[ "${AP_IFACE}" == "${WIFI_IFACE_DETECTED}" ]]; then
    nmcli dev disconnect "${WIFI_IFACE_DETECTED}" >/dev/null 2>&1 || true
fi

nmcli dev set "${AP_IFACE}" managed no >/dev/null 2>&1 || true
ip link set "${AP_IFACE}" up
ip addr flush dev "${AP_IFACE}" >/dev/null 2>&1 || true
ip addr add "${HOTSPOT_IP:-192.168.50.1}/24" dev "${AP_IFACE}"

cat > /run/raspi-hostapd.conf <<EOF
interface=${AP_IFACE}
driver=nl80211
ssid=${HOTSPOT_SSID:-RaspiSetup}
hw_mode=g
channel=6
wmm_enabled=0
auth_algs=1
wpa=2
wpa_passphrase=${HOTSPOT_PASSPHRASE:-raspisetup123}
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF
chmod 600 /run/raspi-hostapd.conf

hostapd -B /run/raspi-hostapd.conf
dnsmasq \
    --interface="${AP_IFACE}" \
    --bind-interfaces \
    --dhcp-range="${HOTSPOT_DHCP_RANGE:-192.168.50.10,192.168.50.50}",12h \
    --address=/#/"${HOTSPOT_IP:-192.168.50.1}" \
    --pid-file=/run/raspi-dnsmasq.pid \
    --log-facility=/var/log/raspi-dnsmasq.log \
    --no-daemon &

echo "${AP_IFACE}" > /run/raspi-hotspot-ap-iface
echo "${AP_IS_VIRTUAL}" > /run/raspi-hotspot-ap-virtual

echo "Hotspot is up on ${AP_IFACE}: SSID=${HOTSPOT_SSID:-RaspiSetup}, IP=${HOTSPOT_IP:-192.168.50.1}"
SCRIPT
chmod +x /usr/local/bin/raspi-hotspot-up

echo "==> Creating hotspot shutdown script /usr/local/bin/raspi-hotspot-down..."
cat > /usr/local/bin/raspi-hotspot-down <<'SCRIPT'
#!/usr/bin/env bash
set -euo pipefail

AP_IFACE="$(cat /run/raspi-hotspot-ap-iface 2>/dev/null || echo "uap0")"
AP_IS_VIRTUAL="$(cat /run/raspi-hotspot-ap-virtual 2>/dev/null || echo "0")"

pkill -f "hostapd -B /run/raspi-hostapd.conf" >/dev/null 2>&1 || true

if [[ -f /run/raspi-dnsmasq.pid ]]; then
    kill "$(cat /run/raspi-dnsmasq.pid)" >/dev/null 2>&1 || true
    rm -f /run/raspi-dnsmasq.pid
else
    pkill -f "dnsmasq.*raspi-dnsmasq" >/dev/null 2>&1 || true
fi

ip addr flush dev "${AP_IFACE}" >/dev/null 2>&1 || true

if [[ "${AP_IS_VIRTUAL}" == "1" ]]; then
    iw dev "${AP_IFACE}" del >/dev/null 2>&1 || true
else
    nmcli dev set "${AP_IFACE}" managed yes >/dev/null 2>&1 || true
fi

rm -f /run/raspi-hotspot-ap-iface /run/raspi-hotspot-ap-virtual /run/raspi-hostapd.conf
SCRIPT
chmod +x /usr/local/bin/raspi-hotspot-down

echo "==> Hotspot setup complete."
echo "    Compatible mode enabled for Pi 3 and Pi 2 + USB WiFi dongle."
echo "    SSID: ${SSID}  |  IP: ${HOST_IP}"
