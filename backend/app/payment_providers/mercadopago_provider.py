import uuid

import requests
from fastapi import HTTPException

from app.core.config import settings
from app.models.card import Transaction, TransactionType
from app.payment_providers.base import PaymentMethod, PaymentResult, PaymentStatus
from app.payment_providers.registry import register


@register
class MercadoPagoProvider:
    name = "mercadopago"

    def _headers(self):
        if not settings.MP_ACCESS_TOKEN:
            raise HTTPException(
                status_code=503,
                detail="Mercado Pago no configurado: falta MP_ACCESS_TOKEN",
            )
        return {"Authorization": f"Bearer {settings.MP_ACCESS_TOKEN}"}

    def get_methods(self):
        return [
            PaymentMethod("nequi", "Nequi"),
            PaymentMethod("pse", "PSE - Pago en línea"),
            PaymentMethod("card", "Tarjeta de crédito"),
        ]

    def init_recharge(self, db, payload: dict, meta: dict) -> PaymentResult:
        headers = self._headers()
        reference = "MP-" + uuid.uuid4().hex[:12].upper()

        preference = requests.post(
            f"{settings.MP_URL}/checkout/preferences",
            headers=headers,
            json={
                "external_reference": reference,
                "items": [{
                    "title": "Recarga de tarjeta School POS",
                    "quantity": 1,
                    "unit_price": float(payload.get("amount", 0)),
                    "currency_id": "COP",
                }],
                "notification_url": f"{meta.get('base_url', '')}/api/v1/payments/notify/mercadopago",
                "back_urls": {
                    "success": meta.get("return_url", ""),
                    "pending": meta.get("return_url", ""),
                    "failure": meta.get("return_url", ""),
                },
                "auto_return": "approved",
            },
            timeout=15,
        )
        data = preference.json()
        init_point = data.get("init_point", "")

        tx = Transaction(
            card_id=payload.get("card_id"),
            amount=payload.get("amount", 0),
            type=TransactionType.RECHARGE,
            description=f"Recarga Mercado Pago en proceso ({reference})",
            reference_code=reference,
            status="pending",
            gateway="mercadopago",
            currency="COP",
        )
        db.add(tx)
        db.commit()

        return PaymentResult(
            reference=reference,
            status=PaymentStatus.PENDING,
            redirect_url=init_point,
        )

    def handle_notification(self, db, form_data: dict) -> dict:
        data = form_data.get("data", {}) if isinstance(form_data.get("data"), dict) else {}
        payment_id = data.get("id")
        if not payment_id:
            return {"message": "Missing payment id"}

        headers = self._headers()
        response = requests.get(
            f"{settings.MP_URL}/v1/payments/{payment_id}",
            headers=headers,
            timeout=15,
        )
        info = response.json()
        reference = info.get("external_reference")

        tx = db.query(Transaction).filter(Transaction.reference_code == reference).first()
        if not tx:
            return {"message": "TX Not Found"}

        tx.raw_notification = str(form_data)
        if tx.status == "approved":
            db.add(tx)
            db.commit()
            return {"message": "Already Approved"}

        if info.get("status") == "approved":
            tx.status = "approved"
            tx.description = "Recarga Mercado Pago aprobada"
            if tx.card and tx.amount:
                tx.card.balance += tx.amount
                db.add(tx.card)
        else:
            tx.status = "declined"
            tx.description = f"Recarga Mercado Pago: status {info.get('status')}"

        db.add(tx)
        db.commit()
        return {"message": "OK"}