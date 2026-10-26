from decimal import Decimal

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
# Importamos CategoryResponse para poder anidarlo en la respuesta
from app.schemas.category import CategoryResponse 

# Base común para evitar repetición
class ProductBase(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    category_id: int = Field(gt=0)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    cost: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    stock: int = Field(default=0, ge=0)
    low_stock_threshold: int = Field(default=5, ge=0)
    image_url: Optional[str] = None
    is_active: bool = True

# Schema para CREAR (Hereda todo de Base)
class ProductCreate(ProductBase):
    pass

# Schema para ACTUALIZAR (Todos los campos opcionales)
class ProductUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    description: Optional[str] = Field(default=None, max_length=255)
    category_id: Optional[int] = Field(default=None, gt=0)
    price: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    cost: Optional[Decimal] = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    # stock: Optional[int] = None
    low_stock_threshold: Optional[int] = Field(default=None, ge=0)
    image_url: Optional[str] = None
    is_active: Optional[bool] = None

# Schema para RESPONDER AL CLIENTE (Incluye ID y Objeto Categoría)
class ProductResponse(ProductBase):
    id: int
    price: float
    cost: float
    updated_at: Optional[datetime] = None
    
    # Campo calculado/relacional que viene del ORM
    # Puede ser None si borraron la categoría (aunque la FK lo impide)
    category_rel: Optional[CategoryResponse] = None 

    class Config:
        from_attributes = True