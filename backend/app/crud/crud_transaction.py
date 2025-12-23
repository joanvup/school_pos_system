import uuid
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app.models.card import Card, Transaction, TransactionType, CardStatus
from app.schemas.recharge import RechargeCreate

def recharge_card(db: Session, recharge: RechargeCreate):
    # 1. Buscar Tarjeta
    card = db.query(Card).filter(Card.uid == recharge.card_uid).first()
    if not card:
        raise HTTPException(status_code=404, detail="Tarjeta no encontrada")
    
    # Validar monto positivo
    if recharge.amount <= 0:
        raise HTTPException(status_code=400, detail="El monto de recarga debe ser mayor a 0")

    # 2. Generar Referencia Única (Simulando lo que devuelve el Banco)
    # Ejemplo: PSE-12345678...
    reference = f"PSE-{uuid.uuid4().hex[:8].upper()}"

    try:
        # 3. Crear Transacción
        db_transaction = Transaction(
            card_id=card.id,
            amount=recharge.amount, # Positivo porque entra dinero
            type=TransactionType.RECHARGE,
            description="Recarga Online PSE",
            reference_code=reference
        )
        
        # 4. Actualizar Saldo
        card.balance += recharge.amount

        # Si la tarjeta estaba bloqueada por falta de pago (opcional), se podría activar aqui
        # if card.status == CardStatus.BLOCKED: ...

        db.add(db_transaction)
        db.add(card)
        db.commit()
        db.refresh(db_transaction)
        db.refresh(card)

        return {
            "transaction_id": db_transaction.id,
            "reference_code": reference,
            "amount": recharge.amount,
            "new_balance": card.balance,
            "timestamp": db_transaction.timestamp
        }

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error procesando recarga: {str(e)}")