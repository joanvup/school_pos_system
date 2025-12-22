from sqlalchemy.orm import Session
from sqlalchemy import func
from fastapi import HTTPException
from datetime import datetime
from app.models.card import Card, Transaction, TransactionDetail, TransactionType, CardStatus
from app.models.product import Product
from app.models.user import User

def process_sale(db: Session, sale_in: dict):
    # 1. Buscar y Validar Tarjeta
    card = db.query(Card).filter(Card.uid == sale_in.card_uid).first()
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
    
    if card.status != CardStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="La tarjeta está bloqueada o inactiva")

    # 2. PRE-VALIDACIÓN: Validar Stock y Calcular Total
    # Recopilamos los datos en una lista para no tocar la BD aún
    total_amount = 0.0
    items_to_process = []

    for item in sale_in.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Producto ID {item.product_id} no encontrado")
        
        if product.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para {product.name}")

        subtotal = product.price * item.quantity
        total_amount += subtotal
        
        # Guardamos el objeto producto y la cantidad para el paso final
        items_to_process.append({
            "product": product,
            "quantity": item.quantity,
            "unit_price": product.price,
            "subtotal": subtotal
        })

    # 3. Validar Saldo Suficiente
    if card.balance < total_amount:
        raise HTTPException(status_code=400, detail="Saldo insuficiente en la tarjeta")

    # 4. Validar Cupo Diario (Opcional si lo implementaste)
    if card.daily_limit and card.daily_limit > 0:
        today = datetime.now().date()
        spent_today = db.query(func.sum(func.abs(Transaction.amount))).filter(
            Transaction.card_id == card.id,
            Transaction.type == TransactionType.PURCHASE,
            func.date(Transaction.timestamp) == today
        ).scalar() or 0.0
        
        if (spent_today + total_amount) > card.daily_limit:
            raise HTTPException(status_code=400, detail="Supera el cupo diario permitido")

    # --- INICIO DE LA TRANSACCIÓN EN BASE DE DATOS ---
    try:
        # A. Crear la cabecera de la Transacción
        db_transaction = Transaction(
            card_id=card.id,
            amount=-total_amount, # Negativo porque es un gasto
            type=TransactionType.PURCHASE,
            description="Compra en Cafetería"
        )
        db.add(db_transaction)
        db.flush() # <--- CRÍTICO: Esto genera el ID de la transacción sin cerrar la sesión

        # B. Crear los detalles y actualizar stock
        for item in items_to_process:
            product = item["product"]
            
            # Crear detalle de venta
            detail = TransactionDetail(
                transaction_id=db_transaction.id, # Ahora sí el ID existe
                product_id=product.id,            # Guardamos el ID para reportes
                product_name=product.name,
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                subtotal=item["subtotal"]
            )
            db.add(detail)
            
            # Restar del inventario
            product.stock -= item["quantity"]
            db.add(product)

        # C. Descontar saldo de la tarjeta
        card.balance -= total_amount
        db.add(card)

        # D. Confirmar todo el bloque
        db.commit()
        db.refresh(db_transaction)
        db.refresh(card)

        return {
            "transaction_id": db_transaction.id,
            "total_amount": total_amount,
            "new_balance": card.balance,
            "timestamp": db_transaction.timestamp
        }

    except Exception as e:
        db.rollback()
        print(f"ERROR EN VENTA: {str(e)}")
        raise HTTPException(status_code=500, detail="Error interno procesando la venta")

def reverse_sale(db: Session, transaction_id: int):
    tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
    if not tx:
        raise HTTPException(status_code=404, detail="Venta no encontrada")
    if tx.status == "reversed":
        raise HTTPException(status_code=400, detail="Esta venta ya fue reversada")
    if tx.type != TransactionType.PURCHASE:
        raise HTTPException(status_code=400, detail="Solo se pueden reversar compras")

    try:
        # 1. Devolver Stock
        for detail in tx.details:
            product = db.query(Product).filter(Product.id == detail.product_id).first()
            if product:
                product.stock += detail.quantity
                db.add(product)

        # 2. Reembolsar Saldo
        card = tx.card
        card.balance += abs(tx.amount)
        db.add(card)

        # 3. Marcar como reversada
        tx.status = "reversed"
        db.add(tx)
        
        db.commit()
        return tx
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))