from sqlalchemy import Column, Integer, String, Boolean, Text
from app.db.session import Base


class PaymentGatewaySetting(Base):
    __tablename__ = "payment_gateway_settings"

    id = Column(Integer, primary_key=True, index=True)
    gateway = Column(String(30), unique=True, index=True, nullable=False)
    label = Column(String(80), nullable=False)
    is_active = Column(Boolean, default=False)
    is_test = Column(Boolean, default=True)
    has_credentials = Column(Boolean, default=False)
    config = Column(Text, nullable=True)  # JSON con config extra por pasarela