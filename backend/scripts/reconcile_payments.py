"""Reconciliación de solo lectura para recargas PayU.

Reporta:
  - recargas pendientes con más de 15 minutos
  - recargas aprobadas sin crédito aplicado
  - recargas aprobadas con credited_at pero sin monto consistente
  - tarjetas con saldo negativo (no debería ocurrir por constraints)

Uso: python -m scripts.reconcile_payments
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import or_

from app.db.session import SessionLocal
from app.models.card import Card, Transaction, TransactionStatus, TransactionType


def main() -> int:
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(minutes=15)
    problems = 0

    with SessionLocal() as db:
        stale_pending = (
            db.query(Transaction)
            .filter(
                Transaction.type == TransactionType.RECHARGE,
                Transaction.status == TransactionStatus.PENDING.value,
                Transaction.timestamp < cutoff,
            )
            .all()
        )
        approved_without_credit = (
            db.query(Transaction)
            .filter(
                Transaction.type == TransactionType.RECHARGE,
                Transaction.status == TransactionStatus.APPROVED.value,
                Transaction.credited_at.is_(None),
            )
            .all()
        )
        approved_inconsistent = (
            db.query(Transaction)
            .filter(
                Transaction.type == TransactionType.RECHARGE,
                Transaction.status == TransactionStatus.APPROVED.value,
                Transaction.credited_at.isnot(None),
                or_(Transaction.amount <= 0, Transaction.reference_code.is_(None)),
            )
            .all()
        )
        negative_cards = db.query(Card).filter(Card.balance < 0).all()

        for tx in stale_pending:
            problems += 1
            print(
                f"[RECON][PENDIENTE] ref={tx.reference_code} monto={tx.amount} "
                f"creada={tx.timestamp}"
            )
        for tx in approved_without_credit:
            problems += 1
            print(
                f"[RECON][SIN CREDITO] ref={tx.reference_code} monto={tx.amount} "
                f"cus={tx.cus}"
            )
        for tx in approved_inconsistent:
            problems += 1
            print(
                f"[RECON][INCONSISTENTE] ref={tx.reference_code} monto={tx.amount} "
                f"credited_at={tx.credited_at}"
            )
        for card in negative_cards:
            problems += 1
            print(f"[RECON][SALDO NEGATIVO] card_id={card.id} saldo={card.balance}")

    print(f"[RECON] Hallazgos: {problems}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
