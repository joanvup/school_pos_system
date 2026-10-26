from decimal import Decimal
import enum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class CardStatus(str, enum.Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"


class TransactionType(str, enum.Enum):
    RECHARGE = "recharge"
    PURCHASE = "purchase"


class TransactionStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    DECLINED = "declined"
    COMPLETED = "completed"
    REVERSED = "reversed"
    FAILED = "failed"
    EXPIRED = "expired"


MONEY = Numeric(12, 2)


class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(50), unique=True, index=True, nullable=False)
    balance = Column(MONEY, nullable=False, default=Decimal("0.00"))
    status = Column(Enum(CardStatus), default=CardStatus.ACTIVE, nullable=False)
    daily_limit = Column(MONEY, nullable=True)

    student_id = Column(Integer, ForeignKey("students.id"), unique=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True)

    student = relationship("Student", back_populates="card")
    employee = relationship("User", back_populates="card")
    transactions = relationship("Transaction", back_populates="card")

    __table_args__ = (
        CheckConstraint("balance >= 0", name="ck_cards_balance_non_negative"),
        CheckConstraint(
            "daily_limit IS NULL OR daily_limit >= 0",
            name="ck_cards_daily_limit_non_negative",
        ),
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(Integer, ForeignKey("cards.id"), nullable=False, index=True)
    amount = Column(MONEY, nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    description = Column(String(255))
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    reference_code = Column(String(64), nullable=True, unique=True, index=True)
    status = Column(String(20), nullable=False, default=TransactionStatus.COMPLETED.value)
    cus = Column(String(100), nullable=True, index=True)
    gateway = Column(String(30), default="payu", index=True)
    currency = Column(String(10), default="COP")
    payment_method = Column(String(30), nullable=True)
    raw_notification = Column(Text, nullable=True)
    response_code = Column(String(100), nullable=True)
    credited_at = Column(DateTime(timezone=True), nullable=True)
    reversed_at = Column(DateTime(timezone=True), nullable=True)
    reversed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    card = relationship("Card", back_populates="transactions")
    details = relationship("TransactionDetail", back_populates="transaction")

    __table_args__ = (
        CheckConstraint("amount <> 0", name="ck_transactions_amount_non_zero"),
        Index("ix_transactions_card_timestamp", "card_id", "timestamp"),
        Index("ix_transactions_status_type", "status", "type"),
        Index("ix_transactions_gateway_reference", "gateway", "reference_code"),
    )


class TransactionDetail(Base):
    __tablename__ = "transaction_details"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(
        Integer, ForeignKey("transactions.id"), nullable=False, index=True
    )
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    product_name = Column(String(100))
    quantity = Column(Integer, nullable=False)
    unit_price = Column(MONEY, nullable=False)
    subtotal = Column(MONEY, nullable=False)

    transaction = relationship("Transaction", back_populates="details")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_transaction_details_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="ck_transaction_details_price_non_negative"),
        CheckConstraint("subtotal >= 0", name="ck_transaction_details_subtotal_non_negative"),
    )


class PaymentNotification(Base):
    __tablename__ = "payment_notifications"

    id = Column(Integer, primary_key=True, index=True)
    reference_code = Column(String(64), nullable=True, index=True)
    gateway = Column(String(30), nullable=False, default="payu")
    raw = Column(Text, nullable=True)
    remote_ip = Column(String(45), nullable=True)
    signature_valid = Column(Boolean, nullable=False, default=False)
    reason = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    action = Column(String(50), nullable=False, index=True)
    entity = Column(String(30), nullable=True)
    entity_id = Column(Integer, nullable=True)
    details = Column(Text)
    ip = Column(String(45), nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    user = relationship("User", back_populates="audit_logs")
