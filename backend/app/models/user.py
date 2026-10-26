from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.session import Base

class UserRole(str, enum.Enum):
    ADMIN = "admin"
    SUPERVISOR = "supervisor"
    VENDEDOR = "vendedor"
    PADRE = "padre"
    EMPLEADO = "empleado"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.PADRE)
    is_active = Column(Boolean, default=True)
    must_change_password = Column(Boolean, default=False, nullable=False)
    token_version = Column(Integer, default=0, nullable=False)
    failed_login_attempts = Column(Integer, default=0, nullable=False)
    locked_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Saldo pendiente cuando la tarjeta está desvinculada: se traslada a la nueva tarjeta al vincular otra
    pending_balance = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))

    # Relaciones
    students = relationship("Student", back_populates="parent")
    card = relationship("Card", back_populates="employee", uselist=False)
    audit_logs = relationship("AuditLog", back_populates="user")

    __table_args__ = (
        CheckConstraint("pending_balance >= 0", name="ck_users_pending_balance_non_negative"),
        CheckConstraint("token_version >= 0", name="ck_users_token_version_non_negative"),
        CheckConstraint(
            "failed_login_attempts >= 0",
            name="ck_users_failed_login_attempts_non_negative",
        ),
    )

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False)
    grade = Column(String(50)) # Grado o Curso
    parent_id = Column(Integer, ForeignKey("users.id"))

    # Saldo pendiente cuando la tarjeta está desvinculada: se traslada a la nueva tarjeta al vincular otra
    pending_balance = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    
    # Relaciones
    parent = relationship("User", back_populates="students")
    card = relationship("Card", back_populates="student", uselist=False)

    __table_args__ = (
        CheckConstraint(
            "pending_balance >= 0",
            name="ck_students_pending_balance_non_negative",
        ),
    )