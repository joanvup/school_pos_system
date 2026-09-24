from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.payment_gateway_settings import PaymentGatewaySetting


def get_active(db: Session) -> Optional[PaymentGatewaySetting]:
    return db.query(PaymentGatewaySetting).filter(PaymentGatewaySetting.is_active.is_(True)).first()


def get_by_gateway(db: Session, gateway: str) -> Optional[PaymentGatewaySetting]:
    return db.query(PaymentGatewaySetting).filter(PaymentGatewaySetting.gateway == gateway).first()


def list_all(db: Session) -> List[PaymentGatewaySetting]:
    return db.query(PaymentGatewaySetting).order_by(PaymentGatewaySetting.gateway).all()


def set_active(db: Session, gateway: str) -> PaymentGatewaySetting:
    """Activa una pasarela y desactiva las demás. Retorna la fila activada."""
    gateway_row = get_by_gateway(db, gateway)
    if not gateway_row:
        raise ValueError(f"La pasarela '{gateway}' no está registrada.")

    others = db.query(PaymentGatewaySetting).filter(PaymentGatewaySetting.is_active.is_(True)).all()
    for other in others:
        other.is_active = False
    gateway_row.is_active = True
    db.add_all([gateway_row] + others)
    db.commit()
    db.refresh(gateway_row)
    return gateway_row


def update_has_credentials(db: Session, gateway: str, has_credentials: bool) -> None:
    row = get_by_gateway(db, gateway)
    if row:
        row.has_credentials = has_credentials
        db.add(row)
        db.commit()


def seed_defaults(db: Session) -> None:
    """Garantiza filas mínimas para PayU, Wompi y Mercado Pago."""
    defaults = [
        ("payu", "PayU (PSE)", True),
        ("wompi", "Wompi (Bancolombia)", False),
        ("mercadopago", "Mercado Pago", False),
    ]
    for gateway, label, active in defaults:
        row = get_by_gateway(db, gateway)
        if not row:
            db.add(PaymentGatewaySetting(gateway=gateway, label=label, is_active=active, is_test=True))
    db.commit()
