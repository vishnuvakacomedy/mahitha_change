"""
Email notifications via SendGrid.
Set SENDGRID_API_KEY and SENDER_EMAIL in your .env file.
"""
import os
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "noreply@mahithavaka.com")
SENDER_NAME = "Mahitha Vaka"


def _send(to_email: str, subject: str, html_body: str):
    """Send an email via SendGrid. Silently logs on failure."""
    if not SENDGRID_API_KEY:
        print(f"[email] SENDGRID_API_KEY not set — skipping email to {to_email}")
        return
    try:
        message = Mail(
            from_email=(SENDER_EMAIL, SENDER_NAME),
            to_emails=to_email,
            subject=subject,
            html_content=html_body,
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        sg.send(message)
        print(f"[email] Sent '{subject}' to {to_email}")
    except Exception as e:
        print(f"[email] Failed to send to {to_email}: {e}")


def _format_dt(iso_str: str) -> str:
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        return dt.strftime("%A, %B %-d, %Y at %-I:%M %p UTC")
    except Exception:
        return iso_str


def send_booking_confirmation(name: str, email: str, slot_datetime: str, booking_id: str):
    """Send confirmation email to the person who booked."""
    formatted_dt = _format_dt(slot_datetime)
    subject = "Your Coaching Session is Confirmed — Mahitha Vaka"
    html = f"""
    <div style="font-family: Georgia, serif; max-width: 560px; margin: 0 auto; color: #2C2C2C;">
      <div style="background: #846754; padding: 24px 32px; border-radius: 8px 8px 0 0;">
        <h1 style="color: white; font-weight: normal; font-size: 22px; margin: 0;">
          You're Booked!
        </h1>
      </div>
      <div style="background: #faf7f2; padding: 32px; border: 1px solid #ddd8ce; border-top: none; border-radius: 0 0 8px 8px;">
        <p style="margin-bottom: 16px;">Hi {name},</p>
        <p style="margin-bottom: 24px;">
          Your complimentary coaching session with <strong>Mahitha Vaka</strong> is confirmed.
          I look forward to connecting with you!
        </p>

        <div style="background: #F1EDE4; border-left: 3px solid #846754; padding: 16px 20px;
                    border-radius: 0 6px 6px 0; margin-bottom: 24px;">
          <p style="margin: 0 0 8px; font-size: 13px; color: #888;">SESSION DETAILS</p>
          <p style="margin: 0 0 6px;"><strong>Date &amp; Time:</strong> {formatted_dt}</p>
          <p style="margin: 0 0 6px;"><strong>Duration:</strong> 60 minutes</p>
          <p style="margin: 0 0 6px;"><strong>Format:</strong> Zoom (link will be sent separately)</p>
          <p style="margin: 0;"><strong>Cost:</strong> Complimentary</p>
        </div>

        <p style="margin-bottom: 8px; font-size: 13px; color: #888;">
          Booking reference: <code style="background: #e8e4dc; padding: 2px 6px; border-radius: 4px;">{booking_id}</code>
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
    _send(email, subject, html)


def send_host_notification(guest_name: str, guest_email: str, guest_phone: str,
                           goal: str, challenge: str,
                           slot_datetime: str, booking_id: str):
    """Notify Mahitha when someone books a session."""
    host_email = os.getenv("HOST_EMAIL", SENDER_EMAIL)
    formatted_dt = _format_dt(slot_datetime)
    subject = f"New Booking: {guest_name} — {formatted_dt}"
    html = f"""
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
            <td style="padding: 10px 0;">{guest_name}</td>
          </tr>
          <tr style="border-bottom: 1px solid #ddd8ce;">
            <td style="padding: 10px 0; color: #888;">Email</td>
            <td style="padding: 10px 0;"><a href="mailto:{guest_email}" style="color: #846754;">{guest_email}</a></td>
          </tr>
          <tr style="border-bottom: 1px solid #ddd8ce;">
            <td style="padding: 10px 0; color: #888;">Phone</td>
            <td style="padding: 10px 0;">{guest_phone or '—'}</td>
          </tr>
          <tr style="border-bottom: 1px solid #ddd8ce;">
            <td style="padding: 10px 0; color: #888; vertical-align: top;">Goal</td>
            <td style="padding: 10px 0;">{goal}</td>
          </tr>
          <tr style="border-bottom: 1px solid #ddd8ce;">
            <td style="padding: 10px 0; color: #888; vertical-align: top;">Challenge</td>
            <td style="padding: 10px 0;">{challenge}</td>
          </tr>
          <tr>
            <td style="padding: 10px 0; color: #888;">Booking ID</td>
            <td style="padding: 10px 0; font-size: 12px; color: #aaa;">{booking_id}</td>
          </tr>
        </table>
      </div>
    </div>
    """
    _send(host_email, subject, html)
