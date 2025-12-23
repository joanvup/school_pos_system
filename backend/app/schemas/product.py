from pydantic import BaseModel
from typing import Optional
from datetime import datetime
# Importamos CategoryResponse para poder anidarlo en la respuesta
from app.schemas.category import CategoryResponse 

# Base común para evitar repetición
class ProductBase(BaseModel):
    name: str
    description: Optional[str] = None
    category_id: int  # Ahora es un ID obligatorio
    price: float
    cost: float
    stock: int
    low_stock_threshold: int = 5
    image_url: Optional[str] = None
    is_active: bool = True

# Schema para CREAR (Hereda todo de Base)
class ProductCreate(ProductBase):
    pass

# Schema para ACTUALIZAR (Todos los campos opcionales)
class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    price: Optional[float] = None
    cost: Optional[float] = None
    # stock: Optional[int] = None
    low_stock_threshold: Optional[int] = None
    image_url: Optional[str] = None
    is_active: Optional[bool] = None

# Schema para RESPONDER AL CLIENTE (Incluye ID y Objeto Categoría)
class ProductResponse(ProductBase):
    id: int
    updated_at: Optional[datetime] = None
    
    # Campo calculado/relacional que viene del ORM
    # Puede ser None si borraron la categoría (aunque la FK lo impide)
    category_rel: Optional[CategoryResponse] = None 

    class Config:
        from_attributes = True