from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr
from google.cloud import firestore
from datetime import datetime, timezone
import os
import stripe
from pathlib import Path
from dotenv import load_dotenv
from email_service import send_booking_confirmation, send_host_notification

load_dotenv()

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
APP_URL = os.getenv("APP_URL", "http://localhost:5173")

app = FastAPI(title="Mahitha Vaka Booking API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db = firestore.Client()


# ── Models ───────────────────────────────────────────────────────────────────

class CheckoutRequest(BaseModel):
    slot_id: str
    name: str
    email: EmailStr
    phone: str
    goal: str
    challenge: str


# ── Routes ───────────────────────────────────────────────────────────────────

@app.get("/sessions")
def get_sessions():
    docs = db.collection("sessions").stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


@app.get("/availability")
def get_availability(date: str = None):
    ref = db.collection("availability").where("booked", "==", False)
    if date:
        ref = ref.where("date", "==", date)
    docs = ref.order_by("datetime").stream()
    return [{"id": doc.id, **doc.to_dict()} for doc in docs]


@app.post("/bookings")
def create_booking(req: CheckoutRequest):
    """Direct booking without payment (pre-Stripe)."""
    slot_ref = db.collection("availability").document(req.slot_id)
    slot = slot_ref.get()

    if not slot.exists:
        raise HTTPException(status_code=404, detail="Slot not found")
    slot_data = slot.to_dict()
    if slot_data.get("booked"):
        raise HTTPException(status_code=409, detail="Slot already booked")

    slot_ref.update({"booked": True})

    booking_ref = db.collection("bookings").add({
        "slot_id": req.slot_id,
        "slot_datetime": slot_data.get("datetime"),
        "name": req.name,
        "email": req.email,
        "phone": req.phone,
        "goal": req.goal,
        "challenge": req.challenge,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "confirmed",
    })
    booking_id = booking_ref[1].id
    slot_datetime = slot_data.get("datetime")

    send_booking_confirmation(req.name, req.email, slot_datetime, booking_id)
    send_host_notification(req.name, req.email, req.phone,
                           req.goal, req.challenge, slot_datetime, booking_id)

    return {"booking_id": booking_id, "slot_datetime": slot_datetime}


@app.post("/create-checkout-session")
def create_checkout_session(req: CheckoutRequest):
    """Create a Stripe Checkout session and return the URL."""
    slot_ref = db.collection("availability").document(req.slot_id)
    slot = slot_ref.get()

    if not slot.exists:
        raise HTTPException(status_code=404, detail="Slot not found")
    if slot.to_dict().get("booked"):
        raise HTTPException(status_code=409, detail="Slot already booked")

    # Store pending booking in Firestore (confirmed after payment)
    pending_ref = db.collection("pending_bookings").add({
        "slot_id": req.slot_id,
        "slot_datetime": slot.to_dict().get("datetime"),
        "name": req.name,
        "email": req.email,
        "phone": req.phone,
        "goal": req.goal,
        "challenge": req.challenge,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    })
    pending_id = pending_ref[1].id

    # Create Stripe Checkout session
    checkout = stripe.checkout.Session.create(
        payment_method_types=["card"],
        line_items=[{
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": "Clarity Coaching Session — Mahitha Vaka",
                    "description": "60-minute 1-on-1 coaching session via Zoom",
                },
                "unit_amount": 8000,  # $80.00 in cents
            },
            "quantity": 1,
        }],
        mode="payment",
        customer_email=req.email,
        metadata={"pending_id": pending_id},
        success_url=f"{APP_URL}/confirm?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{APP_URL}/book/{req.slot_id}?cancelled=true",
    )

    return {"checkout_url": checkout.url}


@app.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe payment confirmation."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, STRIPE_WEBHOOK_SECRET)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid webhook signature")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        pending_id = session["metadata"].get("pending_id")

        if not pending_id:
            return {"status": "ignored"}

        pending_ref = db.collection("pending_bookings").document(pending_id)
        pending = pending_ref.get()

        if not pending.exists:
            return {"status": "not found"}

        data = pending.to_dict()

        # Mark slot as booked
        db.collection("availability").document(data["slot_id"]).update({"booked": True})

        # Create confirmed booking
        booking_ref = db.collection("bookings").add({
            **data,
            "stripe_session_id": session["id"],
            "status": "confirmed",
            "confirmed_at": datetime.now(timezone.utc).isoformat(),
        })
        booking_id = booking_ref[1].id

        # Update pending record
        pending_ref.update({"status": "confirmed", "booking_id": booking_id})

        # Send emails
        send_booking_confirmation(data["name"], data["email"], data["slot_datetime"], booking_id)
        send_host_notification(data["name"], data["email"], data["phone"],
                               data["goal"], data["challenge"], data["slot_datetime"], booking_id)

    return {"status": "ok"}


@app.get("/booking-by-session/{stripe_session_id}")
def get_booking_by_stripe_session(stripe_session_id: str):
    """Look up confirmed booking by Stripe session ID (used on confirm page)."""
    docs = db.collection("bookings").where("stripe_session_id", "==", stripe_session_id).stream()
    results = [{"id": doc.id, **doc.to_dict()} for doc in docs]
    if not results:
        raise HTTPException(status_code=404, detail="Booking not found")
    return results[0]


@app.get("/health")
def health():
    return {"status": "ok"}


# ── Serve React frontend ──────────────────────────────────────────────────────
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}")
    def serve_frontend(full_path: str):
        return FileResponse(STATIC_DIR / "index.html")
