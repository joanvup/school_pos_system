import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.purchase import PurchaseOrder, PurchaseOrderDetail, OrderStatus
from app.models.product import Product
from app.schemas.purchase import PurchaseOrderCreate

def create_purchase_order(db: Session, order_in: PurchaseOrderCreate, user_id: int):
    # 1. Crear Cabecera
    # Generamos un consecutivo simple basado en fecha o UUID corto
    code = f"OC-{uuid.uuid4().hex[:6].upper()}"
    
    db_order = PurchaseOrder(
        code=code,
        user_id=user_id,
        status=OrderStatus.COMPLETED,
        total_cost=0
    )
    db.add(db_order)
    db.flush() # Para tener el ID

    total_cost = 0.0

    # 2. Procesar Items y Actualizar Stock
    for item in order_in.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Producto ID {item.product_id} no existe")

        # Guardar detalle
        detail = PurchaseOrderDetail(
            order_id=db_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            unit_cost=item.unit_cost
        )
        db.add(detail)

        # ACTUALIZAR INVENTARIO (Sumar)
        product.stock += item.quantity
        
        # Opcional: Actualizar el costo del producto al nuevo costo de compra
        product.cost = item.unit_cost 
        
        total_cost += (item.quantity * item.unit_cost)
        db.add(product)

    # 3. Finalizar
    db_order.total_cost = total_cost
    db.commit()
    db.refresh(db_order)
    return db_order

def cancel_purchase_order(db: Session, order_id: int):
    order = db.query(PurchaseOrder).filter(PurchaseOrder.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Orden no encontrada")
    
    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(status_code=400, detail="La orden ya está anulada")

    # VALIDAR SI PODEMOS REVERTIR
    # Para cada item, verificar si hay stock suficiente para devolverlo
    for detail in order.details:
        product = db.query(Product).filter(Product.id == detail.product_id).first()
        
        # Si compramos 10, y ahora hay 5 en stock (porque vendimos 5), 
        # no podemos anular la compra de 10.
        if product.stock < detail.quantity:
             raise HTTPException(
                 status_code=400, 
                 detail=f"No se puede anular: El producto '{product.name}' ya ha sido vendido. Stock actual: {product.stock}, Intenta retirar: {detail.quantity}"
             )

    # SI PASA LA VALIDACIÓN, REVERTIMOS
    for detail in order.details:
        product = db.query(Product).filter(Product.id == detail.product_id).first()
        product.stock -= detail.quantity
        db.add(product)

    order.status = OrderStatus.CANCELLED
    db.commit()
    db.refresh(order)
    return order

def get_orders(db: Session, skip: int = 0, limit: int = 100):
    return db.query(PurchaseOrder).order_by(PurchaseOrder.timestamp.desc()).offset(skip).limit(limit).all()