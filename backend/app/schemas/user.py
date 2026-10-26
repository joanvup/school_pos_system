from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from datetime import datetime
from app.models.user import UserRole
from app.schemas.card import CardResponse
from app.core.security import validate_password


# Propiedades compartidas
class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=150)
    role: Optional[UserRole] = UserRole.PADRE
    is_active: Optional[bool] = True

# Propiedades para recibir al crear (request)
class UserCreate(UserBase):
    password: str = Field(min_length=10, max_length=72)

    @field_validator("password")
    @classmethod
    def _password_policy(cls, value: str) -> str:
        return validate_password(value)

class UserUpdate(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=150)
    email: Optional[EmailStr] = None
    password: Optional[str] = Field(default=None, min_length=10, max_length=72)
    is_active: Optional[bool] = None
    role: Optional[UserRole] = None

    @field_validator("password")
    @classmethod
    def _password_policy(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        return validate_password(value)

class UserResponse(UserBase):
    id: int
    must_change_password: bool = False
    created_at: Optional[datetime] = None
    card: Optional[CardResponse] = None

    class Config:
        from_attributes = True

