from pydantic import BaseModel
from typing import Optional
from app.schemas.card import CardResponse

class StudentBase(BaseModel):
    full_name: str
    grade: str # Curso: "5A", "11B", etc.

class StudentCreate(StudentBase):
    parent_id: int # El ID del padre en la tabla Users

class StudentUpdate(StudentBase):
    full_name: Optional[str] = None
    grade: Optional[str] = None
    parent_id: Optional[int] = None

class StudentResponse(StudentBase):
    id: int
    parent_id: int
    card: Optional[CardResponse] = None

    class Config:
        from_attributes = True