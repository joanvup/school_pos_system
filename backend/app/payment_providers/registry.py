from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.payment_gateway_settings import PaymentGatewaySetting

_PROVIDERS = {}


def register(cls):
    """Decorador: registra el provider por su atributo `name`."""
    _PROVIDERS[cls.name] = cls()
    return cls


def get_provider(name: str):
    return _PROVIDERS.get(name)


def get_all_providers():
    return _PROVIDERS


def get_active_provider(db: Session):
    """Provider activo según la tabla; cae siempre a PayU como seguro."""
    active = (
        db.query(PaymentGatewaySetting)
        .filter(PaymentGatewaySetting.is_active.is_(True))
        .first()
    )
    name = active.gateway if active else "payu"
    provider = _PROVIDERS.get(name)
    if not provider:
        raise HTTPException(status_code=503, detail=f"Pasarela '{name}' no registrada")
    return provider