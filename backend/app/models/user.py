from sqlalchemy import Column, Integer, String, Boolean, Float, ForeignKey, Enum, DateTime
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
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Saldo pendiente cuando la tarjeta está desvinculada: se traslada a la nueva tarjeta al vincular otra
    pending_balance = Column(Float, default=0.0)

    # Relaciones
    students = relationship("Student", back_populates="parent")
    card = relationship("Card", back_populates="employee", uselist=False) # Solo empleados tienen tarjeta directa
    audit_logs = relationship("AuditLog", back_populates="user")

class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    full_name = Column(String(150), nullable=False)
    grade = Column(String(50)) # Grado o Curso
    parent_id = Column(Integer, ForeignKey("users.id"))

    # Saldo pendiente cuando la tarjeta está desvinculada: se traslada a la nueva tarjeta al vincular otra
    pending_balance = Column(Float, default=0.0)
    
    # Relaciones
    parent = relationship("User", back_populates="students")
    card = relationship("Card", back_populates="student", uselist=False)