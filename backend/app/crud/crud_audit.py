from decimal import Decimal, InvalidOperation

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.card import AuditLog, Card, Transaction, TransactionType


def log_action(
    db: Session,
    user_id: int,
    action: str,
    details: str,
    *,
    entity: str = None,
    entity_id: int = None,
    ip: str = None,
    commit: bool = True,
):
    """
    Registra una acción de auditoría.

    En operaciones de dinero usar commit=False para que la auditoría se
    confirme junto con el cambio de saldo/stock.
    """
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=details,
        ip=ip,
    )
    db.add(log)

    if commit:
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"ERROR AUDITORIA: {e}")

    return log


def reconcile_card_balance(db: Session, card_id: int):
    """Recalcula el saldo real basado en transacciones y lo compara con el actual."""
    card = db.query(Card).filter(Card.id == card_id).first()
    if not card:
        return None

    recharge_sum = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.card_id == card.id,
            Transaction.type == TransactionType.RECHARGE,
            Transaction.status == "approved",
            Transaction.credited_at.isnot(None),
        )
        .scalar()
        or Decimal("0.00")
    )

    purchase_sum = (
        db.query(func.sum(Transaction.amount))
        .filter(
            Transaction.card_id == card.id,
            Transaction.type == TransactionType.PURCHASE,
            Transaction.status != "reversed",
        )
        .scalar()
        or Decimal("0.00")
    )

    calculated_balance = recharge_sum + purchase_sum
    current_stored_balance = Decimal(card.balance or 0)
    discrepancy = calculated_balance - current_stored_balance

    return {
        "stored_balance": float(current_stored_balance),
        "calculated_balance": float(calculated_balance),
        "discrepancy": float(discrepancy),
        "recharges_count": db.query(Transaction)
        .filter(
            Transaction.card_id == card.id,
            Transaction.type == TransactionType.RECHARGE,
        )
        .count(),
        "purchases_count": db.query(Transaction)
        .filter(
            Transaction.card_id == card.id,
            Transaction.type == TransactionType.PURCHASE,
        )
        .count(),
    }


def update_to_correct_balance(
    db: Session,
    card_id: int,
    new_balance,
    reason: str,
    actor_id: int,
    ip: str = None,
):
    """Ajuste manual de saldo con bloqueo, motivo y auditoría en una sola transacción."""
    if not reason or not str(reason).strip():
        raise ValueError("El motivo del ajuste es obligatorio")

    try:
        target = Decimal(str(new_balance)).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Saldo inválido")

    if target < 0:
        raise ValueError("El saldo no puede ser negativo")

    card = (
        db.query(Card)
        .filter(Card.id == card_id)
        .with_for_update()
        .first()
    )
    if not card:
        return False

    previous = Decimal(card.balance or 0)
    card.balance = target

    log_action(
        db=db,
        user_id=actor_id,
        action="ADJUST_BALANCE",
        entity="card",
        entity_id=card.id,
        details=(
            f"Ajuste manual UID {card.uid}: {previous} -> {target}. "
            f"Motivo: {str(reason).strip()}"
        ),
        ip=ip,
        commit=False,
    )

    db.commit()
    db.refresh(card)
    return True
