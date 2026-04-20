import logging
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import stripe
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.staticfiles import StaticFiles
from google.cloud import firestore
from pydantic import BaseModel, EmailStr, Field

from email_service import (
    send_booking_confirmation,
    send_host_lead_notification,
    send_host_notification,
)

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("booking")

# ── Config ───────────────────────────────────────────────────────────────────

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
APP_URL = os.getenv("APP_URL", "http://localhost:5173")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
if not ADMIN_USERNAME or not ADMIN_PASSWORD:
    raise RuntimeError(
        "ADMIN_USERNAME and ADMIN_PASSWORD must be set in the environment."
    )

ET = ZoneInfo("America/New_York")

security = HTTPBasic()


def require_admin(credentials: HTTPBasicCredentials = Depends(security)):
    ok = (
        secrets.compare_digest(credentials.username, ADMIN_USERNAME)
        and secrets.compare_digest(credentials.password, ADMIN_PASSWORD)
    )
    if not ok:
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )


app = FastAPI(title="Mahitha Vaka Booking API")

# Frontend is served from the same origin in production, so CORS is only
# needed for local dev against Vite. Pin to APP_URL rather than "*".
app.add_middleware(
    CORSMiddleware,
    allow_origins=[APP_URL],
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

db = firestore.Client(project=os.getenv("GCP_PROJECT", "mahitha-booking"))


# ── Models ───────────────────────────────────────────────────────────────────


class CheckoutRequest(BaseModel):
    slot_id: str
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr
    phone: str = Field(default="", max_length=40)
    emotional_state: str = Field(min_length=1, max_length=2000)
    life_impact: str = Field(min_length=1, max_length=2000)
    goals: list[str] = Field(min_length=1, max_length=20)
    commitment: int = Field(ge=1, le=10)


class SlotRequest(BaseModel):
    date: str  # YYYY-MM-DD
    hour: int = Field(ge=0, le=23)


# ── Helpers ──────────────────────────────────────────────────────────────────


def _format_goal(req: CheckoutRequest) -> str:
    return ", ".join(req.goals)


def _format_challenge(req: CheckoutRequest) -> str:
    return (
        f"Emotional state: {req.emotional_state}\n\n"
        f"Life impact: {req.life_impact}\n\n"
        f"Commitment: {req.commitment}/10"
    )


def _pending_payload(req: CheckoutRequest, slot_datetime: str) -> dict:
    """Shape the Firestore document for a pending booking."""
    return {
        "slot_id": req.slot_id,
        "slot_datetime": slot_datetime,
        "name": req.name,
        "email": req.email,
        "phone": req.phone,
        "emotional_state": req.emotional_state,
        "life_impact": req.life_impact,
        "goals": req.goals,
        "commitment": req.commitment,
        # Legacy / convenience fields kept so host email and admin UI keep working.
        "goal": _format_goal(req),
        "challenge": _format_challenge(req),
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }


# ── Public routes ────────────────────────────────────────────────────────────


@app.get("/sessions")
def get_sessions():
    docs = db.collection("sessions").stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


@app.get("/availability")
def get_availability(date: Optional[str] = None):
    ref = db.collection("availability").where("booked", "==", False)
    if date:
        ref = ref.where("date", "==", date)
    docs = ref.order_by("datetime").stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


@app.post("/create-checkout-session")
def create_checkout_session(req: CheckoutRequest):
    """Reserve the slot inside a transaction, then create a Stripe Checkout session."""
    slot_ref = db.collection("availability").document(req.slot_id)

    # Atomically verify the slot is free and mark it as held.
    transaction = db.transaction()

    @firestore.transactional
    def _reserve(tx) -> str:
        snap = slot_ref.get(transaction=tx)
        if not snap.exists:
            raise HTTPException(status_code=404, detail="Slot not found")
        data = snap.to_dict() or {}
        if data.get("booked") or data.get("held"):
            raise HTTPException(status_code=409, detail="Slot already booked")
        tx.update(slot_ref, {"held": True, "held_at": datetime.now(timezone.utc).isoformat()})
        return data.get("datetime")

    slot_datetime = _reserve(transaction)

    pending_ref = db.collection("pending_bookings").add(_pending_payload(req, slot_datetime))
    pending_id = pending_ref[1].id

    # Notify host of the lead immediately so they see it even if payment is abandoned.
    send_host_lead_notification(
        req.name,
        req.email,
        req.phone,
        _format_goal(req),
        _format_challenge(req),
        slot_datetime,
        pending_id,
    )

    try:
        checkout = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": "Clarity Coaching Session — Mahitha Vaka",
                            "description": "60-minute 1-on-1 coaching session via Zoom",
                        },
                        "unit_amount": 8000,  # $80.00
                    },
                    "quantity": 1,
                }
            ],
            mode="payment",
            customer_email=req.email,
            metadata={"pending_id": pending_id},
            success_url=f"{APP_URL}/confirm?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{APP_URL}/book/{req.slot_id}?cancelled=true",
        )
    except Exception:
        # Release the hold if Stripe fails so the slot doesn't get stuck.
        log.exception("Stripe checkout creation failed, releasing slot hold")
        slot_ref.update({"held": False, "held_at": firestore.DELETE_FIELD})
        db.collection("pending_bookings").document(pending_id).delete()
        raise HTTPException(status_code=502, detail="Payment provider unavailable")

    return {"checkout_url": checkout.url}


@app.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe payment confirmation. Must be idempotent — Stripe retries on any non-2xx."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception:
        log.warning("Invalid Stripe webhook signature")
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] != "checkout.session.completed":
        return {"status": "ignored"}

    session = event["data"]["object"]
    stripe_session_id = session["id"]
    # Stripe SDK v15 dropped dict.get() on StripeObject — use attribute access.
    metadata = getattr(session, "metadata", None)
    pending_id = getattr(metadata, "pending_id", None) if metadata else None
    if not pending_id:
        return {"status": "ignored"}

    # Idempotency check #1: have we already confirmed a booking for this Stripe session?
    existing = list(
        db.collection("bookings")
        .where("stripe_session_id", "==", stripe_session_id)
        .limit(1)
        .stream()
    )
    if existing:
        log.info("Webhook replay for session %s — already confirmed", stripe_session_id)
        return {"status": "already_confirmed"}

    pending_ref = db.collection("pending_bookings").document(pending_id)
    pending = pending_ref.get()
    if not pending.exists:
        log.warning("Webhook: pending booking %s not found", pending_id)
        return {"status": "not_found"}

    data = pending.to_dict() or {}

    # Idempotency check #2: pending was already flipped to confirmed on a prior retry.
    if data.get("status") == "confirmed":
        return {"status": "already_confirmed"}

    # Mark slot as booked (and clear the "held" flag set at checkout time).
    db.collection("availability").document(data["slot_id"]).update(
        {"booked": True, "held": False}
    )

    booking_ref = db.collection("bookings").add(
        {
            **data,
            "stripe_session_id": stripe_session_id,
            "status": "confirmed",
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    booking_id = booking_ref[1].id

    pending_ref.update({"status": "confirmed", "booking_id": booking_id})

    send_booking_confirmation(data["name"], data["email"], data["slot_datetime"], booking_id)
    send_host_notification(
        data["name"],
        data["email"],
        data.get("phone", ""),
        data.get("goal", ""),
        data.get("challenge", ""),
        data["slot_datetime"],
        booking_id,
    )

    return {"status": "ok"}


@app.get("/booking-by-session/{stripe_session_id}")
def get_booking_by_stripe_session(stripe_session_id: str):
    """Look up confirmed booking by Stripe session ID (used on confirm page)."""
    docs = (
        db.collection("bookings")
        .where("stripe_session_id", "==", stripe_session_id)
        .limit(1)
        .stream()
    )
    results = [{"id": doc.id, **doc.to_dict()} for doc in docs]
    if not results:
        raise HTTPException(status_code=404, detail="Booking not found")
    return results[0]


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Admin routes (password protected) ────────────────────────────────────────


@app.get("/admin/bookings")
def admin_get_bookings(_=Depends(require_admin)):
    """List all confirmed bookings."""
    docs = db.collection("bookings").order_by("slot_datetime").stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


@app.get("/admin/slots")
def admin_get_slots(_=Depends(require_admin)):
    """List all availability slots (booked and unbooked)."""
    docs = db.collection("availability").order_by("datetime").stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


@app.post("/admin/slots")
def admin_add_slot(req: SlotRequest, _=Depends(require_admin)):
    """Add a single availability slot."""
    try:
        y, m, d = (int(x) for x in req.date.split("-"))
        dt_local = datetime(y, m, d, req.hour, 0, 0, tzinfo=ET)
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid date")
    dt_utc = dt_local.astimezone(timezone.utc)
    ref = db.collection("availability").add(
        {
            "date": req.date,
            "datetime": dt_utc.isoformat(),
            "timezone": "America/New_York",
            "booked": False,
        }
    )
    return {"id": ref[1].id, "date": req.date, "hour": req.hour}


@app.delete("/admin/slots/{slot_id}")
def admin_delete_slot(slot_id: str, _=Depends(require_admin)):
    """Remove an availability slot (only if not booked). Transactional to close the read-then-delete race."""
    ref = db.collection("availability").document(slot_id)

    transaction = db.transaction()

    @firestore.transactional
    def _delete(tx):
        snap = ref.get(transaction=tx)
        if not snap.exists:
            raise HTTPException(status_code=404, detail="Slot not found")
        data = snap.to_dict() or {}
        if data.get("booked"):
            raise HTTPException(status_code=400, detail="Cannot delete a booked slot")
        tx.delete(ref)

    _delete(transaction)
    return {"status": "deleted"}


@app.delete("/admin/bookings/{booking_id}")
def admin_cancel_booking(booking_id: str, _=Depends(require_admin)):
    """Cancel a booking and free up the slot."""
    booking_ref = db.collection("bookings").document(booking_id)
    booking = booking_ref.get()
    if not booking.exists:
        raise HTTPException(status_code=404, detail="Booking not found")
    data = booking.to_dict() or {}
    db.collection("availability").document(data["slot_id"]).update(
        {"booked": False, "held": False}
    )
    booking_ref.update({"status": "cancelled"})
    return {"status": "cancelled"}


# ── Serve React frontend ──────────────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")
    if (STATIC_DIR / "imgs").exists():
        app.mount("/imgs", StaticFiles(directory=STATIC_DIR / "imgs"), name="imgs")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        return FileResponse(STATIC_DIR / "index.html")
