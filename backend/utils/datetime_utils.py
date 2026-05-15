"""Datetime helpers for JSON serialization."""
from __future__ import annotations
from datetime import datetime, timezone


def utc_isoformat(value: datetime | None) -> str | None:
    """Return an ISO timestamp with explicit UTC timezone information."""
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    else:
        value = value.astimezone(timezone.utc)
    return value.isoformat()
