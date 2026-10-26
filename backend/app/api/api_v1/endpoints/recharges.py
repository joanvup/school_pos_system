from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.api import deps
from app.api.api_v1.endpoints.payments import handle_payu_notification_request
from app.crud import crud_payment_gateway
from app.db.session import get_db
from app.models.user import User
from app.payment_providers.registry import get_active_provider
from app.services.payment_service import (
    get_payment_status,
    require_rechargeable_card,
    start_payu_payment,
)
from app.utils.payu_service import PayUService

router = APIRouter()


@router.get("/banks")
def get_pse_banks(current_user: User = Depends(deps.get_current_active_user)):
    """Retorna la lista de bancos de PayU."""
    banks = PayUService.get_banks()
    if not banks:
        raise HTTPException(
            status_code=503,
            detail="No se pudo obtener la lista de bancos desde PayU.",
        )
    return banks


@router.post("/init-payu-pse")
def init_recharge(
    request: Request,
    payload: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    """Alias legacy de /payments/init. Se retira tras actualizar el frontend."""
    crud_payment_gateway.seed_gateway_settings(db)
    get_active_provider(db)

    card_uid = str(payload.get("card_uid") or "").strip()
    if not card_uid:
        raise HTTPException(status_code=400, detail="card_uid es obligatorio")

    card = require_rechargeable_card(db, card_uid, current_user)

    result = start_payu_payment(
        db=db,
        card=card,
        amount=payload.get("amount"),
        buyer={
            **payload,
            "buyer_name": current_user.full_name,
            "buyer_email": payload.get("buyer_email") or current_user.email,
        },
        client_ip=request.headers.get("X-Real-IP")
        or (request.client.host if request.client else "0.0.0.0"),
        user_agent=request.headers.get("User-Agent") or "Unknown",
    )

    return {
        "redirect_url": result.redirect_url,
        "reference": result.reference,
    }


@router.post("/payu-confirmation")
async def payu_confirmation(request: Request, db: Session = Depends(get_db)):
    """Alias legacy del webhook. Retirar después de actualizar PayU."""
    return await handle_payu_notification_request(request, db)


@router.get("/status/{reference_code}")
def get_recharge_status(
    reference_code: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user),
):
    return get_payment_status(db, current_user, reference_code)
