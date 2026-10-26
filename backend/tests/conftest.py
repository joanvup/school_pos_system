"""Configuración común de pruebas.

Se ejecutan con SQLite en memoria: los bloqueos `FOR UPDATE` son no-op, así que
las pruebas de concurrencia deben correr contra MySQL (`TEST_DATABASE_URL`).
"""
import os
import uuid
from decimal import Decimal

# Deben definirse ANTES de importar app.* (Settings se instancia al importar).
_TEST_ENV = {
    "ENVIRONMENT": "development",
    "DATABASE_URL": "sqlite://",
    "SECRET_KEY": "test-secret-key-with-enough-length-0123456789",
    "SETTINGS_ENCRYPTION_KEY": "test-encryption-key-with-enough-length-012345",
    "ALGORITHM": "HS256",
    "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
    "ALLOWED_ORIGINS": "*",
    "PUBLIC_BASE_URL": "https://pos.test",
    "FRONTEND_URL": "https://pos.test",
    "PAYU_MERCHANT_ID": "test-merchant",
    "PAYU_API_KEY": "test-api-key",
    "PAYU_API_LOGIN": "test-login",
    "PAYU_ACCOUNT_ID": "test-account",
    "PAYU_IS_TEST": "true",
    "PAYU_URL": "https://sandbox.api.payulatam.com/payments-api/4.0/service.cgi",
    "MIN_RECHARGE_AMOUNT": "1000",
    "MAX_RECHARGE_AMOUNT": "500000",
}
os.environ.update(_TEST_ENV)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.core.security import create_access_token, get_password_hash  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.models.card import Card, CardStatus  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.models.user import Student, User, UserRole  # noqa: E402
from main import app  # noqa: E402


@pytest.fixture()
def engine():
    """Base SQLite nueva por prueba: aislamiento total sin depender de savepoints."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture()
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    TestingSession = sessionmaker(
        bind=connection, join_transaction_mode="create_savepoint"
    )
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db):
    def _override_get_db():
        yield db

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def user_factory(db):
    def make(role=UserRole.PADRE, email=None, password="Segura2026x", full_name="Usuario Test"):
        user = User(
            email=email or f"{role.value}-{uuid.uuid4().hex[:10]}@example.com",
            full_name=full_name,
            hashed_password=get_password_hash(password),
            role=role,
            is_active=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return make


@pytest.fixture()
def auth_headers():
    def make(user):
        return {
            "Authorization": (
                f"Bearer {create_access_token(user.id, user.token_version)}"
            )
        }

    return make


@pytest.fixture()
def family_factory(db, user_factory):
    """Crea padre + estudiante + tarjeta."""

    def make(
        balance="10000.00",
        daily_limit=None,
        status=CardStatus.ACTIVE,
        parent=None,
        uid=None,
    ):
        parent = parent or user_factory(role=UserRole.PADRE)
        student = Student(
            full_name=f"Estudiante {uuid.uuid4().hex[:6]}",
            grade="5-A",
            parent_id=parent.id,
        )
        db.add(student)
        db.flush()

        card = Card(
            uid=uid or f"UID{uuid.uuid4().hex[:10].upper()}",
            balance=Decimal(str(balance)),
            daily_limit=None if daily_limit is None else Decimal(str(daily_limit)),
            status=status,
            student_id=student.id,
        )
        db.add(card)
        db.commit()
        db.refresh(card)
        db.refresh(student)
        db.refresh(parent)
        return parent, student, card

    return make


@pytest.fixture()
def employee_card_factory(db, user_factory):
    """Crea empleado + tarjeta propia."""

    def make(balance="10000.00", status=CardStatus.ACTIVE):
        employee = user_factory(role=UserRole.EMPLEADO)
        card = Card(
            uid=f"UID{uuid.uuid4().hex[:10].upper()}",
            balance=Decimal(str(balance)),
            status=status,
            user_id=employee.id,
        )
        db.add(card)
        db.commit()
        db.refresh(card)
        db.refresh(employee)
        return employee, card

    return make


@pytest.fixture()
def product_factory(db):
    def make(price="2500.00", stock=10, cost="1000.00", is_active=True):
        category = Category(name=f"Cat-{uuid.uuid4().hex[:8]}")
        db.add(category)
        db.flush()

        product = Product(
            name=f"Producto {uuid.uuid4().hex[:6]}",
            category_id=category.id,
            price=Decimal(str(price)),
            cost=Decimal(str(cost)),
            stock=stock,
            is_active=is_active,
        )
        db.add(product)
        db.commit()
        db.refresh(product)
        return product

    return make
