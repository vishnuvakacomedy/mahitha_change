"""
Email notifications via Gmail SMTP + App Password.
Set GMAIL_USER and GMAIL_APP_PASSWORD in your environment.
"""
import html
import logging
import os
import smtplib
import ssl
from datetime import datetime
from email.message import EmailMessage
from email.utils import formataddr
from zoneinfo import ZoneInfo

log = logging.getLogger(__name__)

GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
SENDER_NAME = "Mahitha Vaka"

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_TIMEOUT = 15  # seconds

DISPLAY_TZ = ZoneInfo("America/New_York")


def _send(to_email: str, subject: str, html_body: str):
    """Send an email via Gmail SMTP. Logs and swallows errors so one failed
    send never breaks the booking flow."""
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        log.warning(
            "GMAIL_USER/GMAIL_APP_PASSWORD not set — skipping email to %s", to_email
        )
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = formataddr((SENDER_NAME, GMAIL_USER))
    msg["To"] = to_email
    # Plain-text fallback for clients that don't render HTML.
    msg.set_content("This email is best viewed in an HTML-capable client.")
    msg.add_alternative(html_body, subtype="html")

    try:
        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SMTP_TIMEOUT) as smtp:
            smtp.starttls(context=context)
            smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            smtp.send_message(msg)
        log.info("Sent %r to %s", subject, to_email)
    except Exception:
        log.exception("Failed to send email to %s", to_email)


def _format_dt(iso_str: str) -> str:
    """Format an ISO-8601 UTC string as a human-readable Eastern Time string."""
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        dt_et = dt.astimezone(DISPLAY_TZ)
        # Portable: no %-d / %-I. Strip leading zeros manually.
        day = dt_et.day
        hour12 = dt_et.strftime("%I").lstrip("0") or "12"
        tz_label = dt_et.tzname() or "ET"  # "EST" or "EDT" depending on DST
        return dt_et.strftime(f"%A, %B {day}, %Y at {hour12}:%M %p {tz_label}")
    except Exception:
        return iso_str


def _e(value) -> str:
    """HTML-escape a value for safe inclusion in email templates."""
    return html.escape("" if value is None else str(value), quote=True)


def send_booking_confirmation(name: str, email: str, slot_datetime: str, booking_id: str):
    """Send confirmation email to the person who booked."""
    formatted_dt = _e(_format_dt(slot_datetime))
    safe_name = _e(name)
    safe_booking_id = _e(booking_id)
    subject = "Your Coaching Session is Confirmed — Mahitha Vaka"
    html_body = f"""
    <div style="font-family: Georgia, serif; max-width: 560px; margin: 0 auto; color: #2C2C2C;">
      <div style="background: #846754; padding: 24px 32px; border-radius: 8px 8px 0 0;">
        <h1 style="color: white; font-weight: normal; font-size: 22px; margin: 0;">
          You're Booked!
        </h1>
      </div>
      <div style="background: #faf7f2; padding: 32px; border: 1px solid #ddd8ce; border-top: none; border-radius: 0 0 8px 8px;">
        <p style="margin-bottom: 16px;">Hi {safe_name},</p>
        <p style="margin-bottom: 24px;">
          Your coaching session with <strong>Mahitha Vaka</strong> is confirmed.
          I look forward to connecting with you!
        </p>

        <div style="background: #F1EDE4; border-left: 3px solid #846754; padding: 16px 20px;
                    border-radius: 0 6px 6px 0; margin-bottom: 24px;">
          <p style="margin: 0 0 8px; font-size: 13px; color: #888;">SESSION DETAILS</p>
          <p style="margin: 0 0 6px;"><strong>Date &amp; Time:</strong> {formatted_dt}</p>
          <p style="margin: 0 0 6px;"><strong>Duration:</strong> 60 minutes</p>
          <p style="margin: 0;"><strong>Format:</strong> Zoom (link will be sent separately)</p>
        </div>

        <p style="margin-bottom: 8px; font-size: 13px; color: #888;">
          Booking reference: <code style="background: #e8e4dc; padding: 2px 6px; border-radius: 4px;">{safe_booking_id}</code>
        </p>

        <p style="margin-top: 24px; font-size: 13px; color: #888;">
          Need to reschedule? Reply to this email and we'll sort it out.
        </p>

        <p style="margin-top: 32px;">Warmly,<br/><strong>Mahitha Vaka</strong><br/>
          <a href="https://mahithavaka.com" style="color: #846754;">mahithavaka.com</a>
        </p>
      </div>
    </div>
    """
    _send(email, subject, html_body)


def send_host_notification(guest_name: str, guest_email: str, guest_phone: str,
                           goal: str, challenge: str,
                           slot_datetime: str, booking_id: str):
    """Notify Mahitha when someone books a session."""
    host_email = os.getenv("HOST_EMAIL", GMAIL_USER or "")
    if not host_email:
        log.warning("No HOST_EMAIL or GMAIL_USER set — skipping host notification")
        return

    formatted_dt = _e(_format_dt(slot_datetime))
    safe_name = _e(guest_name)
    safe_email = _e(guest_email)
    safe_phone = _e(guest_phone) if guest_phone else "—"
    safe_goal = _e(goal).replace("\n", "<br/>")
    safe_challenge = _e(challenge).replace("\n", "<br/>")
    safe_booking_id = _e(booking_id)

    subject = f"New Booking: {guest_name} — {_format_dt(slot_datetime)}"
    html_body = f"""
    <div style="font-family: Georgia, serif; max-width: 560px; margin: 0 auto; color: #2C2C2C;">
      <div style="background: #A5A58D; padding: 20px 32px; border-radius: 8px 8px 0 0;">
        <h1 style="color: white; font-weight: normal; font-size: 20px; margin: 0;">
          New Session Booked
        </h1>
      </div>
      <div style="background: #faf7f2; padding: 28px 32px; border: 1px solid #ddd8ce;
                  border-top: none; border-radius: 0 0 8px 8px;">
        <table style="width: 100%; border-collapse: collapse; font-size: 14px;">
          <tr style="border-bottom: 1px solid #ddd8ce;">
            <td style="padding: 10px 0; color: #888; width: 120px;">Date &amp; Time</td>
            <td style="padding: 10px 0;"><strong>{formatted_dt}</strong></td>
          </tr>
          <tr style="border-bottom: 1px solid #ddd8ce;">
            <td style="padding: 10px 0; color: #888;">Name</td>
            <td style="padding: 10px 0;">{safe_name}</td>
          </tr>
          <tr style="border-bottom: 1px solid #ddd8ce;">
            <td style="padding: 10px 0; color: #888;">Email</td>
            <td style="padding: 10px 0;"><a href="mailto:{safe_email}" style="color: #846754;">{safe_email}</a></td>
          </tr>
          <tr style="border-bottom: 1px solid #ddd8ce;">
            <td style="padding: 10px 0; color: #888;">Phone</td>
            <td style="padding: 10px 0;">{safe_phone}</td>
          </tr>
          <tr style="border-bottom: 1px solid #ddd8ce;">
            <td style="padding: 10px 0; color: #888; vertical-align: top;">Goal</td>
            <td style="padding: 10px 0;">{safe_goal}</td>
          </tr>
          <tr style="border-bottom: 1px solid #ddd8ce;">
            <td style="padding: 10px 0; color: #888; vertical-align: top;">Challenge</td>
            <td style="padding: 10px 0;">{safe_challenge}</td>
          </tr>
          <tr>
            <td style="padding: 10px 0; color: #888;">Booking ID</td>
            <td style="padding: 10px 0; font-size: 12px; color: #aaa;">{safe_booking_id}</td>
          </tr>
        </table>
      </div>
    </div>
    """
    _send(host_email, subject, html_body)
