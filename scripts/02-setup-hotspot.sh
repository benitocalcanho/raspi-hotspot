#!/usr/bin/env bash
# =============================================================================
# 02-setup-hotspot.sh — Prepares the Pi 3 for first-boot hotspot mode.
#
# Pi 3 strategy: create a uap0 virtual AP interface on top of wlan0.
# This works with the Broadcom BCM43438 driver (brcmfmac).
# =============================================================================
set -euo pipefail

INSTALL_DIR="/home/pi/raspi-hotspot"

# Load env values
source "${INSTALL_DIR}/config/.env"

SSID="${HOTSPOT_SSID:-RaspiSetup}"
PASS="${HOTSPOT_PASSPHRASE:-raspisetup123}"
HOST_IP="${HOTSPOT_IP:-192.168.50.1}"

echo "==> Configuring hostapd..."
cat > /etc/hostapd/hostapd.conf <<EOF
interface=uap0
driver=nl80211
ssid=${SSID}
hw_mode=g
channel=6
wmm_enabled=0
auth_algs=1
wpa=2
wpa_passphrase=${PASS}
wpa_key_mgmt=WPA-PSK
rsn_pairwise=CCMP
EOF
chmod 600 /etc/hostapd/hostapd.conf

# Point hostapd at our config
sed -i 's|^#DAEMON_CONF=.*|DAEMON_CONF="/etc/hostapd/hostapd.conf"|' /etc/default/hostapd

echo "==> Writing uap0 NetworkManager ignore rule..."
cat > /etc/NetworkManager/conf.d/99-unmanaged-uap0.conf <<EOF
[keyfile]
unmanaged-devices=interface-name:uap0
EOF

echo "==> Creating hotspot startup script /usr/local/bin/raspi-hotspot-up..."
cat > /usr/local/bin/raspi-hotspot-up <<'SCRIPT'
#!/usr/bin/env bash
set -e
# Create virtual AP interface on top of wlan0
iw dev wlan0 interface add uap0 type __ap 2>/dev/null || true
ip link set uap0 up
ip addr add "${HOTSPOT_IP:-192.168.50.1}/24" dev uap0 2>/dev/null || true
hostapd -B /etc/hostapd/hostapd.conf
dnsmasq \
    --interface=uap0 \
    --bind-interfaces \
    --dhcp-range=192.168.50.10,192.168.50.50,12h \
    --address=/#/"${HOTSPOT_IP:-192.168.50.1}" \
    --pid-file=/run/raspi-dnsmasq.pid \
    --log-facility=/var/log/raspi-dnsmasq.log \
    --no-daemon &
echo "Hotspot is up: SSID=${HOTSPOT_SSID:-RaspiSetup}, IP=${HOTSPOT_IP:-192.168.50.1}"
SCRIPT
chmod +x /usr/local/bin/raspi-hotspot-up

echo "==> Hotspot setup complete."
echo "    The hotspot is started automatically by systemd on first boot."
echo "    SSID: ${SSID}  |  IP: ${HOST_IP}"
