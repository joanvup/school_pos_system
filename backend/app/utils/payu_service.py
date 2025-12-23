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
    def init_pse_payment(data: dict, ip_address: str, user_agent: str, base_url: str):
        reference = f"RECH-{uuid.uuid4().hex[:10].upper()}"
        
        # Limpieza de monto para evitar el .0 en el JSON
        amount_val = float(data['amount'])
        amount_json = int(amount_val) if amount_val == int(amount_val) else amount_val
        
        signature = PayUService.generate_signature(reference, amount_json)
        # Datos de contacto opcionales con fallback
        phone = data.get('phone') if data.get('phone') else "3221234567"
        address = data.get('address') if data.get('address') else "Calle 3 # 19b 105"
        
        # PayU prefiere un deviceSessionId de 32 caracteres (MD5)
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
                    "accountId": str(settings.PAYU_ACCOUNT_ID),
                    "referenceCode": reference,
                    "description": f"Recarga Cafeteria FCBV - Tarjeta {data['card_uid']}",
                    "language": "es",
                    "signature": signature,
                    "notifyUrl": f"{base_url}/api/v1/recharges/payu-confirmation", 
                    "additionalValues": {
                        "TX_VALUE": {"value": amount_json, "currency": "COP"},
                        "TX_TAX": {"value": 0, "currency": "COP"},
                        "TX_TAX_RETURN_BASE": {"value": 0, "currency": "COP"}
                    },
                    "buyer": {
                        "merchantBuyerId": "1",
                        "fullName": data['buyer_name'],
                        "emailAddress": data['buyer_email'],
                        "contactPhone": phone,
                        "dniNumber": str(data['buyer_dni']),
                        "shippingAddress": {
                            "street1": address,
                            "city": "Bogota",
                            "state": "Bogota D.C.",
                            "country": "CO",
                            "postalCode": "000000",
                            "phone": phone
                        }
                    }
                },
                "payer": {
                    "fullName": data['buyer_name'],
                    "emailAddress": data['buyer_email'],
                    "contactPhone": phone,
                    "dniNumber": str(data['buyer_dni']),
                    "billingAddress": {
                        "street1": address,
                        "city": "Bogota",
                        "state": "Bogota D.C.",
                        "country": "CO",
                        "postalCode": "000000",
                        "phone": phone
                    }
                },
                "extraParameters": {
                    "RESPONSE_URL": f"{base_url}/payment-result",
                    "PSE_REFERENCE1": ip_address,
                    "FINANCIAL_INSTITUTION_CODE": str(data['bank_code']),
                    "USER_TYPE": "N" if data['user_type'] == "0" else "J",
                    "PSE_REFERENCE2": str(data['buyer_dni_type']),
                    "PSE_REFERENCE3": str(data['buyer_dni'])
                },
                "type": "AUTHORIZATION_AND_CAPTURE",
                "paymentMethod": "PSE",
                "paymentCountry": "CO",
                "deviceSessionId": session_id,
                "ipAddress": ip_address,
                "userAgent": user_agent
            },
            "test": False # Cambiado a False para coincidir con ejemplo Sandbox
        }
        
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        response = requests.post(settings.PAYU_URL, json=payload, headers=headers, timeout=20)
        return response.json(), reference
        
    @staticmethod
    def verify_confirmation_signature(merchant_id, reference, value, currency, state, incoming_sign):
        """
        Versión ultra-robusta para validar la firma de PayU.
        Prueba múltiples formatos de número para asegurar coincidencia.
        """
        import decimal
        
        # PayU usa: ApiKey~merchant_id~reference_sale~value~currency~state_pol
        # El valor es un dolor de cabeza, probaremos las 3 variantes más comunes:
        
        # Variante 1: Un decimal (.0) - El más común
        val_1 = str(decimal.Decimal(value).quantize(decimal.Decimal('0.0'), rounding=decimal.ROUND_HALF_EVEN))
        # Variante 2: Sin decimales
        val_2 = str(int(float(value)))
        # Variante 3: Tal cual llega
        val_3 = str(value)

        for v in [val_1, val_2, val_3]:
            raw_str = f"{settings.PAYU_API_KEY}~{merchant_id}~{reference}~{v}~{currency}~{state}"
            generated_sign = hashlib.md5(raw_str.encode('utf-8')).hexdigest()
            if generated_sign == incoming_sign:
                print(f"DEBUG: Firma validada con éxito usando valor: {v}")
                return True
        
        print(f"DEBUG: Error de firma. Recibida: {incoming_sign}")
        return False