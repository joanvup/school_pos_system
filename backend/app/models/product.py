from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.db.session import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    description = Column(String(255))
    
    # CAMBIO: Ahora es un ID apuntando a la tabla categories
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    
    price = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    cost = Column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    stock = Column(Integer, nullable=False, default=0)
    low_stock_threshold = Column(Integer, default=5)
    image_url = Column(String(255))
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relación para traer el nombre de la categoría automáticamente
    category_rel = relationship("Category", back_populates="products")

    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_products_price_non_negative"),
        CheckConstraint("cost >= 0", name="ck_products_cost_non_negative"),
        CheckConstraint("stock >= 0", name="ck_products_stock_non_negative"),
        CheckConstraint(
            "low_stock_threshold >= 0",
            name="ck_products_low_stock_threshold_non_negative",
        ),
    )