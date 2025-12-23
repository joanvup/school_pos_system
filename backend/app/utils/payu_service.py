import hashlib
import requests
import uuid
from app.core.config import settings

class PayUService:
    @staticmethod
    def generate_signature(reference_code, amount, currency="COP"):
        # La firma en PayU es: ApiKey~merchantId~referenceCode~amount~currency
        # Importante: El monto debe formatearse a una cifra decimal si termina en .0
        raw_str = f"{settings.PAYU_API_KEY}~{settings.PAYU_MERCHANT_ID}~{reference_code}~{amount}~{currency}"
        return hashlib.md5(raw_str.encode('utf-8')).hexdigest()

    @staticmethod
    def get_banks():
        """Obtener la lista de bancos habilitados para PSE"""
        payload = {
            "language": "es",
            "command": "GET_BANKS_LIST",
            "merchant": {
                "apiLogin": settings.PAYU_API_LOGIN,
                "apiKey": settings.PAYU_API_KEY
            },
            "test": settings.PAYU_IS_TEST,
            "bankListInformation": {
                "paymentMethod": "PSE",
                "paymentCountry": "CO"
            }
        }
        response = requests.post(settings.PAYU_URL, json=payload)
        if response.status_code == 200:
            return response.json().get("banks", [])
        return []

    @staticmethod
    def init_pse_payment(data: dict):
        """Enviar solicitud de pago a PayU"""
        reference = f"RECH-{uuid.uuid4().hex[:10].upper()}"
        signature = PayUService.generate_signature(reference, data['amount'])

        payload = {
            "language": "es",
            "command": "SUBMIT_TRANSACTION",
            "merchant": {
                "apiLogin": settings.PAYU_API_LOGIN,
                "apiKey": settings.PAYU_API_KEY
            },
            "transaction": {
                "order": {
                    "accountId": settings.PAYU_ACCOUNT_ID,
                    "referenceCode": reference,
                    "description": f"Recarga tarjeta {data['card_uid']}",
                    "language": "es",
                    "signature": signature,
                    "notifyUrl": "https://pos.colegiobilingue.edu.co/api/v1/recharges/payu-confirmation",
                    "additionalValues": {
                        "TX_VALUE": {"value": data['amount'], "currency": "COP"}
                    },
                    "buyer": {
                        "emailAddress": data['buyer_email'],
                        "fullName": data['buyer_name'],
                        "contactPhone": "3000000000",
                        "dniNumber": "123456"
                    }
                },
                "type": "AUTHORIZATION_AND_CAPTURE",
                "paymentMethod": "PSE",
                "paymentCountry": "CO",
                "deviceSessionId": "v768p964465i58552p54", # Requerido por seguridad
                "ipAddress": "127.0.0.1",
                "extraParameters": {
                    "RESPONSE_URL": "https://pos.colegiobilingue.edu.co/payment-result",
                    "PSE_REFERENCE1": "127.0.0.1",
                    "FINANCIAL_INSTITUTION_CODE": data['bank_code'],
                    "USER_TYPE": data['user_type'], # 0: Natural, 1: Jurídica
                    "PSE_REFERENCE2": data['buyer_dni_type'],
                    "PSE_REFERENCE3": data['buyer_dni']
                }
            },
            "test": settings.PAYU_IS_TEST
        }
        
        response = requests.post(settings.PAYU_URL, json=payload)
        return response.json(), reference

    @staticmethod
    def verify_confirmation_signature(merchant_id, reference, value, currency, state, incoming_sign):
        """
        Valida la firma que envía PayU en la confirmación.
        La fórmula es: ApiKey~merchant_id~referenceCode~new_value~currency~state
        Nota: PayU a veces envía el valor con un decimal (.0), hay que ser exactos.
        """
        # El valor debe tratarse con cuidado para que coincida con el hash
        # Si el valor es 50000.00, PayU suele firmar como 50000.0 o 50000
        # Una técnica común es formatear a 1 decimal si es necesario.
        import decimal
        formatted_value = str(decimal.Decimal(value).quantize(decimal.Decimal('0.0'), rounding=decimal.ROUND_HALF_EVEN))
        
        raw_str = f"{settings.PAYU_API_KEY}~{merchant_id}~{reference}~{formatted_value}~{currency}~{state}"
        # Si no coincide con .0, intentamos sin decimales (depende de la versión de PayU)
        generated_sign = hashlib.md5(raw_str.encode('utf-8')).hexdigest()
        
        if generated_sign == incoming_sign:
            return True
            
        # Intento 2: Sin decimales
        raw_str_alt = f"{settings.PAYU_API_KEY}~{merchant_id}~{reference}~{int(float(value))}~{currency}~{state}"
        generated_sign_alt = hashlib.md5(raw_str_alt.encode('utf-8')).hexdigest()
        
        return generated_sign_alt == incoming_sign