#!/usr/bin/env python3
"""Run one calendar sync cycle and print created-user count."""
from app import create_app
from services.calendar_service import sync_calendar


def main() -> int:
    app = create_app()
    with app.app_context():
        created = sync_calendar(app)
    print(f"users_created={created}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
