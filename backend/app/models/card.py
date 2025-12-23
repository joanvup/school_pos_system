from sqlalchemy import Column, Integer, String, Float, ForeignKey, Enum, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.session import Base

class CardStatus(str, enum.Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"

class TransactionType(str, enum.Enum):
    RECHARGE = "recharge" # Recarga PSE
    PURCHASE = "purchase" # Compra en cafetería

class Card(Base):
    __tablename__ = "cards"

    id = Column(Integer, primary_key=True, index=True)
    uid = Column(String(50), unique=True, index=True, nullable=False) # ID del chip RFID
    balance = Column(Float, default=0.0)
    status = Column(Enum(CardStatus), default=CardStatus.ACTIVE)
    daily_limit = Column(Float, nullable=True) # Opcional: limite diario de gasto
    
    # Una tarjeta pertenece a UN estudiante O a UN empleado (usuario)
    student_id = Column(Integer, ForeignKey("students.id"), unique=True, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=True) # Para empleados

    student = relationship("Student", back_populates="card")
    employee = relationship("User", back_populates="card")
    transactions = relationship("Transaction", back_populates="card")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    card_id = Column(Integer, ForeignKey("cards.id"))
    amount = Column(Float, nullable=False) # Positivo recarga, Negativo compra
    type = Column(Enum(TransactionType), nullable=False)
    description = Column(String(255))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    reference_code = Column(String(100), nullable=True) # Código PSE
    status = Column(String(20), default="completed") 

    card = relationship("Card", back_populates="transactions")
    details = relationship("TransactionDetail", back_populates="transaction")

class TransactionDetail(Base):
    __tablename__ = "transaction_details"
    
    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"))
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True) 
    product_name = Column(String(100)) # Guardamos nombre por si se borra el producto
    quantity = Column(Integer)
    unit_price = Column(Float)
    subtotal = Column(Float)

    transaction = relationship("Transaction", back_populates="details")

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id")) # Quien hizo la acción
    action = Column(String(50)) # CREATE, UPDATE, DELETE, LOGIN
    details = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="audit_logs")