import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud.crud_audit import log_action
from app.models.product import Product
from app.models.stock_adjustment import StockAdjustment, StockAdjustmentDetail


def create_adjustment(db: Session, user_id: int, reason: str, items: list):
    if not reason or not str(reason).strip():
        raise HTTPException(status_code=400, detail="El motivo del ajuste es obligatorio")
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail="El ajuste no tiene productos")

    normalized = []
    seen = set()
    for item in items:
        try:
            product_id = int(item["product_id"])
            quantity = int(item["quantity"])
        except (KeyError, TypeError, ValueError):
            raise HTTPException(status_code=400, detail="Ítem de ajuste inválido")
        if product_id <= 0 or quantity == 0:
            raise HTTPException(
                status_code=400, detail="Producto y cantidad del ajuste deben ser válidos"
            )
        if product_id in seen:
            raise HTTPException(
                status_code=400, detail="Hay productos duplicados en el ajuste"
            )
        seen.add(product_id)
        normalized.append((product_id, quantity))

    try:
        ordered_ids = sorted(seen)
        products = (
            db.query(Product)
            .filter(Product.id.in_(ordered_ids))
            .order_by(Product.id)
            .with_for_update()
            .all()
        )
        products_by_id = {product.id: product for product in products}

        for product_id, _ in normalized:
            if product_id not in products_by_id:
                raise HTTPException(
                    status_code=404, detail=f"Producto ID {product_id} no encontrado"
                )

        for product_id, quantity in normalized:
            product = products_by_id[product_id]
            if product.stock + quantity < 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"El ajuste dejaría a {product.name} con stock negativo.",
                )

        code = f"ADJ-{uuid.uuid4().hex[:6].upper()}"
        db_adj = StockAdjustment(
            code=code, user_id=user_id, reason=str(reason).strip()
        )
        db.add(db_adj)
        db.flush()

        for product_id, quantity in normalized:
            product = products_by_id[product_id]
            product.stock += quantity
            db.add(
                StockAdjustmentDetail(
                    adjustment_id=db_adj.id,
                    product_id=product.id,
                    quantity=quantity,
                )
            )

        log_action(
            db=db,
            user_id=user_id,
            action="STOCK_ADJUSTMENT",
            entity="stock_adjustment",
            entity_id=db_adj.id,
            details=f"Ajuste {code}: {str(reason).strip()}",
            commit=False,
        )

        db.commit()
        db.refresh(db_adj)
        return db_adj
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno en el ajuste de stock")
