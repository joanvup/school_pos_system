from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.sale import SaleCreate, SaleResponse
from app.crud import crud_sale
from app.api import deps
from app.models.user import User
from app.models.card import Card, Transaction, TransactionDetail, TransactionType, CardStatus
from typing import List, Any 

router = APIRouter()

@router.post("/", response_model=SaleResponse)
def create_sale(
    sale_in: SaleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_user) # Vendedores pueden vender
):
    """
    Registrar una nueva venta (Cobro con tarjeta RFID).
    Requiere tarjeta activa y saldo suficiente.
    """
    return crud_sale.process_sale(db=db, sale_in=sale_in)

@router.get("/recent", response_model=List[dict])
def get_recent_sales(db: Session = Depends(get_db)):
    """Obtiene las últimas 5 ventas para el POS"""
    sales = db.query(Transaction).filter(Transaction.type == TransactionType.PURCHASE)\
              .order_by(Transaction.timestamp.desc()).limit(5).all()
    return [{
        "id": s.id,
        "timestamp": s.timestamp,
        "amount": abs(s.amount),
        "comprador": s.card.student.full_name if s.card.student else s.card.employee.full_name,
        "status": s.status
    } for s in sales]

@router.post("/reverse/{transaction_id}")
def void_sale(transaction_id: int, db: Session = Depends(get_db), current_user: User = Depends(deps.get_current_active_admin)):
    """Solo Admins pueden reversar"""
    return crud_sale.reverse_sale(db, transaction_id)