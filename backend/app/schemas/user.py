from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from app.models.user import UserRole
from app.schemas.card import CardResponse 


# Propiedades compartidas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str
    role: Optional[UserRole] = UserRole.PADRE
    is_active: Optional[bool] = True

# Propiedades para recibir al crear (request)
class UserCreate(UserBase):
    password: str

# Propiedades para devolver al cliente (response)
class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True # Antes 'orm_mode' en Pydantic v1

class UserUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[EmailStr] = None
    password: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None

class UserResponse(UserBase):
    id: int
    created_at: Optional[datetime] = None
    # CAMPO NUEVO:
    card: Optional[CardResponse] = None 

    class Config:
        from_attributes = True

