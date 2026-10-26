from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field


class OrderDetailCreate(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=10000)
    unit_cost: Decimal = Field(gt=0, max_digits=12, decimal_places=2)


class PurchaseOrderCreate(BaseModel):
    items: list[OrderDetailCreate] = Field(min_length=1, max_length=200)


class OrderDetailResponse(BaseModel):
    product_id: int
    quantity: int
    unit_cost: float

    class Config:
        from_attributes = True


class PurchaseOrderResponse(BaseModel):
    id: int
    code: str
    timestamp: datetime
    status: str
    total_cost: float
    items: list[OrderDetailResponse] = []

    class Config:
        from_attributes = True
