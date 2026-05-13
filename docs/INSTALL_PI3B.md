# Raspberry Pi 3 B+ Notes

Use [INSTALLATION.md](INSTALLATION.md) for the canonical install instructions. This file keeps only Raspberry Pi 3 B+ notes that are easy to lose in the general guide.

## Hardware Baseline

- Raspberry Pi 3 Model B/B+
- Raspberry Pi OS Lite, preferably 64-bit
- 16 GB or larger microSD card
- 5V / 2.5A power supply

Avoid Raspberry Pi OS Full on small SD cards. The desktop image leaves little room for Docker images and logs.

## OS Setup Notes

After first boot:

```bash
sudo apt update
sudo apt upgrade -y
```

For a Pi that should run 24/7:

```bash
sudo raspi-config nonint do_blanking 1
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
sudo systemctl disable NetworkManager-wait-online.service
```

Pi OS Lite usually expands the filesystem automatically on first boot.

## Install Command

On the Pi, use the production image plus the Pi overlay:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml up -d
```

The Pi overlay is required for:
- GPIO relays
- reed sensor monitoring
- dashboard WiFi management through host NetworkManager

## Quick Checks

Find the Pi IP:

```bash
hostname -I
```

Check the app:

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

## Hardware References

- Relay and reed switch wiring: [HARDWARE.md](HARDWARE.md)
- Pin assignment table: [GPIO_PINOUT.md](GPIO_PINOUT.md)
- Repeatable update runbook: [DEPLOY_PI.md](DEPLOY_PI.md)
