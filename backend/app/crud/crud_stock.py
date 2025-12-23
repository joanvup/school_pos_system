import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.stock_adjustment import StockAdjustment, StockAdjustmentDetail
from app.models.product import Product

def create_adjustment(db: Session, user_id: int, reason: str, items: list):
    code = f"ADJ-{uuid.uuid4().hex[:6].upper()}"
    
    db_adj = StockAdjustment(code=code, user_id=user_id, reason=reason)
    db.add(db_adj)
    db.flush()

    for item in items:
        product = db.query(Product).filter(Product.id == item['product_id']).first()
        if not product: continue

        # Aplicar cambio al stock (Suma algebraicamente)
        # Si quantity es -5, resta. Si es 5, suma.
        product.stock += item['quantity']
        
        # Validar que no quede stock negativo por un ajuste manual erróneo
        if product.stock < 0:
            db.rollback()
            raise HTTPException(status_code=400, detail=f"El ajuste dejaría a {product.name} con stock negativo.")

        detail = StockAdjustmentDetail(
            adjustment_id=db_adj.id,
            product_id=product.id,
            quantity=item['quantity']
        )
        db.add(detail)
        db.add(product)

    db.commit()
    db.refresh(db_adj)
    return db_adj