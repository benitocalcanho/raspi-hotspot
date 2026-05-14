# Raspberry Pi Deployment Runbook

Use this checklist every time you deploy updates to the Raspberry Pi.

## 1) Optional: release local ngrok endpoint first

Run on your local machine only if your local app is running and may hold the same ngrok endpoint.

```bash
cd ~/Documents/Visual\ Studio\ Projects/Raspi\ Hotspot
pkill -f "app.py" || true
pkill -f "ngrok" || true
ss -ltnp | grep 5000 || true
```

## 2) Open a shell on the Pi

Use SSH when you are on the same network or have another private route:

```bash
ssh pi@hotspot.local
ssh pi@<pi-ip>
```

When you are away from the network, use **Raspberry Pi Connect** remote shell instead. This is the recommended recovery/admin path if you prepared the Pi with Raspberry Pi Imager.

## 3) Update app code on the Pi

```bash
cd ~/docker/raspi-hotspot
git fetch origin
git checkout main
git pull --ff-only origin main
```

## 4) Rebuild and restart production stack

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml pull app
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml up -d --force-recreate app
```

Note: `docker-compose.prod.yml` uses prebuilt GHCR images. `git pull` updates compose/config files, while `pull` + `force-recreate` updates the running container image.

If you need to build locally on the Pi from source instead of pulling GHCR image:

```bash
docker compose -f docker-compose.yml -f docker-compose.pi.yml up -d --build
```

## 5) Verify containers are healthy

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml ps
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml logs --tail=200 app
```

## 6) Verify scheduler and timezone behavior

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml logs --tail=300 app | grep -Ei "Effective app timezone|Scheduler started|checkout|checkin|timezone"
```

Expected: log line includes effective timezone source (for example `source=system` or `source=config`) and scheduler startup details.

## 7) Verify app endpoint

```bash
curl -I http://127.0.0.1:5000
```

## 8) Optional runtime introspection (scheduler and effective timezone)

```bash
docker exec -i raspi-hotspot python - <<'PY'
from app import create_app
from services import calendar_service
app = create_app()
with app.app_context():
    print("APP_TIMEZONE:", app.config.get("APP_TIMEZONE"))
    print("EFFECTIVE_TIMEZONE:", app.config.get("EFFECTIVE_TIMEZONE"))
    s = calendar_service._scheduler
    print("scheduler running:", bool(s and s.running))
    if s:
        for j in s.get_jobs():
            print(j.id, j.next_run_time)
PY
```

## Troubleshooting shortcuts

If service name errors appear, confirm compose services:

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.pi.yml config --services
```

If your system only has the old Docker Compose binary, replace `docker compose` with `docker-compose`.
