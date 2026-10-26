"""Ventas, reversos, compras y ajustes atómicos (WP4)."""
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.crud import crud_purchase, crud_sale, crud_stock
from app.models.card import Transaction, TransactionDetail, TransactionStatus
from app.models.purchase import OrderStatus
from app.models.user import UserRole
from app.schemas.purchase import PurchaseOrderCreate
from app.schemas.sale import SaleCreate

API = "/api/v1"


def make_sale(card, items):
    return SaleCreate(
        card_uid=card.uid,
        items=[{"product_id": product.id, "quantity": qty} for product, qty in items],
    )


def test_sale_debits_balance_and_stock(db, family_factory, product_factory, user_factory):
    seller = user_factory(role=UserRole.VENDEDOR)
    _, _, card = family_factory(balance="10000.00")
    product = product_factory(price="2500.00", stock=10)

    result = crud_sale.process_sale(db, make_sale(card, [(product, 2)]), actor_id=seller.id)

    db.refresh(card)
    db.refresh(product)
    tx = db.query(Transaction).filter(Transaction.id == result["transaction_id"]).one()
    detail = db.query(TransactionDetail).filter(
        TransactionDetail.transaction_id == tx.id
    ).one()

    assert tx.status == TransactionStatus.COMPLETED.value
    assert tx.amount == Decimal("-5000.00")
    assert detail.quantity == 2
    assert detail.subtotal == Decimal("5000.00")
    assert card.balance == Decimal("5000.00")
    assert product.stock == 8


def test_sale_with_insufficient_balance_rolls_back(
    db, family_factory, product_factory, user_factory
):
    seller = user_factory(role=UserRole.VENDEDOR)
    _, _, card = family_factory(balance="1000.00")
    product = product_factory(price="2500.00", stock=10)

    with pytest.raises(HTTPException) as error:
        crud_sale.process_sale(db, make_sale(card, [(product, 2)]), actor_id=seller.id)

    assert error.value.status_code == 400
    db.refresh(card)
    db.refresh(product)
    assert card.balance == Decimal("1000.00")
    assert product.stock == 10
    assert db.query(Transaction).count() == 0


def test_sale_with_insufficient_stock_is_rejected(
    db, family_factory, product_factory, user_factory
):
    seller = user_factory(role=UserRole.VENDEDOR)
    _, _, card = family_factory(balance="10000.00")
    product = product_factory(price="2500.00", stock=1)

    with pytest.raises(HTTPException) as error:
        crud_sale.process_sale(db, make_sale(card, [(product, 2)]), actor_id=seller.id)

    assert error.value.status_code == 400
    db.refresh(card)
    db.refresh(product)
    assert card.balance == Decimal("10000.00")
    assert product.stock == 1


def test_sale_rejects_duplicate_products(
    db, family_factory, product_factory, user_factory
):
    seller = user_factory(role=UserRole.VENDEDOR)
    _, _, card = family_factory(balance="10000.00")
    product = product_factory(price="1000.00", stock=10)

    sale = SaleCreate(
        card_uid=card.uid,
        items=[
            {"product_id": product.id, "quantity": 1},
            {"product_id": product.id, "quantity": 1},
        ],
    )
    with pytest.raises(HTTPException) as error:
        crud_sale.process_sale(db, sale, actor_id=seller.id)
    assert error.value.status_code == 400


def test_sale_respects_daily_limit(db, family_factory, product_factory, user_factory):
    seller = user_factory(role=UserRole.VENDEDOR)
    _, _, card = family_factory(balance="10000.00", daily_limit="3000.00")
    product = product_factory(price="2500.00", stock=10)

    with pytest.raises(HTTPException) as error:
        crud_sale.process_sale(db, make_sale(card, [(product, 2)]), actor_id=seller.id)

    assert error.value.status_code == 400
    assert "cupo diario" in error.value.detail.lower()


def test_reverse_sale_restores_balance_and_stock(
    db, family_factory, product_factory, user_factory
):
    seller = user_factory(role=UserRole.VENDEDOR)
    admin = user_factory(role=UserRole.ADMIN)
    _, _, card = family_factory(balance="10000.00")
    product = product_factory(price="2500.00", stock=10)

    result = crud_sale.process_sale(db, make_sale(card, [(product, 2)]), actor_id=seller.id)
    tx = crud_sale.reverse_sale(db, result["transaction_id"], actor_id=admin.id)

    db.refresh(card)
    db.refresh(product)
    assert tx.status == TransactionStatus.REVERSED.value
    assert tx.reversed_at is not None
    assert tx.reversed_by_id == admin.id
    assert card.balance == Decimal("10000.00")
    assert product.stock == 10


def test_double_reverse_restores_only_once(
    db, family_factory, product_factory, user_factory
):
    seller = user_factory(role=UserRole.VENDEDOR)
    admin = user_factory(role=UserRole.ADMIN)
    _, _, card = family_factory(balance="10000.00")
    product = product_factory(price="2500.00", stock=10)

    result = crud_sale.process_sale(db, make_sale(card, [(product, 2)]), actor_id=seller.id)
    crud_sale.reverse_sale(db, result["transaction_id"], actor_id=admin.id)

    with pytest.raises(HTTPException) as error:
        crud_sale.reverse_sale(db, result["transaction_id"], actor_id=admin.id)
    assert error.value.status_code == 400

    db.refresh(card)
    db.refresh(product)
    assert card.balance == Decimal("10000.00")
    assert product.stock == 10


def test_parent_cannot_sell(client, family_factory, product_factory, auth_headers):
    parent, _, card = family_factory(balance="10000.00")
    product = product_factory()

    response = client.post(
        f"{API}/sales/",
        json={"card_uid": card.uid, "items": [{"product_id": product.id, "quantity": 1}]},
        headers=auth_headers(parent),
    )
    assert response.status_code == 403


def test_seller_can_sell_but_not_reverse(
    client, family_factory, product_factory, user_factory, auth_headers
):
    seller = user_factory(role=UserRole.VENDEDOR)
    _, _, card = family_factory(balance="10000.00")
    product = product_factory(price="2500.00", stock=10)

    response = client.post(
        f"{API}/sales/",
        json={"card_uid": card.uid, "items": [{"product_id": product.id, "quantity": 2}]},
        headers=auth_headers(seller),
    )
    assert response.status_code == 200
    transaction_id = response.json()["transaction_id"]

    reverse = client.post(
        f"{API}/sales/reverse/{transaction_id}", headers=auth_headers(seller)
    )
    assert reverse.status_code == 403


def test_purchase_order_updates_stock_and_cost(
    db, product_factory, user_factory
):
    admin = user_factory(role=UserRole.ADMIN)
    product = product_factory(stock=10, cost="1000.00")

    order_in = PurchaseOrderCreate(
        items=[{"product_id": product.id, "quantity": 5, "unit_cost": "1200.50"}]
    )
    order = crud_purchase.create_purchase_order(db, order_in, user_id=admin.id)

    db.refresh(product)
    assert order.status == OrderStatus.COMPLETED
    assert order.total_cost == Decimal("6002.50")
    assert product.stock == 15
    assert product.cost == Decimal("1200.50")


def test_cancel_purchase_restores_stock(db, product_factory, user_factory):
    admin = user_factory(role=UserRole.ADMIN)
    product = product_factory(stock=10)

    order_in = PurchaseOrderCreate(
        items=[{"product_id": product.id, "quantity": 5, "unit_cost": "1200.00"}]
    )
    order = crud_purchase.create_purchase_order(db, order_in, user_id=admin.id)
    cancelled = crud_purchase.cancel_purchase_order(db, order.id, actor_id=admin.id)

    db.refresh(product)
    assert cancelled.status == OrderStatus.CANCELLED
    assert product.stock == 10


def test_cancel_purchase_fails_when_stock_was_sold(
    db, product_factory, user_factory
):
    admin = user_factory(role=UserRole.ADMIN)
    product = product_factory(stock=10)

    order_in = PurchaseOrderCreate(
        items=[{"product_id": product.id, "quantity": 5, "unit_cost": "1200.00"}]
    )
    order = crud_purchase.create_purchase_order(db, order_in, user_id=admin.id)

    product.stock = 2
    db.commit()

    with pytest.raises(HTTPException) as error:
        crud_purchase.cancel_purchase_order(db, order.id, actor_id=admin.id)
    assert error.value.status_code == 400

    db.refresh(product)
    db.refresh(order)
    assert product.stock == 2
    assert order.status == OrderStatus.COMPLETED


def test_stock_adjustment_rejects_negative_stock(
    db, product_factory, user_factory
):
    admin = user_factory(role=UserRole.ADMIN)
    product = product_factory(stock=3)

    with pytest.raises(HTTPException) as error:
        crud_stock.create_adjustment(
            db,
            user_id=admin.id,
            reason="Conteo físico",
            items=[{"product_id": product.id, "quantity": -5}],
        )
    assert error.value.status_code == 400

    db.refresh(product)
    assert product.stock == 3


def test_stock_adjustment_rejects_duplicates_and_missing_reason(
    db, product_factory, user_factory
):
    admin = user_factory(role=UserRole.ADMIN)
    product = product_factory(stock=3)

    with pytest.raises(HTTPException):
        crud_stock.create_adjustment(
            db, user_id=admin.id, reason="", items=[{"product_id": product.id, "quantity": 1}]
        )

    with pytest.raises(HTTPException):
        crud_stock.create_adjustment(
            db,
            user_id=admin.id,
            reason="Duplicado",
            items=[
                {"product_id": product.id, "quantity": 1},
                {"product_id": product.id, "quantity": 2},
            ],
        )
