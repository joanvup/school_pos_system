from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api import deps
from app.core.config import settings
from app.crud import crud_payment_gateway
from app.db.session import get_db
from app.models.card import Card
from app.models.user import User, UserRole
from app.payment_providers.registry import get_active_provider, get_provider
from app.schemas.payment import (
    ActivateProvider,
    InitPayment,
    InitPaymentResponse,
    PaymentMethodInfo,
    PaymentsMethodsResponse,
)

router = APIRouter()


def _require_admin(user: User):
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Solo administradores")


@router.get("/providers")
def list_payment_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    _require_admin(current_user)
    rows = crud_payment_gateway.list_providers(db)
    return [
        {
            "gateway": r.gateway,
            "label": r.label,
            "is_active": r.is_active,
            "is_test": r.is_test,
            "has_credentials": r.has_credentials,
        }
        for r in rows
    ]


@router.post("/providers/activate")
def activate_payment_provider(
    payload: ActivateProvider,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    _require_admin(current_user)
    row = crud_payment_gateway.set_active_provider(db, payload.gateway)
    if not row:
        raise HTTPException(status_code=404, detail="Pasarela no encontrada")
    return {"detail": f"Pasarela activa: {row.label}"}


@router.get("/methods", response_model=PaymentsMethodsResponse)
def get_payment_methods(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    crud_payment_gateway.seed_gateway_settings(db)
    provider = get_active_provider(db)
    from app.models.payment_gateway_settings import PaymentGatewaySetting
    active_row = (
        db.query(PaymentGatewaySetting)
        .filter(PaymentGatewaySetting.is_active.is_(True))
        .first()
    )
    return PaymentsMethodsResponse(
        gateway=provider.name,
        label=active_row.label if active_row else provider.name,
        methods=[PaymentMethodInfo(id=m.id, label=m.label) for m in provider.get_methods()],
        is_test=active_row.is_test if active_row else True,
    )


@router.post("/init", response_model=InitPaymentResponse)
def init_payment(
    payload: InitPayment,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    crud_payment_gateway.seed_gateway_settings(db)
    provider = get_active_provider(db)

    card = db.query(Card).filter(Card.uid == payload.card_uid).first()
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no existe")

    scheme = request.headers.get("x-forwarded-proto", "https")
    host = request.headers.get("host")
    base_url = f"{scheme}://{host}"
    return_url = payload.reference or f"{base_url}/"

    data = {
        "card_id": card.id,
        "card_uid": card.uid,
        "amount": payload.amount,
        "method": payload.method,
        "buyer_name": payload.buyer_name or current_user.full_name,
        "buyer_email": payload.buyer_email,
        "buyer_dni": payload.buyer_dni,
        "bank_code": payload.bank_code,
        "client_ip": request.headers.get("X-Real-IP") or request.client.host,
        "user_agent": request.headers.get("User-Agent") or "Unknown",
    }

    result = provider.init_recharge(db, data, {"base_url": base_url, "return_url": return_url})
    return InitPaymentResponse(
        redirect_url=result.redirect_url,
        qr_content=result.qr_content,
        reference=result.reference,
        status=result.status.value,
    )


@router.post("/notify/{gateway}")
async def notify_payment(gateway: str, request: Request, db: Session = Depends(get_db)):
    provider = get_provider(gateway)
    if not provider:
        raise HTTPException(status_code=404, detail="Pasarela no registrada")

    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        try:
            form_data = await request.json()
        except Exception:
            form_data = {}
    else:
        try:
            form_data = dict(await request.form())
        except Exception:
            form_data = {}

    return provider.handle_notification(db, form_data)


@router.get("/status/{reference}")
def get_payment_status(reference: str, db: Session = Depends(get_db)):
    from app.models.card import Transaction

    tx = db.query(Transaction).filter(Transaction.reference_code == reference).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    return {
        "reference": tx.reference_code,
        "status": tx.status,
        "amount": tx.amount,
        "gateway": tx.gateway,
    }