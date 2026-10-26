from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api import deps
from app.crud import crud_payment_gateway
from app.db.session import get_db
from app.models.user import User, UserRole
from app.payment_providers.registry import get_active_provider
from app.schemas.payment import (
    ActivateProvider,
    InitPayment,
    InitPaymentResponse,
    PaymentMethodInfo,
    PaymentsMethodsResponse,
)
from app.services.payment_service import (
    require_rechargeable_card,
    get_payment_status,
    process_payu_notification,
    start_payu_payment,
)

router = APIRouter()

MAX_WEBHOOK_BYTES = 16 * 1024


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
        raise HTTPException(status_code=404, detail="Pasarela no soportada")
    return {"detail": f"Pasarela activa: {row.label}"}


@router.get("/methods", response_model=PaymentsMethodsResponse)
def get_payment_methods(
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    crud_payment_gateway.seed_gateway_settings(db)
    provider = get_active_provider(db)
    rows = crud_payment_gateway.list_providers(db)
    return PaymentsMethodsResponse(
        gateway=provider.name,
        label="PayU PSE",
        methods=[PaymentMethodInfo(id=m.id, label=m.label) for m in provider.get_methods()],
        is_test=rows[0].is_test if rows else True,
    )


@router.post("/init", response_model=InitPaymentResponse)
def init_payment(
    payload: InitPayment,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    crud_payment_gateway.seed_gateway_settings(db)
    get_active_provider(db)

    card = require_rechargeable_card(db, payload.card_uid, current_user)

    result = start_payu_payment(
        db=db,
        card=card,
        amount=payload.amount,
        buyer={
            "buyer_name": payload.buyer_name or current_user.full_name,
            "buyer_email": payload.buyer_email or current_user.email,
            "buyer_dni": payload.buyer_dni,
            "bank_code": payload.bank_code,
            "phone": "",
            "address": "",
            "user_type": "0",
            "buyer_dni_type": "CC",
        },
        client_ip=request.headers.get("X-Real-IP") or (request.client.host if request.client else "0.0.0.0"),
        user_agent=request.headers.get("User-Agent") or "Unknown",
    )
    return InitPaymentResponse(
        redirect_url=result.redirect_url,
        qr_content=result.qr_content,
        reference=result.reference,
        status=result.status.value,
    )


async def handle_payu_notification_request(request: Request, db: Session) -> dict:
    raw = await request.body()
    if len(raw) > MAX_WEBHOOK_BYTES:
        raise HTTPException(status_code=413, detail="Notificación demasiado grande")

    content_type = request.headers.get("content-type", "").lower()
    if "application/json" in content_type:
        try:
            form_data = await request.json()
        except Exception:
            raise HTTPException(status_code=400, detail="JSON inválido")
    else:
        try:
            form_data = dict(await request.form())
        except Exception:
            raise HTTPException(status_code=400, detail="Formulario inválido")

    if not isinstance(form_data, dict) or not form_data:
        raise HTTPException(status_code=400, detail="Notificación vacía")

    return process_payu_notification(
        db,
        form_data,
        raw_text=raw.decode("utf-8", errors="replace"),
        remote_ip=request.client.host if request.client else None,
    )


@router.post("/notify/payu")
async def notify_payu(request: Request, db: Session = Depends(get_db)):
    """Webhook canónico de PayU. Debe estar configurado en el dashboard."""
    return await handle_payu_notification_request(request, db)


@router.post("/notify/{gateway}")
async def notify_payment(gateway: str, request: Request, db: Session = Depends(get_db)):
    if gateway != "payu":
        raise HTTPException(status_code=404, detail="Pasarela no registrada")
    return await handle_payu_notification_request(request, db)


@router.get("/status/{reference}")
def get_payment_status_endpoint(
    reference: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    return get_payment_status(db, current_user, reference)
