from pydantic import BaseModel
from typing import Optional, Any
from enum import Enum

class CardStatus(str, Enum):
    ACTIVE = "active"
    BLOCKED = "blocked"

class CardBase(BaseModel):
    uid: str
    daily_limit: Optional[float] = None

class CardCreate(CardBase):
    student_id: Optional[int] = None
    user_id: Optional[int] = None

class CardUpdate(BaseModel):
    status: Optional[str] = None
    daily_limit: Optional[float] = None
    is_active: Optional[bool] = None

class CardResponse(CardBase):
    id: int
    balance: float
    status: str
    # No incluimos objetos 'student' o 'employee' aquí para evitar el bucle
    class Config:
        from_attributes = True