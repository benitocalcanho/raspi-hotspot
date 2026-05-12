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

from utils.timezone_utils import get_effective_timezone, get_effective_timezone_info, local_today

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
def _parse_ical_events_active_today(ical_text: str, today: Optional[date] = None):
    """
    Parse an iCal string and return a list of (SUMMARY, DTSTART, DTEND) tuples for events active today.
    Handles line folding (RFC 5545: continuation lines start with a space/tab).
    """
    unfolded = re.sub(r"\r?\n[ \t]", "", ical_text)
    target_day = today or date.today()
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
        if dt_start <= target_day < dt_end:
            active_events.append((m_summary.group(1).strip(), dt_start, dt_end))
    return active_events


def sync_calendar_ical(app) -> dict:
    """
    iCal-based sync: fetch the private iCal URL, find events active today,
    and rotate the single active guest account to today's guest.
    Returns a detail dict describing every change made.
    """
    result = {
        "status": "ok",
        "error": None,
        "guest_created": False,
        "guest_updated": False,
        "guest_username": None,
        "guest_event_title": None,
        "guest_valid_until": None,   # ISO date string YYYY-MM-DD
        "guests_deleted": 0,
        "cleaner_deactivated": False,
        "cleaner_activated": False,
        "cleaner_created": False,
    }

    with app.app_context():
        import requests as req
        from models import db
        from models.user import User
        from models.setting import Setting
        from services.audit_service import log_event

        ical_url = (Setting.get("ICAL_URL") or "").strip()
        password_mode = Setting.get("CALENDAR_GUEST_PASSWORD_MODE") or "fixed"
        default_password = Setting.get("CALENDAR_GUEST_DEFAULT_PASSWORD") or "guest12345"

        if not ical_url:
            result["status"] = "no_url"
            return result

        try:
            resp = req.get(ical_url, timeout=15)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("iCal fetch failed: %s", exc)
            result["status"] = "fetch_error"
            result["error"] = str(exc)
            return result

        active_events = _parse_ical_events_active_today(resp.text, today=local_today(app=app))
        if not active_events:
            # No ongoing event — delete guests and activate/create cleaner
            old_guests = User.query.filter_by(created_by="calendar", role="guest").all()
            result["guests_deleted"] = len(old_guests)
            for old in old_guests:
                db.session.delete(old)
            cleaner_username = (Setting.get("CLEANER_USERNAME") or app.config.get("CLEANER_USERNAME", "cleaner")).lower()
            cleaner_password = Setting.get("CLEANER_PASSWORD") or app.config.get("CLEANER_PASSWORD", "cleaner12345")
            cleaners = User.query.filter_by(role="cleaner").all()
            if not cleaners:
                cleaner = User(
                    username=cleaner_username,
                    email=User.build_internal_email(cleaner_username),
                    role="cleaner",
                    created_by="manual",
                    is_active=True,
                )
                db.session.add(cleaner)
                try:
                    cleaner.set_password(cleaner_password)
                except Exception as exc:
                    logger.error("Cleaner password error: %s", exc)
                    db.session.rollback()
                    result["status"] = "error"
                    result["error"] = f"Cleaner password error: {exc}"
                    return result
                result["cleaner_created"] = True
                logger.info("iCal sync: no cleaner found, created cleaner '%s'.", cleaner_username)
            else:
                for cleaner in cleaners:
                    cleaner.is_active = True
                    db.session.add(cleaner)
                result["cleaner_activated"] = True
            db.session.commit()
            logger.info("iCal sync: no active events today. Deleted %d calendar guest(s).", result["guests_deleted"])
            return result

        # Use the first active event
        raw_name, dt_start, dt_end = active_events[0][0], active_events[0][1], active_events[0][2]
        first_word = raw_name.split()[0] if raw_name.split() else raw_name
        new_username = normalize_username(first_word)
        if not new_username:
            logger.warning("iCal sync: could not derive username from '%s'.", raw_name)
            result["error"] = f"Could not derive username from event title '{raw_name}'"
            return result

        result["guest_username"] = new_username
        result["guest_event_title"] = raw_name
        result["guest_valid_until"] = dt_end.isoformat()

        # Determine guest password
        if password_mode == "from_event":
            words = raw_name.split()
            guest_password = words[-1] if words else default_password
            logger.info("iCal sync: using last word of event title as password: '%s'", guest_password)
        else:
            guest_password = default_password

        # Deactivate all cleaner accounts during a guest stay
        cleaners = User.query.filter_by(role="cleaner").all()
        deactivated_any = False
        for cleaner in cleaners:
            if cleaner.is_active:
                cleaner.is_active = False
                db.session.add(cleaner)
                deactivated_any = True
        if cleaners:
            db.session.commit()
        if deactivated_any:
            result["cleaner_deactivated"] = True
            logger.info("All cleaner accounts deactivated due to active guest stay.")

        # Delete all previous calendar guests (keeps the table clean)
        old_guests = User.query.filter_by(created_by="calendar", role="guest").all()
        for old in old_guests:
            if old.username != new_username:
                db.session.delete(old)
        db.session.flush()

        # Update existing guest or create fresh one
        existing = User.query.filter_by(username=new_username).first()
        if existing:
            existing.is_active = True
            existing.role = "guest"
            existing.created_by = "calendar"
            existing.valid_until = dt_end
            try:
                existing.set_password(guest_password)
            except ValueError:
                pass
            db.session.commit()
            log_event("guest_rotated", user_id=existing.id,
                      detail={"username": new_username, "source": "ical"})
            logger.info("iCal sync: updated existing guest '%s'.", new_username)
            result["guest_updated"] = True
            return result

        # Create fresh guest account
        try:
            new_user = User(
                username=new_username,
                email=User.build_internal_email(new_username),
                role="guest",
                created_by="calendar",
                valid_until=dt_end,
            )
            new_user.set_password(guest_password)
            db.session.add(new_user)
            db.session.commit()
            log_event("user_created_from_calendar", user_id=new_user.id,
                      detail={"username": new_username, "source": "ical", "event_title": raw_name})
            logger.info("iCal sync: created guest '%s' (from '%s').", new_username, raw_name)
            result["guest_created"] = True
            return result
        except Exception as exc:
            db.session.rollback()
            logger.error("iCal sync: failed to create guest: %s", exc)
            result["status"] = "error"
            result["error"] = str(exc)
            return result


# ── Sync job ──────────────────────────────────────────────────────────────────

def sync_calendar(app) -> dict:
    """
    Main sync entry point. Uses iCal mode if ICAL_URL is configured
    (recommended — no API credentials needed), otherwise falls back to
    the Google Calendar API mode.
    Runs inside an app context (called by APScheduler or manual trigger).
    Returns a detail dict (iCal mode) or a minimal dict (legacy mode).
    """
    # DB setting takes priority: the dashboard stores ICAL_URL there, not in .env
    with app.app_context():
        from models.setting import Setting
        ical_url = (Setting.get("ICAL_URL") or "").strip() or app.config.get("ICAL_URL", "").strip()
    if ical_url:
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

        return {"status": "ok", "guest_created": created > 0, "guest_updated": False,
                "guest_username": None, "guest_event_title": None, "guest_valid_until": None,
                "guests_deleted": 0, "cleaner_deactivated": False,
                "cleaner_activated": False, "cleaner_created": False, "error": None}


# ── APScheduler setup ─────────────────────────────────────────────────────────

def checkout_guests(app) -> None:
    """
    Run at checkout time (default 12:00).
    Re-checks the calendar:
    - If an event still covers today (multi-day stay): keep guest, ensure cleaner is deactivated.
    - If no active event: delete calendar guests, then create or reactivate the cleaner account.
    """
    with app.app_context():
        from models import db
        from models.user import User
        from models.setting import Setting
        from services.audit_service import log_event

        import requests as req
        cfg = app.config
        # Read from DB first (dashboard saves there), fall back to .env
        ical_url = (Setting.get("ICAL_URL") or "").strip() or cfg.get("ICAL_URL", "").strip()
        if not ical_url:
            logger.info("Checkout job: no iCal URL configured.")
            return
        try:
            resp = req.get(ical_url, timeout=15)
            resp.raise_for_status()
        except Exception as exc:
            logger.error("iCal fetch failed during checkout: %s", exc)
            return
        active_events = _parse_ical_events_active_today(resp.text, today=local_today(app=app))
        if active_events:
            # Ongoing multi-day stay: keep guest, ensure cleaner is deactivated
            logger.info("Checkout job: ongoing event(s) found, not deleting guest.")
            cleaner = User.query.filter_by(role="cleaner").first()
            if cleaner and cleaner.is_active:
                cleaner.is_active = False
                db.session.add(cleaner)
                db.session.commit()
                logger.info("Cleaner account deactivated due to ongoing guest event.")
            return

        # No active event — delete calendar guests and activate or create cleaner
        guests = User.query.filter_by(created_by="calendar", role="guest").all()
        count = len(guests)
        for g in guests:
            db.session.delete(g)

        # Activate cleaner if exists; create it if it doesn't
        cleaner_username = (Setting.get("CLEANER_USERNAME") or cfg.get("CLEANER_USERNAME", "cleaner")).lower()
        cleaner_password = Setting.get("CLEANER_PASSWORD") or cfg.get("CLEANER_PASSWORD", "cleaner12345")
        cleaners = User.query.filter_by(role="cleaner").all()
        if not cleaners:
            new_cleaner = User(
                username=cleaner_username,
                email=User.build_internal_email(cleaner_username),
                role="cleaner",
                created_by="manual",
                is_active=True,
            )
            try:
                new_cleaner.set_password(cleaner_password)
            except Exception as exc:
                logger.error("Checkout job: cleaner password error: %s", exc)
                db.session.rollback()
                return
            db.session.add(new_cleaner)
            logger.info("Checkout job: no cleaner found, created cleaner '%s'.", cleaner_username)
        else:
            for c in cleaners:
                c.is_active = True
                db.session.add(c)

        db.session.commit()
        if count:
            logger.info("Checkout job: deleted %d guest(s). Cleaner activated.", count)
            log_event("guests_checked_out", detail={"count": count})
        else:
            logger.info("Checkout job: no calendar guests to remove. Cleaner activated.")


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

        tz_info = get_effective_timezone_info(app=app)
        scheduler_tz = get_effective_timezone(app=app)
        _scheduler = BackgroundScheduler(timezone=scheduler_tz)
        _scheduler.add_job(
            checkout_guests,
            CronTrigger(hour=co_h, minute=co_m, timezone=scheduler_tz),
            args=[app],
            id="checkout_guests",
            replace_existing=True,
        )
        _scheduler.add_job(
            sync_calendar,
            CronTrigger(hour=ci_h, minute=ci_m, timezone=scheduler_tz),
            args=[app],
            id="checkin_sync",
            replace_existing=True,
        )
        _scheduler.start()
        checkout_job = _scheduler.get_job("checkout_guests")
        checkin_job = _scheduler.get_job("checkin_sync")
        logger.info(
            "Scheduler started: checkout=%s, checkin=%s, timezone=%s(source=%s), next_checkout=%s, next_checkin=%s.",
            checkout_str,
            checkin_str,
            tz_info["name"],
            tz_info["source"],
            checkout_job.next_run_time if checkout_job else None,
            checkin_job.next_run_time if checkin_job else None,
        )
    except Exception as exc:
        logger.error("Failed to start calendar scheduler: %s", exc)
