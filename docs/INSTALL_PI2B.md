# Raspberry Pi 2 B Notes

Use [INSTALLATION.md](INSTALLATION.md) for the canonical install instructions. This file keeps the Raspberry Pi 2 B-specific details in one place.

## Hardware Baseline

- Raspberry Pi 2 Model B
- Raspberry Pi OS Lite 32-bit
- 16 GB or larger microSD card recommended
- 5V / 2A or better power supply
- Ethernet, or a USB WiFi adapter supported by Raspberry Pi OS

The Raspberry Pi 2 B is 32-bit and has no onboard WiFi. In Raspberry Pi Imager, choose **Raspberry Pi OS Lite 32-bit**. Do not choose the 64-bit image for this board.

## First Boot Setup

After first boot, install the basic tools that are not guaranteed to be present on Lite:

```bash
sudo apt update
sudo apt upgrade -y
sudo apt install -y git curl ca-certificates
```

If you use Raspberry Pi Connect for remote shell access, enable user lingering:

```bash
loginctl enable-linger
```

Install Docker from the Raspberry Pi OS packages. Do **not** use `curl -fsSL https://get.docker.com | sh` on Raspberry Pi OS 32-bit Trixie; Docker's upstream Raspbian repo may not provide a `trixie` release for this board.

```bash
sudo rm -f /etc/apt/sources.list.d/docker.list
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
sudo reboot
```

After reboot:

```bash
docker --version
docker compose version
```

## Install Invisible Key

Clone the repository, or update the existing clone if you already tried once:

```bash
if [ -d invisible-key ]; then
  cd invisible-key
  git pull --ff-only origin main
else
  git clone https://github.com/benitocalcanho/invisible-key.git
  cd invisible-key
fi
```

Start the app:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml up -d
```

The published Docker image includes `linux/arm/v7`, which is the architecture used by Raspberry Pi 2 B with Raspberry Pi OS Lite 32-bit.

## Performance Expectations

Raspberry Pi 2 B is supported as a lightweight deployment target, but it is slower than a Pi 3/4/5:

- Docker image pulls can take several minutes.
- First startup can feel slow.
- Avoid building the image locally on the Pi 2 B; pull the prebuilt GHCR image instead.
- Use a reliable power supply and a good microSD card.

## WiFi Note

Raspberry Pi 2 B has no onboard WiFi. If you need WiFi or first-boot hotspot behavior, use a USB WiFi adapter supported by Raspberry Pi OS. Ethernet is simpler and more reliable when available.

If you use a WiFi range extender/repeater, local inbound access such as SSH or `http://<pi-ip>:5000` can fail even when ping works. Some repeaters, including basic TP-Link RE models such as TL-WA850RE, use MAC proxy/translation. Disable NetworkManager WiFi MAC randomization on the Pi before relying on a repeater path.

Create this file:

```bash
sudo mkdir -p /etc/NetworkManager/conf.d
sudo nano /etc/NetworkManager/conf.d/00-disable-wifi-randomization.conf
```

Add:

```ini
[device]
wifi.scan-rand-mac-address=no

[connection]
wifi.cloned-mac-address=permanent
ethernet.cloned-mac-address=permanent
```

Reboot:

```bash
sudo reboot
```

After reconnecting, verify the active network and test inbound access from another machine:

```bash
hostname -I
iw dev wlan0 link
ssh pi@<pi-ip>
curl -I http://<pi-ip>:5000
```

For repeaters, also check that the repeater DHCP server is disabled, access control/blacklist is disabled, and firmware is current. If the main router shows a different MAC address for the Pi than `ip addr show wlan0`, that can be normal repeater proxy behavior. Reserve the IP against the MAC address that the main router actually sees.

## Troubleshooting Notes

### Docker install fails with `trixie Release` missing

If you accidentally ran Docker's convenience script and saw this error:

```text
E: The repository 'https://download.docker.com/linux/raspbian trixie Release' does not have a Release file.
```

remove the broken Docker source and use Raspberry Pi OS packages:

```bash
sudo rm -f /etc/apt/sources.list.d/docker.list
sudo apt update
sudo apt install -y docker.io docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker "$USER"
sudo reboot
```

### Locale warnings during `apt`

Warnings such as `Setting locale failed` are not fatal. They usually mean the language/locale selected in Raspberry Pi Imager was not generated fully yet. The app and Docker install can continue.

### SSH host key changed

If you reused an IP address from an older Pi install, SSH may warn that the remote host identification changed. For a freshly imaged Pi on your own network, remove the old key:

```bash
ssh-keygen -f "$HOME/.ssh/known_hosts" -R "<pi-ip>"
```

Then connect again and accept the new fingerprint.

## Quick Checks

```bash
docker --version
docker compose version
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml ps
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml logs --tail=200 app
```

First image pull and first startup can take several minutes on a Pi 2 B. Let Docker finish pulling layers before judging startup time.

Open:

```text
http://<pi-ip>:5000
```

Default login:

```text
admin / admin12345
```

Change the admin password immediately.
