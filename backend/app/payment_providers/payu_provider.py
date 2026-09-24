from fastapi import HTTPException

from app.core.config import settings
from app.models.card import Transaction, TransactionType
from app.payment_providers.base import PaymentMethod, PaymentResult, PaymentStatus
from app.payment_providers.registry import register
from app.utils.payu_service import PayUService


@register
class PayUProvider:
    name = "payu"

    def get_methods(self):
        return [PaymentMethod("pse", "PSE - Pago en línea")]

    def init_recharge(self, db, payload: dict, meta: dict) -> PaymentResult:
        client_ip = payload.get("client_ip", "0.0.0.0")
        user_agent = payload.get("user_agent", "Unknown")
        # Campos que PayUService real exige; con default para funcionar
        # igual desde el endpoint neutro /payments/init.
        data = dict(payload)
        data["user_type"] = data.get("user_type", "0")
        data["buyer_dni_type"] = str(data.get("buyer_dni_type", "CC"))
        data["bank_code"] = str(data.get("bank_code", "1009"))
        data["card_uid"] = data.get("card_uid", "")
        res, reference = PayUService.init_pse_payment(
            data, client_ip, user_agent, meta.get("base_url", "")
        )
        tx_res = res.get("transactionResponse", {})

        if (
            tx_res.get("state") == "PENDING"
            and "extraParameters" in tx_res
            and "BANK_URL" in tx_res["extraParameters"]
        ):
            tx = Transaction(
                card_id=payload.get("card_id"),
                amount=payload.get("amount", 0),
                type=TransactionType.RECHARGE,
                description=f"Recarga PSE en proceso ({reference})",
                reference_code=reference,
                cus=tx_res.get("trazabilityCode"),
                status="pending",
                gateway="payu",
                currency="COP",
            )
            db.add(tx)
            db.commit()
            return PaymentResult(
                reference=reference,
                status=PaymentStatus.PENDING,
                redirect_url=tx_res["extraParameters"]["BANK_URL"],
            )

        response_code = tx_res.get("responseCode", "UNKNOWN_ERROR")
        raise HTTPException(status_code=400, detail=f"Error en la transacción: {response_code}")

    def handle_notification(self, db, form_data: dict) -> dict:
        reference = form_data.get("reference_sale")
        if not reference:
            return {"message": "Missing reference"}

        tx = db.query(Transaction).filter(Transaction.reference_code == reference).first()
        if not tx:
            return {"message": "TX Not Found"}

        tx.raw_notification = str(form_data)
        tx.gateway = "payu"
        tx.currency = form_data.get("currency", "COP")
        tx.response_code = form_data.get("response_code_pol")

        if tx.status == "approved":
            db.add(tx)
            db.commit()
            return {"message": "Already Approved"}

        if form_data.get("state_pol") == "4":
            tx.status = "approved"
            tx.cus = form_data.get("cus")
            tx.description = f"Recarga PSE Aprobada (CUS: {tx.cus})"
            if tx.card and form_data.get("value"):
                tx.card.balance += float(form_data["value"])
                db.add(tx.card)
        else:
            tx.status = "declined"
            tx.description = f"Recarga PSE no aprobada. Estado PayU: {form_data.get('state_pol')}"

        db.add(tx)
        db.commit()
        return {"message": "OK"}