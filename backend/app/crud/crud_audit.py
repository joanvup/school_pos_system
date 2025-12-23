from sqlalchemy.orm import Session
from app.models.card import AuditLog
from sqlalchemy import func
from app.models.card import Card, Transaction, TransactionType

def log_action(db: Session, user_id: int, action: str, details: str):
    """
    Registra una acción en la tabla de auditoría.
    Ej: User 1 (Admin) ACTION: UPDATE_CARD DETAILS: Bloqueó tarjeta ABC
    """
    try:
        log = AuditLog(
            user_id=user_id,
            action=action,
            details=details
        )
        db.add(log)
        db.commit()
    except Exception as e:
        # Si falla el log, no deberíamos detener la operación principal, 
        # pero sí imprimirlo en consola.
        print(f"ERROR AUDITORIA: {e}")

def reconcile_card_balance(db: Session, card_id: int):
    """
    Recalcula el saldo real basado en transacciones y lo compara con el saldo actual.
    """
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        return None

    # 1. Obtener saldo inicial (asumimos 0 si no hay registro de apertura, 
    # o podrías tener una transacción tipo 'initial_load')
    
    # 2. Sumar todas las recargas aprobadas (Positivas)
    total_recharges = db.query(func.sum(Transaction.amount)).filter(
        Transaction.card_id == card.id,
        Transaction.type == TransactionType.RECHARGE,
        Transaction.status == "approved"
    ).scalar() or 0.0

    # 3. Sumar todos los consumos no reversados (Negativos)
    total_purchases = db.query(func.sum(Transaction.amount)).filter(
        Transaction.card_id == card.id,
        Transaction.type == TransactionType.PURCHASE,
        Transaction.status != "reversed"
    ).scalar() or 0.0

    # 4. Saldo Matemático Real
    calculated_balance = float(total_recharges) + float(total_purchases)
    current_stored_balance = float(card.balance)
    discrepancy = calculated_balance - current_stored_balance

    return {
        "stored_balance": current_stored_balance,
        "calculated_balance": calculated_balance,
        "discrepancy": discrepancy,
        "recharges_count": db.query(Transaction).filter(Transaction.card_id == card.id, Transaction.type == TransactionType.RECHARGE).count(),
        "purchases_count": db.query(Transaction).filter(Transaction.card_id == card.id, Transaction.type == TransactionType.PURCHASE).count()
    }

def update_to_correct_balance(db: Session, card_id: int, new_balance: float):
    """Aplica el recalculo a la base de datos"""
    card = db.query(Card).filter(Card.id == card_id).first()
    if card:
        card.balance = new_balance
        db.commit()
        return True
    return False