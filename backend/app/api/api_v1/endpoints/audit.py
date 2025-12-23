from fastapi import APIRouter, Depends, HTTPException
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
    payload: dict, # { "new_balance": float }
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin)
):
    success = crud_audit.update_to_correct_balance(db, card_id, payload['new_balance'])
    if not success:
        raise HTTPException(status_code=400, detail="No se pudo actualizar")
    return {"message": "Saldo corregido exitosamente"}