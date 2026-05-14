"""
ngrok tunnel service.

Architecture:
  - One tunnel exposes the Flask app on port 5000.
  - Users access their personal dashboard at  /dashboard  (protected by JWT).
  - The admin uses the Tailscale IP directly — ngrok is for regular users only.
"""
import threading
import logging
import os
import time
from typing import Optional
from flask import current_app

logger = logging.getLogger(__name__)

_tunnel = None
_tunnel_lock = threading.Lock()
_next_retry_at = 0.0
_retry_delay = 30.0
_max_retry_delay = 15 * 60.0


def _is_tunnel_alive() -> bool:
    """Check whether the cached tunnel is still active in ngrok."""
    if _tunnel is None:
        return False
    try:
        from pyngrok import ngrok
        active_urls = {t.public_url for t in ngrok.get_tunnels()}
        return _tunnel.public_url in active_urls
    except Exception:
        return False


def _ngrok_path() -> Optional[str]:
    path = os.getenv("NGROK_PATH", "/usr/local/bin/ngrok")
    return path if os.path.exists(path) else None


def _retry_later() -> None:
    global _next_retry_at, _retry_delay
    _next_retry_at = time.monotonic() + _retry_delay
    _retry_delay = min(_retry_delay * 2, _max_retry_delay)


def _reset_retry() -> None:
    global _next_retry_at, _retry_delay
    _next_retry_at = 0.0
    _retry_delay = 30.0


def start_tunnel(port: int = 5000, force: bool = False) -> Optional[str]:
    """
    Start (or return existing) ngrok HTTPS tunnel to Flask.
    If the tunnel has dropped (e.g. after a network reconnect) it is
    automatically restarted.
    Returns the public URL or None on failure.
    """
    global _tunnel

    with _tunnel_lock:
        if not force and time.monotonic() < _next_retry_at:
            wait_seconds = int(_next_retry_at - time.monotonic())
            logger.info("ngrok restart deferred for %ss after previous failure.", wait_seconds)
            return None

        if _tunnel is not None and _is_tunnel_alive():
            return _tunnel.public_url
        # Tunnel is stale — clear it so we reconnect below
        if _tunnel is not None:
            logger.info("ngrok tunnel appears dead, restarting...")
            try:
                from pyngrok import ngrok
                ngrok.disconnect(_tunnel.public_url)
            except Exception:
                pass
            _tunnel = None

        try:
            from pyngrok import ngrok, conf

            authtoken = current_app.config.get("NGROK_AUTHTOKEN", "")
            static_domain = current_app.config.get("NGROK_STATIC_DOMAIN", "")

            if not authtoken:
                logger.warning("NGROK_AUTHTOKEN not set — tunnel will not start.")
                return None

            conf.get_default().auth_token = authtoken
            installed_ngrok = _ngrok_path()
            if installed_ngrok:
                conf.get_default().ngrok_path = installed_ngrok

            options = {"bind_tls": True}
            if static_domain:
                options["hostname"] = static_domain

            _tunnel = ngrok.connect(port, **options)
            _reset_retry()
            logger.info("ngrok tunnel started: %s", _tunnel.public_url)
            return _tunnel.public_url

        except Exception as exc:
            logger.error("Failed to start ngrok tunnel: %s", exc)
            _retry_later()
            return None


def stop_tunnel() -> None:
    """Disconnect the ngrok tunnel."""
    global _tunnel
    with _tunnel_lock:
        if _tunnel is not None:
            try:
                from pyngrok import ngrok
                ngrok.disconnect(_tunnel.public_url)
            except Exception as exc:
                logger.warning("Error stopping ngrok tunnel: %s", exc)
            finally:
                _tunnel = None


def get_public_url() -> Optional[str]:
    """Return the active public URL without starting a new tunnel."""
    if _tunnel is not None and _is_tunnel_alive():
        return _tunnel.public_url
    return None
