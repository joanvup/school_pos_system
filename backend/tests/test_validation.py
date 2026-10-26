"""Validación de esquemas, política de contraseñas y reglas de monto."""
from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.core.config import Settings
from app.core.security import validate_password
from app.models.card import Card, CardStatus
from app.models.user import UserRole
from app.schemas.purchase import PurchaseOrderCreate
from app.schemas.sale import SaleCreate
from app.schemas.user import UserCreate
from app.services.payment_service import _validate_amount, require_rechargeable_card


@pytest.mark.parametrize("quantity", [0, -1, 101])
def test_sale_item_quantity_must_be_positive_and_bounded(quantity):
    with pytest.raises(ValidationError):
        SaleCreate(
            card_uid="UID1", items=[{"product_id": 1, "quantity": quantity}]
        )


def test_sale_requires_items_and_rejects_duplicates_at_crud():
    with pytest.raises(ValidationError):
        SaleCreate(card_uid="UID1", items=[])
    with pytest.raises(ValidationError):
        SaleCreate(
            card_uid="UID1",
            items=[{"product_id": i, "quantity": 1} for i in range(51)],
        )


@pytest.mark.parametrize("unit_cost", ["0", "-100.00"])
def test_purchase_unit_cost_must_be_positive(unit_cost):
    with pytest.raises(ValidationError):
        PurchaseOrderCreate(
            items=[{"product_id": 1, "quantity": 1, "unit_cost": unit_cost}]
        )


@pytest.mark.parametrize("quantity", [0, -5])
def test_purchase_quantity_must_be_positive(quantity):
    with pytest.raises(ValidationError):
        PurchaseOrderCreate(
            items=[{"product_id": 1, "quantity": quantity, "unit_cost": "100.00"}]
        )


@pytest.mark.parametrize(
    "password",
    ["123456", "12345678", "admin123", "empleado123", "sololetras", "12345678901"],
)
def test_weak_passwords_are_rejected(password):
    with pytest.raises(ValidationError):
        UserCreate(
            email="padre@test.local",
            full_name="Padre Test",
            role="padre",
            password=password,
        )


def test_password_longer_than_bcrypt_limit_is_rejected():
    with pytest.raises(ValueError):
        validate_password("A1" * 40)


def test_strong_password_is_accepted():
    user = UserCreate(
        email="padre@example.com",
        full_name="Padre Test",
        role="padre",
        password="ClaveSegura2026",
    )
    assert user.password == "ClaveSegura2026"


@pytest.mark.parametrize(
    ("amount", "valid"),
    [("1000.00", True), ("499999.99", True), ("999.99", False), ("500000.01", False)],
)
def test_recharge_amount_bounds(amount, valid):
    if valid:
        assert _validate_amount(amount) == Decimal(amount)
    else:
        with pytest.raises(HTTPException) as error:
            _validate_amount(amount)
        assert error.value.status_code == 400


def test_recharge_amount_rejects_three_decimals():
    with pytest.raises(HTTPException) as error:
        _validate_amount("1000.555")
    assert error.value.status_code == 400


def test_blocked_card_cannot_be_recharged(db, family_factory):
    parent, _, card = family_factory(status=CardStatus.BLOCKED)
    with pytest.raises(HTTPException) as error:
        require_rechargeable_card(db, card.uid, parent)
    assert error.value.status_code == 400


def test_unlinked_card_cannot_be_recharged(db, user_factory):
    admin = user_factory(role=UserRole.ADMIN)
    card = Card(uid="UIDUNLINKED", balance=Decimal("0.00"))
    db.add(card)
    db.commit()

    with pytest.raises(HTTPException) as error:
        require_rechargeable_card(db, card.uid, admin)
    assert error.value.status_code == 400


def test_staff_seller_cannot_recharge_a_card(db, family_factory, user_factory):
    _, _, card = family_factory()
    seller = user_factory(role=UserRole.VENDEDOR)

    with pytest.raises(HTTPException) as error:
        require_rechargeable_card(db, card.uid, seller)
    assert error.value.status_code == 403


def test_production_settings_require_hardening():
    base = dict(
        DATABASE_URL="sqlite://",
        ALGORITHM="HS256",
        ACCESS_TOKEN_EXPIRE_MINUTES=30,
        SETTINGS_ENCRYPTION_KEY="e" * 40,
        PAYU_MERCHANT_ID="m",
        PAYU_API_KEY="k",
        PAYU_API_LOGIN="l",
        PAYU_ACCOUNT_ID="a",
        PAYU_URL="https://example.test",
    )

    with pytest.raises(ValidationError):
        Settings(ENVIRONMENT="production", SECRET_KEY="short", **base)

    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="x" * 40,
            ALLOWED_ORIGINS="*",
            PUBLIC_BASE_URL="https://pos.test",
            **base,
        )

    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="x" * 40,
            ALLOWED_ORIGINS="https://pos.test",
            PUBLIC_BASE_URL="http://pos.test",
            **base,
        )

    with pytest.raises(ValidationError):
        Settings(
            ENVIRONMENT="production",
            SECRET_KEY="x" * 40,
            SETTINGS_ENCRYPTION_KEY="",
            ALLOWED_ORIGINS="https://pos.test",
            PUBLIC_BASE_URL="https://pos.test",
            **{k: v for k, v in base.items() if k != "SETTINGS_ENCRYPTION_KEY"},
        )

    hardened = Settings(
        ENVIRONMENT="production",
        SECRET_KEY="x" * 40,
        ALLOWED_ORIGINS="https://pos.test",
        PUBLIC_BASE_URL="https://pos.test/",
        **base,
    )
    assert hardened.PUBLIC_BASE_URL == "https://pos.test"
