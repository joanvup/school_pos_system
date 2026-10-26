from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CardStatus(str, Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"


class CardBase(BaseModel):
    uid: str = Field(min_length=1, max_length=50)
    daily_limit: Optional[Decimal] = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )


class CardCreate(CardBase):
    student_id: Optional[int] = Field(default=None, gt=0)
    user_id: Optional[int] = Field(default=None, gt=0)


class CardUpdate(BaseModel):
    status: Optional[CardStatus] = None
    daily_limit: Optional[Decimal] = Field(
        default=None, ge=0, max_digits=12, decimal_places=2
    )


class CardResponse(CardBase):
    id: int
    balance: float
    status: str

    class Config:
        from_attributes = True
