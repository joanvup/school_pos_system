from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.card import Card, Transaction, TransactionDetail, TransactionType, CardStatus
from app.models.product import Product
from app.schemas.sale import SaleCreate

def process_sale(db: Session, sale_in: SaleCreate):
    # 1. Buscar y Validar Tarjeta
    card = db.query(Card).filter(Card.uid == sale_in.card_uid).first()
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
    
    if card.status != CardStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="La tarjeta está bloqueada o inactiva")

    # 2. Validar Productos, Calcular Total y Verificar Stock
    total_amount = 0.0
    transaction_details = []
    products_to_update = []

    for item in sale_in.items:
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Producto ID {item.product_id} no encontrado")
        
        if not product.is_active:
             raise HTTPException(status_code=400, detail=f"El producto '{product.name}' no está disponible para la venta")

        if product.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"Stock insuficiente para '{product.name}'. Disponible: {product.stock}")

        # Cálculos
        subtotal = product.price * item.quantity
        total_amount += subtotal
        
        # Preparamos el detalle (snapshot del precio actual)
        detail = TransactionDetail(
            transaction_id=db_transaction.id, # Se asignará después o mediante flush
            product_id=product.id,    # <--- ¡ASEGÚRATE DE AGREGAR ESTA LÍNEA!
            product_name=product.name,
            quantity=item.quantity,
            unit_price=product.price,
            subtotal=subtotal
        )
        transaction_details.append(detail)
        
        # Preparamos actualización de stock (pero no guardamos todavía)
        products_to_update.append((product, item.quantity))

    # 3. Validar Saldo Suficiente
    if card.balance < total_amount:
        raise HTTPException(status_code=400, detail=f"Saldo insuficiente. Saldo: ${card.balance}, Total: ${total_amount}")

    # --- INICIO DE LA TRANSACCIÓN ATÓMICA ---
    try:
        # A. Crear Transacción Padre
        db_transaction = Transaction(
            card_id=card.id,
            amount=-total_amount, # Negativo porque es gasto
            type=TransactionType.PURCHASE,
            description="Compra en Cafetería"
        )
        db.add(db_transaction)
        db.flush() # Para obtener el ID de la transacción antes del commit final

        # B. Guardar Detalles
        for detail in transaction_details:
            detail.transaction_id = db_transaction.id
            db.add(detail)

        # C. Actualizar Stock
        for product, qty in products_to_update:
            product.stock -= qty
            db.add(product)

        # D. Descontar Saldo Tarjeta
        card.balance -= total_amount
        db.add(card)

        # E. Confirmar todo
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
        db.rollback() # Si algo falla, deshacer todo
        raise HTTPException(status_code=500, detail=f"Error procesando la venta: {str(e)}")