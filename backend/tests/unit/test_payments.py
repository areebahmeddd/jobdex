import hashlib
import hmac
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestVerifyPayment:
    def _signature(self, order_id, payment_id, secret):
        return hmac.new(
            secret.encode(), f"{order_id}|{payment_id}".encode(), hashlib.sha256
        ).hexdigest()

    @patch("app.routers.payments.settings")
    def test_valid_signature(self, mock_settings):
        mock_settings.RAZORPAY_KEY_SECRET = "test_secret"
        order_id, payment_id = "order_abc123", "pay_xyz789"
        sig = self._signature(order_id, payment_id, "test_secret")

        r = client.post(
            "/payments/verify",
            json={
                "razorpay_order_id": order_id,
                "razorpay_payment_id": payment_id,
                "razorpay_signature": sig,
            },
        )
        assert r.status_code == 200
        assert r.json()["status"] == "verified"
        assert r.json()["payment_id"] == payment_id

    @patch("app.routers.payments.settings")
    def test_invalid_signature(self, mock_settings):
        mock_settings.RAZORPAY_KEY_SECRET = "test_secret"

        r = client.post(
            "/payments/verify",
            json={
                "razorpay_order_id": "order_abc123",
                "razorpay_payment_id": "pay_xyz789",
                "razorpay_signature": "tampered",
            },
        )
        assert r.status_code == 400

    @patch("app.routers.payments.settings")
    def test_missing_secret(self, mock_settings):
        mock_settings.RAZORPAY_KEY_SECRET = ""

        r = client.post(
            "/payments/verify",
            json={
                "razorpay_order_id": "order_abc123",
                "razorpay_payment_id": "pay_xyz789",
                "razorpay_signature": "any",
            },
        )
        assert r.status_code == 503


class TestCreateOrder:
    @pytest.mark.parametrize("amount", [0, -1, 10_001, 99_999])
    @patch("app.routers.payments.settings")
    def test_invalid_amounts(self, mock_settings, amount):
        mock_settings.RAZORPAY_KEY_ID = "rzp_test_key"
        mock_settings.RAZORPAY_KEY_SECRET = "test_secret"

        r = client.post("/payments/orders", json={"amount": amount})
        assert r.status_code == 400

    @pytest.mark.parametrize("amount", [1, 10, 500, 10_000])
    @patch("app.routers.payments._razorpay_client")
    @patch("app.routers.payments.settings")
    def test_valid_amounts(self, mock_settings, mock_client, amount):
        mock_settings.RAZORPAY_KEY_ID = "rzp_test_key"
        mock_settings.RAZORPAY_KEY_SECRET = "test_secret"
        mock_client.return_value.order.create.return_value = {
            "id": "order_test123",
            "amount": amount * 100,
            "currency": "INR",
        }

        r = client.post("/payments/orders", json={"amount": amount})
        assert r.status_code == 200
        assert r.json()["order_id"] == "order_test123"
        assert r.json()["key_id"] == "rzp_test_key"

    @patch("app.routers.payments.settings")
    def test_unconfigured_keys(self, mock_settings):
        mock_settings.RAZORPAY_KEY_ID = ""
        mock_settings.RAZORPAY_KEY_SECRET = ""

        r = client.post("/payments/orders", json={"amount": 100})
        assert r.status_code == 503
