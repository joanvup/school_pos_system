"""Pruebas de concurrencia reales. Requieren MySQL 8 (los locks de SQLite son no-op).

Se ejecutan solo si `TEST_DATABASE_URL` apunta a una base DE PRUEBA descartable,
por ejemplo:
    TEST_DATABASE_URL=mysql+pymysql://user:pass@localhost/school_pos_test
"""
import os
import threading

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.crud import crud_sale
from app.db.base import Base
from app.models.card import Card, CardStatus
from app.models.category import Category
from app.models.product import Product
from app.models.user import Student, User, UserRole
from app.schemas.sale import SaleCreate

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL, reason="Requiere MySQL de pruebas (TEST_DATABASE_URL)"
)


@pytest.fixture(scope="module")
def mysql_engine():
    engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def mysql_session_factory(mysql_engine):
    Session = sessionmaker(bind=mysql_engine, autocommit=False, autoflush=False)
    yield Session
    with mysql_engine.begin() as connection:
        for table in reversed(Base.metadata.sorted_tables):
            connection.execute(table.delete())


def _seed(Session, balance, stock, price, actor_role=UserRole.VENDEDOR):
    with Session() as session:
        actor = User(
            email=f"{actor_role.value}@concurrency.test",
            full_name="Actor",
            hashed_password="x",
            role=actor_role,
        )
        parent = User(
            email="parent@concurrency.test",
            full_name="Parent",
            hashed_password="x",
            role=UserRole.PADRE,
        )
        session.add_all([actor, parent])
        session.flush()

        student = Student(full_name="Student", grade="1-A", parent_id=parent.id)
        session.add(student)
        session.flush()

        card = Card(
            uid="UID-CONCURRENCY",
            balance=balance,
            status=CardStatus.ACTIVE,
            student_id=student.id,
        )
        category = Category(name="Conc")
        session.add_all([card, category])
        session.flush()

        product = Product(
            name="Producto Concurrencia",
            category_id=category.id,
            price=price,
            cost=price,
            stock=stock,
        )
        session.add(product)
        session.commit()
        return actor.id, card.id, product.id


def _run_concurrently(callables, barrier):
    results = []

    def runner(fn):
        barrier.wait()
        try:
            results.append(("ok", fn()))
        except Exception as exc:  # noqa: BLE001
            results.append(("error", exc))

    threads = [threading.Thread(target=runner, args=(fn,)) for fn in callables]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def test_concurrent_sales_never_overdraw(mysql_session_factory):
    Session = mysql_session_factory
    actor_id, card_id, product_id = _seed(
        Session, balance=5000, stock=10, price=3000
    )

    def make_call():
        def call():
            with Session() as session:
                card = session.get(Card, card_id)
                return crud_sale.process_sale(
                    session,
                    SaleCreate(
                        card_uid=card.uid,
                        items=[{"product_id": product_id, "quantity": 1}],
                    ),
                    actor_id=actor_id,
                )

        return call

    results = _run_concurrently([make_call(), make_call()], threading.Barrier(2))

    successes = [value for status, value in results if status == "ok"]
    failures = [value for status, value in results if status == "error"]
    assert len(successes) == 1
    assert len(failures) == 1

    with Session() as session:
        card = session.get(Card, card_id)
        product = session.get(Product, product_id)
        assert card.balance >= 0
        assert card.balance == 2000
        assert product.stock == 9


def test_concurrent_reverses_restore_only_once(mysql_session_factory):
    Session = mysql_session_factory
    actor_id, card_id, product_id = _seed(
        Session, balance=5000, stock=10, price=3000
    )

    with Session() as session:
        card = session.get(Card, card_id)
        sale = crud_sale.process_sale(
            session,
            SaleCreate(
                card_uid=card.uid,
                items=[{"product_id": product_id, "quantity": 1}],
            ),
            actor_id=actor_id,
        )
    transaction_id = sale["transaction_id"]

    def make_call():
        def call():
            with Session() as session:
                return crud_sale.reverse_sale(session, transaction_id, actor_id=actor_id)

        return call

    results = _run_concurrently([make_call(), make_call()], threading.Barrier(2))

    successes = [value for status, value in results if status == "ok"]
    assert len(successes) == 1

    with Session() as session:
        card = session.get(Card, card_id)
        product = session.get(Product, product_id)
        assert card.balance == 5000
        assert product.stock == 10
