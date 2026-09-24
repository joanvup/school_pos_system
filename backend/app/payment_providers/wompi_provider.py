import uuid

import requests
from fastapi import HTTPException

from app.core.config import settings
from app.models.card import Transaction, TransactionType
from app.payment_providers.base import PaymentMethod, PaymentResult, PaymentStatus
from app.payment_providers.registry import register


@register
class WompiProvider:
    name = "wompi"

    def _check_credentials(self):
        if not settings.WOMPI_PUBLIC_KEY or not settings.WOMPI_PRIVATE_KEY:
            raise HTTPException(
                status_code=503,
                detail="Wompi no configurado: faltan WOMPI_PUBLIC_KEY / WOMPI_PRIVATE_KEY",
            )

    def get_methods(self):
        return [
            PaymentMethod("nequi", "Nequi"),
            PaymentMethod("qr", "Código QR"),
            PaymentMethod("pse", "PSE"),
        ]

    def init_recharge(self, db, payload: dict, meta: dict) -> PaymentResult:
        self._check_credentials()
        reference = "WOMPI-" + uuid.uuid4().hex[:12].upper()
        method = payload.get("method", "pse")

        tx = Transaction(
            card_id=payload.get("card_id"),
            amount=payload.get("amount", 0),
            type=TransactionType.RECHARGE,
            description=f"Recarga {method} en proceso ({reference})",
            reference_code=reference,
            status="pending",
            gateway="wompi",
            currency="COP",
        )
        db.add(tx)
        db.commit()

        redirect_url = (
            f"https://checkout.wompi.co/{settings.WOMPI_PUBLIC_KEY}/wompi/pay"
            f"?reference={reference}"
        )
        return PaymentResult(
            reference=reference,
            status=PaymentStatus.PENDING,
            redirect_url=redirect_url,
        )

    def handle_notification(self, db, form_data: dict) -> dict:
        data = form_data.get("data", {}) if isinstance(form_data.get("data"), dict) else {}
        trans = data.get("transaction", {}) if isinstance(data.get("transaction"), dict) else {}
        reference = trans.get("reference") or data.get("reference")
        status = trans.get("status")
        if not reference:
            return {"message": "Missing reference"}

        tx = db.query(Transaction).filter(Transaction.reference_code == reference).first()
        if not tx:
            return {"message": "TX Not Found"}

        tx.raw_notification = str(form_data)
        if tx.status == "approved":
            db.add(tx)
            db.commit()
            return {"message": "Already Approved"}

        if status == "APPROVED":
            tx.status = "approved"
            tx.description = "Recarga Wompi aprobada"
            if tx.card and tx.amount:
                tx.card.balance += tx.amount
                db.add(tx.card)
        else:
            tx.status = "declined"
            tx.description = "Recarga Wompi no aprobada"

        db.add(tx)
        db.commit()
        return {"message": "OK"}