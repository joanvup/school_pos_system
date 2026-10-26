"""Endurecimiento de PayU: firma, monto, moneda e idempotencia (WP2)."""
import hashlib
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.core.config import settings
from app.models.card import (
    PaymentNotification,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.services.payment_service import process_payu_notification
from app.utils.payu_service import PayUService

API = "/api/v1"


def confirmation_signature(reference, value, currency, state, merchant_id=None):
    merchant_id = merchant_id or settings.PAYU_MERCHANT_ID
    raw = (
        f"{settings.PAYU_API_KEY}~{merchant_id}~{reference}~"
        f"{value}~{currency}~{state}"
    )
    return hashlib.md5(raw.encode("utf-8")).hexdigest()


def notification_form(reference, value="50000.00", currency="COP", state="4", **overrides):
    form = {
        "reference_sale": reference,
        "merchant_id": settings.PAYU_MERCHANT_ID,
        "value": value,
        "currency": currency,
        "state_pol": state,
        "cus": "CUS-TEST-1",
        "response_code_pol": "1",
        "sign": confirmation_signature(reference, value, currency, state),
    }
    form.update(overrides)
    return form


def pending_recharge(db, card, reference="RECH-TEST-1", amount="50000.00", currency="COP"):
    tx = Transaction(
        card_id=card.id,
        amount=Decimal(amount),
        type=TransactionType.RECHARGE,
        description="Recarga de prueba",
        reference_code=reference,
        status=TransactionStatus.PENDING.value,
        gateway="payu",
        currency=currency,
        payment_method="pse",
    )
    db.add(tx)
    db.commit()
    db.refresh(tx)
    return tx


def test_signature_verification_accepts_valid_and_rejects_invalid():
    sign = confirmation_signature("RECH-1", "50000.00", "COP", "4")
    assert PayUService.verify_confirmation_signature(
        settings.PAYU_MERCHANT_ID, "RECH-1", "50000.00", "COP", "4", sign
    )
    assert not PayUService.verify_confirmation_signature(
        settings.PAYU_MERCHANT_ID, "RECH-1", "50000.00", "COP", "4", "deadbeef"
    )
    assert not PayUService.verify_confirmation_signature(
        settings.PAYU_MERCHANT_ID, "RECH-1", "50000.00", "COP", "4", None
    )


def test_generate_reference_is_unique_and_server_side():
    references = {PayUService.generate_reference() for _ in range(50)}
    assert len(references) == 50
    assert all(reference.startswith("RECH-") for reference in references)
    assert all(len(reference) == 37 for reference in references)


def test_valid_notification_credits_exact_amount_once(db, family_factory):
    _, _, card = family_factory(balance="10000.00")
    tx = pending_recharge(db, card, reference="RECH-VALID")

    result = process_payu_notification(db, notification_form("RECH-VALID"))

    db.refresh(card)
    db.refresh(tx)
    assert result["status"] == "approved"
    assert tx.status == TransactionStatus.APPROVED.value
    assert tx.credited_at is not None
    assert card.balance == Decimal("60000.00")

    notification = db.query(PaymentNotification).first()
    assert notification.signature_valid is True
    assert notification.reason == "abono aplicado"


def test_replayed_notification_does_not_credit_twice(db, family_factory):
    _, _, card = family_factory(balance="10000.00")
    tx = pending_recharge(db, card, reference="RECH-REPLAY")

    process_payu_notification(db, notification_form("RECH-REPLAY"))
    process_payu_notification(db, notification_form("RECH-REPLAY"))

    db.refresh(card)
    db.refresh(tx)
    assert card.balance == Decimal("60000.00")
    assert tx.status == TransactionStatus.APPROVED.value


def test_invalid_signature_never_credits(db, family_factory):
    _, _, card = family_factory(balance="10000.00")
    pending_recharge(db, card, reference="RECH-BADSIGN")

    form = notification_form("RECH-BADSIGN", sign="f" * 32)
    with pytest.raises(HTTPException) as error:
        process_payu_notification(db, form)
    assert error.value.status_code == 400

    db.refresh(card)
    notification = db.query(PaymentNotification).first()
    assert card.balance == Decimal("10000.00")
    assert notification.signature_valid is False
    assert notification.reason == "firma inválida"


def test_missing_signature_never_credits(db, family_factory):
    _, _, card = family_factory(balance="10000.00")
    pending_recharge(db, card, reference="RECH-NOSIGN")

    form = notification_form("RECH-NOSIGN")
    form.pop("sign")
    with pytest.raises(HTTPException) as error:
        process_payu_notification(db, form)
    assert error.value.status_code == 400

    db.refresh(card)
    assert card.balance == Decimal("10000.00")


def test_wrong_merchant_is_rejected(db, family_factory):
    _, _, card = family_factory(balance="10000.00")
    pending_recharge(db, card, reference="RECH-MERCHANT")

    form = notification_form("RECH-MERCHANT", merchant_id="otro-merchant")
    form["sign"] = confirmation_signature(
        "RECH-MERCHANT", "50000.00", "COP", "4", merchant_id="otro-merchant"
    )
    with pytest.raises(HTTPException) as error:
        process_payu_notification(db, form)
    assert error.value.status_code == 400

    db.refresh(card)
    assert card.balance == Decimal("10000.00")


def test_amount_mismatch_is_rejected(db, family_factory):
    _, _, card = family_factory(balance="10000.00")
    pending_recharge(db, card, reference="RECH-AMOUNT", amount="50000.00")

    form = notification_form("RECH-AMOUNT", value="99999.00")
    with pytest.raises(HTTPException) as error:
        process_payu_notification(db, form)
    assert error.value.status_code == 400

    db.refresh(card)
    assert card.balance == Decimal("10000.00")


def test_currency_mismatch_is_rejected(db, family_factory):
    _, _, card = family_factory(balance="10000.00")
    pending_recharge(db, card, reference="RECH-CURRENCY", currency="COP")

    form = notification_form("RECH-CURRENCY", currency="USD")
    with pytest.raises(HTTPException) as error:
        process_payu_notification(db, form)
    assert error.value.status_code == 400

    db.refresh(card)
    assert card.balance == Decimal("10000.00")


def test_unknown_reference_is_rejected(db):
    form = notification_form("RECH-UNKNOWN")
    with pytest.raises(HTTPException) as error:
        process_payu_notification(db, form)
    assert error.value.status_code == 404


def test_declined_notification_does_not_credit(db, family_factory):
    _, _, card = family_factory(balance="10000.00")
    tx = pending_recharge(db, card, reference="RECH-DECLINED")

    result = process_payu_notification(
        db, notification_form("RECH-DECLINED", state="6")
    )

    db.refresh(card)
    db.refresh(tx)
    assert result["status"] == "declined"
    assert tx.status == TransactionStatus.DECLINED.value
    assert card.balance == Decimal("10000.00")


def test_webhook_endpoint_rejects_unknown_reference(client):
    response = client.post(
        f"{API}/payments/notify/payu",
        data=notification_form("RECH-HTTP-UNKNOWN"),
    )
    assert response.status_code == 404


def test_webhook_endpoint_accepts_form_and_is_idempotent(client, db, family_factory):
    _, _, card = family_factory(balance="10000.00")
    pending_recharge(db, card, reference="RECH-HTTP-OK")

    first = client.post(
        f"{API}/payments/notify/payu", data=notification_form("RECH-HTTP-OK")
    )
    assert first.status_code == 200
    assert first.json()["status"] == "approved"

    second = client.post(
        f"{API}/payments/notify/payu", data=notification_form("RECH-HTTP-OK")
    )
    assert second.status_code == 200
    assert second.json()["status"] == "approved"

    db.refresh(card)
    assert card.balance == Decimal("60000.00")


def test_payment_status_is_owned(client, db, family_factory, user_factory, auth_headers):
    parent_a, _, _ = family_factory(balance="10000.00")
    parent_b, _, card_b = family_factory(balance="10000.00")
    pending_recharge(db, card_b, reference="RECH-OWNER")

    foreign = client.get(
        f"{API}/payments/status/RECH-OWNER", headers=auth_headers(parent_a)
    )
    assert foreign.status_code == 403

    owner = client.get(
        f"{API}/payments/status/RECH-OWNER", headers=auth_headers(parent_b)
    )
    assert owner.status_code == 200
    assert owner.json() == {
        "reference": "RECH-OWNER",
        "status": "pending",
        "amount": 50000.0,
        "gateway": "payu",
    }

    anonymous = client.get(f"{API}/payments/status/RECH-OWNER")
    assert anonymous.status_code == 401


def test_payment_init_rejects_foreign_card(client, family_factory, auth_headers):
    parent_a, _, _ = family_factory(balance="10000.00")
    _, _, card_b = family_factory(balance="10000.00")

    response = client.post(
        f"{API}/payments/init",
        json={
            "card_uid": card_b.uid,
            "amount": "20000.00",
            "method": "pse",
            "buyer_email": parent_a.email,
            "buyer_dni": "123456",
            "bank_code": "1009",
        },
        headers=auth_headers(parent_a),
    )
    assert response.status_code == 403


def test_payment_init_rejects_out_of_range_amount(client, family_factory, auth_headers):
    parent, _, card = family_factory(balance="10000.00")

    response = client.post(
        f"{API}/payments/init",
        json={
            "card_uid": card.uid,
            "amount": "500.00",
            "method": "pse",
            "buyer_email": parent.email,
            "buyer_dni": "123456",
            "bank_code": "1009",
        },
        headers=auth_headers(parent),
    )
    assert response.status_code == 400


def test_payment_init_rejects_more_than_two_decimals(
    client, family_factory, auth_headers
):
    parent, _, card = family_factory(balance="10000.00")

    response = client.post(
        f"{API}/payments/init",
        json={
            "card_uid": card.uid,
            "amount": "20000.555",
            "method": "pse",
            "buyer_email": parent.email,
            "buyer_dni": "123456",
            "bank_code": "1009",
        },
        headers=auth_headers(parent),
    )
    assert response.status_code == 422
