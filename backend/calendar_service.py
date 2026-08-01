"""
Google Calendar sync for confirmed bookings.

Uses the app's existing Cloud Run service account, self-impersonated to pick
up Calendar scope (the attached identity's default token doesn't include it).
No key file, no OAuth consent flow — the host just shares her calendar with
the service account's email address, the same way you'd share it with any
other collaborator.
"""
import logging
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import google.auth
from google.auth import impersonated_credentials
from google.auth.transport.requests import AuthorizedSession

log = logging.getLogger(__name__)

CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar"]
CALENDAR_ID = os.getenv("HOST_EMAIL", "")
GCP_PROJECT = os.getenv("GCP_PROJECT", "mahitha-booking")
SERVICE_ACCOUNT_EMAIL = f"mahitha-booking-api@{GCP_PROJECT}.iam.gserviceaccount.com"
SESSION_DURATION_MINUTES = 60
DISPLAY_TZ = ZoneInfo("America/New_York")

_session = None


def _get_session():
    """Lazily build an AuthorizedSession scoped for Calendar, via self-
    impersonation of the attached service account. Requires that SA to have
    roles/iam.serviceAccountTokenCreator on itself."""
    global _session
    if _session is not None:
        return _session
    try:
        source_creds, _ = google.auth.default()
        target_creds = impersonated_credentials.Credentials(
            source_credentials=source_creds,
            target_principal=SERVICE_ACCOUNT_EMAIL,
            target_scopes=CALENDAR_SCOPES,
        )
        _session = AuthorizedSession(target_creds)
    except Exception:
        log.exception("Failed to build Calendar-scoped credentials")
        return None
    return _session


def create_event(name: str, email: str, phone: str, goal: str, challenge: str,
                  slot_datetime: str, booking_id: str) -> str | None:
    """Create a Calendar event on CALENDAR_ID for a confirmed booking.
    Returns the created event's ID, or None on any failure — calendar sync
    is best-effort and must never break the booking flow."""
    if not CALENDAR_ID:
        log.warning("HOST_EMAIL not set — skipping calendar sync")
        return None
    session = _get_session()
    if session is None:
        return None

    start = datetime.fromisoformat(slot_datetime).astimezone(DISPLAY_TZ)
    end = start + timedelta(minutes=SESSION_DURATION_MINUTES)

    body = {
        "summary": f"Coaching Session — {name}",
        "description": (
            f"Booking ID: {booking_id}\n"
            f"Email: {email}\n"
            f"Phone: {phone or '—'}\n\n"
            f"Goals: {goal}\n\n"
            f"{challenge}"
        ),
        "start": {"dateTime": start.isoformat(), "timeZone": "America/New_York"},
        "end": {"dateTime": end.isoformat(), "timeZone": "America/New_York"},
    }

    try:
        resp = session.post(
            f"https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events",
            json=body,
            timeout=15,
        )
        resp.raise_for_status()
        event_id = resp.json().get("id")
        log.info("Created calendar event %s for booking %s", event_id, booking_id)
        return event_id
    except Exception:
        log.exception("Failed to create calendar event for booking %s", booking_id)
        return None


def delete_event(event_id: str):
    """Delete a previously-created Calendar event. Swallows errors — a stray
    leftover event is preferable to breaking the cancellation flow."""
    if not CALENDAR_ID or not event_id:
        return
    session = _get_session()
    if session is None:
        return
    try:
        resp = session.delete(
            f"https://www.googleapis.com/calendar/v3/calendars/{CALENDAR_ID}/events/{event_id}",
            timeout=15,
        )
        if resp.status_code not in (200, 204, 404, 410):
            resp.raise_for_status()
        log.info("Deleted calendar event %s", event_id)
    except Exception:
        log.exception("Failed to delete calendar event %s", event_id)
