"""
Contrato de pasarelas de pago (test sin red real).

Corre con la stdlib:  python -m unittest discover -s tests -v
Mockea requests.post/get y usa FakeSession (objetos SimpleNamespace), así que
NO toca PayU/Wompi/MercadoPago ni la base de datos. Valida el CONTRATO que
debe cumplir cualquier PaymentProvider: métodos expuestos, resultado
normalizado (redirect_url/qr), abono de saldo e IDEMPOTENCIA (no doble abono).

Dependencias solo stdlib + fastapi + requests (ya en requirements.txt).
"""
import os
import unittest
from unittest.mock import patch
from types import SimpleNamespace as NS

# Settings se instancia al importar app.*; sin .env fallaría. Proveemos valores
# de prueba ANTES de importar app.
os.environ.setdefault("DATABASE_URL", "mysql+pymysql://test:test@localhost/test_db")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("PAYU_MERCHANT_ID", "merchant123")
os.environ.setdefault("PAYU_API_KEY", "apikey123")
os.environ.setdefault("PAYU_API_LOGIN", "login123")
os.environ.setdefault("PAYU_ACCOUNT_ID", "acct123")
os.environ.setdefault("PAYU_URL", "https://sandbox.api.payulatam.com/payments-api/4.0/service.cgi")
os.environ.setdefault("PAYU_IS_TEST", "True")

from app.payment_providers.registry import get_active_provider, get_provider
from app.payment_providers.base import PaymentStatus
from app.core.config import settings
# Registrar TODOS los modelos (necesario para resolver relationships de Card)
from app.db import base as _db_base  # noqa: F401


def make_tx(reference="REF-TEST-1", status="pending", amount=50000.0, card=None):
    return NS(reference_code=reference, status=status, amount=amount, card=card,
              cus=None, description=None)


def make_card(uid="CARDTEST1", balance=10000.0):
    return NS(uid=uid, balance=balance)


class FakeSession:
    """Mínimo suficiente para los providers (query/filter/first/add/commit)."""
    def __init__(self, rows):
        self.rows = list(rows)
    def query(self, *_):
        return QueryStub(self.rows)
    def add(self, *_):
        pass
    def commit(self):
        pass
    def rollback(self):
        pass


class QueryStub:
    def __init__(self, rows):
        self.rows = list(rows)
    def filter(self, *_):
        return self
    def first(self):
        return self.rows[0] if self.rows else None


class RegistryContractTest(unittest.TestCase):
    def test_naming_required_fields(self):
        for name in ("payu", "wompi", "mercadopago"):
            p = get_provider(name)
            self.assertIsNotNone(p, f"provider '{name}' no registrado")
            self.assertTrue(p.name)
            self.assertTrue(callable(p.get_methods))
            self.assertTrue(callable(p.init_recharge))
            self.assertTrue(callable(p.handle_notification))

    def test_active_falls_back_to_payu_when_none(self):
        p = get_active_provider(FakeSession([]))
        self.assertEqual(p.name, "payu")

    def test_active_returns_registered(self):
        p = get_active_provider(FakeSession([NS(gateway="wompi")]))
        self.assertEqual(p.name, "wompi")


class PayUProviderTest(unittest.TestCase):
    def setUp(self):
        self.provider = get_provider("payu")
        self.assertIsNotNone(self.provider)

    def test_methods_include_pse(self):
        ids = [m.id for m in self.provider.get_methods()]
        self.assertIn("pse", ids)

    def test_init_creates_transaction_pending(self):
        payload = {"card_uid": "X", "amount": 50000, "buyer_name": "A",
                   "buyer_email": "a@b.c", "buyer_dni": "1", "bank_code": "1009",
                   "client_ip": "127.0.0.1", "user_agent": "test"}
        fake_resp = NS(
            status_code=200,
            json=lambda: {
                "transactionResponse": {
                    "state": "PENDING",
                    "responseCode": "APPROVED",
                    "trazabilityCode": "TRAZ1",
                    "extraParameters": {"BANK_URL": "https://bank.example/redirect"},
                }
            },
        )
        with patch("requests.post", return_value=fake_resp):
            res = self.provider.init_recharge(FakeSession([]), payload,
                                              {"base_url": "http://test", "return_url": "http://test/x"})
        self.assertTrue(res.reference)
        self.assertEqual(res.status, PaymentStatus.PENDING)
        self.assertEqual(res.redirect_url, "https://bank.example/redirect")

    def test_notification_approved_credits_balance(self):
        card = make_card()
        tx = make_tx(card=card)
        db = FakeSession([tx])
        form = {"reference_sale": "REF-TEST-1", "state_pol": "4", "value": "50000",
                "cus": "CUS-1"}
        self.provider.handle_notification(db, form)
        self.assertEqual(tx.status, "approved")
        self.assertEqual(card.balance, 60000.0)

    def test_notification_idempotent_no_double_credit(self):
        card = make_card()
        tx = make_tx(card=card, status="approved")
        db = FakeSession([tx])
        form = {"reference_sale": "REF-TEST-1", "state_pol": "4", "value": "50000"}
        self.provider.handle_notification(db, form)
        self.assertEqual(card.balance, 10000.0, "¡Doble abono!")


class WompiProviderTest(unittest.TestCase):
    def setUp(self):
        self.provider = get_provider("wompi")
        self.assertIsNotNone(self.provider)
        # Credenciales de prueba para pasar el guard.
        settings.WOMPI_PUBLIC_KEY = "pub_test"
        settings.WOMPI_PRIVATE_KEY = "priv_test"

    def test_methods_include_nequi_and_qr(self):
        ids = [m.id for m in self.provider.get_methods()]
        self.assertIn("nequi", ids)
        self.assertIn("qr", ids)

    def test_init_without_credentials_raises(self):
        from fastapi import HTTPException
        with patch.object(settings, "WOMPI_PRIVATE_KEY", ""):
            with self.assertRaises(HTTPException):
                self.provider.init_recharge(FakeSession([]),
                                            {"amount": 50000, "method": "nequi", "card_id": 1}, {})

    def test_init_returns_checkout_url(self):
        merchant_json = NS(json=lambda: {"data": {"presigned_acceptance":
                                                  {"acceptance_token": "acc_tok"}}})
        with patch("requests.get", return_value=merchant_json):
            res = self.provider.init_recharge(
                FakeSession([]), {"amount": 50000, "method": "nequi", "card_id": 1},
                {"base_url": "http://test", "return_url": "http://test/x"})
        self.assertTrue(res.redirect_url.startswith("https://checkout.wompi.co/"))
        self.assertTrue(res.reference.startswith("WOMPI-"))

    def test_notification_approved_credits(self):
        card = make_card()
        tx = make_tx(reference="WOMPI", card=card)
        db = FakeSession([tx])
        self.provider.handle_notification(
            db, {"data": {"transaction": {"status": "APPROVED", "reference": "WOMPI"}}})
        self.assertEqual(tx.status, "approved")
        self.assertEqual(card.balance, 60000.0)

    def test_notification_idempotent(self):
        card = make_card()
        tx = make_tx(reference="WOMPI", card=card, status="approved")
        db = FakeSession([tx])
        self.provider.handle_notification(
            db, {"data": {"transaction": {"status": "APPROVED", "reference": "WOMPI"}}})
        self.assertEqual(card.balance, 10000.0)


class MercadoPagoProviderTest(unittest.TestCase):
    def setUp(self):
        self.provider = get_provider("mercadopago")
        self.assertIsNotNone(self.provider)
        settings.MP_ACCESS_TOKEN = "TEST-123"

    def test_methods_include_pse_and_nequi(self):
        ids = [m.id for m in self.provider.get_methods()]
        self.assertIn("pse", ids)
        self.assertIn("nequi", ids)

    def test_init_creates_preference_and_returns_init_point(self):
        created = {}

        def fake_post(url, json=None, headers=None, timeout=None):
            created["json"] = json
            return NS(status_code=201,
                      json=lambda: {"init_point": "https://mp.example/pay/ABC",
                                    "external_reference": json["external_reference"]})

        with patch("requests.post", side_effect=fake_post):
            res = self.provider.init_recharge(
                FakeSession([]), {"amount": 50000, "card_id": 1}, {"base_url": "http://test"})
        self.assertEqual(created["json"]["external_reference"], res.reference)
        self.assertTrue(res.reference.startswith("MP-"))
        self.assertEqual(res.redirect_url, "https://mp.example/pay/ABC")

    def test_notification_requeries_and_credits(self):
        card = make_card()
        tx = make_tx(reference="MP-1", card=card)
        db = FakeSession([tx])
        paid = NS(status_code=200, json=lambda: {"status": "approved",
                                                 "external_reference": "MP-1"})
        with patch("requests.get", return_value=paid):
            self.provider.handle_notification(db, {"data": {"id": "12345"}})
        self.assertEqual(tx.status, "approved")
        self.assertEqual(card.balance, 60000.0)

    def test_notification_idempotent(self):
        card = make_card()
        tx = make_tx(reference="MP-1", card=card, status="approved")
        db = FakeSession([tx])
        with patch("requests.get"):
            self.provider.handle_notification(db, {"data": {"id": "12345"}})
        self.assertEqual(card.balance, 10000.0)


if __name__ == "__main__":
    unittest.main()
