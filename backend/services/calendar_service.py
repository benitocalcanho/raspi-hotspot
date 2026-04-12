"""
Google Calendar sync service.

Convention used for automatic user creation:
  Calendar event title format:  CREATE_USER | username | email | password
  Example:  CREATE_USER | johndoe | john@example.com | Temp1234!

The keyword prefix is configurable via CALENDAR_USER_CREATION_KEYWORD in .env.
The sync runs as a background APScheduler job every CALENDAR_SYNC_INTERVAL seconds.
"""
import logging
import re
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


# ── OAuth flow helpers ─────────────────────────────────────────────────────────

def _build_service(credentials_file: str, token_file: str):
    """Authenticate with Google and return a Calendar API service object."""
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    import os

    SCOPES = ["https://www.googleapis.com/auth/calendar.readonly"]
    creds = None

    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_file, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_file, "w") as f:
            f.write(creds.to_json())

    return build("calendar", "v3", credentials=creds)


# ── Event parser ──────────────────────────────────────────────────────────────

_EVENT_RE = re.compile(
    r"^(?P<keyword>[^|]+)\|(?P<username>[^|]+)\|(?P<email>[^|]+)\|(?P<password>.+)$"
)


def parse_user_creation_event(title: str, keyword: str) -> dict | None:
    """
    Parse a calendar event title into user fields.
    Returns None if the title doesn't match the expected format.
    """
    stripped = title.strip()
    if not stripped.upper().startswith(keyword.upper()):
        return None

    match = _EVENT_RE.match(stripped)
    if not match:
        return None

    return {
        "username": match.group("username").strip(),
        "email": match.group("email").strip(),
        "password": match.group("password").strip(),
    }


# ── Sync job ──────────────────────────────────────────────────────────────────

def sync_calendar(app) -> int:
    """
    Fetch upcoming Google Calendar events and create users for matching ones.
    Runs inside an app context (called by APScheduler).
    Returns the number of users created in this run.
    """
    with app.app_context():
        from models import db
        from models.user import User
        from services.audit_service import log_event

        cfg = app.config
        credentials_file = cfg.get("GOOGLE_CREDENTIALS_FILE", "")
        token_file = cfg.get("GOOGLE_TOKEN_FILE", "")
        calendar_id = cfg.get("GOOGLE_CALENDAR_ID", "primary")
        keyword = cfg.get("CALENDAR_USER_CREATION_KEYWORD", "CREATE_USER")

        if not credentials_file or not token_file:
            logger.debug("Google Calendar credentials not configured — skipping sync.")
            return 0

        try:
            service = _build_service(credentials_file, token_file)
        except Exception as exc:
            logger.error("Google Calendar auth failed: %s", exc)
            return 0

        now = datetime.now(timezone.utc).isoformat()
        try:
            events_result = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    timeMin=now,
                    maxResults=50,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
        except Exception as exc:
            logger.error("Google Calendar API error: %s", exc)
            return 0

        created = 0
        for event in events_result.get("items", []):
            title = event.get("summary", "")
            event_id = event.get("id", "")

            # Skip if we already processed this event
            if User.query.filter_by(calendar_event_id=event_id).first():
                continue

            parsed = parse_user_creation_event(title, keyword)
            if not parsed:
                continue

            if User.query.filter_by(username=parsed["username"]).first():
                logger.warning("Calendar sync: user '%s' already exists — skipping.", parsed["username"])
                continue

            try:
                new_user = User(
                    username=parsed["username"],
                    email=parsed["email"],
                    role="user",
                    created_by="calendar",
                    calendar_event_id=event_id,
                )
                new_user.set_password(parsed["password"])
                db.session.add(new_user)
                db.session.commit()

                log_event(
                    "user_created_from_calendar",
                    user_id=new_user.id,
                    detail={"event_id": event_id, "title": title},
                )
                logger.info("Created user '%s' from calendar event.", parsed["username"])
                created += 1

            except Exception as exc:
                db.session.rollback()
                logger.error("Failed to create user from calendar event '%s': %s", event_id, exc)

        return created


# ── APScheduler setup ─────────────────────────────────────────────────────────

def start_scheduler(app) -> None:
    """Start the background calendar sync scheduler."""
    try:
        from apscheduler.schedulers.background import BackgroundScheduler

        interval = app.config.get("CALENDAR_SYNC_INTERVAL", 300)
        scheduler = BackgroundScheduler()
        scheduler.add_job(sync_calendar, "interval", seconds=interval, args=[app])
        scheduler.start()
        logger.info("Calendar sync scheduler started (interval=%ds).", interval)
    except Exception as exc:
        logger.error("Failed to start calendar scheduler: %s", exc)
