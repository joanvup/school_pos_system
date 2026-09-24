"""
Abstracción neutra de pasarelas de pago.

Cada pasarela implementa PaymentProvider con la MISMA interfaz, de modo que
la aplicación no sabe si está hablando con PayU, Wompi, Mercado Pago, etc.
El resultado normalizado (PaymentResult) es el que consume el frontend y la BD.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


class PaymentStatus:
    """Estados normalizados independientes de la pasarela."""
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"


@dataclass
class PaymentMethod:
    """Un método de pago mostrado al usuario (PSE, Nequi, tarjeta, ...)."""
    id: str
    label: str
    type: str                      # "redirect" | "qr" | "tokenized" | "bank_list"
    extra: Optional[Dict[str, Any]] = None


@dataclass
class PaymentResult:
    """
    Respuesta normalizada de un init de pago.
    Dependiendo del método puede venir una URL de redirección, un QR o una
    referencia para POLLING posterior.
    """
    reference: str = ""
    redirect_url: Optional[str] = None
    qr_content: Optional[str] = None
    status: str = PaymentStatus.PENDING
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


class PaymentProvider(ABC):
    #: identificador corto usado en BD/config/frontend
    name: str = "generic"
    #: nombre legible para el panel de administración
    label: str = "Pasarela genérica"
    #: si la pasarela requiere tener una cuenta creada (para mostrarla en admin)
    needs_account: bool = True

    @abstractmethod
    def get_methods(self, db=None) -> List[PaymentMethod]:
        """Métodos de pago disponibles con esta pasarela."""

    @abstractmethod
    def init_recharge(self, db, data: dict, meta: dict) -> PaymentResult:
        """
        Inicia la recarga. `data` trae datos del cliente (buyer_name, email,
        dni, método, bancos...); `meta` trae ip_url/user_agent/base_url.
        Debe lanzar HTTPException(400) con `detail` humano si hay error.
        """

    @abstractmethod
    def handle_notification(self, db, form_data: dict) -> dict:
        """
        Procesa la notificación (webhook) de la pasarela.
        `form_data` es el diccionario tal y como llegó (form-urlencoded o JSON).
        Debe validar la firma U OBLIGATORIAMENTE confirmar que la notificación
        corresponde a esta pasarela, registrar el evento y abonar el saldo.
        Devuelve un dict normalizado {"status", "reference", "extra"}.
        """

    def validate_and_abort_if_repeated(self, db, reference: str, desired: str = PaymentStatus.PENDING) -> bool:
        """Idempotencia: evita abonar dos veces la misma recarga."""
        from app.models.card import Transaction
        tx = db.query(Transaction).filter(Transaction.reference_code == reference).first()
        if not tx:
            return False
        if tx.status == desired:
            # ya procesada/abonada → el webhook no debe re-abonar
            return False
        return True
