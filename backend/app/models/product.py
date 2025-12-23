from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship # Importante
from app.db.session import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    description = Column(String(255))
    
    # CAMBIO: Ahora es un ID apuntando a la tabla categories
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    
    price = Column(Float, nullable=False)
    cost = Column(Float, nullable=False)
    stock = Column(Integer, default=0)
    low_stock_threshold = Column(Integer, default=5)
    image_url = Column(String(255))
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relación para traer el nombre de la categoría automáticamente
    category_rel = relationship("Category", back_populates="products")