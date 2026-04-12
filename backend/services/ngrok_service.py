"""
ngrok tunnel service.

Architecture:
  - One tunnel exposes the Flask app on port 5000.
  - Users access their personal dashboard at  /dashboard  (protected by JWT).
  - The admin uses the Tailscale IP directly — ngrok is for regular users only.
"""
import threading
import logging
from flask import current_app

logger = logging.getLogger(__name__)

_tunnel = None
_tunnel_lock = threading.Lock()


def start_tunnel(port: int = 5000) -> str | None:
    """
    Start (or return existing) ngrok HTTPS tunnel to Flask.
    Returns the public URL or None on failure.
    """
    global _tunnel

    with _tunnel_lock:
        if _tunnel is not None:
            return _tunnel.public_url

        try:
            from pyngrok import ngrok, conf

            authtoken = current_app.config.get("NGROK_AUTHTOKEN", "")
            static_domain = current_app.config.get("NGROK_STATIC_DOMAIN", "")

            if not authtoken:
                logger.warning("NGROK_AUTHTOKEN not set — tunnel will not start.")
                return None

            conf.get_default().auth_token = authtoken

            options = {"bind_tls": True}
            if static_domain:
                options["hostname"] = static_domain

            _tunnel = ngrok.connect(port, **options)
            logger.info("ngrok tunnel started: %s", _tunnel.public_url)
            return _tunnel.public_url

        except Exception as exc:
            logger.error("Failed to start ngrok tunnel: %s", exc)
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


def get_public_url() -> str | None:
    """Return the active public URL without starting a new tunnel."""
    if _tunnel is not None:
        return _tunnel.public_url
    return None
