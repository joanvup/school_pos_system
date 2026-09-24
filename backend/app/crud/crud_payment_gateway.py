from sqlalchemy.orm import Session

from app.models.payment_gateway_settings import PaymentGatewaySetting

DEFAULT_PROVIDERS = [
    {"gateway": "payu", "label": "PayU PSE", "is_active": True, "is_test": True},
    {"gateway": "wompi", "label": "Wompi", "is_active": False, "is_test": True},
    {"gateway": "mercadopago", "label": "Mercado Pago", "is_active": False, "is_test": True},
]


def list_providers(db: Session):
    rows = db.query(PaymentGatewaySetting).order_by(PaymentGatewaySetting.id).all()
    if rows:
        return rows
    # Respaldo: si la tabla está vacía (seed no corrió), sembramos y devolvemos.
    seed_gateway_settings(db)
    return db.query(PaymentGatewaySetting).order_by(PaymentGatewaySetting.id).all()


def seed_gateway_settings(db: Session):
    for data in DEFAULT_PROVIDERS:
        exists = (
            db.query(PaymentGatewaySetting)
            .filter(PaymentGatewaySetting.gateway == data["gateway"])
            .first()
        )
        if not exists:
            db.add(PaymentGatewaySetting(**data))
    db.commit()

    active = (
        db.query(PaymentGatewaySetting)
        .filter(PaymentGatewaySetting.is_active.is_(True))
        .first()
    )
    if not active:
        payu = (
            db.query(PaymentGatewaySetting)
            .filter(PaymentGatewaySetting.gateway == "payu")
            .first()
        )
        if payu:
            payu.is_active = True
            db.commit()


def set_active_provider(db: Session, gateway: str) -> PaymentGatewaySetting:
    row = (
        db.query(PaymentGatewaySetting)
        .filter(PaymentGatewaySetting.gateway == gateway)
        .first()
    )
    if not row:
        return None
    db.query(PaymentGatewaySetting).update(
        {PaymentGatewaySetting.is_active: False}
    )
    row.is_active = True
    db.commit()
    db.refresh(row)
    return row