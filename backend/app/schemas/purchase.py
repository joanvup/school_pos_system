from pydantic import BaseModel
from typing import List
from datetime import datetime

class OrderDetailCreate(BaseModel):
    product_id: int
    quantity: int
    unit_cost: float

class PurchaseOrderCreate(BaseModel):
    items: List[OrderDetailCreate]

class PurchaseOrderResponse(BaseModel):
    id: int
    code: str
    timestamp: datetime
    status: str
    total_cost: float
    items: List[OrderDetailCreate] = []

    class Config:
        from_attributes = True