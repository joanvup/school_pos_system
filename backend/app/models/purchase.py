from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.session import Base

class OrderStatus(str, enum.Enum):
    COMPLETED = "completed" # Orden aplicada al stock
    CANCELLED = "cancelled" # Orden anulada

class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True) # Ej: OC-0001
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    status = Column(Enum(OrderStatus), default=OrderStatus.COMPLETED)
    total_cost = Column(Float, default=0.0)
    
    # Usuario que creó la orden
    user_id = Column(Integer, ForeignKey("users.id"))
    
    user = relationship("User")
    details = relationship("PurchaseOrderDetail", back_populates="order", cascade="all, delete-orphan")

class PurchaseOrderDetail(Base):
    __tablename__ = "purchase_order_details"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("purchase_orders.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    
    quantity = Column(Integer, nullable=False) # Cantidad que entró
    unit_cost = Column(Float, nullable=False)  # Costo al momento de la compra

    order = relationship("PurchaseOrder", back_populates="details")
    product = relationship("Product")