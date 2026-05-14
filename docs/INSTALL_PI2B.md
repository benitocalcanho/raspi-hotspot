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

```bash
git clone https://github.com/benitocalcanho/invisible-key.git
cd invisible-key
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

Raspberry Pi 2 B has no onboard WiFi. If you need WiFi or first-boot hotspot behavior, use a USB WiFi adapter supported by Raspberry Pi OS. Ethernet is simpler and more reliable.

## Quick Checks

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml ps
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml logs --tail=200 app
```

Open:

```text
http://<pi-ip>:5000
```

Default login:

```text
admin / admin12345
```

Change the admin password immediately.
