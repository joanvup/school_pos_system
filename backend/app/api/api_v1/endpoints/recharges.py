from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.recharge import RechargeCreate, RechargeResponse
from app.crud import crud_transaction, crud_card
from app.api import deps
from app.models.user import User, UserRole

router = APIRouter()

@router.post("/simulate-pse", response_model=RechargeResponse)
def simulate_pse_recharge(
    recharge: RechargeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Simula una transacción aprobada por PSE.
    Validaciones:
    - Admin: Puede recargar cualquiera.
    - Empleado: Solo su propia tarjeta.
    - Padre: Solo tarjetas de sus hijos.
    """
    
    # 1. Obtener la tarjeta para validar permisos
    card = crud_card.get_card_by_uid(db, uid=recharge.card_uid)
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")

    # 2. Validar Permisos
    is_authorized = False

    if current_user.role == UserRole.ADMIN:
        is_authorized = True
    
    elif current_user.role == UserRole.EMPLEADO:
        # Verificar si la tarjeta es del empleado
        if card.user_id == current_user.id:
            is_authorized = True
            
    elif current_user.role == UserRole.PADRE:
        # Verificar si la tarjeta pertenece a un estudiante de este padre
        if card.student and card.student.parent_id == current_user.id:
            is_authorized = True

    if not is_authorized:
        raise HTTPException(
            status_code=403, 
            detail="No tienes permiso para recargar esta tarjeta."
        )

    # 3. Procesar Recarga
    return crud_transaction.recharge_card(db=db, recharge=recharge)