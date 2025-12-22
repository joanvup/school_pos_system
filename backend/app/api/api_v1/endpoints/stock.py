from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api import deps
from app.models.user import User, UserRole
from app.crud import crud_stock

router = APIRouter()

@router.post("/")
def make_adjustment(
    payload: dict, # {reason: str, items: [{product_id, quantity}]}
    db: Session = Depends(get_db),
    current_user: User = Depends(deps.get_current_active_admin) # EXCLUSIVO ADMIN
):
    return crud_stock.create_adjustment(
        db, 
        user_id=current_user.id, 
        reason=payload['reason'], 
        items=payload['items']
    )

@router.get("/")
def get_adjustments(db: Session = Depends(get_db), current_user: User = Depends(deps.get_current_active_admin)):
    from app.models.stock_adjustment import StockAdjustment
    return db.query(StockAdjustment).order_by(StockAdjustment.timestamp.desc()).all()