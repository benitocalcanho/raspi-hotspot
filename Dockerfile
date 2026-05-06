# syntax=docker/dockerfile:1
#
# Multi-stage build:
#   Stage 1 (frontend-build): Compile the Vue 3 SPA with Node.js
#   Stage 2 (app):            Python/Gunicorn production server
#
# Single image works on both desktop and Raspberry Pi.
# GPIO behaviour is controlled at runtime via ENABLE_GPIO env var:
#   ENABLE_GPIO=false  → GPIO routes disabled, mock fallback used (desktop)
#   ENABLE_GPIO=true   → GPIO routes active (Raspberry Pi)
#
# Published to GitHub Container Registry by CI on every push to main.
# Pull with:  docker pull ghcr.io/benitocalcanho/raspi-hotspot:latest

# ════════════════════════════════════════════════════════════════════════════
# Stage 1 — Build the Vue 3 frontend
# ════════════════════════════════════════════════════════════════════════════
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend

# Install dependencies first (better layer caching)
COPY frontend/package*.json ./
RUN npm ci

# Copy source and build
COPY frontend/ ./
RUN npm run build
# Output: /app/frontend/dist/

# ════════════════════════════════════════════════════════════════════════════
# Stage 2 — Production image (runs on Pi or desktop)
# ════════════════════════════════════════════════════════════════════════════
FROM python:3.11-slim

# Prevent .pyc files and enable unbuffered logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

WORKDIR /app

# ── System packages ──────────────────────────────────────────────────────────
# bash   : needed to run stop_ngrok.sh
# procps : pkill used by stop_ngrok.sh
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    procps \
    && rm -rf /var/lib/apt/lists/*

# ── Python dependencies ──────────────────────────────────────────────────────
# Always install requirements-pi.txt (includes gpiozero).
# gpiozero uses MockFactory automatically on non-Pi hardware, so it is safe
# to include in every image variant.
COPY backend/requirements.txt ./backend/requirements.txt
COPY backend/requirements-pi.txt ./backend/requirements-pi.txt

RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir -r backend/requirements-pi.txt

# ── Application source ───────────────────────────────────────────────────────
COPY backend/ ./backend/
COPY scripts/ ./scripts/

# Flask expects the built Vue SPA at ../frontend/dist/ relative to backend/app.py
COPY --from=frontend-build /app/frontend/dist ./frontend/dist/

# ── Persistent directories ───────────────────────────────────────────────────
# These are mounted as Docker named volumes at runtime (see docker-compose.yml)
RUN mkdir -p \
    /app/backend/data \
    /app/backend/uploads \
    /app/config

# ── Runtime ──────────────────────────────────────────────────────────────────
EXPOSE 5000
WORKDIR /app/backend

# Single worker to avoid multiple ngrok tunnels on startup.
# --timeout 120 accommodates calendar sync on slow Pi hardware.
CMD ["gunicorn", \
     "--bind", "0.0.0.0:5000", \
     "--workers", "1", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "app:create_app()"]
