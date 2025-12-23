from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.purchase import PurchaseOrderCreate, PurchaseOrderResponse
from app.crud import crud_purchase
from app.api import deps
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=PurchaseOrderResponse)
def create_order(
    order: PurchaseOrderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_or_supervisor)
):
    """Crear orden de entrada de mercancía (Suma Stock)"""
    return crud_purchase.create_purchase_order(db, order, current_user.id)

@router.get("/", response_model=List[PurchaseOrderResponse])
def read_orders(
    skip: int = 0, limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_admin_or_supervisor)
):
    return crud_purchase.get_orders(db, skip, limit)

@router.delete("/{order_id}", response_model=PurchaseOrderResponse)
def cancel_order(
    order_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin)
):
    """Anular orden (Resta Stock si es posible)"""
    return crud_purchase.cancel_purchase_order(db, order_id)