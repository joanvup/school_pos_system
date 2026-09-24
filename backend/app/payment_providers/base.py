from enum import Enum
from typing import Optional


class PaymentStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"


class PaymentMethod:
    def __init__(self, id: str, label: str):
        self.id = id
        self.label = label


class PaymentResult:
    def __init__(self, reference: str, status: PaymentStatus,
                 redirect_url: Optional[str] = None,
                 qr_content: Optional[str] = None,
                 raw: Optional[str] = None):
        self.reference = reference
        self.status = status
        self.redirect_url = redirect_url
        self.qr_content = qr_content
        self.raw = raw


class PaymentProvider:
    """Contrato de pasarela de pago."""
    name: str = ""

    def get_methods(self):
        """Lista de PaymentMethod que soporta la pasarela."""
        raise NotImplementedError

    def init_recharge(self, db, payload: dict, meta: dict) -> PaymentResult:
        """Crea el pago.
        payload: card_id, amount, buyer_name, buyer_email, buyer_dni, method...
        meta: base_url, return_url...
        """
        raise NotImplementedError

    def handle_notification(self, db, form_data: dict) -> dict:
        """Procesa el webhook. form_data ya viene parseado (dict)."""
        raise NotImplementedError