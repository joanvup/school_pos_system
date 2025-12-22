from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Un item dentro del carrito de compras
class SaleItem(BaseModel):
    product_id: int
    quantity: int

# La petición de venta completa
class SaleCreate(BaseModel):
    card_uid: str
    items: List[SaleItem]

# Respuesta de la venta (Ticket digital)
class SaleResponse(BaseModel):
    transaction_id: int
    total_amount: float
    new_balance: float
    timestamp: datetime
    status: str = "success"

    class Config:
        from_attributes = True