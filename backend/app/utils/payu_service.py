import hashlib
import requests
import uuid
import decimal
from app.core.config import settings

class PayUService:
    @staticmethod
    def generate_signature(reference_code, amount, currency="COP"):
        # PayU pide: ApiKey~merchantId~referenceCode~amount~currency
        # Formateamos el monto: si es 50000.0 -> "50000", si es 50000.5 -> "50000.5"
        amount_val = float(amount)
        if amount_val == int(amount_val):
            amount_str = str(int(amount_val))
        else:
            amount_str = str(amount_val)

        raw_str = f"{settings.PAYU_API_KEY}~{settings.PAYU_MERCHANT_ID}~{reference_code}~{amount_str}~{currency}"
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
        
        # --- NUEVOS ENCABEZADOS CRÍTICOS ---
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "FastAPI-SchoolPOS-Client/1.0"
        }

        try:
            print(f"DEBUG: Conectando a {settings.PAYU_URL}")
            response = requests.post(
                settings.PAYU_URL, 
                json=payload, 
                headers=headers, 
                timeout=15
            )
            
            # Si hay error (ej. 403 Forbidden o 404), imprimimos el texto de respuesta
            if response.status_code != 200:
                print(f"⚠️ PayU respondió status {response.status_code}: {response.text}")
                return []

            # Intentamos leer JSON con precaución
            try:
                data = response.json()
                return data.get("banks", [])
            except ValueError:
                print(f"❌ Error: PayU no envió un JSON válido. Respuesta recibida: {response.text[:200]}")
                return []

        except requests.exceptions.RequestException as e:
            print(f"❌ ERROR DE RED CON PAYU: {e}")
            return []

    @staticmethod
    def init_pse_payment(data: dict, ip_address: str, user_agent: str):
        """Enviar solicitud de pago a PayU con datos estrictos"""
        reference = f"RECH-{uuid.uuid4().hex[:10].upper()}"
        signature = PayUService.generate_signature(reference, data['amount'])
        
        # PayU Sandbox a veces falla si el sessionId no es un hash MD5
        session_id = hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()

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
                    "description": "Recarga Saldo Escolar",
                    "language": "es",
                    "signature": signature,
                    "notifyUrl": "https://pos.colegiobilingue.edu.co/api/v1/recharges/payu-confirmation",
                    "additionalValues": {
                        "TX_VALUE": {"value": float(data['amount']), "currency": "COP"}
                    },
                    "buyer": {
                        "emailAddress": data['buyer_email'],
                        "fullName": data['buyer_name'],
                        "contactPhone": "3221234567",
                        "dniNumber": str(data['buyer_dni']) # Forzar String
                    }
                },
                "payer": {
                    "fullName": data['buyer_name'],
                    "emailAddress": data['buyer_email'],
                    "contactPhone": "3221234567",
                    "dniNumber": str(data['buyer_dni']), # Forzar String
                    "dniType": str(data['buyer_dni_type'])
                },
                "type": "AUTHORIZATION_AND_CAPTURE",
                "paymentMethod": "PSE",
                "paymentCountry": "CO",
                "deviceSessionId": session_id,
                "ipAddress": ip_address, # IP Real del cliente
                "userAgent": user_agent,
                "extraParameters": {
                    "RESPONSE_URL": "https://pos.colegiobilingue.edu.co/payment-result",
                    "PSE_REFERENCE1": ip_address,
                    "FINANCIAL_INSTITUTION_CODE": str(data['bank_code']), # Forzar String
                    "USER_TYPE": str(data['user_type']), # Forzar String
                    "PSE_REFERENCE2": str(data['buyer_dni_type']),
                    "PSE_REFERENCE3": str(data['buyer_dni'])
                }
            },
            "test": settings.PAYU_IS_TEST
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

        response = requests.post(settings.PAYU_URL, json=payload, headers=headers, timeout=20)
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