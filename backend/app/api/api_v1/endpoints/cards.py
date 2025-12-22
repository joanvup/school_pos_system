from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Any

from app.db.session import get_db
from app.schemas.card import CardCreate, CardResponse, CardUpdate
from app.crud import crud_card, crud_student, crud_audit
from app.api import deps
from app.models.user import User

from typing import List, Optional
from app.models.card import Transaction

from pydantic import BaseModel
from datetime import datetime

# Sub-schema para los productos individuales
class TransactionDetailResponse(BaseModel):
    product_name: str
    quantity: int
    unit_price: float
    subtotal: float

    class Config:
        from_attributes = True

# Schema principal actualizado
class TransactionHistory(BaseModel):
    id: int
    timestamp: datetime
    amount: float
    type: str
    description: Optional[str] = None
    # CAMPO NUEVO: Lista de productos
    details: List[TransactionDetailResponse] = [] 

    class Config:
        from_attributes = True

router = APIRouter()

@router.post("/", response_model=CardResponse)
def assign_card(
    card: CardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin)
):
    """
    Asignar una tarjeta nueva a un estudiante o empleado.
    """
    # 1. Verificar si la tarjeta ya existe (el plástico físico)
    existing_card = crud_card.get_card_by_uid(db, uid=card.uid)
    if existing_card:
        raise HTTPException(status_code=400, detail="Esta tarjeta ya está registrada en el sistema.")

    # 2. Verificar que el estudiante exista (si aplica)
    if card.student_id:
        student = crud_student.get_student(db, student_id=card.student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Estudiante no encontrado.")
        # Verificar si el estudiante ya tiene tarjeta
        if student.card:
             raise HTTPException(status_code=400, detail="Este estudiante ya tiene una tarjeta asignada.")

    return crud_card.create_card(db=db, card=card)

@router.get("/check/{uid}") # Quitamos response_model temporalmente para enviar un dict personalizado
def check_card_status(
    uid: str,
    db: Session = Depends(get_db)
):
    card = crud_card.get_card_by_uid(db, uid=uid)
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
    
    # Construimos la respuesta a mano para el POS
    # Esto es 100% seguro y evita cualquier bucle de Pydantic
    owner_name = "Desconocido"
    owner_type = "N/A"
    
    if card.student:
        owner_name = card.student.full_name
        owner_type = f"Estudiante - {card.student.grade}"
    elif card.employee:
        owner_name = card.employee.full_name
        owner_type = "Personal Staff"

    return {
        "uid": card.uid,
        "balance": card.balance,
        "status": card.status,
        "owner_name": owner_name,
        "owner_type": owner_type
    }

@router.put("/{uid}", response_model=CardResponse)
def update_card_status(
    uid: str,
    card_in: CardUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Bloquear/Desbloquear tarjeta o cambiar límite diario.
    """
    card = crud_card.get_card_by_uid(db, uid=uid)
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada.")

    # --- LÓGICA DE PERMISOS CORREGIDA ---
    is_authorized = False

    # 1. Es Admin
    if current_user.role == "admin":
        is_authorized = True
    
    # 2. Es MI tarjeta (Caso Empleado)
    elif card.user_id == current_user.id:
        is_authorized = True
        
    # 3. Es la tarjeta de MI hijo (Caso Padre)
    elif card.student and card.student.parent_id == current_user.id:
        is_authorized = True

    if not is_authorized:
         raise HTTPException(status_code=403, detail="No tienes permiso sobre esta tarjeta.")
    # ------------------------------------

    # --- INYECCIÓN DE AUDITORÍA (Mantenemos lo que ya tenías) ---
    details = f"Cambio de estado: {card.status} -> {card_in.status if card_in.status else 'Sin cambio'}. " 
    crud_audit.log_action(
        db=db,
        user_id=current_user.id,
        action="UPDATE_CARD",
        details=f"Tarjeta UID {uid}. {details}"
    )
    # -----------------------------------------------------------

    return crud_card.update_card(db, db_card=card, card_in=card_in)


@router.get("/{card_uid}/history", response_model=List[TransactionHistory])
def read_card_history(
    card_uid: str,
    skip: int = 0,   # <--- NUEVO PARAMETRO
    limit: int = 20, # <--- Defecto bajo para carga rápida
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user)
):
    """
    Obtener historial paginado.
    """
    card = crud_card.get_card_by_uid(db, uid=card_uid)
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")

    # ... (Mantener la lógica de verificación de permisos igual) ...
    is_authorized = False
    if current_user.role == "admin":
        is_authorized = True
    elif card.user_id == current_user.id: 
        is_authorized = True
    elif card.student and card.student.parent_id == current_user.id: 
        is_authorized = True
        
    if not is_authorized:
        raise HTTPException(status_code=403, detail="No autorizado")

    # CONSULTA OPTIMIZADA CON OFFSET
    history = db.query(Transaction)\
        .filter(Transaction.card_id == card.id)\
        .order_by(Transaction.timestamp.desc())\
        .offset(skip)\
        .limit(limit)\
        .all()
        
    return history