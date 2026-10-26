from datetime import datetime

from pydantic import BaseModel, Field


class SaleItem(BaseModel):
    product_id: int = Field(gt=0)
    quantity: int = Field(gt=0, le=100)


class SaleCreate(BaseModel):
    card_uid: str = Field(min_length=1, max_length=50)
    items: list[SaleItem] = Field(min_length=1, max_length=50)


class SaleResponse(BaseModel):
    transaction_id: int
    total_amount: float
    new_balance: float
    timestamp: datetime
    status: str = "success"

    class Config:
        from_attributes = True
