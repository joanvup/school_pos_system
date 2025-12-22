from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.session import Base

class StockAdjustment(Base):
    __tablename__ = "stock_adjustments"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True) # Ej: ADJ-001
    reason = Column(Text, nullable=False) # Explicación del ajuste
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(Integer, ForeignKey("users.id")) # Admin que ajustó

    user = relationship("User")
    details = relationship("StockAdjustmentDetail", back_populates="adjustment", cascade="all, delete-orphan")

class StockAdjustmentDetail(Base):
    __tablename__ = "stock_adjustment_details"

    id = Column(Integer, primary_key=True, index=True)
    adjustment_id = Column(Integer, ForeignKey("stock_adjustments.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    quantity = Column(Integer, nullable=False) # Puede ser positivo (+5) o negativo (-3)

    adjustment = relationship("StockAdjustment", back_populates="details")
    product = relationship("Product")