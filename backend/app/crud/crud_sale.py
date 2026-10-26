from datetime import datetime, time, timedelta, timezone
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.crud.crud_audit import log_action
from app.crud.crud_card import normalize_card_uid
from app.models.card import (
    Card,
    CardStatus,
    Transaction,
    TransactionDetail,
    TransactionStatus,
    TransactionType,
)
from app.models.product import Product


def _daily_spent(db: Session, card_id: int) -> Decimal:
    local_now = datetime.now(ZoneInfo(settings.APP_TIMEZONE))
    start = datetime.combine(local_now.date(), time.min)
    end = start + timedelta(days=1)

    spent = (
        db.query(func.coalesce(func.sum(func.abs(Transaction.amount)), 0))
        .filter(
            Transaction.card_id == card_id,
            Transaction.type == TransactionType.PURCHASE,
            Transaction.status != TransactionStatus.REVERSED.value,
            Transaction.timestamp >= start,
            Transaction.timestamp < end,
        )
        .scalar()
    )
    return Decimal(spent or 0).quantize(Decimal("0.01"))


def process_sale(db: Session, sale_in, actor_id: int):
    product_ids = [item.product_id for item in sale_in.items]
    if len(product_ids) != len(set(product_ids)):
        raise HTTPException(status_code=400, detail="Hay productos duplicados en la venta")

    try:
        # 1. Bloquear la tarjeta primero.
        clean_uid = normalize_card_uid(sale_in.card_uid)
        card = (
            db.query(Card)
            .filter(Card.uid == clean_uid)
            .populate_existing()
            .with_for_update()
            .first()
        )
        if not card:
            raise HTTPException(status_code=404, detail="Tarjeta NFC no encontrada")

        if not card.student_id and not card.user_id:
            raise HTTPException(
                status_code=400,
                detail="La tarjeta no está vinculada a un estudiante ni a un empleado.",
            )
        if card.status != CardStatus.ACTIVE:
            raise HTTPException(status_code=400, detail="La tarjeta está bloqueada o inactiva")

        # 2. Bloquear productos en orden determinista para evitar deadlocks.
        ordered_ids = sorted(set(product_ids))
        products = (
            db.query(Product)
            .filter(Product.id.in_(ordered_ids))
            .order_by(Product.id)
            .populate_existing()
            .with_for_update()
            .all()
        )
        products_by_id = {product.id: product for product in products}

        total_amount = Decimal("0.00")
        items_to_process = []
        for item in sale_in.items:
            product = products_by_id.get(item.product_id)
            if not product or not product.is_active:
                raise HTTPException(
                    status_code=404,
                    detail=f"Producto ID {item.product_id} no encontrado",
                )
            if product.stock < item.quantity:
                raise HTTPException(
                    status_code=400, detail=f"Stock insuficiente para {product.name}"
                )

            unit_price = Decimal(product.price).quantize(Decimal("0.01"))
            subtotal = (unit_price * item.quantity).quantize(Decimal("0.01"))
            total_amount += subtotal

            items_to_process.append(
                {
                    "product": product,
                    "quantity": item.quantity,
                    "unit_price": unit_price,
                    "subtotal": subtotal,
                }
            )

        # 3. Validaciones con los bloqueos ya tomados.
        if total_amount <= 0:
            raise HTTPException(status_code=400, detail="El total de la venta debe ser mayor a 0")
        if Decimal(card.balance or 0) < total_amount:
            raise HTTPException(status_code=400, detail="Saldo insuficiente en la tarjeta")

        if card.daily_limit and card.daily_limit > 0:
            spent_today = _daily_spent(db, card.id)
            if spent_today + total_amount > Decimal(card.daily_limit):
                raise HTTPException(status_code=400, detail="Supera el cupo diario permitido")

        db_transaction = Transaction(
            card_id=card.id,
            amount=-total_amount,
            type=TransactionType.PURCHASE,
            description="Compra en Cafetería",
            status=TransactionStatus.COMPLETED.value,
        )
        db.add(db_transaction)
        db.flush()

        for item in items_to_process:
            product = item["product"]
            db.add(
                TransactionDetail(
                    transaction_id=db_transaction.id,
                    product_id=product.id,
                    product_name=product.name,
                    quantity=item["quantity"],
                    unit_price=item["unit_price"],
                    subtotal=item["subtotal"],
                )
            )
            product.stock -= item["quantity"]

        card.balance = Decimal(card.balance or 0) - total_amount

        log_action(
            db=db,
            user_id=actor_id,
            action="SALE",
            entity="transaction",
            entity_id=db_transaction.id,
            details=(
                f"Venta UID {card.uid} por {total_amount}. "
                f"Saldo resultante: {card.balance}"
            ),
            commit=False,
        )

        db.commit()
        db.refresh(db_transaction)
        db.refresh(card)

        return {
            "transaction_id": db_transaction.id,
            "total_amount": total_amount,
            "new_balance": card.balance,
            "timestamp": db_transaction.timestamp,
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno procesando la venta")


def reverse_sale(db: Session, transaction_id: int, actor_id: int):
    try:
        tx = db.query(Transaction).filter(Transaction.id == transaction_id).first()
        if not tx:
            raise HTTPException(status_code=404, detail="Venta no encontrada")
        if tx.type != TransactionType.PURCHASE:
            raise HTTPException(status_code=400, detail="Solo se pueden reversar compras")

        # Orden de bloqueo: tarjeta -> transacción -> productos.
        card = (
            db.query(Card)
            .filter(Card.id == tx.card_id)
            .populate_existing()
            .with_for_update()
            .first()
        )
        tx = (
            db.query(Transaction)
            .filter(Transaction.id == transaction_id)
            .populate_existing()
            .with_for_update()
            .first()
        )

        if not card or not tx:
            raise HTTPException(status_code=404, detail="Venta inconsistente")

        if tx.status == TransactionStatus.REVERSED.value:
            raise HTTPException(status_code=400, detail="Esta venta ya fue reversada")
        if tx.status != TransactionStatus.COMPLETED.value:
            raise HTTPException(status_code=400, detail="La venta no está completada")

        details = list(tx.details)
        product_ids = sorted(
            {detail.product_id for detail in details if detail.product_id is not None}
        )
        products = (
            db.query(Product)
            .filter(Product.id.in_(product_ids))
            .order_by(Product.id)
            .populate_existing()
            .with_for_update()
            .all()
            if product_ids
            else []
        )
        products_by_id = {product.id: product for product in products}

        for detail in details:
            product = products_by_id.get(detail.product_id)
            if product:
                product.stock += detail.quantity

        card.balance = Decimal(card.balance or 0) + abs(Decimal(tx.amount))
        tx.status = TransactionStatus.REVERSED.value
        tx.reversed_at = datetime.now(timezone.utc)
        tx.reversed_by_id = actor_id

        log_action(
            db=db,
            user_id=actor_id,
            action="REVERSE_SALE",
            entity="transaction",
            entity_id=tx.id,
            details=f"Reverso de venta {tx.id}. Saldo resultante: {card.balance}",
            commit=False,
        )

        db.commit()
        db.refresh(tx)
        return tx
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(status_code=500, detail="Error interno reversando la venta")
