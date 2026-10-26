import uuid
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.crud.crud_audit import log_action
from app.models.product import Product
from app.models.purchase import OrderStatus, PurchaseOrder, PurchaseOrderDetail
from app.schemas.purchase import PurchaseOrderCreate


def create_purchase_order(db: Session, order_in: PurchaseOrderCreate, user_id: int):
    product_ids = [item.product_id for item in order_in.items]
    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(status_code=400, detail="Hay productos duplicados en la orden")

    try:
        ordered_ids = sorted(set(product_ids))
        products = (
            db.query(Product)
            .filter(Product.id.in_(ordered_ids))
            .order_by(Product.id)
            .with_for_update()
            .all()
        )
        products_by_id = {product.id: product for product in products}

        for product_id in ordered_ids:
            if product_id not in products_by_id:
                raise HTTPException(
                    status_code=404, detail=f"Producto ID {product_id} no existe"
                )

        code = f"OC-{uuid.uuid4().hex[:6].upper()}"
        db_order = PurchaseOrder(
            code=code,
            user_id=user_id,
            status=OrderStatus.COMPLETED,
            total_cost=Decimal("0.00"),
        )
        db.add(db_order)
        db.flush()

        total_cost = Decimal("0.00")
        for item in order_in.items:
            product = products_by_id[item.product_id]
            unit_cost = Decimal(item.unit_cost).quantize(Decimal("0.01"))

            db.add(
                PurchaseOrderDetail(
                    order_id=db_order.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_cost=unit_cost,
                )
            )

            product.stock += item.quantity
            product.cost = unit_cost
            total_cost += unit_cost * item.quantity

        db_order.total_cost = total_cost.quantize(Decimal("0.01"))

        log_action(
            db=db,
            user_id=user_id,
            action="CREATE_PURCHASE_ORDER",
            entity="purchase_order",
            entity_id=db_order.id,
            details=f"Orden {db_order.code} por {db_order.total_cost}",
            commit=False,
        )

        db.commit()
        db.refresh(db_order)
        return db_order
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno creando la orden")


def cancel_purchase_order(db: Session, order_id: int, actor_id: int):
    try:
        order = (
            db.query(PurchaseOrder)
            .filter(PurchaseOrder.id == order_id)
            .with_for_update()
            .first()
        )
        if not order:
            raise HTTPException(status_code=404, detail="Orden no encontrada")
        if order.status == OrderStatus.CANCELLED:
            raise HTTPException(status_code=400, detail="La orden ya está anulada")

        details = list(order.details)
        product_ids = sorted(
            {detail.product_id for detail in details if detail.product_id is not None}
        )
        products = (
            db.query(Product)
            .filter(Product.id.in_(product_ids))
            .order_by(Product.id)
            .with_for_update()
            .all()
            if product_ids
            else []
        )
        products_by_id = {product.id: product for product in products}

        for detail in details:
            product = products_by_id.get(detail.product_id)
            if not product:
                raise HTTPException(
                    status_code=400,
                    detail="No se puede anular: producto de la orden no encontrado",
                )
            if product.stock < detail.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"No se puede anular: El producto '{product.name}' ya ha sido vendido. "
                        f"Stock actual: {product.stock}, Intentas retirar: {detail.quantity}"
                    ),
                )

        for detail in details:
            products_by_id[detail.product_id].stock -= detail.quantity

        order.status = OrderStatus.CANCELLED

        log_action(
            db=db,
            user_id=actor_id,
            action="CANCEL_PURCHASE_ORDER",
            entity="purchase_order",
            entity_id=order.id,
            details=f"Anulación de orden {order.code}",
            commit=False,
        )

        db.commit()
        db.refresh(order)
        return order
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno anulando la orden")


def get_orders(db: Session, skip: int = 0, limit: int = 100):
    return (
        db.query(PurchaseOrder)
        .order_by(PurchaseOrder.timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
