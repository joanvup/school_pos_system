from fastapi import HTTPException

from app.models.card import Card
from app.payment_providers.base import PaymentMethod, PaymentResult
from app.payment_providers.registry import register
from app.services.payment_service import (
    process_payu_notification,
    start_payu_payment,
)


@register
class PayUProvider:
    name = "payu"

    def get_methods(self):
        return [PaymentMethod("pse", "PSE - Pago en línea")]

    def init_recharge(self, db, payload: dict, meta: dict) -> PaymentResult:
        card = db.query(Card).filter(Card.id == payload.get("card_id")).first()
        if not card:
            raise HTTPException(status_code=404, detail="Tarjeta no encontrada")

        return start_payu_payment(
            db=db,
            card=card,
            amount=payload.get("amount"),
            buyer=payload,
            client_ip=payload.get("client_ip", "0.0.0.0"),
            user_agent=payload.get("user_agent", "Unknown"),
        )

    def handle_notification(self, db, form_data: dict) -> dict:
        return process_payu_notification(db, form_data, raw_text=str(form_data))
