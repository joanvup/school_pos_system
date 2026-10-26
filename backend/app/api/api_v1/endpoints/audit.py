from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api import deps
from app.models.user import User
from app.crud import crud_audit

router = APIRouter()

@router.get("/reconcile/{card_id}")
def audit_card(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin) # EXCLUSIVO ADMIN
):
    result = crud_audit.reconcile_card_balance(db, card_id)
    if not result:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
    return result

@router.post("/fix-balance/{card_id}")
def apply_fix(
    card_id: int,
    payload: dict, # { "new_balance": float, "reason": "..." }
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin)
):
    try:
        success = crud_audit.update_to_correct_balance(
            db,
            card_id,
            payload.get("new_balance"),
            payload.get("reason"),
            actor_id=current_user.id,
            ip=request.client.host if request.client else None,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if not success:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
    return {"message": "Saldo corregido exitosamente"}