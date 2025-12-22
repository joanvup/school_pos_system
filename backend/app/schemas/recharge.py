from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class RechargeCreate(BaseModel):
    card_uid: str
    amount: float

class RechargeResponse(BaseModel):
    transaction_id: int
    reference_code: str
    amount: float
    new_balance: float
    status: str = "APPROVED"
    timestamp: datetime

    class Config:
        from_attributes = True