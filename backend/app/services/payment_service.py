from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import re

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.permissions import can_recharge_card
from app.crud.crud_card import get_card_by_uid
from app.models.card import (
    Card,
    CardStatus,
    PaymentNotification,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from app.models.user import User
from app.payment_providers.base import PaymentResult, PaymentStatus
from app.utils.payu_service import PaymentGatewayError, PayUService

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_amount(amount) -> Decimal:
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Monto inválido")

    if value.as_tuple().exponent < -2:
        raise HTTPException(status_code=400, detail="El monto admite máximo 2 decimales")

    value = value.quantize(Decimal("0.01"))
    if value < settings.MIN_RECHARGE_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail=f"El monto mínimo es {settings.MIN_RECHARGE_AMOUNT}",
        )
    if value > settings.MAX_RECHARGE_AMOUNT:
        raise HTTPException(
            status_code=400,
            detail=f"El monto máximo es {settings.MAX_RECHARGE_AMOUNT}",
        )
    return value


def _validate_buyer(data: dict, fallback_name: str) -> dict:
    buyer_name = (data.get("buyer_name") or fallback_name or "").strip()
    buyer_email = (data.get("buyer_email") or "").strip()
    buyer_dni = str(data.get("buyer_dni") or "").strip()
    bank_code = str(data.get("bank_code") or "").strip()

    if not buyer_name:
        raise HTTPException(status_code=400, detail="El nombre del comprador es obligatorio")
    if not EMAIL_RE.match(buyer_email):
        raise HTTPException(status_code=400, detail="Correo del comprador inválido")
    if not buyer_dni:
        raise HTTPException(status_code=400, detail="El documento del comprador es obligatorio")
    if not bank_code:
        raise HTTPException(status_code=400, detail="El banco es obligatorio")

    return {
        **data,
        "buyer_name": buyer_name,
        "buyer_email": buyer_email,
        "buyer_dni": buyer_dni,
        "bank_code": bank_code,
    }


def require_rechargeable_card(db: Session, card_uid: str, user: User) -> Card:
    card = get_card_by_uid(db, uid=card_uid)
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
    if not can_recharge_card(user, card):
        raise HTTPException(
            status_code=403, detail="No tienes permiso para recargar esta tarjeta"
        )
    if card.status != CardStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="La tarjeta está bloqueada")
    if not card.student_id and not card.user_id:
        raise HTTPException(status_code=400, detail="La tarjeta no está vinculada")
    return card


def start_payu_payment(
    db: Session,
    card: Card,
    amount,
    buyer: dict,
    client_ip: str,
    user_agent: str,
) -> PaymentResult:
    """Crea la transacción pendiente y luego llama a PayU (nunca dentro de la TX)."""
    amount = _validate_amount(amount)
    buyer = _validate_buyer(buyer, fallback_name="")

    reference = PayUService.generate_reference()
    transaction = Transaction(
        card_id=card.id,
        amount=amount,
        type=TransactionType.RECHARGE,
        description=f"Recarga PSE en proceso ({reference})",
        reference_code=reference,
        status=TransactionStatus.PENDING.value,
        gateway="payu",
        currency=settings.PAYMENT_CURRENCY,
        payment_method="pse",
    )
    db.add(transaction)
    db.commit()

    data = {
        **buyer,
        "card_id": card.id,
        "card_uid": card.uid,
        "amount": amount,
        "currency": settings.PAYMENT_CURRENCY,
        "client_ip": client_ip,
        "user_agent": user_agent,
    }

    try:
        response = PayUService.init_pse_payment(
            data, client_ip, user_agent, reference
        )
    except PaymentGatewayError:
        # La transacción queda pendiente: un webhook tardío aún puede abonarla.
        transaction.response_code = "GATEWAY_ERROR"
        db.commit()
        raise HTTPException(
            status_code=502, detail="No se pudo iniciar el pago con la pasarela"
        )

    tx_res = response.get("transactionResponse") or {}
    state = tx_res.get("state")
    bank_url = (tx_res.get("extraParameters") or {}).get("BANK_URL")

    if state != "PENDING" or not bank_url:
        transaction.status = TransactionStatus.DECLINED.value
        transaction.response_code = str(tx_res.get("responseCode") or "UNKNOWN_ERROR")
        transaction.raw_notification = str(response)
        db.commit()
        raise HTTPException(status_code=502, detail="La pasarela rechazó el pago")

    if not str(bank_url).startswith("https://"):
        transaction.status = TransactionStatus.FAILED.value
        transaction.response_code = "INVALID_REDIRECT"
        db.commit()
        raise HTTPException(status_code=502, detail="Respuesta inválida de la pasarela")

    transaction.cus = tx_res.get("trazabilityCode")
    transaction.response_code = tx_res.get("responseCode")
    db.commit()

    return PaymentResult(
        reference=reference,
        status=PaymentStatus.PENDING,
        redirect_url=bank_url,
    )


def _record_notification(
    db: Session,
    reference: str,
    raw_text: str,
    remote_ip: str,
    signature_valid: bool,
) -> PaymentNotification:
    notification = PaymentNotification(
        reference_code=reference,
        gateway="payu",
        raw=raw_text,
        remote_ip=remote_ip,
        signature_valid=signature_valid,
        reason=None,
    )
    db.add(notification)
    return notification


def process_payu_notification(
    db: Session,
    form_data: dict,
    raw_text: str = "",
    remote_ip: str = None,
) -> dict:
    reference = str(form_data.get("reference_sale") or "").strip()
    merchant_id = str(form_data.get("merchant_id") or "").strip()
    value = form_data.get("value")
    currency = str(form_data.get("currency") or "").strip().upper()
    state = str(form_data.get("state_pol") or "").strip()
    incoming_sign = form_data.get("sign")

    notification = _record_notification(
        db, reference or None, raw_text, remote_ip, signature_valid=False
    )

    def abort(status_code: int, reason: str):
        notification.reason = reason
        db.commit()
        raise HTTPException(status_code=status_code, detail="Notificación rechazada")

    if not merchant_id or merchant_id != str(settings.PAYU_MERCHANT_ID):
        abort(400, "merchant_id inválido")

    if not PayUService.verify_confirmation_signature(
        merchant_id, reference, value, currency, state, incoming_sign
    ):
        abort(400, "firma inválida")

    notification.signature_valid = True

    tx = (
        db.query(Transaction)
        .filter(Transaction.reference_code == reference)
        .first()
    )
    if not tx:
        abort(404, "referencia desconocida")

    try:
        notified_amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        abort(400, "monto inválido")

    if notified_amount != Decimal(tx.amount).quantize(Decimal("0.01")):
        abort(400, "monto no coincide")

    if currency != (tx.currency or settings.PAYMENT_CURRENCY).upper():
        abort(400, "moneda no coincide")

    if tx.type != TransactionType.RECHARGE:
        abort(400, "tipo de transacción inválido")

    # Orden de bloqueo: tarjeta -> transacción.
    card = (
        db.query(Card)
        .filter(Card.id == tx.card_id)
        .with_for_update()
        .first()
    )
    tx = (
        db.query(Transaction)
        .filter(Transaction.id == tx.id)
        .with_for_update()
        .first()
    )

    if not card or not tx:
        abort(404, "transacción inconsistente")

    if notified_amount != Decimal(tx.amount).quantize(Decimal("0.01")):
        abort(400, "monto no coincide")

    if tx.status == TransactionStatus.APPROVED.value and tx.credited_at is not None:
        notification.reason = "duplicado"
        db.commit()
        return {"message": "Already approved", "status": "approved"}

    if tx.status in (
        TransactionStatus.COMPLETED.value,
        TransactionStatus.REVERSED.value,
    ):
        abort(400, "estado no permite abono")

    tx.gateway = "payu"
    tx.currency = currency
    tx.raw_notification = raw_text or str(form_data)
    tx.response_code = str(form_data.get("response_code_pol") or "")

    if state == "4":
        tx.status = TransactionStatus.APPROVED.value
        tx.credited_at = datetime.now(timezone.utc)
        tx.cus = str(form_data.get("cus") or tx.cus or "")
        tx.description = f"Recarga PSE Aprobada (CUS: {tx.cus})"
        card.balance = Decimal(card.balance or 0) + Decimal(tx.amount)
        notification.reason = "abono aplicado"
        db.add(card)
        db.add(tx)
        db.commit()
        return {"message": "OK", "status": "approved"}

    if tx.status == TransactionStatus.PENDING.value:
        tx.status = TransactionStatus.DECLINED.value
        tx.description = f"Recarga PSE no aprobada. Estado PayU: {state}"
        notification.reason = "rechazada por PayU"
        db.add(tx)
        db.commit()
        return {"message": "OK", "status": "declined"}

    notification.reason = "estado ignorado"
    db.commit()
    return {"message": "Ignored", "status": tx.status}


def get_payment_status(db: Session, user: User, reference: str) -> dict:
    tx = (
        db.query(Transaction)
        .filter(Transaction.reference_code == reference)
        .first()
    )
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")

    card = db.query(Card).filter(Card.id == tx.card_id).first()
    if not card or not can_recharge_card(user, card):
        raise HTTPException(status_code=403, detail="No autorizado")

    return {
        "reference": tx.reference_code,
        "status": tx.status,
        "amount": float(tx.amount),
        "gateway": tx.gateway,
    }
