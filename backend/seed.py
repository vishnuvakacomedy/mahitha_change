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
TIMEZONE = pytz.timezone("America/New_York")
WEEKDAY_HOURS = [17, 18, 19, 20]      # Mon–Fri: 5pm–9pm (last slot starts 8pm)
WEEKEND_HOURS = [9, 10, 11, 12, 13, 14, 15, 16]  # Sat–Sun: 9am–5pm
DAYS_AHEAD = 30
WEEKDAYS = {0, 1, 2, 3, 4}   # Mon–Fri
WEEKENDS = {5, 6}             # Sat–Sun

print("Seeding availability slots...")
count = 0
today = datetime.now(TIMEZONE).date()

for day_offset in range(1, DAYS_AHEAD + 1):
    day = today + timedelta(days=day_offset)
    weekday = day.weekday()
    if weekday in WEEKDAYS:
        hours = WEEKDAY_HOURS
    elif weekday in WEEKENDS:
        hours = WEEKEND_HOURS
    else:
        continue
    for hour in hours:
        dt_local = TIMEZONE.localize(datetime(day.year, day.month, day.day, hour, 0, 0))
        dt_utc = dt_local.astimezone(timezone.utc)
        db.collection("availability").add({
            "date": day.isoformat(),
            "datetime": dt_utc.isoformat(),
            "timezone": "America/New_York",
            "booked": False,
        })
        count += 1

print(f"  Added {count} slot(s)")
print("Done!")
