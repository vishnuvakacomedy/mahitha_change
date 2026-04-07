"""
Seed Firestore with session types and available time slots.
Run once: python seed.py

Generates slots Mon–Fri, 9am–5pm (on the hour) for the next 30 days.
"""
from google.cloud import firestore
from datetime import datetime, timedelta, timezone
import pytz

db = firestore.Client()

# ── Session types ────────────────────────────────────────────────────────────
sessions = [
    {
        "title": "Complimentary Coaching Session",
        "duration_minutes": 60,
        "price": 80,
        "currency": "USD",
        "description": (
            "A focused 60-minute 1-on-1 session with Mahitha Vaka. "
            "We'll slow down the mental noise, identify what's really blocking you, "
            "and create one clear, grounded next step forward."
        ),
        "meeting_type": "Zoom",
    }
]

print("Seeding sessions...")
for s in sessions:
    db.collection("sessions").add(s)
print(f"  Added {len(sessions)} session(s)")

# ── Availability slots ───────────────────────────────────────────────────────
TIMEZONE = pytz.timezone("America/Chicago")
SLOT_HOURS = [9, 10, 11, 13, 14, 15, 16]   # skip noon
DAYS_AHEAD = 30
WEEKDAYS = {0, 1, 2, 3, 4}  # Mon–Fri

print("Seeding availability slots...")
count = 0
today = datetime.now(TIMEZONE).date()

for day_offset in range(1, DAYS_AHEAD + 1):
    day = today + timedelta(days=day_offset)
    if day.weekday() not in WEEKDAYS:
        continue
    for hour in SLOT_HOURS:
        dt_local = TIMEZONE.localize(datetime(day.year, day.month, day.day, hour, 0, 0))
        dt_utc = dt_local.astimezone(timezone.utc)
        db.collection("availability").add({
            "date": day.isoformat(),          # "2025-04-01"
            "datetime": dt_utc.isoformat(),   # ISO UTC string
            "timezone": "America/Chicago",
            "booked": False,
        })
        count += 1

print(f"  Added {count} slot(s)")
print("Done!")
