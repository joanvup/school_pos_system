from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text
from sqlalchemy.sql import func
from app.db.session import Base


class PaymentGatewaySetting(Base):
    """
    Configuración por pasarela de pago.
    - Solo UNA fila debe tener is_active=True (la pasarela activa que usa la app).
    - Las credenciales van en .env (PAYU_*, WOMPI_*, MP_*); aquí solo el estado.
    - `config` es JSON texto con extras opcionales por pasarela (no secretos).
    """
    __tablename__ = "payment_gateway_settings"

    id = Column(Integer, primary_key=True, index=True)
    gateway = Column(String(20), unique=True, nullable=False, index=True)  # payu, wompi, mercadopago
    label = Column(String(60), nullable=False)
    is_active = Column(Boolean, default=False)
    is_test = Column(Boolean, default=True)
    has_credentials = Column(Boolean, default=False)   # indica si el .env tiene credenciales para este provider
    config = Column(Text, nullable=True)               # JSON opcional (no secretos)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
