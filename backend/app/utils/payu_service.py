import hashlib
import hmac
import uuid
from decimal import Decimal, InvalidOperation

import requests

from app.core.config import settings


class PaymentGatewayError(Exception):
    """Error de comunicación o respuesta inválida de la pasarela."""


def _amount_as_decimal(amount) -> Decimal:
    try:
        value = Decimal(str(amount))
    except (InvalidOperation, TypeError, ValueError):
        raise PaymentGatewayError("Monto inválido")
    if value <= 0:
        raise PaymentGatewayError("Monto inválido")
    return value.quantize(Decimal("0.01"))


def _amount_for_signature(amount: Decimal) -> str:
    quantized = _amount_as_decimal(amount)
    if quantized == quantized.to_integral_value():
        return str(int(quantized))
    return format(quantized.normalize(), "f")


class PayUService:
    @staticmethod
    def generate_signature(reference_code, amount, currency="COP"):
        amount_str = _amount_for_signature(amount)
        raw_str = (
            f"{settings.PAYU_API_KEY}~{settings.PAYU_MERCHANT_ID}~"
            f"{reference_code}~{amount_str}~{currency}"
        )
        return hashlib.md5(raw_str.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_reference() -> str:
        # 128 bits de entropía, generados siempre en el servidor.
        return f"RECH-{uuid.uuid4().hex.upper()}"

    @staticmethod
    def get_banks():
        """Obtener la lista de bancos habilitados para PSE."""
        payload = {
            "language": "es",
            "command": "GET_BANKS_LIST",
            "merchant": {
                "apiLogin": settings.PAYU_API_LOGIN,
                "apiKey": settings.PAYU_API_KEY,
            },
            "test": settings.PAYU_IS_TEST,
            "bankListInformation": {
                "paymentMethod": "PSE",
                "paymentCountry": "CO",
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "FastAPI-SchoolPOS-Client/1.0",
        }

        try:
            response = requests.post(
                settings.PAYU_URL, json=payload, headers=headers, timeout=15
            )
            if response.status_code != 200:
                return []
            try:
                data = response.json()
            except ValueError:
                return []
            return data.get("banks", [])
        except requests.exceptions.RequestException:
            return []

    @staticmethod
    def init_pse_payment(data: dict, ip_address: str, user_agent: str, reference: str):
        if not reference:
            raise PaymentGatewayError("Referencia requerida")

        amount = _amount_as_decimal(data["amount"])
        currency = data.get("currency") or settings.PAYMENT_CURRENCY
        signature = PayUService.generate_signature(reference, amount, currency)

        phone = data.get("phone") or "3221234567"
        address = data.get("address") or "Calle 3 # 19b 105"
        session_id = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()

        amount_json = (
            int(amount) if amount == amount.to_integral_value() else float(amount)
        )

        payload = {
            "language": "es",
            "command": "SUBMIT_TRANSACTION",
            "merchant": {
                "apiLogin": settings.PAYU_API_LOGIN,
                "apiKey": settings.PAYU_API_KEY,
            },
            "transaction": {
                "order": {
                    "accountId": str(settings.PAYU_ACCOUNT_ID),
                    "referenceCode": reference,
                    "description": f"Recarga Cafeteria FCBV - Tarjeta {data['card_uid']}",
                    "language": "es",
                    "signature": signature,
                    "notifyUrl": f"{settings.PUBLIC_BASE_URL}/api/v1/payments/notify/payu",
                    "additionalValues": {
                        "TX_VALUE": {"value": amount_json, "currency": currency},
                        "TX_TAX": {"value": 0, "currency": currency},
                        "TX_TAX_RETURN_BASE": {"value": 0, "currency": currency},
                    },
                    "buyer": {
                        "merchantBuyerId": "1",
                        "fullName": data["buyer_name"],
                        "emailAddress": data["buyer_email"],
                        "contactPhone": phone,
                        "dniNumber": str(data["buyer_dni"]),
                        "shippingAddress": {
                            "street1": address,
                            "city": "Bogota",
                            "state": "Bogota D.C.",
                            "country": "CO",
                            "postalCode": "000000",
                            "phone": phone,
                        },
                    },
                },
                "payer": {
                    "fullName": data["buyer_name"],
                    "emailAddress": data["buyer_email"],
                    "contactPhone": phone,
                    "dniNumber": str(data["buyer_dni"]),
                    "billingAddress": {
                        "street1": address,
                        "city": "Bogota",
                        "state": "Bogota D.C.",
                        "country": "CO",
                        "postalCode": "000000",
                        "phone": phone,
                    },
                },
                "extraParameters": {
                    "RESPONSE_URL": (
                        f"{settings.FRONTEND_URL}/payment-result?reference={reference}"
                    ),
                    "PSE_REFERENCE1": ip_address,
                    "FINANCIAL_INSTITUTION_CODE": str(data["bank_code"]),
                    "USER_TYPE": "N" if data.get("user_type", "0") == "0" else "J",
                    "PSE_REFERENCE2": str(data.get("buyer_dni_type", "CC")),
                    "PSE_REFERENCE3": str(data["buyer_dni"]),
                },
                "type": "AUTHORIZATION_AND_CAPTURE",
                "paymentMethod": "PSE",
                "paymentCountry": "CO",
                "deviceSessionId": session_id,
                "ipAddress": ip_address,
                "userAgent": user_agent,
            },
            "test": settings.PAYU_IS_TEST,
        }

        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        try:
            response = requests.post(
                settings.PAYU_URL, json=payload, headers=headers, timeout=20
            )
        except requests.exceptions.RequestException as exc:
            raise PaymentGatewayError("No se pudo contactar a PayU") from exc

        if response.status_code >= 400:
            raise PaymentGatewayError("PayU rechazó la solicitud")
        try:
            return response.json()
        except ValueError as exc:
            raise PaymentGatewayError("Respuesta inválida de PayU") from exc

    @staticmethod
    def verify_confirmation_signature(
        merchant_id, reference, value, currency, state, incoming_sign
    ) -> bool:
        """
        PayU usa: ApiKey~merchant_id~reference_sale~value~currency~state_pol.
        El formato del monto varía; se prueban las variantes conocidas y se
        compara en tiempo constante.
        """
        if not incoming_sign or not reference:
            return False

        try:
            amount = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return False

        variants = {
            format(amount.quantize(Decimal("0.0")), "f"),
            str(int(amount)),
            str(value).strip(),
        }

        received = str(incoming_sign).strip().lower()
        for variant in variants:
            raw_str = (
                f"{settings.PAYU_API_KEY}~{merchant_id}~{reference}~"
                f"{variant}~{currency}~{state}"
            )
            generated = hashlib.md5(raw_str.encode("utf-8")).hexdigest()
            if hmac.compare_digest(generated, received):
                return True
        return False
