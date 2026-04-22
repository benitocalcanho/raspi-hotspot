"""
iCal calendar sync service (Google API code removed).

Only iCal mode is supported: Set ICAL_URL to the private iCal URL from Google Calendar settings.
Each day the job checks for an event starting today, reads the first
word of the event title as the guest's username, and rotates the
single active guest account to that name.
"""
import logging
import re
from datetime import date, datetime, timezone
from typing import Optional, Dict

logger = logging.getLogger(__name__)
_scheduler = None  # module-level reference so it can be shut down on restart





# ── Event parser ──────────────────────────────────────────────────────────────

_EVENT_RE = re.compile(
    r"^(?P<keyword>[^|]+)\|(?P<username>[^|]+)\|(?P<password>.+)$"
)


def parse_user_creation_event(title: str, keyword: str) -> Optional[Dict[str, str]]:
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
        "password": match.group("password").strip(),
    }


def normalize_username(raw_value: str) -> Optional[str]:
    cleaned = re.sub(r"[^a-z0-9]+", "_", raw_value.strip().lower()).strip("_")
    if not cleaned:
        return None
    return cleaned[:50]


def parse_guest_username_from_title(title: str, prefix: str) -> Optional[str]:
    stripped = title.strip()
    if not stripped:
        return None

    if prefix:
        upper_prefix = prefix.upper()
        if not stripped.upper().startswith(upper_prefix):
            return None

        remainder = stripped[len(prefix):].strip()
        if remainder.startswith("|"):
            remainder = remainder[1:].strip()
        elif remainder.startswith(":"):
            remainder = remainder[1:].strip()
        elif remainder.startswith("-"):
            remainder = remainder[1:].strip()
        guest_name = remainder
    else:
        guest_name = stripped

    return normalize_username(guest_name)


def next_available_username(User, base_username: str) -> str:
    candidate = base_username
    suffix = 2
    while User.query.filter_by(username=candidate).first():
        candidate = f"{base_username}_{suffix}"
        suffix += 1
    return candidate


# ── iCal sync (simple mode) ───────────────────────────────────────────────────


# New: Parse all events and return those active today (today in [DTSTART, DTEND))
def _parse_ical_events_active_today(ical_text: str):
    """
    Parse an iCal string and return a list of (SUMMARY, DTSTART, DTEND) tuples for events active today.
    Handles line folding (RFC 5545: continuation lines start with a space/tab).
    """
    unfolded = re.sub(r"\r?\n[ \t]", "", ical_text)
    today = date.today()
    active_events = []
    for block in re.split(r"BEGIN:VEVENT", unfolded):
        # DTSTART
        m_start = re.search(r"DTSTART[^:]*:(\d{8})", block)
        m_end = re.search(r"DTEND[^:]*:(\d{8})", block)
        m_summary = re.search(r"SUMMARY:(.*)", block)
        if not (m_start and m_end and m_summary):
            continue
        dt_start = datetime.strptime(m_start.group(1), "%Y%m%d").date()
        dt_end = datetime.strptime(m_end.group(1), "%Y%m%d").date()
        # iCal: DTEND is exclusive, so event is active if today in [start, end)
        if dt_start <= today < dt_end:
            active_events.append((m_summary.group(1).strip(), dt_start, dt_end))
    return active_events


def sync_calendar_ical(app) -> int:
    """
    iCal-based sync: fetch the private iCal URL, find events starting today,
    and rotate the single active guest account to today's guest name.

    Logic mirrors the original web2py bash script:
      - Event title first word → new guest username (lowercased)
      - All previous calendar-created guests are deactivated
      - One active guest account at a time
      - Fixed password from ICAL_GUEST_PASSWORD setting
    Returns number of guest accounts created/updated (0 or 1).
    """
    with app.app_context():
        import requests as req
        from models import db
        from models.user import User
        from services.audit_service import log_event

        from models.setting import Setting
        ical_url = Setting.get("ICAL_URL") or ""
        guest_password = Setting.get("ICAL_GUEST_PASSWORD") or Setting.get("CALENDAR_GUEST_DEFAULT_PASSWORD") or "guest12345"
        ical_url = ical_url.strip()
        guest_password = guest_password.strip()

        if not ical_url:
            return 0

        try:
            resp = req.get(ical_url, timeout=15)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("iCal fetch failed: %s", exc)
            return 0



        active_events = _parse_ical_events_active_today(resp.text)
        if not active_events:
            # No ongoing event: delete all calendar-created guest accounts
            old_guests = User.query.filter_by(created_by="calendar", role="guest").all()
            deleted_count = 0
            for old in old_guests:
                db.session.delete(old)
                deleted_count += 1
            # Ensure cleaner account exists and is activated
            from models.setting import Setting
            cleaner_username = (Setting.get("CLEANER_USERNAME") or app.config.get("CLEANER_USERNAME", "cleaner")).lower()
            cleaner_password = Setting.get("CLEANER_PASSWORD") or app.config.get("CLEANER_PASSWORD", "cleaner12345")
            cleaner = User.query.filter_by(role="cleaner").first()
            if not cleaner:
                from models.user import User as UserModel
                cleaner = UserModel(
                    username=cleaner_username,
                    email=UserModel.build_internal_email(cleaner_username),
                    role="cleaner",
                    created_by="manual",
                    is_active=True,
                )
                db.session.add(cleaner)
                logger.info(f"iCal sync: no cleaner found, created cleaner '{cleaner_username}'.")
            else:
                cleaner.is_active = True
                cleaner.username = cleaner_username
                cleaner.email = cleaner.__class__.build_internal_email(cleaner_username)
                db.session.add(cleaner)
            # Always set password to dashboard value
            try:
                cleaner.set_password(cleaner_password)
            except Exception as exc:
                logger.error(f"Cleaner password error: {exc}")
                db.session.rollback()
                raise ValueError(f"Cleaner password error: {exc}")
            db.session.commit()
            logger.info(f"iCal sync: no active events today. Deleted {deleted_count} calendar guest(s). Cleaner activated.")
            return 0

        # Use the first active event for guest username
        raw_name = active_events[0][0]
        first_word = raw_name.split()[0] if raw_name.split() else raw_name
        new_username = normalize_username(first_word)
        if not new_username:
            logger.warning("iCal sync: could not derive username from '%s'.", raw_name)
            return 0
        # Deactivate cleaner account if exists
        cleaner = User.query.filter_by(role="cleaner").first()
        if cleaner and cleaner.is_active:
            cleaner.is_active = False
            db.session.add(cleaner)
            db.session.commit()
            logger.info("Cleaner account deactivated due to guest creation.")

        # Delete all previous calendar guests (keeps the table clean)
        old_guests = User.query.filter_by(created_by="calendar", role="guest").all()
        for old in old_guests:
            if old.username != new_username:
                db.session.delete(old)
        db.session.flush()

        # Check if a guest with this username already exists (same guest returning)
        existing = User.query.filter_by(username=new_username).first()
        if existing:
            existing.is_active = True
            existing.role = "guest"
            existing.created_by = "calendar"
            try:
                existing.set_password(guest_password)
            except ValueError:
                pass
            db.session.commit()
            log_event("guest_rotated", user_id=existing.id,
                      detail={"username": new_username, "source": "ical"})
            logger.info("iCal sync: updated existing guest '%s'.", new_username)
            return 1

        # Create fresh guest account
        try:
            new_user = User(
                username=new_username,
                email=User.build_internal_email(new_username),
                role="guest",
                created_by="calendar",
            )
            new_user.set_password(guest_password)
            db.session.add(new_user)
            db.session.commit()
            log_event("user_created_from_calendar", user_id=new_user.id,
                      detail={"username": new_username, "source": "ical", "event_title": raw_name})
            logger.info("iCal sync: created guest '%s' (from '%s').", new_username, raw_name)
            return 1
        except Exception as exc:
            db.session.rollback()
            logger.error("iCal sync: failed to create guest: %s", exc)
            return 0


# ── Sync job ──────────────────────────────────────────────────────────────────

def sync_calendar(app) -> int:
    """
    Main sync entry point. Uses iCal mode if ICAL_URL is configured
    (recommended — no API credentials needed), otherwise falls back to
    the Google Calendar API mode.
    Runs inside an app context (called by APScheduler or manual trigger).
    Returns the number of users created/updated in this run.
    """
    if app.config.get("ICAL_URL", "").strip():
        return sync_calendar_ical(app)

    # ── Google Calendar API mode (legacy) ─────────────────────────────────────
    with app.app_context():
        from models import db
        from models.user import User
        from services.audit_service import log_event

        cfg = app.config
        credentials_file = cfg.get("GOOGLE_CREDENTIALS_FILE", "")
        credentials_json = cfg.get("GOOGLE_CREDENTIALS_JSON", "")
        token_file = cfg.get("GOOGLE_TOKEN_FILE", "")
        calendar_id = cfg.get("GOOGLE_CALENDAR_ID", "primary")
        keyword = cfg.get("CALENDAR_USER_CREATION_KEYWORD", "CREATE_USER")
        guest_auto_create = cfg.get("CALENDAR_GUEST_AUTO_CREATE", True)
        guest_prefix = cfg.get("CALENDAR_GUEST_EVENT_PREFIX", "GUEST")
        guest_password = cfg.get("CALENDAR_GUEST_DEFAULT_PASSWORD", "guest12345")

        if not (credentials_file or credentials_json) or not token_file:
            logger.debug("Google Calendar credentials not configured — skipping sync.")
            return 0

        try:
            service = _build_service(credentials_file, token_file, credentials_json)
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
            mode = "manual"
            if not parsed and guest_auto_create:
                guest_username = parse_guest_username_from_title(title, guest_prefix)
                if guest_username:
                    parsed = {
                        "username": guest_username,
                        "password": guest_password,
                    }
                    mode = "guest_auto"

            if not parsed:
                continue

            if mode == "guest_auto":
                parsed["username"] = next_available_username(User, parsed["username"])
            elif User.query.filter_by(username=parsed["username"]).first():
                logger.warning("Calendar sync: user '%s' already exists — skipping.", parsed["username"])
                continue

            try:
                new_user = User(
                    username=parsed["username"],
                    email=User.build_internal_email(parsed["username"]),
                    role="guest",
                    created_by="calendar",
                    calendar_event_id=event_id,
                )
                new_user.set_password(parsed["password"])
                db.session.add(new_user)
                db.session.commit()

                log_event(
                    "user_created_from_calendar",
                    user_id=new_user.id,
                    detail={"event_id": event_id, "title": title, "mode": mode},
                )
                logger.info("Created user '%s' from calendar event.", parsed["username"])
                created += 1

            except Exception as exc:
                db.session.rollback()
                logger.error("Failed to create user from calendar event '%s': %s", event_id, exc)

        return created


# ── APScheduler setup ─────────────────────────────────────────────────────────

def checkout_guests(app) -> None:
    """
    Deactivate all active calendar-created guests.
    Runs at checkout time (default 12:00) so previous guests lose access.
    """
    with app.app_context():
        from models import db
        from models.user import User
        from services.audit_service import log_event

        import requests as req
        cfg = app.config
        ical_url = cfg.get("ICAL_URL", "").strip()
        if not ical_url:
            logger.info("Checkout job: no iCal URL configured.")
            return
        try:
            resp = req.get(ical_url, timeout=15)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("iCal fetch failed during checkout: %s", exc)
            return
        active_events = _parse_ical_events_active_today(resp.text)
        if active_events:
            logger.info("Checkout job: ongoing event(s) found, not deleting guest.")
            # Deactivate cleaner if active
            cleaner = User.query.filter_by(role="cleaner").first()
            if cleaner and cleaner.is_active:
                cleaner.is_active = False
                db.session.add(cleaner)
                db.session.commit()
                logger.info("Cleaner account deactivated due to ongoing guest event.")
            return
        guests = User.query.filter_by(created_by="calendar", role="guest").all()
        if not guests:
            logger.info("Checkout job: no calendar guests to remove.")
            # Activate cleaner if exists
            cleaner = User.query.filter_by(role="cleaner").first()
            if cleaner:
                cleaner.is_active = True
                db.session.add(cleaner)
                db.session.commit()
                logger.info("Cleaner account activated (no guests present).")
            return
        count = len(guests)
        for g in guests:
            db.session.delete(g)
        # Activate cleaner if exists
        cleaner = User.query.filter_by(role="cleaner").first()
        if cleaner:
            cleaner.is_active = True
            db.session.add(cleaner)
        db.session.commit()
        logger.info("Checkout job: deleted %d guest(s). Cleaner activated.", count)
        log_event("guests_checked_out", detail={"count": count})


def _parse_time(time_str: str):
    """Parse 'HH:MM' string into (hour, minute) integers. Returns (12, 0) on error."""
    try:
        h, m = time_str.strip().split(":")
        return int(h), int(m)
    except Exception:
        return (12, 0)


def start_scheduler(app) -> None:
    """
    Start two daily cron jobs:
      checkout_time (default 12:00) — deactivate current guests
      checkin_time  (default 14:00) — fetch iCal and create today's guest
    Times are read from app.config so they can be changed via the Settings GUI.
    """
    global _scheduler
    try:
        from apscheduler.schedulers.background import BackgroundScheduler
        from apscheduler.triggers.cron import CronTrigger

        # Shut down existing scheduler if already running
        if _scheduler and _scheduler.running:
            _scheduler.shutdown(wait=False)

        checkout_str = app.config.get("CHECKOUT_TIME", "12:00")
        checkin_str  = app.config.get("CHECKIN_TIME",  "14:00")

        co_h, co_m = _parse_time(checkout_str)
        ci_h, ci_m = _parse_time(checkin_str)

        _scheduler = BackgroundScheduler()
        _scheduler.add_job(
            checkout_guests,
            CronTrigger(hour=co_h, minute=co_m),
            args=[app],
            id="checkout_guests",
            replace_existing=True,
        )
        _scheduler.add_job(
            sync_calendar,
            CronTrigger(hour=ci_h, minute=ci_m),
            args=[app],
            id="checkin_sync",
            replace_existing=True,
        )
        _scheduler.start()
        logger.info(
            "Scheduler started: checkout=%s, checkin=%s.",
            checkout_str, checkin_str,
        )
    except Exception as exc:
        logger.error("Failed to start calendar scheduler: %s", exc)
