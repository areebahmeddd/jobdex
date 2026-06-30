import hashlib
import hmac
import uuid

import razorpay
from fastapi import APIRouter, HTTPException
from loguru import logger

from app.config import settings
from app.schemas import OrderRequest, OrderResponse, VerifyRequest, VerifyResponse

router = APIRouter(prefix="/payments", tags=["payments"])


def _razorpay_client() -> razorpay.Client:
    return razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_KEY_SECRET))


@router.post("/orders", response_model=OrderResponse)
def create_order(body: OrderRequest):
    """Create a Razorpay order for the given INR amount and return the order ID."""
    if body.amount < 1 or body.amount > 10_000:
        raise HTTPException(status_code=400, detail="Amount must be between ₹1 and ₹10,000.")

    if not settings.RAZORPAY_KEY_ID or not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Payment gateway not configured.")

    try:
        order = _razorpay_client().order.create(
            {
                "amount": body.amount * 100,
                "currency": "INR",
                "receipt": f"donation_{uuid.uuid4().hex[:12]}",
                "payment_capture": 1,
                "notes": {"source": "jobdex_donation"},
            }
        )
    except Exception as exc:
        logger.error(f"[payments] order creation failed: {exc}")
        raise HTTPException(status_code=502, detail="Payment service unavailable.") from exc

    return OrderResponse(
        order_id=order["id"],
        amount=order["amount"],
        currency=order["currency"],
        key_id=settings.RAZORPAY_KEY_ID,
    )


@router.post("/verify", response_model=VerifyResponse)
def verify_payment(body: VerifyRequest):
    """Verify a Razorpay payment signature and confirm the transaction is authentic."""
    if not settings.RAZORPAY_KEY_SECRET:
        raise HTTPException(status_code=503, detail="Payment gateway not configured.")

    payload = f"{body.razorpay_order_id}|{body.razorpay_payment_id}"
    expected = hmac.new(
        settings.RAZORPAY_KEY_SECRET.encode(),
        payload.encode(),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, body.razorpay_signature):
        raise HTTPException(status_code=400, detail="Payment signature verification failed.")

    return VerifyResponse(status="verified", payment_id=body.razorpay_payment_id)
